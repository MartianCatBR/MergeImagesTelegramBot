package main

import (
	"bytes"
	"crypto/hmac"
	"crypto/sha256"
	"crypto/subtle"
	"database/sql"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"html"
	"io"
	"log"
	"mime/multipart"
	"net"
	"net/http"
	"net/url"
	"os"
	"runtime"
	"sort"
	"strconv"
	"strings"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/cors"
	"github.com/gofiber/fiber/v2/middleware/helmet"
	"github.com/gofiber/fiber/v2/middleware/logger"
	_ "github.com/mattn/go-sqlite3"
)

func validateInitData(initData string, token string) bool {
	q, err := url.ParseQuery(initData)
	if err != nil {
		return false
	}
	hash := q.Get("hash")
	if hash == "" {
		return false
	}
	q.Del("hash")

	var keys []string
	for k := range q {
		keys = append(keys, k)
	}
	sort.Strings(keys)

	var dataCheckArr []string
	for _, k := range keys {
		dataCheckArr = append(dataCheckArr, k+"="+q.Get(k))
	}
	dataCheckString := strings.Join(dataCheckArr, "\n")

	macSecret := hmac.New(sha256.New, []byte("WebAppData"))
	macSecret.Write([]byte(token))
	secretKey := macSecret.Sum(nil)

	macData := hmac.New(sha256.New, secretKey)
	macData.Write([]byte(dataCheckString))
	calculatedHash := hex.EncodeToString(macData.Sum(nil))

	return subtle.ConstantTimeCompare([]byte(calculatedHash), []byte(hash)) == 1
}

func userIDFromInitData(initData string) string {
	q, err := url.ParseQuery(initData)
	if err != nil {
		return ""
	}

	var userData struct {
		ID int64 `json:"id"`
	}
	if err := json.Unmarshal([]byte(q.Get("user")), &userData); err != nil || userData.ID == 0 {
		return ""
	}

	return fmt.Sprintf("%d", userData.ID)
}

func isAdminNotificationsEnabled(userID string) bool {
	db, err := sql.Open("sqlite3", "../data/user_images.db")
	if err != nil {
		log.Printf("Erro ao abrir db para checar notificações: %v", err)
		return true
	}
	defer db.Close()

	var value string
	err = db.QueryRow("SELECT value FROM system_config WHERE key = 'admin_notifications'").Scan(&value)
	if err == nil && value == "0" {
		return false
	}

	if userID != "" {
		var mutedID string
		err = db.QueryRow("SELECT user_id FROM muted_users WHERE user_id = ?", userID).Scan(&mutedID)
		if err == nil {
			// user is muted
			return false
		}
	}
	return true
}

var telegramToken = os.Getenv("TELEGRAM_TOKEN")
var startTime = time.Now()
var telegramHTTPTimeout = durationFromEnv("TELEGRAM_HTTP_TIMEOUT", 30*time.Second)
var telegramHTTPClient = &http.Client{Timeout: telegramHTTPTimeout}

var adminID = os.Getenv("ADMIN_ID")

type quotaInfo struct {
	ImagesSinceLastAd int
	Threshold         int
	TotalAdsSeen      int
	IsPremium         bool
	PremiumUntil      string
}

func durationFromEnv(name string, fallback time.Duration) time.Duration {
	value := os.Getenv(name)
	if value == "" {
		return fallback
	}
	seconds, err := time.ParseDuration(value + "s")
	if err != nil {
		log.Printf("AVISO: %s inválido (%q), usando %s", name, value, fallback)
		return fallback
	}
	return seconds
}

func isPlaceholderTelegramToken(token string) bool {
	return strings.Contains(token, "replace_with_your_bot_token") || strings.HasPrefix(token, "1234567890:")
}

func logTelegramConnectivityCheck() {
	host := "api.telegram.org"
	port := "443"
	ip, err := net.LookupHost(host)
	if err != nil {
		log.Printf("Diagnóstico Telegram: falha de DNS para %s: %v", host, err)
		return
	}
	log.Printf("Diagnóstico Telegram: DNS OK %s -> %s", host, strings.Join(ip, ", "))

	conn, err := net.DialTimeout("tcp", net.JoinHostPort(host, port), telegramHTTPTimeout)
	if err != nil {
		log.Printf("Diagnóstico Telegram: falha TCP em %s:%s: %v", host, port, err)
		return
	}
	conn.Close()
	log.Printf("Diagnóstico Telegram: TCP OK em %s:%s", host, port)
}

func logMiniAppUsage(userID string, actionName string) {
	db, err := sql.Open("sqlite3", "../data/user_images.db")
	if err != nil {
		return
	}
	defer db.Close()
	_, _ = db.Exec("INSERT INTO activity_logs (user_id, username, action, timestamp) VALUES (?, NULL, ?, datetime('now'))", userID, actionName)
}

func parsePremiumActive(value string) bool {
	value = strings.TrimSpace(value)
	if value == "" {
		return false
	}
	layouts := []string{
		time.RFC3339,
		"2006-01-02T15:04:05.999999",
		"2006-01-02T15:04:05",
		"2006-01-02 15:04:05.999999",
		"2006-01-02 15:04:05",
	}
	for _, layout := range layouts {
		if parsed, err := time.Parse(layout, value); err == nil {
			return time.Now().Before(parsed)
		}
	}
	return false
}

func loadQuotaInfo(db *sql.DB, userID string) quotaInfo {
	info := quotaInfo{Threshold: 50}

	var thresholdValue string
	if err := db.QueryRow("SELECT value FROM system_config WHERE key = 'ad_threshold'").Scan(&thresholdValue); err == nil {
		if parsed, err := strconv.Atoi(thresholdValue); err == nil && parsed > 0 {
			info.Threshold = parsed
		}
	}

	var premiumUntil sql.NullString
	var isPremium int
	err := db.QueryRow(
		"SELECT COALESCE(images_since_last_ad, 0), COALESCE(total_voluntary_ads, 0), COALESCE(is_premium, 0), premium_until FROM users WHERE user_id = ?",
		userID,
	).Scan(&info.ImagesSinceLastAd, &info.TotalAdsSeen, &isPremium, &premiumUntil)
	if err != nil {
		return info
	}
	info.IsPremium = isPremium == 1 || (premiumUntil.Valid && parsePremiumActive(premiumUntil.String))
	if premiumUntil.Valid {
		info.PremiumUntil = premiumUntil.String
	}
	return info
}

func quotaBlocksUsage(info quotaInfo) bool {
	if info.IsPremium {
		return false
	}
	return info.ImagesSinceLastAd >= info.Threshold
}

func incrementUserCredits(userID string) {
	db, err := sql.Open("sqlite3", "../data/user_images.db")
	if err != nil {
		log.Printf("Erro ao abrir db para incrementar créditos user_id=%s: %v", userID, err)
		return
	}
	defer db.Close()

	_, err = db.Exec("UPDATE users SET images_since_last_ad = images_since_last_ad + 1, total_credits_spent = total_credits_spent + 1 WHERE user_id = ?", userID)
	if err != nil {
		log.Printf("Erro ao incrementar créditos user_id=%s: %v", userID, err)
	}
}

func miniAppAdminCaption(userID string) string {
	firstName := "N/A"
	creditsRemaining := 0
	totalAdsSeen := 0

	db, err := sql.Open("sqlite3", "../data/user_images.db")
	if err == nil {
		defer db.Close()
		var dbFirstName sql.NullString
		err = db.QueryRow(
			"SELECT first_name FROM users WHERE user_id = ?",
			userID,
		).Scan(&dbFirstName)
		if err == nil {
			if dbFirstName.Valid && dbFirstName.String != "" {
				firstName = dbFirstName.String
			}

		} else {
			log.Printf("[upload] failed to load user info for admin caption user_id=%s: %v", userID, err)
		}
		info := loadQuotaInfo(db, userID)
		creditsRemaining = info.Threshold - info.ImagesSinceLastAd
		if creditsRemaining < 0 {
			creditsRemaining = 0
		}
		totalAdsSeen = info.TotalAdsSeen
	} else {
		log.Printf("[upload] failed to open db for admin caption user_id=%s: %v", userID, err)
	}

	return fmt.Sprintf(
		"🖼️ Imagem criada por: %s | %s\n🛠️ Ferramenta: MiniApp | Créditos restantes: %d | Ads vistos: %d",
		html.EscapeString(firstName),
		html.EscapeString(userID),
		creditsRemaining,
		totalAdsSeen,
	)
}

func main() {
	if telegramToken == "" {
		log.Println("AVISO: TELEGRAM_TOKEN não definido. O envio para o Telegram não funcionará.")
	} else if isPlaceholderTelegramToken(telegramToken) {
		log.Fatal("ERRO: TELEGRAM_TOKEN ainda está com o valor de exemplo. Configure o token real do BotFather.")
	}
	logTelegramConnectivityCheck()

	app := fiber.New(fiber.Config{
		BodyLimit: 12 * 1024 * 1024,
	})
	app.Use(logger.New(logger.Config{
		Next: func(c *fiber.Ctx) bool {
			return c.Path() == "/favicon.ico"
		},
	}))
	allowedOrigins := os.Getenv("MINIAPP_ALLOWED_ORIGINS")
	if allowedOrigins == "" {
		allowedOrigins = "https://your-miniapp-domain.com"
	}
	app.Use(cors.New(cors.Config{
		AllowOrigins:     allowedOrigins,
		AllowMethods:     "GET,POST,OPTIONS",
		AllowHeaders:     "Content-Type",
		AllowCredentials: false,
	}))
	app.Use(helmet.New())

	app.Use(func(c *fiber.Ctx) error {
		c.Set("Cache-Control", "no-store, no-cache, must-revalidate, proxy-revalidate")
		c.Set("Pragma", "no-cache")
		c.Set("Expires", "0")
		return c.Next()
	})

	app.Get("/favicon.ico", func(c *fiber.Ctx) error {
		return c.SendStatus(fiber.StatusNoContent)
	})

	// Servir arquivos estáticos do frontend
	app.Static("/", "./public", fiber.Static{
		CacheDuration: -1 * time.Second,
	})
	// Endpoint genérico para logar interações do Mini App.
	app.Post("/api/log_miniapp_action", func(c *fiber.Ctx) error {
		var reqData struct {
			InitData string `json:"init_data"`
		}
		if err := c.BodyParser(&reqData); err != nil {
			return c.SendStatus(400)
		}
		if telegramToken == "" || reqData.InitData == "" || !validateInitData(reqData.InitData, telegramToken) {
			return c.Status(401).JSON(fiber.Map{"error": "Unauthorized"})
		}
		userID := userIDFromInitData(reqData.InitData)
		if userID == "" {
			return c.Status(401).JSON(fiber.Map{"error": "Unauthorized"})
		}
		go logMiniAppUsage(userID, "miniapp_usage")
		return c.SendStatus(200)
	})

	// Endpoint para recuperar o idioma salvo no bot tradicional
	app.Post("/api/user_language", func(c *fiber.Ctx) error {
		var reqData struct {
			InitData string `json:"init_data"`
		}

		if err := c.BodyParser(&reqData); err != nil {
			return c.Status(400).JSON(fiber.Map{"error": "invalid JSON payload"})
		}

		if telegramToken == "" {
			return c.Status(500).JSON(fiber.Map{"error": "telegram token is not configured"})
		}

		if reqData.InitData == "" || !validateInitData(reqData.InitData, telegramToken) {
			return c.Status(401).JSON(fiber.Map{"error": "Unauthorized. Invalid initData signature."})
		}

		userID := userIDFromInitData(reqData.InitData)
		if userID == "" {
			return c.Status(400).JSON(fiber.Map{"error": "user_id is required"})
		}

		db, err := sql.Open("sqlite3", "../data/user_images.db")
		if err != nil {
			log.Printf("Erro ao abrir db para idioma user_id=%s: %v", userID, err)
			return c.Status(500).JSON(fiber.Map{"error": "database error"})
		}
		defer db.Close()

		var lang string
		err = db.QueryRow(
			"SELECT COALESCE(custom_language, language_code, '') FROM users WHERE user_id = ?",
			userID,
		).Scan(&lang)
		if err == sql.ErrNoRows {
			return c.JSON(fiber.Map{"language": ""})
		}
		if err != nil {
			log.Printf("Erro ao consultar idioma user_id=%s: %v", userID, err)
			return c.Status(500).JSON(fiber.Map{"error": "database error"})
		}

		return c.JSON(fiber.Map{"language": lang})
	})

	// Endpoint para atualizar o idioma do usuário (sincronização entre miniapp e bot)
	app.Post("/api/update_user_language", func(c *fiber.Ctx) error {
		log.Println("[LANG] /api/update_user_language request received")
		var reqData struct {
			InitData string `json:"init_data"`
			Language string `json:"language"`
		}

		if err := c.BodyParser(&reqData); err != nil {
			log.Printf("[LANG] Failed to parse body: %v", err)
			return c.Status(400).JSON(fiber.Map{"success": false, "message": "invalid JSON payload"})
		}

		if telegramToken == "" {
			log.Println("[LANG] Telegram token not configured")
			return c.Status(500).JSON(fiber.Map{"success": false, "message": "telegram token is not configured"})
		}

		if reqData.InitData == "" || !validateInitData(reqData.InitData, telegramToken) {
			log.Println("[LANG] Invalid or missing initData")
			return c.Status(401).JSON(fiber.Map{"success": false, "message": "Unauthorized. Invalid initData signature."})
		}

		userID := userIDFromInitData(reqData.InitData)
		if userID == "" {
			log.Println("[LANG] user_id missing after extracting from initData")
			return c.Status(400).JSON(fiber.Map{"success": false, "message": "user_id is required"})
		}

		if reqData.Language == "" {
			log.Println("[LANG] language is required but was empty")
			return c.Status(400).JSON(fiber.Map{"success": false, "message": "language is required"})
		}
		supportedLanguages := map[string]bool{
			"pt": true,
			"en": true,
			"es": true,
			"ru": true,
			"ar": true,
			"fr": true,
			"it": true,
		}
		if !supportedLanguages[reqData.Language] {
			log.Printf("[LANG] unsupported language received: %s", reqData.Language)
			return c.Status(400).JSON(fiber.Map{"success": false, "message": "unsupported language"})
		}

		log.Printf("[LANG] Opening DB for user_id=%s to update language to %s", userID, reqData.Language)
		db, err := sql.Open("sqlite3", "../data/user_images.db")
		if err != nil {
			log.Printf("Erro ao abrir db para atualizar idioma user_id=%s: %v", userID, err)
			return c.Status(500).JSON(fiber.Map{"success": false, "message": "database error"})
		}
		defer db.Close()

		// Atualiza o idioma customizado do usuário
		result, err := db.Exec(
			"UPDATE users SET custom_language = ? WHERE user_id = ?",
			reqData.Language,
			userID,
		)
		if err != nil {
			log.Printf("[LANG] Erro ao atualizar idioma user_id=%s language=%s: %v", userID, reqData.Language, err)
			return c.Status(500).JSON(fiber.Map{"success": false, "message": "failed to update language"})
		}

		rowsAffected, _ := result.RowsAffected()
		if rowsAffected == 0 {
			log.Printf("[LANG] No user found to update language user_id=%s language=%s", userID, reqData.Language)
			return c.Status(404).JSON(fiber.Map{"success": false, "message": "user not found"})
		}
		log.Printf("[LANG] ✓ Language updated for user_id=%s: %s (Rows affected: %d)", userID, reqData.Language, rowsAffected)

		// Mensagens de aviso para o usuário no bot tradicional
		langMessages := map[string]string{
			"pt": "ℹ️ O idioma da sua interface Web foi atualizado! Para aplicar essa alteração aos menus e botões do bot, por favor, envie o comando /start.",
			"en": "ℹ️ Your Web interface language has been updated! To apply this change to the bot's menus and buttons, please send the /start command.",
			"es": "ℹ️ ¡El idioma de tu interfaz web ha sido actualizado! Para aplicar este cambio a los menús y botones del bot, por favor, envía el comando /start.",
			"ru": "ℹ️ Язык веб-интерфейса обновлен! Чтобы применить это изменение к меню и кнопкам бота, отправьте команду /start.",
			"ar": "ℹ️ تم تحديث لغة واجهة الويب الخاصة بك! لتطبيق هذا التغيير على قوائم وأزرار البوت، يرجى إرسال الأمر /start.",
			"fr": "ℹ️ La langue de votre interface Web a été mise à jour ! Pour appliquer ce changement aux menus et boutons du bot, veuillez envoyer la commande /start.",
			"it": "ℹ️ La lingua dell'interfaccia web è stata aggiornata! Per applicare questa modifica ai menu e ai pulsanti del bot, invia il comando /start.",
		}

		botMsg, exists := langMessages[reqData.Language]
		if !exists {
			botMsg = langMessages["en"]
		}

		payload := map[string]interface{}{
			"chat_id": userID,
			"text":    botMsg,
		}
		bodyData, _ := json.Marshal(payload)

		req, errReq := http.NewRequest("POST", fmt.Sprintf("https://api.telegram.org/bot%s/sendMessage", telegramToken), bytes.NewBuffer(bodyData))
		if errReq == nil {
			req.Header.Set("Content-Type", "application/json")
			resp, errResp := telegramHTTPClient.Do(req)
			if errResp == nil {
				resp.Body.Close()
			} else {
				log.Printf("[LANG] Failed to send telegram message to user: %v", errResp)
			}
		}

		return c.JSON(fiber.Map{"success": true, "message": "language updated successfully"})
	})

	// Endpoint para registrar que o anúncio foi assistido
	app.Post("/api/reward_ad_watched", func(c *fiber.Ctx) error {
		var reqData struct {
			InitData string `json:"init_data"`
			Type     string `json:"type"`
		}

		if err := c.BodyParser(&reqData); err != nil {
			return c.Status(400).JSON(fiber.Map{"success": false, "message": "invalid JSON payload"})
		}

		if telegramToken == "" {
			return c.Status(500).JSON(fiber.Map{"success": false, "message": "telegram token is not configured"})
		}

		if reqData.InitData == "" || !validateInitData(reqData.InitData, telegramToken) {
			return c.Status(401).JSON(fiber.Map{"success": false, "message": "Unauthorized. Invalid initData signature."})
		}
		if reqData.Type != "quota" && reqData.Type != "voluntary" {
			return c.Status(400).JSON(fiber.Map{"success": false, "message": "unsupported reward type"})
		}

		userID := userIDFromInitData(reqData.InitData)
		if userID == "" {
			return c.Status(400).JSON(fiber.Map{"success": false, "message": "user_id is required"})
		}

		db, err := sql.Open("sqlite3", "../data/user_images.db")
		if err != nil {
			log.Printf("Erro ao abrir db para zerar cota user_id=%s: %v", userID, err)
			return c.Status(500).JSON(fiber.Map{"success": false, "message": "database error"})
		}
		defer db.Close()

		isVoluntary := reqData.Type == "voluntary"
		if !isVoluntary {
			quota := loadQuotaInfo(db, userID)
			if !quotaBlocksUsage(quota) {
				return c.Status(409).JSON(fiber.Map{"success": false, "message": "quota is not currently blocked"})
			}
		}
		if isVoluntary {
			tx, errTx := db.Begin()
			if errTx != nil {
				log.Printf("Erro ao iniciar transacao user_id=%s: %v", userID, errTx)
				return c.Status(500).JSON(fiber.Map{"success": false, "message": "database error"})
			}
			defer tx.Rollback()

			_, err = tx.Exec("UPDATE users SET images_since_last_ad = 0, total_voluntary_ads = total_voluntary_ads + 1 WHERE user_id = ?", userID)
			if err != nil {
				log.Printf("Erro ao atualizar total_voluntary_ads user_id=%s: %v", userID, err)
				return c.Status(500).JSON(fiber.Map{"success": false, "message": "failed to update database"})
			}

			_, err = tx.Exec("INSERT INTO donation_history (user_id, amount_stars, currency) VALUES (?, 0.2, 'voluntary_ad')", userID)
			if err != nil {
				log.Printf("Erro ao inserir em donation_history user_id=%s: %v", userID, err)
				return c.Status(500).JSON(fiber.Map{"success": false, "message": "failed to update database"})
			}

			// Recalcular donor_status
			var totalDonatedStars float64
			var totalVoluntaryAds int
			err = tx.QueryRow("SELECT COALESCE(total_donated_stars, 0), COALESCE(total_voluntary_ads, 0) FROM users WHERE user_id = ?", userID).Scan(&totalDonatedStars, &totalVoluntaryAds)
			if err == nil {
				virtualStars := totalDonatedStars + (float64(totalVoluntaryAds) / 5.0)
				status := "🌟 Iniciante"
				if virtualStars >= 1000 {
					status = "👑 Lenda"
				} else if virtualStars >= 500 {
					status = "💎 Ouro"
				} else if virtualStars >= 250 {
					status = "🥈 Prata"
				} else if virtualStars >= 50 {
					status = "🥉 Bronze"
				}
				_, err = tx.Exec("UPDATE users SET donor_status = ? WHERE user_id = ?", status, userID)
				if err != nil {
					log.Printf("Erro ao atualizar donor_status user_id=%s: %v", userID, err)
				}
			} else {
				log.Printf("Erro ao consultar dados para status user_id=%s: %v", userID, err)
			}

			err = tx.Commit()
			if err != nil {
				log.Printf("Erro ao fazer commit da transacao user_id=%s: %v", userID, err)
				return c.Status(500).JSON(fiber.Map{"success": false, "message": "failed to commit transaction"})
			}
		} else {
			_, err = db.Exec("UPDATE users SET images_since_last_ad = 0 WHERE user_id = ?", userID)
			if err != nil {
				log.Printf("Erro ao zerar cota de anuncios user_id=%s: %v", userID, err)
				return c.Status(500).JSON(fiber.Map{"success": false, "message": "failed to update database"})
			}
		}

		log.Printf("Cota de anúncios resetada para user_id=%s (Voluntario=%t)", userID, isVoluntary)

		// Query user language code
		var lang string
		err = db.QueryRow("SELECT COALESCE(custom_language, language_code, 'pt') FROM users WHERE user_id = ?", userID).Scan(&lang)
		if err != nil {
			lang = "pt"
		}
		// Normalize language code to first 2 letters
		lang = strings.ToLower(lang)
		if len(lang) > 2 {
			lang = lang[:2]
		}

		// Envia mensagem de agradecimento pelo bot
		var thankMsg string
		if isVoluntary {
			switch lang {
			case "en":
				thankMsg = "🎉 <b>Thank you for your voluntary support!</b>\n\nYou watched the complete ad of your own free will and helped keep UnifyImages online and free for everyone! Your attitude makes all the difference. ❤️"
			case "es":
				thankMsg = "🎉 <b>¡Gracias por tu apoyo voluntario!</b>\n\n¡Has visto el anuncio completo por tu propia voluntad y has ayudado a mantener UnifyImages en línea y gratis para todos! Tu actitud marca la diferencia. ❤️"
			case "fr":
				thankMsg = "🎉 <b>Merci pour votre soutien volontaire !</b>\n\nVous avez regardé la publicité complète de votre plein gré et avez aidé à maintenir UnifyImages en ligne et gratuit pour tous ! Votre attitude fait toute la différence. ❤️"
			case "it":
				thankMsg = "🎉 <b>Grazie per il tuo supporto volontario!</b>\n\nHai guardato l'annuncio completo di tua spontanea volontà e hai aiutato a mantenere UnifyImages online e gratuito per tutti! Il tuo atteggiamento fa la differenza. ❤️"
			case "ru":
				thankMsg = "🎉 <b>Спасибо за вашу добровольную поддержку!</b>\n\nВы добровольно посмотрели рекламу до конца и помогли сохранить UnifyImages в сети и бесплатным для всех! Ваше участие имеет огромное значение. ❤️"
			case "ar":
				thankMsg = "🎉 <b>شكراً لك على دعمك الطوعي!</b>\n\nلقد شاهدت الإعلان كاملاً بمحض إرادتك وساعدت في إبقاء UnifyImages متاحاً على الإنترنت ومجانياً للجميع! موقفك يصنع كل الفرق. ❤️"
			default: // pt
				thankMsg = "🎉 <b>Obrigado pelo seu apoio voluntário!</b>\n\nVocê assistiu ao anúncio completo de livre e espontânea vontade e ajudou a manter o UnifyImages online e gratuito para todos! Sua atitude faz toda a diferença. ❤️"
			}
		} else {
			switch lang {
			case "en":
				thankMsg = "🎉 <b>Thank you for supporting the bot!</b>\n\nYour image creation limit has been restored. You can now go back to editing!"
			case "es":
				thankMsg = "🎉 <b>¡Gracias por apoyar al bot!</b>\n\nSe ha restablecido tu límite de creación de imágenes. ¡Ya puedes volver a editar!"
			case "fr":
				thankMsg = "🎉 <b>Merci de soutenir le bot !</b>\n\nVotre limite de création d'images a été restaurée. Vous pouvez maintenant recommencer à éditer !"
			case "it":
				thankMsg = "🎉 <b>Grazie per aver supportato il bot!</b>\n\nIl tuo limite di creazione delle immagini è stato ripristinato. Ora puoi tornare a modificare!"
			case "ru":
				thankMsg = "🎉 <b>Спасибо за поддержку бота!</b>\n\nЛимит на создание изображений восстановлен. Вы можете вернуться к редактированию!"
			case "ar":
				thankMsg = "🎉 <b>شكراً لدعمك البوت!</b>\n\nتم استعادة حد إنشاء الصور الخاص بك. يمكنك الآن العودة إلى التعديل!"
			default: // pt
				thankMsg = "🎉 <b>Obrigado por apoiar o bot!</b>\n\nO seu limite de criação de imagens foi restaurado. Você já pode voltar a editar!"
			}
		}

		payload := map[string]interface{}{
			"chat_id":    userID,
			"text":       thankMsg,
			"parse_mode": "HTML",
		}
		bodyData, _ := json.Marshal(payload)
		req, _ := http.NewRequest("POST", fmt.Sprintf("https://api.telegram.org/bot%s/sendMessage", telegramToken), bytes.NewBuffer(bodyData))
		req.Header.Set("Content-Type", "application/json")
		resp, errResp := telegramHTTPClient.Do(req)
		if errResp == nil {
			resp.Body.Close()
		}

		return c.JSON(fiber.Map{"success": true})
	})

	// Endpoint para receber a imagem fundida do Mini App
	app.Post("/api/upload", func(c *fiber.Ctx) error {
		requestID := fmt.Sprintf("%d", time.Now().UnixNano())
		start := time.Now()

		var reqData struct {
			InitData   string `json:"init_data"`
			UserID     string `json:"user_id"`
			AsDocument string `json:"as_document"`
			ImageB64   string `json:"image_base64"`
		}

		if err := c.BodyParser(&reqData); err != nil {
			log.Printf("[upload:%s] JSON inválido: %v", requestID, err)
			return c.Status(400).JSON(fiber.Map{"error": "invalid JSON payload"})
		}

		log.Printf("[upload:%s] recebido user_id=%s as_document=%s image_base64_len=%d init_data_len=%d",
			requestID, reqData.UserID, reqData.AsDocument, len(reqData.ImageB64), len(reqData.InitData))

		if telegramToken == "" {
			log.Printf("[upload:%s] TELEGRAM_TOKEN não definido", requestID)
			return c.Status(500).JSON(fiber.Map{"error": "telegram token is not configured"})
		}

		if reqData.InitData == "" || !validateInitData(reqData.InitData, telegramToken) {
			log.Printf("[upload:%s] initData inválido ou ausente user_id=%s", requestID, reqData.UserID)
			return c.Status(401).JSON(fiber.Map{"error": "Unauthorized. Invalid initData signature."})
		}

		authenticatedUserID := userIDFromInitData(reqData.InitData)
		if authenticatedUserID == "" {
			log.Printf("[upload:%s] user_id ausente no initData", requestID)
			return c.Status(401).JSON(fiber.Map{"error": "Unauthorized. Invalid Telegram user."})
		}

		if reqData.UserID == "" {
			log.Printf("[upload:%s] user_id ausente", requestID)
			return c.Status(400).JSON(fiber.Map{"error": "user_id is required"})
		}
		if reqData.UserID != authenticatedUserID {
			log.Printf("[upload:%s] user_id divergente payload=%s init_data=%s", requestID, reqData.UserID, authenticatedUserID)
			return c.Status(401).JSON(fiber.Map{"error": "Unauthorized. User mismatch."})
		}

		if reqData.ImageB64 == "" {
			log.Printf("[upload:%s] imagem ausente user_id=%s", requestID, reqData.UserID)
			return c.Status(400).JSON(fiber.Map{"error": "image is required"})
		}

		db, err := sql.Open("sqlite3", "../data/user_images.db")
		if err != nil {
			log.Printf("[upload:%s] erro ao abrir db para cota user_id=%s: %v", requestID, reqData.UserID, err)
			return c.Status(500).JSON(fiber.Map{"error": "database error"})
		}
		quota := loadQuotaInfo(db, reqData.UserID)
		db.Close()
		if reqData.UserID != adminID && quotaBlocksUsage(quota) {
			log.Printf("[upload:%s] cota bloqueada user_id=%s used=%d threshold=%d", requestID, reqData.UserID, quota.ImagesSinceLastAd, quota.Threshold)
			return c.Status(429).JSON(fiber.Map{"error_key": "quota_reached"})
		}

		// Remover o prefixo 'data:image/jpeg;base64,' se existir
		b64data := reqData.ImageB64
		if idx := strings.Index(b64data, ","); idx != -1 {
			b64data = b64data[idx+1:]
		}

		imgBytes, err := base64.StdEncoding.DecodeString(b64data)
		if err != nil {
			log.Printf("[upload:%s] falha decode base64 user_id=%s: %v", requestID, reqData.UserID, err)
			return c.Status(400).JSON(fiber.Map{"error": "failed to decode base64 image"})
		}

		filename := "merged_image.jpg"
		log.Printf("[upload:%s] imagem decodificada user_id=%s bytes=%d", requestID, reqData.UserID, len(imgBytes))

		// Enviar para o usuário final
		if reqData.AsDocument == "true" {
			log.Printf("[upload:%s] enviando documento para user_id=%s", requestID, reqData.UserID)
			err = sendDocumentToTelegram(reqData.UserID, filename, bytes.NewReader(imgBytes), "")
		} else {
			log.Printf("[upload:%s] enviando foto para user_id=%s", requestID, reqData.UserID)
			err = sendPhotoToTelegram(reqData.UserID, filename, bytes.NewReader(imgBytes), "")
		}

		if err != nil {
			log.Printf("[upload:%s] erro ao enviar para o Telegram user_id=%s elapsed=%s: %v",
				requestID, reqData.UserID, time.Since(start), err)
			return c.Status(500).JSON(fiber.Map{"error": "failed to send to telegram"})
		}

		go logMiniAppUsage(reqData.UserID, "miniapp_usage")
		go incrementUserCredits(reqData.UserID)

		log.Printf("[upload:%s] concluído user_id=%s elapsed=%s", requestID, reqData.UserID, time.Since(start))
		return c.JSON(fiber.Map{"success": true})
	})
	// Endpoint para notificar primeiro acesso do Mini App
	app.Post("/api/notify_first_access", func(c *fiber.Ctx) error {
		var data struct {
			InitData string `json:"init_data"`
		}
		if err := c.BodyParser(&data); err != nil {
			return c.Status(400).JSON(fiber.Map{"error": "invalid json"})
		}
		if telegramToken == "" || data.InitData == "" || !validateInitData(data.InitData, telegramToken) {
			return c.Status(401).JSON(fiber.Map{"error": "Unauthorized"})
		}
		userID := userIDFromInitData(data.InitData)
		if userID == "" {
			return c.Status(401).JSON(fiber.Map{"error": "Unauthorized"})
		}
		go logMiniAppUsage(userID, "miniapp_first_access")
		return c.JSON(fiber.Map{"success": true})
	})

	// Endpoint de diagnóstico disponível somente ao administrador autenticado.
	app.Post("/api/diagnostics", func(c *fiber.Ctx) error {
		var reqData struct {
			InitData string `json:"init_data"`
		}
		if err := c.BodyParser(&reqData); err != nil || telegramToken == "" || !validateInitData(reqData.InitData, telegramToken) {
			return c.Status(401).JSON(fiber.Map{"error": "Unauthorized"})
		}
		userID := userIDFromInitData(reqData.InitData)
		if userID == "" || userID != adminID {
			return c.Status(403).JSON(fiber.Map{"error": "Forbidden"})
		}
		uptime := time.Since(startTime)

		// Formatar uptime de forma amigável (ex: "2h 45m 10s")
		days := int(uptime.Hours()) / 24
		hours := int(uptime.Hours()) % 24
		minutes := int(uptime.Minutes()) % 60
		seconds := int(uptime.Seconds()) % 60

		var uptimeStr string
		if days > 0 {
			uptimeStr = fmt.Sprintf("%dd %dh %dm %ds", days, hours, minutes, seconds)
		} else if hours > 0 {
			uptimeStr = fmt.Sprintf("%dh %dm %ds", hours, minutes, seconds)
		} else {
			uptimeStr = fmt.Sprintf("%dm %ds", minutes, seconds)
		}

		return c.JSON(fiber.Map{
			"status":        "healthy",
			"go_version":    runtime.Version(),
			"fiber_version": "v" + fiber.Version,
			"uptime":        uptimeStr,
			"os":            runtime.GOOS,
			"arch":          runtime.GOARCH,
			"goroutines":    runtime.NumGoroutine(),
		})
	})

	port := os.Getenv("PORT")
	if port == "" {
		port = "3000"
	}

	log.Printf("Servidor Go rodando na porta %s", port)
	app.Listen(":" + port)
}

// Função para fazer o POST Multipart para a API do Telegram
func sendPhotoToTelegram(chatID, filename string, fileData io.Reader, caption string) error {
	apiURL := fmt.Sprintf("https://api.telegram.org/bot%s/sendPhoto", telegramToken)
	start := time.Now()

	var b bytes.Buffer
	w := multipart.NewWriter(&b)

	// Add chat_id
	fw, err := w.CreateFormField("chat_id")
	if err != nil {
		return err
	}
	_, err = io.WriteString(fw, chatID)
	if err != nil {
		return err
	}

	// Add photo
	fw, err = w.CreateFormFile("photo", filename)
	if err != nil {
		return err
	}
	_, err = io.Copy(fw, fileData)
	if err != nil {
		return err
	}

	if caption != "" {
		fw, err = w.CreateFormField("caption")
		if err != nil {
			return err
		}
		if _, err = io.WriteString(fw, caption); err != nil {
			return err
		}

		fw, err = w.CreateFormField("parse_mode")
		if err != nil {
			return err
		}
		if _, err = io.WriteString(fw, "HTML"); err != nil {
			return err
		}
	}

	w.Close()

	req, err := http.NewRequest("POST", apiURL, &b)
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", w.FormDataContentType())

	res, err := telegramHTTPClient.Do(req)
	if err != nil {
		return fmt.Errorf("request sendPhoto failed after %s: %w", time.Since(start), err)
	}
	defer res.Body.Close()

	if res.StatusCode != 200 {
		var result map[string]interface{}
		json.NewDecoder(res.Body).Decode(&result)
		return fmt.Errorf("telegram sendPhoto status=%d after %s: %v", res.StatusCode, time.Since(start), result)
	}

	log.Printf("Telegram sendPhoto ok chat_id=%s elapsed=%s", chatID, time.Since(start))
	return nil
}

// Função para fazer o POST Multipart para a API do Telegram como Documento
func sendDocumentToTelegram(chatID, filename string, fileData io.Reader, caption string) error {
	apiURL := fmt.Sprintf("https://api.telegram.org/bot%s/sendDocument", telegramToken)
	start := time.Now()

	var b bytes.Buffer
	w := multipart.NewWriter(&b)

	// Add chat_id
	fw, err := w.CreateFormField("chat_id")
	if err != nil {
		return err
	}
	_, err = io.WriteString(fw, chatID)
	if err != nil {
		return err
	}

	// Add document
	fw, err = w.CreateFormFile("document", filename)
	if err != nil {
		return err
	}
	_, err = io.Copy(fw, fileData)
	if err != nil {
		return err
	}

	if caption != "" {
		fw, err = w.CreateFormField("caption")
		if err != nil {
			return err
		}
		if _, err = io.WriteString(fw, caption); err != nil {
			return err
		}

		fw, err = w.CreateFormField("parse_mode")
		if err != nil {
			return err
		}
		if _, err = io.WriteString(fw, "HTML"); err != nil {
			return err
		}
	}

	w.Close()

	req, err := http.NewRequest("POST", apiURL, &b)
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", w.FormDataContentType())

	res, err := telegramHTTPClient.Do(req)
	if err != nil {
		return fmt.Errorf("request sendDocument failed after %s: %w", time.Since(start), err)
	}
	defer res.Body.Close()

	if res.StatusCode != 200 {
		var result map[string]interface{}
		json.NewDecoder(res.Body).Decode(&result)
		return fmt.Errorf("telegram sendDocument status=%d after %s: %v", res.StatusCode, time.Since(start), result)
	}

	log.Printf("Telegram sendDocument ok chat_id=%s elapsed=%s", chatID, time.Since(start))
	return nil
}
