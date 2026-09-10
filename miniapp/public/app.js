// app.js

// Inicializa a API do Telegram
const tg = window.Telegram.WebApp;
tg.expand(); // Expande o app para tela cheia
tg.ready();

// Detecta o contexto: estamos dentro do Telegram ou fora (web)?
const isInsideTelegram = tg.initData && tg.initData.length > 0;
const isOutsideTelegram = !isInsideTelegram;

// Diagnósticos administrativos devem ser protegidos no servidor; o frontend
// não expõe nem confia em um identificador de administrador.

function logMiniappAction() {
    if (!isInsideTelegram) return;
    fetch('/api/log_miniapp_action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ init_data: initDataPayload })
    }).catch(err => console.error('[LOG]', err));
}

// Log abertura do miniapp
logMiniappAction();

// === LÓGICA DE ANÚNCIOS (ADSGRAM) ===
const urlParams = new URLSearchParams(window.location.search);
const isAdMode = urlParams.get('action') === 'watch_ad';

if (isAdMode) {
    document.getElementById('ad-screen').style.display = 'flex';
    document.getElementById('btn-close-ad').addEventListener('click', () => {
        tg.close();
    });

    document.getElementById('btn-watch-ad').addEventListener('click', () => {
        if (!window.Adsgram) {
            const adCopy = getAdCopy();
            let msg = (typeof texts !== "undefined" && texts.adErrSdk) ? texts.adErrSdk : "Ad SDK did not load. Please try again later.";
            tg.showAlert(msg);
            return;
        }

        const AdController = window.Adsgram.init({ blockId: "35780" });
        
        // Bloquear o botão enquanto carrega
        const btn = document.getElementById('btn-watch-ad');
        const originalText = btn.innerText;
        btn.innerText = (typeof texts !== "undefined" && texts.adLoading) ? texts.adLoading : "⏳ Loading...";
        btn.disabled = true;

        AdController.show().then((result) => {
            // Anúncio visto até o fim
            const watchType = urlParams.get('type') || 'quota';
            fetch('/api/reward_ad_watched', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ init_data: tg.initData, type: watchType })
            }).then(async (response) => {
                let data = {};
                try {
                    data = await response.json();
                } catch (e) {
                    data = {};
                }
                if (!response.ok || data.success !== true) {
                    throw new Error(data.message || `${response.status} ${response.statusText}`);
                }
                const adCopy = getAdCopy();
                let msg = adCopy.success || "🎉 Done! You can return to the bot.";
                tg.showAlert(msg);
                setTimeout(() => tg.close(), 1500);
            }).catch(() => {
                let msg = (typeof texts !== "undefined" && texts.adErrConfirm) ? texts.adErrConfirm : "Error confirming the view. Please try again.";
                tg.showAlert(msg);
                btn.innerText = originalText;
                btn.disabled = false;
            });
        }).catch((result) => {
            // Erro ou fechou antes da hora
            console.error("Ad error or closed early", result);
            const adCopy = getAdCopy();
            let msg = adCopy.incomplete || "Please watch the full ad to continue.";
            tg.showAlert(msg);
            btn.innerText = originalText;
            btn.disabled = false;
        });
    });
}


// Log cliques em botões
document.addEventListener('click', (e) => {
    if (e.target.closest('button')) {
        logMiniappAction();
    }
});


// Notifica o primeiro acesso ao Admin
if (isInsideTelegram && !localStorage.getItem('miniapp_first_access_notified')) {
    fetch('/api/notify_first_access', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ init_data: tg.initData })
    }).then(r => r.json()).then(res => {
        if (res.success) {
            localStorage.setItem('miniapp_first_access_notified', 'true');
        }
    }).catch(err => console.error('Erro na notificação de primeiro acesso:', err));
}

// Dicionário de Traduções
const TRANSLATIONS = {
    pt: {
        title: "Editor Visual",
        addImage: "➕ Imagem",
        reset: "Limpar",
        save: "Salvar e Enviar",
        loading: "Enviando para o Bot...",
        alertNoImage: "Adicione pelo menos uma imagem antes de salvar.",
        alertSuccess: "Imagem enviada com sucesso! Volte ao chat do bot para encontrá-la.",
        alertError: "Erro ao enviar: ",
        alertUnexpected: "Erro inesperado ao salvar a imagem.",
        popupBeta: "Bem-vindo ao editor visual do MergeImages! Esta modalidade de MiniApp do Telegram ainda está em desenvolvimento. Novas funções chegarão aos poucos.",
        btnCancel: "Cancelar",
        btnCrop: "Cortar",
        exportTitle: "Como deseja enviar?",
        exportDesc: "Calcularemos a melhor resolução baseada nas fotos originais.",
        exportPhoto: "🖼️ Como Foto (Rápido)",
        exportDoc: "📄 Como Arquivo (Sem Perda)",
        btnFront: "⬆️ Frente",
        btnBack: "⬇️ Trás",
        btnRotate: "🔄 90º",
        btnDelete: "🗑️ Apagar",
        btnUndo: "Desfazer",
        btnRedo: "Refazer",
        lblGrid: "Grade Magnética",
        lblRot: "Giro Magnético (º)",
        btnSettings: "⚙️ Configs",
        modalSettingsTitle: "Configurações",
        lblBgColor: "Cor do Fundo",
        lblGridColor: "Cor da Grade",
        btnDownload: "📥 Baixar Imagem", lblLang: "Idioma", alertLangUpdate: "Para atualizar o idioma do bot e do teclado, feche o miniapp e envie o comando /start no chat.", txtMadeIn: "Feito no 🇧🇷", txtVersion: "Versão: 0.1", adTitle: "Liberar Acesso", adDesc: "Assista a um vídeo rápido para liberar a criação de mais imagens gratuitamente!", adVoluntaryTitle: "Apoiar o Merge Images", adVoluntaryDesc: "Assista a um vídeo rápido para ajudar a manter o bot online e gratuito para todos.", btnWatchAd: "🎥 Assistir Vídeo", btnCloseAd: "Voltar", adErrSdk: "SDK de Anúncios não carregou. Tente novamente mais tarde.", adLoading: "⏳ Carregando...", adSuccess: "🎉 Limite restaurado com sucesso! Você já pode voltar a criar imagens.", adVoluntarySuccess: "🎉 Obrigado pelo apoio! Você ajudou a manter o Merge Images online e gratuito.", adErrConfirm: "Erro ao confirmar visualização. Tente novamente.", adErrIncomplete: "Você precisa assistir ao anúncio inteiro para continuar.", adVoluntaryIncomplete: "Assista ao anúncio inteiro para que o apoio seja contabilizado.", uploadQuotaReached: "Limite atingido. Assista a um anúncio para continuar."
    },
    en: {
        title: "Visual Editor",
        addImage: "➕ Image",
        reset: "Clear",
        save: "Save & Send",
        loading: "Sending to Bot...",
        alertNoImage: "Add at least one image before saving.",
        alertSuccess: "Image sent successfully! Return to the bot chat to find it.",
        alertError: "Error sending: ",
        alertUnexpected: "Unexpected error while saving the image.",
        popupBeta: "Welcome to the MergeImages visual editor! This Telegram MiniApp mode is still in development. New features will arrive gradually.",
        btnCancel: "Cancel",
        btnCrop: "Crop",
        exportTitle: "How to send?",
        exportDesc: "We will calculate the best resolution based on original photos.",
        exportPhoto: "🖼️ As Photo (Fast)",
        exportDoc: "📄 As File (Lossless)",
        btnFront: "⬆️ Front",
        btnBack: "⬇️ Back",
        btnRotate: "🔄 90º",
        btnDelete: "🗑️ Delete",
        btnUndo: "Undo",
        btnRedo: "Redo",
        lblGrid: "Magnetic Grid",
        lblRot: "Rotation Snap (º)",
        btnSettings: "⚙️ Settings",
        modalSettingsTitle: "Settings",
        lblBgColor: "Background Color",
        lblGridColor: "Grid Color",
        btnDownload: "📥 Download Image", lblLang: "Language", alertLangUpdate: "To update the bot and keyboard language, close the miniapp and send the /start command in the chat.", txtMadeIn: "Made in 🇧🇷", txtVersion: "Version: 0.1", adTitle: "Unlock Access", adDesc: "Watch a quick video to unlock more image creation for free!", adVoluntaryTitle: "Support Merge Images", adVoluntaryDesc: "Watch a quick video to help keep the bot online and free for everyone.", btnWatchAd: "🎥 Watch Video", btnCloseAd: "Back", adErrSdk: "Ad SDK did not load. Please try again later.", adLoading: "⏳ Loading...", adSuccess: "🎉 Access restored successfully! You can go back to creating images.", adVoluntarySuccess: "🎉 Thanks for your support! You helped keep Merge Images online and free.", adErrConfirm: "Error confirming the view. Please try again.", adErrIncomplete: "You need to watch the full ad to continue.", adVoluntaryIncomplete: "Watch the full ad so your support can be counted.", uploadQuotaReached: "Limit reached. Watch an ad to continue."
    },
    es: {
        title: "Editor Visual",
        addImage: "➕ Imagen",
        reset: "Limpiar",
        save: "Guardar y Enviar",
        loading: "Enviando al Bot...",
        alertNoImage: "Añade al menos una imagen antes de guardar.",
        alertSuccess: "¡Imagen enviada con éxito! Vuelve al chat del bot para encontrarla.",
        alertError: "Error al enviar: ",
        alertUnexpected: "Error inesperado al guardar la imagen.",
        promptOutsideTelegram: "Estás probando fuera de Telegram. Introduce tu Chat ID de Telegram (ej. 190618316) para recibir la foto en el bot:",
        popupBeta: "¡Bienvenido al editor visual de MergeImages! Esta modalidad de MiniApp de Telegram aún está en desarrollo. Nuevas funciones llegarán poco a poco.",
        btnCancel: "Cancelar",
        btnCrop: "Recortar",
        exportTitle: "¿Cómo desea enviar?",
        exportDesc: "Calcularemos la mejor resolución según las fotos originales.",
        exportPhoto: "🖼️ Como Foto (Rápido)",
        exportDoc: "📄 Como Archivo (Sin Pérdida)",
        btnFront: "⬆️ Frente",
        btnBack: "⬇️ Atrás",
        btnRotate: "🔄 90º",
        btnDelete: "🗑️ Borrar",
        btnUndo: "Deshacer",
        btnRedo: "Rehacer",
        lblGrid: "Cuadrícula Magnética",
        lblRot: "Giro Magnético (º)",
        btnSettings: "⚙️ Ajustes",
        modalSettingsTitle: "Ajustes",
        lblBgColor: "Color de Fondo",
        lblGridColor: "Color de Cuadrícula",
        btnDownload: "📥 Descargar Imagen", lblLang: "Idioma", alertLangUpdate: "Para actualizar el idioma del bot y del teclado, cierra la miniapp y envía el comando /start en el chat.", txtMadeIn: "Hecho en 🇧🇷", txtVersion: "Versión: 0.1", adTitle: "Liberar Acceso", adDesc: "¡Mira un video rápido para desbloquear la creación de más imágenes gratis!", adVoluntaryTitle: "Apoyar Merge Images", adVoluntaryDesc: "Mira un video rápido para ayudar a mantener el bot en línea y gratis para todos.", btnWatchAd: "🎥 Ver Video", btnCloseAd: "Volver", adErrSdk: "El SDK de anuncios no se cargó. Inténtalo de nuevo más tarde.", adLoading: "⏳ Cargando...", adSuccess: "🎉 ¡Acceso restaurado con éxito! Ya puedes volver a crear imágenes.", adVoluntarySuccess: "🎉 ¡Gracias por tu apoyo! Ayudaste a mantener Merge Images en línea y gratis.", adErrConfirm: "Error al confirmar la visualización. Inténtalo de nuevo.", adErrIncomplete: "Debes ver el anuncio completo para continuar.", adVoluntaryIncomplete: "Mira el anuncio completo para que tu apoyo sea contabilizado.", uploadQuotaReached: "Límite alcanzado. Mira un anuncio para continuar."
    },
    ru: {
        title: "Визуальный редактор",
        addImage: "➕ Изображение",
        reset: "Очистить",
        save: "Сохранить и отправить",
        loading: "Отправка боту...",
        alertNoImage: "Добавьте хотя бы одно изображение перед сохранением.",
        alertSuccess: "Изображение успешно отправлено! Вернитесь в чат бота, чтобы найти его.",
        alertError: "Ошибка при отправке: ",
        alertUnexpected: "Непредвиденная ошибка при сохранении изображения.",
        promptOutsideTelegram: "Вы тестируете вне Telegram. Введите ваш Telegram Chat ID (например, 190618316), чтобы получить фото:",
        popupBeta: "Добро пожаловать в визуальный редактор MergeImages! Этот режим Telegram MiniApp всё ещё находится в разработке. Новые функции будут появляться постепенно.",
        btnCancel: "Отмена",
        btnCrop: "Обрезать",
        exportTitle: "Как отправить?",
        exportDesc: "Мы рассчитаем лучшее разрешение на основе исходных фотографий.",
        exportPhoto: "🖼️ Как фото (быстро)",
        exportDoc: "📄 Как файл (без потерь)",
        btnFront: "⬆️ Вперед",
        btnBack: "⬇️ Назад",
        btnRotate: "🔄 90º",
        btnDelete: "🗑️ Удалить",
        btnUndo: "Отменить",
        btnRedo: "Повторить",
        lblGrid: "Магнитная сетка",
        lblRot: "Вращение (º)",
        btnSettings: "⚙️ Настройки",
        modalSettingsTitle: "Настройки",
        lblBgColor: "Цвет фона",
        lblGridColor: "Цвет сетки",
        btnDownload: "📥 Скачать", lblLang: "Язык", alertLangUpdate: "Чтобы обновить язык бота и клавиатуры, закройте мини-приложение и отправьте команду /start в чат.", txtMadeIn: "Сделано в 🇧🇷", txtVersion: "Версия: 0.1", adTitle: "Открыть доступ", adDesc: "Посмотрите короткое видео, чтобы бесплатно создавать больше изображений!", adVoluntaryTitle: "Поддержать Merge Images", adVoluntaryDesc: "Посмотрите короткое видео, чтобы помочь боту оставаться онлайн и бесплатным для всех.", btnWatchAd: "🎥 Смотреть видео", btnCloseAd: "Назад", adErrSdk: "SDK рекламы не загрузился. Попробуйте позже.", adLoading: "⏳ Загрузка...", adSuccess: "🎉 Доступ успешно восстановлен! Можно снова создавать изображения.", adVoluntarySuccess: "🎉 Спасибо за поддержку! Вы помогли Merge Images оставаться онлайн и бесплатным.", adErrConfirm: "Ошибка подтверждения просмотра. Попробуйте снова.", adErrIncomplete: "Нужно посмотреть объявление полностью, чтобы продолжить.", adVoluntaryIncomplete: "Посмотрите объявление полностью, чтобы поддержка была засчитана.", uploadQuotaReached: "Лимит достигнут. Посмотрите рекламу, чтобы продолжить."
    },
    ar: {
        title: "المحرر المرئي",
        addImage: "➕ صورة",
        reset: "مسح",
        save: "حفظ وإرسال",
        loading: "جاري الإرسال للبوت...",
        alertNoImage: "يرجى إضافة صورة واحدة على الأقل قبل الحفظ.",
        alertSuccess: "تم إرسال الصورة بنجاح! عُد إلى دردشة البوت للعثور عليها.",
        alertError: "خطأ في الإرسال: ",
        alertUnexpected: "حدث خطأ غير متوقع أثناء حفظ الصورة.",
        promptOutsideTelegram: "أنت تقوم بالاختبار خارج Telegram. أدخل معرف الدردشة الخاص بك (مثال: 190618316) لتلقي الصورة:",
        popupBeta: "مرحبًا بك في المحرر المرئي لـ MergeImages! لا يزال وضع تطبيق Telegram المصغر هذا قيد التطوير. ستصل الميزات الجديدة تدريجيًا.",
        btnCancel: "إلغاء",
        btnCrop: "قص",
        exportTitle: "كيف تريد الإرسال؟",
        exportDesc: "سنقوم بحساب أفضل دقة بناءً على الصور الأصلية.",
        exportPhoto: "🖼️ كصورة (سريع)",
        exportDoc: "📄 كملف (بدون فقدان)",
        btnFront: "⬆️ للأمام",
        btnBack: "⬇️ للخلف",
        btnRotate: "🔄 90º",
        btnDelete: "🗑️ حذف",
        btnUndo: "تراجع",
        btnRedo: "إعادة",
        lblGrid: "شبكة مغناطيسية",
        lblRot: "تدوير (º)",
        btnSettings: "⚙️ الإعدادات",
        modalSettingsTitle: "الإعدادات",
        lblBgColor: "لون الخلفية",
        lblGridColor: "لون الشبكة",
        btnDownload: "📥 تحميل", lblLang: "لغة", alertLangUpdate: "لتحديث لغة البوت ولوحة المفاتيح، أغلق التطبيق المصغر وأرسل الأمر /start في الدردشة.", txtMadeIn: "صنع في 🇧🇷", txtVersion: "الإصدار: 0.1", adTitle: "فتح الوصول", adDesc: "شاهد فيديو قصيرًا لفتح إمكانية إنشاء المزيد من الصور مجانًا!", adVoluntaryTitle: "دعم Merge Images", adVoluntaryDesc: "شاهد فيديو قصيرًا للمساعدة في إبقاء البوت متاحًا ومجانيًا للجميع.", btnWatchAd: "🎥 مشاهدة الفيديو", btnCloseAd: "رجوع", adErrSdk: "تعذر تحميل SDK الإعلانات. حاول مرة أخرى لاحقًا.", adLoading: "⏳ جارٍ التحميل...", adSuccess: "🎉 تمت استعادة الوصول بنجاح! يمكنك العودة إلى إنشاء الصور.", adVoluntarySuccess: "🎉 شكرًا لدعمك! لقد ساعدت في إبقاء Merge Images متاحًا ومجانيًا.", adErrConfirm: "حدث خطأ أثناء تأكيد المشاهدة. حاول مرة أخرى.", adErrIncomplete: "يجب مشاهدة الإعلان كاملًا للمتابعة.", adVoluntaryIncomplete: "شاهد الإعلان كاملًا حتى يتم احتساب دعمك.", uploadQuotaReached: "تم الوصول إلى الحد. شاهد إعلانًا للمتابعة."
    },
    fr: {
        title: "Éditeur Visuel",
        addImage: "➕ Image",
        reset: "Effacer",
        save: "Enregistrer & Envoyer",
        loading: "Envoi au Bot...",
        alertNoImage: "Ajoutez au moins une image avant d'enregistrer.",
        alertSuccess: "Image envoyée avec succès ! Retournez dans le chat du bot pour la retrouver.",
        alertError: "Erreur d'envoi: ",
        alertUnexpected: "Une erreur inattendue est survenue lors de l'enregistrement.",
        promptOutsideTelegram: "Vous testez en dehors de Telegram. Entrez votre Chat ID Telegram (ex: 190618316) pour recevoir la photo:",
        popupBeta: "Bienvenue dans l\'éditeur visuel de MergeImages ! Ce mode MiniApp Telegram est encore en développement. De nouvelles fonctionnalités arriveront progressivement.",
        btnCancel: "Annuler",
        btnCrop: "Recadrer",
        exportTitle: "Comment envoyer?",
        exportDesc: "Nous calculerons la meilleure résolution basée sur les photos originales.",
        exportPhoto: "🖼️ Comme Photo (Rapide)",
        exportDoc: "📄 Comme Fichier (Sans Perte)",
        btnFront: "⬆️ Avant",
        btnBack: "⬇️ Arrière",
        btnRotate: "🔄 90º",
        btnDelete: "🗑️ Supprimer",
        btnUndo: "Annuler",
        btnRedo: "Rétablir",
        lblGrid: "Grille Magnétique",
        lblRot: "Rotation (º)",
        btnSettings: "⚙️ Paramètres",
        modalSettingsTitle: "Paramètres",
        lblBgColor: "Couleur de Fond",
        lblGridColor: "Couleur de la Grille",
        btnDownload: "📥 Télécharger", lblLang: "Langue", alertLangUpdate: "Pour mettre à jour la langue du bot et du clavier, fermez la miniapp et envoyez la commande /start dans le chat.", txtMadeIn: "Fait au 🇧🇷", txtVersion: "Version: 0.1", adTitle: "Débloquer l'accès", adDesc: "Regardez une courte vidéo pour créer plus d'images gratuitement !", adVoluntaryTitle: "Soutenir Merge Images", adVoluntaryDesc: "Regardez une courte vidéo pour aider à garder le bot en ligne et gratuit pour tous.", btnWatchAd: "🎥 Regarder la vidéo", btnCloseAd: "Retour", adErrSdk: "Le SDK publicitaire n'a pas été chargé. Réessayez plus tard.", adLoading: "⏳ Chargement...", adSuccess: "🎉 Accès restauré avec succès ! Vous pouvez recommencer à créer des images.", adVoluntarySuccess: "🎉 Merci pour votre soutien ! Vous aidez Merge Images à rester en ligne et gratuit.", adErrConfirm: "Erreur lors de la confirmation du visionnage. Réessayez.", adErrIncomplete: "Vous devez regarder toute l'annonce pour continuer.", adVoluntaryIncomplete: "Regardez toute l'annonce pour que votre soutien soit comptabilisé.", uploadQuotaReached: "Limite atteinte. Regardez une annonce pour continuer."
    },
    it: {
        title: "Editor Visuale",
        addImage: "➕ Immagine",
        reset: "Cancella",
        save: "Salva e Invia",
        loading: "Invio al Bot...",
        alertNoImage: "Aggiungi almeno un'immagine prima di salvare.",
        alertSuccess: "Immagine inviata con successo! Torna nella chat del bot per trovarla.",
        alertError: "Errore durante l'invio: ",
        alertUnexpected: "Errore imprevisto durante il salvataggio dell'immagine.",
        promptOutsideTelegram: "Stai testando fuori da Telegram. Inserisci il tuo Chat ID Telegram (es: 190618316) per ricevere la foto:",
        popupBeta: "Benvenuto nell\'editor visuale di MergeImages! Questa modalità MiniApp di Telegram è ancora in fase di sviluppo. Nuove funzionalità arriveranno gradualmente.",
        btnCancel: "Annulla",
        btnCrop: "Ritaglia",
        exportTitle: "Come inviare?",
        exportDesc: "Calcoleremo la migliore risoluzione basata sulle foto originali.",
        exportPhoto: "🖼️ Come Foto (Veloce)",
        exportDoc: "📄 Come File (Senza Perdita)",
        btnFront: "⬆️ Avanti",
        btnBack: "⬇️ Indietro",
        btnRotate: "🔄 90º",
        btnDelete: "🗑️ Elimina",
        btnUndo: "Annulla",
        btnRedo: "Ripristina",
        lblGrid: "Griglia Magnetica",
        lblRot: "Rotazione (º)",
        btnSettings: "⚙️ Impostazioni",
        modalSettingsTitle: "Impostazioni",
        lblBgColor: "Colore di Sfondo",
        lblGridColor: "Colore Griglia",
        btnDownload: "📥 Scarica Immagine", lblLang: "Lingua", alertLangUpdate: "Per aggiornare la lingua del bot e della tastiera, chiudi la miniapp e invia il comando /start nella chat.", txtMadeIn: "Fatto in 🇧🇷", txtVersion: "Versione: 0.1", adTitle: "Sblocca Accesso", adDesc: "Guarda un breve video per sbloccare gratuitamente la creazione di altre immagini!", adVoluntaryTitle: "Supporta Merge Images", adVoluntaryDesc: "Guarda un breve video per aiutare a mantenere il bot online e gratuito per tutti.", btnWatchAd: "🎥 Guarda Video", btnCloseAd: "Indietro", adErrSdk: "SDK annunci non caricato. Riprova più tardi.", adLoading: "⏳ Caricamento...", adSuccess: "🎉 Accesso ripristinato con successo! Puoi tornare a creare immagini.", adVoluntarySuccess: "🎉 Grazie per il supporto! Hai aiutato Merge Images a restare online e gratuito.", adErrConfirm: "Errore durante la conferma della visualizzazione. Riprova.", adErrIncomplete: "Devi guardare tutto l'annuncio per continuare.", adVoluntaryIncomplete: "Guarda tutto l'annuncio affinché il supporto venga conteggiato.", uploadQuotaReached: "Limite raggiunto. Guarda un annuncio per continuare."
    }
};

const SUPPORTED_LANGS = Object.keys(TRANSLATIONS);

function normalizeLanguage(lang) {
    if (!lang) return null;
    const baseLang = String(lang).toLowerCase().split('-')[0];
    if (baseLang === 'hi') return 'en';
    return SUPPORTED_LANGS.includes(baseLang) ? baseLang : null;
}

// Detecta o idioma do usuário
function getLanguage() {
    const urlParams = new URLSearchParams(window.location.search);
    const urlLang = normalizeLanguage(urlParams.get('lang'));

    if (isInsideTelegram) {
        // === DENTRO DO TELEGRAM ===
        // NUNCA usa localStorage aqui - sempre busca do banco de dados do bot
        // O usuário terá a escolha feita no bot tradicional
        if (false) console.log("[LANG] Inside Telegram - will fetch from bot database");

        // Permite abrir o Mini App com ?lang=ru quando o botão/link do bot já
        // passar explicitamente o idioma. O banco continua sendo sincronizado depois.
        if (urlLang) {
            if (false) console.log(`[LANG] Using language from URL parameter: ${urlLang}`);
            return urlLang;
        }
        
        // Temos que retornar um idioma padrão aqui e sincronizar depois
        // Retorna baseado no idioma do Telegram do usuário
        if (tg.initDataUnsafe && tg.initDataUnsafe.user && tg.initDataUnsafe.user.language_code) {
            const telegramLang = normalizeLanguage(tg.initDataUnsafe.user.language_code);
            if (telegramLang) {
                if (false) console.log(`[LANG] Using Telegram user language: ${telegramLang}`);
                return telegramLang;
            }
        }
        if (false) console.log("[LANG] Falling back to English (en)");
        return 'en';
    } else {
        // === FORA DO TELEGRAM (WEB) ===
        // Usa apenas localStorage - sem sincronização com bot
        if (false) console.log("[LANG] Outside Telegram (Web) - using localStorage only");
        
        // Prioridade 1: Escolha prévia do usuário no localStorage
        const savedLang = normalizeLanguage(localStorage.getItem('miniapp_lang'));
        if (savedLang) {
            if (false) console.log(`[LANG] Using saved language from localStorage: ${savedLang}`);
            return savedLang;
        }

        // Prioridade 2: Parâmetro de URL
        if (urlLang) {
            if (false) console.log(`[LANG] Using language from URL parameter: ${urlLang}`);
            localStorage.setItem('miniapp_lang', urlLang);
            return urlLang;
        }

        // Prioridade 3: Idioma do navegador
        const browserLang = normalizeLanguage(navigator.language || (navigator.languages && navigator.languages[0]));
        if (browserLang) {
            if (false) console.log(`[LANG] Using browser language: ${browserLang}`);
            return browserLang;
        }

        // Fallback: Inglês
        if (false) console.log("[LANG] Using default language: en");
        return 'en';
    }
}

let userLang = getLanguage();
let texts = TRANSLATIONS[userLang] || TRANSLATIONS['en'];
const adType = urlParams.get('type') === 'voluntary' ? 'voluntary' : 'quota';

function getAdCopy() {
    const t = texts || TRANSLATIONS['en'];
    if (adType === 'voluntary') {
        return {
            title: t.adVoluntaryTitle || t.adTitle,
            desc: t.adVoluntaryDesc || t.adDesc,
            success: t.adVoluntarySuccess || t.adSuccess,
            incomplete: t.adVoluntaryIncomplete || t.adErrIncomplete
        };
    }
    return {
        title: t.adTitle,
        desc: t.adDesc,
        success: t.adSuccess,
        incomplete: t.adErrIncomplete
    };
}

if (false) console.log(`[LANG] Initial language loaded: ${userLang}`);

// Setup Lang Selector
if (document.getElementById('lang-selector')) {
    document.getElementById('lang-selector').value = userLang;
    document.getElementById('lang-selector').addEventListener('change', (e) => {
        const newLang = e.target.value;
        
        if (isInsideTelegram) {
            // === DENTRO DO TELEGRAM ===
            // Salva no banco de dados do bot (sincroniza com bot tradicional)
            if (false) console.log(`[LANG] User changed language from "${userLang}" to "${newLang}" (inside Telegram)`);
            
            // Primeiro, atualiza a interface
            localStorage.setItem('miniapp_lang', newLang);
            if (false) console.log(`[LANG] Sending language change to bot backend...`);
            
            // Envia para o backend sincronizar com o bot tradicional
            fetch('/api/update_user_language', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    init_data: tg.initData,
                    language: newLang
                })
            })
            .then(r => {
                if (!r.ok) {
                    console.error(`[LANG] Server returned HTTP ${r.status}`);
                }
                return r.json();
            })
            .then(res => {
                if (res.success) {
                    if (false) console.log(`[LANG] ✓ Language successfully saved to bot database: ${newLang}`);
                    applyTranslations(newLang);
                    if (isInsideTelegram && tg.showPopup) {
                        tg.showPopup({
                            title: 'MergeImages',
                            message: texts.alertLangUpdate,
                            buttons: [{ type: 'ok' }]
                        }, function() {
                            window.location.reload();
                        });
                    } else {
                        alert(texts.alertLangUpdate);
                        window.location.reload();
                    }
                }
            })
            .catch(err => {
                console.error("[LANG] ✗ Error syncing language with bot:", err);
                tg.showAlert("Erro de conexão ao salvar idioma: " + err.message);
            });
        } else {
            // === FORA DO TELEGRAM (WEB) ===
            // Salva apenas no localStorage
            if (false) console.log(`[LANG] User changed language from "${userLang}" to "${newLang}" (web access)`);
            localStorage.setItem('miniapp_lang', newLang);
            if (false) console.log(`[LANG] ✓ Language saved to localStorage. Reloading page...`);
            window.location.reload();
        }
    });
}

function applyTranslations(lang) {
    userLang = lang;
    texts = TRANSLATIONS[userLang] || TRANSLATIONS['en'];

    if (false) console.log(`[LANG] ✓ Applying translations for language: ${lang}`);

    if (document.getElementById('lang-selector')) {
        document.getElementById('lang-selector').value = userLang;
    }

    // Aplica as traduções nos elementos HTML
    document.getElementById('txt-title').innerText = texts.title;
    document.getElementById('txt-add-image').innerText = texts.addImage;
    document.getElementById('btn-reset').innerText = texts.reset;
    document.getElementById('btn-save').innerText = isOutsideTelegram ? texts.btnDownload : texts.save;
    document.getElementById('txt-loading').innerText = texts.loading;
    document.getElementById('btn-crop-cancel').innerText = texts.btnCancel;
    document.getElementById('btn-crop-confirm').innerText = texts.btnCrop;
    if (document.getElementById('btn-upload-cancel')) { document.getElementById('btn-upload-cancel').innerText = texts.btnCancel; }

    document.getElementById('btn-front').innerText = texts.btnFront;
    document.getElementById('btn-back').innerText = texts.btnBack;
    document.getElementById('btn-rotate').innerText = texts.btnRotate;
    document.getElementById('btn-delete').innerText = texts.btnDelete;
    document.getElementById('btn-undo').title = texts.btnUndo;
    document.getElementById('btn-redo').title = texts.btnRedo;
    document.getElementById('btn-settings').innerText = texts.btnSettings;
    document.getElementById('txt-settings-title').innerText = texts.modalSettingsTitle;
    document.getElementById('txt-bg-color').innerText = texts.lblBgColor;
    document.getElementById('txt-grid-color').innerText = texts.lblGridColor;
    document.getElementById('txt-grid').innerText = texts.lblGrid;
    document.getElementById('txt-rot').innerText = texts.lblRot;
    if (document.getElementById('txt-lang')) { document.getElementById('txt-lang').innerText = texts.lblLang; }
    if (document.getElementById('txt-made-in')) { document.getElementById('txt-made-in').innerText = texts.txtMadeIn; }
    if (document.getElementById('txt-version')) { document.getElementById('txt-version').innerText = texts.txtVersion; }
    
    const adCopy = getAdCopy();
    if (document.getElementById('txt-ad-title')) { document.getElementById('txt-ad-title').innerText = adCopy.title || "Unlock Access"; }
    if (document.getElementById('txt-ad-desc')) { document.getElementById('txt-ad-desc').innerText = adCopy.desc || "Watch a quick video to continue."; }
    if (document.getElementById('btn-watch-ad')) { 
        if (document.getElementById('btn-watch-ad').innerText !== texts.adLoading) {
            document.getElementById('btn-watch-ad').innerText = texts.btnWatchAd || "🎥 Watch Video";
        }
    }
    if (document.getElementById('btn-close-ad')) { document.getElementById('btn-close-ad').innerText = texts.btnCloseAd || "Back"; }

    if (texts.exportTitle) {
        document.getElementById('txt-export-title').innerText = texts.exportTitle;
        document.getElementById('txt-export-desc').innerText = texts.exportDesc;
        document.getElementById('btn-export-photo').innerText = texts.exportPhoto;
        document.getElementById('btn-export-doc').innerText = texts.exportDoc;
    }
}

// Aplica o idioma inicial imediatamente
applyTranslations(userLang);

// === SINCRONIZAÇÃO DE IDIOMA COM O BOT ===
// Apenas dentro do Telegram: busca o idioma salvo no bot tradicional
if (isInsideTelegram && tg.initData) {
    if (false) console.log("[LANG] Inside Telegram - Fetching language from bot database...");
    fetch('/api/user_language', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ init_data: tg.initData })
    })
    .then(r => {
        if (!r.ok) {
            throw new Error('failed to fetch user language: status ' + r.status);
        }
        return r.json();
    })
    .then(res => {
        if (false) console.log("[LANG] Bot database language result:", res);
        const dbLang = normalizeLanguage(res.language);
        if (dbLang && dbLang !== userLang) {
            if (false) console.log(`[LANG] ✓ Switching from "${userLang}" to bot-defined language: "${dbLang}"`);
            localStorage.setItem('miniapp_lang', dbLang);
            applyTranslations(dbLang);
            userLang = dbLang;
        } else if (dbLang === userLang) {
            if (false) console.log(`[LANG] Bot language matches current (${userLang})`);
        }
    })
    .catch(err => {
        console.error("[LANG] ✗ Error fetching language from bot backend:", err);
    });
} else if (!isInsideTelegram) {
    if (false) console.log("[LANG] Outside Telegram (Web) - No bot database sync");
}


const loadingDetailMessages = {
    pt: [
        'Preparando a imagem final...',
        'Enviando para o bot. Isso pode levar alguns segundos.',
        'Aguardando confirmação do Telegram...',
        'Quase pronto...'
    ],
    en: [
        'Preparing the final image...',
        'Sending to the bot. This may take a few seconds.',
        'Waiting for Telegram confirmation...',
        'Almost done...'
    ],
    es: [
        'Preparando la imagen final...',
        'Enviando al bot. Esto puede tardar unos segundos.',
        'Esperando confirmación de Telegram...',
        'Casi listo...'
    ],
    ru: [
        'Подготовка итогового изображения...',
        'Отправка боту. Это может занять несколько секунд.',
        'Ожидание подтверждения Telegram...',
        'Почти готово...'
    ],
    ar: [
        'جار تجهيز الصورة النهائية...',
        'جار الإرسال إلى البوت. قد يستغرق ذلك بضع ثوان.',
        'بانتظار تأكيد Telegram...',
        'اكتمل الأمر تقريبًا...'
    ],
    fr: [
        'Preparation de l image finale...',
        'Envoi au bot. Cela peut prendre quelques secondes.',
        'Attente de la confirmation Telegram...',
        'Presque termine...'
    ],
    it: [
        'Preparazione dell immagine finale...',
        'Invio al bot. Potrebbe richiedere alcuni secondi.',
        'In attesa della conferma di Telegram...',
        'Quasi pronto...'
    ]
};

let loadingProgressTimer = null;
let loadingProgress = 0;
let currentUploadController = null;
let currentUploadTimeout = null;
let uploadCancelRequested = false;

function setLoadingProgress(value, detailText) {
    loadingProgress = Math.max(0, Math.min(value, 100));
    const progressBar = document.getElementById('loading-progress-bar');
    const detail = document.getElementById('txt-loading-detail');
    if (progressBar) progressBar.style.width = `${loadingProgress}%`;
    if (detail && detailText) detail.innerText = detailText;
}

function showLoading(detailText) {
    const messages = loadingDetailMessages[userLang] || loadingDetailMessages.en;
    document.getElementById('loading').classList.remove('hidden');
    const cancelBtn = document.getElementById('btn-upload-cancel');
    if (cancelBtn) cancelBtn.style.display = 'none';
    setLoadingProgress(8, detailText || messages[0]);

    if (loadingProgressTimer) clearInterval(loadingProgressTimer);
    loadingProgressTimer = setInterval(() => {
        const nextProgress = loadingProgress < 70 ? loadingProgress + 7 : loadingProgress + 2;
        const msgIndex = loadingProgress < 32 ? 1 : (loadingProgress < 72 ? 2 : 3);
        setLoadingProgress(Math.min(nextProgress, 92), messages[msgIndex]);
    }, 1800);
}

function hideLoading() {
    if (loadingProgressTimer) {
        clearInterval(loadingProgressTimer);
        loadingProgressTimer = null;
    }
    const cancelBtn = document.getElementById('btn-upload-cancel');
    if (cancelBtn) cancelBtn.style.display = 'none';
    setLoadingProgress(100);
    setTimeout(() => {
        document.getElementById('loading').classList.add('hidden');
        setLoadingProgress(0);
    }, 250);
}

function cancelCurrentUpload() {
    uploadCancelRequested = true;
    if (currentUploadTimeout) {
        clearTimeout(currentUploadTimeout);
        currentUploadTimeout = null;
    }
    if (currentUploadController) {
        currentUploadController.abort();
    }
}

document.getElementById('btn-upload-cancel').addEventListener('click', cancelCurrentUpload);

// === POPUP DE SELEÇÃO DE IDIOMA (APENAS FORA DO TELEGRAM) ===
// Exibe o modal de escolha de idioma APENAS para acesso via web (fora do Telegram)
if (!isInsideTelegram && !localStorage.getItem('miniapp_lang_popup_shown')) {
    if (false) console.log("[POPUP] Showing language selection popup (web access)");
    
    setTimeout(() => {
        const langModal = document.getElementById('first-access-lang-modal');
        if (langModal) {
            langModal.style.display = 'flex';
            
            // Adiciona listeners aos botões de escolha de idioma
            document.querySelectorAll('.lang-choice-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    const selectedLang = btn.getAttribute('data-lang');
                    if (false) console.log(`[POPUP] User selected language: ${selectedLang}`);
                    
                    localStorage.setItem('miniapp_lang', selectedLang);
                    applyTranslations(selectedLang);
                    userLang = selectedLang;
                    
                    // Fecha o modal de idioma
                    langModal.style.display = 'none';
                    
                    // Exibe a mensagem de boas-vindas no idioma selecionado
                    setTimeout(() => {
                        if (false) console.log(`[POPUP] ✓ Showing welcome message in ${selectedLang}`);
                        try {
                            alert(texts.popupBeta);
                        } catch(e) {
                            alert(texts.popupBeta);
                        }
                        localStorage.setItem('miniapp_lang_popup_shown', 'true');
                    }, 400);
                });
            });
        } else {
            if (false) console.log("[POPUP] Language modal element not found (fallback)");
            // Fallback se o modal não existir
            alert(texts.popupBeta);
            localStorage.setItem('miniapp_lang_popup_shown', 'true');
        }
    }, 600);
} else if (isInsideTelegram) {
    if (false) console.log("[POPUP] Inside Telegram - Skipping language selection popup (using bot settings)");
} else {
    if (false) console.log("[POPUP] Popup already shown before");
}

// Configurações do Canvas
const wrapper = document.querySelector('.canvas-container-wrapper');
const canvas = new fabric.Canvas('canvas', {
    width: wrapper.clientWidth,
    height: wrapper.clientHeight,
    backgroundColor: '#ffffff'
});

function updateDeskOriginCross() {
    const crossH = document.getElementById('cross-h');
    const crossV = document.getElementById('cross-v');
    if (!crossH || !crossV) return;

    const viewport = canvas.viewportTransform || [1, 0, 0, 1, 0, 0];
    const origin = new fabric.Point(canvas.getWidth() / 2, canvas.getHeight() / 2);
    const screenPoint = fabric.util.transformPoint(origin, viewport);

    crossH.style.transform = `translateY(${screenPoint.y}px)`;
    crossV.style.transform = `translateX(${screenPoint.x}px)`;
}

// Lida com o redimensionamento da janela
window.addEventListener('resize', () => {
    canvas.setWidth(wrapper.clientWidth);
    canvas.setHeight(wrapper.clientHeight);
    canvas.renderAll();
    updateDeskOriginCross();
});

let currentBgColor = '#ffffff';

function saveSettings() {
    const settings = {
        bgColor: document.getElementById('bg-color').value,
        gridColor: document.getElementById('grid-color').value,
        snapGrid: document.getElementById('snap-grid-chk').checked,
        gridSize: document.getElementById('grid-size').value,
        rotSnap: document.getElementById('rot-snap').value
    };
    const settingsStr = JSON.stringify(settings);
    localStorage.setItem('miniapp_editor_settings', settingsStr);
    if (isInsideTelegram && tg.CloudStorage) {
        tg.CloudStorage.setItem('miniapp_editor_settings', settingsStr);
    }
}

function applyLoadedSettings(saved) {
    if (!saved) return;
    try {
        const settings = JSON.parse(saved);
        if (settings.bgColor) {
            document.getElementById('bg-color').value = settings.bgColor;
            currentBgColor = settings.bgColor;
        }
        if (settings.gridColor) document.getElementById('grid-color').value = settings.gridColor;
        if (settings.snapGrid !== undefined) document.getElementById('snap-grid-chk').checked = settings.snapGrid;
        if (settings.gridSize) document.getElementById('grid-size').value = settings.gridSize;
        if (settings.rotSnap) document.getElementById('rot-snap').value = settings.rotSnap;
        updateGridBackground();
    } catch (e) {
        console.error('Error loading settings', e);
    }
}

function loadSettings() {
    if (isInsideTelegram && tg.CloudStorage) {
        tg.CloudStorage.getItem('miniapp_editor_settings', function(err, val) {
            if (!err && val) {
                applyLoadedSettings(val);
            } else {
                applyLoadedSettings(localStorage.getItem('miniapp_editor_settings'));
            }
        });
    } else {
        applyLoadedSettings(localStorage.getItem('miniapp_editor_settings'));
    }
}
loadSettings();

document.getElementById('bg-color').addEventListener('input', (e) => {
    currentBgColor = e.target.value;
    updateGridBackground();
});

function updateGridBackground() {
    const isGridEnabled = document.getElementById('snap-grid-chk').checked;
    const gridSize = parseInt(document.getElementById('grid-size').value, 10);
    const gridColor = document.getElementById('grid-color').value;
    const gridColorWithAlpha = gridColor + '33'; // ~20% opacidade
    
    // Cor mais escura para a cruz central (50% mais escuro)
    let r = parseInt(gridColor.substring(1, 3), 16);
    let g = parseInt(gridColor.substring(3, 5), 16);
    let b = parseInt(gridColor.substring(5, 7), 16);
    r = Math.floor(r * 0.5);
    g = Math.floor(g * 0.5);
    b = Math.floor(b * 0.5);
    const darkerColor = `#${(1 << 24 | r << 16 | g << 8 | b).toString(16).slice(1)}`;
    
    // Atualiza a cor das divs da cruz
    if (document.getElementById('cross-h')) {
        document.getElementById('cross-h').style.backgroundColor = darkerColor;
        document.getElementById('cross-v').style.backgroundColor = darkerColor;
    }

    const wrapper = document.querySelector('.canvas-container-wrapper');
    
    let bgImage = '';
    let bgSize = '';
    let bgPos = '';
    let bgRep = '';
    
    if (isGridEnabled && gridSize > 0) {
        bgImage = `linear-gradient(to right, ${gridColorWithAlpha} 1px, transparent 1px), linear-gradient(to bottom, ${gridColorWithAlpha} 1px, transparent 1px)`;
        bgSize = `${gridSize}px ${gridSize}px, ${gridSize}px ${gridSize}px`;
        bgPos = `0 0, 0 0`;
        bgRep = `repeat, repeat`;
    }
    
    wrapper.style.backgroundImage = bgImage;
    wrapper.style.backgroundSize = bgSize;
    wrapper.style.backgroundPosition = bgPos;
    wrapper.style.backgroundRepeat = bgRep;
    wrapper.style.backgroundColor = currentBgColor;
    canvas.backgroundColor = 'transparent';
    canvas.renderAll();
    updateDeskOriginCross();
    
    saveSettings();
}

document.getElementById('snap-grid-chk').addEventListener('change', updateGridBackground);
document.getElementById('grid-size').addEventListener('input', updateGridBackground);
document.getElementById('grid-color').addEventListener('input', updateGridBackground);
document.getElementById('rot-snap').addEventListener('input', saveSettings);
updateGridBackground();

const SNAP_DISTANCE = 20;

canvas.on('object:moving', function(options) {
    const obj = options.target;
    
    const isGridEnabled = document.getElementById('snap-grid-chk').checked;
    const gridSize = parseInt(document.getElementById('grid-size').value, 10);

    if (isGridEnabled && gridSize > 0) {
        // Alinha a borda superior-esquerda à grade
        const objW = obj.getScaledWidth();
        const objH = obj.getScaledHeight();
        
        const edgeLeft = obj.left - objW / 2;
        const edgeTop = obj.top - objH / 2;
        
        const snappedEdgeLeft = Math.round(edgeLeft / gridSize) * gridSize;
        const snappedEdgeTop = Math.round(edgeTop / gridSize) * gridSize;
        
        obj.set({
            left: snappedEdgeLeft + objW / 2,
            top: snappedEdgeTop + objH / 2
        });
        return; // Pula o snap magnético com outras imagens
    }
    
    // Snap magnético (Ímã)
    const objW = obj.getScaledWidth();
    const objH = obj.getScaledHeight();
    const objLeft = obj.left - objW / 2;
    const objRight = obj.left + objW / 2;
    const objTop = obj.top - objH / 2;
    const objBottom = obj.top + objH / 2;

    // Snap para os eixos centrais da tela
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    if (Math.abs(obj.left - centerX) < SNAP_DISTANCE) obj.set({ left: centerX });
    if (Math.abs(obj.top - centerY) < SNAP_DISTANCE) obj.set({ top: centerY });

    // Snap com outros objetos
    const objects = canvas.getObjects();
    for (let i = 0; i < objects.length; i++) {
        const target = objects[i];
        if (target === obj) continue;

        const targetW = target.getScaledWidth();
        const targetH = target.getScaledHeight();
        const targetLeft = target.left - targetW / 2;
        const targetRight = target.left + targetW / 2;
        const targetTop = target.top - targetH / 2;
        const targetBottom = target.top + targetH / 2;

        // Borda Direita com Borda Esquerda
        if (Math.abs(objRight - targetLeft) < SNAP_DISTANCE) {
            obj.set({ left: targetLeft - objW / 2 });
        }
        // Borda Esquerda com Borda Direita
        if (Math.abs(objLeft - targetRight) < SNAP_DISTANCE) {
            obj.set({ left: targetRight + objW / 2 });
        }
        // Base com Topo
        if (Math.abs(objBottom - targetTop) < SNAP_DISTANCE) {
            obj.set({ top: targetTop - objH / 2 });
        }
        // Topo com Base
        if (Math.abs(objTop - targetBottom) < SNAP_DISTANCE) {
            obj.set({ top: targetBottom + objH / 2 });
        }
        // Centros
        if (Math.abs(obj.left - target.left) < SNAP_DISTANCE) {
            obj.set({ left: target.left });
        }
        if (Math.abs(obj.top - target.top) < SNAP_DISTANCE) {
            obj.set({ top: target.top });
        }
    }
});

// Snap to grid ao redimensionar
canvas.on('object:scaling', function(options) {
    const isGridEnabled = document.getElementById('snap-grid-chk').checked;
    const gridSize = parseInt(document.getElementById('grid-size').value, 10);

    if (isGridEnabled && gridSize > 0) {
        const obj = options.target;
        
        const unscaledW = obj.width;
        const unscaledH = obj.height;
        
        let newW = obj.scaleX * unscaledW;
        let newH = obj.scaleY * unscaledH;
        
        newW = Math.round(newW / gridSize) * gridSize;
        newH = Math.round(newH / gridSize) * gridSize;
        
        if (newW < gridSize) newW = gridSize;
        if (newH < gridSize) newH = gridSize;
        
        obj.set({
            scaleX: newW / unscaledW,
            scaleY: newH / unscaledH
        });
    }
});

// Snap to grid ao rotacionar
canvas.on('object:rotating', function(options) {
    const snapAngle = parseInt(document.getElementById('rot-snap').value, 10);
    if (snapAngle > 0) {
        const obj = options.target;
        obj.set('angle', Math.round(obj.angle / snapAngle) * snapAngle);
    }
});

// Sistema de Histórico (Undo/Redo)
const history = [];
let historyIndex = -1;
let isHistoryAction = false;

function saveHistory() {
    if (isHistoryAction) return;
    const json = JSON.stringify(canvas.toJSON());
    if (historyIndex < history.length - 1) {
        history.splice(historyIndex + 1);
    }
    history.push(json);
    if (history.length > 11) { // 1 atual + 10 de histórico
        history.shift();
    }
    historyIndex = history.length - 1;
}

function updateElementCount() {
    const count = canvas.getObjects('image').length;
    const badge = document.getElementById('element-count');
    if (badge) {
        badge.innerText = `🖼️ ${count}`;
    }
}

canvas.on('object:added', () => {
    saveHistory();
    updateElementCount();
});
canvas.on('object:modified', () => {
    saveHistory();
    updateElementCount();
});
canvas.on('object:removed', () => {
    saveHistory();
    updateElementCount();
});

// Inicializa o contador na tela
setTimeout(updateElementCount, 150);

document.getElementById('btn-undo').addEventListener('click', () => {
    if (historyIndex > 0) {
        isHistoryAction = true;
        historyIndex--;
        canvas.loadFromJSON(history[historyIndex], function() {
            canvas.renderAll();
            isHistoryAction = false;
            updateElementCount();
        });
    }
});

document.getElementById('btn-redo').addEventListener('click', () => {
    if (historyIndex < history.length - 1) {
        isHistoryAction = true;
        historyIndex++;
        canvas.loadFromJSON(history[historyIndex], function() {
            canvas.renderAll();
            isHistoryAction = false;
            updateElementCount();
        });
    }
});

// Salva o estado inicial em branco
setTimeout(saveHistory, 100);

// Upload de Imagens do Celular para o Canvas
document.getElementById('upload-image').addEventListener('change', function(e) {
    const files = e.target.files;
    if (!files.length) return;

    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const reader = new FileReader();

        reader.onload = function(f) {
            const data = f.target.result;
            fabric.Image.fromURL(data, function(img) {
                // Escala a imagem se for muito grande
                const maxSize = Math.min(canvas.width, canvas.height) * 0.8;
                if (img.width > maxSize || img.height > maxSize) {
                    img.scaleToWidth(maxSize);
                }
                
                // Centraliza a imagem no canvas
                img.set({
                    left: canvas.width / 2,
                    top: canvas.height / 2,
                    originX: 'center',
                    originY: 'center',
                    cornerColor: tg.themeParams.button_color || '#2481cc',
                    borderColor: tg.themeParams.button_color || '#2481cc',
                    transparentCorners: false
                });

                canvas.add(img);
                canvas.setActiveObject(img);
            });
        };
        reader.readAsDataURL(file);
    }
    // Reseta o input para permitir carregar a mesma imagem novamente
    e.target.value = '';
});

// Controles de Objeto (Aparecem quando uma imagem é selecionada)
const objControls = document.getElementById('object-controls');

canvas.on('selection:created', () => objControls.classList.remove('hidden'));
canvas.on('selection:updated', () => objControls.classList.remove('hidden'));
canvas.on('selection:cleared', () => objControls.classList.add('hidden'));

document.getElementById('btn-front').addEventListener('click', () => {
    const obj = canvas.getActiveObject();
    if (obj) { obj.bringToFront(); canvas.renderAll(); }
});

document.getElementById('btn-back').addEventListener('click', () => {
    const obj = canvas.getActiveObject();
    if (obj) { obj.sendToBack(); canvas.renderAll(); }
});

document.getElementById('btn-rotate').addEventListener('click', () => {
    const obj = canvas.getActiveObject();
    if (obj) { 
        obj.rotate((obj.angle || 0) + 90); 
        canvas.renderAll(); 
    }
});

document.getElementById('btn-delete').addEventListener('click', () => {
    const obj = canvas.getActiveObject();
    if (obj) { 
        canvas.remove(obj); 
        canvas.discardActiveObject();
        objControls.classList.add('hidden');
    }
});

// Navegação (Zoom e Pan)
const MIN_ZOOM = 0.1;
const MAX_ZOOM = 20;

function clampZoom(zoom) {
    return Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, zoom));
}

function zoomCanvasToPoint(point, zoom) {
    canvas.zoomToPoint(point, clampZoom(zoom));
    canvas.requestRenderAll();
}

function zoomCanvasByFactor(factor) {
    zoomCanvasToPoint(
        { x: canvas.width / 2, y: canvas.height / 2 },
        canvas.getZoom() * factor
    );
}

document.getElementById('btn-recenter').addEventListener('click', () => {
    canvas.setViewportTransform([1, 0, 0, 1, 0, 0]);
    canvas.requestRenderAll();
});

document.getElementById('btn-zoom-in').addEventListener('click', () => {
    zoomCanvasByFactor(1.2);
});

document.getElementById('btn-zoom-out').addEventListener('click', () => {
    zoomCanvasByFactor(1 / 1.2);
});

canvas.on('mouse:wheel', function(opt) {
    const delta = opt.e.deltaY;
    let zoom = canvas.getZoom();
    zoom *= 0.999 ** delta;
    
    // Zoom centralizado no mouse
    zoomCanvasToPoint({ x: opt.e.offsetX, y: opt.e.offsetY }, zoom);
    opt.e.preventDefault();
    opt.e.stopPropagation();
});

canvas.fireMiddleClick = true;

let isTouchPanning = false;
let lastTouchX = 0;
let lastTouchY = 0;
let lastTouchDistance = 0;

function isTouchEvent(evt) {
    return !!(
        evt &&
        (
            evt.pointerType === 'touch' ||
            evt.type === 'touchstart' ||
            evt.type === 'touchmove' ||
            evt.type === 'touchend' ||
            evt.touches
        )
    );
}

function getTouchCenter(touches) {
    return {
        x: (touches[0].clientX + touches[1].clientX) / 2,
        y: (touches[0].clientY + touches[1].clientY) / 2
    };
}

function getTouchDistance(touches) {
    const dx = touches[0].clientX - touches[1].clientX;
    const dy = touches[0].clientY - touches[1].clientY;
    return Math.hypot(dx, dy);
}

canvas.upperCanvasEl.addEventListener('touchstart', (e) => {
    if (e.touches.length >= 2) {
        isTouchPanning = true;
        const center = getTouchCenter(e.touches);
        lastTouchX = center.x;
        lastTouchY = center.y;
        lastTouchDistance = getTouchDistance(e.touches);
        e.preventDefault();
        e.stopPropagation();
    }
}, { passive: false });

canvas.upperCanvasEl.addEventListener('touchmove', (e) => {
    if (isTouchPanning && e.touches.length >= 2) {
        const center = getTouchCenter(e.touches);
        const currentX = center.x;
        const currentY = center.y;
        const vpt = canvas.viewportTransform;
        vpt[4] += currentX - lastTouchX;
        vpt[5] += currentY - lastTouchY;

        const currentDistance = getTouchDistance(e.touches);
        if (lastTouchDistance > 0 && currentDistance > 0) {
            const zoomFactor = currentDistance / lastTouchDistance;
            const rect = canvas.upperCanvasEl.getBoundingClientRect();
            zoomCanvasToPoint(
                { x: currentX - rect.left, y: currentY - rect.top },
                canvas.getZoom() * zoomFactor
            );
        }

        canvas.requestRenderAll();
        lastTouchX = currentX;
        lastTouchY = currentY;
        lastTouchDistance = currentDistance;
        e.preventDefault();
        e.stopPropagation();
    }
}, { passive: false });

canvas.upperCanvasEl.addEventListener('touchend', (e) => {
    if (e.touches.length < 2) {
        isTouchPanning = false;
        lastTouchDistance = 0;
    }
});

canvas.on('mouse:down', function(opt) {
    const evt = opt.e;
    const touchGesture = isTouchEvent(evt);
    // Permite Panning se clicar com o botão do meio (1), usar Alt, ou clicar no fundo vazio do Canvas (Mobile e PC)
    // No mobile, o pan com um dedo é desativado para não deslocar a mesa sem querer.
    if (evt.button === 1 || evt.altKey || (!touchGesture && !opt.target)) {
        this.isDragging = true;
        this.selection = false;
        this.lastPosX = evt.clientX;
        this.lastPosY = evt.clientY;
    }
});

canvas.on('mouse:move', function(opt) {
    if (this.isDragging) {
        const e = opt.e;
        const clientX = e.clientX !== undefined ? e.clientX : (e.touches ? e.touches[0].clientX : 0);
        const clientY = e.clientY !== undefined ? e.clientY : (e.touches ? e.touches[0].clientY : 0);
        
        const vpt = this.viewportTransform;
        vpt[4] += clientX - this.lastPosX;
        vpt[5] += clientY - this.lastPosY;
        
        this.setViewportTransform(this.viewportTransform);
        this.requestRenderAll();
        
        this.lastPosX = clientX;
        this.lastPosY = clientY;
    }
});

canvas.on('mouse:up', function(opt) {
    this.isDragging = false;
    this.selection = true;
});

canvas.on('after:render', updateDeskOriginCross);
updateDeskOriginCross();

// Modal Configurações
document.getElementById('btn-settings').addEventListener('click', () => {
    document.getElementById('settings-modal').style.display = 'flex';
});
document.getElementById('btn-settings-close').addEventListener('click', () => {
    document.getElementById('settings-modal').style.display = 'none';
});

// Botão Limpar
document.getElementById('btn-reset').addEventListener('click', () => {
    canvas.clear();
    canvas.backgroundColor = currentBgColor;
    updateElementCount();
});

// Lógica de Crop Rápido (Duplo clique)
let cropper = null;
let cropTargetObj = null;

canvas.on('mousedblclick', function(options) {
    const obj = options.target;
    if (!obj || obj.type !== 'image') return;
    
    cropTargetObj = obj;
    const cropModal = document.getElementById('crop-modal');
    const cropImage = document.getElementById('crop-image');
    
    cropImage.src = obj.getSrc();
    cropModal.style.display = 'flex';
    
    // Inicia o Cropper após a imagem carregar
    cropImage.onload = () => {
        if (cropper) cropper.destroy();
        cropper = new Cropper(cropImage, {
            viewMode: 1,
            dragMode: 'crop',
            autoCropArea: 1,
            restore: false,
            guides: true,
            center: true,
            highlight: false,
            cropBoxMovable: true,
            cropBoxResizable: true,
            toggleDragModeOnDblclick: false,
        });
    };
});

document.getElementById('btn-crop-cancel').addEventListener('click', () => {
    document.getElementById('crop-modal').style.display = 'none';
    if (cropper) {
        cropper.destroy();
        cropper = null;
    }
});

document.getElementById('btn-crop-confirm').addEventListener('click', () => {
    if (!cropper || !cropTargetObj) return;
    
    const canvasCropped = cropper.getCroppedCanvas();
    const croppedDataUrl = canvasCropped.toDataURL('image/jpeg', 0.95);
    
    cropTargetObj.setSrc(croppedDataUrl, function() {
        canvas.renderAll();
        document.getElementById('crop-modal').style.display = 'none';
        cropper.destroy();
        cropper = null;
    });
});

async function performDownload() {
    showLoading();
    try {
        const dataUrl = await getCroppedCanvasDataURL();
        if (!dataUrl) return;
        setLoadingProgress(85);
        const a = document.createElement('a');
        a.href = dataUrl;
        a.download = 'merged_image.jpg';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    } catch(e) {
        alert(texts.alertUnexpected);
    } finally {
        hideLoading();
    }
}

// Extrai o conteúdo real do canvas (recorta o espaço branco em branco em volta das imagens)
function getCroppedCanvasDataURL() {
    return new Promise((resolve, reject) => {
        // Remove seleção antes de salvar
        canvas.discardActiveObject();
        canvas.renderAll();

        const objects = canvas.getObjects();
        if (objects.length === 0) {
            resolve(null);
            return;
        }

        // 1. Salva o estado atual do viewport, dimensões do canvas e cor de fundo
        const originalVpt = canvas.viewportTransform.slice(0);
        const originalWidth = canvas.width;
        const originalHeight = canvas.height;
        const originalBg = canvas.backgroundColor;

        // 2. Reseta o viewport transform temporariamente para calcular as coordenadas reais
        canvas.setViewportTransform([1, 0, 0, 1, 0, 0]);
        canvas.renderAll();

        // 3. Calcula o bounding box dos objetos sem restrição de 0 ou tamanho da tela
        let minX = Number.MAX_SAFE_INTEGER, minY = Number.MAX_SAFE_INTEGER;
        let maxX = Number.MIN_SAFE_INTEGER, maxY = Number.MIN_SAFE_INTEGER;
        
        objects.forEach(obj => {
            const bound = obj.getBoundingRect(true); // true ignora o viewport transform
            if (bound.left < minX) minX = bound.left;
            if (bound.top < minY) minY = bound.top;
            if (bound.left + bound.width > maxX) maxX = bound.left + bound.width;
            if (bound.top + bound.height > maxY) maxY = bound.top + bound.height;
        });

        // 4. Se o bounding box for inválido, restaura e sai
        if (minX >= maxX || minY >= maxY) {
            canvas.setViewportTransform(originalVpt);
            resolve(null);
            return;
        }

        const width = maxX - minX;
        const height = maxY - minY;

        // 5. Encontra o fator de escala dinâmico com base nas imagens originais
        let maxScale = 0;
        objects.forEach(obj => {
            if (obj.type === 'image') {
                const s = Math.max(obj.scaleX || 1, obj.scaleY || 1);
                if (s > maxScale) maxScale = s;
            }
        });
        if (maxScale === 0) maxScale = 1.0;
        
        let multiplier = 1.0 / maxScale;

        // Limitado a 4000 para evitar que o WebView falhe
        if (width * multiplier > 4000 || height * multiplier > 4000) {
            multiplier = 4000 / Math.max(width, height);
        }

        // 6. Translada temporariamente todos os objetos para que o canto superior esquerdo do bounding box fique em (0,0)
        objects.forEach(obj => {
            obj.left -= minX;
            obj.top -= minY;
            obj.setCoords(); // Atualiza as coordenadas internas do Fabric
        });

        // 7. Define o tamanho do canvas para o tamanho exato da área das imagens e define a cor de fundo
        canvas.setWidth(width);
        canvas.setHeight(height);
        canvas.backgroundColor = currentBgColor;
        canvas.renderAll();

        try {
            // 8. Gera a imagem final com o multiplicador de alta resolução
            const dataUrl = canvas.toDataURL({
                format: 'jpeg',
                quality: 0.95,
                multiplier: multiplier
            });

            // 9. Restaura tudo ao estado original
            objects.forEach(obj => {
                obj.left += minX;
                obj.top += minY;
                obj.setCoords();
            });

            canvas.setWidth(originalWidth);
            canvas.setHeight(originalHeight);
            canvas.backgroundColor = originalBg;
            canvas.setViewportTransform(originalVpt);
            canvas.renderAll();

            if (!dataUrl || dataUrl === 'data:,') {
                reject(new Error("Falha ao gerar DataURL da imagem (toDataURL retornou vazio)"));
                return;
            }

            resolve(dataUrl);
        } catch (err) {
            // Restaura mesmo em caso de erro
            objects.forEach(obj => {
                obj.left += minX;
                obj.top += minY;
                obj.setCoords();
            });
            canvas.setWidth(originalWidth);
            canvas.setHeight(originalHeight);
            canvas.backgroundColor = originalBg;
            canvas.setViewportTransform(originalVpt);
            canvas.renderAll();
            reject(err);
        }
    });
}

// Salvar e Enviar para o Bot
document.getElementById('btn-save').addEventListener('click', () => {
    if (canvas.getObjects('image').length === 0) {
        alert(texts.alertNoImage);
        return;
    }
    
    if (isOutsideTelegram) {
        performDownload();
        return;
    }

    if (texts.exportTitle) {
        document.getElementById('export-modal').style.display = 'flex';
    } else {
        performExport(false);
    }
});

document.getElementById('btn-export-cancel').addEventListener('click', () => {
    document.getElementById('export-modal').style.display = 'none';
});

document.getElementById('btn-export-photo').addEventListener('click', () => {
    document.getElementById('export-modal').style.display = 'none';
    performExport(false);
});

document.getElementById('btn-export-doc').addEventListener('click', () => {
    document.getElementById('export-modal').style.display = 'none';
    performExport(true);
});

async function performExport(asDocument) {
    const loadingMessages = loadingDetailMessages[userLang] || loadingDetailMessages.en;
    showLoading(loadingMessages[0]);
    uploadCancelRequested = false;
    currentUploadController = null;
    currentUploadTimeout = null;

    try {
        const dataUrl = await getCroppedCanvasDataURL();
        if (uploadCancelRequested) {
            throw new DOMException('Upload canceled', 'AbortError');
        }
        if (!dataUrl) {
            return;
        }
        setLoadingProgress(28, loadingMessages[1]);
        
        const payload = {
            image_base64: dataUrl,
            as_document: asDocument ? "true" : "false"
        };
        
        // Pega os dados do usuário via Telegram WebApp API
        if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
            payload.user_id = tg.initDataUnsafe.user.id.toString();
            payload.init_data = tg.initData;

            console.log('Iniciando upload para /api/upload', {
                user_id: payload.user_id,
                as_document: payload.as_document,
                image_base64_len: payload.image_base64.length
            });

            currentUploadController = new AbortController();
            currentUploadTimeout = setTimeout(() => currentUploadController.abort(), 45000);
            const cancelBtn = document.getElementById('btn-upload-cancel');
            if (cancelBtn) cancelBtn.style.display = 'inline-flex';
            setLoadingProgress(42, loadingMessages[1]);

            const response = await fetch('/api/upload', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload),
                signal: currentUploadController.signal
            });
            clearTimeout(currentUploadTimeout);
            currentUploadTimeout = null;
            setLoadingProgress(96, loadingMessages[3]);

            console.log('Resposta /api/upload', {
                ok: response.ok,
                status: response.status,
                statusText: response.statusText
            });

            if (response.ok) {
                tg.showAlert(texts.alertSuccess, () => {
                    tg.close(); // Fecha o Mini App
                });
            } else {
                let errData = {};
                try {
                    errData = await response.json();
                } catch (jsonErr) {
                    errData.error = `${response.status} ${response.statusText}`;
                }
                const translatedError = errData.error_key === 'quota_reached'
                    ? (texts.uploadQuotaReached || texts.adErrIncomplete)
                    : (errData.error || 'falha desconhecida');
                tg.showAlert(texts.alertError + translatedError);
            }
        } else {
            // Modo de teste local
            const a = document.createElement('a');
            a.href = dataUrl;
            a.download = 'merged_image_test.jpg';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            
            alert("Fora do Telegram: imagem baixada em ALTA RESOLUÇÃO!");
        }
    } catch (e) {
        console.error(e);
        if (!uploadCancelRequested) {
            const errMsg = e.name === 'AbortError'
                ? 'Tempo limite excedido ao enviar para o bot. Veja os logs do container unify-images-miniapp.'
                : (e.message || e.toString());
            if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
                tg.showAlert(texts.alertUnexpected + "\n\nDetalhes:\n" + errMsg);
            } else {
                alert(texts.alertUnexpected + "\n\nDetalhes:\n" + errMsg);
            }
        }
    } finally {
        if (currentUploadTimeout) clearTimeout(currentUploadTimeout);
        currentUploadTimeout = null;
        currentUploadController = null;
        hideLoading();
        uploadCancelRequested = false;
    }
}
