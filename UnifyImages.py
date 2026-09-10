# /seu_projeto/bot.py

import asyncio
import concurrent.futures
import datetime
import gc
import glob
import html
import io
import json
import logging
import math
import os
import platform
import random
import socket
import ssl
import sys
import tempfile
import time
import traceback
import uuid
import zipfile
from collections import deque
from logging.handlers import RotatingFileHandler

import aiohttp
import aiosqlite
import matplotlib
import psutil
from matplotlib import dates

matplotlib.use("Agg")
import re
from importlib.metadata import PackageNotFoundError, version

import cv2
import httpx
import matplotlib.pyplot as plt
import numpy as np
import pytesseract
from PIL import ExifTags, Image
from functools import wraps
import pymupdf as fitz
from pillow_heif import register_heif_opener


def pdfinfo_from_bytes(pdf_bytes: bytes) -> dict:
    """Extrai informações e metadados de PDF via PyMuPDF."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        meta = doc.metadata or {}
        info = {
            "Pages": len(doc),
            "Author": meta.get("author", "") or "",
            "CreationDate": meta.get("creationDate", "") or "",
            "ModDate": meta.get("modDate", "") or "",
            "Title": meta.get("title", "") or "",
            "Subject": meta.get("subject", "") or "",
            "Keywords": meta.get("keywords", "") or "",
            "Creator": meta.get("creator", "") or "",
            "Producer": meta.get("producer", "") or "",
            "Encrypted": "yes" if doc.is_encrypted else "no",
        }
        doc.close()
        return info
    except Exception as e:
        logger.error(f"Erro ao ler pdfinfo: {e}")
        return {"Pages": 1}


def convert_from_bytes(pdf_bytes: bytes, dpi: int = 150) -> list:
    """Converte páginas de PDF em lista de objetos PIL Image via PyMuPDF."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    for page in doc:
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        images.append(img)
    doc.close()
    return images
from telegram import (
    LabeledPrice,
    PreCheckoutQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,

    ReplyKeyboardMarkup,
    Update,
    User,
    WebAppInfo,
)
from telegram.error import BadRequest, Conflict, Forbidden, NetworkError
from telegram.ext import (
    PreCheckoutQueryHandler,
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    TypeHandler,
    ConversationHandler,
    filters,
)
from telegram.request import HTTPXRequest

# Registra suporte a HEIC no Pillow
register_heif_opener()

# Sistema de Tickets
# Garante que o diretório atual esteja no path para Docker/ambientes onde o PWD pode mudar
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import handlers_tickets_ptb as tickets_mod

# Configurações
# Tenta pegar do ambiente (Docker/.env).
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TELEGRAM_TOKEN:
    # O bot não pode funcionar sem um token.
    # Lançar um erro aqui faz com que o bot pare imediatamente se o token não for fornecido.
    raise ValueError("A variável de ambiente TELEGRAM_TOKEN não foi definida.")
if "replace_with_your_bot_token" in TELEGRAM_TOKEN or TELEGRAM_TOKEN.startswith("1234567890:"):
    raise ValueError("A variável TELEGRAM_TOKEN ainda está com o valor de exemplo. Configure o token real do BotFather.")

TELEGRAM_CONNECT_TIMEOUT = float(os.getenv("TELEGRAM_CONNECT_TIMEOUT", "30"))
TELEGRAM_READ_TIMEOUT = float(os.getenv("TELEGRAM_READ_TIMEOUT", "30"))
TELEGRAM_WRITE_TIMEOUT = float(os.getenv("TELEGRAM_WRITE_TIMEOUT", "30"))
TELEGRAM_POOL_TIMEOUT = float(os.getenv("TELEGRAM_POOL_TIMEOUT", "10"))
TELEGRAM_POLL_TIMEOUT = int(os.getenv("TELEGRAM_POLL_TIMEOUT", "30"))
TELEGRAM_BOOTSTRAP_RETRIES = int(os.getenv("TELEGRAM_BOOTSTRAP_RETRIES", "3"))
TELEGRAM_PROXY = os.getenv("TELEGRAM_PROXY") or None
TON_WALLET_ADDRESS = os.getenv("TON_WALLET_ADDRESS", "").strip()
TONCENTER_API_KEY = os.getenv("TONCENTER_API_KEY", "").strip()
TON_USDT_MASTER = os.getenv(
    "TON_USDT_MASTER",
    "EQCxE6mUtQJKFnGfaROTKOt1lZbDiiX1kCixRv7Nw2Id_sDs",
).strip()
TON_USDT_PACKAGES = ((1.0, 100), (5.0, 500), (10.0, 1000))

try:
    ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
    if not ADMIN_ID:
        raise ValueError("A variável de ambiente ADMIN_ID não foi definida ou é inválida.")
except (ValueError, TypeError):
    raise ValueError("A variável de ambiente ADMIN_ID deve ser um número inteiro.")
VERSION = "1.1.0"
RELEASE_DATE = "10/Sep/2026"
MAX_IMAGES = 20
MAX_FILE_SIZE_MB = 20
RATE_LIMIT_SECONDS = 5

COLORS = {
    "WHITE": ("⚪️ White", (255, 255, 255)),
    "BLACK": ("⚫️ Black", (0, 0, 0)),
    "GRAY": ("🩶 Gray", (128, 128, 128)),
    "RED": ("🔴 Red", (255, 0, 0)),
    "GREEN": ("🟢 Green", (0, 128, 0)),
    "BLUE": ("🔵 Blue", (0, 0, 255)),
    "YELLOW": ("🟡 Yellow", (255, 255, 0)),
    "PURPLE": ("🟣 Purple", (128, 0, 128)),
    "ORANGE": ("🟠 Orange", (255, 165, 0)),
    "BROWN": ("🟤 Brown", (165, 42, 42)),
    "PINK": ("🌸 Pink", (255, 192, 203)),
    "CYAN": ("💧 Cyan", (0, 255, 255)),
    "GOLD": ("🌟 Gold", (255, 215, 0)),
    "SILVER": ("💿 Silver", (192, 192, 192)),
    "NAVY": ("⚓️ Navy", (0, 0, 128)),
}

TRANSLATIONS = {}
LAST_MERGE_USAGE = {}
BOT_PAUSED = False
ADMIN_NOTIFICATIONS_ENABLED = False
MUTED_USERS = set()
TIP_IMAGE_CACHE = {}
LAST_BROADCAST_STATS = {}
# Executor global para tarefas CPU-bound (Processamento de Imagem)
# Limitado a 1 worker para evitar sobrecarga em hardware modesto (i3/4GB RAM)
PROCESS_POOL = concurrent.futures.ProcessPoolExecutor(max_workers=1)
PROCESSING_SEMAPHORE = asyncio.Semaphore(1)
PROCESSING_QUEUE = []  # Lista de tuplas (user_id, user_name)
CURRENT_PROCESSING = None  # Tupla (user_id, user_name)
ESTIMATED_TIME_PER_JOB = 30  # Segundos estimados por job
PENDING_LOGS = []  # Buffer para logs de atividade
AD_THRESHOLD = 50  # Limite padrão de imagens por anúncio
MINIAPP_AD_URL = os.getenv("MINIAPP_AD_URL", "https://your-miniapp-domain.com/")

# Configurações Padrão para GIF
GIF_DEFAULTS = {
    "fps": 10,
    "scale": 1.0,  # 1.0 = Original, 0.5 = 50%
    "speed": 1.0   # Multiplicador de velocidade
}


def is_gif_animated(file_path_or_bytes: str | bytes | io.BytesIO) -> bool:
    """Verifica se um GIF é animado (possui múltiplos frames)."""
    try:
        if isinstance(file_path_or_bytes, (bytes, bytearray)):
            file_path_or_bytes = io.BytesIO(file_path_or_bytes)
        with Image.open(file_path_or_bytes) as img:
            return getattr(img, "is_animated", False)
    except Exception:
        return False


def get_miniapp_ad_url(lang_code: str | None = None, ad_type: str | None = None) -> str:
    """Monta a URL do Mini App de anúncios com idioma explícito."""
    base_lang = (lang_code or "en").split("-")[0].lower()
    if base_lang == "hi":
        base_lang = "en"
    if base_lang not in {"pt", "en", "es", "fr", "it", "ru", "ar"}:
        base_lang = "en"

    params = f"?action=watch_ad&lang={base_lang}"
    if ad_type:
        params += f"&type={ad_type}"
    return MINIAPP_AD_URL + params


def _check_heic_encode_support() -> bool:
    """Verifica em tempo de inicialização se o encoder HEIC está disponível."""
    try:
        import pillow_heif
        pillow_heif.register_heif_opener()
        test_img = Image.new("RGB", (4, 4), color=(255, 0, 0))
        buf = io.BytesIO()
        test_img.save(buf, format="HEIF")
        return buf.tell() > 0
    except Exception:
        return False


HEIC_ENCODE_SUPPORTED: bool = _check_heic_encode_support()


async def spinner_task(
    message,
    base_text: str,
    stop_event: asyncio.Event,
    interval: float = 4.0,
) -> None:
    """Anima a mensagem com pontos enquanto `stop_event` não for definido.

    Cicla: base_text ⏳ → base_text ⏳. → base_text ⏳.. → base_text ⏳...
    """
    frames = ["⏳", "⏳.", "⏳..", "⏳..."]
    i = 0
    while not stop_event.is_set():
        try:
            await message.edit_text(f"{base_text}\n{frames[i % len(frames)]}", parse_mode="HTML")
        except Exception:
            pass  # ignora erros de flood/sem mudança
        i += 1
        try:
            await asyncio.wait_for(asyncio.shield(stop_event.wait()), timeout=interval)
        except asyncio.TimeoutError:
            pass


def load_translations() -> None:
    """Carrega traduções de arquivos JSON na pasta translations."""
    base_dir = os.path.dirname(__file__)
    # Procura na pasta translations e na raiz (para casos como Docker onde arquivos podem estar na raiz)
    search_dirs = [os.path.join(base_dir, "translations"), base_dir]

    for directory in search_dirs:
        if not os.path.exists(directory):
            continue
        for filename in glob.glob(os.path.join(directory, "*.json")):
            lang_code = os.path.splitext(os.path.basename(filename))[0]
            if lang_code in TRANSLATIONS:
                continue
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Verifica se é um arquivo de tradução válido (contém a chave 'start')
                    if isinstance(data, dict) and "start" in data:
                        TRANSLATIONS[lang_code] = data
            except Exception as e:
                logger.error(f"Erro ao carregar tradução {filename}: {e}")
    logger.info(f"Traduções carregadas: {list(TRANSLATIONS.keys())}")


def get_text(
    user: User | None, context: ContextTypes.DEFAULT_TYPE | None, key: str, lang: str = None, **kwargs
) -> str:
    """Retorna o texto traduzido para o idioma especificado ou do usuário, com fallback para inglês e português."""
    # 1. Tenta pegar o idioma passado explicitamente
    lang_code = lang

    # 2. Se não houver, tenta pegar o idioma personalizado do contexto (mais atual)
    if not lang_code and (
        context
        and hasattr(context, "user_data")
        and isinstance(context.user_data, dict)
    ):
        lang_code = context.user_data.get("custom_language")

    # 3. Se não houver, tenta pegar do objeto user
    if not lang_code and user and user.language_code:
        lang_code = user.language_code

    # Normaliza o idioma (ex: 'pt-br' -> 'pt')
    base_lang = lang_code.split("-")[0].lower() if lang_code else "en"
    if base_lang == "hi": # Força Hindi para Inglês
        base_lang = "en"

    # Ordem de preferência dos idiomas
    langs_to_try = []
    if lang_code: langs_to_try.append(lang_code)
    if base_lang not in langs_to_try: langs_to_try.append(base_lang)
    for l in ["en", "pt"]:
        if l not in langs_to_try:
            langs_to_try.append(l)

    text = None
    for lang_to_use in langs_to_try:
        if lang_to_use in TRANSLATIONS:
            text = TRANSLATIONS[lang_to_use].get(key)
            if text:
                break

    if not text:
        return key

    kwargs["version"] = VERSION
    try:
        return text.format(**kwargs)
    except:
        return text


def get_main_menu_keyboard(
    user: User | None, context: ContextTypes.DEFAULT_TYPE
) -> ReplyKeyboardMarkup:
    """Gera o teclado principal com base no idioma do usuário."""
    kb = [
        [
            get_text(user, context, "menu_merge_vertical"),
            get_text(user, context, "menu_merge_horizontal"),
        ],
        [
            get_text(user, context, "menu_tools"),
            get_text(user, context, "menu_my_usage"),
        ],
        [
            get_text(user, context, "menu_settings"),
            get_text(user, context, "menu_help"),
        ],
        [
            get_text(user, context, "menu_cancel"),
        ],
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True, is_persistent=True)


def get_admin_menu_keyboard() -> ReplyKeyboardMarkup:
    """Gera o teclado do painel administrativo com atalhos rápidos."""
    kb = [
        [
            "📊 /relatorio",
            "📈 /relatorio_uso",
        ],

        [
            "🎫 Gestão de Tickets",
        ],
        [
            "📢 /broadcast",
            "🔒 /banir",
            "⚙️ /diagnostico",
        ],
        [
            "⏸️ /pausar",
            "▶️ /retomar",
            "🔄 /restart",
        ],
        [
            "💾 /backup_db",
            "🧹 /limpar_cache",
        ],
        [
            "🧠 /cache",
        ],
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True, is_persistent=True)


def get_tools_menu_keyboard(
    user: User | None, context: ContextTypes.DEFAULT_TYPE
) -> ReplyKeyboardMarkup:
    """Gera o teclado de ferramentas com base no idioma do usuário."""
    kb = [
        [
            get_text(user, context, "menu_grid"),
            get_text(user, context, "menu_converter"),
            get_text(user, context, "menu_merge_pdf"),
        ],
        [
            get_text(user, context, "menu_compress"),
            get_text(user, context, "menu_ocr"),
            get_text(user, context, "menu_gif"),
        ],
        [
            get_text(user, context, "menu_remove_metadata"),
            get_text(user, context, "menu_sticker"),
            get_text(user, context, "menu_qrcode"),
        ],
        [
            get_text(user, context, "menu_zip_queue"),
            get_text(user, context, "menu_remove_bg"),
            get_text(user, context, "menu_watermark"),
        ],
        [
            get_text(user, context, "menu_meme"),
            get_text(user, context, "menu_censor"),
            get_text(user, context, "menu_other_bots"),
        ],
        [
            get_text(user, context, "btn_back"),
            get_text(user, context, "menu_contribute"),
        ],
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True, is_persistent=True)


def get_language_buttons(prefix: str) -> list[list[InlineKeyboardButton]]:
    """Gera a lista de botões de idioma para uso em teclados inline."""
    return [
        [
            InlineKeyboardButton("🇺🇸 English", callback_data=f"{prefix}:en"),
            InlineKeyboardButton("🇧🇷 Português", callback_data=f"{prefix}:pt"),
            InlineKeyboardButton("🇪🇸 Español", callback_data=f"{prefix}:es"),
        ],
        [
            InlineKeyboardButton("🇷🇺 Русский", callback_data=f"{prefix}:ru"),
            InlineKeyboardButton("🇺🇦 Українська", callback_data=f"{prefix}:uk"),
            InlineKeyboardButton("🇮🇹 Italiano", callback_data=f"{prefix}:it"),
        ],
        [
            InlineKeyboardButton("🇫🇷 Français", callback_data=f"{prefix}:fr"),
            InlineKeyboardButton("🇸🇦 العربية", callback_data=f"{prefix}:ar"),
        ],
    ]


def get_random_tip(user: User | None, context: ContextTypes.DEFAULT_TYPE) -> str | None:
    """Retorna uma dica aleatória traduzida."""
    # 1. Tenta pegar o idioma personalizado do contexto
    lang_code = context.user_data.get("custom_language")

    # 2. Se não houver, tenta pegar do objeto user
    if not lang_code and user and user.language_code:
        lang_code = user.language_code.split("-")[0].lower()

    # Força Hindi para Inglês
    if lang_code == "hi":
        lang_code = "en"

    fallback_order = ["en", "pt"]
    langs_to_try = []
    if lang_code:
        langs_to_try.append(lang_code)
    for lang in fallback_order:
        if lang not in langs_to_try:
            langs_to_try.append(lang)

    for lang in langs_to_try:
        if lang in TRANSLATIONS:
            tips = TRANSLATIONS[lang].get("tips")
            if tips and isinstance(tips, list) and len(tips) > 0:
                return random.choice(tips)
    return None


def check_rate_limit(user_id: int) -> int:
    """Verifica se o usuário está no rate limit. Retorna segundos restantes ou 0."""
    now = time.time()
    last_usage = LAST_MERGE_USAGE.get(user_id, 0)
    if now - last_usage < RATE_LIMIT_SECONDS:
        return int(RATE_LIMIT_SECONDS - (now - last_usage))
    return 0




async def check_ad_quota_reached(update, context, user) -> bool:
    """Verifica se o usuário atingiu a cota de imagens e exige anúncio."""
    if not user or user.id == ADMIN_ID:
        return False

    try:
        import aiosqlite
        import datetime
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
        async with aiosqlite.connect(DB_FILE) as db:
            async with db.execute("SELECT images_since_last_ad, is_premium, premium_until FROM users WHERE user_id = ?", (user.id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    images_since_last_ad = row[0]
                    is_premium = row[1]
                    premium_until_str = row[2]
                else:
                    return False

        if is_premium:
            return False

        if premium_until_str:
            try:
                premium_until = datetime.datetime.fromisoformat(premium_until_str)
                if datetime.datetime.now() < premium_until:
                    return False
            except:
                pass

        if images_since_last_ad >= AD_THRESHOLD:
            if images_since_last_ad == AD_THRESHOLD:
                if ADMIN_NOTIFICATIONS_ENABLED and user.id not in MUTED_USERS:
                    try:
                        admin_msg = (
                            "⚠️ <b>Alerta de Cota:</b> um usuário atingiu "
                            f"o limite de {AD_THRESHOLD} usos e precisa ver um anúncio."
                        )
                        import asyncio
                        asyncio.create_task(context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode="HTML"))
                    except Exception:
                        pass

                # A mensagem de apoio é um aviso único. O envio ocorre aqui
                # para que a segunda condição seja imediata, sem aguardar o job diário.
                async with aiosqlite.connect(DB_FILE) as reminder_db:
                    async with reminder_db.execute(
                        "SELECT support_quota_reminder_sent, COALESCE(custom_language, language_code) FROM users WHERE user_id = ?",
                        (user.id,),
                    ) as reminder_cursor:
                        reminder_row = await reminder_cursor.fetchone()
                    if reminder_row and not reminder_row[0]:
                        reminder_lang = reminder_row[1] or (user.language_code or "pt")
                        reminder_text = get_text_by_lang(reminder_lang, "weekly_ad_reminder_msg")
                        reminder_button = get_text_by_lang(reminder_lang, "btn_free_ad")
                        reminder_keyboard = InlineKeyboardMarkup([[
                            InlineKeyboardButton(
                                reminder_button,
                                web_app=WebAppInfo(url=get_miniapp_ad_url(reminder_lang, "voluntary")),
                            )
                        ]])
                        await context.bot.send_message(
                            chat_id=user.id,
                            text=reminder_text,
                            reply_markup=reminder_keyboard,
                            parse_mode="HTML",
                        )
                        await reminder_db.execute(
                            "UPDATE users SET support_quota_reminder_sent = 1 WHERE user_id = ?",
                            (user.id,),
                        )
                        await reminder_db.commit()

            # Pega o idioma para a mensagem de erro. Fallback manual simplificado se get_text falhar.
            try:
                text = get_text(user, context, "ad_quota_reached", threshold=AD_THRESHOLD)
                if text == "ad_quota_reached":
                    raise ValueError("Not translated")
            except:
                text = f"⏳ Você atingiu o limite gratuito de {AD_THRESHOLD} imagens!\\n\\nPara continuar criando e editando, por favor assista a um anúncio rápido clicando no botão abaixo. Isso ajuda a manter o bot online e gratuito para todos!"

            btn_text = get_text(user, context, "btn_watch_ad")
            if btn_text == "btn_watch_ad":
                btn_text = "🎥 Assistir Anúncio"
            ad_lang = (
                context.user_data.get("custom_language")
                if context and hasattr(context, "user_data") and isinstance(context.user_data, dict)
                else None
            ) or (user.language_code if user else None)
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(btn_text, web_app=WebAppInfo(url=get_miniapp_ad_url(ad_lang)))]])
            if update.callback_query:
                alert_text = get_text(user, context, "ad_quota_reached_alert")
                if alert_text == "ad_quota_reached_alert":
                    alert_text = "Limite atingido!"
                await update.callback_query.answer(text=alert_text, show_alert=True)
                await update.callback_query.message.reply_text(text, reply_markup=keyboard)
            elif update.message:
                await update.message.reply_text(text, reply_markup=keyboard)
            return True

        return False
    except Exception as e:
        logger.error(f"Erro ao checar cota de anúncio: {e}")
        return False

def update_rate_limit(user_id: int) -> None:
    """Atualiza o timestamp de uso do usuário e incrementa a cota de anúncios."""
    LAST_MERGE_USAGE[user_id] = time.time()

    async def increment_ad():
        try:
            import aiosqlite
            async with aiosqlite.connect(DB_FILE) as db:
                await db.execute("UPDATE users SET images_since_last_ad = images_since_last_ad + 1, total_credits_spent = total_credits_spent + 1 WHERE user_id = ?", (user_id,))
                await db.commit()
        except Exception as e:
            logger.error(f"Erro ao incrementar cota de anúncio: {e}")

    try:
        import asyncio
        loop = asyncio.get_running_loop()
        loop.create_task(increment_ad())
    except RuntimeError:
        pass



def _format_size(size_bytes: int) -> str:
    """Formata bytes para KB, MB, GB."""
    if size_bytes == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"


def base_handler_checks(func):
    """Um decorador para executar verificações padrão em handlers."""

    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        # As verificações precisam de um usuário e mensagem efetivos.
        if not update.effective_user or not update.effective_message:
            return

        if update.effective_message is None:
            return

        if await check_and_handle_setup_flow(update, context):
            return
        if await check_banned(update, context):
            return
        if await check_maintenance(update, context):
            return
        # Se todas as verificações passarem, executa a função original
        return await func(update, context, *args, **kwargs)

    return wrapper


# Configura o logging para nos ajudar a depurar
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        RotatingFileHandler(
            "bot.log", maxBytes=5 * 1024 * 1024, backupCount=2, encoding="utf-8"
        ),
        logging.StreamHandler(),
    ],
)
# Silencia logs verbosos do httpx (requisições HTTP do bot) para evitar flood
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Variáveis globais para diagnóstico
START_TIME = datetime.datetime.now()
PROCESS = psutil.Process(os.getpid())

# Garante que o caminho seja absoluto em relação ao arquivo do script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "data", "user_images.db")


def log_telegram_connectivity_check() -> None:
    """Registra um diagnóstico curto de DNS/TCP antes do polling."""
    host = "api.telegram.org"
    port = 443
    try:
        ip = socket.gethostbyname(host)
        logger.info("Diagnóstico Telegram: DNS OK %s -> %s", host, ip)
    except OSError as e:
        logger.error("Diagnóstico Telegram: falha de DNS para %s: %s", host, e)
        return

    try:
        with socket.create_connection((host, port), timeout=TELEGRAM_CONNECT_TIMEOUT):
            logger.info("Diagnóstico Telegram: TCP OK em %s:%s", host, port)
    except OSError as e:
        logger.error("Diagnóstico Telegram: falha TCP em %s:%s: %s", host, port, e)


async def setup_database() -> None:
    """Cria a tabela no banco de dados se ela não existir."""
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS user_images (
                user_id INTEGER,
                file_id TEXT,
                received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_document INTEGER DEFAULT 0
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT,
                username TEXT,
                language_code TEXT,
                last_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS system_config (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS muted_users (
                user_id INTEGER PRIMARY KEY
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS banned_users (
                user_id INTEGER PRIMARY KEY,
                reason TEXT,
                banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS last_merge_files (
                user_id INTEGER,
                file_id TEXT,
                file_order INTEGER
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS user_pdfs (
                user_id INTEGER,
                file_id TEXT,
                file_name TEXT,
                received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS donation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount_stars REAL,
                currency TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                action TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS ton_deposits (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                amount_usdt REAL NOT NULL,
                amount_stars REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                confirmed_at TIMESTAMP,
                tx_hash TEXT
            )
            """
        )
        await db.commit()

        # Helper para migrações seguras
        async def ensure_column(table_name, column_name, column_def):
            async with db.execute(f"PRAGMA table_info({table_name})") as cursor:
                columns = [row[1] for row in await cursor.fetchall()]
            if column_name not in columns:
                try:
                    await db.execute(
                        f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}"
                    )
                    logger.info(
                        f"Migração: Coluna '{column_name}' adicionada à tabela '{table_name}'."
                    )
                except Exception as e:
                    logger.error(f"Erro na migração da coluna '{column_name}': {e}")

        # Verifica se a tabela banned_users existe. Se não, cria.
        async with db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='banned_users'"
        ) as cursor:
            if not await cursor.fetchone():
                await db.execute(
                    """CREATE TABLE banned_users (user_id INTEGER PRIMARY KEY, reason TEXT, banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"""
                )

        async with db.execute("PRAGMA table_info(donation_history)") as cursor:
            donation_columns = await cursor.fetchall()
        amount_col = next((row for row in donation_columns if row[1] == "amount_stars"), None)
        if amount_col and (amount_col[2] or "").upper() == "INTEGER":
            try:
                await db.execute("ALTER TABLE donation_history RENAME TO donation_history_old")
                await db.execute(
                    """
                    CREATE TABLE donation_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        amount_stars REAL,
                        currency TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                await db.execute(
                    """
                    INSERT INTO donation_history (id, user_id, amount_stars, currency, timestamp)
                    SELECT id, user_id, amount_stars, currency, timestamp
                    FROM donation_history_old
                    """
                )
                await db.execute("DROP TABLE donation_history_old")
                logger.info("Migração: donation_history.amount_stars alterado para REAL.")
            except Exception as e:
                logger.error(f"Erro ao migrar donation_history.amount_stars para REAL: {e}")

        # Migração: Tenta adicionar a coluna username se ela não existir (para bancos antigos)
        await ensure_column("activity_logs", "username", "TEXT")

        # Migrações da tabela users
        await ensure_column("users", "output_format", "TEXT DEFAULT 'JPEG'")
        await ensure_column("users", "compression_quality", "INTEGER DEFAULT 100")
        await ensure_column("users", "background_color", "TEXT DEFAULT 'WHITE'")
        await ensure_column("users", "current_state", "TEXT DEFAULT NULL")
        await ensure_column("users", "custom_language", "TEXT DEFAULT NULL")
        await ensure_column("users", "auto_resize", "INTEGER DEFAULT 1")
        await ensure_column("users", "acquisition_source", "TEXT DEFAULT NULL")
        await ensure_column("users", "captcha_answer", "INTEGER DEFAULT NULL")
        await ensure_column("users", "border_width", "INTEGER DEFAULT 0")
        await ensure_column("users", "border_color", "TEXT DEFAULT 'WHITE'")

        # Migração manual para joined_at (evita erro de default não constante em SQLite antigo)
        async with db.execute("PRAGMA table_info(users)") as cursor:
            user_columns = [row[1] for row in await cursor.fetchall()]

        if "joined_at" not in user_columns:
            try:
                await db.execute("ALTER TABLE users ADD COLUMN joined_at TIMESTAMP")
                await db.execute(
                    "UPDATE users SET joined_at = CURRENT_TIMESTAMP WHERE joined_at IS NULL"
                )
                logger.info("Migração: Coluna 'joined_at' adicionada à tabela 'users'.")
            except Exception as e:
                logger.error(f"Erro na migração da coluna 'joined_at': {e}")

        await ensure_column("users", "promo_sent", "INTEGER DEFAULT 0")
        await ensure_column("users", "promo_martiancat_sent", "INTEGER DEFAULT 0")
        await ensure_column("users", "total_donated_stars", "INTEGER DEFAULT 0")
        await ensure_column("users", "donor_status", "TEXT DEFAULT 'User'")
        await ensure_column("users", "support_reminder_sent", "INTEGER DEFAULT 0")
        await ensure_column("users", "support_quota_reminder_sent", "INTEGER DEFAULT 0")

        # Migrações parea Marca d'água
        await ensure_column("users", "watermark_enabled", "INTEGER DEFAULT 0")
        await ensure_column("users", "watermark_text", "TEXT DEFAULT 'UnifyImages'")
        await ensure_column("users", "watermark_size", "INTEGER DEFAULT 30")
        await ensure_column("users", "watermark_color", "TEXT DEFAULT 'WHITE'")
        await ensure_column("users", "watermark_position", "TEXT DEFAULT 'bottom_right'")
        await ensure_column("users", "watermark_margin", "INTEGER DEFAULT 20")

        # Migrações da tabela user_images
        await ensure_column("user_images", "is_document", "INTEGER DEFAULT 0")
        await ensure_column("user_images", "message_id", "INTEGER")
        await ensure_column("user_images", "file_name", "TEXT")
        await ensure_column("user_images", "file_size_text", "TEXT")
        await ensure_column("user_images", "dimensions", "TEXT")
        await ensure_column("user_images", "file_fmt", "TEXT")
        await ensure_column("user_pdfs", "message_id", "INTEGER")
        await ensure_column("user_pdfs", "file_size_text", "TEXT")

        # Ad_quota columns
        await ensure_column("users", "images_since_last_ad", "INTEGER DEFAULT 0")
        await ensure_column("users", "total_credits_spent", "INTEGER DEFAULT 0")
        await ensure_column("users", "is_premium", "INTEGER DEFAULT 0")
        await ensure_column("users", "premium_until", "TIMESTAMP DEFAULT NULL")
        await ensure_column("users", "total_voluntary_ads", "INTEGER DEFAULT 0")
        await ensure_column("users", "last_ad_support_reminder", "TEXT DEFAULT NULL")

        # Tabela do sistema de tickets de suporte
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS support_tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                category TEXT,
                status TEXT DEFAULT 'open',
                text TEXT,
                admin_reply TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                closed_at DATETIME
            )
            """
        )

        await db.commit()
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS user_docx (
                user_id INTEGER,
                file_id TEXT,
                file_name TEXT,
                message_id INTEGER,
                file_size_text TEXT,
                received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS metadata_stats (
                tag_name TEXT PRIMARY KEY,
                removal_count INTEGER DEFAULT 0
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS error_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                error_message TEXT,
                traceback TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS maintenance_queue (
                user_id INTEGER PRIMARY KEY,
                attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Índices para performance
        await db.execute("CREATE INDEX IF NOT EXISTS idx_error_logs_timestamp ON error_logs(timestamp)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_activity_logs_user_id ON activity_logs(user_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_activity_logs_timestamp ON activity_logs(timestamp)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_support_tickets_user_id ON support_tickets(user_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_support_tickets_status ON support_tickets(status)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_user_images_user_id_received ON user_images(user_id, received_at)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_users_last_interaction ON users(last_interaction)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_ton_deposits_status ON ton_deposits(status, created_at)")
        await db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_ton_deposits_tx_hash ON ton_deposits(tx_hash) WHERE tx_hash IS NOT NULL")

        await db.commit()


async def post_init(application: Application) -> None:
    """Inicializa o banco de dados antes do bot começar."""
    await setup_database()
    await check_database_integrity()
    # Configura o módulo de tickets com dependências do bot principal
    tickets_mod.setup_tickets_module(
        db_file=DB_FILE,
        admin_id=ADMIN_ID,
        get_text_fn=get_text,
        translations=TRANSLATIONS,
    )
    # Carrega configurações do banco de dados
    global BOT_PAUSED, ADMIN_NOTIFICATIONS_ENABLED, PROCESS_POOL, PROCESSING_SEMAPHORE
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute(
            "SELECT value FROM system_config WHERE key = 'paused'"
        ) as cursor:
            row = await cursor.fetchone()
            if row and row[0] == "1":
                BOT_PAUSED = True

        async with db.execute(
            "SELECT value FROM system_config WHERE key = 'admin_notifications'"
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                ADMIN_NOTIFICATIONS_ENABLED = (row[0] == "1")
            else:
                # Valor padrão: Ativado
                await db.execute(
                    "INSERT INTO system_config (key, value) VALUES ('admin_notifications', '1')"
                )
                await db.commit()

        global MUTED_USERS
        async with db.execute("SELECT user_id FROM muted_users") as cursor:
            async for row in cursor:
                MUTED_USERS.add(row[0])

        # Carrega ad_threshold
        global AD_THRESHOLD
        async with db.execute(
            "SELECT value FROM system_config WHERE key = 'ad_threshold'"
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                AD_THRESHOLD = int(row[0])
            else:
                AD_THRESHOLD = 50
                await db.execute(
                    "INSERT INTO system_config (key, value) VALUES ('ad_threshold', '50')"
                )
                await db.commit()

        # Carrega max_workers
        async with db.execute(
            "SELECT value FROM system_config WHERE key = 'max_workers'"
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                workers = int(row[0])
            else:
                workers = 1
                await db.execute(
                    "INSERT INTO system_config (key, value) VALUES ('max_workers', '1')"
                )
                await db.commit()

    # Atualiza o pool e o semáforo se o valor for diferente do padrão (1) ou para garantir sincronia
    if workers != 1:
        if PROCESS_POOL:
            PROCESS_POOL.shutdown(wait=False)
        PROCESS_POOL = concurrent.futures.ProcessPoolExecutor(max_workers=workers)
        PROCESSING_SEMAPHORE = asyncio.Semaphore(workers)
        logger.info(f"Pool de processos ajustado para {workers} workers.")



@base_handler_checks
async def set_ad_threshold(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Define a quantidade de imagens necessárias para ver um anúncio (/anuncios_qtd)."""
    user = update.effective_user
    if user.id != ADMIN_ID:
        return

    try:
        qtd = int(context.args[0])
        if qtd < 1:
            raise ValueError

        global AD_THRESHOLD
        AD_THRESHOLD = qtd

        import aiosqlite
        async with aiosqlite.connect(DB_FILE) as db:
            await db.execute("INSERT INTO system_config (key, value) VALUES ('ad_threshold', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(qtd),))
            await db.commit()

        await update.message.reply_text(f"✅ Quantidade de imagens para exibir anúncio atualizada para: {qtd}")
    except (IndexError, ValueError):
        await update.message.reply_text("Uso correto: /anuncios_qtd <numero>")

async def flush_activity_logs(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Escreve os logs pendentes no banco de dados em lote para evitar I/O excessivo."""
    global PENDING_LOGS
    if not PENDING_LOGS:
        return

    # Copia e limpa a lista global atomicamente (para o contexto da thread/async)
    # Filtra interações do admin para não contabilizar nas estatísticas
    logs_to_save = [log for log in PENDING_LOGS if log[0] != ADMIN_ID]
    PENDING_LOGS.clear()

    if not logs_to_save:
        return

    try:
        async with aiosqlite.connect(DB_FILE) as db:
            await db.executemany(
                "INSERT INTO activity_logs (user_id, username, action, timestamp) VALUES (?, ?, ?, ?)",
                logs_to_save,
            )
            await db.commit()
        logger.info(f"Logs de atividade: {len(logs_to_save)} registros salvos.")
    except Exception as e:
        logger.error(f"Erro ao salvar logs de atividade em lote: {e}")
        # Em caso de erro grave, poderíamos tentar devolver ao buffer, mas para logs, melhor descartar para não estourar memória


def notify_admin_background(bot, text: str) -> None:
    """Dispara uma notificação textual para o Admin em background."""
    if not ADMIN_ID or not ADMIN_NOTIFICATIONS_ENABLED:
        return

    async def _send():
        try:
            await bot.send_message(
                chat_id=ADMIN_ID,
                text=text,
                parse_mode="HTML",
                read_timeout=5,
                write_timeout=5,
            )
        except Exception as e:
            logger.error(f"Erro ao notificar admin (background): {e}")

    try:
        asyncio.create_task(_send())
    except Exception as e:
        logger.error(f"Erro ao agendar notificação ao admin: {e}")


async def flush_settings_notifications(
    user: User, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Envia todas as notificações de alteração de configurações acumuladas."""
    if not ADMIN_ID or user.id == ADMIN_ID or not ADMIN_NOTIFICATIONS_ENABLED or user.id in MUTED_USERS:
        return

    settings_changes = context.user_data.get("settings_changes", [])
    if settings_changes:
        try:
            header = "🔔 Alteração de configuração do usuário\n"

            # A primeira alteração é "Abriu as configurações", então tratamos ela como título
            action_title = settings_changes[0]
            # As demais são os detalhes
            changes_details = "\n- ".join(
                html.escape(change) for change in settings_changes[1:]
            )

            msg = f"{header}{html.escape(action_title)}"
            if changes_details:
                msg += f":\n- {changes_details}"

            notify_admin_background(context.bot, msg)
        except Exception as e:
            logger.error(f"Erro ao preparar notificação de configurações agrupadas: {e}")
        finally:
            # Limpa a lista de alterações após o envio (ou falha no envio)
            context.user_data["settings_changes"] = []


async def register_interaction(
    user: User,
    context: ContextTypes.DEFAULT_TYPE,
    action_description: str,
    is_settings_change: bool = False,
) -> None:
    """Registra a interação do usuário e notifica o admin sem compartilhar conteúdo."""
    # Atualiza dados do usuário (Last Seen) - Mantemos direto no DB pois é um UPSERT importante
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute(
            """
            INSERT INTO users (user_id, first_name, username, language_code, last_interaction, output_format, compression_quality, background_color, joined_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, 'JPEG', 100, 'WHITE', CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                first_name=excluded.first_name,
                username=excluded.username,
                language_code=excluded.language_code,
                last_interaction=CURRENT_TIMESTAMP
            """,
            (user.id, user.first_name, user.username, user.language_code),
        )

        # Mantém o cache em memória sincronizado com alterações feitas fora do
        # bot tradicional, como a troca de idioma pelo Mini App.
        async with db.execute(
            "SELECT custom_language FROM users WHERE user_id = ?", (user.id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row and row[0]:
                context.user_data["custom_language"] = row[0]
            else:
                context.user_data.pop("custom_language", None)

        await db.commit()

    # Adiciona ao buffer de logs em vez de escrever direto no disco
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    PENDING_LOGS.append((user.id, None, action_description, timestamp))

    if is_settings_change:
        if "settings_changes" not in context.user_data:
            context.user_data["settings_changes"] = []
        context.user_data["settings_changes"].append(action_description)
    else:
        # Envia quaisquer notificações de configurações pendentes antes da nova ação
        await flush_settings_notifications(user, context)

        # Envia a notificação para a ação atual (que não é de configuração) em background
        if ADMIN_ID and user.id != ADMIN_ID and ADMIN_NOTIFICATIONS_ENABLED and user.id not in MUTED_USERS:
            msg = f"🔔 Ação de usuário: {html.escape(action_description)}"
            notify_admin_background(context.bot, msg)


async def global_logging_middleware(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Captura qualquer interação para fins estatísticos, sem bloquear o processamento."""
    user = update.effective_user
    if not user:
        return

    # Define o tipo de interação
    action_type = "interaction_unknown"
    if update.message:
        if update.message.text:
            action_type = "msg_text"
        elif update.message.photo:
            action_type = "msg_photo"
        elif update.message.document:
            action_type = "msg_document"
    elif update.callback_query:
        action_type = "callback_query"
    elif update.inline_query:
        action_type = "inline_query"

    # Adiciona ao buffer diretamente (sem notificar admin ou atualizar last_seen pesado)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    PENDING_LOGS.append((user.id, None, action_type, timestamp))


async def check_banned(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Verifica se o usuário está banido. Retorna True se estiver."""
    user = update.effective_user
    if user.id == ADMIN_ID:
        return False

    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute(
            "SELECT reason FROM banned_users WHERE user_id = ?", (user.id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                reason = row[0] or "N/A"
                if update.effective_message:
                    await update.effective_message.reply_html(
                        get_text(user, context, "banned_msg", reason=reason)
                    )
                return True
    return False


async def check_maintenance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Verifica se o bot está em manutenção. Retorna True se estiver pausado e o usuário não for admin."""
    if BOT_PAUSED and update.effective_user.id != ADMIN_ID:
        # Registra o usuário na fila de notificação de retorno
        async with aiosqlite.connect(DB_FILE) as db:
            await db.execute(
                "INSERT OR IGNORE INTO maintenance_queue (user_id) VALUES (?)",
                (update.effective_user.id,),
            )
            await db.commit()

        await update.effective_message.reply_html(
            get_text(update.effective_user, context, "maintenance_msg")
        )
        return True
    return False


async def send_keyboard_tip_image(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Envia a imagem de dica do teclado baseada no idioma e notifica admin em caso de erro."""
    user = update.effective_user
    chat_id = update.effective_chat.id
    lang_code = context.user_data.get("custom_language")
    if not lang_code and user and user.language_code:
        lang_code = user.language_code.split("-")[0].lower()

    # Força Hindi para Inglês
    if lang_code == "hi":
        lang_code = "en"

    image_map = {
        "pt": "DicaTeclado_Portugues.png",
        "ru": "DicaTeclado_Russo.png",
        "it": "DicaTeclado_Italiano.png",
        "ar": "DicaTeclado_Arabe.png",
        "es": "DicaTeclado_Espanhol.png",
        "fr": "DicaTeclado_Frances.png",
    }
    image_filename = image_map.get(lang_code, "DicaTeclado_Ingles.png")

    # Tenta enviar pelo cache (file_id) primeiro
    cached_id = TIP_IMAGE_CACHE.get(image_filename)
    success = False
    error_msg = None

    if cached_id:
        try:
            await context.bot.send_photo(chat_id=chat_id, photo=cached_id)
            success = True
        except Exception:
            TIP_IMAGE_CACHE.pop(image_filename, None)

    if not success:
        image_path = os.path.join(os.path.dirname(__file__), image_filename)

        # Fallback para inglês se a imagem traduzida não existir
        if (
            not os.path.exists(image_path)
            and image_filename != "DicaTeclado_Ingles.png"
        ):
            image_filename = "DicaTeclado_Ingles.png"
            image_path = os.path.join(os.path.dirname(__file__), image_filename)

        if os.path.exists(image_path):
            try:
                def _read_bytes(path: str) -> bytes:
                    with open(path, "rb") as f:
                        return f.read()

                img_data = await asyncio.to_thread(_read_bytes, image_path)
                sent_msg = await context.bot.send_photo(chat_id=chat_id, photo=io.BytesIO(img_data))
                if sent_msg.photo:
                    TIP_IMAGE_CACHE[image_filename] = sent_msg.photo[-1].file_id
                    success = True
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Erro ao enviar imagem de dica ({image_filename}): {e}")
        else:
            error_msg = "Arquivo não encontrado"
            logger.error(f"Imagem de dica não encontrada: {image_filename}")

    if success and ADMIN_ID and user.id != ADMIN_ID and ADMIN_NOTIFICATIONS_ENABLED:
        try:
            # A dica é enviada somente ao usuário; não há encaminhamento de
            # identidade ou conteúdo ao administrador.
            if context.user_data.get("is_new_user"):
                context.user_data.pop("is_new_user", None)
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text="🔔 Dica de teclado enviada a um usuário.",
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(f"Erro ao notificar admin sobre dica enviada: {e}")

    if not success and error_msg and ADMIN_ID:
        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text="⚠️ Não foi possível enviar uma dica de teclado a um usuário.",
            )
        except Exception:
            pass


async def check_and_handle_setup_flow(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    """
    Verifica se um usuário está no fluxo de configuração inicial.
    Se estiver, re-solicita a ação e retorna True (bloqueando a execução).
    Caso contrário, retorna False.
    """
    user = update.effective_user
    # Não bloqueia o admin ou se não houver uma mensagem para responder.
    if not user or user.id == ADMIN_ID or not update.effective_message:
        return False

    state = context.user_data.get("state")

    # Se o usuário não está no DB, ele deve usar /start.
    # O próprio /start irá lidar com isso. Qualquer outro comando será bloqueado.
    is_start_command = (
        update.message
        and update.message.text
        and update.message.text.startswith("/start")
    )
    # Verifica se o usuário existe no banco para evitar erros, mas o estado vem da memória
    if state is None and not is_start_command:
        # Opcional: verificar se user existe no DB se quiser ser muito estrito,
        # mas aqui assumimos que se não tem estado e não é start, segue o fluxo normal.
        pass

    # Lógica original adaptada: se não tem estado e não é start, verifica se é user novo no DB
    # Para manter compatibilidade com a lógica anterior de bloquear users não registrados:
    if state is None and not is_start_command:
        async with aiosqlite.connect(DB_FILE) as db:
            async with db.execute(
                "SELECT 1 FROM users WHERE user_id = ?", (user.id,)
            ) as cursor:
                if not await cursor.fetchone():
                    await update.effective_message.reply_html(
                        get_text(user, context, "start", mention=user.mention_html())
                    )
                    return True

    if state == "WAITING_LANGUAGE":
        btns = get_language_buttons("set_lang_init")
        reply_markup = InlineKeyboardMarkup(btns)
        await update.effective_message.reply_html(
            get_text(user, context, "setup_choose_language"), reply_markup=reply_markup
        )
        return True

    if state == "WAITING_CAPTCHA":
        n1 = random.randint(1, 10)
        n2 = random.randint(1, 10)
        context.user_data["captcha_answer"] = n1 + n2
        ans = n1 + n2
        async with aiosqlite.connect(DB_FILE) as db:
            await db.execute(
                "UPDATE users SET captcha_answer = ? WHERE user_id = ?", (ans, user.id)
            )
            await db.commit()
        await update.effective_message.reply_html(
            get_text(user, context, "captcha_error", n1=n1, n2=n2)
        )
        return True

    return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para o comando /start."""
    user = update.effective_user
    if await check_banned(update, context):
        return

    # Captura a origem se houver (deep linking)
    source = context.args[0] if context.args else None

    # Verifica se é o primeiro acesso (antes de registrar no banco)
    is_first_access = False
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute(
            "SELECT 1 FROM users WHERE user_id = ?", (user.id,)
        ) as cursor:
            if not await cursor.fetchone():
                is_first_access = True

    if is_first_access and user.id != ADMIN_ID:
        context.user_data["is_new_user"] = True
        action_desc = f"{get_text(user, context, 'start_nav', lang='pt')} ({get_text(user, context, 'first_access', lang='pt')})"
        if source:
            action_desc += f" via '{source}'"
        # A interação é registrada primeiro para criar o usuário no DB
        await register_interaction(user, context, action_desc)

        # Agora que o usuário foi registrado, salva a fonte e o estado inicial
        async with aiosqlite.connect(DB_FILE) as db:
            # Estado agora é em memória
            if source:
                await db.execute(
                    "UPDATE users SET acquisition_source = ? WHERE user_id = ?",
                    (source, user.id),
                )
            await db.commit()

        context.user_data["state"] = "WAITING_LANGUAGE"

        # Envia seleção de idioma
        btns = get_language_buttons("set_lang_init")
        reply_markup = InlineKeyboardMarkup(btns)
        await update.message.reply_html(
            get_text(user, context, "setup_choose_language"), reply_markup=reply_markup
        )
        return

    action_desc = "Usou /start"
    if source:
        action_desc += f" com payload '{source}'"
    await register_interaction(user, context, action_desc)
    await show_start_menu(update, context)


async def check_database_integrity() -> None:
    """Verifica a integridade do banco de dados na inicialização."""
    if not os.path.exists(DB_FILE):
        return

    logger.info("Verificando integridade do banco de dados...")
    try:
        async with aiosqlite.connect(DB_FILE) as db:
            async with db.execute("PRAGMA integrity_check") as cursor:
                row = await cursor.fetchone()
                if row and row[0] == "ok":
                    async with db.execute("SELECT COUNT(*) FROM users") as count_cursor:
                        user_count = (await count_cursor.fetchone())[0]

                    db_size_mb = os.path.getsize(DB_FILE) / (1024 * 1024)
                    logger.info(
                        f"✅ Banco de dados íntegro. Tamanho: {db_size_mb:.2f} MB | Usuários: {user_count}"
                    )
                else:
                    logger.critical(f"❌ ERRO DE INTEGRIDADE NO BANCO DE DADOS: {row}")
    except Exception as e:
        logger.error(f"❌ Falha ao verificar integridade do DB: {e}")


async def show_start_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Exibe o menu principal e mensagens de boas-vindas."""
    user = update.effective_user

    # Mensagem especial para o admin
    if user.id == ADMIN_ID:
        # Busca workers atuais para exibir no menu
        current_workers = "1"
        try:
            async with aiosqlite.connect(DB_FILE) as db:
                async with db.execute(
                    "SELECT value FROM system_config WHERE key = 'max_workers'"
                ) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        current_workers = row[0]
        except Exception:
            pass

        # Busca meta atual
        goal_stats = await get_monthly_goal_stats()
        goal_display = f"[${goal_stats['goal']}]" if goal_stats['goal'] > 0 else ""

        # Busca estado das notificações do admin
        notifications_status = "Ativado" if ADMIN_NOTIFICATIONS_ENABLED else "Desativado"

        admin_msg = (
            "👑 <b>Painel Admin — MergeImages</b>\n\n"
            "/relatorio - Gera relatório de atividade e crescimento.\n"
            "/relatorio_uso - Gráficos de uso e Top Users.\n"
            "/diagnostico - Mostra a saúde do bot e do servidor.\n"
            "/backup_db - Envia o arquivo do banco de dados.\n"
            "/pausar - Pausa o bot para manutenção.\n"
            "/retomar - O bot volta a funcionar.\n"
            f"/processos [{current_workers}] - Define processamentos simultâneos.\n"
            f"/anuncios_qtd [{AD_THRESHOLD}] - Define meta de imagens para anúncio.\n"
            "/banir [id|user] - Bane um usuário.\n"
            "/listar_banidos - Exibe todos os usuários banidos.\n"
            "/desbanir [id] - Remove o banimento.\n"

            "/limpar_cache - Limpa arquivos temporários e RAM.\n"
            "/limpar_db_bloqueados - Remove usuários que bloquearam o bot.\n"
            "/validar_doacao_cripto [id] [usd] - Validar doação externa.\n"
            f"/meta_mensal [usd] -\u003e {goal_display} - Define meta de doação.\n"
            "/saldo_estrelas - Consulta histórico oficial de Stars (API).\n"
            "/broadcast - Mensagem a todos os usuários do bot\n"
            "/broadcast_usuario [id/username] - Mensagem para usuário específico\n"
            "/broadcast_ultimo - Dados do último broadcast\n"
            "/logs [n] - Ver últimas linhas do log\n"
            "/restart - Reinicia o bot\n"
            "/settings - Abrir menu de configurações\n\n"
            "<i>Use os atalhos no teclado abaixo para acesso rápido.</i>"
        )
        await context.bot.send_message(
            chat_id=user.id, text=admin_msg, parse_mode="HTML",
            reply_markup=get_admin_menu_keyboard()
        )
        return

    msg = get_text(user, context, "start", mention=user.mention_html())
    reply_markup = get_main_menu_keyboard(user, context)
    await context.bot.send_message(
        chat_id=user.id, text=msg, parse_mode="HTML", reply_markup=reply_markup
    )

    # Se estiver em manutenção, avisa logo após as boas-vindas
    if BOT_PAUSED:
        if user.id != ADMIN_ID:
            async with aiosqlite.connect(DB_FILE) as db:
                await db.execute(
                    "INSERT OR IGNORE INTO maintenance_queue (user_id) VALUES (?)",
                    (user.id,),
                )
                await db.commit()
        await update.message.reply_html(get_text(user, context, "maintenance_msg"))


async def version_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para o comando /version."""
    if await check_and_handle_setup_flow(update, context):
        return
    user = update.effective_user
    await register_interaction(user, context, "Usou /version")
    msg = get_text(user, context, "version_msg", version=VERSION, date=RELEASE_DATE)
    await update.message.reply_html(msg)

@base_handler_checks
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para o comando /help. Envia um arquivo HTML explicativo."""
    user = update.effective_user
    await register_interaction(user, context, "Usou /help")

    # Obtém o idioma configurado para o usuário
    user_lang = context.user_data.get("custom_language")
    if not user_lang:
        async with aiosqlite.connect(DB_FILE) as db:
            async with db.execute("SELECT custom_language, language_code FROM users WHERE user_id = ?", (user.id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    user_lang = row[0] or row[1] or "en"
                else:
                    user_lang = "en"

    # Normaliza para o código de idioma base suportado
    user_lang = user_lang.split("-")[0].lower() if user_lang else "en"
    if user_lang not in ["pt", "en", "es", "fr", "it", "ru", "ar"]:
        user_lang = "en"

    # Obtém o conteúdo HTML localizado
    html_content = get_text(user, context, "help_html_content", lang=user_lang)

    # Se não houver conteúdo HTML na tradução, usa o fallback de texto atual
    if not html_content or html_content == "help_html_content":
        await update.message.reply_html(get_text(user, context, "help", lang=user_lang))
        tip = get_random_tip(user, context)
        if tip:
            await update.message.reply_html(tip)
        await send_keyboard_tip_image(update, context)
        return

    # Estilo CSS para o HTML ser premium
    css = """
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; background-color: #f4f7f6; }
        .container { background-color: #fff; padding: 30px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }
        h1 { color: #0088cc; text-align: center; border-bottom: 2px solid #0088cc; padding-bottom: 10px; }
        h2 { color: #2c3e50; margin-top: 30px; border-left: 5px solid #0088cc; padding-left: 10px; }
        .feature-card { background: #eef2f3; padding: 15px; border-radius: 8px; margin-bottom: 15px; border-left: 4px solid #3498db; }
        .feature-card b { color: #2980b9; }
        .footer { text-align: center; margin-top: 30px; color: #7f8c8d; font-size: 0.9em; }
        .highlight { color: #e74c3c; font-weight: bold; }
        .btn-link { display: inline-block; padding: 10px 20px; background-color: #0088cc; color: white; text-decoration: none; border-radius: 5px; margin-top: 20px; }
    </style>
    """

    full_html = f"""
    <!DOCTYPE html>
    <html lang="{user_lang}">
    <head>
        <meta charset="UTF-8">
        <title>Help - UnifyImages</title>
        {css}
    </head>
    <body>
        <div class="container">
            {html_content}
            <div class="footer">
                <p>UnifyImages Bot v{VERSION} - {RELEASE_DATE}</p>
            </div>
        </div>
    </body>
    </html>
    """

    filename = f"help_{user_lang}.html"
    f_io = io.BytesIO(full_html.encode("utf-8"))
    f_io.name = filename

    # Adiciona botão de apoio no caption do manual
    keyboard_help = [
        [InlineKeyboardButton(get_text(user, context, "menu_contribute"), callback_data="contribute:menu")],
        [InlineKeyboardButton(get_text(user, context, "menu_support_tickets"), callback_data="help_open_tickets")],
    ]

    await update.message.reply_document(
        document=f_io,
        caption=get_text(user, context, "help_file_caption", lang=user_lang),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard_help)
    )



@base_handler_checks
async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Armazena o file_id da imagem recebida."""
    user = update.effective_user
    await register_interaction(user, context, "Enviou uma imagem")
    user_id = user.id
    message_id = update.message.message_id
    # Pegamos a foto de maior resolução
    file_size = 0
    file_name = "Foto"
    file_fmt = "JPEG"
    width = 0
    height = 0
    is_document = 0

    if update.message.document:
        file_id = update.message.document.file_id
        file_size = update.message.document.file_size
        file_name = update.message.document.file_name or "Documento"
        if update.message.document.mime_type:
            file_fmt = update.message.document.mime_type.split("/")[-1].upper()
        is_document = 1

        # Verificação de segurança: Extensão do arquivo
        if file_name:
            ext = os.path.splitext(file_name)[1].lower()
            if ext not in [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".gif", ".heic", ".heif"]:
                await update.message.reply_html(
                    get_text(user, context, "invalid_file_type")
                )
                return
    elif update.message.photo:
        photo = update.message.photo[-1]
        file_id = photo.file_id
        file_size = photo.file_size
        file_name = get_text(user, context, "telegram_photo")
        width = photo.width
        height = photo.height
        is_document = 0
    else:
        return

    if file_size and file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
        await update.message.reply_text(
            get_text(user, context, "file_too_large", max=MAX_FILE_SIZE_MB)
        )
        return

    dims_text = f"{width}x{height}" if width and height else "?"
    size_text = _format_size(file_size)

    async with aiosqlite.connect(DB_FILE) as db:
        # Verifica quantas imagens o usuário já tem ANTES de inserir
        async with db.execute(
            "SELECT COUNT(*) FROM user_images WHERE user_id = ?", (user_id,)
        ) as cursor_count:
            count = (await cursor_count.fetchone())[0]

        if count >= MAX_IMAGES:
            await update.message.reply_text(
                get_text(user, context, "too_many_images", count=count, max=MAX_IMAGES)
            )
            return

        # Aviso quando está na penúltima posição (X-1)
        if count == MAX_IMAGES - 1:
            await update.message.reply_html(
                get_text(user, context, "near_limit_warning", max=MAX_IMAGES)
            )

        cursor = await db.execute(
            "INSERT INTO user_images (user_id, file_id, is_document, message_id, file_name, file_size_text, dimensions, file_fmt) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, file_id, is_document, message_id, file_name, size_text, dims_text, file_fmt),
        )
        rowid = cursor.lastrowid
        await db.commit()

        # Incrementa para exibir na mensagem
        count += 1

    # Detectar QR Code e GIF Animado na imagem
    qr_detected = False
    qr_content = None
    is_animated = False
    try:
        # Baixa a imagem para detecção
        file = await context.bot.get_file(file_id)
        image_bytes = await file.download_as_bytearray()

        # 1. Verifica se o GIF é animado (se for o caso)
        if file_fmt == "GIF":
            is_animated = await asyncio.to_thread(is_gif_animated, bytes(image_bytes))

        # 2. Executa detecção de QR Code em background
        loop = asyncio.get_running_loop()
        qr_content = await loop.run_in_executor(
            PROCESS_POOL,
            _detect_qr_code_task,
            bytes(image_bytes)
        )
        if qr_content:
            qr_detected = True
            # Armazena o conteúdo do QR Code no contexto do usuário
            context.user_data[f"qr_content_{rowid}"] = qr_content
    except Exception as e:
        logger.debug(f"Erro ao processar imagem para detecção: {e}")

    # Responde com a sequência e botão de lixeira
    keyboard = [
        [
            InlineKeyboardButton("🔼", callback_data=f"move:up:{rowid}"),
            InlineKeyboardButton("🔽", callback_data=f"move:down:{rowid}"),
        ],
        [
            InlineKeyboardButton(
                get_text(user, context, "btn_about"), callback_data=f"about_img:{rowid}"
            ),
            InlineKeyboardButton("🔍", callback_data=f"search_img:{rowid}"),
            InlineKeyboardButton(
                get_text(user, context, "btn_delete"), callback_data=f"del_img:{rowid}"
            )
        ],
    ]

    # Adiciona botão de ler QR Code se detectado
    if qr_detected:
        keyboard.append([
            InlineKeyboardButton(
                get_text(user, context, "btn_read_qr"), callback_data=f"read_qr:{rowid}"
            )
        ])

    # Define reply_markup padrão
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Texto base da sequência
    msg_text = get_text(
        user,
        context,
        "image_sequence",
        count=count,
        name=html.escape(file_name),
        format=file_fmt,
        dims=dims_text,
        size=size_text,
    )

    # Adiciona aviso de GIF se for o caso e alterna botões
    if file_fmt == "GIF":
        if is_animated:
            # Para GIFs animados, removemos da fila de imagens para não atrapalhar o merge
            # Mas informamos as opções de conversão/extração
            async with aiosqlite.connect(DB_FILE) as db:
                await db.execute("DELETE FROM user_images WHERE rowid = ?", (rowid,))
                await db.commit()

            msg_text = f"🎞️ <b>{html.escape(file_name)}</b>\n{get_text(user, context, 'gif_animated')}"

            # Salva o file_id em cache curto para evitar callback_data grande (Bug Button_data_invalid)
            # Usamos o message_id como chave única temporária
            context.user_data[f"temp_gif_{message_id}"] = file_id

            keyboard = [
                [
                    InlineKeyboardButton(
                        get_text(user, context, "gif_btn_gif_to_video"),
                        callback_data=f"gif_conv:vid:{message_id}"
                    ),
                    InlineKeyboardButton(
                        get_text(user, context, "gif_btn_extract_frames"),
                        callback_data=f"gif_conv:ext:{message_id}"
                    )
                ],
                [
                    InlineKeyboardButton(get_text(user, context, "menu_cancel"), callback_data=f"gif_conv:can:{message_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
        else:
            msg_text += get_text(user, context, "gif_static")

    await update.message.reply_html(
        msg_text,
        reply_markup=reply_markup,
    )

    # O teclado inline acima controla a imagem; esta mensagem restaura o menu principal.
    await update.message.reply_text(
        get_text(user, context, "image_received"),
        reply_markup=get_main_menu_keyboard(user, context),
    )


async def handle_search_image_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Solicita consentimento e, depois, envia a imagem a serviços externos."""
    query = update.callback_query
    user = query.from_user

    try:
        data_parts = query.data.split(":")
        action = data_parts[0]
        rowid = int(data_parts[1])
    except (IndexError, ValueError):
        await query.answer(get_text(user, context, "search_error_invalid_action"), show_alert=True)
        return

    if action == "search_img":
        consent_text = get_text(user, context, "search_external_consent")
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                get_text(user, context, "search_external_continue"),
                callback_data=f"search_img_confirm:{rowid}",
            ),
            InlineKeyboardButton(
                get_text(user, context, "menu_cancel"),
                callback_data=f"search_img_cancel:{rowid}",
            ),
        ]])
        await query.answer()
        await query.message.reply_html(consent_text, reply_markup=keyboard)
        return

    if action == "search_img_cancel":
        await query.answer(get_text(user, context, "search_external_cancelled"), show_alert=True)
        try:
            await query.message.delete()
        except Exception:
            pass
        return

    if action != "search_img_confirm":
        await query.answer(get_text(user, context, "search_error_invalid_action"), show_alert=True)
        return

    await query.answer(get_text(user, context, "msg_generating_search_link"))

    try:
        # O upload só começa depois da confirmação explícita do usuário.
        # Busca o file_id no banco
        async with aiosqlite.connect(DB_FILE) as db:
            async with db.execute(
                "SELECT file_id, file_name FROM user_images WHERE rowid = ?", (rowid,)
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    await query.message.reply_html(get_text(user, context, "session_expired"))
                    return
                file_id = row[0]
                orig_file_name = row[1] or "image.jpg"

        # Baixa a imagem
        file = await context.bot.get_file(file_id)

        # Verifica o tamanho (o telegra.ph aceita até 5MB)
        if file.file_size > 5 * 1024 * 1024:
            await query.message.reply_html(get_text(user, context, "search_error_too_large"))
            return

        image_bytes = await file.download_as_bytearray()

        # Upload para o host temporário
        image_url = None

        # Tenta primeiro Telegra.ph
        try:
            async with httpx.AsyncClient() as client:
                files = {'file': ('image.jpg', bytes(image_bytes), 'image/jpeg')}
                logger.info(f"Uploading to telegra.ph: size={len(image_bytes)} bytes")
                response = await client.post(
                    'https://telegra.ph/upload',
                    files=files,
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
                )

                if response.status_code == 200:
                    res_data = response.json()
                    if isinstance(res_data, list) and len(res_data) > 0:
                        image_url = f"https://telegra.ph{res_data[0]['src']}"
                        logger.info(f"Telegra.ph upload success: {image_url}")
                    else:
                        logger.warning(f"Telegra.ph returned unexpected format: {res_data}")
                else:
                    logger.error(f"Telegra.ph failed ({response.status_code}): {response.text}")
        except Exception as e:
            logger.error(f"Error on Telegra.ph upload: {e}")

        # Se falhou, tenta Catbox.moe como fallback
        if not image_url:
            try:
                async with httpx.AsyncClient() as client:
                    data = {'reqtype': 'fileupload'}
                    files = {'fileToUpload': ('image.jpg', bytes(image_bytes), 'image/jpeg')}
                    logger.info("Trying Catbox.moe fallback...")
                    # Aumentamos o timeout pois o catbox pode demorar um pouco
                    response = await client.post('https://catbox.moe/user/api.php', data=data, files=files, timeout=30.0)

                    if response.status_code == 200 and response.text.startswith("https://"):
                        image_url = response.text.strip()
                        logger.info(f"Catbox.moe upload success: {image_url}")
                    else:
                        logger.error(f"Catbox.moe failed ({response.status_code}): {response.text}")
            except Exception as e:
                logger.error(f"Error on Catbox.moe upload: {e}")

        if not image_url:
            raise Exception("Todos os serviços de upload falharam.")

        lens_url = f"https://lens.google.com/uploadbyurl?url={image_url}"

        keyboard = [[InlineKeyboardButton("🔗 Google Lens", url=lens_url)]]
        await query.message.reply_html(
            get_text(user, context, "search_link_ready"),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        # Log de estatísticas
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        PENDING_LOGS.append((user.id, None, "search_img", timestamp))

    except Exception as e:
        logger.error(f"Erro ao gerar link de pesquisa: {e}")
        await query.message.reply_html(get_text(user, context, "search_link_error", error=str(e)))


@base_handler_checks
async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Armazena o file_id do PDF recebido e oferece opções."""
    user = update.effective_user
    doc = update.message.document
    message_id = update.message.message_id
    if doc.file_size and doc.file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
        await update.message.reply_text(
            get_text(user, context, "file_too_large", max=MAX_FILE_SIZE_MB)
        )
        return

    await register_interaction(user, context, "Enviou um PDF")

    # Salva o file_id associado à mensagem para recuperação no callback
    context.user_data[f"pdf_{update.message.message_id}"] = doc.file_id

    size_text = _format_size(doc.file_size or 0)

    # Adiciona à fila de PDFs para mesclagem
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute(
            "INSERT INTO user_pdfs (user_id, file_id, file_name, message_id, file_size_text) VALUES (?, ?, ?, ?, ?)",
            (user.id, doc.file_id, doc.file_name or "file.pdf", message_id, size_text),
        )
        rowid = cursor.lastrowid
        await db.commit()
        async with db.execute("SELECT COUNT(*) FROM user_pdfs WHERE user_id = ?", (user.id,)) as cursor:
            pdf_count = (await cursor.fetchone())[0]

    page_count = "?"
    author = "?"
    date_info = "?"
    is_protected = "?"

    try:
        # Baixa o arquivo para obter o número de páginas
        pdf_file = await context.bot.get_file(doc.file_id)
        pdf_bytes = await pdf_file.download_as_bytearray()
        info = await asyncio.to_thread(pdfinfo_from_bytes, bytes(pdf_bytes))
        page_count = info.get("Pages", "?")
        author = info.get("Author", get_text(user, context, "val_unknown")) or get_text(user, context, "val_unknown")
        date_info = info.get("ModDate", info.get("CreationDate", "?"))
        is_protected = get_text(user, context, "val_yes") if "yes" in str(info.get("Encrypted", "")).lower() else get_text(user, context, "val_no")
    except Exception as e:
        logger.error(f"Erro ao obter informações do PDF para o usuário {user.id}: {e}")
        # Pode ser um erro de poppler não instalado, notificar admin
        if ADMIN_ID:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text="⚠️ Falha ao processar um PDF; detalhes foram omitidos por privacidade.",
            )
        await update.message.reply_html(get_text(user, context, "pdf_read_error"))
        return

    keyboard = [
        [
            InlineKeyboardButton(
                get_text(user, context, "menu_extract_pages"),
                callback_data=f"pdf_action:extract_pages:{update.message.message_id}",
            ),
            InlineKeyboardButton(
                get_text(user, context, "menu_extract_text"),
                callback_data=f"pdf_action:extract_text:{update.message.message_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                get_text(user, context, "menu_convert_docx"),
                callback_data=f"pdf_action:to_docx:{update.message.message_id}",
            ),
        ],
        [
            InlineKeyboardButton("🔼", callback_data=f"move_pdf:up:{rowid}"),
            InlineKeyboardButton("🔽", callback_data=f"move_pdf:down:{rowid}"),
        ],
        [
            InlineKeyboardButton(
                get_text(user, context, "btn_about"), callback_data=f"about_pdf:{rowid}"
            ),
            InlineKeyboardButton(
                get_text(user, context, "btn_delete"), callback_data=f"del_pdf:{rowid}"
            )
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Exibe posição na fila de PDFs
    if pdf_count > 1:
        await update.message.reply_html(
            get_text(user, context, "pdf_queue_position", current=pdf_count, total=pdf_count)
        )

    # Se houver mais de um PDF na fila, adiciona o botão de mesclar
    if pdf_count > 1:
        keyboard.append([
            InlineKeyboardButton(get_text(user, context, "menu_merge_pdfs"), callback_data=f"pdf_action:merge_pdfs:{update.message.message_id}")
        ])
        reply_markup = InlineKeyboardMarkup(keyboard)


    await update.message.reply_html(
        get_text(
            user,
            context,
            "pdf_info",
            name=html.escape(doc.file_name or "file.pdf"),
            pages=page_count,
            size=size_text,
            author=html.escape(author),
            date=html.escape(date_info),
            protected=is_protected,
        ),
        reply_markup=reply_markup,
    )


@base_handler_checks
async def handle_invalid_file(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Rejeita arquivos que não sejam imagens."""
    user = update.effective_user
    await update.message.reply_html(get_text(user, context, "invalid_file_type"))


def _inspect_and_cache_docx_task(docx_bytes: bytes, cache_path: str) -> tuple[int | str, int | str]:
    """Salva DOCX em cache e extrai estatísticas de parágrafos/palavras em processo separado."""
    try:
        from docx import Document as DocxDocument
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, "wb") as f:
            f.write(docx_bytes)

        docx_doc = DocxDocument(io.BytesIO(docx_bytes))
        paragraphs = [p.text for p in docx_doc.paragraphs if p.text.strip()]
        para_count = len(paragraphs)
        all_words = " ".join(paragraphs)
        word_count = len(all_words.split())
        return para_count, word_count
    except Exception as e:
        logger.error(f"Erro no _inspect_and_cache_docx_task: {e}")
        return "?", "?"


@base_handler_checks
async def handle_docx(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Armazena o file_id do DOCX recebido e oferece opções de processamento."""
    user = update.effective_user
    doc = update.message.document
    message_id = update.message.message_id

    if doc.file_size and doc.file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
        await update.message.reply_text(
            get_text(user, context, "file_too_large", max=MAX_FILE_SIZE_MB)
        )
        return

    await register_interaction(user, context, "Enviou um DOCX")

    # Salva no contexto para recuperação rápida no callback
    context.user_data[f"docx_{message_id}"] = doc.file_id

    size_text = _format_size(doc.file_size or 0)

    # Salva na fila do banco
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute(
            "INSERT INTO user_docx (user_id, file_id, file_name, message_id, file_size_text) VALUES (?, ?, ?, ?, ?)",
            (user.id, doc.file_id, doc.file_name or "file.docx", message_id, size_text),
        )
        rowid = cursor.lastrowid
        await db.commit()

    # Tenta obter info básica do DOCX via python-docx de forma assíncrona
    word_count = "?"
    para_count = "?"
    try:
        docx_file = await context.bot.get_file(doc.file_id)
        docx_bytes = await docx_file.download_as_bytearray()
        cache_path = os.path.join("cache", f"docx_{user.id}_{message_id}.docx")

        loop = asyncio.get_running_loop()
        para_count, word_count = await loop.run_in_executor(
            PROCESS_POOL, _inspect_and_cache_docx_task, bytes(docx_bytes), cache_path
        )
        context.user_data[f"docx_path_{message_id}"] = cache_path
    except Exception as e:
        logger.error(f"Erro ao ler DOCX do usuário {user.id}: {e}")

    keyboard = [
        [
            InlineKeyboardButton(
                get_text(user, context, "menu_extract_docx_pages"),
                callback_data=f"docx_action:extract_pages:{message_id}",
            ),
            InlineKeyboardButton(
                get_text(user, context, "menu_extract_docx_text"),
                callback_data=f"docx_action:extract_text:{message_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                get_text(user, context, "menu_convert_docx_pdf"),
                callback_data=f"docx_action:to_pdf:{message_id}",
            ),
        ],
        [
            InlineKeyboardButton("🔼", callback_data=f"move_docx:up:{rowid}"),
            InlineKeyboardButton("🔽", callback_data=f"move_docx:down:{rowid}"),
        ],
        [
            InlineKeyboardButton(
                get_text(user, context, "btn_delete"), callback_data=f"del_docx:{rowid}"
            ),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_html(
        get_text(
            user,
            context,
            "docx_info",
            name=html.escape(doc.file_name or "file.docx"),
            size=size_text,
            words=word_count,
            paragraphs=para_count,
        ),
        reply_markup=reply_markup,
    )


async def handle_docx_action_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Despacha as ações para um arquivo DOCX (extrair páginas, texto ou converter para PDF)."""
    query = update.callback_query
    await query.answer()
    user = query.from_user

    # Data: docx_action:action:msg_id
    parts = query.data.split(":")
    action = parts[1]
    msg_id = parts[2]

    file_id = context.user_data.get(f"docx_{msg_id}")
    if not file_id:
        await query.edit_message_text(get_text(user, context, "session_expired"))
        return

    # Rate Limit para todas as ações
    if await check_ad_quota_reached(update, context, user):
        return
    remaining = check_rate_limit(user.id)
    if remaining > 0:
        await query.answer(
            get_text(user, context, "rate_limit_error", seconds=remaining),
            show_alert=True,
        )
        return
    update_rate_limit(user.id)

    # Obtém os bytes do DOCX (do cache ou baixa novamente)
    async def get_docx_bytes() -> bytes:
        path = context.user_data.get(f"docx_path_{msg_id}")
        if path and os.path.exists(path):
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, lambda: open(path, "rb").read())
        docx_file = await context.bot.get_file(file_id)
        return bytes(await docx_file.download_as_bytearray())

    if action == "extract_text":
        status_msg = await query.message.reply_html(
            get_text(user, context, "extracting_docx_text")
        )
        try:
            docx_bytes = await get_docx_bytes()
            loop = asyncio.get_running_loop()
            text = await loop.run_in_executor(
                PROCESS_POOL, _extract_docx_text_task, docx_bytes
            )
            await status_msg.delete()
            await register_interaction(user, context, "Extraiu texto de DOCX")

            if not text.strip():
                await query.message.reply_html(get_text(user, context, "docx_no_text"))
            else:
                caption = get_text(user, context, "extract_text_success")
                if len(text) > 4000:
                    f_bytes = io.BytesIO(text.encode("utf-8"))
                    f_bytes.name = "texto_extraido.txt"
                    await query.message.reply_document(document=f_bytes, caption=caption)
                else:
                    await query.message.reply_html(
                        f"{caption}\n<pre>{html.escape(text.strip())}</pre>"
                    )
        except Exception as e:
            logger.error(f"Erro ao extrair texto do DOCX para {user.id}: {e}")
            await status_msg.edit_text(get_text(user, context, "docx_read_error"))

    elif action == "to_pdf":
        status_msg = await query.message.reply_html(
            get_text(user, context, "converting_docx_pdf")
        )
        try:
            docx_bytes = await get_docx_bytes()
            loop = asyncio.get_running_loop()
            stop_spin = asyncio.Event()
            spin = asyncio.create_task(
                spinner_task(status_msg, get_text(user, context, "converting_docx_pdf"), stop_spin)
            )
            try:
                pdf_bytes = await loop.run_in_executor(
                    PROCESS_POOL, _convert_docx_to_pdf_task, docx_bytes
                )
            finally:
                stop_spin.set()
                spin.cancel()
            pdf_buffer = io.BytesIO(pdf_bytes)
            pdf_buffer.name = f"converted_{user.id}.pdf"
            await context.bot.send_document(
                chat_id=query.message.chat_id,
                document=pdf_buffer,
                caption=get_text(user, context, "convert_docx_pdf_success"),
            )
            await status_msg.delete()
            await register_interaction(user, context, "Converteu DOCX para PDF")
        except Exception as e:
            logger.error(f"Erro ao converter DOCX para PDF para {user.id}: {e}")
            await status_msg.edit_text(get_text(user, context, "convert_docx_pdf_error"))

    elif action == "extract_pages":
        status_msg = await query.message.reply_html(
            get_text(user, context, "extracting_docx_pages")
        )
        try:
            docx_bytes = await get_docx_bytes()
            loop = asyncio.get_running_loop()
            stop_spin = asyncio.Event()
            spin = asyncio.create_task(
                spinner_task(status_msg, get_text(user, context, "extracting_docx_pages"), stop_spin)
            )
            try:
                zip_bytes = await loop.run_in_executor(
                    PROCESS_POOL, _extract_docx_pages_task, docx_bytes
                )
            finally:
                stop_spin.set()
                spin.cancel()
            zip_buffer = io.BytesIO(zip_bytes)
            zip_buffer.name = f"docx_pages_{user.id}.zip"
            await context.bot.send_document(
                chat_id=query.message.chat_id,
                document=zip_buffer,
                caption=get_text(user, context, "extract_pages_success"),
            )
            await status_msg.delete()
            await register_interaction(user, context, "Extraiu páginas de DOCX")
        except Exception as e:
            logger.error(f"Erro ao extrair páginas do DOCX para {user.id}: {e}")
            await status_msg.edit_text(get_text(user, context, "docx_read_error"))


async def handle_delete_docx_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Remove um DOCX específico da fila do usuário."""
    query = update.callback_query
    await query.answer()
    user = query.from_user

    rowid = int(query.data.split(":")[1])
    async with aiosqlite.connect(DB_FILE) as db:
        # Obtém message_id para limpar do contexto
        async with db.execute(
            "SELECT message_id FROM user_docx WHERE rowid = ? AND user_id = ?",
            (rowid, user.id),
        ) as cursor:
            row = await cursor.fetchone()
        if row:
            context.user_data.pop(f"docx_{row[0]}", None)
            path = context.user_data.pop(f"docx_path_{row[0]}", None)
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass
        await db.execute(
            "DELETE FROM user_docx WHERE rowid = ? AND user_id = ?", (rowid, user.id)
        )
        await db.commit()

    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_html(get_text(user, context, "docx_deleted"))


async def gif_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Exibe o menu de ferramentas de GIF."""
    user = update.effective_user
    await register_interaction(user, context, "Abriu menu GIF")

    # Garante configurações padrão na sessão
    if "gif_settings" not in context.user_data:
        context.user_data["gif_settings"] = GIF_DEFAULTS.copy()

    keyboard = [
        [InlineKeyboardButton(get_text(user, context, "gif_btn_imgs"), callback_data="gif_action:imgs_to_gif")],
        [InlineKeyboardButton(get_text(user, context, "gif_btn_video"), callback_data="gif_action:vid_to_gif")],
        [InlineKeyboardButton(get_text(user, context, "gif_btn_gif_to_video"), callback_data="gif_action:gif_to_vid")],
        [InlineKeyboardButton(get_text(user, context, "gif_btn_extract_zip"), callback_data="gif_action:gif_to_zip")],
        [
            InlineKeyboardButton(get_text(user, context, "gif_btn_settings"), callback_data="gif_action:settings"),
            InlineKeyboardButton(get_text(user, context, "btn_back"), callback_data="gif_action:back")
        ]
    ]

    text = get_text(user, context, "gif_menu_title")

    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    else:
        await update.message.reply_html(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_gif_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gerencia a navegação do menu GIF."""
    query = update.callback_query
    await query.answer()
    user = query.from_user
    action = query.data.split(":")[1]

    if action == "back":
        # Volta para o menu ferramentas (reutilizando tools_menu_command logicamente)
        msg = get_text(user, context, "tools_menu_title")
        reply_markup = get_tools_menu_keyboard(user, context)
        # Como tools_menu envia nova msg, aqui deletamos a antiga e mandamos nova para manter consistência de teclado
        await query.message.delete()
        await query.message.reply_text(msg, reply_markup=reply_markup, parse_mode="HTML")
        return

    if action == "settings":
        settings = context.user_data.get("gif_settings", GIF_DEFAULTS)
        text = (
            get_text(user, context, "gif_settings_title",
                     fps=settings['fps'],
                     scale=int(settings['scale']*100))
        )

        # Obter traduções para escala e FPS
        scale_label = get_text(user, context, "gif_scale_label")
        fps_label = get_text(user, context, "gif_fps_label")

        # Determinar opções selecionadas
        current_fps = settings.get('fps', 10)
        current_scale = settings.get('scale', 1.0)

        # Criar botões com check emoji para opções selecionadas
        keyboard = [
            [
                InlineKeyboardButton(f"{'✅ ' if current_fps == 5 else ''}{fps_label}: 5", callback_data="gif_set:fps:5"),
                InlineKeyboardButton(f"{'✅ ' if current_fps == 10 else ''}{fps_label}: 10", callback_data="gif_set:fps:10"),
                InlineKeyboardButton(f"{'✅ ' if current_fps == 20 else ''}{fps_label}: 20", callback_data="gif_set:fps:20"),
            ],
            [
                InlineKeyboardButton(f"{'✅ ' if current_scale == 0.5 else ''}{scale_label}: 50%", callback_data="gif_set:scale:0.5"),
                InlineKeyboardButton(f"{'✅ ' if current_scale == 1.0 else ''}{scale_label}: 100%", callback_data="gif_set:scale:1.0"),
            ],
            [InlineKeyboardButton(get_text(user, context, "btn_back"), callback_data="gif_action:menu")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return

    if action == "menu":
        await gif_menu_command(update, context)
        return

    if action == "imgs_to_gif":
        await process_images_to_gif(update, context)
        return

    if action == "vid_to_gif":
        context.user_data["state"] = "WAITING_VIDEO_FOR_GIF"
        await query.edit_message_text(
            get_text(user, context, "gif_waiting_video"),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(get_text(user, context, "menu_cancel"), callback_data="gif_action:menu")]])
        )
        return

    if action == "gif_to_vid":
        context.user_data["state"] = "WAITING_GIF_FOR_VIDEO"
        await query.edit_message_text(
            get_text(user, context, "gif_waiting_gif"),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(get_text(user, context, "menu_cancel"), callback_data="gif_action:menu")]])
        )
        return

    if action == "gif_to_zip":
        context.user_data["state"] = "WAITING_GIF_FOR_ZIP"
        await query.edit_message_text(
            get_text(user, context, "gif_waiting_extract_zip"),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(get_text(user, context, "menu_cancel"), callback_data="gif_action:menu")]])
        )
        return


async def handle_gif_settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Atualiza configurações de GIF."""
    query = update.callback_query
    await query.answer()

    # data: gif_set:key:value
    parts = query.data.split(":")
    key = parts[1]
    value = float(parts[2])

    if "gif_settings" not in context.user_data:
        context.user_data["gif_settings"] = GIF_DEFAULTS.copy()

    if key == "fps":
        context.user_data["gif_settings"]["fps"] = int(value)
    elif key == "scale":
        context.user_data["gif_settings"]["scale"] = value

    # Chama handle_gif_menu_callback para renderizar a tela de settings
    await handle_gif_menu_callback(update, context)


def _create_gif_from_images_task(image_bytes_list: list[bytes], fps: int, scale: float) -> bytes:
    """Cria GIF a partir de lista de imagens."""
    if not image_bytes_list:
        return b""

    frames = []
    min_width = float('inf')
    min_height = float('inf')

    # Primeiro passo: carregar todas as imagens e encontrar o menor tamanho
    for b in image_bytes_list:
        try:
            img = Image.open(io.BytesIO(b))
            if img.mode != "RGBA":
                img = img.convert("RGBA")

            # Aplica escala primeiro
            if scale != 1.0:
                new_size = (int(img.width * scale), int(img.height * scale))
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            # Encontra o menor tamanho
            min_width = min(min_width, img.width)
            min_height = min(min_height, img.height)

            frames.append(img)
        except Exception:
            pass

    if not frames:
        raise ValueError("Nenhuma imagem válida para GIF.")

    # Segundo passo: redimensionar todas as imagens para o menor tamanho
    resized_frames = []
    for img in frames:
        if img.width != min_width or img.height != min_height:
            img = img.resize((min_width, min_height), Image.Resampling.LANCZOS)
        resized_frames.append(img)

    out = io.BytesIO()
    # Duration é em milissegundos por frame. 1000ms / fps
    duration = int(1000 / fps)

    resized_frames[0].save(
        out,
        format="GIF",
        save_all=True,
        append_images=resized_frames[1:],
        duration=duration,
        loop=0,
        disposal=2,
        optimize=True
    )
    return out.getvalue()


def _detect_qr_code_task(image_bytes: bytes) -> str | None:
    """Detecta QR Code em uma imagem e retorna o conteúdo se encontrado."""
    try:
        import numpy as np
        # Converte bytes para imagem OpenCV
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            return None

        # Inicializa o detector de QR Code
        qr_decoder = cv2.QRCodeDetector()

        # Detecta e decodifica o QR Code
        ret_qr, decoded_info, points, straight_barcode = qr_decoder.detectAndDecodeMulti(img)

        if ret_qr and decoded_info:
            # Retorna o primeiro QR Code encontrado
            return decoded_info[0] if decoded_info else None

        return None
    except Exception as e:
        logger.debug(f"Erro ao detectar QR Code: {e}")
        return None


def _video_to_gif_task(video_path: str, fps: int, scale: float) -> bytes:
    """Converte vídeo para GIF usando OpenCV e PIL."""
    cap = cv2.VideoCapture(video_path)
    frames = []

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Converte BGR (OpenCV) para RGB (PIL)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(frame_rgb)

            if scale != 1.0:
                new_size = (int(pil_img.width * scale), int(pil_img.height * scale))
                pil_img = pil_img.resize(new_size, Image.Resampling.NEAREST) # Nearest é mais rápido para vídeo

            frames.append(pil_img)

            # Limite de segurança de frames para não estourar memória (aprox 10 seg a 30fps = 300 frames)
            if len(frames) > 400:
                break
    finally:
        cap.release()

    if not frames:
        raise ValueError("Não foi possível ler frames do vídeo.")

    # Reduz FPS se necessário pulando frames
    # Se o vídeo original for 30fps e queremos 10fps, pegamos 1 a cada 3
    step = max(1, int(30 / fps))
    final_frames = frames[::step]

    out = io.BytesIO()
    duration = int(1000 / fps)

    final_frames[0].save(
        out,
        format="GIF",
        save_all=True,
        append_images=final_frames[1:],
        duration=duration,
        loop=0,
        optimize=True
    )
    return out.getvalue()


def _gif_to_video_task(gif_bytes: bytes) -> str:
    """Converte GIF para Vídeo (MP4) usando OpenCV."""
    import tempfile

    # Salva GIF temporário para leitura
    with tempfile.NamedTemporaryFile(suffix=".gif", delete=False) as tmp_gif:
        tmp_gif.write(gif_bytes)
        tmp_gif_path = tmp_gif.name

    output_path = tmp_gif_path.replace(".gif", ".mp4")

    try:
        cap = cv2.VideoCapture(tmp_gif_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 10
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Codec mp4v é amplamente suportado
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            out.write(frame)

        cap.release()
        out.release()

        return output_path
    finally:
        if os.path.exists(tmp_gif_path):
            os.remove(tmp_gif_path)


async def process_images_to_gif(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Processa a fila de imagens para criar um GIF."""
    user = update.effective_user

    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute(
            "SELECT file_id FROM user_images WHERE user_id = ? ORDER BY received_at ASC",
            (user.id,),
        )
        rows = await cursor.fetchall()

    if not rows or len(rows) < 2:
        await update.callback_query.answer("⚠️ Você precisa de pelo menos 2 imagens na fila.", show_alert=True)
        return

    # Tenta editar a mensagem original, mas se falhar continua
    try:
        await update.callback_query.edit_message_text(get_text(user, context, "gif_generating"), parse_mode="HTML")
    except Exception:
        pass  # Mensagem pode ter sido deletada

    await context.bot.send_chat_action(chat_id=user.id, action="upload_video")

    try:
        # Mostrar barra de progresso visual - enviando mensagem de progresso
        progress_msg = await context.bot.send_message(
            chat_id=user.id,
            text=get_text(user, context, 'gif_generating_progress')
        )

        tasks = [context.bot.get_file(row[0]) for row in rows]
        files = await asyncio.gather(*tasks)
        content_tasks = [f.download_as_bytearray() for f in files]
        image_contents = await asyncio.gather(*content_tasks)

        settings = context.user_data.get("gif_settings", GIF_DEFAULTS)

        # Atualiza barra de progresso
        try:
            await progress_msg.edit_text(f"⏳ {get_text(user, context, 'gif_creating_animation') or 'Criando animação...'}")
        except Exception:
            pass

        loop = asyncio.get_running_loop()
        gif_bytes = await loop.run_in_executor(
            PROCESS_POOL,
            _create_gif_from_images_task,
            [bytes(c) for c in image_contents],
            settings["fps"],
            settings["scale"]
        )

        if len(gif_bytes) > 50 * 1024 * 1024:
            await update.callback_query.message.reply_text(
                get_text(user, context, "gif_too_large", size=_format_size(len(gif_bytes)))
            )
            return

        f_io = io.BytesIO(gif_bytes)
        f_io.name = f"animation_{user.id}.gif"

        await context.bot.send_animation(
            chat_id=user.id,
            animation=f_io,
            caption=get_text(user, context, "gif_success")
        )

        # Notifica Admin e Loga
        if ADMIN_ID and user.id != ADMIN_ID and ADMIN_NOTIFICATIONS_ENABLED and user.id not in MUTED_USERS:
            notify_admin_background(context.bot, "🎞️ GIF criado com sucesso.")

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        PENDING_LOGS.append((user.id, None, "gif_created_from_images", timestamp))

        # Limpa fila
        async with aiosqlite.connect(DB_FILE) as db:
            await db.execute("DELETE FROM user_images WHERE user_id = ?", (user.id,))
            await db.commit()

        # Remove mensagem de progresso
        try:
            await progress_msg.delete()
        except Exception:
            pass

        # Remove mensagem original do callback
        try:
            await update.callback_query.delete_message()
        except Exception:
            pass

        await gif_menu_command(update, context) # Retorna ao menu

    except Exception as e:
        logger.error(f"Erro ao criar GIF: {e}")
        try:
            await progress_msg.delete()
        except Exception:
            pass
        await update.callback_query.message.reply_text(get_text(user, context, "gif_error"))


async def handle_move_docx_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Reordena um DOCX na fila (up / down)."""
    query = update.callback_query
    await query.answer()
    user = query.from_user

    parts = query.data.split(":")
    direction = parts[1]
    rowid = int(parts[2])

    async with aiosqlite.connect(DB_FILE) as db:
        # Carrega todos os registros do usuário em ordem
        async with db.execute(
            "SELECT rowid, file_id, file_name, message_id, file_size_text, received_at "
            "FROM user_docx WHERE user_id = ? ORDER BY received_at ASC",
            (user.id,),
        ) as cursor:
            rows = await cursor.fetchall()

        idx = next((i for i, r in enumerate(rows) if r[0] == rowid), None)
        if idx is None:
            return

        if direction == "up" and idx > 0:
            other_idx = idx - 1
        elif direction == "down" and idx < len(rows) - 1:
            other_idx = idx + 1
        else:
            await query.answer()
            return

        # Troca os timestamps para simular reordenação
        ts_current = rows[idx][5]
        ts_other = rows[other_idx][5]
        await db.execute(
            "UPDATE user_docx SET received_at = ? WHERE rowid = ?",
            (ts_other, rows[idx][0]),
        )
        await db.execute(
            "UPDATE user_docx SET received_at = ? WHERE rowid = ?",
            (ts_current, rows[other_idx][0]),
        )
        await db.commit()

    await query.answer("✅")


async def handle_pdf_action_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Lida com as ações para um arquivo PDF (extrair páginas ou texto)."""
    query = update.callback_query
    await query.answer()
    user = query.from_user

    # Data: pdf_action:action:msg_id
    parts = query.data.split(":")
    action = parts[1]
    msg_id = parts[2]

    file_id = context.user_data.get(f"pdf_{msg_id}")
    if not file_id:
        await query.edit_message_text(get_text(user, context, "session_expired"))
        return

    if action == "merge_pdfs":
        # Rate Limit
        if await check_ad_quota_reached(update, context, user):
            return
        remaining = check_rate_limit(user.id)
        if remaining > 0:
            await query.answer(
                get_text(user, context, "rate_limit_error", seconds=remaining),
                show_alert=True,
            )
            return
        update_rate_limit(user.id)

        async with aiosqlite.connect(DB_FILE) as db:
            cursor = await db.execute(
                "SELECT file_id FROM user_pdfs WHERE user_id = ? ORDER BY received_at ASC",
                (user.id,),
            )
            rows = await cursor.fetchall()

        if not rows or len(rows) < 2:
            await query.answer(get_text(user, context, "need_more_images"), show_alert=True)
            return

        await query.edit_message_text(
            get_text(user, context, "merging_pdfs", count=len(rows)), parse_mode="HTML"
        )

        try:
            tasks = [context.bot.get_file(row[0]) for row in rows]
            files = await asyncio.gather(*tasks)
            content_tasks = [f.download_as_bytearray() for f in files]
            pdf_contents = await asyncio.gather(*content_tasks)

            loop = asyncio.get_running_loop()
            merged_pdf = await loop.run_in_executor(
                PROCESS_POOL, _merge_pdfs_task, [bytes(c) for c in pdf_contents]
            )

            f_io = io.BytesIO(merged_pdf)
            f_io.name = f"merged_{user.id}.pdf"
            await context.bot.send_document(
                chat_id=query.message.chat_id,
                document=f_io,
                caption=get_text(user, context, "pdf_merge_success"),
            )
            # await query.message.delete() # Mantém a mensagem original

            # Limpa a fila de PDFs
            async with aiosqlite.connect(DB_FILE) as db:
                await db.execute("DELETE FROM user_pdfs WHERE user_id = ?", (user.id,))
                await db.commit()

            await register_interaction(user, context, f"Mesclou {len(rows)} PDFs")

        except Exception as e:
            logger.error(f"Erro ao mesclar PDFs para {user.id}: {e}")
            await query.edit_message_text(get_text(user, context, "pdf_merge_error"))
        return

    if action == "extract_pages":
        # Rate Limit
        if await check_ad_quota_reached(update, context, user):
            return
        remaining = check_rate_limit(user.id)
        if remaining > 0:
            await query.answer(
                get_text(user, context, "rate_limit_error", seconds=remaining),
                show_alert=True,
            )
            return
        update_rate_limit(user.id)

        # Envia mensagem de status separada em vez de editar a original
        status_msg = await query.message.reply_html(get_text(user, context, "extracting_pages"))

        try:
            pdf_file = await context.bot.get_file(file_id)
            pdf_bytes = await pdf_file.download_as_bytearray()

            loop = asyncio.get_running_loop()
            zip_bytes = await loop.run_in_executor(
                PROCESS_POOL, _extract_pdf_pages_task, bytes(pdf_bytes)
            )

            zip_buffer = io.BytesIO(zip_bytes)
            zip_buffer.name = f"pdf_pages_{user.id}.zip"

            await context.bot.send_document(
                chat_id=query.message.chat_id,
                document=zip_buffer,
                caption=get_text(user, context, "extract_pages_success"),
            )
            await status_msg.delete()
            # context.user_data.pop(f"pdf_{msg_id}", None) # Mantém o arquivo no cache para novas ações
            await register_interaction(user, context, "Extraiu páginas de PDF")

        except Exception as e:
            logger.error(f"Erro ao extrair páginas do PDF para {user.id}: {e}")
            await status_msg.edit_text(get_text(user, context, "pdf_read_error"))

    elif action == "extract_text":
        # Mostra o menu de seleção de idioma do OCR
        supported_langs = {
            "eng": "🇬🇧 English",
            "por": "🇧🇷 Português",
            "spa": "🇪🇸 Español",
            "ita": "🇮🇹 Italiano",
            "fra": "🇫🇷 Français",
            "rus": "🇷🇺 Русский",
            "ukr": "🇺🇦 Українська",
            "ara": "🇸🇦 العربية",
        }
        keyboard = []
        row_btns = []
        for code, name in supported_langs.items():
            # Adiciona o msg_id ao callback
            row_btns.append(
                InlineKeyboardButton(name, callback_data=f"pdf_ocr_lang:{code}:{msg_id}")
            )
            if len(row_btns) >= 2:
                keyboard.append(row_btns)
                row_btns = []
        if row_btns:
            keyboard.append(row_btns)

        # Envia o menu de idiomas como NOVA mensagem, preservando o PDF original
        await query.message.reply_html(
            get_text(user, context, "ocr_select_language"),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif action == "to_docx":
        # Rate Limit
        if await check_ad_quota_reached(update, context, user):
            return
        remaining = check_rate_limit(user.id)
        if remaining > 0:
            await query.answer(
                get_text(user, context, "rate_limit_error", seconds=remaining),
                show_alert=True,
            )
            return
        update_rate_limit(user.id)

        status_msg = await query.message.reply_html(
            get_text(user, context, "converting_to_docx")
        )

        try:
            pdf_file = await context.bot.get_file(file_id)
            pdf_bytes = await pdf_file.download_as_bytearray()

            loop = asyncio.get_running_loop()
            stop_spin = asyncio.Event()
            spin = asyncio.create_task(
                spinner_task(status_msg, get_text(user, context, "converting_to_docx"), stop_spin)
            )
            try:
                docx_bytes = await loop.run_in_executor(
                    PROCESS_POOL, _convert_pdf_to_docx_task, bytes(pdf_bytes)
                )
            finally:
                stop_spin.set()
                spin.cancel()

            docx_buffer = io.BytesIO(docx_bytes)
            docx_buffer.name = f"converted_{user.id}.docx"

            await context.bot.send_document(
                chat_id=query.message.chat_id,
                document=docx_buffer,
                caption=get_text(user, context, "convert_docx_success"),
            )
            await status_msg.delete()
            await register_interaction(user, context, "Converteu PDF para DOCX")

        except Exception as e:
            logger.error(f"Erro ao converter PDF para DOCX para {user.id}: {e}")
            await status_msg.edit_text(get_text(user, context, "convert_docx_error"))


async def handle_pdf_ocr_lang_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Processa a extração de texto de um PDF após a seleção do idioma."""
    query = update.callback_query
    await query.answer()
    user = query.from_user

    # Data: pdf_ocr_lang:lang_code:msg_id
    parts = query.data.split(":")
    lang_code = parts[1]
    msg_id = parts[2]

    file_id = context.user_data.get(f"pdf_{msg_id}")
    if not file_id:
        await query.edit_message_text(get_text(user, context, "session_expired"))
        return

    # Rate Limit
    if await check_ad_quota_reached(update, context, user):
        return
    remaining = check_rate_limit(user.id)
    if remaining > 0:
        await query.answer(
            get_text(user, context, "rate_limit_error", seconds=remaining),
            show_alert=True,
        )
        return
    update_rate_limit(user.id)

    await query.edit_message_text(
        get_text(user, context, "extracting_text"), parse_mode="HTML"
    )

    try:
        pdf_file = await context.bot.get_file(file_id)
        pdf_bytes = await pdf_file.download_as_bytearray()

        loop = asyncio.get_running_loop()
        full_text = await loop.run_in_executor(
            PROCESS_POOL, _extract_pdf_text_task, bytes(pdf_bytes), lang_code
        )

        await query.message.delete()
        # context.user_data.pop(f"pdf_{msg_id}", None) # Mantém o arquivo no cache
        await register_interaction(user, context, f"Extraiu texto de PDF ({lang_code})")

        if not full_text.strip():
            await query.message.reply_html(get_text(user, context, "pdf_no_text"))
        else:
            caption = get_text(user, context, "extract_text_success")
            if len(full_text) > 4000:
                f_bytes = io.BytesIO(full_text.encode("utf-8"))
                f_bytes.name = "texto_extraido_pdf.txt"
                await query.message.reply_document(document=f_bytes, caption=caption)
            else:
                await query.message.reply_html(
                    f"{caption}\n<pre>{html.escape(full_text.strip())}</pre>"
                )

    except Exception as e:
        logger.error(f"Erro ao extrair texto do PDF para {user.id}: {e}")
        await query.edit_message_text(get_text(user, context, "pdf_read_error"))


async def handle_about_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Exibe metadados do arquivo."""
    query = update.callback_query
    await query.answer()
    user = query.from_user

    # Rate Limit
    if await check_ad_quota_reached(update, context, user):
        return
    remaining = check_rate_limit(user.id)
    if remaining > 0:
        await query.answer(get_text(user, context, "rate_limit_error", seconds=remaining), show_alert=True)
        return
    update_rate_limit(user.id)

    parts = query.data.split(":")
    file_type = parts[0] # about_img ou about_pdf
    rowid = int(parts[1])

    table = "user_images" if file_type == "about_img" else "user_pdfs"

    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute(f"SELECT file_id FROM {table} WHERE rowid = ? AND user_id = ?", (rowid, user.id)) as cursor:
            row = await cursor.fetchone()

    if not row:
        await query.answer(get_text(user, context, "err_file_not_found"), show_alert=True)
        return

    try:
        f = await context.bot.get_file(row[0])
        f_bytes = await f.download_as_bytearray()

        loop = asyncio.get_running_loop()
        if file_type == "about_img":
            meta_text = await loop.run_in_executor(PROCESS_POOL, _get_image_metadata_task, bytes(f_bytes))
        else:
            meta_text = await loop.run_in_executor(PROCESS_POOL, _get_pdf_metadata_task, bytes(f_bytes))

        if not meta_text:
            meta_text = get_text(user, context, "metadata_none")

        msg_text = f"{get_text(user, context, 'metadata_title')}\n\n{meta_text}{get_text(user, context, 'metadata_footer')}"

        keyboard = [[InlineKeyboardButton(get_text(user, context, "btn_close"), callback_data="close_msg")]]
        await context.bot.send_message(chat_id=user.id, text=msg_text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

    except Exception as e:
        logger.error(f"Erro ao obter metadados: {e}")
        await query.answer(get_text(user, context, "metadata_error"), show_alert=True)


async def handle_close_msg_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fecha a mensagem atual."""
    await update.callback_query.message.delete()


def get_admin_markup(buttons=None):
    """Gera um markup de teclado inline para admin com o botão Fechar sempre incluso."""
    if buttons is None:
        buttons = []

    # Se for uma lista simples de botões, transforma em uma linha
    if buttons and not isinstance(buttons[0], list):
        # Tenta agrupar em 2 por linha se for muito longa
        if len(buttons) > 2:
            buttons = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
        else:
            buttons = [buttons]

    # Adiciona o botão fechar ao final
    buttons.append([InlineKeyboardButton("❌ Fechar", callback_data="close_msg")])
    return InlineKeyboardMarkup(buttons)


async def handle_delete_pdf_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Remove um PDF específico da lista do usuário."""
    query = update.callback_query
    user = query.from_user
    await query.answer()

    try:
        rowid = int(query.data.split(":")[1])

        async with aiosqlite.connect(DB_FILE) as db:
            # Deleta apenas se pertencer ao usuário (segurança via user_id)
            await db.execute(
                "DELETE FROM user_pdfs WHERE rowid = ? AND user_id = ?",
                (rowid, user.id),
            )
            await db.commit()

        # Atualiza a mensagem removendo o botão e confirmando a exclusão
        await query.edit_message_text(
            get_text(user, context, "pdf_deleted"), parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Erro ao deletar PDF individual: {e}")
@base_handler_checks
async def clear_all_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Exibe confirmação para limpar toda a fila (imagens e PDFs)."""
    user = update.effective_user
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM user_images WHERE user_id = ?", (user.id,)
        ) as cursor:
            img_count = (await cursor.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(*) FROM user_pdfs WHERE user_id = ?", (user.id,)
        ) as cursor:
            pdf_count = (await cursor.fetchone())[0]

    if img_count == 0 and pdf_count == 0:
        await update.message.reply_html(get_text(user, context, "cancel_empty"))
        return

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                get_text(user, context, "btn_yes"),
                callback_data="clear_all:confirm",
            ),
            InlineKeyboardButton(
                get_text(user, context, "btn_no"),
                callback_data="clear_all:cancel",
            ),
        ]
    ])
    await update.message.reply_html(
        get_text(user, context, "clear_all_confirm", img_count=img_count, pdf_count=pdf_count),
        reply_markup=keyboard,
    )


async def handle_clear_all_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Processa a confirmação/cancelamento da limpeza geral."""
    query = update.callback_query
    await query.answer()
    user = query.from_user
    action = query.data.split(":")[1]

    if action == "confirm":
        async with aiosqlite.connect(DB_FILE) as db:
            await db.execute("DELETE FROM user_images WHERE user_id = ?", (user.id,))
            await db.execute("DELETE FROM user_pdfs WHERE user_id = ?", (user.id,))
            await db.commit()
        await query.edit_message_text(
            get_text(user, context, "cancel", count=0), parse_mode="HTML"
        )
    else:
        await query.message.delete()
async def handle_move_pdf_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Move um PDF para cima ou para baixo na lista."""
    query = update.callback_query
    user = query.from_user

    parts = query.data.split(":")
    direction = parts[1]
    rowid = int(parts[2])

    async with aiosqlite.connect(DB_FILE) as db:
        # Busca todos os PDFs ordenados
        async with db.execute(
            "SELECT rowid, received_at, message_id, file_name, file_size_text FROM user_pdfs WHERE user_id = ? ORDER BY received_at ASC",
            (user.id,),
        ) as cursor:
            rows = await cursor.fetchall()

        current_idx = -1
        for i, row in enumerate(rows):
            if row[0] == rowid:
                current_idx = i
                break

        if current_idx == -1:
            await query.answer(get_text(user, context, "err_pdf_not_found"), show_alert=True)
            return

        target_idx = current_idx - 1 if direction == "up" else current_idx + 1

        if 0 <= target_idx < len(rows):
            row_current = rows[current_idx]
            row_target = rows[target_idx]

            t_current = row_current[1]
            t_target = row_target[1]

            await db.execute("UPDATE user_pdfs SET received_at = ? WHERE rowid = ?", (t_target, row_current[0]))
            await db.execute("UPDATE user_pdfs SET received_at = ? WHERE rowid = ?", (t_current, row_target[0]))

            if t_current == t_target:
                modifier = "'-1 second'" if direction == "up" else "'+1 second'"
                await db.execute(f"UPDATE user_pdfs SET received_at = datetime(received_at, {modifier}) WHERE rowid = ?", (row_current[0],))

            await db.commit()
            arrow = "🔼" if direction == "up" else "🔽"
            await query.answer(get_text(user, context, "pdf_moved", arrow=arrow), show_alert=False)

            # Atualiza o texto das mensagens para refletir a nova ordem
            # row_current agora está na posição target_idx (visual)
            # row_target agora está na posição current_idx (visual)
            # Mas os índices visuais são 1-based.

            # O item que estava em current_idx agora é o número (target_idx + 1)
            # O item que estava em target_idx agora é o número (current_idx + 1)

            items_to_update = [
                (row_current, target_idx + 1),
                (row_target, current_idx + 1)
            ]

            for row, new_count in items_to_update:
                msg_id = row[2]
                if msg_id:
                    try:
                        new_text = get_text(
                            user, context, "pdf_info",
                            name=html.escape(row[3] or "file.pdf"),
                            pages="?", # Não temos pages no DB, mantemos ? ou teríamos que salvar
                            size=row[4] or "?",
                            author="?",
                            date="?",
                            protected="?"
                        )
                        # Nota: pdf_info não tem {count}. O PDF handler não mostra "PDF 1 added".
                        # Se não mostra contagem, não precisa editar o texto para reordenar visualmente a numeração.
                        pass
                    except Exception:
                        pass
        else:
            await query.answer(get_text(user, context, "err_limit_reached"), show_alert=False)


async def handle_delete_image_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Remove uma imagem específica da lista do usuário."""
    query = update.callback_query
    user = query.from_user
    await query.answer()

    try:
        rowid = int(query.data.split(":")[1])

        async with aiosqlite.connect(DB_FILE) as db:
            # Deleta apenas se pertencer ao usuário (segurança via user_id)
            await db.execute(
                "DELETE FROM user_images WHERE rowid = ? AND user_id = ?",
                (rowid, user.id),
            )
            await db.commit()

        # Atualiza a mensagem removendo o botão e confirmando a exclusão
        await query.edit_message_text(
            get_text(user, context, "image_deleted"), parse_mode="HTML"
        )

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        PENDING_LOGS.append(
            (user.id, None, "Apagou imagem da lista", timestamp)
        )

    except Exception as e:
        logger.error(f"Erro ao deletar imagem individual: {e}")
        await query.edit_message_text(get_text(user, context, "err_delete_failed"), parse_mode="HTML")


async def handle_move_image_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Move uma imagem para cima ou para baixo na lista."""
    query = update.callback_query
    user = query.from_user

    parts = query.data.split(":")
    direction = parts[1]
    rowid = int(parts[2])

    async with aiosqlite.connect(DB_FILE) as db:
        # Busca todas as imagens ordenadas
        async with db.execute(
            "SELECT rowid, received_at, message_id, file_name, file_fmt, dimensions, file_size_text FROM user_images WHERE user_id = ? ORDER BY received_at ASC",
            (user.id,),
        ) as cursor:
            rows = await cursor.fetchall()

        current_idx = -1
        for i, row in enumerate(rows):
            if row[0] == rowid:
                current_idx = i
                break

        if current_idx == -1:
            await query.answer(get_text(user, context, "err_img_not_found"), show_alert=True)
            return

        target_idx = current_idx - 1 if direction == "up" else current_idx + 1

        if 0 <= target_idx < len(rows):
            row_current = rows[current_idx]
            row_target = rows[target_idx]

            # Troca os timestamps para reordenar
            # Se timestamps forem iguais, adiciona/subtrai 1 segundo para forçar a ordem
            t_current = row_current[1]
            t_target = row_target[1]

            # Atualiza o timestamp do alvo para o do atual e vice-versa
            await db.execute(
                "UPDATE user_images SET received_at = ? WHERE rowid = ?",
                (t_target, row_current[0]),
            )
            await db.execute(
                "UPDATE user_images SET received_at = ? WHERE rowid = ?",
                (t_current, row_target[0]),
            )

            # Correção para timestamps idênticos
            if t_current == t_target:
                modifier = "'-1 second'" if direction == "up" else "'+1 second'"
                await db.execute(
                    f"UPDATE user_images SET received_at = datetime(received_at, {modifier}) WHERE rowid = ?",
                    (row_current[0],),
                )

            await db.commit()

            arrow = "🔼" if direction == "up" else "🔽"
            await query.answer(get_text(user, context, "img_moved", arrow=arrow), show_alert=False)

            # Atualiza o texto das mensagens para refletir a nova ordem (Numeração)
            # row_current (que estava em current_idx) foi para target_idx. Nova posição: target_idx + 1
            # row_target (que estava em target_idx) foi para current_idx. Nova posição: current_idx + 1

            items_to_update = [
                (row_current, target_idx + 1),
                (row_target, current_idx + 1)
            ]

            for row, new_count in items_to_update:
                msg_id = row[2]
                if msg_id:
                    try:
                        # Reconstrói o texto com o novo número
                        # row structure: 0:rowid, 1:received_at, 2:message_id, 3:file_name, 4:file_fmt, 5:dims, 6:size
                        new_text = get_text(
                            user,
                            context,
                            "image_sequence",
                            count=new_count,
                            name=html.escape(row[3] or "Foto"),
                            format=row[4] or "JPEG",
                            dims=row[5] or "?",
                            size=row[6] or "?"
                        )
                        # Mantém o teclado original (não temos como pegar o markup atual facilmente sem fazer outra chamada, mas edit_message_text mantém se não passar reply_markup? Não, remove. Precisamos reconstruir o markup.)
                        # O markup depende do rowid, que temos.
                        keyboard_update = [
                            [
                                InlineKeyboardButton("🔼", callback_data=f"move:up:{row[0]}"),
                                InlineKeyboardButton("🔽", callback_data=f"move:down:{row[0]}"),
                            ],
                            [
                                InlineKeyboardButton(
                                    get_text(user, context, "btn_about"), callback_data=f"about_img:{row[0]}"
                                ),
                                InlineKeyboardButton(
                                    get_text(user, context, "btn_delete"), callback_data=f"del_img:{row[0]}"
                                )
                            ],
                        ]
                        await context.bot.edit_message_text(
                            chat_id=user.id,
                            message_id=msg_id,
                            text=new_text,
                            parse_mode="HTML",
                            reply_markup=InlineKeyboardMarkup(keyboard_update)
                        )
                    except Exception as e:
                        logger.error(f"Erro ao atualizar texto da mensagem {msg_id} após mover: {e}")
        else:
            await query.answer(get_text(user, context, "err_limit_reached"), show_alert=False)


async def handle_read_qr_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Lê o conteúdo de um QR Code detectado na imagem."""
    query = update.callback_query
    await query.answer()
    user = query.from_user

    parts = query.data.split(":")
    rowid = int(parts[1])

    # Recupera o conteúdo do QR Code do contexto do usuário
    qr_content = context.user_data.get(f"qr_content_{rowid}")

    if not qr_content:
        await query.message.reply_text(
            get_text(user, context, "qr_read_error")
        )
        return

    # Envia o conteúdo do QR Code
    await query.message.reply_html(
        get_text(user, context, "qr_read_success", content=qr_content)
    )


async def handle_video_to_gif_confirm_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Confirma a conversão de vídeo para GIF."""
    query = update.callback_query
    await query.answer()
    user = query.from_user

    parts = query.data.split(":")
    file_id = parts[1]
    file_type = parts[2]

    # Armazena o file_id para processamento
    context.user_data["pending_video_file_id"] = file_id
    context.user_data["pending_video_type"] = file_type

    # Tenta deletar a mensagem de confirmação
    try:
        await query.message.delete()
    except Exception:
        pass

    # Envia mensagem de processamento
    status_msg = await context.bot.send_message(
        chat_id=user.id,
        text=get_text(user, context, "gif_generating")
    )

    # Inicia o spinner
    stop_spin = asyncio.Event()
    spin_task = asyncio.create_task(
        spinner_task(status_msg, get_text(user, context, "gif_generating"), stop_spin)
    )

    try:
        # Baixa o arquivo
        new_file = await context.bot.get_file(file_id)

        if file_type == "video":
            # Baixa para arquivo temporário pois OpenCV precisa de path
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_vid:
                await new_file.download_to_drive(tmp_vid.name)
                tmp_vid_path = tmp_vid.name

            settings = context.user_data.get("gif_settings", GIF_DEFAULTS)
            loop = asyncio.get_running_loop()

            try:
                gif_bytes = await loop.run_in_executor(
                    PROCESS_POOL, _video_to_gif_task, tmp_vid_path, settings["fps"], settings["scale"]
                )

                if len(gif_bytes) > 50 * 1024 * 1024:
                    await context.bot.send_message(
                        chat_id=user.id,
                        text=get_text(user, context, "gif_too_large", size=_format_size(len(gif_bytes)))
                    )
                    return

                f_io = io.BytesIO(gif_bytes)
                f_io.name = "converted.gif"
                await context.bot.send_animation(
                    chat_id=user.id,
                    animation=f_io,
                    caption=get_text(user, context, "gif_success")
                )

                # Registra apenas a ação, sem compartilhar o GIF com o administrador.

                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                PENDING_LOGS.append((user.id, None, "gif_created_from_video", timestamp))
            finally:
                if os.path.exists(tmp_vid_path):
                    os.remove(tmp_vid_path)

        # Limpa estado
        context.user_data.pop("pending_video_file_id", None)
        context.user_data.pop("pending_video_type", None)
        context.user_data["state"] = None

        # Para spinner e remove mensagem
        stop_spin.set()
        await spin_task
        try:
            await status_msg.delete()
        except Exception:
            pass

    except Exception as e:
        logger.error(f"Erro ao converter vídeo para GIF: {e}")
        stop_spin.set()
        try:
            await spin_task
        except Exception:
            pass
        await context.bot.send_message(
            chat_id=user.id,
            text=get_text(user, context, "gif_error")
        )


async def handle_video_to_gif_cancel_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Cancela a conversão de vídeo para GIF."""
    query = update.callback_query
    await query.answer()
    user = query.from_user

    # Limpa estado
    context.user_data.pop("pending_video_file_id", None)
    context.user_data.pop("pending_video_type", None)
    context.user_data["state"] = None

    # Tenta deletar a mensagem
    try:
        await query.message.delete()
    except Exception:
        pass

    await context.bot.send_message(
        chat_id=user.id,
        text=get_text(user, context, "cancel", count=0)
    )


@base_handler_checks
async def merge_vertically_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Une as imagens verticalmente."""
    await process_merge(update, context, "vertical")


@base_handler_checks
async def merge_horizontally_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Une as imagens horizontalmente."""
    await process_merge(update, context, "horizontal")


@base_handler_checks
async def tools_menu_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Exibe o menu de ferramentas."""
    user = update.effective_user
    await register_interaction(user, context, "Abriu menu de ferramentas")
    msg = get_text(user, context, "tools_menu_title")
    reply_markup = get_tools_menu_keyboard(user, context)

    if update.callback_query:
        # Quando vem de um InlineKeyboardMarkup (como o menu de marca d'água),
        # precisamos excluir a mensagem anterior e enviar uma nova
        # para que o ReplyKeyboardMarkup (teclado fixo) funcione corretamente.
        await update.callback_query.message.delete()
        await context.bot.send_message(
            chat_id=user.id,
            text=msg,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode="HTML")


@base_handler_checks
async def other_bots_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Exibe informações sobre outros bots do desenvolvedor."""
    user = update.effective_user
    await register_interaction(user, context, "Visualizou outros bots")
    msg = get_text(user, context, "other_bots_msg")
    keyboard = [
        [
            InlineKeyboardButton(
                get_text(user, context, "btn_martiancat"),
                url="https://martiancat.space",
            )
        ],
        [
            InlineKeyboardButton(
                get_text(user, context, "btn_everydaycrypto"),
                url="https://t.me/EverydayCryptoBot",
            )
        ],
    ]
    await update.message.reply_html(msg, reply_markup=InlineKeyboardMarkup(keyboard))


@base_handler_checks
async def my_usage_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Exibe estatísticas de uso do usuário."""
    user = update.effective_user
    await register_interaction(user, context, "Verificou estatísticas de uso")

    status_msg = await update.message.reply_html(
        get_text(user, context, "generating_stats")
    )

    stats = {
        "horizontal": 0,
        "vertical": 0,
        "grid": 0,
        "pdf": 0,
        "converted": 0,
        "compressed": 0,
        "metadata": 0,
        "ocr": 0,
        "docx": 0,
        "zip": 0,
        "gif": 0,
        "meme": 0,
        "bg_removed": 0,
        "search": 0,
    }

    rank = 0
    daily_data = {}
    command_data = {}

    async with aiosqlite.connect(DB_FILE) as db:
        # 1. Contagem por tipo (Lógica existente)
        async with db.execute(
            "SELECT action, COUNT(*) FROM activity_logs WHERE user_id = ? GROUP BY action",
            (user.id,),
        ) as cursor:
            rows = await cursor.fetchall()

        # 2. Ranking
        # Conta quantos usuários têm mais interações que o atual
        async with db.execute(
            """
            SELECT COUNT(*) + 1
            FROM (
                SELECT user_id, COUNT(*) as cnt
                FROM activity_logs
                GROUP BY user_id
            )
            WHERE cnt > (
                SELECT COUNT(*)
                FROM activity_logs
                WHERE user_id = ?
            )
        """,
            (user.id,),
        ) as cursor:
            rank_row = await cursor.fetchone()
            rank = rank_row[0] if rank_row else 0

        # 3. Dados para Gráfico Diário (30 dias)
        async with db.execute(
            """
            SELECT DATE(timestamp) as day, COUNT(*)
            FROM activity_logs
            WHERE user_id = ? AND timestamp >= datetime('now', '-30 days')
            GROUP BY day
        """,
            (user.id,),
        ) as cursor:
            daily_rows = await cursor.fetchall()
            daily_data = {row[0]: row[1] for row in daily_rows}

    # 1.1 Contagem Total de Interações (Dados Brutos)
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM activity_logs WHERE user_id = ?", (user.id,)
        ) as cursor:
            total_interactions = (await cursor.fetchone())[0]

    stats["total_interactions"] = total_interactions

    for action, count in rows:
        # Stats Text
        if action == "merge_horizontal":
            stats["horizontal"] += count
        elif action == "merge_vertical":
            stats["vertical"] += count
        elif action == "merge_grid":
            stats["grid"] += count
        elif action == "pdf_created":
            stats["pdf"] += count
        elif action == "compression_created":
            stats["compressed"] += count
        elif action == "metadata_removed":
            stats["metadata"] += count
        elif action and action.startswith("Converteu de"):
            stats["converted"] += count
        elif action and action.startswith("ocr_"):
            stats["ocr"] += count
        elif action and (
            action.startswith("Converteu PDF para DOCX")
            or action.startswith("Converteu DOCX para PDF")
            or action.startswith("Extraiu páginas de DOCX")
            or action.startswith("enviou um DOCX")
        ):
            stats["docx"] += count
        elif action == "zip_queue":
            stats["zip"] += count
        elif action == "bg_removed":
            stats["bg_removed"] += count
        elif action in ["gif_created_from_images", "gif_created_from_video", "video_created_from_gif"]:
            stats["gif"] += count
        elif action == "meme_created":
            stats["meme"] += count
        elif action == "search_img":
            stats["search"] += count

        # Chart Data Mapping
        key = None
        if action.startswith("merge_vertical"):
            key = get_text(user, context, "chart_label_merge_vert")
        elif action.startswith("merge_horizontal"):
            key = get_text(user, context, "chart_label_merge_horiz")
        elif action.startswith("merge_grid"):
            key = get_text(user, context, "chart_label_grid")
        elif action == "pdf_created":
            key = get_text(user, context, "chart_label_pdf")
        elif action == "compression_created":
            key = get_text(user, context, "chart_label_compression")
        elif action == "metadata_removed":
            key = get_text(user, context, "chart_label_metadata")
        elif action == "zip_queue":
            key = get_text(user, context, "chart_label_zip")
        elif action.startswith("ocr_"):
            key = get_text(user, context, "chart_label_ocr")
        elif "Converteu de" in action:
            key = get_text(user, context, "chart_label_converter")
        elif action in ["gif_created_from_images", "gif_created_from_video", "video_created_from_gif"]:
            key = get_text(user, context, "chart_label_gif_video")
        elif action == "meme_created":
            key = get_text(user, context, "chart_label_meme")
        elif action == "search_img":
            key = get_text(user, context, "chart_label_search")

        if key:
            if key in command_data:
                command_data[key] += count
            else:
                command_data[key] = count

    msg = get_text(user, context, "my_usage_msg", **stats)
    msg += get_text(user, context, "rank_msg", rank=rank)

    # Botão de apoio/contribuição
    keyboard_usage = [
        [
            InlineKeyboardButton(
                get_text(user, context, "menu_contribute"), callback_data="contribute:menu"
            )
        ]
    ]
    reply_markup_usage = InlineKeyboardMarkup(keyboard_usage)

    # Gera gráficos
    loop = asyncio.get_running_loop()
    try:
        if not command_data and not daily_data:
            # Se não tiver dados suficientes para gráfico, manda só texto com teclado
            await status_msg.edit_text(msg, parse_mode="HTML", reply_markup=reply_markup_usage)
            return

        labels = {
            "chart_title_my_30d": get_text(user, context, "chart_title_my_30d"),
            "chart_actions": get_text(user, context, "chart_actions"),
            "chart_title_my_commands": get_text(
                user, context, "chart_title_my_commands"
            ),
            "chart_total": get_text(user, context, "chart_total"),
        }
        image_bytes = await loop.run_in_executor(
            PROCESS_POOL,
            _generate_my_usage_charts_task,
            daily_data,
            command_data,
            labels,
        )

        await update.message.reply_photo(
            photo=image_bytes, caption=msg, parse_mode="HTML", reply_markup=reply_markup_usage
        )
        await status_msg.delete()
    except Exception as e:
        logger.error(f"Erro ao gerar gráficos de uso pessoal: {e}")
        await status_msg.edit_text(msg, parse_mode="HTML", reply_markup=reply_markup_usage)


@base_handler_checks
async def back_to_main_menu_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Retorna ao menu principal."""
    # Reutiliza a lógica de mostrar o menu inicial
    await show_start_menu(update, context)


@base_handler_checks
async def grid_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Inicia o processo de criação de grade, perguntando o número de colunas."""
    user = update.effective_user
    # Verifica se tem imagens suficientes antes de mostrar o menu
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM user_images WHERE user_id = ?", (user.id,)
        ) as cursor:
            count = (await cursor.fetchone())[0]

    if count < 2:
        await update.message.reply_text(get_text(user, context, "need_more_images"))
        return

    keyboard = [
        [
            InlineKeyboardButton("2", callback_data="grid_cols:2"),
            InlineKeyboardButton("3", callback_data="grid_cols:3"),
        ],
        [
            InlineKeyboardButton("4", callback_data="grid_cols:4"),
            InlineKeyboardButton("5", callback_data="grid_cols:5"),
        ],
        [
            InlineKeyboardButton(
                get_text(user, context, "menu_cancel"),
                callback_data="settings_nav:close",
            )
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        get_text(user, context, "grid_select_columns"), reply_markup=reply_markup
    )


@base_handler_checks
async def handle_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Identifica stickers e oferece conversão."""
    user = update.effective_user
    sticker = update.message.sticker
    # Filtra stickers animados ou de vídeo (não suportados pelo PIL diretamente)
    if sticker.is_animated or sticker.is_video:
        await update.message.reply_html(
            get_text(user, context, "sticker_not_supported")
        )
        return

    # Salva o file_id associado à mensagem para recuperação no callback
    # Usamos o message_id como chave para permitir múltiplos stickers
    context.user_data[f"sticker_{update.message.message_id}"] = sticker.file_id

    keyboard = [
        [
            InlineKeyboardButton(
                get_text(user, context, "sticker_convert_btn_png"),
                callback_data=f"sticker_convert:png:{update.message.message_id}",
            ),
            InlineKeyboardButton(
                get_text(user, context, "sticker_convert_btn_webp"),
                callback_data=f"sticker_convert:webp:{update.message.message_id}",
            ),
            InlineKeyboardButton(
                get_text(user, context, "sticker_convert_btn_jpg"),
                callback_data=f"sticker_convert:jpg:{update.message.message_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                get_text(user, context, "menu_cancel"),
                callback_data=f"sticker_convert:cancel:{update.message.message_id}",
            )
        ],
    ]

    await update.message.reply_html(
        get_text(user, context, "sticker_detected"),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


def _convert_sticker_task(
    image_bytes: bytes, target_format: str, bg_color: str = "WHITE"
) -> bytes:
    """Converte bytes de sticker (WEBP) para PNG, WEBP ou JPG."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
    except Image.DecompressionBombError as e:
        logger.error(f"Ataque de Decompression Bomb detectado em _convert_sticker_task: {e}")
        raise ValueError(
            "O sticker é uma 'bomba de descompressão' e não pode ser processado."
        ) from e
    out = io.BytesIO()

    save_format = target_format.upper()
    if save_format == "JPG":
        save_format = "JPEG"

    if save_format == "JPEG":
        # Create background
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        bg_tuple = (255, 255, 255)
        if bg_color in COLORS:
            bg_tuple = COLORS[bg_color][1]
        elif bg_color.startswith("#"):
            try:
                h = bg_color.lstrip("#")
                bg_tuple = tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))
            except:
                pass
        elif "," in bg_color:
            try:
                bg_tuple = tuple(map(int, bg_color.split(",")))
            except:
                pass

        bg = Image.new("RGB", img.size, bg_tuple)
        bg.paste(img, mask=img.split()[3])
        img = bg

    img.save(out, format=save_format)
    return out.getvalue()


async def handle_sticker_convert_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Processa a conversão do sticker."""
    query = update.callback_query
    await query.answer()
    user = query.from_user

    # data: sticker_convert:fmt:msg_id
    parts = query.data.split(":")
    target_fmt = parts[1]
    msg_id = parts[2]

    if target_fmt == "cancel":
        context.user_data.pop(f"sticker_{msg_id}", None)
        await query.message.delete()
        return

    file_id = context.user_data.get(f"sticker_{msg_id}")
    if not file_id:
        await query.edit_message_text(get_text(user, context, "session_expired"))
        return

    bg_color = "WHITE"
    if target_fmt.lower() == "jpg":
        async with aiosqlite.connect(DB_FILE) as db:
            async with db.execute(
                "SELECT background_color FROM users WHERE user_id = ?", (user.id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row and row[0]:
                    bg_color = row[0]

    await query.edit_message_text(
        get_text(user, context, "processing", count=1, direction=target_fmt)
    )

    try:
        new_file = await context.bot.get_file(file_id)
        f_bytes = await new_file.download_as_bytearray()

        loop = asyncio.get_running_loop()
        converted_bytes = await loop.run_in_executor(
            PROCESS_POOL, _convert_sticker_task, bytes(f_bytes), target_fmt, bg_color
        )

        f_io = io.BytesIO(converted_bytes)
        f_io.name = f"sticker_{user.id}.{target_fmt}"

        caption_key = "sticker_converted"
        if target_fmt.lower() == "webp":
            caption_key = "sticker_file_caption"

        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=f_io,
            caption=get_text(user, context, caption_key),
            parse_mode="HTML",
        )

        # Log
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        PENDING_LOGS.append(
            (user.id, None, f"sticker_converted_{target_fmt}", timestamp)
        )

        # Cleanup
        context.user_data.pop(f"sticker_{msg_id}", None)
        await query.message.delete()

    except Exception as e:
        logger.error(f"Erro ao converter sticker: {e}")
        await query.message.edit_text(get_text(user, context, "sticker_error"))


@base_handler_checks
async def sticker_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Converte imagens da fila em stickers."""
    user = update.effective_user

    # Rate Limit
    if await check_ad_quota_reached(update, context, user):
        return
    remaining = check_rate_limit(user.id)
    if remaining > 0:
        await update.message.reply_text(
            get_text(user, context, "rate_limit_error", seconds=remaining)
        )
        return
    update_rate_limit(user.id)

    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute(
            "SELECT file_id FROM user_images WHERE user_id = ? ORDER BY received_at ASC",
            (user.id,),
        )
        rows = await cursor.fetchall()

    if not rows:
        await update.message.reply_text(get_text(user, context, "need_one_image"))
        return

    await update.message.reply_text(
        get_text(user, context, "sticker_processing_batch", count=len(rows))
    )

    tasks = [context.bot.get_file(row[0]) for row in rows]
    files = await asyncio.gather(*tasks)
    content_tasks = [f.download_as_bytearray() for f in files]
    image_contents = await asyncio.gather(*content_tasks)

    loop = asyncio.get_running_loop()

    for i, content in enumerate(image_contents):
        try:
            sticker_bytes = await loop.run_in_executor(
                PROCESS_POOL, _create_sticker_task, bytes(content)
            )
            f_io = io.BytesIO(sticker_bytes)
        except ValueError as e: # Captura o erro da Decompression Bomb
            await context.bot.send_message(
                chat_id=user.id,
                text=f"❌ Erro ao processar imagem {i+1}: {e}",
                parse_mode="HTML",
            )
            continue
        except Exception as e:
            logger.error(f"Erro ao criar sticker para user {user.id}: {e}")
            continue

        f_io.name = f"sticker_{i + 1}.webp"

        await context.bot.send_document(
            chat_id=user.id,
            document=f_io,
            caption=get_text(user, context, "sticker_file_caption"),
            parse_mode="HTML",
        )

    # Clear queue
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("DELETE FROM user_images WHERE user_id = ?", (user.id,))
        await db.commit()


# Constantes para o estado de conversation do QR Code
QRCODE_WAITING_TEXT = "WAITING_QRCODE_TEXT"
QRCODE_WAITING_EXTRA_TEXT = "WAITING_QRCODE_EXTRA_TEXT"


def _generate_qrcode_task(text: str, extra_text: str = None) -> bytes:
    """Gera um QR Code a partir do texto (executado em processo separado)."""
    import qrcode
    from PIL import Image

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(text)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # Se há texto extra, adicionar um rodapé com o texto
    if extra_text:
        # Converter para RGB se necessário
        if img.mode != 'RGB':
            img = img.convert('RGB')

        # Criar imagem maior para o texto
        text_height = 50
        new_height = img.height + text_height
        new_img = Image.new('RGB', (img.width, new_height), 'white')
        new_img.paste(img, (0, 0))

        # Adicionar texto na parte inferior
        from PIL import ImageDraw, ImageFont
        draw = ImageDraw.Draw(new_img)

        # Tentar usar uma fonte padrão, mas se não funcionar, usar padrão
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
        except:
            font = ImageFont.load_default()

        # Centralizar o texto
        text_width = draw.textlength(extra_text, font=font) if hasattr(draw, 'textlength') else len(extra_text) * 8
        text_x = (img.width - text_width) // 2
        draw.text((text_x, img.height + 15), extra_text, fill='black', font=font)

        img = new_img

    output = io.BytesIO()
    img.save(output, format="PNG")
    return output.getvalue()


@base_handler_checks
async def qrcode_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Inicia o processo de geração de QR Code, pedindo o texto/link."""
    user = update.effective_user

    # Rate Limit
    if await check_ad_quota_reached(update, context, user):
        return
    remaining = check_rate_limit(user.id)
    if remaining > 0:
        await update.message.reply_text(
            get_text(user, context, "rate_limit_error", seconds=remaining)
        )
        return
    update_rate_limit(user.id)

    # A notificação ao admin será enviada após a geração da imagem nos handlers específicos

    # Define o estado para esperar o texto
    context.user_data["state"] = QRCODE_WAITING_TEXT

    await update.message.reply_html(get_text(user, context, "qrcode_enter_text"))


async def handle_qrcode_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Processa o texto digitado pelo usuário para gerar QR Code."""
    user = update.effective_user
    text = update.message.text

    if context.user_data.get("state") != QRCODE_WAITING_TEXT:
        return

    if not text or len(text.strip()) == 0:
        await update.message.reply_html(get_text(user, context, "qrcode_enter_text"))
        return

    # Limpa o estado
    context.user_data.pop("state", None)

    # Gera o QR Code
    status_msg = await update.message.reply_html(get_text(user, context, "qrcode_generating"))

    try:
        loop = asyncio.get_running_loop()
        qr_bytes = await loop.run_in_executor(
            PROCESS_POOL, _generate_qrcode_task, text.strip()
        )

        await register_interaction(user, context, "Gerou QR Code")

        # Envia o QR Code com botão para adicionar texto
        qr_io = io.BytesIO(qr_bytes)
        qr_io.name = "qrcode.png"

        keyboard = [
            [InlineKeyboardButton(
                get_text(user, context, "qrcode_add_text"),
                callback_data=f"qrcode_add_text:{update.message.message_id}"
            )]
        ]

        # Salva o texto original no contexto para uso posterior
        context.user_data[f"qrcode_original_text_{update.message.message_id}"] = text.strip()

        await status_msg.delete()
        await update.message.reply_photo(
            photo=qr_io,
            caption=get_text(user, context, "qrcode_success", content=text.strip()),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        logger.error(f"Erro ao gerar QR Code para {user.id}: {e}")
        await status_msg.edit_text(get_text(user, context, "qrcode_error"))


async def handle_qrcode_add_text_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Processa o callback para adicionar texto ao QR Code."""
    query = update.callback_query
    await query.answer()
    user = query.from_user

    # Extrai o message_id do callback
    parts = query.data.split(":")
    if len(parts) < 2:
        return

    original_msg_id = parts[1]
    original_text = context.user_data.get(f"qrcode_original_text_{original_msg_id}")

    if not original_text:
        await query.edit_message_text(get_text(user, context, "session_expired"))
        return

    # Define o estado para esperar o texto adicional
    context.user_data["state"] = QRCODE_WAITING_EXTRA_TEXT
    context.user_data["qrcode_msg_id"] = original_msg_id

    await query.message.reply_html(get_text(user, context, "qrcode_enter_extra_text"))


async def handle_qrcode_extra_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Processa o texto adicional digitado pelo usuário para gerar novo QR Code."""
    user = update.effective_user
    text = update.message.text

    if context.user_data.get("state") != QRCODE_WAITING_EXTRA_TEXT:
        return

    if not text or len(text.strip()) == 0:
        await update.message.reply_html(get_text(user, context, "qrcode_enter_extra_text"))
        return

    # Recupera o texto original
    msg_id = context.user_data.get("qrcode_msg_id")
    original_text = context.user_data.get(f"qrcode_original_text_{msg_id}")

    if not original_text:
        await update.message.reply_html(get_text(user, context, "session_expired"))
        return

    # Limpa o estado
    context.user_data.pop("state", None)
    context.user_data.pop("qrcode_msg_id", None)

    # Gera o QR Code com texto adicional
    status_msg = await update.message.reply_html(get_text(user, context, "qrcode_generating_with_text"))

    try:
        loop = asyncio.get_running_loop()
        qr_bytes = await loop.run_in_executor(
            PROCESS_POOL, _generate_qrcode_task, original_text, text.strip()
        )

        await register_interaction(user, context, "Gerou QR Code com texto extra")

        # Envia o novo QR Code
        qr_io = io.BytesIO(qr_bytes)
        qr_io.name = "qrcode.png"

        await status_msg.delete()
        await update.message.reply_photo(
            photo=qr_io,
            caption=get_text(user, context, "qrcode_success", content=original_text),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Erro ao gerar QR Code com texto para {user.id}: {e}")
        await status_msg.edit_text(get_text(user, context, "qrcode_error"))


def _create_sticker_task(image_bytes: bytes) -> bytes:
    """Redimensiona imagem para formato de sticker (512x512 max) e converte para WEBP."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
    except Image.DecompressionBombError as e:
        logger.error(f"Ataque de Decompression Bomb detectado em _create_sticker_task: {e}")
        raise ValueError(
            "A imagem é uma 'bomba de descompressão' e não pode ser processada."
        ) from e

    out = io.BytesIO()
    img.save(out, format="WEBP")
    return out.getvalue()


async def _get_settings_text_and_markup(
    user: User, context: ContextTypes.DEFAULT_TYPE
) -> tuple[str, InlineKeyboardMarkup]:
    """Helper para buscar as configurações do usuário e construir a mensagem de configurações."""
    # Valores padrão
    user_settings = {
        "format": "JPEG",
        "quality": 100,
        "background": "WHITE",
        "resize": 1,
        "border_width": 0,
        "border_color": "WHITE",
    }
    merged_count = 0

    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute(
            "SELECT output_format, compression_quality, background_color, auto_resize, border_width, border_color FROM users WHERE user_id = ?",
            (user.id,),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                user_settings["format"] = row[0] or "JPEG"
                user_settings["quality"] = row[1] or 100
                user_settings["background"] = row[2] or "WHITE"
                user_settings["resize"] = (
                    row[3] if len(row) > 3 and row[3] is not None else 1
                )
                user_settings["border_width"] = (
                    row[4] if len(row) > 4 and row[4] is not None else 0
                )
                user_settings["border_color"] = (
                    row[5] if len(row) > 5 and row[5] is not None else "WHITE"
                )

        # Conta quantas vezes o usuário já unificou imagens
        async with db.execute(
            "SELECT COUNT(*) FROM activity_logs WHERE user_id = ? AND action LIKE 'merge_%'",
            (user.id,),
        ) as cursor_count:
            row_count = await cursor_count.fetchone()
            if row_count:
                merged_count = row_count[0]

    resize_text = (
        get_text(user, context, "resize_yes")
        if user_settings["resize"]
        else get_text(user, context, "resize_no")
    )
    resize_icon = "✅" if user_settings["resize"] else "❌"
    resize_btn_text = f"{resize_icon} {get_text(user, context, 'settings_btn_resize')}"

    borders_text = f"{user_settings['border_width']}px, {user_settings['border_color']}"

    text = get_text(
        user,
        context,
        "settings_title",
        format=user_settings["format"],
        quality=user_settings["quality"],
        background=user_settings["background"],
        resize=resize_text,
        borders=borders_text,
        merged_count=merged_count,
    )

    keyboard = [
        [
            InlineKeyboardButton(
                get_text(user, context, "settings_btn_format"),
                callback_data="settings_nav:format",
            ),
            InlineKeyboardButton(
                get_text(user, context, "settings_btn_quality"),
                callback_data="settings_nav:quality",
            ),
        ],
        [
            InlineKeyboardButton(
                get_text(user, context, "settings_btn_bgcolor"),
                callback_data="settings_nav:bgcolor",
            ),
            InlineKeyboardButton(
                get_text(user, context, "settings_btn_language"),
                callback_data="settings_nav:language",
            ),
        ],
        [
            InlineKeyboardButton(resize_btn_text, callback_data="set_resize:toggle"),
            InlineKeyboardButton(
                get_text(user, context, "settings_btn_borders"),
                callback_data="settings_nav:borders",
            ),
        ],
        [
            InlineKeyboardButton(
                get_text(user, context, "btn_ok"), callback_data="settings_nav:close"
            )
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    return text, reply_markup


@base_handler_checks
async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Exibe o menu de configurações."""
    user = update.effective_user
    await register_interaction(
        user, context, "Abriu as configurações (/settings)", is_settings_change=True
    )
    text, reply_markup = await _get_settings_text_and_markup(user, context)
    await update.message.reply_html(text, reply_markup=reply_markup)


async def handle_settings_navigation(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Lida com a navegação no menu de configurações."""
    query = update.callback_query
    await query.answer()
    user = query.from_user

    action = query.data.split(":")[1]

    if action == "main":
        text, reply_markup = await _get_settings_text_and_markup(user, context)
        if query.message.photo or query.message.document:
            await query.message.delete()
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=text,
                parse_mode="HTML",
                reply_markup=reply_markup,
            )
        else:
            await query.edit_message_text(
                text, parse_mode="HTML", reply_markup=reply_markup
            )

    elif action == "format":
        current_fmt = "JPEG"
        async with aiosqlite.connect(DB_FILE) as db:
            async with db.execute(
                "SELECT output_format FROM users WHERE user_id = ?", (user.id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row and row[0]:
                    current_fmt = row[0]

        keyboard = [
            [
                InlineKeyboardButton("PNG", callback_data="set_fmt:PNG"),
                InlineKeyboardButton("JPG", callback_data="set_fmt:JPG"),
            ],
            [
                InlineKeyboardButton("WEBP", callback_data="set_fmt:WEBP"),
                InlineKeyboardButton("BMP", callback_data="set_fmt:BMP"),
            ],
            [
                InlineKeyboardButton("TIFF", callback_data="set_fmt:TIFF"),
                InlineKeyboardButton("GIF", callback_data="set_fmt:GIF"),
            ],
            [
                InlineKeyboardButton(
                    get_text(user, context, "btn_back"),
                    callback_data="settings_nav:main",
                )
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        msg = get_text(user, context, "format_choose", current=current_fmt)
        await query.edit_message_text(msg, parse_mode="HTML", reply_markup=reply_markup)

    elif action == "quality":
        current_quality = 100
        async with aiosqlite.connect(DB_FILE) as db:
            async with db.execute(
                "SELECT compression_quality FROM users WHERE user_id = ?", (user.id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row and row[0]:
                    current_quality = row[0]

            # await db.execute("UPDATE users SET current_state = 'WAITING_QUALITY' WHERE user_id = ?", (user.id,))
            context.user_data["state"] = "WAITING_QUALITY"

        msg = get_text(user, context, "quality_prompt", current=current_quality)
        await query.edit_message_text(msg, parse_mode="HTML")

    elif action == "bgcolor":
        current_bg = "WHITE"
        async with aiosqlite.connect(DB_FILE) as db:
            async with db.execute(
                "SELECT background_color FROM users WHERE user_id = ?", (user.id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row and row[0]:
                    current_bg = row[0]

        keyboard = [
            [
                InlineKeyboardButton("⚪️ White", callback_data="set_bg:WHITE"),
                InlineKeyboardButton("⚫️ Black", callback_data="set_bg:BLACK"),
            ],
            [
                InlineKeyboardButton(
                    get_text(user, context, "btn_back"),
                    callback_data="settings_nav:main",
                )
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        msg = get_text(user, context, "bgcolor_prompt", current=current_bg)
        await query.edit_message_text(msg, parse_mode="HTML", reply_markup=reply_markup)

    elif action == "language":
        # Mapa de códigos para nomes de exibição
        lang_map = {
            "en": "English",
            "pt": "Português",
            "es": "Español",
            "ru": "Русский",
            "it": "Italiano",
            "fr": "Français",
        }

        # Determina o idioma atual (já processado pelo ensure_custom_language)
        code = user.language_code.split("-")[0] if user.language_code else "en"
        current_lang = lang_map.get(code, "English")

        # Obtém botões de idioma e adiciona o botão de voltar
        keyboard = get_language_buttons("set_lang")
        keyboard.append(
            [
                InlineKeyboardButton(
                    get_text(user, context, "btn_back"),
                    callback_data="settings_nav:main",
                )
            ]
        )
        reply_markup = InlineKeyboardMarkup(keyboard)
        msg = get_text(user, context, "language_choose", current=current_lang)
        await query.edit_message_text(msg, parse_mode="HTML", reply_markup=reply_markup)

    elif action == "borders":
        # Fetch current border settings
        border_width = 0
        border_color = "WHITE"
        async with aiosqlite.connect(DB_FILE) as db:
            async with db.execute(
                "SELECT border_width, border_color FROM users WHERE user_id = ?",
                (user.id,),
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    border_width = row[0] if row[0] is not None else 0
                    border_color = row[1] or "WHITE"

        keyboard = [
            [
                InlineKeyboardButton(
                    get_text(user, context, "borders_btn_width"),
                    callback_data="borders_nav:width",
                ),
                InlineKeyboardButton(
                    get_text(user, context, "borders_btn_color"),
                    callback_data="borders_nav:color",
                ),
            ],
            [
                InlineKeyboardButton(
                    get_text(user, context, "btn_back"),
                    callback_data="settings_nav:main",
                )
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        msg = get_text(
            user, context, "borders_title", width=border_width, color=border_color
        )
        await query.edit_message_text(msg, parse_mode="HTML", reply_markup=reply_markup)

    elif action == "close":
        settings_changes = context.user_data.get("settings_changes", [])
        language_changed = any("Idioma para" in change for change in settings_changes)

        await flush_settings_notifications(user, context)
        try:
            await query.message.delete()
        except Exception:
            # Se a mensagem for muito antiga para deletar, apenas remove os botões
            await query.edit_message_reply_markup(reply_markup=None)

        if language_changed:
            await query.message.reply_text(
                get_text(user, context, "language_update_hint")
            )

async def _get_watermark_settings_text_and_markup(user, context):
    """Gera o texto e o teclado do menu de configurações da marca d'água."""
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute(
            "SELECT watermark_enabled, watermark_text, watermark_size, watermark_color, watermark_position, watermark_margin FROM users WHERE user_id = ?",
            (user.id,),
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                # Se o usuário não existir no banco, usamos valores padrão
                enabled, text, size, color, pos, margin = 0, "UnifyImages", 30, "WHITE", "bottom_right", 20
            else:
                enabled, text, size, color, pos, margin = row

    status_label = get_text(user, context, "watermark_enabled_label" if enabled else "watermark_disabled_label")
    toggle_icon = "✅" if enabled else "❌"

    # Mapeamento de posição para texto localizado
    pos_map = {
        "top_left": "watermark_pos_tl", "top_center": "watermark_pos_tc", "top_right": "watermark_pos_tr",
        "middle_left": "watermark_pos_ml", "middle_center": "watermark_pos_mc", "middle_right": "watermark_pos_mr",
        "bottom_left": "watermark_pos_bl", "bottom_center": "watermark_pos_bc", "bottom_right": "watermark_pos_br"
    }
    pos_label = get_text(user, context, pos_map.get(pos, "watermark_pos_br"))
    color_label = COLORS.get(color, ("⚪️ White", (255, 255, 255)))[0]

    msg = get_text(
        user, context, "watermark_settings_title",
        status=status_label, text=text, size=size, color=color_label, position=pos_label, margin=margin
    )

    keyboard = [
        [
            InlineKeyboardButton(f"{toggle_icon} {status_label}", callback_data="wm_toggle"),
        ],
        [
            InlineKeyboardButton(get_text(user, context, "watermark_btn_text"), callback_data="wm_set:text"),
            InlineKeyboardButton(get_text(user, context, "watermark_btn_size"), callback_data="wm_set:size"),
        ],
        [
            InlineKeyboardButton(get_text(user, context, "watermark_btn_color"), callback_data="wm_nav:color"),
            InlineKeyboardButton(get_text(user, context, "watermark_btn_position"), callback_data="wm_nav:position"),
            InlineKeyboardButton(get_text(user, context, "watermark_btn_margin"), callback_data="wm_set:margin"),
        ],
        [
            InlineKeyboardButton(get_text(user, context, "btn_back"), callback_data="back_tools"),
        ]
    ]
    return msg, InlineKeyboardMarkup(keyboard)

async def watermark_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Invoca o menu de configurações de marca d'água via mensagem de texto (menu ferramentas)."""
    user = update.effective_user
    await register_interaction(user, context, get_text(user, context, "log_watermark_menu", lang="pt"))
    msg, reply_markup = await _get_watermark_settings_text_and_markup(user, context)
    await update.message.reply_html(msg, reply_markup=reply_markup)

@base_handler_checks
async def watermark_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lida com as interações nos botões inline do menu de marca d'água."""
    query = update.callback_query
    user = query.from_user
    data = query.data

    await query.answer()

    if data == "wm_toggle":
        async with aiosqlite.connect(DB_FILE) as db:
            await db.execute(
                "UPDATE users SET watermark_enabled = 1 - watermark_enabled WHERE user_id = ?",
                (user.id,),
            )
            await db.commit()

        await register_interaction(user, context, "Alternou Marca d'água", is_settings_change=True)
        msg, reply_markup = await _get_watermark_settings_text_and_markup(user, context)
        await query.edit_message_text(msg, parse_mode="HTML", reply_markup=reply_markup)

    elif data.startswith("wm_set:"):
        field = data.split(":")[1]
        context.user_data["state"] = f"WAITING_WATERMARK_{field.upper()}"

        prompts = {
            "text": "watermark_text_prompt",
            "size": "watermark_size_prompt",
            "margin": "watermark_margin_prompt"
        }
        await query.edit_message_text(get_text(user, context, prompts.get(field)), parse_mode="HTML")

    elif data == "wm_nav:color":
        async with aiosqlite.connect(DB_FILE) as db:
            async with db.execute("SELECT watermark_color FROM users WHERE user_id = ?", (user.id,)) as cursor:
                row = await cursor.fetchone()
                current_color = row[0] if row else "WHITE"

        current_color_label = COLORS.get(current_color, ("Unknown", None))[0]
        prompt = get_text(user, context, "watermark_color_prompt") + f"\n\n🎨 Atual: <b>{current_color_label}</b>"

        keyboard = []
        color_keys = list(COLORS.keys())[:12]  # Pega as primeiras 12 cores
        for i in range(0, len(color_keys), 3):
            row = [InlineKeyboardButton(COLORS[k][0], callback_data=f"wm_color:{k}") for k in color_keys[i:i+3]]
            keyboard.append(row)

        keyboard.append([InlineKeyboardButton(get_text(user, context, "btn_back"), callback_data="wm_nav:main")])
        await query.edit_message_text(prompt, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "wm_nav:position":
        async with aiosqlite.connect(DB_FILE) as db:
            async with db.execute("SELECT watermark_position FROM users WHERE user_id = ?", (user.id,)) as cursor:
                row = await cursor.fetchone()
                current_pos = row[0] if row else "bottom_right"

        pos_keys = [
            ("watermark_pos_tl", "top_left"), ("watermark_pos_tc", "top_center"), ("watermark_pos_tr", "top_right"),
            ("watermark_pos_ml", "middle_left"), ("watermark_pos_mc", "middle_center"), ("watermark_pos_mr", "middle_right"),
            ("watermark_pos_bl", "bottom_left"), ("watermark_pos_bc", "bottom_center"), ("watermark_pos_br", "bottom_right")
        ]

        current_pos_label = "Unknown"
        for k_text, k_val in pos_keys:
            if k_val == current_pos:
                current_pos_label = get_text(user, context, k_text)
                break

        prompt = f"📍 <b>{get_text(user, context, 'watermark_btn_position')}</b>\n\nEscolha a posição da marca d'água:\n\n📍 Atual: <b>{current_pos_label}</b>"

        keyboard = []
        for i in range(0, len(pos_keys), 3):
            row = [InlineKeyboardButton(get_text(user, context, k[0]), callback_data=f"wm_pos:{k[1]}") for k in pos_keys[i:i+3]]
            keyboard.append(row)

        keyboard.append([InlineKeyboardButton(get_text(user, context, "btn_back"), callback_data="wm_nav:main")])
        await query.edit_message_text(prompt, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "wm_nav:main":
        msg, reply_markup = await _get_watermark_settings_text_and_markup(user, context)
        await query.edit_message_text(msg, parse_mode="HTML", reply_markup=reply_markup)

    elif data.startswith("wm_color:"):
        color = data.split(":")[1]
        async with aiosqlite.connect(DB_FILE) as db:
            await db.execute("UPDATE users SET watermark_color = ? WHERE user_id = ?", (color, user.id))
            await db.commit()
        await register_interaction(user, context, f"Cor marca d'água: {color}", is_settings_change=True)
        msg, reply_markup = await _get_watermark_settings_text_and_markup(user, context)
        await query.edit_message_text(msg, parse_mode="HTML", reply_markup=reply_markup)

    elif data.startswith("wm_pos:"):
        pos = data.split(":")[1]
        async with aiosqlite.connect(DB_FILE) as db:
            await db.execute("UPDATE users SET watermark_position = ? WHERE user_id = ?", (pos, user.id))
            await db.commit()
        await register_interaction(user, context, f"Posição marca d'água: {pos}", is_settings_change=True)
        msg, reply_markup = await _get_watermark_settings_text_and_markup(user, context)
        await query.edit_message_text(msg, parse_mode="HTML", reply_markup=reply_markup)


async def handle_format_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Processa a escolha do formato."""
    query = update.callback_query
    await query.answer()

    new_fmt = query.data.split(":")[1]
    user = query.from_user

    await register_interaction(
        user, context, f"Formato para {new_fmt}", is_settings_change=True
    )
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute(
            "UPDATE users SET output_format = ? WHERE user_id = ?", (new_fmt, user.id)
        )
        await db.commit()

    text, reply_markup = await _get_settings_text_and_markup(user, context)
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)


async def handle_bgcolor_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Processa a escolha da cor de fundo."""
    query = update.callback_query
    await query.answer()

    new_bg = query.data.split(":")[1]
    user = query.from_user

    await register_interaction(
        user, context, f"Cor de fundo para {new_bg}", is_settings_change=True
    )
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute(
            "UPDATE users SET background_color = ? WHERE user_id = ?", (new_bg, user.id)
        )
        await db.commit()

    text, reply_markup = await _get_settings_text_and_markup(user, context)
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)


async def handle_borders_navigation(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Lida com a navegação no menu de bordas."""
    query = update.callback_query
    await query.answer()
    user = query.from_user

    action = query.data.split(":")[1]

    if action == "width":
        current_width = 0
        async with aiosqlite.connect(DB_FILE) as db:
            async with db.execute(
                "SELECT border_width FROM users WHERE user_id = ?", (user.id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row and row[0] is not None:
                    current_width = row[0]

            # await db.execute("UPDATE users SET current_state = 'WAITING_BORDER_WIDTH' WHERE user_id = ?", (user.id,))
            context.user_data["state"] = "WAITING_BORDER_WIDTH"

        msg = get_text(user, context, "border_width_prompt", current=current_width)
        if query.message.photo or query.message.document:
            await query.message.delete()
            await context.bot.send_message(
                chat_id=query.message.chat_id, text=msg, parse_mode="HTML"
            )
        else:
            await query.edit_message_text(msg, parse_mode="HTML")

    elif action == "color":
        current_color = "WHITE"
        async with aiosqlite.connect(DB_FILE) as db:
            async with db.execute(
                "SELECT border_color FROM users WHERE user_id = ?", (user.id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row and row[0]:
                    current_color = row[0]

        keyboard = []
        row_btns = []
        for color_key, (display_name, _) in COLORS.items():
            row_btns.append(
                InlineKeyboardButton(
                    display_name, callback_data=f"set_border_color:{color_key}"
                )
            )
            if len(row_btns) == 3:
                keyboard.append(row_btns)
                row_btns = []
        if row_btns:
            keyboard.append(row_btns)

        # Botão para cor customizada
        keyboard.append(
            [
                InlineKeyboardButton(
                    get_text(user, context, "btn_custom_color"),
                    callback_data="set_border_color:CUSTOM",
                )
            ]
        )
        keyboard.append(
            [
                InlineKeyboardButton(
                    get_text(user, context, "btn_back"),
                    callback_data="settings_nav:borders",
                )
            ]
        )
        reply_markup = InlineKeyboardMarkup(keyboard)
        msg = get_text(user, context, "border_color_prompt", current=current_color)
        if query.message.photo or query.message.document:
            await query.message.delete()
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=msg,
                parse_mode="HTML",
                reply_markup=reply_markup,
            )
        else:
            await query.edit_message_text(
                msg, parse_mode="HTML", reply_markup=reply_markup
            )


async def handle_border_color_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Processa a escolha da cor da borda."""
    query = update.callback_query
    await query.answer()

    new_color = query.data.split(":")[1]
    user = query.from_user

    if new_color == "CUSTOM":
        async with aiosqlite.connect(DB_FILE) as db:
            # await db.execute("UPDATE users SET current_state = 'WAITING_BORDER_COLOR_CUSTOM' WHERE user_id = ?", (user.id,))
            context.user_data["state"] = "WAITING_BORDER_COLOR_CUSTOM"

        # Pede o input do usuário
        await query.edit_message_text(
            get_text(user, context, "border_color_custom_prompt"), parse_mode="HTML"
        )
        return

    await register_interaction(
        user, context, f"Cor da borda para {new_color}", is_settings_change=True
    )
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute(
            "UPDATE users SET border_color = ? WHERE user_id = ?", (new_color, user.id)
        )
        await db.commit()

    await handle_settings_navigation(
        update, context
    )  # Re-chama para redesenhar o menu de bordas


async def handle_language_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Processa a escolha do idioma."""
    query = update.callback_query
    await query.answer()

    new_lang = query.data.split(":")[1]
    user = query.from_user

    # Atualiza no banco de dados
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute(
            "UPDATE users SET custom_language = ? WHERE user_id = ?",
            (new_lang, user.id),
        )
        await db.commit()

    # Atualiza o cache local para que a mudança de idioma seja refletida imediatamente
    context.user_data["custom_language"] = new_lang

    await register_interaction(
        user, context, f"Idioma para {new_lang}", is_settings_change=True
    )

    lang_names = {
        "en": "English",
        "pt": "Português",
        "es": "Español",
        "ru": "Русский",
        "ar": "العربية",
        "it": "Italiano",
            "fr": "Français",
    }
    # A partir daqui, get_text usará o novo idioma porque 'custom_language' está no contexto
    success_msg = get_text(
        user, context, "language_updated", language=lang_names.get(new_lang, new_lang)
    )

    text, reply_markup = await _get_settings_text_and_markup(user, context)
    await query.edit_message_text(
        f"{success_msg}\n\n{text}", parse_mode="HTML", reply_markup=reply_markup
    )


async def handle_language_init_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Processa a escolha do idioma no primeiro acesso."""
    query = update.callback_query
    await query.answer()

    new_lang = query.data.split(":")[1]
    user = query.from_user

    # Apaga a mensagem de seleção
    await query.message.delete()

    context.user_data["custom_language"] = new_lang

    # Gera CAPTCHA
    n1 = random.randint(1, 10)
    n2 = random.randint(1, 10)
    ans = n1 + n2

    async with aiosqlite.connect(DB_FILE) as db:
        # Atualiza idioma, estado e resposta do captcha em uma única transação atômica.
        # Se a coluna 'captcha_answer' não existir, a operação inteira falha,
        # o que impede o usuário de ficar em um estado inconsistente.
        await db.execute(
            "UPDATE users SET custom_language = ?, captcha_answer = ? WHERE user_id = ?",
            (new_lang, ans, user.id),
        )
        await db.commit()

    context.user_data["state"] = "WAITING_CAPTCHA"

    msg = get_text(user, context, "captcha_prompt", n1=n1, n2=n2)
    await context.bot.send_message(chat_id=user.id, text=msg, parse_mode="HTML")


async def handle_autoresize_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Alterna a configuração de auto redimensionamento."""
    query = update.callback_query
    await query.answer()
    user = query.from_user

    async with aiosqlite.connect(DB_FILE) as db:
        # Alterna entre 0 e 1
        await db.execute(
            "UPDATE users SET auto_resize = NOT COALESCE(auto_resize, 1) WHERE user_id = ?",
            (user.id,),
        )
        await db.commit()

    await register_interaction(
        user, context, "Alterou Auto Resize", is_settings_change=True
    )

    text, reply_markup = await _get_settings_text_and_markup(user, context)
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)


def clear_pending_input_state(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Limpa qualquer fluxo de entrada textual pendente do usuário."""
    context.user_data.pop("state", None)


async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lida com entradas de texto genéricas baseadas no estado do usuário."""
    user = update.effective_user

    # Este handler é exclusivo para mensagens de texto recebidas do usuário.
    # Não usar effective_message aqui: em callbacks ele pode ser a mensagem
    # associada ao botão, embora update.message seja None.
    message = update.message
    if not message or not message.text:
        return

    # As verificações de ban e manutenção são feitas aqui, antes de qualquer processamento,
    # mas depois de garantir que há uma mensagem de texto.
    # O check de setup é tratado separadamente abaixo.
    if await check_banned(update, context):
        return
    if await check_maintenance(update, context):
        return

    text = message.text.strip()

    # Prioriza o fluxo de configuração inicial (captcha)
    state = context.user_data.get("state")

    if state == "WAITING_CAPTCHA":
        # A lógica de tratamento do captcha está mais abaixo, mas a priorizamos aqui
        pass
    elif await check_and_handle_setup_flow(update, context):
        # Se não for captcha mas estiver em outro passo da configuração, bloqueia
        return

    # Intercept de resposta do admin a ticket (antes do roteamento normal)
    if await tickets_mod.msg_admin_reply(update, context):
        return

    # Intercept de entrada de texto para broadcast multi-idioma (Admin)
    if await handle_broadcast_multi_input(update, context):
        return

    # Mapeamento de chaves de tradução para funções
    menu_actions = {
        "menu_settings": settings_command,
        "menu_cancel": cancel_command,
        "menu_help": help_command,
        "menu_compress": compress_command,
        "pdf_btn": convert_to_pdf_command,
        "menu_merge_pdf": merge_pdfs_command,
        "menu_clear_all": clear_all_command,
        "menu_zip_queue": zip_queue_command,
        "menu_remove_bg": remove_bg_start,
        "menu_remove_metadata": remove_metadata_command,
        "menu_converter": converter_menu_command,
        "menu_ocr": ocr_command,
        "menu_other_bots": other_bots_command,
        "menu_sticker": sticker_command,
        "menu_qrcode": qrcode_command,
        # Comandos de união são tratados separadamente para o check de setup
        "menu_gif": gif_menu_command, # Mapeamento do botão de texto
        "menu_merge_vertical": merge_vertically_command,
        "menu_merge_horizontal": merge_horizontally_command,
        "menu_grid": grid_command,
        "menu_meme": meme_start,
        "menu_censor": censor_menu_command,
        "menu_tools": tools_menu_command,
        "menu_contribute": contribute_command,
        "btn_back": back_to_main_menu_command,
        "menu_my_usage": my_usage_command,
        "menu_watermark": watermark_menu_command,
        "menu_support_tickets": tickets_mod.ticket_main_message,
    }

    # Tenta encontrar a ação correspondente ao texto
    action_func = None
    action_key = None

    # 1. Verifica no idioma atual (caminho feliz)
    for key, func in menu_actions.items():
        if text == get_text(user, context, key):
            action_func = func
            action_key = key
            break

    # 2. Se não encontrou, verifica em todos os idiomas disponíveis (caso o teclado esteja desatualizado)
    if not action_func:
        for lang_data in TRANSLATIONS.values():
            for key, func in menu_actions.items():
                if lang_data.get(key) == text:
                    action_func = func
                    action_key = key
                    break
            if action_func:
                break

    if action_func:
        # Qualquer opção de menu interrompe o fluxo textual anterior. A opção
        # de compressão cria um novo estado dentro de compress_command.
        if action_key != "menu_compress":
            clear_pending_input_state(context)
        await action_func(update, context)
        return

    if state == "WAITING_CAPTCHA":
        try:
            user_ans = int(text)

            # Busca a resposta correta no banco de dados
            correct_ans = None
            async with aiosqlite.connect(DB_FILE) as db:
                async with db.execute(
                    "SELECT captcha_answer FROM users WHERE user_id = ?", (user.id,)
                ) as cursor:
                    row_ans = await cursor.fetchone()
                    if row_ans:
                        correct_ans = row_ans[0]

            if correct_ans is not None and user_ans == correct_ans:
                async with aiosqlite.connect(DB_FILE) as db:
                    await db.execute(
                        "UPDATE users SET captcha_answer = NULL WHERE user_id = ?",
                        (user.id,),
                    )
                    await db.commit()
                context.user_data["state"] = None

                await register_interaction(user, context, "✅ Passou no CAPTCHA")

                await update.message.reply_html(
                    get_text(user, context, "captcha_success")
                )
                await send_keyboard_tip_image(update, context)
                await show_start_menu(update, context)
            else:
                raise ValueError("Wrong answer")
        except (ValueError, TypeError):
            await register_interaction(
                user, context, f"❌ Errou o CAPTCHA (Tentou: {text[:50]})"
            )

            n1 = random.randint(1, 10)
            n2 = random.randint(1, 10)
            new_ans = n1 + n2

            async with aiosqlite.connect(DB_FILE) as db:
                await db.execute(
                    "UPDATE users SET captcha_answer = ? WHERE user_id = ?",
                    (new_ans, user.id),
                )
                await db.commit()

            await update.message.reply_html(
                get_text(user, context, "captcha_error", n1=n1, n2=n2)
            )
        return

    # Estado para geração de QR Code - esperando o texto/link
    if state == QRCODE_WAITING_TEXT:
        await handle_qrcode_text_input(update, context)
        return

    # Estado para geração de QR Code - esperando texto adicional
    if state == QRCODE_WAITING_EXTRA_TEXT:
        await handle_qrcode_extra_text_input(update, context)
        return

        return

    elif state == "WAITING_WATERMARK_TEXT":
        async with aiosqlite.connect(DB_FILE) as db:
            await db.execute(
                "UPDATE users SET watermark_text = ? WHERE user_id = ?",
                (text, user.id),
            )
            await db.commit()
            context.user_data["state"] = None

            await register_interaction(
                user, context, f"Texto marca d'água: {text[:20]}", is_settings_change=True
            )
            success_msg = get_text(user, context, "watermark_text_success", text=text)
            msg, reply_markup = await _get_watermark_settings_text_and_markup(user, context)
            await update.message.reply_html(f"{success_msg}\n\n{msg}", reply_markup=reply_markup)
        return

    elif state == "WAITING_WATERMARK_SIZE":
        if text.isdigit():
            val = int(text)
            if 10 <= val <= 200:
                async with aiosqlite.connect(DB_FILE) as db:
                    await db.execute(
                        "UPDATE users SET watermark_size = ? WHERE user_id = ?",
                        (val, user.id),
                    )
                    await db.commit()
                context.user_data["state"] = None
                await register_interaction(user, context, f"Tamanho marca d'água: {val}", is_settings_change=True)
                success_msg = get_text(user, context, "watermark_size_success", value=val)
                msg, reply_markup = await _get_watermark_settings_text_and_markup(user, context)
                await update.message.reply_html(f"{success_msg}\n\n{msg}", reply_markup=reply_markup)
            else:
                await update.message.reply_html(get_text(user, context, "watermark_size_invalid"))
        else:
            await update.message.reply_html(get_text(user, context, "watermark_size_invalid"))
        return

    elif state == "WAITING_WATERMARK_MARGIN":
        if text.isdigit():
            val = int(text)
            if 0 <= val <= 500:
                async with aiosqlite.connect(DB_FILE) as db:
                    await db.execute(
                        "UPDATE users SET watermark_margin = ? WHERE user_id = ?",
                        (val, user.id),
                    )
                    await db.commit()
                context.user_data["state"] = None
                await register_interaction(user, context, f"Margem marca d'água: {val}px", is_settings_change=True)
                success_msg = get_text(user, context, "watermark_margin_success", value=val)
                msg, reply_markup = await _get_watermark_settings_text_and_markup(user, context)
                await update.message.reply_html(f"{success_msg}\n\n{msg}", reply_markup=reply_markup)
            else:
                await update.message.reply_html(get_text(user, context, "watermark_margin_invalid"))
        else:
            await update.message.reply_html(get_text(user, context, "watermark_margin_invalid"))
        return

    if state == "WAITING_QUALITY":
        async with aiosqlite.connect(DB_FILE) as db:
            if text.isdigit():
                val = int(text)
                if 5 <= val <= 100:
                    await db.execute(
                        "UPDATE users SET compression_quality = ? WHERE user_id = ?",
                        (val, user.id),
                    )
                    await db.commit()
                    context.user_data["state"] = None

                    await register_interaction(
                        user, context, f"Qualidade para {val}%", is_settings_change=True
                    )
                    success_msg = get_text(user, context, "quality_success", value=val)
                    settings_text, reply_markup = await _get_settings_text_and_markup(
                        user, context
                    )

                    combined_msg = f"{success_msg}\n\n{settings_text}"
                    await update.message.reply_html(
                        combined_msg, reply_markup=reply_markup
                    )
                else:
                    await update.message.reply_html(
                        get_text(user, context, "quality_invalid")
                    )
            else:
                await update.message.reply_html(
                    get_text(user, context, "quality_invalid")
                )
        return

    elif state == "WAITING_COMPRESSION_TARGET":
        try:
            # Substitui vírgula por ponto para suportar formatos como "0,5"
            val_str = text.replace(",", ".")
            target_mb = float(val_str)
            if target_mb > 0:
                context.user_data["state"] = None
                await process_compression(update, context, target_mb)
            else:
                await message.reply_html(
                    get_text(user, context, "compress_invalid")
                )
        except ValueError:
            await message.reply_html(get_text(user, context, "compress_invalid"))
        return

    elif state == "WAITING_BORDER_WIDTH":
        async with aiosqlite.connect(DB_FILE) as db:
            if text.isdigit():
                val = int(text)
                if 0 <= val <= 50:  # Allow 0 for no border
                    await db.execute(
                        "UPDATE users SET border_width = ? WHERE user_id = ?",
                        (val, user.id),
                    )
                    await db.commit()
                    context.user_data["state"] = None

                    await register_interaction(
                        user,
                        context,
                        f"Tamanho da borda para {val}px",
                        is_settings_change=True,
                    )
                    success_msg = get_text(
                        user, context, "border_width_success", value=val
                    )

                    # Go back to the borders menu
                    border_color = "WHITE"
                    async with db.execute(
                        "SELECT border_color FROM users WHERE user_id = ?", (user.id,)
                    ) as cursor:
                        row = await cursor.fetchone()
                        if row:
                            border_color = row[0] or "WHITE"

                    keyboard = [
                        [
                            InlineKeyboardButton(
                                get_text(user, context, "borders_btn_width"),
                                callback_data="borders_nav:width",
                            ),
                            InlineKeyboardButton(
                                get_text(user, context, "borders_btn_color"),
                                callback_data="borders_nav:color",
                            ),
                        ],
                        [
                            InlineKeyboardButton(
                                get_text(user, context, "btn_back"),
                                callback_data="settings_nav:main",
                            )
                        ],
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    main_msg = get_text(
                        user, context, "borders_title", width=val, color=border_color
                    )

                    await update.message.reply_html(
                        f"{success_msg}\n\n{main_msg}", reply_markup=reply_markup
                    )
                else:
                    await update.message.reply_html(
                        get_text(user, context, "border_width_invalid")
                    )
            else:
                await update.message.reply_html(
                    get_text(user, context, "border_width_invalid")
                )
        return

    elif state == "WAITING_BORDER_COLOR_CUSTOM":
        # Validação de cor customizada
        valid = False
        final_color = ""

        # Remove espaços extras
        clean_text = text.strip().replace(" ", "")

        # Verifica Hex (#RRGGBB ou #RGB)
        if re.match(r"^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$", clean_text):
            valid = True
            final_color = clean_text.upper()
            # Expande formato curto #F00 -> #FF0000
            if len(final_color) == 4:
                final_color = "#" + "".join([c * 2 for c in final_color[1:]])

        # Verifica RGB (0-255,0-255,0-255)
        elif re.match(r"^\d{1,3},\d{1,3},\d{1,3}$", clean_text):
            parts = [int(x) for x in clean_text.split(",")]
            if all(0 <= x <= 255 for x in parts):
                valid = True
                final_color = f"{parts[0]},{parts[1]},{parts[2]}"

        if valid:
            async with aiosqlite.connect(DB_FILE) as db:
                await db.execute(
                    "UPDATE users SET border_color = ? WHERE user_id = ?",
                    (final_color, user.id),
                )
                await db.commit()
            context.user_data["state"] = None

            await register_interaction(
                user,
                context,
                f"Cor da borda customizada para {final_color}",
                is_settings_change=True,
            )
            success_msg = get_text(
                user, context, "border_color_updated", color=final_color
            )

            # Gera imagem de preview
            preview_bio = None
            try:
                color_tuple = (255, 255, 255)
                if final_color.startswith("#"):
                    h = final_color.lstrip("#")
                    color_tuple = tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))
                else:
                    color_tuple = tuple(map(int, final_color.split(",")))

                preview_img = Image.new("RGB", (150, 50), color_tuple)
                preview_bio = io.BytesIO()
                preview_img.save(preview_bio, format="PNG")
                preview_bio.seek(0)
            except Exception as e:
                logger.error(f"Erro ao gerar preview de cor: {e}")

            # Retorna ao menu de bordas
            # Busca width atual para exibir corretamente
            border_width = 0
            async with aiosqlite.connect(DB_FILE) as db:
                async with db.execute(
                    "SELECT border_width FROM users WHERE user_id = ?", (user.id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        border_width = row[0] or 0

            # Chama a função auxiliar para gerar o menu de bordas (reutilizando lógica existente seria ideal, mas aqui reconstruímos para responder ao texto)
            keyboard = [
                [
                    InlineKeyboardButton(
                        get_text(user, context, "borders_btn_width"),
                        callback_data="borders_nav:width",
                    ),
                    InlineKeyboardButton(
                        get_text(user, context, "borders_btn_color"),
                        callback_data="borders_nav:color",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        get_text(user, context, "btn_back"),
                        callback_data="settings_nav:main",
                    )
                ],
            ]
            main_msg = get_text(
                user, context, "borders_title", width=border_width, color=final_color
            )

            if preview_bio:
                await update.message.reply_photo(
                    photo=preview_bio,
                    caption=f"{success_msg}\n\n{main_msg}",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )
            else:
                await update.message.reply_html(
                    f"{success_msg}\n\n{main_msg}",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )
        else:
            await update.message.reply_html(
                get_text(user, context, "border_color_invalid")
            )
        return

    # Se não houver estado ou não for tratado, ignora (ou pode adicionar lógica de chat aqui)
    pass


@base_handler_checks
async def handle_media_for_gif(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler específico para receber Vídeo ou GIF quando o estado solicita."""
    user = update.effective_user
    state = context.user_data.get("state")

    # Removemos a guarda estrita de estado para permitir que o bot reaja a vídeos/gifs enviados diretamente
    # if state not in ["WAITING_VIDEO_FOR_GIF", "WAITING_GIF_FOR_VIDEO"]:
    #     return

    file_obj = None
    file_type = ""

    if update.message.video:
        file_obj = update.message.video
        file_type = "video"
    elif update.message.video_note:
        file_obj = update.message.video_note
        file_type = "video"
    elif update.message.animation:
        file_obj = update.message.animation
        file_type = "gif"
    elif update.message.document:
        # Verifica MIME type
        mime = update.message.document.mime_type or ""
        if "video" in mime:
            file_obj = update.message.document
            file_type = "video"
        elif "gif" in mime or update.message.document.file_name.lower().endswith(".gif"):
            file_obj = update.message.document
            file_type = "gif"

    if not file_obj:
        await update.message.reply_html(get_text(user, context, "invalid_file_type"))
        return

    # Verifica tamanho 20MB
    if file_obj.file_size > 20 * 1024 * 1024:
        await update.message.reply_html(get_text(user, context, "file_too_large", max=20))
        return

    # Armazena o file_id temporariamente para processamento posterior
    temp_file_id = file_obj.file_id
    temp_file_type = file_type
    temp_file_size = file_obj.file_size

    # Armazena o file_id temporariamente para processamento posterior (Bug Button_data_invalid)
    msg_id = update.message.message_id
    context.user_data[f"temp_media_{msg_id}"] = {
        "file_id": temp_file_id,
        "type": temp_file_type,
        "size": temp_file_size
    }

    # Se for GIF, salva também no cache específico de GIF para os handlers de conversão
    if temp_file_type == "gif":
        context.user_data[f"temp_gif_{msg_id}"] = temp_file_id

    # Se for vídeo, oferece conversão para GIF independente do estado
    if temp_file_type == "video":
        keyboard = [
            [
                InlineKeyboardButton(
                    get_text(user, context, "gif_btn_video"),
                    callback_data=f"vid_to_gif_confirm:{msg_id}"
                ),
                InlineKeyboardButton(
                    get_text(user, context, "btn_delete"),
                    callback_data=f"video_to_gif_cancel:{msg_id}"
                )
            ]
        ]
        await update.message.reply_html(
            get_text(user, context, "video_received"),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Se for GIF animado
    if temp_file_type == "gif":
        # Se estiver esperando especificamente para vídeo
        if state == "WAITING_GIF_FOR_VIDEO":
            await process_gif_to_video(update, context, temp_file_id)
            return

        # Se estiver esperando especificamente para ZIP
        if state == "WAITING_GIF_FOR_ZIP":
            await process_gif_extraction_zip(update, context, temp_file_id)
            return

        # Se não houver estado ou for outro estado, oferece o menu de opções do GIF animado
        # (Isso unifica o comportamento para qualquer GIF animado enviado)
        keyboard = [
            [
                InlineKeyboardButton(get_text(user, context, "gif_btn_gif_to_video"), callback_data=f"gif_conv:vid:{msg_id}"),
                InlineKeyboardButton(get_text(user, context, "gif_btn_extract_frames"), callback_data=f"gif_conv:ext:{msg_id}")
            ],
            [
                InlineKeyboardButton(get_text(user, context, "menu_cancel"), callback_data=f"gif_conv:can:{msg_id}")
            ]
        ]
        await update.message.reply_html(
            get_text(user, context, "gif_animated"),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def handle_gif_conv_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para as opções de GIF Animado (Vídeo, Extrair, Cancelar)."""
    query = update.callback_query
    user = update.effective_user
    await query.answer()

    # data: gif_conv:action:msg_id
    parts = query.data.split(":")
    action = parts[1]
    msg_id = parts[2]

    file_id = context.user_data.get(f"temp_gif_{msg_id}")
    if not file_id:
        await query.edit_message_text(f"⚠️ {get_text(user, context, 'err_file_not_found')}", parse_mode="HTML")
        return

    if action == "can":
        await query.edit_message_text(get_text(user, context, "action_cancelled"), parse_mode="HTML")
        # Limpa cache
        context.user_data.pop(f"temp_gif_{msg_id}", None)
        return

    if action == "vid":
        # Inicia fluxo de conversão para vídeo
        await process_gif_to_video(update, context, file_id)
        return

    if action == "ext":
        # Sub-menu de extração
        keyboard = [
            [
                InlineKeyboardButton(get_text(user, context, "gif_btn_extract_here"), callback_data=f"gif_ext:here:{msg_id}"),
            ],
            [
                InlineKeyboardButton(get_text(user, context, "gif_btn_extract_zip"), callback_data=f"gif_ext:zip:{msg_id}"),
            ],
            [
                InlineKeyboardButton(get_text(user, context, "btn_back"), callback_data=f"gif_ext:back:{msg_id}")
            ]
        ]
        await query.edit_message_text(
            get_text(user, context, "gif_extract_menu_title"),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        return


async def handle_gif_extraction_sub_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para o sub-menu de extração (Fila vs ZIP)."""
    query = update.callback_query
    user = update.effective_user
    await query.answer()

    # data: gif_ext:action:msg_id
    parts = query.data.split(":")
    action = parts[1]
    msg_id = parts[2]

    file_id = context.user_data.get(f"temp_gif_{msg_id}")
    if not file_id:
        await query.edit_message_text(f"⚠️ {get_text(user, context, 'err_file_not_found')}", parse_mode="HTML")
        return

    if action == "back":
        # Retorna ao menu principal do GIF
        keyboard = [
            [
                InlineKeyboardButton(get_text(user, context, "gif_btn_gif_to_video"), callback_data=f"gif_conv:vid:{msg_id}"),
                InlineKeyboardButton(get_text(user, context, "gif_btn_extract_frames"), callback_data=f"gif_conv:ext:{msg_id}")
            ],
            [
                InlineKeyboardButton(get_text(user, context, "menu_cancel"), callback_data=f"gif_conv:can:{msg_id}")
            ]
        ]
        await query.edit_message_text(
            get_text(user, context, "gif_animated"),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        return

    if action == "here":
        await process_gif_extraction(update, context, file_id)
        return

    if action == "zip":
        await process_gif_extraction_zip(update, context, file_id)
        return


async def process_gif_extraction_zip(update: Update, context: ContextTypes.DEFAULT_TYPE, file_id: str) -> None:
    """Extrai frames de um GIF e envia em um arquivo ZIP."""
    user = update.effective_user
    query = update.callback_query

    try:
        if query:
            await query.edit_message_text(get_text(user, context, 'gif_generating'), parse_mode="HTML")
        else:
            await update.message.reply_html(get_text(user, context, 'gif_generating'))

        file = await context.bot.get_file(file_id)
        image_bytes = await file.download_as_bytearray()

        # Executa extração em background
        loop = asyncio.get_running_loop()
        frames_bytes = await loop.run_in_executor(
            PROCESS_POOL,
            _extract_gif_frames_task,
            bytes(image_bytes)
        )

        if not frames_bytes:
            raise ValueError("Nenhum quadro extraído.")

        # Cria o ZIP
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for i, frame_data in enumerate(frames_bytes):
                zf.writestr(f"frame_{i+1}.jpg", frame_data)

        zip_buffer.seek(0)

        await context.bot.send_document(
            chat_id=user.id,
            document=zip_buffer,
            filename="frames_gif.zip",
            caption=get_text(user, context, "zip_caption")
        )

        if query:
            await query.delete_message()


    except Exception as e:
        logger.error(f"Erro na extração ZIP de GIF: {e}")
        error_msg = get_text(user, context, "gif_error")
        if query:
            await query.edit_message_text(error_msg, parse_mode="HTML")
        else:
            await update.message.reply_html(error_msg)


async def process_gif_extraction(update: Update, context: ContextTypes.DEFAULT_TYPE, file_id: str) -> None:
    """Extrai frames de um GIF e adiciona à fila de merge."""
    user = update.effective_user
    query = update.callback_query

    try:
        if query:
            await query.edit_message_text(get_text(user, context, 'gif_generating'), parse_mode="HTML")
        else:
            await update.message.reply_html(get_text(user, context, 'gif_generating'))

        file = await context.bot.get_file(file_id)
        image_bytes = await file.download_as_bytearray()

        # Executa extração em background
        loop = asyncio.get_running_loop()
        frames_bytes = await loop.run_in_executor(
            PROCESS_POOL,
            _extract_gif_frames_task,
            bytes(image_bytes)
        )

        if not frames_bytes:
            raise ValueError("Nenhum quadro extraído.")

        # Adiciona frames ao banco de dados
        async with aiosqlite.connect(DB_FILE) as db:
            count = 0
            for i, frame_data in enumerate(frames_bytes):
                # Para cada frame, precisamos "simular" um recebimento
                # Como não temos um file_id do Telegram para cada frame extraído localmente,
                # e o bot depende de file_id para merge, teremos que enviar o frame para o bot (ou para um canal privado/admin)
                # para obter um file_id válido OU mudar o merge para aceitar bytes (complexo).
                # Atalho: Envia para o próprio usuário de forma "silenciosa" ou apenas salva os bytes (se suportado).
                # Melhor: Envia os frames como fotos para o usuário e captura os file_ids.

                buf = io.BytesIO(frame_data)
                sent_msg = await context.bot.send_photo(
                    chat_id=user.id,
                    photo=buf,
                    caption=f"Frame {i+1}",
                    disable_notification=True
                )

                photo = sent_msg.photo[-1]
                file_fmt = "JPEG"
                size_text = _format_size(photo.file_size)
                dims_text = f"{photo.width}x{photo.height}"

                await db.execute(
                    "INSERT INTO user_images (user_id, file_id, is_document, message_id, file_name, file_size_text, dimensions, file_fmt) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (user.id, photo.file_id, 0, sent_msg.message_id, f"Frame_{i+1}.jpg", size_text, dims_text, file_fmt),
                )
                count += 1
            await db.commit()

        success_msg = get_text(user, context, "gif_extract_success", count=count)
        if query:
            await query.edit_message_text(success_msg, parse_mode="HTML")
        else:
            await update.message.reply_html(success_msg)

        # A extração é registrada apenas nas métricas locais.
    except Exception as e:
        logger.error(f"Erro na extração de GIF: {e}")
        error_msg = get_text(user, context, "gif_error")
        if query:
            await query.edit_message_text(error_msg, parse_mode="HTML")
        else:
            await update.message.reply_html(error_msg)


def _extract_gif_frames_task(gif_bytes: bytes) -> list[bytes]:
    """Extrai até 20 frames de um GIF ou Vídeo Curto (Animação MP4). CPU-bound."""
    frames_output = []

    # Tenta como GIF primeiro (Pillow)
    try:
        with Image.open(io.BytesIO(gif_bytes)) as img:
            # Limite de 20 frames para não sobrecarregar
            n_frames = min(getattr(img, "n_frames", 1), 20)

            for i in range(n_frames):
                img.seek(i)
                # Converte para RGB (remover transparência se houver)
                frame = img.convert("RGB")
                buf = io.BytesIO()
                frame.save(buf, format="JPEG", quality=90)
                frames_output.append(buf.getvalue())

            if frames_output:
                return frames_output
    except Exception:
        # Se falhar no Pillow, tenta como vídeo usando OpenCV
        pass

    # Fallback: Tenta como vídeo (OpenCV) para animações MP4 do Telegram
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp.write(gif_bytes)
            tmp_path = tmp.name

        cap = cv2.VideoCapture(tmp_path)
        try:
            count = 0
            while count < 20:
                ret, frame = cap.read()
                if not ret:
                    break
                # OpenCV uses BGR, convert to RGB for PIL
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(frame_rgb)

                buf = io.BytesIO()
                pil_img.save(buf, format="JPEG", quality=90)
                frames_output.append(buf.getvalue())
                count += 1
        finally:
            cap.release()
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    except Exception as e:
        logger.error(f"Erro no task de extração: {e} | bytes_length: {len(gif_bytes)}")

    return frames_output


async def process_gif_to_video(update: Update, context: ContextTypes.DEFAULT_TYPE, file_id: str) -> None:
    """Invoca o processamento de GIF para Vídeo."""
    user = update.effective_user
    query = update.callback_query

    if query:
        await query.edit_message_text(get_text(user, context, 'gif_generating'), parse_mode="HTML")
    else:
        await update.message.reply_html(get_text(user, context, 'gif_generating'))

    # Reutiliza lógica existente de GIF -> Vídeo (que já existe no bot)
    # Mas precisamos de um objeto Update compatível ou chamar a task direto
    file = await context.bot.get_file(file_id)
    gif_bytes = await file.download_as_bytearray()

    try:
        # Executa em pool
        loop = asyncio.get_running_loop()
        output_path = await loop.run_in_executor(
            PROCESS_POOL,
            _gif_to_video_task,
            bytes(gif_bytes)
        )

        if output_path and os.path.exists(output_path):
            with open(output_path, "rb") as video:
                await context.bot.send_video(
                    chat_id=user.id,
                    video=video,
                    filename="video.mp4",
                    caption=get_text(user, context, "gif_video_success")
                )
            os.remove(output_path)

            if query:
                await query.delete_message()


        else:
            raise ValueError("Falha ao gerar vídeo.")
    except Exception as e:
        logger.error(f"Erro ao converter GIF -> Vídeo: {e}")
        error_msg = get_text(user, context, "gif_error")
        if query:
            await query.edit_message_text(error_msg, parse_mode="HTML")


async def handle_media_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para as confirmações de Video/GIF vindo do handle_media_for_gif (Bug Fix)."""
    query = update.callback_query
    user = update.effective_user
    await query.answer()

    # data: (vid_to_gif_confirm|gif_to_video_confirm|video_to_gif_cancel):msg_id
    data = query.data
    parts = data.split(":")
    action = parts[0]
    msg_id = parts[1]

    media_data = context.user_data.get(f"temp_media_{msg_id}")

    if action == "video_to_gif_cancel":
        await query.edit_message_text(get_text(user, context, "action_cancelled"), parse_mode="HTML")
        context.user_data.pop(f"temp_media_{msg_id}", None)
        return

    if not media_data:
        await query.edit_message_text(get_text(user, context, "session_expired"), parse_mode="HTML")
        return

    file_id = media_data["file_id"]

    if action == "vid_to_gif_confirm":
        # Chama a função de conversão de vídeo para gif
        # Nota: O bot atual parece ter process_video_to_gif_action (preciso achar o nome exato)
        # Vou implementar a chamada direta para evitar erros de assinatura
        await query.edit_message_text(get_text(user, context, 'gif_generating'), parse_mode="HTML")

        file = await context.bot.get_file(file_id)
        video_path = f"/tmp/video_{msg_id}.mp4"
        await file.download_to_drive(video_path)

        settings = context.user_data.get("gif_settings", GIF_DEFAULTS)

        try:
            loop = asyncio.get_running_loop()
            gif_bytes = await loop.run_in_executor(
                PROCESS_POOL,
                _video_to_gif_task,
                video_path,
                settings["fps"],
                settings["scale"]
            )

            f_io = io.BytesIO(gif_bytes)
            f_io.name = "animation.gif"

            await context.bot.send_animation(
                chat_id=user.id,
                animation=f_io,
                caption=get_text(user, context, "gif_success")
            )
            await query.delete_message()

            # O GIF é enviado somente ao usuário.
        except Exception as e:
            logger.error(f"Erro vid_to_gif: {e}")
            await query.edit_message_text(get_text(user, context, "gif_error"))
        finally:
            if os.path.exists(video_path):
                os.remove(video_path)

    elif action == "gif_to_video_confirm":
        await process_gif_to_video(update, context, file_id)


async def execute_merge(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    rows: list,
    direction: str,
    override_resize: bool | None = None,
    override_watermark: bool | None = None,
) -> None:
    """Executa o processo de download, união e envio das imagens."""
    user = update.effective_user
    user_id = user.id

    # Traduz a direção para exibição e para o log
    if direction.startswith("grid"):
        dir_display = (
            get_text(user, context, "direction_grid") + f" ({direction.split('_')[1]}x)"
        )
    else:
        dir_display = get_text(user, context, f"direction_{direction}")

    async with aiosqlite.connect(DB_FILE) as db:
        # Busca preferências do usuário
        async with db.execute(
            "SELECT output_format, compression_quality, background_color, auto_resize, border_width, border_color, watermark_enabled, watermark_text, watermark_size, watermark_color, watermark_position, watermark_margin FROM users WHERE user_id = ?",
            (user_id,),
        ) as cursor_fmt:
            row_fmt = await cursor_fmt.fetchone()
            output_format = row_fmt[0] if row_fmt and row_fmt[0] else "JPEG"
            quality = row_fmt[1] if row_fmt and row_fmt[1] else 100
            bg_color = row_fmt[2] if row_fmt and row_fmt[2] else "WHITE"
            auto_resize = row_fmt[3] if row_fmt and len(row_fmt) > 3 and row_fmt[3] is not None else 1
            border_width = row_fmt[4] if row_fmt and len(row_fmt) > 4 and row_fmt[4] is not None else 0
            border_color = row_fmt[5] if row_fmt and len(row_fmt) > 5 and row_fmt[5] else "WHITE"

            # Watermark settings
            wm_enabled_db = row_fmt[6] if row_fmt and len(row_fmt) > 6 else 0
            wm_text = row_fmt[7] if row_fmt and len(row_fmt) > 7 else "UnifyImages"
            wm_size = row_fmt[8] if row_fmt and len(row_fmt) > 8 else 30
            wm_color = row_fmt[9] if row_fmt and len(row_fmt) > 9 else "WHITE"
            wm_pos = row_fmt[10] if row_fmt and len(row_fmt) > 10 else "bottom_right"
            wm_margin = row_fmt[11] if row_fmt and len(row_fmt) > 11 else 20

            # Aplica override se fornecido, senão usa do banco
            wm_enabled = wm_enabled_db if override_watermark is None else (1 if override_watermark else 0)

    # Define se usa o resize do banco ou o override
    use_resize = bool(auto_resize)
    if override_resize is not None:
        use_resize = override_resize

    # Envia mensagem de processamento (se for callback, usa effective_message)
    status_msg = None
    if update.callback_query:
        status_msg = await update.effective_message.reply_text(
            get_text(
                user, context, "processing", count=len(rows), direction=dir_display
            )
        )
    else:
        status_msg = await update.message.reply_text(
            get_text(
                user, context, "processing", count=len(rows), direction=dir_display
            )
        )

    # Adiciona usuário à lista de espera para cálculo de posição
    user_info = (user.id, user.first_name)
    PROCESSING_QUEUE.append(user_info)

    try:
        # Verifica se o servidor está ocupado e avisa o usuário com estimativa
        if PROCESSING_SEMAPHORE.locked():
            idx = PROCESSING_QUEUE.index(user_info)
            # Pessoas na frente = 1 (rodando) + idx (pessoas antes de mim na lista)
            ahead = idx + 1
            est_time = ahead * ESTIMATED_TIME_PER_JOB
            if update.callback_query:
                await update.effective_message.reply_html(
                    get_text(
                        user, context, "added_to_queue", ahead=ahead, time=est_time
                    )
                )
            else:
                await update.message.reply_html(
                    get_text(
                        user, context, "added_to_queue", ahead=ahead, time=est_time
                    )
                )

        # Entra na fila de processamento (bloqueia aqui até liberar)
        async with PROCESSING_SEMAPHORE:
            # Remove da fila de espera pois já vai processar
            if user_info in PROCESSING_QUEUE:
                PROCESSING_QUEUE.remove(user_info)

            global CURRENT_PROCESSING
            CURRENT_PROCESSING = user_info

            # Helper para retry de envio
            async def send_with_retry(func, **kwargs):
                for i in range(3):
                    try:
                        return await func(**kwargs)
                    except (NetworkError, httpx.RemoteProtocolError):
                        if i == 2:
                            raise
                        await asyncio.sleep(1 + i)

            try:

                async def download_image(file_id: str) -> tuple[str, bytes | None]:
                    attempts = 3
                    for attempt in range(1, attempts + 1):
                        try:
                            async with asyncio.timeout(20):  # Timeout de 20s
                                new_file = await context.bot.get_file(file_id)
                                file_bytes = await new_file.download_as_bytearray()
                                return file_id, file_bytes
                        except Exception as e:
                            if attempt < attempts:
                                await asyncio.sleep(1 * attempt)  # Backoff simples
                            else:
                                logger.error(
                                    f"Erro final ao baixar a imagem {file_id} após {attempts} tentativas: {e}"
                                )
                                return file_id, None
                    return file_id, None

                # Download paralelo de todas as imagens
                tasks = [download_image(row[0]) for row in rows]
                results = await asyncio.gather(*tasks)

                image_bytes_list = []
                failed_ids = []

                for fid, content in results:
                    if content:
                        image_bytes_list.append(content)
                    else:
                        failed_ids.append(fid)

                if failed_ids:
                    # Remove apenas as imagens que falharam
                    async with aiosqlite.connect(DB_FILE) as db:
                        for fid in failed_ids:
                            await db.execute(
                                "DELETE FROM user_images WHERE user_id = ? AND file_id = ?",
                                (user_id, fid),
                            )
                        await db.commit()
                    msg_text = get_text(
                        user, context, "download_error_partial", count=len(failed_ids)
                    )
                    if update.callback_query:
                        await update.effective_message.reply_text(msg_text)
                    else:
                        await update.message.reply_text(msg_text)
                    return

                # Processa as imagens
                try:
                    # Prepare watermark settings dictionary
                    watermark_data = {
                        "enabled": wm_enabled,
                        "text": wm_text,
                        "size": wm_size,
                        "color": wm_color,
                        "position": wm_pos,
                        "margin": wm_margin
                    }

                    if direction == "vertical":
                        final_image_bytes_content = await merge_images_vertically(
                            image_bytes_list,
                            output_format,
                            quality,
                            bg_color,
                            use_resize,
                            border_width,
                            border_color,
                            watermark_settings=watermark_data,
                        )
                    elif direction.startswith("grid"):
                        final_image_bytes_content = await merge_images_grid(
                            image_bytes_list,
                            direction,
                            output_format,
                            quality,
                            bg_color,
                            use_resize,
                            border_width,
                            border_color,
                            watermark_settings=watermark_data,
                        )
                    else:
                        final_image_bytes_content = await merge_images_horizontally(
                            image_bytes_list,
                            output_format,
                            quality,
                            bg_color,
                            use_resize,
                            border_width,
                            border_color,
                            watermark_settings=watermark_data,
                        )

                    final_image_bytes = io.BytesIO(final_image_bytes_content)
                except Exception as e:
                    logger.error(
                        f"Erro ao unir as imagens para o usuário {user_id}: {e}"
                    )
                    msg_text = get_text(user, context, "process_error")
                    if update.callback_query:
                        await update.effective_message.reply_text(msg_text)
                    else:
                        await update.message.reply_text(msg_text)
                    return

                # Envia a imagem final
                final_image_bytes.seek(0)
                with Image.open(final_image_bytes) as img_check:
                    img_w, img_h = img_check.size

                final_image_bytes.seek(0, io.SEEK_END)
                file_size = final_image_bytes.tell()
                final_image_bytes.seek(0)

                # Define a extensão correta
                ext = output_format.lower()
                if ext == "jpeg":
                    ext = "jpg"

                # Salva a imagem em cache para permitir o download como arquivo
                cache_dir = "cache"
                os.makedirs(cache_dir, exist_ok=True)
                filename = f"merged_{user_id}_{int(time.time())}.{ext}"
                filepath = os.path.join(cache_dir, filename)

                with open(filepath, "wb") as f:
                    f.write(final_image_bytes.read())
                final_image_bytes.seek(0)  # Rewind para envio

                # Configura botões de regeneração
                regen_resize_val = 0 if use_resize else 1
                regen_text_key = "btn_no_resize" if use_resize else "btn_with_resize"
                regen_text = get_text(user, context, regen_text_key)

                # Para manter o estado do watermark na regeneração normal (sem override)
                # usamos wm_enabled (que pode ter vindo de um override anterior ou do banco)
                current_wm_val = 1 if wm_enabled else 0

                # Botão para inverter direção (Horizontal <-> Vertical)
                opposite_btn = []
                current_resize_val = 1 if use_resize else 0
                if direction == "horizontal":
                    opposite_text = get_text(user, context, "menu_merge_vertical")
                    opposite_btn = [
                        InlineKeyboardButton(
                            opposite_text,
                            callback_data=f"regen:vertical:{current_resize_val}:{current_wm_val}",
                        )
                    ]
                elif direction == "vertical":
                    opposite_text = get_text(user, context, "menu_merge_horizontal")
                    opposite_btn = [
                        InlineKeyboardButton(
                            opposite_text,
                            callback_data=f"regen:horizontal:{current_resize_val}:{current_wm_val}",
                        )
                    ]

                # Botão para inverter ordem
                reverse_text = get_text(user, context, "btn_reverse_order")
                reverse_btn = [
                    InlineKeyboardButton(
                        reverse_text,
                        callback_data=f"reverse:{direction}:{current_resize_val}:{current_wm_val}",
                    )
                ]

                # Linha de botões de regeneração (Resize e opcionalmente No Watermark)
                regen_row = [
                    InlineKeyboardButton(
                        regen_text,
                        callback_data=f"regen:{direction}:{regen_resize_val}:{current_wm_val}",
                    )
                ]

                # Se o watermark está habilitado NO BANCO, mostra opção de gerar sem
                if wm_enabled_db and wm_enabled:
                    regen_row.append(
                        InlineKeyboardButton(
                            get_text(user, context, "btn_no_watermark"),
                            callback_data=f"regen:{direction}:{current_resize_val}:0",
                        )
                    )

                # Botão para baixar como arquivo
                keyboard = [
                    [
                        InlineKeyboardButton(
                            get_text(user, context, "btn_file"),
                            callback_data=f"get_doc:{filename}",
                        ),
                        InlineKeyboardButton(
                            get_text(user, context, "pdf_btn"),
                            callback_data=f"get_pdf:{filename}",
                        ),
                        InlineKeyboardButton(
                            get_text(user, context, "btn_zip"),
                            callback_data=f"get_zip:{filename}",
                        ),
                    ],
                    regen_row,
                    reverse_btn + opposite_btn,
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                # Legenda de sucesso
                caption = get_text(
                    user, context, "success_caption", direction=dir_display
                )

                if img_w > 2560 or img_h > 2560:
                    caption += "\n\n" + get_text(user, context, "quality_warning")

                if status_msg:
                    try:
                        await status_msg.edit_text(
                            get_text(user, context, "uploading_msg")
                        )
                    except Exception:
                        pass

                if file_size > 10 * 1024 * 1024:
                    await update.effective_message.reply_html(
                        get_text(user, context, "dimensions_limit_warning")
                    )
                    await send_with_retry(
                        context.bot.send_document,
                        chat_id=update.effective_chat.id,
                        document=final_image_bytes,
                        filename=f"merged_{direction}.{ext}",
                        caption=caption,
                        read_timeout=60,
                        write_timeout=60,
                        parse_mode="HTML",
                    )
                else:
                    try:
                        await send_with_retry(
                            context.bot.send_photo,
                            chat_id=update.effective_chat.id,
                            photo=final_image_bytes,
                            caption=caption,
                            reply_markup=reply_markup,
                            read_timeout=60,
                            write_timeout=60,
                            parse_mode="HTML",
                        )
                    except BadRequest:
                        # Fallback para documento se der erro de dimensões (Photo_invalid_dimensions)
                        final_image_bytes.seek(0)
                        await update.effective_message.reply_html(
                            get_text(user, context, "dimensions_limit_warning")
                        )
                        await send_with_retry(
                            context.bot.send_document,
                            chat_id=update.effective_chat.id,
                            document=final_image_bytes,
                            filename=f"merged_{direction}.{ext}",
                            caption=caption,
                            read_timeout=60,
                            write_timeout=60,
                            parse_mode="HTML",
                        )
            finally:
                CURRENT_PROCESSING = None
                if status_msg:
                    try:
                        await status_msg.delete()
                    except Exception:
                        pass
    finally:
        # Garante que o usuário seja removido da fila se ocorrer erro antes do processamento
        if user_info in PROCESSING_QUEUE:
            PROCESSING_QUEUE.remove(user_info)

    if ADMIN_ID and user.id != ADMIN_ID and ADMIN_NOTIFICATIONS_ENABLED and user.id not in MUTED_USERS:
        notify_admin_background(context.bot, "🖼️ Imagem processada com sucesso para um usuário.")

    # Registra o log de criação
    if direction == "vertical":
        action_log = "merge_vertical"
    elif direction == "horizontal":
        action_log = "merge_horizontal"
    elif direction.startswith("grid"):
        action_log = "merge_grid"

    # Adiciona ao buffer
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    PENDING_LOGS.append((user_id, None, action_log, timestamp))


async def process_merge(
    update: Update, context: ContextTypes.DEFAULT_TYPE, direction: str
) -> None:
    """Lógica inicial para unir imagens (chamada pelos comandos)."""
    user = update.effective_user
    user_id = user.id

    # Rate Limit
    if await check_ad_quota_reached(update, context, user):
        return
    remaining = check_rate_limit(user_id)
    if remaining > 0:
        await update.message.reply_text(
            get_text(user, context, "rate_limit_error", seconds=remaining)
        )
        return
    update_rate_limit(user_id)

    # Para o log do admin, forçamos o português
    if direction.startswith("grid"):
        direction_pt = f"grade ({direction.split('_')[1]} colunas)"
    else:
        direction_pt = "vertical" if direction == "vertical" else "horizontal"
    action_desc = f"solicitou união {direction_pt}"
    await register_interaction(user, context, action_desc)

    # Limpeza preventiva: Remove arquivos de cache antigos deste usuário específico
    try:
        for f in glob.glob(os.path.join("cache", f"merged_{user_id}_*")):
            try:
                os.remove(f)
            except Exception:
                pass
    except Exception:
        pass

    async with aiosqlite.connect(DB_FILE) as db:
        # Busca imagens
        cursor = await db.execute(
            "SELECT file_id FROM user_images WHERE user_id = ? ORDER BY received_at ASC",
            (user_id,),
        )
        rows = await cursor.fetchall()

    if not rows or len(rows) < 2:
        await update.message.reply_text(get_text(user, context, "need_more_images"))
        return

    if len(rows) > MAX_IMAGES:
        await update.message.reply_text(
            get_text(user, context, "too_many_images", count=len(rows), max=MAX_IMAGES)
        )
        return

    # Salva em last_merge_files e limpa user_images
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("DELETE FROM last_merge_files WHERE user_id = ?", (user_id,))
        for i, row in enumerate(rows):
            await db.execute(
                "INSERT INTO last_merge_files (user_id, file_id, file_order) VALUES (?, ?, ?)",
                (user_id, row[0], i),
            )
        await db.execute("DELETE FROM user_images WHERE user_id = ?", (user_id,))
        await db.commit()

    await execute_merge(update, context, rows, direction)


async def handle_grid_columns_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Processa a escolha do número de colunas para a grade."""
    query = update.callback_query
    await query.answer()

    cols = query.data.split(":")[1]
    # Remove o menu de seleção
    await query.message.delete()
    await process_merge(update, context, f"grid_{cols}")


def apply_watermark(image: Image.Image, text: str, size: int, color_name: str, position: str, margin: int) -> Image.Image:
    """Aplica uma marca d'água de texto na imagem baseada nas configurações do usuário."""
    from PIL import ImageDraw, ImageFont

    # Cria uma cópia para não alterar a original se necessário (aqui já estamos com uma RGBA do merge)
    img = image.copy().convert("RGBA")
    draw = ImageDraw.Draw(img)

    # Tenta carregar uma fonte, fallback para default
    try:
        # Tenta carregar uma fonte sans-serif comum no sistema
        font_path = None
        if platform.system() == "Darwin": # macOS
            font_path = "/System/Library/Fonts/Supplemental/Arial.ttf"
        elif platform.system() == "Windows":
            font_path = "C:\\Windows\\Fonts\\arial.ttf"
        else: # Linux/Outros
            font_paths = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/TTF/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/freefont/FreeSans.ttf"
            ]
            for p in font_paths:
                if os.path.exists(p):
                    font_path = p
                    break

        if font_path and os.path.exists(font_path):
            font = ImageFont.truetype(font_path, size)
        else:
            font = ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()

    # Pega cor do dicionário global COLORS
    color_tuple = COLORS.get(color_name, ("WHITE", (255, 255, 255)))[1]
    # Adiciona canal Alpha (transparência leve de 180/255)
    fill_color = color_tuple + (180,)

    # Calcula dimensões do texto
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    text_width = right - left
    text_height = bottom - top

    # Calcula coordenadas baseadas na posição
    w, h = img.size

    if position == "top_left":
        coords = (margin, margin)
    elif position == "top_center":
        coords = ((w - text_width) // 2, margin)
    elif position == "top_right":
        coords = (w - text_width - margin, margin)
    elif position == "middle_left":
        coords = (margin, (h - text_height) // 2)
    elif position == "middle_center":
        coords = ((w - text_width) // 2, (h - text_height) // 2)
    elif position == "middle_right":
        coords = (w - text_width - margin, (h - text_height) // 2)
    elif position == "bottom_left":
        coords = (margin, h - text_height - margin)
    elif position == "bottom_center":
        coords = ((w - text_width) // 2, h - text_height - margin)
    else: # bottom_right
        coords = (w - text_width - margin, h - text_height - margin)

    # Aplica o texto
    draw.text(coords, text, font=font, fill=fill_color)

    return img


def _merge_images_task(
    image_bytes_list: list[bytes],
    direction: str,
    output_format: str,
    quality: int,
    bg_color: str,
    auto_resize: bool = True,
    border_width: int = 0,
    border_color: str = "WHITE",
    watermark_settings: dict | None = None,
) -> bytes:
    """Função bloqueante que processa a união das imagens (Vertical, Horizontal ou Grade). Contém a lógica de bordas, redimensionamento, colagem e salvamento."""
    try:
        images = [Image.open(io.BytesIO(b)) for b in image_bytes_list]
    except Image.DecompressionBombError as e:
        # Loga o erro e lança uma exceção que pode ser tratada pelo handler que chamou a função
        logger.error(f"Ataque de Decompression Bomb detectado em _merge_images_task: {e}")
        raise ValueError(
            "Uma das imagens é uma 'bomba de descompressão' e não pode ser processada."
        ) from e

    # Adiciona borda se necessário
    if border_width > 0:
        # Fallback para branco se a cor não estiver no mapa
        border_color_tuple = (255, 255, 255)

        if border_color in COLORS:
            border_color_tuple = COLORS[border_color][1]
        elif border_color.startswith("#"):
            # Tenta converter Hex
            try:
                h = border_color.lstrip("#")
                border_color_tuple = tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))
            except:
                pass
        elif "," in border_color:
            # Tenta converter RGB string
            try:
                border_color_tuple = tuple(map(int, border_color.split(",")))
            except:
                pass

        images_with_border = []
        for img in images:
            # Cria uma tela RGBA para a borda para garantir compatibilidade com imagens transparentes
            new_size = (img.width + 2 * border_width, img.height + 2 * border_width)
            border_canvas = Image.new("RGBA", new_size, border_color_tuple + (255,))

            # Cola a imagem original (pode ser RGBA ou RGB) na tela
            border_canvas.paste(
                img,
                (border_width, border_width),
                mask=img if "A" in img.getbands() else None,
            )

            images_with_border.append(border_canvas)
        images = images_with_border

    # Garante que todas as imagens estão em modo RGBA para o resto do processamento de união
    images = [img.convert("RGBA") for img in images]

    if direction == "horizontal" and auto_resize:
        # Encontra a menor altura para redimensionar as maiores por ela
        min_height = min(img.size[1] for img in images)
        resized_images = []
        for img in images:
            if img.size[1] > min_height:
                ratio = min_height / img.size[1]
                new_width = int(img.size[0] * ratio)
                resized_images.append(
                    img.resize((new_width, min_height), Image.Resampling.LANCZOS)
                )
            else:
                resized_images.append(img)
        images = resized_images

    if direction == "vertical" and auto_resize:
        # Encontra a menor largura para redimensionar as maiores por ela
        min_width = min(img.size[0] for img in images)
        resized_images = []
        for img in images:
            if img.size[0] > min_width:
                ratio = min_width / img.size[0]
                new_height = int(img.size[1] * ratio)
                resized_images.append(
                    img.resize((min_width, new_height), Image.Resampling.LANCZOS)
                )
            else:
                resized_images.append(img)
        images = resized_images

    widths, heights = zip(*(i.size for i in images))

    if direction.startswith("grid"):
        cols = int(direction.split("_")[1])
        # Divide as imagens em linhas
        rows_of_images = [images[i : i + cols] for i in range(0, len(images), cols)]

        row_heights = []
        total_height = 0
        for row_imgs in rows_of_images:
            h = max(img.size[1] for img in row_imgs)
            row_heights.append(h)
            total_height += h

        # Largura total é a máxima soma das larguras das linhas
        total_width = max(sum(img.size[0] for img in row) for row in rows_of_images)

    elif direction == "vertical":
        total_width = max(widths)
        total_height = sum(heights)
    else:
        total_width = sum(widths)
        total_height = max(heights)

    # Cria uma nova imagem em branco
    new_im = Image.new("RGBA", (total_width, total_height))

    offset = 0
    for im in images:
        if direction.startswith("grid"):
            # Lógica de grade já processada acima para dimensões, agora colagem
            pass  # Loop diferente abaixo
        elif direction == "vertical":
            x_offset = (total_width - im.size[0]) // 2
            new_im.paste(im, (x_offset, offset))
            offset += im.size[1]
        else:
            y_offset = (total_height - im.size[1]) // 2
            new_im.paste(im, (offset, y_offset))
            offset += im.size[0]

    if direction.startswith("grid"):
        y_offset = 0
        for i, row_imgs in enumerate(rows_of_images):
            x_offset = 0
            row_h = row_heights[i]
            for im in row_imgs:
                # Centraliza verticalmente na célula
                y_pos = y_offset + (row_h - im.size[1]) // 2
                # Cola
                new_im.paste(im, (x_offset, y_pos))
                x_offset += im.size[0]
            y_offset += row_h

    # Aplica marca d'água se habilitada
    if watermark_settings and watermark_settings.get("enabled"):
        new_im = apply_watermark(
            new_im,
            text=watermark_settings.get("text", "UnifyImages"),
            size=watermark_settings.get("size", 30),
            color_name=watermark_settings.get("color", "WHITE"),
            position=watermark_settings.get("position", "bottom_right"),
            margin=watermark_settings.get("margin", 20)
        )

    # Tratamento para formatos que não suportam transparência
    save_fmt = output_format.upper()
    if save_fmt == "JPG":
        save_fmt = "JPEG"

    save_params = {}
    if save_fmt == "JPEG":
        save_params["quality"] = quality
        save_params["optimize"] = True
    elif save_fmt == "WEBP":
        save_params["quality"] = quality
    elif save_fmt == "PNG":
        save_params["optimize"] = True

    if save_fmt in ["JPEG", "BMP"]:
        bg_tuple = (0, 0, 0) if bg_color == "BLACK" else (255, 255, 255)
        bg = Image.new("RGB", new_im.size, bg_tuple)
        if new_im.mode == "RGBA":
            bg.paste(new_im, mask=new_im.split()[3])
        else:
            bg.paste(new_im)
        new_im = bg

    # Salva a imagem final em um buffer de bytes
    final_buffer = io.BytesIO()
    new_im.save(final_buffer, format=save_fmt, **save_params)

    return final_buffer.getvalue()





def _get_image_metadata_task(image_bytes: bytes) -> str:
    """Extrai metadados de imagem para exibição."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        lines = []

        # Info básica
        lines.append(f"<b>Format:</b> {img.format}")
        lines.append(f"<b>Mode:</b> {img.mode}")
        lines.append(f"<b>Size:</b> {img.width}x{img.height}")

        # EXIF
        if hasattr(img, "getexif"):
            exif = img.getexif()
            if exif:
                lines.append("\n<b>EXIF:</b>")
                for k, v in exif.items():
                    name = ExifTags.TAGS.get(k, str(k))
                    val_str = str(v)
                    if len(val_str) > 50: val_str = val_str[:47] + "..."
                    lines.append(f"{name}: {html.escape(val_str)}")

        # Info genérica
        if img.info:
            lines.append("\n<b>Info:</b>")
            for k, v in img.info.items():
                if k in ["exif", "icc_profile"]: continue # Pula blobs binários
                val_str = str(v)
                if len(val_str) > 50: val_str = val_str[:47] + "..."
                lines.append(f"{k}: {html.escape(val_str)}")

        return "\n".join(lines) if lines else ""
    except Exception:
        return ""


def _get_pdf_metadata_task(pdf_bytes: bytes) -> str:
    """Extrai metadados de PDF para exibição."""
    try:
        info = pdfinfo_from_bytes(bytes(pdf_bytes))
        lines = []
        for k, v in info.items():
            val_str = str(v)
            if len(val_str) > 100: val_str = val_str[:97] + "..."
            lines.append(f"<b>{k}:</b> {html.escape(val_str)}")
        return "\n".join(lines)
    except Exception:
        return ""


def _remove_pdf_metadata_task(pdf_bytes: bytes) -> tuple[bytes, list[tuple[str, str]]]:
    """Remove metadados de um arquivo PDF usando PyMuPDF."""
    removed_tags = []
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if doc.metadata:
            for k, v in doc.metadata.items():
                if v and str(v).strip():
                    val_str = str(v)
                    if len(val_str) > 50: val_str = val_str[:47] + "..."
                    removed_tags.append((k, val_str))
        doc.set_metadata({})
        clean_bytes = doc.tobytes(garbage=4, clean=True, deflate=True)
        doc.close()
        return clean_bytes, removed_tags
    except Exception as e:
        logger.error(f"Erro ao remover metadados do PDF: {e}")
        return pdf_bytes, []


def _convert_pdf_to_docx_task(pdf_bytes: bytes) -> bytes:
    """Converte bytes de PDF em bytes de DOCX usando pdf2docx (executado em processo separado)."""
    import tempfile
    from pdf2docx import Converter

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
        tmp_pdf.write(pdf_bytes)
        tmp_pdf_path = tmp_pdf.name

    tmp_docx_path = tmp_pdf_path.replace(".pdf", ".docx")

    try:
        cv = Converter(tmp_pdf_path)
        cv.convert(tmp_docx_path)
        cv.close()

        with open(tmp_docx_path, "rb") as f:
            return f.read()
    finally:
        import os as _os
        _os.unlink(tmp_pdf_path)
        if _os.path.exists(tmp_docx_path):
            _os.unlink(tmp_docx_path)


def _extract_docx_text_task(docx_bytes: bytes) -> str:
    """Extrai o texto de um arquivo DOCX usando python-docx (executado em processo separado)."""
    from docx import Document as DocxDocument

    doc = DocxDocument(io.BytesIO(docx_bytes))
    lines = []
    for para in doc.paragraphs:
        if para.text.strip():
            lines.append(para.text)
    # Incluir texto de tabelas
    for table in doc.tables:
        for row in table.rows:
            row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
            if row_text:
                lines.append(row_text)
    return "\n".join(lines)


def _convert_docx_to_pdf_task(docx_bytes: bytes) -> bytes:
    """
    Converte bytes de DOCX em bytes de PDF usando LibreOffice via subprocess.
    Requer LibreOffice instalado no sistema (soffice no PATH).
    """
    import tempfile
    import subprocess
    import os as _os

    with tempfile.TemporaryDirectory() as tmp_dir:
        docx_path = _os.path.join(tmp_dir, "input.docx")
        pdf_path = _os.path.join(tmp_dir, "input.pdf")

        with open(docx_path, "wb") as f:
            f.write(docx_bytes)

        result = subprocess.run(
            [
                "soffice",
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                tmp_dir,
                docx_path,
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            raise RuntimeError(f"LibreOffice falhou: {result.stderr}")

        if not _os.path.exists(pdf_path):
            raise FileNotFoundError("PDF não foi gerado pelo LibreOffice.")

        with open(pdf_path, "rb") as f:
            return f.read()


def _extract_docx_pages_task(docx_bytes: bytes) -> bytes:
    """
    Extrai cada página do DOCX como imagem e devolve um ZIP.
    Converte DOCX→PDF via LibreOffice, depois PDF→imagens via PyMuPDF.
    """
    pdf_bytes = _convert_docx_to_pdf_task(docx_bytes)
    images = convert_from_bytes(pdf_bytes, dpi=150)

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, img in enumerate(images, start=1):
            img_buffer = io.BytesIO()
            img.save(img_buffer, format="PNG")
            zf.writestr(f"page_{i:03d}.png", img_buffer.getvalue())

    return zip_buffer.getvalue()


def _remove_metadata_task(image_bytes: bytes) -> tuple[bytes, list[tuple[str, str]]]:
    """Remove metadados criando uma nova imagem limpa e retorna lista de (tag, valor_original)."""
    removed_tags = []
    try:
        try:
            img = Image.open(io.BytesIO(image_bytes))
        except Image.DecompressionBombError as e:
            logger.error(f"Ataque de Decompression Bomb detectado em _remove_metadata_task: {e}")
            raise ValueError(
                "A imagem é uma 'bomba de descompressão' e não pode ser processada."
            ) from e

        # Coleta metadados EXIF
        if hasattr(img, "getexif"):
            exif = img.getexif()
            if exif:
                for k, v in exif.items():
                    name = ExifTags.TAGS.get(k, str(k))
                    # Formata o valor para string e trunca se for muito longo
                    val_str = str(v)
                    if len(val_str) > 50:
                        val_str = val_str[:47] + "..."
                    removed_tags.append((name, val_str))

        # Coleta outros metadados em info (ICC, XMP, etc)
        if img.info:
            for k, v in img.info.items():
                if k not in ["dpi", "compression", "exif"]:
                    val_str = str(v)
                    if len(val_str) > 50:
                        val_str = val_str[:47] + "..."
                    removed_tags.append((k, val_str))

        # Cria uma nova imagem e copia os dados de pixel
        # Isso descarta EXIF e outros metadados
        clean_img = Image.new(img.mode, img.size)
        clean_img.paste(img)

        out = io.BytesIO()
        # Tenta manter o formato original, fallback para JPEG
        fmt = img.format if img.format else "JPEG"
        clean_img.save(out, format=fmt, quality=100)

        # Remove duplicatas e ordena
        unique_tags = sorted(list(set(removed_tags)), key=lambda x: x[0])
        return out.getvalue(), unique_tags
    except Exception:
        return image_bytes, []


@base_handler_checks
async def remove_metadata_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Remove metadados das imagens (apenas arquivos)."""
    user = update.effective_user
    # Rate Limit
    if await check_ad_quota_reached(update, context, user):
        return
    remaining = check_rate_limit(user.id)
    if remaining > 0:
        await update.message.reply_text(
            get_text(user, context, "rate_limit_error", seconds=remaining)
        )
        return
    update_rate_limit(user.id)

    async with aiosqlite.connect(DB_FILE) as db:
        # Verifica total
        async with db.execute(
            "SELECT COUNT(*) FROM user_images WHERE user_id = ?", (user.id,)
        ) as cursor:
            total_images = (await cursor.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(*) FROM user_pdfs WHERE user_id = ?", (user.id,)
        ) as cursor:
            total_pdfs = (await cursor.fetchone())[0]

        if total_images == 0 and total_pdfs == 0:
            await update.message.reply_text(get_text(user, context, "need_one_image"))
            return

        # Verifica quantos são documentos
        async with db.execute(
            "SELECT COUNT(*) FROM user_images WHERE user_id = ? AND is_document = 1",
            (user.id,),
        ) as cursor:
            docs_count = (await cursor.fetchone())[0]

    # Se não houver documentos nem PDFs (apenas fotos comprimidas)
    if docs_count == 0 and total_pdfs == 0:
        await update.message.reply_html(get_text(user, context, "metadata_not_needed"))
        return

    # Processa PDFs se houver
    if total_pdfs > 0:
        await process_pdf_metadata_removal(update, context)

    if total_images == 0:
        return

    # Se houver mistura ou apenas documentos, processa apenas os documentos
    await process_metadata_removal(update, context)


async def process_metadata_removal(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    user = update.effective_user

    async with aiosqlite.connect(DB_FILE) as db:
        # Pega apenas documentos
        cursor = await db.execute(
            "SELECT file_id FROM user_images WHERE user_id = ? AND is_document = 1 ORDER BY received_at ASC",
            (user.id,),
        )
        rows = await cursor.fetchall()

    if not rows:
        return

    await update.message.reply_text(
        get_text(user, context, "processing_metadata", count=len(rows))
    )

    # Reutiliza lógica de download
    async def download_image(file_id: str):
        try:
            new_file = await context.bot.get_file(file_id)
            f_bytes = await new_file.download_as_bytearray()
            return file_id, f_bytes
        except Exception:
            return file_id, None

    tasks = [download_image(row[0]) for row in rows]
    results = await asyncio.gather(*tasks)

    loop = asyncio.get_running_loop()

    for fid, content in results:
        if not content:
            continue

        try:
            clean_bytes, removed_tags = await loop.run_in_executor(
                PROCESS_POOL, _remove_metadata_task, bytes(content)
            )
            f_io = io.BytesIO(clean_bytes)
        except ValueError as e: # Captura o erro da Decompression Bomb
            await context.bot.send_message(
                chat_id=user.id,
                text=f"❌ Erro ao processar um dos arquivos: {e}",
                parse_mode="HTML",
            )
            continue

        f_io.name = f"clean_{fid[:8]}.jpg"  # Nome genérico, o formato real é detectado pelo header

        # Atualiza estatísticas e notifica admin
        if removed_tags:
            async with aiosqlite.connect(DB_FILE) as db:
                for tag_name, _ in removed_tags:
                    await db.execute(
                        "INSERT INTO metadata_stats (tag_name, removal_count) VALUES (?, 1) ON CONFLICT(tag_name) DO UPDATE SET removal_count = removal_count + 1",
                        (tag_name,),
                    )
                await db.commit()

        if ADMIN_ID and user.id != ADMIN_ID and ADMIN_NOTIFICATIONS_ENABLED and user.id not in MUTED_USERS:
            if removed_tags:
                msg_admin = "🛡️ Metadados removidos de um arquivo do usuário."
            else:
                msg_admin = "🛡️ Metadados processados; nenhuma tag encontrada."
            notify_admin_background(context.bot, msg_admin)

        # Log de atividade (por arquivo)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        PENDING_LOGS.append((user.id, None, "metadata_removed", timestamp))

        caption = get_text(user, context, "metadata_removed")
        if removed_tags:
            # Limita a quantidade de tags para não poluir o chat
            caption += "\n\n🗑️ <b>Tags:</b>"
            for i, (tag_name, tag_val) in enumerate(removed_tags):
                if i >= 20:  # Limite de 20 linhas
                    caption += f"\n... (+{len(removed_tags) - 20})"
                    break
                caption += f"\n• <b>{html.escape(tag_name)}:</b> {html.escape(tag_val)}"

        try:
            await context.bot.send_document(
                chat_id=user.id, document=f_io, caption=caption, parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Erro ao enviar arquivo limpo: {e}")

    # Limpa a lista
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("DELETE FROM user_images WHERE user_id = ?", (user.id,))
        await db.commit()


async def process_pdf_metadata_removal(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Processa a remoção de metadados para PDFs."""
    user = update.effective_user

    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute(
            "SELECT file_id, file_name FROM user_pdfs WHERE user_id = ? ORDER BY received_at ASC",
            (user.id,),
        )
        rows = await cursor.fetchall()

    if not rows:
        return

    await update.message.reply_text(
        get_text(user, context, "processing_metadata", count=len(rows))
    )

    tasks = [context.bot.get_file(row[0]) for row in rows]
    files = await asyncio.gather(*tasks)
    content_tasks = [f.download_as_bytearray() for f in files]
    pdf_contents = await asyncio.gather(*content_tasks)

    loop = asyncio.get_running_loop()

    for i, content in enumerate(pdf_contents):
        try:
            clean_bytes, removed_tags = await loop.run_in_executor(
                PROCESS_POOL, _remove_pdf_metadata_task, bytes(content)
            )
            f_io = io.BytesIO(clean_bytes)

            original_name = rows[i][1] or f"file_{i}.pdf"
            f_io.name = f"clean_{original_name}"

            caption = get_text(user, context, "metadata_removed")

            if removed_tags:
                caption += "\n\n🗑️ <b>Tags:</b>"
                for idx, (tag_name, tag_val) in enumerate(removed_tags):
                    if idx >= 20:
                        caption += f"\n... (+{len(removed_tags) - 20})"
                        break
                    caption += f"\n• <b>{html.escape(tag_name)}:</b> {html.escape(tag_val)}"

            await context.bot.send_document(
                chat_id=user.id, document=f_io, caption=caption, parse_mode="HTML"
            )

            # Log
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            PENDING_LOGS.append((user.id, None, "metadata_removed_pdf", timestamp))

        except Exception as e:
            logger.error(f"Erro ao remover metadados de PDF: {e}")
            err_msg = get_text(user, context, "err_processing_pdf", e=str(e))
            await context.bot.send_message(chat_id=user.id, text=err_msg)

    # Limpa a lista de PDFs
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("DELETE FROM user_pdfs WHERE user_id = ?", (user.id,))
        await db.commit()


# Estados do ConversationHandler para Remover Fundo
REMBG_FORMAT, REMBG_AGRESSIVENESS = range(2)

# Estados do ConversationHandler para Meme
MEME_IMAGE, MEME_TOP_TEXT, MEME_BOTTOM_TEXT = range(2, 5)

def _get_meme_font_path():
    """Tenta encontrar um caminho de fonte Bold disponível no sistema."""
    # Prioridade 1: Utilizar o gerenciador de fontes do matplotlib (robusto contra mudanças de estrutura, ex: v3.11.0)
    try:
        import matplotlib.font_manager as fm
        font_prop = fm.FontProperties(family='DejaVu Sans', weight='bold')
        font_path = fm.findfont(font_prop, fallback_to_default=True)
        if font_path and os.path.exists(str(font_path)):
            return str(font_path)
    except Exception as e:
        logger.warning(f"Aviso ao buscar fonte via matplotlib: {e}")

    # Prioridade 2: Caminhos comuns do Linux
    linux_fonts = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"
    ]
    for pf in linux_fonts:
        if os.path.exists(pf):
            return pf

    return None

def _remove_bg_task(imgs_data: list, fmt: str, alpha_bg: int, alpha_fg: int) -> list:
    """Remove o fundo de uma lista de imagens com agressividade configurável."""
    try:
        import onnxruntime as ort
        from rembg import remove, new_session
    except ImportError:
        return [b"ERROR_REMBG_NOT_INSTALLED"] * len(imgs_data)

    session_options = ort.SessionOptions()
    session_options.intra_op_num_threads = 2
    session_options.inter_op_num_threads = 2
    # O modelo 'u2netp' (versão leve/mobile) tem apenas ~4.7MB (vs 176MB do u2net),
    # é 3x a 5x mais rápido em CPU e consome muito menos RAM mantendo excelente qualidade.
    my_session = new_session("u2netp", providers=["CPUExecutionProvider"], sess_opts=session_options)

    results = []
    try:
        for content in imgs_data:
            try:
                output = remove(
                    content,
                    session=my_session,
                    alpha_matting=True,
                    alpha_matting_foreground_threshold=alpha_fg,
                    alpha_matting_background_threshold=alpha_bg,
                    alpha_matting_erode_size=10
                )
                results.append(output)
            except Exception as e:
                results.append(str(e).encode('utf-8'))
    finally:
        # Remove a sessão do ONNX para liberar memória e chama o Garbage Collector
        del my_session
        import gc
        gc.collect()

    return results


@base_handler_checks
async def remove_bg_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia o fluxo para remover o fundo das imagens na fila."""
    user = update.effective_user
    await register_interaction(user, context, "Abriu remove_bg")

    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM user_images WHERE user_id = ?", (user.id,)
        ) as cursor:
            count = (await cursor.fetchone())[0]

    if count == 0:
        await update.message.reply_html(get_text(user, context, "remove_bg_empty"))
        return ConversationHandler.END

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(get_text(user, context, "remove_bg_png"), callback_data="rembg:PNG"),
                InlineKeyboardButton(get_text(user, context, "remove_bg_webp"), callback_data="rembg:WEBP"),
            ]
        ]
    )
    await update.message.reply_html(
        get_text(user, context, "remove_bg_format"), reply_markup=keyboard
    )
    return REMBG_FORMAT


async def remove_bg_choose_format(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recebe o formato e pede o nível de agressividade."""
    query = update.callback_query
    await query.answer()

    user = query.from_user
    context.user_data["rembg_fmt"] = query.data.split(":")[1]

    await query.edit_message_text(
        get_text(user, context, "remove_bg_ask_aggressiveness"), parse_mode="HTML"
    )
    return REMBG_AGRESSIVENESS


async def remove_bg_process(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processa o callback de remoção com a agressividade escolhida."""
    user = update.effective_user
    text = update.message.text.strip()

    # Validação do número (0-100)
    if not text.isdigit() or not (0 <= int(text) <= 100):
        await update.message.reply_html(get_text(user, context, "remove_bg_invalid_number"))
        return REMBG_AGRESSIVENESS

    agressividade = int(text)
    fmt_escolhido = context.user_data.get("rembg_fmt", "PNG")

    # Cálculo: foreground diminui e background diminui proporcionalmente à agressividade
    # Se agressividade = 10 (recomendado): FG = 240, BG = 10
    # Se agressividade = 100 (máxima): FG = 150, BG = 100
    alpha_fg = int(250 - agressividade)
    alpha_bg = agressividade

    # Rate Limit
    if await check_ad_quota_reached(update, context, user):
        return
    remaining = check_rate_limit(user.id)
    if remaining > 0:
        await update.message.reply_text(get_text(user, context, "rate_limit_error", seconds=remaining))
        return ConversationHandler.END
    update_rate_limit(user.id)

    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute(
            "SELECT file_id, file_name, file_fmt FROM user_images WHERE user_id = ? ORDER BY received_at ASC",
            (user.id,),
        )
        imgs = await cursor.fetchall()

    count = len(imgs)
    if count == 0:
        await update.message.reply_html(get_text(user, context, "remove_bg_empty"))
        return ConversationHandler.END

    # A notificação ao admin será enviada individualmente para cada imagem processada

    # Spinner
    stop_event = asyncio.Event()
    spinner_text = get_text(user, context, "removing_bg", count=count)
    spinner_message = await update.message.reply_html(spinner_text)
    spinner_future = asyncio.create_task(spinner_task(spinner_message, spinner_text, stop_event))

    try:
        tasks_files = [context.bot.get_file(row[0]) for row in imgs]
        files = await asyncio.gather(*tasks_files)
        contents = await asyncio.gather(*[f.download_as_bytearray() for f in files])
        imgs_data = [bytes(c) for c in contents]

        loop = asyncio.get_running_loop()
        results = await loop.run_in_executor(PROCESS_POOL, _remove_bg_task, imgs_data, fmt_escolhido, alpha_bg, alpha_fg)

        ext = fmt_escolhido.lower()

        for i, (result_bytes, row) in enumerate(zip(results, imgs)):
            if result_bytes == b"ERROR_REMBG_NOT_INSTALLED":
                await context.bot.send_message(
                    chat_id=user.id,
                    text=get_text(user, context, "err_rembg_not_installed")
                )
                break

            original_name = row[1]
            if original_name:
                name_base = os.path.splitext(original_name)[0]
                new_name = f"{name_base}_nobg.{ext}"
            else:
                new_name = f"image_{i+1}_nobg.{ext}"

            img_io = io.BytesIO(result_bytes)
            img_io.name = new_name
            await context.bot.send_document(chat_id=user.id, document=img_io)

            await register_interaction(user, context, f"Removeu fundo ({new_name})")

        async with aiosqlite.connect(DB_FILE) as db:
            await db.execute("DELETE FROM user_images WHERE user_id = ?", (user.id,))
            await db.commit()

    except Exception as e:
        logger.error(f"Erro na remoção de fundo (rembg): {e}")
        await context.bot.send_message(
            chat_id=user.id, text=get_text(user, context, "remove_bg_error")
        )
    finally:
        stop_event.set()
        await spinner_future
        await spinner_message.delete()

    context.user_data.pop("rembg_fmt", None)
    return ConversationHandler.END


async def remove_bg_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela o fluxo de remoção de fundo."""
    user = update.effective_user
    await update.message.reply_html(get_text(user, context, "cancel", count=0))
    context.user_data.pop("rembg_fmt", None)
    return ConversationHandler.END


def _generate_meme_task(image_bytes: bytes, top_text: str, bottom_text: str, font_path: str = None, multiplier: float = 1.0) -> bytes:
    """Tarefa CPU-bound para formatar imagem como meme usando Pillow."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.open(io.BytesIO(image_bytes))

        # Converte para RGB se necessário
        if img.mode != "RGB":
            img = img.convert("RGB")

        w, h = img.size
        draw = ImageDraw.Draw(img)

        # Tamanho básico da fonte: ~8% da altura da imagem * multiplicador
        font_size = int(h * 0.08 * multiplier)
        if font_size < 12: font_size = 12

        # Tenta carregar a fonte
        try:
            if font_path and os.path.exists(font_path):
                font = ImageFont.truetype(font_path, font_size)
            else:
                font = ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()

        def draw_text_with_outline(text, position_y, is_top=True):
            if not text or text == ".": return

            text = text.upper()
            # Wrap text if too long
            lines = []
            words = text.split()
            current_line = []
            for word in words:
                test_line = " ".join(current_line + [word])
                bbox = draw.textbbox((0, 0), test_line, font=font)
                if bbox[2] - bbox[0] < w * 0.9 or not current_line:
                    current_line.append(word)
                else:
                    lines.append(" ".join(current_line))
                    current_line = [word]
            lines.append(" ".join(current_line))

            # Desenha cada linha
            line_height = draw.textbbox((0, 0), "Ay", font=font)[3] - draw.textbbox((0, 0), "Ay", font=font)[1]
            total_h = len(lines) * line_height

            start_y = position_y if is_top else position_y - total_h

            for i, line in enumerate(lines):
                bbox = draw.textbbox((0, 0), line, font=font)
                line_w = bbox[2] - bbox[0]
                lx = (w - line_w) // 2
                ly = start_y + (i * line_height)

                # Outline (Black)
                for ox, oy in [(-2,-2), (2,-2), (-2,2), (2,2), (0,-2), (0,2), (-2,0), (2,0)]:
                    draw.text((lx+ox, ly+oy), line, font=font, fill="black")

                # Text (White)
                draw.text((lx, ly), line, font=font, fill="white")

        # Top
        draw_text_with_outline(top_text, int(h * 0.02), is_top=True)
        # Bottom
        draw_text_with_outline(bottom_text, int(h * 0.98), is_top=False)

        out = io.BytesIO()
        img.save(out, format="JPEG", quality=90)

        # Salva cópia para relatório diário


        return out.getvalue()
    except Exception as e:
        logger.error(f"Erro no _generate_meme_task: {e}")
        return image_bytes


@base_handler_checks
async def meme_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia o fluxo do Meme."""
    user = update.effective_user
    await register_interaction(user, context, "Iniciou Meme")

    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM user_images WHERE user_id = ?", (user.id,)
        ) as cursor:
            count = (await cursor.fetchone())[0]

    if count > 0:
        # Se já tem imagem na fila, pergunta se quer usar a última
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(get_text(user, context, "meme_use_last"), callback_data="meme:use_last")],
            [InlineKeyboardButton(get_text(user, context, "meme_send_new"), callback_data="meme:new")]
        ])
        await update.message.reply_html(get_text(user, context, "meme_ask_image"), reply_markup=keyboard)
        return MEME_IMAGE
    else:
        await update.message.reply_html(get_text(user, context, "meme_send_image_first"))
        return MEME_IMAGE


async def meme_receive_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recebe a imagem para o meme ou trata o callback."""
    user = update.effective_user

    if update.callback_query:
        query = update.callback_query
        await query.answer()
        if query.data == "meme:use_last":
            async with aiosqlite.connect(DB_FILE) as db:
                cursor = await db.execute(
                    "SELECT file_id FROM user_images WHERE user_id = ? ORDER BY received_at DESC LIMIT 1",
                    (user.id,)
                )
                row = await cursor.fetchone()
                if row:
                    context.user_data["meme_file_id"] = row[0]
                    # Adiciona botões de pular e cancelar
                    keyboard = InlineKeyboardMarkup([
                        [
                            InlineKeyboardButton(get_text(user, context, "btn_skip"), callback_data="meme:skip_top"),
                            InlineKeyboardButton(get_text(user, context, "menu_cancel"), callback_data="meme:cancel")
                        ]
                    ])
                    await query.edit_message_text(get_text(user, context, "meme_send_top_text"), parse_mode="HTML", reply_markup=keyboard)
                    return MEME_TOP_TEXT

        await query.edit_message_text(get_text(user, context, "meme_send_image_first"), parse_mode="HTML")
        return MEME_IMAGE

    if not update.message.photo and not update.message.document:
        await update.message.reply_html(get_text(user, context, "error_only_image"))
        return MEME_IMAGE

    # Se enviou uma nova, salva o file_id e prossegue
    if update.message.photo:
        fid = update.message.photo[-1].file_id
    else:
        fid = update.message.document.file_id

    context.user_data["meme_file_id"] = fid
    # Adiciona botões de pular e cancelar
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(get_text(user, context, "btn_skip"), callback_data="meme:skip_top"),
            InlineKeyboardButton(get_text(user, context, "menu_cancel"), callback_data="meme:cancel")
        ]
    ])
    await update.message.reply_html(get_text(user, context, "meme_send_top_text"), reply_markup=keyboard)
    return MEME_TOP_TEXT


async def meme_receive_top_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recebe o texto do topo ou trata o callback de pular."""
    user = update.effective_user

    if update.callback_query:
        query = update.callback_query
        await query.answer()
        context.user_data["meme_top"] = ""
        # Adiciona botões de pular e cancelar
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(get_text(user, context, "btn_skip"), callback_data="meme:skip_bottom"),
                InlineKeyboardButton(get_text(user, context, "menu_cancel"), callback_data="meme:cancel")
            ]
        ])
        await query.edit_message_text(get_text(user, context, "meme_send_bottom_text"), parse_mode="HTML", reply_markup=keyboard)
        return MEME_BOTTOM_TEXT

    content = update.message.text
    if content == ".":
        context.user_data["meme_top"] = ""
    else:
        context.user_data["meme_top"] = content

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(get_text(user, context, "btn_skip"), callback_data="meme:skip_bottom"),
            InlineKeyboardButton(get_text(user, context, "menu_cancel"), callback_data="meme:cancel")
        ]
    ])
    await update.message.reply_html(get_text(user, context, "meme_send_bottom_text"), reply_markup=keyboard)
    return MEME_BOTTOM_TEXT


async def meme_receive_bottom_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recebe o texto da base e processa."""
    user = update.effective_user

    bottom_text = ""
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        bottom_text = ""
        # Remove teclado da mensagem anterior
        await query.edit_message_reply_markup(reply_markup=None)
    else:
        bottom_text = update.message.text
        if bottom_text == ".":
            bottom_text = ""

    top_text = context.user_data.get("meme_top", "")
    file_id = context.user_data.get("meme_file_id")

    if not file_id:
        msg = get_text(user, context, "err_image_lost")
        if update.callback_query:
            await update.callback_query.message.reply_html(msg)
        else:
            await update.message.reply_html(msg)
        return ConversationHandler.END

    status_txt = get_text(user, context, "meme_processing")
    if update.callback_query:
        status_msg = await update.callback_query.message.reply_html(status_txt)
    else:
        status_msg = await update.message.reply_html(status_txt)

    try:
        file = await context.bot.get_file(file_id)
        content = await file.download_as_bytearray()

        loop = asyncio.get_running_loop()
        font_path = _get_meme_font_path()

        result_bytes = await loop.run_in_executor(
            PROCESS_POOL, _generate_meme_task, bytes(content), top_text, bottom_text, font_path, 1.0
        )

        f_io = io.BytesIO(result_bytes)
        f_io.name = "meme.jpg"

        # Keyboard para redimensionar o texto
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(get_text(user, context, "btn_meme_smaller"), callback_data="meme:resize:0.8"),
                InlineKeyboardButton(get_text(user, context, "btn_meme_larger"), callback_data="meme:resize:1.2")
            ]
        ])

        sent_msg = await context.bot.send_photo(
            chat_id=user.id,
            photo=f_io,
            caption="🎭 #meme",
            reply_markup=keyboard
        )

        # Salva metadados para redimensionamento posterior
        # Chave é o message_id da foto enviada
        context.user_data[f"meme_meta_{sent_msg.message_id}"] = {
            "file_id": file_id,
            "top": top_text,
            "bottom": bottom_text,
            "multiplier": 1.0
        }

        # Registra interação com ação específica para estatísticas
        await register_interaction(user, context, "meme_created")

    except Exception as e:
        logger.error(f"Erro ao processar meme: {e}")
        error_msg = get_text(user, context, "err_meme_creation", e=str(e))
        if update.callback_query:
            await update.callback_query.message.reply_html(error_msg)
        else:
            await update.message.reply_html(error_msg)
    finally:
        if 'status_msg' in locals():
            await status_msg.delete()
        context.user_data.pop("meme_file_id", None)
        context.user_data.pop("meme_top", None)

    return ConversationHandler.END


async def meme_resize_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ajusta o tamanho do texto do meme via callback."""
    query = update.callback_query
    user = update.effective_user
    await query.answer()

    msg_id = query.message.message_id
    meta_key = f"meme_meta_{msg_id}"
    meta = context.user_data.get(meta_key)

    if not meta:
        await query.message.reply_html(get_text(user, context, "err_session_expired_simple"))
        return

    # Extrai o fator de ajuste do callback_data (ex: meme:resize:1.2)
    try:
        adjustment = float(query.data.split(":")[-1])
        new_multiplier = meta["multiplier"] * adjustment
        # Limites de segurança para o multiplicador
        if new_multiplier < 0.2: new_multiplier = 0.2
        if new_multiplier > 5.0: new_multiplier = 5.0

        meta["multiplier"] = new_multiplier
    except (ValueError, IndexError):
        return

    status_txt = get_text(user, context, "meme_processing")
    status_msg = await query.message.reply_html(status_txt)

    try:
        file = await context.bot.get_file(meta["file_id"])
        content = await file.download_as_bytearray()

        loop = asyncio.get_running_loop()
        font_path = _get_meme_font_path()

        result_bytes = await loop.run_in_executor(
            PROCESS_POOL,
            _generate_meme_task,
            bytes(content),
            meta["top"],
            meta["bottom"],
            font_path,
            meta["multiplier"]
        )

        # Registra interação para o admin (redimensionamento)
        await register_interaction(user, context, "Alterou tamanho do texto")

        f_io = io.BytesIO(result_bytes)
        f_io.name = "meme.jpg"

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(get_text(user, context, "btn_meme_smaller"), callback_data="meme:resize:0.8"),
                InlineKeyboardButton(get_text(user, context, "btn_meme_larger"), callback_data="meme:resize:1.2")
            ]
        ])

        # Envia como nova mensagem para não perder o histórico se o usuário quiser comparar
        sent_msg = await context.bot.send_photo(
            chat_id=user.id,
            photo=f_io,
            caption="🎭 #meme (Resize)",
            reply_markup=keyboard
        )

        # Transfere metadados para a nova mensagem
        context.user_data[f"meme_meta_{sent_msg.message_id}"] = meta
        # Opcional: manter ou remover o antigo? Vou manter por enquanto.

    except Exception as e:
        logger.error(f"Erro ao redimensionar meme: {e}")
        await query.message.reply_html(get_text(user, context, "err_meme_creation", e=str(e)))
    finally:
        await status_msg.delete()

async def meme_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela o meme."""
    user = update.effective_user
    msg = get_text(user, context, "cancel", count=0)
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(msg, parse_mode="HTML")
    else:
        await update.message.reply_html(msg)
    context.user_data.pop("meme_file_id", None)
    context.user_data.pop("meme_top", None)
    return ConversationHandler.END



def _build_zip_task(files_data: list) -> bytes:
    """Compacta uma lista de (nome_do_arquivo, conteúdo_bytes) em um ZIP."""
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in files_data:
            zf.writestr(name, data)
    return out.getvalue()


@base_handler_checks
async def zip_queue_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Baixa toda a fila de imagens e PDFs e envia compactado em um ZIP."""
    user = update.effective_user
    await register_interaction(user, context, "zip_queue")

    # Rate Limit
    if await check_ad_quota_reached(update, context, user):
        return
    remaining = check_rate_limit(user.id)
    if remaining > 0:
        await update.message.reply_text(
            get_text(user, context, "rate_limit_error", seconds=remaining)
        )
        return
    update_rate_limit(user.id)

    async with aiosqlite.connect(DB_FILE) as db:
        cursor_img = await db.execute(
            "SELECT file_id, file_name, file_fmt FROM user_images WHERE user_id = ? ORDER BY received_at ASC",
            (user.id,),
        )
        imgs = await cursor_img.fetchall()

        cursor_pdf = await db.execute(
            "SELECT file_id, file_name FROM user_pdfs WHERE user_id = ? ORDER BY message_id ASC",
            (user.id,),
        )
        pdfs = await cursor_pdf.fetchall()

    if not imgs and not pdfs:
        await update.message.reply_html(get_text(user, context, "zip_queue_empty"))
        return

    status_msg = await update.message.reply_html(
        get_text(user, context, "zip_queue_processing", count=len(imgs) + len(pdfs))
    )

    try:
        files_data = []
        # Obter arquivos das imagens
        if imgs:
            img_tasks = [context.bot.get_file(row[0]) for row in imgs]
            img_files = await asyncio.gather(*img_tasks)
            img_contents = await asyncio.gather(*[f.download_as_bytearray() for f in img_files])
            for i, (content, row) in enumerate(zip(img_contents, imgs)):
                ext = (row[2] or "jpg").lower()
                name = row[1] or f"image_{i+1}.{ext}"
                files_data.append((name, bytes(content)))

        # Obter arquivos dos PDFs
        if pdfs:
            pdf_tasks = [context.bot.get_file(row[0]) for row in pdfs]
            pdf_files = await asyncio.gather(*pdf_tasks)
            pdf_contents = await asyncio.gather(*[f.download_as_bytearray() for f in pdf_files])
            for i, (content, row) in enumerate(zip(pdf_contents, pdfs)):
                name = row[1] or f"document_{i+1}.pdf"
                files_data.append((name, bytes(content)))

        # Run zip in process pool
        loop = asyncio.get_running_loop()
        zip_bytes = await loop.run_in_executor(PROCESS_POOL, _build_zip_task, files_data)

        zip_io = io.BytesIO(zip_bytes)
        zip_name = get_text(user, context, "zip_filename", count=len(imgs) + len(pdfs))
        zip_io.name = zip_name

        await context.bot.send_document(chat_id=user.id, document=zip_io)

        # Clear queues
        async with aiosqlite.connect(DB_FILE) as db:
            await db.execute("DELETE FROM user_images WHERE user_id = ?", (user.id,))
            await db.execute("DELETE FROM user_pdfs WHERE user_id = ?", (user.id,))
            await db.commit()

        await status_msg.delete()

    except Exception as e:
        logger.error(f"Erro ao criar ZIP da fila: {e}")
        await status_msg.edit_text(get_text(user, context, "err_zip_creation", e=str(e)))


@base_handler_checks
async def compress_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Inicia o fluxo de compressão."""
    user = update.effective_user

    # Rate Limit
    if await check_ad_quota_reached(update, context, user):
        return
    remaining = check_rate_limit(user.id)
    if remaining > 0:
        await update.message.reply_text(
            get_text(user, context, "rate_limit_error", seconds=remaining)
        )
        return
    update_rate_limit(user.id)

    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM user_images WHERE user_id = ?", (user.id,)
        ) as cursor:
            count_img = (await cursor.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(*) FROM user_pdfs WHERE user_id = ?", (user.id,)
        ) as cursor:
            count_pdf = (await cursor.fetchone())[0]

    if count_img == 0 and count_pdf == 0:
        await update.message.reply_text(get_text(user, context, "need_one_image"))
        return

    context.user_data["state"] = "WAITING_COMPRESSION_TARGET"

    await update.message.reply_html(get_text(user, context, "compress_prompt"))


def _compress_image_task(
    image_bytes: bytes, target_mb: float
) -> tuple[bytes, int, int, int, int]:
    """Tarefa CPU-bound para comprimir imagem até o tamanho alvo."""
    # Usa 1000 * 1024 para garantir que 0.1MB seja tratado como 100KB (visual), evitando reclamações de "101KB > 0.1MB"
    target_bytes = int(target_mb * 1000 * 1024)

    old_w, old_h = 0, 0
    try:
        try:
            with Image.open(io.BytesIO(image_bytes)) as img_check:
                old_w, old_h = img_check.size
        except Image.DecompressionBombError as e:
            logger.error(f"Ataque de Decompression Bomb detectado em _compress_image_task (check): {e}")
            raise ValueError("A imagem é uma 'bomba de descompressão' e não pode ser processada.") from e
    except Exception:
        pass

    if len(image_bytes) <= target_bytes:
        return image_bytes, old_w, old_h, old_w, old_h

    try:
        try:
            img = Image.open(io.BytesIO(image_bytes))
        except Image.DecompressionBombError as e:
            logger.error(f"Ataque de Decompression Bomb detectado em _compress_image_task (process): {e}")
            raise ValueError(
                "A imagem é uma 'bomba de descompressão' e não pode ser processada."
            ) from e

        # Converte para RGB para salvar como JPEG (melhor compressão)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        out = io.BytesIO()

        # Passo 1: Reduzir Qualidade
        quality = 95
        while quality >= 10:
            out.seek(0)
            out.truncate()
            img.save(out, format="JPEG", quality=quality, optimize=True)
            if out.tell() <= target_bytes:
                return out.getvalue(), old_w, old_h, old_w, old_h
            quality -= 10

        # Passo 2: Reduzir Dimensões se qualidade 10 ainda for grande
        scale = 0.9
        while scale >= 0.1:
            new_width = int(img.width * scale)
            new_height = int(img.height * scale)
            if new_width < 1 or new_height < 1:
                break

            resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            out.seek(0)
            out.truncate()
            resized.save(out, format="JPEG", quality=10, optimize=True)

            if out.tell() <= target_bytes:
                return out.getvalue(), old_w, old_h, new_width, new_height
            scale -= 0.1

        return out.getvalue(), old_w, old_h, new_width, new_height
    except Exception:
        return image_bytes, old_w, old_h, old_w, old_h


def _compress_pdf_task(pdf_bytes: bytes, target_mb: float) -> bytes:
    """
    Comprime um PDF convertendo suas páginas em imagens comprimidas e remontando.
    Isso reduz drasticamente o tamanho, mas perde a camada de texto selecionável (rasterização).
    """
    try:
        # 0. Verificação de Texto (Evita rasterizar PDFs de texto puro)
        # Se o PDF tiver texto extraível significativo, provavelmente é um documento vetorial
        # e rasterizá-lo vai aumentar o tamanho ou destruir a qualidade.
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text_chars = 0
        num_pages = len(doc)
        for page in doc:
            t = page.get_text()
            if t:
                text_chars += len(t)
        doc.close()

        # Se tiver média > 200 caracteres por página, consideramos texto e pulamos
        if num_pages > 0 and (text_chars / num_pages) > 200:
            return pdf_bytes

        # 1. Converte PDF para imagens (150 DPI é um bom balanço para leitura em tela)
        images = convert_from_bytes(pdf_bytes, dpi=150)

        if not images:
            return pdf_bytes

        # 2. Calcula o tamanho alvo por página (aproximado)
        # Deduzimos 10% para overhead do container PDF
        target_bytes_total = int(target_mb * 1000 * 1024 * 0.9)
        target_bytes_per_page = target_bytes_total // len(images)

        # Garante um mínimo de 20KB por página para não destruir a imagem
        if target_bytes_per_page < 20 * 1024:
            target_bytes_per_page = 20 * 1024

        compressed_images = []

        for img in images:
            # Converte para RGB
            if img.mode != "RGB":
                img = img.convert("RGB")

            # Usa a lógica de compressão de imagem existente
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG', quality=95)
            raw_bytes = img_byte_arr.getvalue()

            # Comprime para o alvo calculado
            comp_bytes, _, _, _, _ = _compress_image_task(raw_bytes, target_bytes_per_page / (1000 * 1024))

            # Reabre como imagem PIL
            compressed_images.append(Image.open(io.BytesIO(comp_bytes)))

        # 3. Remonta o PDF
        return _create_multipage_pdf_task([io.BytesIO(img.tobytes()) for img in compressed_images], "portrait", pre_loaded_images=compressed_images, quality=80)

    except Exception as e:
        logger.error(f"Erro na compressão de PDF: {e}")
        return pdf_bytes


async def process_compression(
    update: Update, context: ContextTypes.DEFAULT_TYPE, target_mb: float
) -> None:
    """Processa a compressão das imagens."""
    user = update.effective_user

    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute(
            "SELECT file_id FROM user_images WHERE user_id = ? ORDER BY received_at ASC",
            (user.id,),
        )
        rows_img = await cursor.fetchall()

        cursor_pdf = await db.execute(
            "SELECT file_id, file_name FROM user_pdfs WHERE user_id = ? ORDER BY received_at ASC",
            (user.id,),
        )
        rows_pdf = await cursor_pdf.fetchall()

    if not rows_img and not rows_pdf:
        return

    await update.message.reply_text(
        get_text(user, context, "compressing", count=len(rows_img) + len(rows_pdf), size=target_mb)
    )

    # Reutiliza lógica de download
    async def download_image(file_id: str):
        try:
            new_file = await context.bot.get_file(file_id)
            f_bytes = await new_file.download_as_bytearray()
            return file_id, f_bytes
        except Exception:
            return file_id, None

    tasks = [download_image(row[0]) for row in rows_img]
    results = await asyncio.gather(*tasks)

    loop = asyncio.get_running_loop()
    target_bytes = int(target_mb * 1000 * 1024)
    any_success = False

    for fid, content in results:
        if not content:
            continue

        # Validação de tamanho: impede compressão se o alvo for maior que o original
        if len(content) <= target_bytes:
            await context.bot.send_message(
                chat_id=user.id,
                text=get_text(
                    user,
                    context,
                    "compression_ignored",
                    size=_format_size(len(content)),
                    target=target_mb,
                ),
            )
            continue

        try:
            # Executa compressão no pool de processos
            compressed_bytes, old_w, old_h, new_w, new_h = await loop.run_in_executor(
                PROCESS_POOL, _compress_image_task, bytes(content), target_mb
            )
        except ValueError as e: # Captura o erro da Decompression Bomb
            await context.bot.send_message(
                chat_id=user.id,
                text=get_text(user, context, "err_files_processing", e=str(e)),
                parse_mode="HTML",
            )
            continue

        f_io = io.BytesIO(compressed_bytes)
        f_io.name = f"compressed_{fid[:8]}.jpg"

        # Estatísticas
        old_size = len(content)
        new_size = len(compressed_bytes)
        percent = 0
        if old_size > 0:
            percent = round((1 - new_size / old_size) * 100, 1)

        caption = get_text(
            user,
            context,
            "compress_stats",
            old_size=_format_size(old_size),
            new_size=_format_size(new_size),
            percent=percent,
            old_dims=f"{old_w}x{old_h}",
            new_dims=f"{new_w}x{new_h}",
        )

        try:
            await context.bot.send_document(
                chat_id=user.id, document=f_io, caption=caption, parse_mode="HTML"
            )
            any_success = True
        except Exception as e:
            logger.error(f"Erro ao enviar doc comprimido: {e}")



        # Log de atividade (por imagem)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        PENDING_LOGS.append((user.id, None, "compression_created", timestamp))

    # --- Processamento de PDFs ---
    if rows_pdf:
        tasks_pdf = [download_image(row[0]) for row in rows_pdf]
        results_pdf = await asyncio.gather(*tasks_pdf)

        for i, (fid, content) in enumerate(results_pdf):
            if not content:
                continue

            old_size = len(content)
            target_bytes = int(target_mb * 1000 * 1024)

            # Validação simples antes de processar
            if old_size <= target_bytes:
                 await context.bot.send_message(
                    chat_id=user.id,
                    text=get_text(user, context, "compression_ignored", size=_format_size(old_size), target=target_mb)
                )
                 continue

            try:
                compressed_bytes = await loop.run_in_executor(
                    PROCESS_POOL, _compress_pdf_task, bytes(content), target_mb
                )

                f_io = io.BytesIO(compressed_bytes)
                original_name = rows_pdf[i][1] or f"file_{i}.pdf"
                f_io.name = f"compressed_{original_name}"

                new_size = len(compressed_bytes)

                # Verifica se o tamanho aumentou (comum em PDFs de texto rasterizados)
                if new_size > old_size:
                    await context.bot.send_message(
                        chat_id=user.id,
                        text=get_text(user, context, "compression_increased", old_size=_format_size(old_size), new_size=_format_size(new_size)),
                        parse_mode="HTML"
                    )
                    continue

                # Se o tamanho for igual (pulou compressão por ser texto), avisa o usuário
                if new_size == old_size:
                     await context.bot.send_message(
                        chat_id=user.id,
                        text=get_text(user, context, "compression_ignored", size=_format_size(old_size), target=target_mb),
                        parse_mode="HTML"
                    )
                     continue

                percent = 0
                if old_size > 0:
                    percent = round((1 - new_size / old_size) * 100, 1)

                caption = get_text(
                    user,
                    context,
                    "compress_stats",
                    old_size=_format_size(old_size),
                    new_size=_format_size(new_size),
                    percent=percent,
                    old_dims="PDF",
                    new_dims="PDF",
                )

                await context.bot.send_document(
                    chat_id=user.id, document=f_io, caption=caption, parse_mode="HTML"
                )
                any_success = True


                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                PENDING_LOGS.append((user.id, None, "compression_created_pdf", timestamp))

            except Exception as e:
                logger.error(f"Erro ao processar compressão de PDF: {e}")
                await context.bot.send_message(chat_id=user.id, text=get_text(user, context, "err_pdf_compression"))

    if any_success:
        await update.message.reply_text(get_text(user, context, "compress_success"))

    # Limpa a lista de imagens após a compressão para encerrar o fluxo
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("DELETE FROM user_images WHERE user_id = ?", (user.id,))
        await db.execute("DELETE FROM user_pdfs WHERE user_id = ?", (user.id,))
        await db.commit()


@base_handler_checks
async def converter_menu_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Exibe o menu para converter imagens."""
    user = update.effective_user
    async with aiosqlite.connect(DB_FILE) as db:
        # Pega a primeira imagem para detectar o formato original
        cursor = await db.execute(
            "SELECT file_id FROM user_images WHERE user_id = ? ORDER BY received_at ASC LIMIT 1",
            (user.id,),
        )
        row = await cursor.fetchone()

    if not row:
        await update.message.reply_text(get_text(user, context, "need_one_image"))
        return

    # Baixa o cabeçalho/imagem para detectar formato
    try:
        f = await context.bot.get_file(row[0])
        f_bytes = await f.download_as_bytearray()
        with Image.open(io.BytesIO(f_bytes)) as img:
            original_fmt = img.format or "JPEG"
    except Exception:
        original_fmt = "JPEG"  # Fallback

    original_fmt = original_fmt.upper()
    if original_fmt == "JPG":
        original_fmt = "JPEG"

    # Lista de formatos suportados (HEIC só incluido se encoder disponível)
    all_formats = ["JPEG", "PNG", "WEBP", "BMP", "TIFF", "GIF", "PDF"]
    if HEIC_ENCODE_SUPPORTED:
        all_formats.append("HEIC")

    # Filtra o formato original
    available_formats = [fmt for fmt in all_formats if fmt != original_fmt]

    # Cria botões
    keyboard = []
    row_btns = []
    for fmt in available_formats:
        row_btns.append(InlineKeyboardButton(fmt, callback_data=f"convert:{fmt}"))
        if len(row_btns) == 3:
            keyboard.append(row_btns)
            row_btns = []
    if row_btns:
        keyboard.append(row_btns)

    keyboard.append(
        [
            InlineKeyboardButton(
                get_text(user, context, "menu_cancel"),
                callback_data="settings_nav:close",
            )
        ]
    )

    msg = get_text(user, context, "converter_select_format", original=original_fmt)
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))


def _convert_image_task(image_bytes: bytes, target_format: str) -> bytes:
    """Converte imagem para o formato alvo."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
    except Image.DecompressionBombError as e:
        logger.error(f"Ataque de Decompression Bomb detectado em _convert_image_task: {e}")
        raise ValueError(
            "A imagem é uma 'bomba de descompressão' e não pode ser processada."
        ) from e

    # Registra o opener do pillow-heif para suporte a HEIC
    if target_format in ("HEIC", "HEIF"):
        try:
            import pillow_heif
            pillow_heif.register_heif_opener()
        except ImportError:
            raise ValueError("pillow-heif não instalado: HEIC não suportado.")

    # Converte modos incompatíveis
    if target_format == "JPEG" and img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    elif target_format in ("HEIC", "HEIF") and img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")

    out = io.BytesIO()
    save_params = {}
    if target_format == "JPEG":
        save_params = {"quality": 100}

    # Pillow reconhece "HEIF" como formato de saída (não "HEIC")
    save_format = "HEIF" if target_format == "HEIC" else target_format
    img.save(out, format=save_format, **save_params)
    return out.getvalue()


async def handle_converter_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Processa a conversão de formato."""
    query = update.callback_query
    await query.answer()

    target_fmt = query.data.split(":")[1]
    user = query.from_user

    # Rate Limit
    if await check_ad_quota_reached(update, context, user):
        return
    remaining = check_rate_limit(user.id)
    if remaining > 0:
        await query.answer(
            get_text(user, context, "rate_limit_error", seconds=remaining),
            show_alert=True,
        )
        return
    update_rate_limit(user.id)

    await query.message.delete()

    if target_fmt == "PDF":
        # Se for PDF, exibe menu de orientação
        keyboard = [
            [
                InlineKeyboardButton(
                    get_text(user, context, "pdf_portrait"),
                    callback_data="pdf_make:portrait",
                ),
                InlineKeyboardButton(
                    get_text(user, context, "pdf_landscape"),
                    callback_data="pdf_make:landscape",
                ),
            ],
            [
                InlineKeyboardButton(
                    get_text(user, context, "menu_cancel"),
                    callback_data="settings_nav:close",
                )
            ],
        ]
        await query.message.reply_text(
            get_text(user, context, "pdf_select_orientation"),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute(
            "SELECT file_id FROM user_images WHERE user_id = ? ORDER BY received_at ASC",
            (user.id,),
        )
        rows = await cursor.fetchall()

    if not rows:
        return

    await query.message.reply_text(
        get_text(user, context, "converting_images", count=len(rows), format=target_fmt)
    )

    # Processamento similar ao metadata removal
    tasks = [context.bot.get_file(row[0]) for row in rows]
    files = await asyncio.gather(*tasks)
    content_tasks = [f.download_as_bytearray() for f in files]
    image_contents = await asyncio.gather(*content_tasks)

    loop = asyncio.get_running_loop()
    original_fmt = "UNKNOWN"

    for i, (content, f) in enumerate(zip(image_contents, files)):
        # Detecta formato da primeira imagem para log do admin
        if i == 0:
            try:
                with Image.open(io.BytesIO(content)) as img_check:
                    original_fmt = (img_check.format or "UNKNOWN").upper()
            except Exception:
                pass

        try:
            converted_bytes = await loop.run_in_executor(
                PROCESS_POOL, _convert_image_task, bytes(content), target_fmt
            )
            f_io = io.BytesIO(converted_bytes)
        except ValueError as e: # Captura o erro da Decompression Bomb
            await context.bot.send_message(
                chat_id=user.id,
                text=get_text(user, context, "err_image_conversion", i=i+1, e=str(e)),
                parse_mode="HTML",
            )
            continue

        # Preserva o nome original, mudando apenas a extensão
        ext = target_fmt.lower()
        if ext == "jpeg":
            ext = "jpg"
        try:
            original_name = os.path.basename(f.file_path or "")
            if original_name:
                stem = os.path.splitext(original_name)[0]
                output_name = f"{stem}.{ext}"
            else:
                output_name = f"converted_{i + 1}.{ext}"
        except Exception:
            output_name = f"converted_{i + 1}.{ext}"

        f_io.name = output_name
        await context.bot.send_document(chat_id=user.id, document=f_io)

    await context.bot.send_message(
        chat_id=user.id, text=get_text(user, context, "conversion_success")
    )

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    PENDING_LOGS.append(
        (
            user.id,
            None,
            f"Converteu de {original_fmt} para {target_fmt}",
            timestamp,
        )
    )

    # Notifica apenas a operação, sem identidade do usuário.
    if ADMIN_ID and user.id != ADMIN_ID and ADMIN_NOTIFICATIONS_ENABLED and user.id not in MUTED_USERS:
        notify_admin_background(
            context.bot,
            f"🔄 Conversão de imagem: .{html.escape(original_fmt)} para .{html.escape(target_fmt)}.",
        )

    # Limpa a lista de imagens após a conversão
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("DELETE FROM user_images WHERE user_id = ?", (user.id,))
        await db.commit()


def _preprocess_image_for_ocr(
    image_bytes: bytes, debug_prefix: str | None = None
) -> Image.Image:
    """
    Aplica pré-processamento avançado usando OpenCV:
    - Grayscale
    - Denoising

    Se `debug_prefix` for fornecido, salva imagens intermediárias.
    """
    # Converte bytes para array numpy
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    # 1. Grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if debug_prefix:
        cv2.imwrite(f"{debug_prefix}_01_grayscale.png", gray)

    # 2. Remoção de Ruído (Median Blur é rápido e eficaz para salt-and-pepper noise)
    gray = cv2.medianBlur(gray, 3)
    if debug_prefix:
        cv2.imwrite(f"{debug_prefix}_02_denoised.png", gray)

    # Converte de volta para PIL Image
    return Image.fromarray(gray)


def _run_ocr_task(
    image_bytes: bytes,
    lang_code: str,
    use_advanced_preprocessing: bool = False,
    debug_prefix: str | None = None,
) -> str:
    """
    Executa o Tesseract OCR em uma imagem.
    É uma função bloqueante, para ser executada em um processo separado.
    """
    try:
        try:
            if use_advanced_preprocessing:
                # Usa o pipeline do OpenCV com modo de depuração
                img = _preprocess_image_for_ocr(image_bytes, debug_prefix)
            else:
                # Carregamento padrão
                img = Image.open(io.BytesIO(image_bytes))
                if debug_prefix:
                    img.save(f"{debug_prefix}_00_original.png")
                # Garante RGB se necessário
                if img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")
        except Image.DecompressionBombError as e:
            logger.error(f"Ataque de Decompression Bomb detectado em _run_ocr_task: {e}")
            raise ValueError(
                "A imagem é uma 'bomba de descompressão' e não pode ser processada."
            ) from e

        text = pytesseract.image_to_string(img, lang=lang_code)
        return text.strip()
    except Exception as e:
        # Logar o erro no processo filho pode ser complicado,
        # então retornamos o erro como string para ser logado no processo principal.
        return f"OCR_ERROR: {str(e)}"


@base_handler_checks
async def ocr_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Inicia o fluxo de extração de texto (OCR)."""
    user = update.effective_user
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM user_images WHERE user_id = ?", (user.id,)
        ) as cursor:
            count_img = (await cursor.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(*) FROM user_pdfs WHERE user_id = ?", (user.id,)
        ) as cursor:
            count_pdf = (await cursor.fetchone())[0]

    if count_img == 0 and count_pdf == 0:
        await update.message.reply_text(get_text(user, context, "need_one_image"))
        return

    # Idiomas suportados pelo Tesseract (código e nome)
    supported_langs = {
        "eng": "🇬🇧 English",
        "por": "🇧🇷 Português",
        "spa": "🇪🇸 Español",
        "ita": "🇮🇹 Italiano",
        "fra": "🇫🇷 Français",
        "rus": "🇷🇺 Русский",
        "ukr": "🇺🇦 Українська",
        "ara": "🇸🇦 العربية",
    }

    keyboard = []
    row_btns = []
    for code, name in supported_langs.items():
        row_btns.append(InlineKeyboardButton(name, callback_data=f"ocr_lang:{code}"))
        if len(row_btns) >= 2:
            keyboard.append(row_btns)
            row_btns = []
    if row_btns:
        keyboard.append(row_btns)

    keyboard.append(
        [
            InlineKeyboardButton(
                get_text(user, context, "menu_cancel"),
                callback_data="settings_nav:close",
            )
        ]
    )

    await update.message.reply_html(
        get_text(user, context, "ocr_select_language"),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )



async def handle_ocr_language_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Processa a escolha do idioma para OCR e inicia a extração."""
    query = update.callback_query
    await query.answer()

    lang_code = query.data.split(":")[1]
    user = query.from_user

    # Rate Limit
    if await check_ad_quota_reached(update, context, user):
        return
    remaining = check_rate_limit(user.id)
    if remaining > 0:
        await query.answer(
            get_text(user, context, "rate_limit_error", seconds=remaining),
            show_alert=True,
        )
        return
    update_rate_limit(user.id)

    await query.message.delete()
    status_msg = await query.message.reply_html(
        get_text(user, context, "ocr_processing")
    )

    # Ativa o modo de depuração se o usuário for o admin
    debug_prefix = None
    if user.id == ADMIN_ID:
        os.makedirs("cache", exist_ok=True)
        debug_prefix = os.path.join("cache", f"debug_{user.id}_{int(time.time())}")

    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute(
            "SELECT file_id FROM user_images WHERE user_id = ? ORDER BY received_at ASC",
            (user.id,),
        )
        rows_img = await cursor.fetchall()

        cursor_pdf = await db.execute(
            "SELECT file_id FROM user_pdfs WHERE user_id = ? ORDER BY received_at ASC",
            (user.id,),
        )
        rows_pdf = await cursor_pdf.fetchall()

    if not rows_img and not rows_pdf:
        await status_msg.edit_text(get_text(user, context, "need_one_image"))
        return

    try:
        tasks = [context.bot.get_file(row[0]) for row in rows_img]
        files = await asyncio.gather(*tasks)
        content_tasks = [f.download_as_bytearray() for f in files]
        image_contents = await asyncio.gather(*content_tasks)

        tasks_pdf = [context.bot.get_file(row[0]) for row in rows_pdf]
        files_pdf = await asyncio.gather(*tasks_pdf)
        content_tasks_pdf = [f.download_as_bytearray() for f in files_pdf]
        pdf_contents = await asyncio.gather(*content_tasks_pdf)
    except Exception as e:
        logger.error(f"Erro no download para OCR: {e}")
        await status_msg.edit_text(get_text(user, context, "download_error"))
        return

    loop = asyncio.get_running_loop()
    full_text = ""

    for i, content in enumerate(image_contents):
        try:
            extracted_text = await loop.run_in_executor(
                PROCESS_POOL, _run_ocr_task, bytes(content), lang_code, False, debug_prefix
            )
        except ValueError as e: # Captura o erro da Decompression Bomb
            extracted_text = f"OCR_ERROR: {e}"
        except Exception as e:
            extracted_text = f"OCR_ERROR: {e}"

        if extracted_text and not extracted_text.startswith("OCR_ERROR:"):
            logger.info(
                f"OCR (Normal) para user {user.id} extraiu {len(extracted_text)} caracteres na imagem {i + 1}."
            )
            full_text += f"\n\n--- Imagem {i + 1} ---\n" + extracted_text
        elif not extracted_text:
            logger.info(
                f"OCR (Normal) para user {user.id} não encontrou texto na imagem {i + 1}."
            )
        else:  # Começa com OCR_ERROR
            logger.error(
                f"Erro no OCR (Normal) para user {user.id} na imagem {i + 1}: {extracted_text}"
            )

    # Processa PDFs
    for i, content in enumerate(pdf_contents):
        try:
            extracted_text = await loop.run_in_executor(
                PROCESS_POOL, _extract_pdf_text_task, bytes(content), lang_code
            )
            if extracted_text:
                logger.info(f"OCR (PDF) para user {user.id} extraiu texto no PDF {i + 1}.")
                full_text += f"\n\n--- PDF {i + 1} ---\n" + extracted_text
            else:
                logger.info(f"OCR (PDF) para user {user.id} não encontrou texto no PDF {i + 1}.")
        except Exception as e:
            logger.error(f"Erro no OCR (PDF) para user {user.id}: {e}")
            full_text += f"\n\n--- PDF {i + 1} (Erro) ---\nErro ao ler PDF."

    await status_msg.delete()

# Limpa arquivos de depuração OCR sem compartilhá-los com o administrador.
    if debug_prefix:
        try:
            debug_files = glob.glob(f"{debug_prefix}_*.png")
            for f in debug_files:
                os.remove(f)
        except Exception as e:
            logger.error(f"Erro ao limpar arquivos de depuração OCR: {e}")

    if not full_text.strip():
        # Adiciona botão para tentar o modo avançado mesmo se não encontrar texto
        keyboard = [
            [
                InlineKeyboardButton(
                    get_text(user, context, "btn_ocr_advanced"),
                    callback_data=f"ocr_adv:{lang_code}",
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_html(
            get_text(user, context, "ocr_no_text"), reply_markup=reply_markup
        )
    else:
        # Adiciona botão para tentar o modo avançado
        keyboard = [
            [
                InlineKeyboardButton(
                    get_text(user, context, "btn_ocr_advanced"),
                    callback_data=f"ocr_adv:{lang_code}",
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        caption = get_text(user, context, "ocr_success")
        if len(full_text) > 4000:
            f_bytes = io.BytesIO(full_text.encode("utf-8"))
            f_bytes.name = "texto_extraido.txt"
            await query.message.reply_document(
                document=f_bytes, caption=caption, reply_markup=reply_markup
            )
        else:
            await query.message.reply_html(
                f"{caption}\n<pre>{html.escape(full_text.strip())}</pre>",
                reply_markup=reply_markup,
            )

    if ADMIN_ID and user.id != ADMIN_ID and ADMIN_NOTIFICATIONS_ENABLED and user.id not in MUTED_USERS:
        notify_admin_background(
            context.bot,
            f"🔍 OCR concluído (idioma: {html.escape(lang_code)}; texto compartilhado apenas com o usuário).",
        )

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    PENDING_LOGS.append(
        (user.id, None, f"ocr_extracted_{lang_code}", timestamp)
    )

    # Salva os file_ids das IMAGENS para um possível 'retry' (PDFs não suportam modo otimizado aqui)
    context.user_data["ocr_retry_files"] = [row[0] for row in rows_img]
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("DELETE FROM user_images WHERE user_id = ?", (user.id,))
        await db.execute("DELETE FROM user_pdfs WHERE user_id = ?", (user.id,))
        await db.commit()


async def handle_ocr_advanced_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Processa o OCR no modo avançado (OpenCV Preprocessing)."""
    query = update.callback_query
    await query.answer()

    lang_code = query.data.split(":")[1]
    user = query.from_user

    # Feedback visual imediato
    status_msg = await query.message.reply_html(
        get_text(user, context, "ocr_processing_advanced")
    )

    # Ativa o modo de depuração se o usuário for o admin
    debug_prefix = None
    if user.id == ADMIN_ID:
        os.makedirs("cache", exist_ok=True)
        debug_prefix = os.path.join("cache", f"debug_{user.id}_{int(time.time())}")

    # Busca os file_ids da sessão do usuário, pois a fila principal já foi limpa.
    file_ids = context.user_data.get("ocr_retry_files")
    if not file_ids:
        await status_msg.edit_text(get_text(user, context, "session_expired"))
        return
    # Simula a estrutura de 'rows' para reutilizar a lógica de download
    rows = [(fid,) for fid in file_ids]

    try:
        tasks = [context.bot.get_file(row[0]) for row in rows]
        files = await asyncio.gather(*tasks)
        content_tasks = [f.download_as_bytearray() for f in files]
        image_contents = await asyncio.gather(*content_tasks)
    except Exception as e:
        await status_msg.edit_text(get_text(user, context, "download_error"))
        return

    loop = asyncio.get_running_loop()
    full_text = ""

    for i, content in enumerate(image_contents):
        # Chama a task com use_advanced_preprocessing=True
        try:
            extracted_text = await loop.run_in_executor(
                PROCESS_POOL, _run_ocr_task, bytes(content), lang_code, True, debug_prefix
            )
        except ValueError as e: # Captura o erro da Decompression Bomb
            extracted_text = f"OCR_ERROR: {e}"
        except Exception as e:
            extracted_text = f"OCR_ERROR: {e}"

        if extracted_text and not extracted_text.startswith("OCR_ERROR:"):
            logger.info(
                f"OCR (Avançado) para user {user.id} extraiu {len(extracted_text)} caracteres na imagem {i + 1}."
            )
            full_text += f"\n\n--- Imagem {i + 1} (Otimizada) ---\n" + extracted_text
        elif not extracted_text:
            logger.info(
                f"OCR (Avançado) para user {user.id} não encontrou texto na imagem {i + 1}."
            )
        else:  # Começa com OCR_ERROR
            logger.error(
                f"Erro no OCR (Avançado) para user {user.id} na imagem {i + 1}: {extracted_text}"
            )
    await status_msg.delete()

    if debug_prefix:
        try:
            debug_files = glob.glob(f"{debug_prefix}_*.png")
            for f in debug_files:
                os.remove(f)
        except Exception as e:
            logger.error(f"Erro ao limpar arquivos de depuração avançada: {e}")

    if not full_text.strip():
        await query.message.reply_html(get_text(user, context, "ocr_no_text"))
    else:
        caption = get_text(user, context, "ocr_success") + " (Modo Otimizado)"
        if len(full_text) > 4000:
            f_bytes = io.BytesIO(full_text.encode("utf-8"))
            f_bytes.name = "texto_otimizado.txt"
            await query.message.reply_document(document=f_bytes, caption=caption)
        else:
            await query.message.reply_html(
                f"{caption}\n<pre>{html.escape(full_text.strip())}</pre>"
            )

    # Notifica Admin sobre uso do modo avançado
    if ADMIN_ID and user.id != ADMIN_ID and ADMIN_NOTIFICATIONS_ENABLED and user.id not in MUTED_USERS:
        notify_admin_background(
            context.bot,
            f"🔬 OCR avançado concluído (idioma: {html.escape(lang_code)}; texto compartilhado apenas com o usuário).",
        )

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    PENDING_LOGS.append(
        (user.id, None, f"ocr_adv_extracted_{lang_code}", timestamp)
    )

    # Limpa os file_ids da sessão de retry, pois a operação foi concluída.
    context.user_data.pop("ocr_retry_files", None)


def _create_multipage_pdf_task(
    image_bytes_list: list[bytes], orientation: str = "portrait", pre_loaded_images: list = None, quality: int = 95
) -> bytes:
    """Cria um PDF com múltiplas páginas a partir de uma lista de imagens."""
    images = []

    if pre_loaded_images:
        source_images = pre_loaded_images
    else:
        source_images = []
        for b in image_bytes_list:
            try:
                img = Image.open(io.BytesIO(b))
                source_images.append(img)
            except Exception:
                pass

    # Definição de A4 em pixels a 150 DPI (bom equilíbrio qualidade/tamanho)
    # A4: 210mm x 297mm -> ~8.27in x 11.7in
    # 150 DPI: 1240 x 1754 pixels
    A4_WIDTH, A4_HEIGHT = 1240, 1754

    target_size = (
        (A4_WIDTH, A4_HEIGHT) if orientation == "portrait" else (A4_HEIGHT, A4_WIDTH)
    )

    for img in source_images:
        try:
            if img.mode != "RGB":
                img = img.convert("RGB")

            # Redimensiona mantendo proporção para caber na página A4
            img.thumbnail(target_size, Image.Resampling.LANCZOS)

            # Cria página branca A4
            page = Image.new("RGB", target_size, (255, 255, 255))
            # Centraliza imagem
            x = (target_size[0] - img.width) // 2
            y = (target_size[1] - img.height) // 2
            page.paste(img, (x, y))

            images.append(page)
        except Exception:
            pass

    if not images:
        return b""

    out = io.BytesIO()
    images[0].save(
        out,
        format="PDF",
        save_all=True,
        append_images=images[1:],
        resolution=150.0,
        quality=quality,
    )
    return out.getvalue()


def _merge_pdfs_task(pdf_bytes_list: list[bytes]) -> bytes:
    """Mescla múltiplos arquivos PDF em um único arquivo via PyMuPDF."""
    merged = fitz.open()
    for pdf_bytes in pdf_bytes_list:
        sub = fitz.open(stream=pdf_bytes, filetype="pdf")
        merged.insert_pdf(sub)
        sub.close()
    out = merged.tobytes(garbage=4, deflate=True)
    merged.close()
    return out


def _extract_pdf_pages_task(pdf_bytes: bytes) -> bytes:
    """Converte páginas de um PDF para imagens e as retorna em um arquivo ZIP."""
    try:
        images = convert_from_bytes(pdf_bytes, dpi=200)

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for i, img in enumerate(images):
                img_buffer = io.BytesIO()
                img.save(img_buffer, format="PNG")
                img_buffer.seek(0)
                zf.writestr(f"page_{i + 1}.png", img_buffer.getvalue())

        zip_buffer.seek(0)
        return zip_buffer.getvalue()
    except Exception as e:
        raise RuntimeError(f"PDF_PAGES_ERROR: {str(e)}") from e


def _extract_pdf_text_task(pdf_bytes: bytes, lang_code: str) -> str:
    """Converte páginas de PDF em imagens e executa OCR em cada uma."""
    try:
        images = convert_from_bytes(pdf_bytes)
        full_text = ""
        for i, img in enumerate(images):
            text = pytesseract.image_to_string(img, lang=lang_code)
            if text.strip():
                full_text += f"\n\n--- Página {i + 1} ---\n{text.strip()}"
        return full_text.strip()
    except Exception as e:
        raise RuntimeError(f"PDF_TEXT_ERROR: {str(e)}") from e


@base_handler_checks
async def convert_to_pdf_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Converte as imagens da lista em um único arquivo PDF."""
    user = update.effective_user
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute(
            "SELECT file_id FROM user_images WHERE user_id = ? ORDER BY received_at ASC",
            (user.id,),
        )
        rows = await cursor.fetchall()

    if not rows:
        await update.message.reply_text(get_text(user, context, "need_one_image"))
        return

    # Menu de seleção de orientação
    keyboard = [
        [
            InlineKeyboardButton(
                get_text(user, context, "pdf_portrait"),
                callback_data="pdf_make:portrait",
            ),
            InlineKeyboardButton(
                get_text(user, context, "pdf_landscape"),
                callback_data="pdf_make:landscape",
            ),
        ],
        [
            InlineKeyboardButton(
                get_text(user, context, "menu_cancel"),
                callback_data="settings_nav:close",
            )
        ],
    ]
    await update.message.reply_text(
        get_text(user, context, "pdf_select_orientation"),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def handle_pdf_orientation_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Processa a criação do PDF após escolha da orientação."""
    query = update.callback_query
    await query.answer()

    orientation = query.data.split(":")[1]
    user = query.from_user

    # Rate Limit
    if await check_ad_quota_reached(update, context, user):
        return
    remaining = check_rate_limit(user.id)
    if remaining > 0:
        await query.answer(
            get_text(user, context, "rate_limit_error", seconds=remaining),
            show_alert=True,
        )
        return
    update_rate_limit(user.id)

    await query.message.delete()
    await query.message.reply_text(get_text(user, context, "processing_pdf"))

    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute(
            "SELECT file_id FROM user_images WHERE user_id = ? ORDER BY received_at ASC",
            (user.id,),
        )
        rows = await cursor.fetchall()

    if not rows:
        return

    # Download das imagens
    tasks = [context.bot.get_file(row[0]) for row in rows]
    files = await asyncio.gather(*tasks)
    content_tasks = [f.download_as_bytearray() for f in files]
    image_contents = await asyncio.gather(*content_tasks)

    loop = asyncio.get_running_loop()
    pdf_bytes = await loop.run_in_executor(
        PROCESS_POOL,
        _create_multipage_pdf_task,
        [bytes(c) for c in image_contents],
        orientation,
    )

    f_io = io.BytesIO(pdf_bytes)
    f_io.name = f"images_{user.id}.pdf"
    await context.bot.send_document(
        chat_id=update.effective_chat.id,
        document=f_io,
        caption=get_text(user, context, "pdf_created"),
    )


    # Log de atividade
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    PENDING_LOGS.append((user.id, None, "pdf_created", timestamp))

    # Limpa a lista de imagens após a geração do PDF
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("DELETE FROM user_images WHERE user_id = ?", (user.id,))
        await db.commit()


@base_handler_checks
async def merge_pdfs_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Mescla os arquivos PDF da fila do usuário."""
    user = update.effective_user

    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute(
            "SELECT file_id FROM user_pdfs WHERE user_id = ? ORDER BY received_at ASC",
            (user.id,),
        )
        rows = await cursor.fetchall()

    if not rows:
        await update.message.reply_text(get_text(user, context, "no_pdfs_queued"))
        return

    if len(rows) < 2:
        await update.message.reply_text(get_text(user, context, "need_two_pdfs"))
        return

    # Rate Limit
    if await check_ad_quota_reached(update, context, user):
        return
    remaining = check_rate_limit(user.id)
    if remaining > 0:
        await update.message.reply_text(
            get_text(user, context, "rate_limit_error", seconds=remaining)
        )
        return
    update_rate_limit(user.id)

    status_msg = await update.message.reply_text(
        get_text(user, context, "merging_pdfs", count=len(rows)), parse_mode="HTML"
    )

    try:
        tasks = [context.bot.get_file(row[0]) for row in rows]
        files = await asyncio.gather(*tasks)
        content_tasks = [f.download_as_bytearray() for f in files]
        pdf_contents = await asyncio.gather(*content_tasks)

        loop = asyncio.get_running_loop()
        merged_pdf = await loop.run_in_executor(
            PROCESS_POOL, _merge_pdfs_task, [bytes(c) for c in pdf_contents]
        )

        f_io = io.BytesIO(merged_pdf)
        f_io.name = f"merged_{user.id}.pdf"
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=f_io,
            caption=get_text(user, context, "pdf_merge_success"),
        )
        await status_msg.delete()


        # Limpa a fila de PDFs
        async with aiosqlite.connect(DB_FILE) as db:
            await db.execute("DELETE FROM user_pdfs WHERE user_id = ?", (user.id,))
            await db.commit()

        await register_interaction(user, context, f"Mesclou {len(rows)} PDFs")

    except Exception as e:
        logger.error(f"Erro ao mesclar PDFs para {user.id}: {e}")
        await status_msg.edit_text(get_text(user, context, "pdf_merge_error"))


def _censor_faces_task(image_bytes: bytes, blur_option: str) -> tuple[bytes, int]:
    """
    Detecta rostos em uma imagem e aplica desfoque (Gaussian Blur ou Pixelate)
    nas regiões dos rostos detectados.
    Retorna (imagem_processada_bytes, quantidade_de_rostos_detectados).
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
    if img is None:
        return image_bytes, 0

    has_alpha = False
    if len(img.shape) == 3 and img.shape[2] == 4:
        has_alpha = True
        bgr = img[:, :, :3].copy()
        alpha = img[:, :, 3]
    elif len(img.shape) == 3:
        bgr = img.copy()
    else:
        bgr = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)

    faces = []
    # Carrega classificadores Haar do OpenCV
    try:
        cascade_alt = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_alt2.xml")
        if not cascade_alt.empty():
            detected_alt = cascade_alt.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=3, minSize=(25, 25), flags=cv2.CASCADE_SCALE_IMAGE
            )
            if len(detected_alt) > 0:
                faces.extend(detected_alt)
    except Exception:
        pass

    try:
        cascade_default = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        if not cascade_default.empty():
            detected_def = cascade_default.detectMultiScale(
                gray, scaleFactor=1.15, minNeighbors=4, minSize=(25, 25), flags=cv2.CASCADE_SCALE_IMAGE
            )
            if len(detected_def) > 0:
                faces.extend(detected_def)
    except Exception:
        pass

    try:
        cascade_profile = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_profileface.xml")
        if not cascade_profile.empty():
            detected_prof = cascade_profile.detectMultiScale(
                gray, scaleFactor=1.15, minNeighbors=4, minSize=(25, 25), flags=cv2.CASCADE_SCALE_IMAGE
            )
            if len(detected_prof) > 0:
                faces.extend(detected_prof)
    except Exception:
        pass

    # Unifica e agrupa retângulos sobrepostos
    if len(faces) > 0:
        rects = [list(f) for f in faces]
        rects, _ = cv2.groupRectangles(rects + rects, groupThreshold=1, eps=0.25)
    else:
        rects = []

    total_faces = len(rects)

    for (x, y, w, h) in rects:
        pad_x = int(w * 0.10)
        pad_y = int(h * 0.10)
        x1 = max(0, x - pad_x)
        y1 = max(0, y - pad_y)
        x2 = min(bgr.shape[1], x + w + pad_x)
        y2 = min(bgr.shape[0], y + h + pad_y)

        face_roi = bgr[y1:y2, x1:x2]
        if face_roi.size == 0:
            continue

        if blur_option == "pixelate":
            rw = max(1, (x2 - x1) // 12)
            rh = max(1, (y2 - y1) // 12)
            small = cv2.resize(face_roi, (rw, rh), interpolation=cv2.INTER_LINEAR)
            censored = cv2.resize(small, (x2 - x1, y2 - y1), interpolation=cv2.INTER_NEAREST)
        else:
            try:
                blur_val = int(blur_option)
            except ValueError:
                blur_val = 35

            ksize = max(15, int((w / 80.0) * blur_val))
            if ksize % 2 == 0:
                ksize += 1
            censored = cv2.GaussianBlur(face_roi, (ksize, ksize), 0)

        bgr[y1:y2, x1:x2] = censored

    if has_alpha:
        out_img = cv2.merge([bgr[:, :, 0], bgr[:, :, 1], bgr[:, :, 2], alpha])
        ext = ".png"
    else:
        out_img = bgr
        ext = ".jpg"

    encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), 95] if ext == ".jpg" else []
    success, enc = cv2.imencode(ext, out_img, encode_params)
    if not success:
        return image_bytes, 0
    return bytes(enc), total_faces


@base_handler_checks
async def censor_menu_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Abre o menu de escolha de nível de desfoque para a ferramenta Censura."""
    user = update.effective_user

    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute(
            "SELECT file_id FROM user_images WHERE user_id = ? ORDER BY received_at ASC",
            (user.id,),
        )
        rows = await cursor.fetchall()

    if not rows:
        await update.message.reply_text(get_text(user, context, "censor_no_images"))
        return

    keyboard = [
        [
            InlineKeyboardButton(
                get_text(user, context, "censor_blur_low"),
                callback_data="censor_blur:15",
            ),
            InlineKeyboardButton(
                get_text(user, context, "censor_blur_medium"),
                callback_data="censor_blur:35",
            ),
        ],
        [
            InlineKeyboardButton(
                get_text(user, context, "censor_blur_high"),
                callback_data="censor_blur:65",
            ),
            InlineKeyboardButton(
                get_text(user, context, "censor_blur_extreme"),
                callback_data="censor_blur:100",
            ),
        ],
        [
            InlineKeyboardButton(
                get_text(user, context, "censor_blur_pixelate"),
                callback_data="censor_blur:pixelate",
            ),
        ],
        [
            InlineKeyboardButton(
                get_text(user, context, "menu_cancel"),
                callback_data="settings_nav:close",
            )
        ],
    ]

    msg = get_text(user, context, "censor_select_blur")
    await update.message.reply_text(
        msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML"
    )


async def handle_censor_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Processa a censura de rostos com o nível de desfoque selecionado."""
    query = update.callback_query
    await query.answer()

    blur_option = query.data.split(":")[1]
    user = query.from_user

    # Rate Limit
    if await check_ad_quota_reached(update, context, user):
        return
    remaining = check_rate_limit(user.id)
    if remaining > 0:
        await query.answer(
            get_text(user, context, "rate_limit_error", seconds=remaining),
            show_alert=True,
        )
        return
    update_rate_limit(user.id)

    await query.message.delete()

    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute(
            "SELECT file_id, is_document, file_name FROM user_images WHERE user_id = ? ORDER BY received_at ASC",
            (user.id,),
        )
        rows = await cursor.fetchall()

    if not rows:
        return

    status_msg = await query.message.reply_text(
        get_text(user, context, "censor_processing", count=len(rows)), parse_mode="HTML"
    )

    tasks = [context.bot.get_file(row[0]) for row in rows]
    files = await asyncio.gather(*tasks)
    content_tasks = [f.download_as_bytearray() for f in files]
    image_contents = await asyncio.gather(*content_tasks)

    loop = asyncio.get_running_loop()
    total_faces_all = 0

    for i, (content, row) in enumerate(zip(image_contents, rows)):
        is_document = bool(row[1])
        original_name = row[2] or f"censor_{i + 1}.jpg"

        censored_bytes, faces_count = await loop.run_in_executor(
            PROCESS_POOL, _censor_faces_task, bytes(content), blur_option
        )
        total_faces_all += faces_count

        if faces_count > 0:
            caption = get_text(user, context, "censor_faces_found", count=faces_count)
        else:
            caption = get_text(user, context, "censor_no_faces_found")

        f_io = io.BytesIO(censored_bytes)
        f_io.name = f"censored_{original_name}"

        if is_document:
            await context.bot.send_document(
                chat_id=user.id, document=f_io, caption=caption, parse_mode="HTML"
            )
        else:
            try:
                await context.bot.send_photo(
                    chat_id=user.id, photo=f_io, caption=caption, parse_mode="HTML"
                )
            except Exception:
                f_io.seek(0)
                await context.bot.send_document(
                    chat_id=user.id, document=f_io, caption=caption, parse_mode="HTML"
                )



    try:
        await status_msg.delete()
    except Exception:
        pass

    await context.bot.send_message(
        chat_id=user.id, text=get_text(user, context, "censor_success_all")
    )

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    PENDING_LOGS.append(
        (user.id, None, f"censor_faces_{blur_option}_{total_faces_all}", timestamp)
    )

    # Limpa a lista de imagens após a censura
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("DELETE FROM user_images WHERE user_id = ?", (user.id,))
        await db.commit()

    await register_interaction(user, context, f"Censurou {len(rows)} fotos (blur={blur_option}, rostos={total_faces_all})")


async def handle_regen_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Regenera a união com configuração de resize invertida ou watermark override."""
    query = update.callback_query
    user = query.from_user

    # Data: regen:direction:resize_val:wm_val
    parts = query.data.split(":")
    direction = parts[1]
    override_resize = bool(int(parts[2]))
    override_watermark = bool(int(parts[3])) if len(parts) > 3 else None

    # Rate Limit
    if await check_ad_quota_reached(update, context, user):
        return
    remaining = check_rate_limit(user.id)
    if remaining > 0:
        await query.answer(
            get_text(user, context, "rate_limit_error", seconds=remaining),
            show_alert=True
        )
        return
    await query.answer()
    update_rate_limit(user.id)

    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute(
            "SELECT file_id FROM last_merge_files WHERE user_id = ? ORDER BY file_order ASC",
            (user.id,),
        )
        rows = await cursor.fetchall()

    if not rows:
        await query.message.reply_text(get_text(user, context, "session_expired"))
        return

    await execute_merge(
        update, context, rows, direction,
        override_resize=override_resize,
        override_watermark=override_watermark
    )


async def handle_reverse_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Inverte a ordem das imagens e regenera."""
    query = update.callback_query
    user = query.from_user

    # Data: reverse:direction:resize_val:wm_val
    parts = query.data.split(":")
    direction = parts[1]
    resize_val = int(parts[2])
    override_resize = bool(resize_val)
    override_watermark = bool(int(parts[3])) if len(parts) > 3 else None

    # Rate Limit
    if await check_ad_quota_reached(update, context, user):
        return
    remaining = check_rate_limit(user.id)
    if remaining > 0:
        await query.answer(
            get_text(user, context, "rate_limit_error", seconds=remaining),
            show_alert=True
        )
        return
    await query.answer()
    update_rate_limit(user.id)

    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute(
            "SELECT file_id FROM last_merge_files WHERE user_id = ? ORDER BY file_order ASC",
            (user.id,),
        )
        rows = await cursor.fetchall()

        if not rows:
            await query.message.reply_text(get_text(user, context, "session_expired"))
            return

        # Inverte a lista
        rows.reverse()

        # Atualiza no banco para persistir a inversão
        await db.execute("DELETE FROM last_merge_files WHERE user_id = ?", (user.id,))
        for i, row in enumerate(rows):
            await db.execute(
                "INSERT INTO last_merge_files (user_id, file_id, file_order) VALUES (?, ?, ?)",
                (user.id, row[0], i),
            )
        await db.commit()

    await execute_merge(
        update, context, rows, direction,
        override_resize=override_resize,
        override_watermark=override_watermark
    )


async def merge_images_vertically(
    image_bytes_list: list[bytes],
    output_format: str = "PNG",
    quality: int = 100,
    bg_color: str = "WHITE",
    auto_resize: bool = True,
    border_width: int = 0,
    border_color: str = "WHITE",
    watermark_settings: dict | None = None,
) -> bytes:
    """Une uma lista de imagens (em formato de bytes) verticalmente."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        PROCESS_POOL,
        _merge_images_task,
        image_bytes_list,
        "vertical",
        output_format,
        quality,
        bg_color,
        auto_resize,
        border_width,
        border_color,
        watermark_settings,
    )


async def merge_images_horizontally(
    image_bytes_list: list[bytes],
    output_format: str = "PNG",
    quality: int = 100,
    bg_color: str = "WHITE",
    auto_resize: bool = True,
    border_width: int = 0,
    border_color: str = "WHITE",
    watermark_settings: dict | None = None,
) -> bytes:
    """Une uma lista de imagens (em formato de bytes) horizontalmente."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        PROCESS_POOL,
        _merge_images_task,
        image_bytes_list,
        "horizontal",
        output_format,
        quality,
        bg_color,
        auto_resize,
        border_width,
        border_color,
        watermark_settings,
    )


async def merge_images_grid(
    image_bytes_list: list[bytes],
    direction: str,
    output_format: str = "PNG",
    quality: int = 100,
    bg_color: str = "WHITE",
    auto_resize: bool = True,
    border_width: int = 0,
    border_color: str = "WHITE",
    watermark_settings: dict | None = None,
) -> bytes:
    """Une uma lista de imagens em grade."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        PROCESS_POOL,
        _merge_images_task,
        image_bytes_list,
        direction,
        output_format,
        quality,
        bg_color,
        auto_resize,
        border_width,
        border_color,
        watermark_settings,
    )


@base_handler_checks
async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Cancela fluxos pendentes e redireciona para clear_all_command."""
    clear_pending_input_state(context)
    await clear_all_command(update, context)


def update_requirements_file(package_name: str) -> None:
    """
    Atualiza a versão de um pacote no requirements.txt para a versão instalada atualmente.
    Útil para persistência em Docker.
    """
    try:
        req_file = "requirements.txt"
        if os.path.exists(req_file):
            # Obtém a versão instalada no ambiente atual
            current_version = version(package_name)

            with open(req_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            found = False
            with open(req_file, "w", encoding="utf-8") as f:
                for line in lines:
                    # Limpa a linha para extrair apenas o nome do pacote
                    clean_line = line.split("#")[0].strip()
                    if not clean_line:
                        f.write(line)
                        continue

                    # Normaliza o nome do pacote, tratando os comparadores de versão
                    pkg_name = (
                        clean_line.split("==")[0]
                        .split(">=")[0]
                        .split("<=")[0]
                        .split(">")[0]
                        .split("<")[0]
                        .strip()
                    )

                    if pkg_name.lower() == package_name.lower():
                        f.write(f"{package_name}=={current_version}\n")
                        found = True
                    else:
                        f.write(line)

            if found:
                logger.info(
                    f"✅ {req_file} atualizado: {package_name} fixado em {current_version}"
                )
            else:
                logger.warning(
                    f"⚠️ Pacote {package_name} não encontrado em {req_file}. Não foi possível atualizar."
                )

    except Exception as e:
        logger.error(f"❌ Falha ao atualizar {req_file}: {e}")


async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gera relatório de uso para o admin."""
    user = update.effective_user
    user_id = user.id

    if user_id != ADMIN_ID:
        return

    status_msg = await update.message.reply_html(
        "📊 <b>Gerando relatório...</b> Por favor, aguarde."
    )

    periods = [
        ("Dia (24h)", "-1 day"),
        ("Semana (7d)", "-7 days"),
        ("Mês (30d)", "-30 days"),
        ("Ano (365d)", "-1 year"),
        ("Total", None),
    ]

    msg = "📊 <b>Relatório de Atividade</b>\n\n"

    async with aiosqlite.connect(DB_FILE) as db:
        for label, modifier in periods:
            # Prepara a query base
            sql_base = "SELECT COUNT(*) FROM activity_logs WHERE (action = ? OR action = 'msg_text' OR action = 'msg_photo')"
            params_time = []

            if modifier:
                sql_base += " AND timestamp >= datetime('now', ?)"
                params_time.append(modifier)

            cursor_uses = await db.execute(
                sql_base, tuple(["interaction_unknown"] + params_time)
            )
            uses = (await cursor_uses.fetchone())[0]

            # Contagem de merges (todos os tipos)
            sql_merge = "SELECT COUNT(*) FROM activity_logs WHERE action LIKE 'merge_%'"
            params_merge = []
            if modifier:
                sql_merge += " AND timestamp >= datetime('now', ?)"
                params_merge.append(modifier)

            cursor_merges = await db.execute(sql_merge, tuple(params_merge))
            merges = (await cursor_merges.fetchone())[0]

            msg += f"<b>{label}:</b> {uses} usos | {merges} imgs\n"

        # Estatísticas Globais Específicas
        msg += "\n📊 <b>Totais Globais (Desde o início):</b>\n"
        stats_queries = [
            ("Horizontal", "merge_horizontal"),
            ("Vertical", "merge_vertical"),
            ("Grade", "merge_grid"),
            ("Comprimidas", "compression_created"),
            ("PDFs", "pdf_created"),
            ("Metadados Removidos", "metadata_removed"),
            ("Memes", "meme_created"),
        ]

        final_stats = []
        for label, action_key in stats_queries:
            async with db.execute(
                "SELECT COUNT(*) FROM activity_logs WHERE action = ?", (action_key,)
            ) as cursor:
                count = (await cursor.fetchone())[0]
                final_stats.append((label, count))

        # Adiciona OCR
        async with db.execute(
            "SELECT COUNT(*) FROM activity_logs WHERE action LIKE 'ocr_extracted_%'"
        ) as cursor:
            count = (await cursor.fetchone())[0]
            if count > 0:
                final_stats.append(("Textos Extraídos (OCR)", count))

        # Adiciona GIFs/Videos
        async with db.execute(
            "SELECT COUNT(*) FROM activity_logs WHERE action IN ('gif_created_from_images', 'gif_created_from_video', 'video_created_from_gif')"
        ) as cursor:
            count = (await cursor.fetchone())[0]
            if count > 0:
                final_stats.append(("GIFs/Vídeos", count))

        # Ordena por contagem decrescente
        final_stats.sort(key=lambda x: x[1], reverse=True)

        for label, count in final_stats:
            msg += f"- {label}: {count}\n"

        # Estatísticas de Idioma
        msg += "\n🌐 <b>Usuários por Idioma:</b>\n"
        sql_lang = """
            SELECT
                COALESCE(custom_language, SUBSTR(language_code, 1, 2), 'en') as lang,
                COUNT(*) as count
            FROM users
            GROUP BY lang
            ORDER BY count DESC
        """
        async with db.execute(sql_lang) as cursor_lang:
            rows = await cursor_lang.fetchall()

        lang_map = {
            "en": "Inglês",
            "pt": "Português",
            "es": "Espanhol",
            "ru": "Russo",
            "ar": "Árabe",
            "it": "Italiano",
            "fr": "Français",
        }

        for lang_code, count in rows:
            lang_name = lang_map.get(lang_code.lower(), lang_code.upper())
            msg += f"- {lang_name}: {count}\n"

        # --- Dados para Gráfico de Crescimento ---
        sql_join_dates = """
            SELECT
                DATE(joined_at) as join_day,
                COUNT(user_id) as new_users
            FROM users
            WHERE joined_at IS NOT NULL
            GROUP BY join_day
            ORDER BY join_day ASC
        """

        cursor_growth = await db.execute(sql_join_dates)
        all_time_growth_data = await cursor_growth.fetchall()

    # --- Processamento e Geração do Gráfico ---
    if all_time_growth_data:
        cumulative_users = 0
        processed_all_time = []
        for date_str, new_users in all_time_growth_data:
            cumulative_users += new_users
            processed_all_time.append(
                (
                    datetime.datetime.strptime(date_str, "%Y-%m-%d").date(),
                    cumulative_users,
                )
            )

        thirty_days_ago = (datetime.datetime.now() - datetime.timedelta(days=30)).date()
        processed_30d = [
            item for item in processed_all_time if item[0] >= thirty_days_ago
        ]

        if processed_30d and processed_all_time.index(processed_30d[0]) > 0:
            previous_day_data = processed_all_time[
                processed_all_time.index(processed_30d[0]) - 1
            ]
            start_point = (thirty_days_ago, previous_day_data[1])
            processed_30d.insert(0, start_point)

        loop = asyncio.get_running_loop()
        try:
            await status_msg.edit_text(
                "📊 <b>Gerando relatório e gráfico...</b>", parse_mode="HTML"
            )
            labels = {
                "chart_title_growth_30d": "Crescimento de Usuários (Últimos 30 Dias)",
                "chart_total_users": "Total de Usuários",
                "chart_title_growth_total": "Crescimento de Usuários (Total)",
            }
            image_bytes = await loop.run_in_executor(
                PROCESS_POOL,
                _generate_user_growth_charts_task,
                processed_30d,
                processed_all_time,
                labels,
            )
            await update.message.reply_photo(
                photo=image_bytes, caption=msg, parse_mode="HTML"
            )
            await status_msg.delete()
        except Exception as e:
            logger.error(f"Erro ao gerar gráfico de crescimento: {e}")
            err_graph = f"❌ Erro ao gerar gráfico: {e}"
            await status_msg.edit_text(f"{msg}\n\n{err_graph}", parse_mode="HTML")
    else:
        await status_msg.edit_text(msg, parse_mode="HTML", reply_markup=get_admin_markup())


def _generate_usage_charts_task(
    data_24h: dict,
    data_30d_hourly: dict,
    data_30d_dow: dict,
    data_commands: dict,
    data_origins: dict,
    labels: dict,
) -> bytes:
    """Gera gráficos de uso usando Matplotlib (Executado em processo separado)."""
    # Configura estilo
    plt.style.use("dark_background")

    # Cria figura com 5 subplots (3 linhas, 2 colunas)
    fig, axes = plt.subplots(3, 2, figsize=(16, 18))

    # 1. Gráfico 24h (Linha 0, Coluna 0)
    hours_int = np.arange(24)
    width = 0.25

    counts_24h_miniapp = [data_24h.get(f"{h:02d}", (0, 0, 0))[0] for h in range(24)]
    counts_24h_externo = [data_24h.get(f"{h:02d}", (0, 0, 0))[1] for h in range(24)]
    counts_24h_trad = [data_24h.get(f"{h:02d}", (0, 0, 0))[2] for h in range(24)]

    axes[0, 0].bar(hours_int - width, counts_24h_trad, width, color="#3498db", alpha=0.8, label="Tradicional")
    axes[0, 0].bar(hours_int, counts_24h_miniapp, width, color="#f1c40f", alpha=0.8, label="Mini App")
    axes[0, 0].bar(hours_int + width, counts_24h_externo, width, color="#9b59b6", alpha=0.8, label="Externo")
    axes[0, 0].set_title(labels.get("chart_title_24h", "Atividade nas Últimas 24 Horas"))
    axes[0, 0].set_xlabel(labels.get("chart_hour", "Hora"))
    axes[0, 0].set_ylabel(labels.get("chart_interactions", "Interações"))
    axes[0, 0].set_xticks(hours_int)
    axes[0, 0].legend()
    axes[0, 0].grid(True, linestyle="--", alpha=0.5)

    # 2. Gráfico 30d Horário (Linha 0, Coluna 1)
    counts_30d_miniapp = [data_30d_hourly.get(f"{h:02d}", (0, 0, 0))[0] for h in range(24)]
    counts_30d_externo = [data_30d_hourly.get(f"{h:02d}", (0, 0, 0))[1] for h in range(24)]
    counts_30d_trad = [data_30d_hourly.get(f"{h:02d}", (0, 0, 0))[2] for h in range(24)]

    axes[0, 1].bar(hours_int - width, counts_30d_trad, width, color="#2ecc71", alpha=0.8, label="Tradicional")
    axes[0, 1].bar(hours_int, counts_30d_miniapp, width, color="#f1c40f", alpha=0.8, label="Mini App")
    axes[0, 1].bar(hours_int + width, counts_30d_externo, width, color="#9b59b6", alpha=0.8, label="Externo")
    axes[0, 1].set_title(
        labels.get(
            "chart_title_30d_hourly", "Horários de Maior Atividade (Últimos 30 Dias)"
        )
    )
    axes[0, 1].set_xlabel(labels.get("chart_hour", "Hora"))
    axes[0, 1].set_ylabel(labels.get("chart_total_interactions", "Total Interações"))
    axes[0, 1].set_xticks(hours_int)
    axes[0, 1].legend()
    axes[0, 1].grid(True, linestyle="--", alpha=0.5)

    # 3. Gráfico Dias da Semana (Linha 1, Coluna 0)
    # 0 = Domingo no SQLite
    dow_labels_str = labels.get("chart_dow_labels", "Dom,Seg,Ter,Qua,Qui,Sex,Sáb")
    dow_labels = dow_labels_str.split(",")
    dow_indices = np.arange(7)
    counts_dow_miniapp = [data_30d_dow.get(str(d), (0, 0, 0))[0] for d in range(7)]
    counts_dow_externo = [data_30d_dow.get(str(d), (0, 0, 0))[1] for d in range(7)]
    counts_dow_trad = [data_30d_dow.get(str(d), (0, 0, 0))[2] for d in range(7)]

    axes[1, 0].bar(dow_indices - width, counts_dow_trad, width, color="#e74c3c", alpha=0.8, label="Tradicional")
    axes[1, 0].bar(dow_indices, counts_dow_miniapp, width, color="#f1c40f", alpha=0.8, label="Mini App")
    axes[1, 0].bar(dow_indices + width, counts_dow_externo, width, color="#9b59b6", alpha=0.8, label="Externo")
    axes[1, 0].set_title(
        labels.get(
            "chart_title_30d_dow", "Atividade por Dia da Semana (Últimos 30 Dias)"
        )
    )
    axes[1, 0].set_xticks(dow_indices)
    axes[1, 0].set_xticklabels(dow_labels)
    axes[1, 0].set_ylabel(labels.get("chart_total_interactions", "Total Interações"))
    axes[1, 0].legend()
    axes[1, 0].grid(True, linestyle="--", alpha=0.5)

    # 4. Gráfico de Comandos (Linha 1, Coluna 1)
    commands = list(data_commands.keys())
    counts_cmd = list(data_commands.values())

    axes[1, 1].bar(commands, counts_cmd, color="#9b59b6", alpha=0.8)
    axes[1, 1].set_ylabel(labels.get("chart_total_uses", "Total de Usos"))
    axes[1, 1].set_title(labels.get("chart_title_commands", "Top Comandos (Geral)"))
    axes[1, 1].grid(True, linestyle="--", alpha=0.5)
    axes[1, 1].tick_params(axis='x', rotation=45)

    # 5. Gráfico Tradicional vs MiniApp (Linha 2, Coluna 0)
    today = datetime.date.today()
    dates_list = [today - datetime.timedelta(days=i) for i in range(29, -1, -1)]
    date_strs = [d.strftime("%Y-%m-%d") for d in dates_list]

    # Formatação de datas para exibição (ex: 29/05)
    labels_30d = [d.strftime("%d/%m") for d in dates_list]
    x_indices = np.arange(len(labels_30d))

    counts_miniapp = [data_origins.get(d, (0, 0, 0))[0] for d in date_strs]
    counts_externo = [data_origins.get(d, (0, 0, 0))[1] for d in date_strs]
    counts_trad = [data_origins.get(d, (0, 0, 0))[2] for d in date_strs]

    axes[2, 0].bar(x_indices - width, counts_trad, width, color="#3498db", alpha=0.8, label="Tradicional")
    axes[2, 0].bar(x_indices, counts_miniapp, width, color="#f1c40f", alpha=0.8, label="Mini App")
    axes[2, 0].bar(x_indices + width, counts_externo, width, color="#9b59b6", alpha=0.8, label="Externo")
    axes[2, 0].set_title("Acessos por Plataforma (Últimos 30 dias)")
    axes[2, 0].set_ylabel("Acessos")
    axes[2, 0].set_xticks(x_indices[::3])
    axes[2, 0].set_xticklabels(labels_30d[::3], rotation=45)
    axes[2, 0].legend()
    axes[2, 0].grid(True, linestyle="--", alpha=0.3)

    # 6. Gráfico de Pizza Proporção 30 dias (Linha 2, Coluna 1)
    total_miniapp = sum(counts_miniapp)
    total_externo = sum(counts_externo)
    total_trad = sum(counts_trad)

    if total_miniapp + total_trad + total_externo > 0:
        axes[2, 1].pie(
            [total_trad, total_miniapp, total_externo],
            labels=["Tradicional", "Mini App", "Externo"],
            colors=["#3498db", "#f1c40f", "#9b59b6"],
            autopct='%1.1f%%',
            startangle=90,
            textprops={'color': "white", 'weight': 'bold'}
        )
        axes[2, 1].set_title("Proporção de Uso (Últimos 30 dias)")
    else:
        axes[2, 1].axis('off')
        axes[2, 1].text(0.5, 0.5, 'Sem dados', ha='center', va='center')

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=100)
    buf.seek(0)
    plt.close(fig)
    return buf.getvalue()


def _generate_donor_charts_task(
    top_all_data: list,
    monthly_history_data: list,
    accumulation_data: list,
    labels: dict
) -> bytes:
    """Gera uma imagem única com 3 subplots de doações em layout de 2 colunas."""
    plt.style.use("dark_background")
    # Grid 2x2 para melhor aproveitamento de espaço
    fig, axes = plt.subplots(2, 2, figsize=(16, 14))

    # 1. Top Doadores (Local: 0,0)
    if top_all_data:
        names = [str(row[0])[:15] or "User" for row in top_all_data]
        usd = [row[3] * 0.01 for row in top_all_data]
        x_pos = range(len(names))
        axes[0, 0].bar(x_pos, usd, color='#FFD700', alpha=0.8)
        axes[0, 0].set_xticks(x_pos)
        axes[0, 0].set_xticklabels(names, rotation=30, ha='right')
        axes[0, 0].set_title(labels.get("title_top", "Top Doadores (USD)"))
        axes[0, 0].set_ylabel(labels.get("label_amount", "Valor ($)"))
        axes[0, 0].grid(True, linestyle="--", alpha=0.3)
    else:
        axes[0, 0].text(0.5, 0.5, "Sem dados", ha='center', va='center')

    # 2. Histórico 12 Meses (Local: 0,1)
    if monthly_history_data:
        months = [str(row[0]) for row in monthly_history_data]
        m_usd = [row[1] * 0.01 for row in monthly_history_data]
        x_pos = range(len(months))
        axes[0, 1].bar(x_pos, m_usd, color='#4CAF50', alpha=0.8)
        axes[0, 1].set_xticks(x_pos)
        axes[0, 1].set_xticklabels(months, rotation=45, ha='right')
        axes[0, 1].set_title(labels.get("title_monthly", "Histórico Mensal (USD)"))
        axes[0, 1].set_ylabel(labels.get("label_amount", "Valor ($)"))
        axes[0, 1].grid(True, linestyle="--", alpha=0.3)
    else:
        axes[0, 1].text(0.5, 0.5, "Sem dados", ha='center', va='center')

    # 3. Acúmulo USD (Local: 1,0)
    if accumulation_data:
        times = [
            datetime.datetime.fromisoformat(row[0]) if isinstance(row[0], str) else row[0]
            for row in accumulation_data
        ]
        usd = [float(row[1]) * 0.01 for row in accumulation_data]
        axes[1, 0].plot(times, usd, marker='o', color='#2196F3', linewidth=2)
        axes[1, 0].fill_between(times, usd, color='#2196F3', alpha=0.2)
        axes[1, 0].set_title(labels.get("title_acc", "Acúmulo USD"))
        axes[1, 0].set_ylabel(labels.get("label_amount", "Valor ($)"))
        axes[1, 0].grid(True, linestyle='--', alpha=0.5)
        axes[1, 0].tick_params(axis='x', rotation=30)
    else:
        axes[1, 0].text(0.5, 0.5, "Sem dados", ha='center', va='center')

    # 4. Info/Logo (Local: 1,1)
    axes[1, 1].axis('off')
    axes[1, 1].text(0.5, 0.5, "MergeImages Supporter Report\n" + datetime.datetime.now().strftime("%Y-%m-%d"),
                    ha='center', va='center', fontsize=14, color='white', alpha=0.5)

    plt.tight_layout()
    buf = io.BytesIO()
    # DPI 85 para evitar httpx.ReadError por arquivo muito grande
    plt.savefig(buf, format="png", dpi=85)
    buf.seek(0)
    plt.close(fig)
    return buf.getvalue()


def _generate_user_growth_charts_task(
    data_30d: list, data_all_time: list, labels: dict
) -> bytes:
    """Gera gráficos de crescimento de usuários (Executado em processo separado)."""
    plt.style.use("dark_background")
    fig, axes = plt.subplots(1, 1, figsize=(12, 6))

    # Helper para formatar datas
    def format_date(x, pos=None):
        return dates.num2date(x).strftime("%d/%m")

    # 1. Gráfico 30 dias
    if data_30d:
        dates_30d = [item[0] for item in data_30d]
        counts_30d = [item[1] for item in data_30d]
        axes.plot(dates_30d, counts_30d, marker="o", linestyle="-", color="#3498db")
        axes.set_title(
            labels.get(
                "chart_title_growth_30d", "Crescimento de Usuários (Últimos 30 Dias)"
            )
        )
        axes.set_ylabel(labels.get("chart_total_users", "Total de Usuários"))
        axes.grid(True, linestyle="--", alpha=0.5)
        axes.xaxis.set_major_formatter(plt.FuncFormatter(format_date))
        axes.xaxis.set_major_locator(
            dates.DayLocator(interval=5)
        )  # Ticks a cada 5 dias
        fig.autofmt_xdate(bottom=0.2, rotation=30, ha="right")

    plt.tight_layout(pad=3.0)

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=100)
    buf.seek(0)
    plt.close(fig)
    return buf.getvalue()


def _generate_my_usage_charts_task(
    daily_data: dict, command_data: dict, labels: dict
) -> bytes:
    """Gera gráficos de uso pessoal usando Matplotlib."""
    plt.style.use("dark_background")
    fig, axes = plt.subplots(2, 1, figsize=(10, 12))

    # 1. Gráfico de Linha (Últimos 30 dias)
    # Preenche datas faltantes com 0
    today = datetime.date.today()
    dates_list = [today - datetime.timedelta(days=i) for i in range(29, -1, -1)]
    counts_list = [daily_data.get(d.strftime("%Y-%m-%d"), 0) for d in dates_list]

    # Formatação de data para o eixo X
    date_labels = [d.strftime("%d/%m") for d in dates_list]
    x_indices = list(range(len(date_labels)))

    axes[0].plot(x_indices, counts_list, marker="o", linestyle="-", color="#3498db")
    axes[0].fill_between(x_indices, counts_list, color="#3498db", alpha=0.3)
    axes[0].set_title(labels.get("chart_title_my_30d", "Seu Uso nos Últimos 30 Dias"))
    axes[0].set_ylabel(labels.get("chart_actions", "Ações"))
    axes[0].grid(True, linestyle="--", alpha=0.5)

    # Reduz a densidade dos labels do eixo X se necessário
    axes[0].set_xticks(range(0, len(date_labels), 3))
    axes[0].set_xticklabels([date_labels[i] for i in range(0, len(date_labels), 3)])

    # 2. Gráfico de Barras (Comandos)
    cmds = list(command_data.keys())
    counts = list(command_data.values())

    # Ordena por contagem
    if cmds:
        zipped = sorted(zip(counts, cmds), reverse=True)
        counts, cmds = zip(*zipped)

    axes[1].bar(cmds, counts, color="#2ecc71", alpha=0.8)
    axes[1].set_title(
        labels.get(
            "chart_title_my_commands", "Total de Uso por Comando (Desde o Início)"
        )
    )
    axes[1].set_ylabel(labels.get("chart_total", "Total"))
    axes[1].grid(True, linestyle="--", alpha=0.5)
    axes[1].tick_params(axis="x", rotation=45)

    plt.tight_layout(pad=3.0)

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=100)
    buf.seek(0)
    plt.close(fig)
    return buf.getvalue()



async def usage_report_graph_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Gera gráficos de uso e lista top usuários (Apenas Admin)."""
    user_id = update.effective_user.id
    user = update.effective_user
    if user_id != ADMIN_ID:
        return

    status_msg = await update.message.reply_html(
        "📊 <b>Gerando gráficos de uso...</b> Por favor, aguarde."
    )

    async with aiosqlite.connect(DB_FILE) as db:
        # 1. Atividade últimas 24h
        cursor = await db.execute(
            """SELECT strftime('%H', timestamp) as hour,
               SUM(CASE WHEN action = 'miniapp_usage' THEN 1 ELSE 0 END) as miniapp,
               SUM(CASE WHEN action = 'miniapp_usage_externo' THEN 1 ELSE 0 END) as externo,
               SUM(CASE WHEN action != 'miniapp_usage' AND action != 'miniapp_usage_externo' THEN 1 ELSE 0 END) as trad
               FROM activity_logs WHERE timestamp >= datetime('now', '-24 hours') GROUP BY hour"""
        )
        data_24h = {row[0]: (row[1], row[2], row[3]) for row in await cursor.fetchall()}

        # 2. Média (Total) últimos 30 dias por horário
        cursor = await db.execute(
            """SELECT strftime('%H', timestamp) as hour,
               SUM(CASE WHEN action = 'miniapp_usage' THEN 1 ELSE 0 END) as miniapp,
               SUM(CASE WHEN action = 'miniapp_usage_externo' THEN 1 ELSE 0 END) as externo,
               SUM(CASE WHEN action != 'miniapp_usage' AND action != 'miniapp_usage_externo' THEN 1 ELSE 0 END) as trad
               FROM activity_logs WHERE timestamp >= datetime('now', '-30 days') GROUP BY hour"""
        )
        data_30d_hourly = {row[0]: (row[1], row[2], row[3]) for row in await cursor.fetchall()}

        # 3. Dias da semana últimos 30 dias
        cursor = await db.execute(
            """SELECT strftime('%w', timestamp) as dow,
               SUM(CASE WHEN action = 'miniapp_usage' THEN 1 ELSE 0 END) as miniapp,
               SUM(CASE WHEN action = 'miniapp_usage_externo' THEN 1 ELSE 0 END) as externo,
               SUM(CASE WHEN action != 'miniapp_usage' AND action != 'miniapp_usage_externo' THEN 1 ELSE 0 END) as trad
               FROM activity_logs WHERE timestamp >= datetime('now', '-30 days') GROUP BY dow"""
        )
        data_30d_dow = {row[0]: (row[1], row[2], row[3]) for row in await cursor.fetchall()}

        # 4. Top 20 Usuários
        cursor = await db.execute(
            """SELECT
                a.user_id,
                COALESCE(u.first_name, 'User'),
                COUNT(*) as total,
                SUM(CASE WHEN action LIKE 'merge_%' OR action IN ('pdf_created', 'compression_created') THEN 1 ELSE 0 END) as created
            FROM activity_logs a
            LEFT JOIN users u ON a.user_id = u.user_id
            GROUP BY a.user_id
            ORDER BY total DESC
            LIMIT 20"""
        )
        top_users = await cursor.fetchall()

        # 5. Comandos mais usados
        cursor = await db.execute(
            "SELECT action, COUNT(*) FROM activity_logs GROUP BY action"
        )
        raw_actions = await cursor.fetchall()

        # 6. Tradicional vs MiniApp vs Externo (Últimos 30 dias)
        cursor = await db.execute(
            """SELECT DATE(timestamp) as day,
               SUM(CASE WHEN action = 'miniapp_usage' THEN 1 ELSE 0 END) as miniapp,
               SUM(CASE WHEN action = 'miniapp_usage_externo' THEN 1 ELSE 0 END) as externo,
               SUM(CASE WHEN action != 'miniapp_usage' AND action != 'miniapp_usage_externo' THEN 1 ELSE 0 END) as trad
               FROM activity_logs
               WHERE timestamp >= datetime('now', '-30 days')
               GROUP BY day"""
        )
        data_origins = {row[0]: (row[1], row[2], row[3]) for row in await cursor.fetchall()}

    # Processamento dos comandos
    command_counts = {}
    for action, count in raw_actions:
        if not action:
            continue
        if action.startswith("merge_vertical"):
            key = "Merge Vert."
        elif action.startswith("merge_horizontal"):
            key = "Merge Horiz."
        elif action.startswith("merge_grid"):
            key = "Grade"
        elif action == "pdf_created":
            key = "PDF"
        elif action == "compression_created":
            key = "Compressão"
        elif action == "metadata_removed":
            key = "Metadados"
        elif action.startswith("ocr_"):
            key = "OCR"
        elif "Converteu de" in action:
            key = "Conversor"
        elif action and (
            action.startswith("Converteu PDF para DOCX")
            or action.startswith("Converteu DOCX para PDF")
            or action.startswith("Extraiu páginas de DOCX")
            or action.startswith("enviou um DOCX")
        ):
            key = "DOCX"
        elif action == "zip_queue":
            key = "ZIP"
        else:
            continue

        command_counts[key] = command_counts.get(key, 0) + count

    data_commands = dict(
        sorted(command_counts.items(), key=lambda item: item[1], reverse=True)[:10]
    )

    loop = asyncio.get_running_loop()
    try:
        labels = {
            "chart_title_24h": "Atividade nas Últimas 24 Horas",
            "chart_hour": "Hora",
            "chart_interactions": "Interações",
            "chart_title_30d_hourly": "Horários de Maior Atividade (Últimos 30 Dias)",
            "chart_total_interactions": "Total Interações",
            "chart_title_30d_dow": "Atividade por Dia da Semana (Últimos 30 Dias)",
            "chart_title_commands": "Comandos/Ações Mais Usados (Total)",
            "chart_total_uses": "Total de Usos",
            "chart_dow_labels": "Dom,Seg,Ter,Qua,Qui,Sex,Sáb",
        }
        image_bytes = await loop.run_in_executor(
            PROCESS_POOL,
            _generate_usage_charts_task,
            data_24h,
            data_30d_hourly,
            data_30d_dow,
            data_commands,
            data_origins,
            labels,
        )

        msg = "📈 <b>Relatório de Uso Avançado</b>\n\n🏆 <b>Top 20 Usuários Mais Ativos:</b>\n<i>(Interações Totais | Imagens Criadas)</i>\n\n"
        for i, (uid, fname, total, created) in enumerate(top_users, 1):
            user_display = f"{html.escape(fname)} (<code>{uid}</code>)"

            created_safe = created if created else 0
            msg += f"{i}. <b>{user_display}</b>: {total} | {created_safe}\n"

        await update.message.reply_photo(
            photo=image_bytes, caption=msg, parse_mode="HTML", reply_markup=get_admin_markup()
        )
    except Exception as e:
        logger.error(f"Erro ao gerar gráficos: {e}")
        await update.message.reply_html(f"❌ Erro ao gerar gráficos: {e}")
    finally:
        await status_msg.delete()

def _format_timedelta(td: datetime.timedelta) -> str:
    """Formata um timedelta em 'Xd Yh Zm Ws'."""
    days = td.days
    hours, rem = divmod(td.seconds, 3600)
    minutes, seconds = divmod(rem, 60)

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0 or days > 0:
        parts.append(f"{hours:02}h")
    if minutes > 0 or hours > 0 or days > 0:
        parts.append(f"{minutes:02}m")
    parts.append(f"{seconds:02}s")

    return " ".join(parts) if parts else "0s"


async def diagnostic_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Exibe um relatório de diagnóstico completo do sistema (Apenas Admin)."""
    user = update.effective_user
    if user.id != ADMIN_ID:
        return

    if update.callback_query:
        query = update.callback_query
        await query.answer("🔄 Atualizando diagnóstico...")
        msg = query.message
    else:
        msg = await update.message.reply_html(
            "🩺 <b>Coletando dados de diagnóstico...</b> Por favor, aguarde."
        )

    # --- Coleta de Dados Assíncrona ---
    tasks = {}

    # Tarefa 1: Versões das Bibliotecas (rede)
    async def get_lib_versions():
        libs_to_check = [
            "pip",
            "python-telegram-bot",
            "Pillow",
            "aiosqlite",
            "psutil",
            "aiohttp",
            "httpx",
            "APScheduler",
            "matplotlib",
            "pytesseract",
            "opencv-python-headless",
            "numpy",
            "PyMuPDF",
            "pillow-heif",
            "pdf2docx",
            "python-docx",
            "rembg",
            "qrcode",
        ]

        async def check_one_lib(session, lib_name):
            result = {"text": "", "update_available": False, "lib_name": lib_name, "version": "N/A"}
            try:
                installed_v = version(lib_name)
                if installed_v is None:
                    installed_v = "N/A"
                result["version"] = installed_v
                try:
                    async with session.get(
                        f"https://pypi.org/pypi/{lib_name}/json", timeout=5
                    ) as resp:
                        if resp.status == 200:
                            latest_v = (await resp.json())["info"]["version"]
                            if installed_v != latest_v:
                                result["text"] = (
                                    f"  ⚠️ {lib_name}=={installed_v} (Nova: {latest_v})"
                                )
                                result["update_available"] = True
                            else:
                                result["text"] = f"  ✅ {lib_name}=={installed_v}"
                        else:
                            result["text"] = (
                                f"  ✅ {lib_name}=={installed_v} (PyPI: {resp.status})"
                            )
                except Exception as e:
                    result["text"] = (
                        f"  ✅ {lib_name}=={installed_v} (PyPI: Erro {str(e)[:40]})"
                    )
            except PackageNotFoundError:
                result["text"] = f"  ❌ {lib_name} (Não instalado)"
            return result

        # Adiciona User-Agent para evitar bloqueio do PyPI (Erro 403/Connection)
        headers = {"User-Agent": f"UnifyImagesBot/{VERSION}"}
        # Força IPv4 para evitar problemas de resolução DNS/IPv6 comuns em Docker
        connector = aiohttp.TCPConnector(family=socket.AF_INET)
        async with aiohttp.ClientSession(
            headers=headers, connector=connector
        ) as session:
            check_tasks = [check_one_lib(session, lib) for lib in libs_to_check]
            results = await asyncio.gather(*check_tasks)
        return results

    tasks["libs"] = asyncio.create_task(get_lib_versions())

    # Tarefa 2: Conexões e DB (rede, disco)
    async def check_connections_and_db():
        start_time_tg = time.monotonic()
        await context.bot.get_me()
        telegram_latency = (time.monotonic() - start_time_tg) * 1000

        db_latency, db_size_mb, user_count = 0, 0, 0
        if os.path.exists(DB_FILE):
            db_size_mb = os.path.getsize(DB_FILE) / (1024 * 1024)
            try:
                async with aiosqlite.connect(DB_FILE) as db:
                    start_db = time.monotonic()
                    await db.execute("SELECT 1")
                    db_latency = (time.monotonic() - start_db) * 1000
                    async with db.execute("SELECT COUNT(*) FROM users") as cursor:
                        user_count = (await cursor.fetchone())[0]
            except Exception as e:
                logger.error(f"Erro ao acessar DB no diagnóstico: {e}")

        internet_status = "❌ Offline"
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection("8.8.8.8", 53), timeout=3.0
            )
            writer.close()
            await writer.wait_closed()
            internet_status = "✅ Online"
        except Exception:
            pass

        return {
            "telegram": telegram_latency,
            "db_latency": db_latency,
            "db_size": db_size_mb,
            "users": user_count,
            "internet": internet_status,
        }

    tasks["connections"] = asyncio.create_task(check_connections_and_db())

    # Tarefa 3: Versão Python
    async def check_python_version():
        current = sys.version.split()[0]
        latest = current
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://endoflife.date/api/python.json", timeout=5
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data and isinstance(data, list):
                            latest = data[0].get("latest", current)
        except Exception:
            pass
        return current, latest

    tasks["python"] = asyncio.create_task(check_python_version())

    # Tarefa 4: Ferramentas do Sistema (Rembg, Tesseract, Poppler, LibreOffice)
    async def check_system_tools():
        tools = {"raw": {}, "display": {}}
        # Rembg / OnnxRuntime
        try:
            import onnxruntime as ort
            tools["display"]["onnx"] = f"✅ {ort.get_device()} ({ort.__version__})"
            tools["raw"]["onnx"] = ort.__version__
        except ImportError:
            tools["display"]["onnx"] = "❌ onnxruntime não instalado"
        except Exception as e:
            tools["display"]["onnx"] = f"❌ Erro: {str(e)[:40]}"

        # PyMuPDF / MuPDF
        try:
            import pymupdf as fitz
            tools["display"]["pdf_engine"] = f"✅ PyMuPDF {fitz.__version__} (MuPDF {getattr(fitz, 'VersionBind', 'N/A')})"
            tools["raw"]["pdf_engine"] = fitz.__version__
        except ImportError:
            tools["display"]["pdf_engine"] = "❌ PyMuPDF não instalado"

        async def run_tool(tool_key, display_name, *cmd):
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=5.0)
                output = (stdout or stderr).decode("utf-8", errors="replace").strip()
                first_line = output.splitlines()[0] if output else ""
                if proc.returncode == 0:
                    if tool_key == "tesseract_langs":
                        lang_lines = [line.strip() for line in output.splitlines()[1:] if line.strip()]
                        lang_text = ", ".join(lang_lines) if lang_lines else first_line
                        tools["display"][tool_key] = f"✅ {lang_text[:160]}"
                    else:
                        tools["display"][tool_key] = first_line or display_name
                        # Extrai a versão numérica para comparação
                        v_match = re.search(r"(\d+\.\d+(?:\.\d+)*)", first_line)
                        if v_match:
                            tools["raw"][tool_key] = v_match.group(1)
                else:
                    tools["display"][tool_key] = f"❌ {display_name} erro {proc.returncode}: {first_line[:80]}"
            except FileNotFoundError:
                tools["display"][tool_key] = f"❌ {display_name} não encontrado no PATH"
            except Exception as e:
                tools["display"][tool_key] = f"❌ {display_name} erro: {str(e)[:80]}"

        await asyncio.gather(
            run_tool("tesseract", "Tesseract OCR", "tesseract", "--version"),
            run_tool("tesseract_langs", "Idiomas Tesseract", "tesseract", "--list-langs"),
            run_tool("libreoffice", "LibreOffice", "soffice", "--version"),
        )

        return tools

    tasks["system_tools"] = asyncio.create_task(check_system_tools())

    # Tarefa 5: Diagnóstico do Mini App (Go Backend)
    async def check_miniapp_diagnostics():
        env_url = os.getenv("MINIAPP_DIAGNOSTIC_URL", "").strip()
        env_port = os.getenv("MINIAPP_PORT", "").strip()
        candidate_bases = []
        if env_url:
            candidate_bases.append(env_url)
        if env_port:
            candidate_bases.extend([f"http://127.0.0.1:{env_port}", f"http://localhost:{env_port}"])
        candidate_bases.extend([
            "http://127.0.0.1:3005",
            "http://localhost:3005",
            "http://127.0.0.1:3000",
            "http://localhost:3000",
            "http://unify-images-miniapp:3005",
            "http://unify-images-miniapp:3000",
            "http://miniapp:3000",
        ])

        seen = set()
        candidate_bases = [url.rstrip("/") for url in candidate_bases if url and not (url in seen or seen.add(url))]
        errors = []
        async with aiohttp.ClientSession() as session:
            for base_url in candidate_bases:
                diagnostics_url = f"{base_url}/api/diagnostics"
                try:
                    async with session.get(diagnostics_url, timeout=3.0) as resp:
                        if resp.status != 200:
                            errors.append(f"{diagnostics_url} -> HTTP {resp.status}")
                            continue
                        data = await resp.json()
                        return {
                            "active": True,
                            "url": diagnostics_url,
                            "go_version": data.get("go_version", "N/A"),
                            "fiber_version": data.get("fiber_version", "N/A"),
                            "uptime": data.get("uptime", "N/A"),
                            "os": data.get("os", "N/A"),
                            "arch": data.get("arch", "N/A"),
                            "goroutines": data.get("goroutines", 0)
                        }
                except Exception as e:
                    errors.append(f"{diagnostics_url} -> {type(e).__name__}: {str(e)[:80]}")
        return {"active": False, "errors": errors[:4]}

    tasks["miniapp"] = asyncio.create_task(check_miniapp_diagnostics())

    # Tarefa 6: Checagem de Versões Mais Recentes (Go, Fiber, LibreOffice, SQLite, Tesseract, Poppler, SSL)
    async def check_software_updates_and_ssl():
        results = {
            "go": None,
            "fiber": None,
            "libreoffice": None,
            "sqlite": None,
            "tesseract": None,
            "poppler": None,
            "ssl": [],
        }

        headers = {"User-Agent": f"UnifyImagesBot/{VERSION}"}
        connector = aiohttp.TCPConnector(family=socket.AF_INET)
        async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
            async def get_go():
                try:
                    async with session.get("https://go.dev/dl/?mode=json", timeout=3.5) as r:
                        if r.status == 200:
                            d = await r.json()
                            if d and isinstance(d, list):
                                return d[0]["version"].replace("go", "")
                except Exception:
                    pass
                return None

            async def get_fiber():
                try:
                    async with session.get("https://proxy.golang.org/github.com/gofiber/fiber/v2/@latest", timeout=3.5) as r:
                        if r.status == 200:
                            d = await r.json()
                            return d.get("Version", "").lstrip("v")
                except Exception:
                    pass
                return None

            async def get_lo():
                try:
                    async with session.get("https://endoflife.date/api/libreoffice.json", timeout=3.5) as r:
                        if r.status == 200:
                            d = await r.json()
                            if d and isinstance(d, list):
                                return d[0].get("latest")
                except Exception:
                    pass
                return None

            async def get_sqlite():
                try:
                    async with session.get("https://endoflife.date/api/sqlite.json", timeout=3.5) as r:
                        if r.status == 200:
                            d = await r.json()
                            if d and isinstance(d, list):
                                return d[0].get("latest")
                except Exception:
                    pass
                return None

            async def get_tesseract():
                try:
                    async with session.get("https://api.github.com/repos/tesseract-ocr/tesseract/releases/latest", timeout=3.5) as r:
                        if r.status == 200:
                            d = await r.json()
                            tag = d.get("tag_name", "")
                            return tag.lstrip("v")
                except Exception:
                    pass
                return None

            async def get_poppler():
                try:
                    async with session.get("https://gitlab.freedesktop.org/api/v4/projects/poppler%2Fpoppler/repository/tags", timeout=3.5) as r:
                        if r.status == 200:
                            d = await r.json()
                            if d and isinstance(d, list):
                                tag = d[0].get("name", "")
                                return tag.replace("poppler-", "")
                except Exception:
                    pass
                return None

            def check_ssl_endpoint(host, port=443):
                try:
                    ctx = ssl.create_default_context()
                    with socket.create_connection((host, port), timeout=3.0) as sock:
                        with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                            cert = ssock.getpeercert()
                            exp_str = cert["notAfter"]
                            exp_dt = datetime.datetime.strptime(exp_str, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=datetime.timezone.utc)
                            now_dt = datetime.datetime.now(datetime.timezone.utc)
                            days = (exp_dt - now_dt).days
                            return {
                                "host": host,
                                "port": port,
                                "days": days,
                                "date": exp_dt.strftime("%Y-%m-%d"),
                                "valid": True,
                            }
                except Exception as e:
                    return {"host": host, "port": port, "error": str(e)[:60], "valid": False}

            # Hosts para checagem SSL
            ssl_hosts = ["api.telegram.org"]
            for env_key in ("MINIAPP_URL", "MINIAPP_DIAGNOSTIC_URL", "WEBHOOK_URL", "SERVER_DOMAIN"):
                v = os.getenv(env_key, "").strip()
                if v and "://" in v:
                    try:
                        from urllib.parse import urlparse
                        p = urlparse(v)
                        if p.scheme == "https" and p.hostname and p.hostname not in ssl_hosts:
                            ssl_hosts.append(p.hostname)
                    except Exception:
                        pass
                elif v and not v.startswith("http") and "." in v and v not in ssl_hosts:
                    ssl_hosts.append(v)

            ssl_tasks = [asyncio.get_running_loop().run_in_executor(None, check_ssl_endpoint, h) for h in ssl_hosts]

            go_res, fib_res, lo_res, sql_res, tess_res, pop_res, *ssl_res = await asyncio.gather(
                get_go(), get_fiber(), get_lo(), get_sqlite(), get_tesseract(), get_poppler(), *ssl_tasks
            )

            results["go"] = go_res
            results["fiber"] = fib_res
            results["libreoffice"] = lo_res
            results["sqlite"] = sql_res
            results["tesseract"] = tess_res
            results["poppler"] = pop_res
            results["ssl"] = ssl_res
            return results

        return results

    tasks["software_updates"] = asyncio.create_task(check_software_updates_and_ssl())

    # --- Coleta de Dados Síncrona (CPU-bound, rápido) ---
    uptime_str = _format_timedelta(datetime.datetime.now() - START_TIME)
    system_info = f"{platform.system()} {platform.release()}"

    # --- Aguarda a finalização das tarefas assíncronas e monta a mensagem ---
    await asyncio.gather(*tasks.values())
    lib_results = tasks["libs"].result()
    conn_info = tasks["connections"].result()
    py_current, py_latest = tasks["python"].result()
    system_tools = tasks["system_tools"].result()
    miniapp_info = tasks["miniapp"].result()
    soft_updates = tasks["software_updates"].result()

    libs_info_lines = []
    update_buttons = []
    pip_display = "N/A"

    for res in lib_results:
        libs_info_lines.append(res["text"])
        if res["lib_name"] == "pip":
            pip_display = f"<code>{res['version']}</code>"
            if res["update_available"]:
                match = re.search(r"Nova: ([\d.]+)", res["text"])
                if match:
                    pip_display += f" (Nova: {match.group(1)})"

        if res["update_available"]:
            update_buttons.append(
                InlineKeyboardButton(
                    f"⬆️ Atualizar {res['lib_name']}",
                    callback_data=f"update_lib:{res['lib_name']}",
                )
            )
    libs_info = "\n".join(libs_info_lines)

    keyboard = (
        [update_buttons[i : i + 2] for i in range(0, len(update_buttons), 2)]
        if update_buttons
        else []
    )
    # Adiciona botões de Atualizar e Fechar
    keyboard.append([
        InlineKeyboardButton("🔄 Atualizar", callback_data="refresh_diagnostic"),
        InlineKeyboardButton("❌ Fechar", callback_data="close_msg")
    ])
    reply_markup = InlineKeyboardMarkup(keyboard)

    py_display = f"<code>{py_current}</code>"
    if py_latest and py_latest != py_current:
        py_display = f"⚠️ <code>{py_current}</code> (Nova: {py_latest})"

    # --- Formatação do Mini App (Go Backend) ---
    miniapp_status = ""
    if miniapp_info["active"]:
        installed_go = miniapp_info["go_version"].replace("go", "").strip()
        latest_go = soft_updates.get("go")
        go_disp = f"<code>{miniapp_info['go_version']}</code>"
        if latest_go and installed_go and not installed_go.startswith(latest_go) and latest_go not in installed_go:
            go_disp = f"⚠️ <code>{miniapp_info['go_version']}</code> (Nova: <code>go{latest_go}</code>)"
        else:
            go_disp = f"✅ <code>{miniapp_info['go_version']}</code>"

        installed_fiber = miniapp_info["fiber_version"].lstrip("v").strip()
        latest_fiber = soft_updates.get("fiber")
        fiber_disp = f"<code>Fiber {miniapp_info['fiber_version']}</code>"
        if latest_fiber and installed_fiber and installed_fiber != latest_fiber:
            fiber_disp = f"⚠️ <code>Fiber {miniapp_info['fiber_version']}</code> (Nova: <code>v{latest_fiber}</code>)"
        else:
            fiber_disp = f"✅ <code>Fiber {miniapp_info['fiber_version']}</code>"

        miniapp_status = (
            f"<b><u>Mini App (Go Backend)</u></b>\n"
            f"<b>Status:</b> ✅ Ativo\n"
            f"<b>Endpoint:</b> <code>{miniapp_info.get('url', 'N/A')}</code>\n"
            f"<b>Uptime:</b> <code>{miniapp_info['uptime']}</code>\n"
            f"<b>Versão Go:</b> {go_disp}\n"
            f"<b>Framework:</b> {fiber_disp}\n"
            f"<b>Sistema (Go):</b> <code>{miniapp_info['os']}/{miniapp_info['arch']}</code>\n"
            f"<b>Goroutines:</b> <code>{miniapp_info['goroutines']}</code>\n\n"
        )
    else:
        miniapp_errors = miniapp_info.get("errors") or []
        miniapp_error_text = ""
        if miniapp_errors:
            miniapp_error_text = (
                "<b>Tentativas:</b>\n"
                f"<code>{html.escape(chr(10).join(miniapp_errors))}</code>\n"
            )
        miniapp_status = (
            f"<b><u>Mini App (Go Backend)</u></b>\n"
            f"<b>Status:</b> ❌ Inativo (Sem Resposta)\n"
            f"{miniapp_error_text}\n"
        )

    # --- Formatação das Ferramentas de Sistema (Tesseract, Poppler, LibreOffice) ---
    sys_display = system_tools.get("display", {})
    sys_raw = system_tools.get("raw", {})

    # Tesseract
    tess_installed = sys_raw.get("tesseract")
    latest_tess = soft_updates.get("tesseract")
    if tess_installed:
        if latest_tess and not tess_installed.startswith(latest_tess) and latest_tess not in tess_installed:
            tess_disp = f"⚠️ <code>{tess_installed}</code> (Nova: <code>{latest_tess}</code>)"
        else:
            tess_disp = f"✅ <code>{tess_installed}</code>"
    else:
        tess_disp = sys_display.get("tesseract", "N/A")

    # Poppler
    pop_installed = sys_raw.get("pdftoppm") or sys_raw.get("pdfinfo")
    latest_pop = soft_updates.get("poppler")
    if pop_installed:
        if latest_pop and not pop_installed.startswith(latest_pop) and latest_pop not in pop_installed:
            pop_disp = f"⚠️ <code>{pop_installed}</code> (Nova: <code>{latest_pop}</code>)"
        else:
            pop_disp = f"✅ <code>{pop_installed}</code>"
    else:
        pop_disp = sys_display.get("pdftoppm") or sys_display.get("pdfinfo", "N/A")

    # LibreOffice
    lo_installed = sys_raw.get("libreoffice")
    latest_lo = soft_updates.get("libreoffice")
    if lo_installed:
        if latest_lo and not lo_installed.startswith(latest_lo) and latest_lo not in lo_installed:
            lo_disp = f"⚠️ <code>{lo_installed}</code> (Nova estável: <code>{latest_lo}</code>)"
        else:
            lo_disp = f"✅ <code>{lo_installed}</code>"
    else:
        lo_disp = sys_display.get("libreoffice", "N/A")

    # SQLite
    import sqlite3
    sqlite_installed = sqlite3.sqlite_version
    latest_sqlite = soft_updates.get("sqlite")
    if latest_sqlite and sqlite_installed != latest_sqlite:
        sqlite_disp = f"⚠️ <code>{sqlite_installed}</code> (Nova: <code>{latest_sqlite}</code>)"
    else:
        sqlite_disp = f"✅ <code>{sqlite_installed}</code>"

    # --- Formatação dos Certificados SSL / HTTPS ---
    ssl_lines = []
    for s_info in soft_updates.get("ssl", []):
        host = s_info.get("host", "")
        if s_info.get("valid"):
            days = s_info["days"]
            exp_date = s_info["date"]
            if days > 15:
                ssl_lines.append(f"• <b>{host}:</b> ✅ Válido (<code>{days}d restantes</code>, expira em <code>{exp_date}</code>)")
            else:
                ssl_lines.append(f"• <b>{host}:</b> ⚠️ <b>Expira em breve!</b> (<code>{days}d restantes</code>, expira em <code>{exp_date}</code>)")
        else:
            err = s_info.get("error", "Falha")
            ssl_lines.append(f"• <b>{host}:</b> ❌ {err}")
    ssl_display = "\n".join(ssl_lines) if ssl_lines else "• N/A"

    final_msg = (
        f"🩺 <b>Relatório de Diagnóstico do Bot</b>\n\n"
        f"<b><u>Bot & Ambiente</u></b>\n"
        f"<b>Uptime:</b> <code>{uptime_str}</code>\n"
        f"<b>Versão Python:</b> {py_display}\n"
        f"<b>Versão Pip:</b> {pip_display}\n"
        f"<b>Sistema:</b> <code>{system_info}</code>\n\n"
        f"{miniapp_status}"
        f"<b><u>Ferramentas de Sistema</u></b>\n"
        f"<b>ONNX Runtime:</b> <code>{sys_display.get('onnx', 'N/A')}</code>\n"
        f"<b>Tesseract OCR:</b> {tess_disp}\n"
        f"<b>Idiomas OCR:</b> <code>{sys_display.get('tesseract_langs', 'N/A')}</code>\n"
        f"<b>Motor PDF:</b> <code>{sys_display.get('pdf_engine', 'N/A')}</code>\n"
        f"<b>LibreOffice:</b> {lo_disp}\n\n"
        f"<b><u>Versões das Bibliotecas</u></b>\n"
        f"<code>{libs_info}</code>\n\n"
        f"<b><u>Conexões & DB</u></b>\n"
        f"<b>API Telegram:</b> ✅ Conectado (<code>{conn_info['telegram']:.2f} ms</code>)\n"
        f"<b>Banco de Dados:</b> ✅ Conectado (<code>{conn_info['db_latency']:.2f} ms</code>)\n"
        f"<b>Versão SQLite:</b> {sqlite_disp}\n"
        f"<b>Internet (DNS):</b> {conn_info['internet']}\n"
        f"<b>Tamanho do DB:</b> <code>{conn_info['db_size']:.2f} MB</code>\n"
        f"<b>Usuários:</b> <code>{conn_info['users']}</code>\n\n"
        f"<b><u>Certificados SSL / HTTPS</u></b>\n"
        f"{ssl_display}\n"
    )

    await msg.edit_text(final_msg, parse_mode="HTML", reply_markup=reply_markup)


# --- MONITORAMENTO DE JOBS ---

async def backup_db_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envia o arquivo do banco de dados para o admin."""
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return

    if not os.path.exists(DB_FILE):
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"❌ Arquivo do banco de dados não encontrado em: <code>{DB_FILE}</code>",
            parse_mode="HTML",
            reply_markup=get_admin_markup()
        )
        return

    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text="O backup do banco deve ser realizado por um canal administrativo seguro, fora do Telegram.",
            reply_markup=get_admin_markup(),
        )
    except Exception as e:
        logger.error(f"Erro ao enviar backup do DB: {e}")
        await context.bot.send_message(
            chat_id=ADMIN_ID, text=f"Ocorreu um erro ao enviar o backup: {e}",
            reply_markup=get_admin_markup()
        )


async def scheduled_backup_db(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Realiza VACUUM, envia relatório, e faz backup automático do banco de dados e envia para o admin."""
    if not ADMIN_ID or not os.path.exists(DB_FILE):
        return

    try:
        size_db_before = os.path.getsize(DB_FILE) / (1024 * 1024)

        async with aiosqlite.connect(DB_FILE) as db:
            await db.execute("VACUUM")

        size_db_after = os.path.getsize(DB_FILE) / (1024 * 1024)

        msg = (
            "🧹 <b>VACUUM Diário Concluído</b>\n\n"
            "📊 <b>Banco de Dados:</b>\n"
            f"Antes: {size_db_before:.2f} MB\n"
            f"Depois: {size_db_after:.2f} MB\n"
            f"Redução: {size_db_before - size_db_after:.2f} MB"
        )
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=msg,
            parse_mode="HTML"
        )
        logger.info("VACUUM automático realizado com sucesso.")

        logger.info("VACUUM automático realizado com sucesso; backup não enviado pelo Telegram.")
    except Exception as e:
        logger.error(f"Erro no vacuum/backup automático: {e}")


async def _broadcast_task(bot, users, payload, status_chat_id, status_message_id):
    """Tarefa em background para envio de broadcast concorrente em lotes."""
    success_count = 0
    fail_count = 0
    total_users = len(users)
    start_time = time.time()
    last_update_time = start_time

    # Configuração de Rate Limit (Envio concorrente em lotes)
    BATCH_SIZE = 20
    BATCH_DELAY = 1.2  # Segundos de pausa entre lotes (~15-20 msgs/s)

    async def _send_single(uid, username):
        nonlocal success_count, fail_count
        if uid == ADMIN_ID:
            return
        try:
            if payload["type"] == "text":
                await bot.send_message(
                    chat_id=uid, text=payload["text"], parse_mode="HTML"
                )
            elif payload["type"] == "copy":
                kwargs = {
                    "chat_id": uid,
                    "from_chat_id": payload["from_chat_id"],
                    "message_id": payload["message_id"],
                }
                if "caption" in payload:
                    kwargs["caption"] = payload["caption"]
                    kwargs["parse_mode"] = "HTML"
                await bot.copy_message(**kwargs)
            success_count += 1
        except Exception as e:
            fail_count += 1
            logger.warning(
                f"Falha no broadcast para user_id={uid}, username=@{username}: {e}"
            )

    for i in range(0, total_users, BATCH_SIZE):
        batch = users[i:i + BATCH_SIZE]
        tasks = [_send_single(uid, uname) for uid, uname in batch]
        await asyncio.gather(*tasks, return_exceptions=True)

        processed = min(i + len(batch), total_users)
        current_time = time.time()

        # Atualiza o status a cada 5 segundos ou ao concluir
        if current_time - last_update_time >= 5 or processed == total_users:
            elapsed = current_time - start_time
            if processed > 0:
                avg_time = elapsed / processed
                remaining = total_users - processed
                est_seconds = remaining * avg_time
                est_str = _format_timedelta(
                    datetime.timedelta(seconds=int(est_seconds))
                )
                percent = (processed / total_users) * 100

                try:
                    await bot.edit_message_text(
                        chat_id=status_chat_id,
                        message_id=status_message_id,
                        text=f"📢 <b>Broadcast em andamento (Background)...</b>\n\n"
                        f"✅ Enviados: {success_count}\n"
                        f"❌ Falhas: {fail_count}\n"
                        f"📊 Progresso: {processed}/{total_users} ({percent:.1f}%)\n"
                        f"⏱ Estimativa: {est_str}",
                        parse_mode="HTML",
                    )
                except Exception:
                    pass
            last_update_time = current_time

        if processed < total_users:
            await asyncio.sleep(BATCH_DELAY)

    total_duration = time.time() - start_time
    duration_str = _format_timedelta(datetime.timedelta(seconds=int(total_duration)))

    # Define o que exibir no histórico (Texto ou indicação de mídia)
    display_msg = (
        payload.get("text") or payload.get("caption") or "[Mídia/Mensagem Copiada]"
    )
    global LAST_BROADCAST_STATS
    LAST_BROADCAST_STATS = {
        "date": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
        "message": display_msg,
        "success": success_count,
        "failed": fail_count,
        "total": total_users,
        "duration": duration_str,
    }

    await bot.edit_message_text(
        chat_id=status_chat_id,
        message_id=status_message_id,
        text=f"✅ <b>Broadcast finalizado!</b>\n\n"
        f"⏱ Duração: {duration_str}\n"
        f"✅ Envios com sucesso: {success_count}\n"
        f"❌ Falhas (bloqueios/erros): {fail_count}",
        parse_mode="HTML",
    )


BROADCAST_MULTI_LANGUAGES = [
    ("pt", "🇧🇷 Português"),
    ("en", "🇺🇸 English (+Outros)"),
    ("es", "🇪🇸 Español"),
    ("it", "🇮🇹 Italiano"),
    ("fr", "🇫🇷 Français"),
    ("ru", "🇷🇺 Русский"),
    ("uk", "🇺🇦 Українська"),
    ("ar", "🇸🇦 العربية"),
]


async def _broadcast_multi_task(
    bot,
    grouped_users: dict[str, list[tuple[int, str]]],
    multi_texts: dict[str, str],
    base_payload: dict,
    status_chat_id: int,
    status_message_id: int,
) -> None:
    """Tarefa em background para envio de broadcast multi-idioma com checklist de status ao vivo."""
    start_time = time.time()
    last_update_time = start_time
    total_users_all = sum(len(u_list) for u_list in grouped_users.values())

    stats = {}
    for code, _ in BROADCAST_MULTI_LANGUAGES:
        u_list = grouped_users.get(code, [])
        stats[code] = {
            "total": len(u_list),
            "processed": 0,
            "success": 0,
            "failed": 0,
            "done": len(u_list) == 0,
        }

    BATCH_SIZE = 20
    BATCH_DELAY = 1.2

    total_processed_all = 0
    total_success_all = 0
    total_failed_all = 0

    def _render_progress_text(is_final: bool = False) -> str:
        elapsed = time.time() - start_time
        if total_processed_all > 0 and not is_final:
            avg_time = elapsed / total_processed_all
            remaining = total_users_all - total_processed_all
            est_seconds = remaining * avg_time
            est_str = _format_timedelta(datetime.timedelta(seconds=int(est_seconds)))
        else:
            est_str = "00s"

        percent_all = (total_processed_all / total_users_all * 100) if total_users_all > 0 else 100.0

        header = "✅ <b>Broadcast Multi-idioma Finalizado!</b>\n\n" if is_final else "📢 <b>Broadcast Multi-idioma em andamento (Background)...</b>\n\n"

        lines = [header, "📋 <b>Status por Idioma:</b>"]
        for code, label in BROADCAST_MULTI_LANGUAGES:
            st = stats[code]
            if st["total"] == 0:
                lines.append(f"⚪ {label}: 0/0 (Sem usuários)")
            elif st["done"] or is_final:
                lines.append(f"✅ {label}: {st['processed']}/{st['total']} (Finalizado)")
            elif st["processed"] > 0:
                lines.append(f"⏳ {label}: {st['processed']}/{st['total']} (Enviando...)")
            else:
                lines.append(f"🕒 {label}: 0/{st['total']} (Aguardando)")

        lines.append("")
        if not is_final:
            lines.append(f"👥 <b>Progresso Geral:</b> {total_processed_all}/{total_users_all} ({percent_all:.1f}%)")
            lines.append(f"✅ Sucessos: {total_success_all} | ❌ Falhas: {total_failed_all}")
            lines.append(f"⏱ Estimativa restante: {est_str}")
        else:
            duration_str = _format_timedelta(datetime.timedelta(seconds=int(elapsed)))
            lines.append(f"⏱ <b>Duração total:</b> {duration_str}")
            lines.append(f"✅ <b>Total entregues:</b> {total_success_all}")
            lines.append(f"❌ <b>Total de falhas:</b> {total_failed_all}")

        return "\n".join(lines)

    async def _send_single(uid, uname, lang_code, text_content):
        nonlocal total_success_all, total_failed_all
        if uid == ADMIN_ID:
            return
        try:
            p_type = base_payload.get("type", "text")
            if p_type == "text":
                await bot.send_message(
                    chat_id=uid, text=text_content, parse_mode="HTML"
                )
            elif p_type == "copy":
                kwargs = {
                    "chat_id": uid,
                    "from_chat_id": base_payload["from_chat_id"],
                    "message_id": base_payload["message_id"],
                }
                if text_content:
                    kwargs["caption"] = text_content
                    kwargs["parse_mode"] = "HTML"
                await bot.copy_message(**kwargs)
            stats[lang_code]["success"] += 1
            total_success_all += 1
        except Exception as e:
            stats[lang_code]["failed"] += 1
            total_failed_all += 1
            logger.warning(f"Falha no broadcast multi para user_id={uid} (lang={lang_code}): {e}")

    # Itera por cada idioma sequencialmente
    for code, label in BROADCAST_MULTI_LANGUAGES:
        u_list = grouped_users.get(code, [])
        if not u_list:
            stats[code]["done"] = True
            continue

        text_content = multi_texts.get(code, "")

        for i in range(0, len(u_list), BATCH_SIZE):
            batch = u_list[i:i + BATCH_SIZE]
            tasks = [_send_single(uid, uname, code, text_content) for uid, uname in batch]
            await asyncio.gather(*tasks, return_exceptions=True)

            stats[code]["processed"] += len(batch)
            total_processed_all += len(batch)
            current_time = time.time()

            # Atualiza status a cada 5 segundos
            if current_time - last_update_time >= 5:
                try:
                    await bot.edit_message_text(
                        chat_id=status_chat_id,
                        message_id=status_message_id,
                        text=_render_progress_text(is_final=False),
                        parse_mode="HTML",
                    )
                except Exception:
                    pass
                last_update_time = current_time

            if total_processed_all < total_users_all:
                await asyncio.sleep(BATCH_DELAY)

        stats[code]["done"] = True
        try:
            await bot.edit_message_text(
                chat_id=status_chat_id,
                message_id=status_message_id,
                text=_render_progress_text(is_final=False),
                parse_mode="HTML",
            )
            last_update_time = time.time()
        except Exception:
            pass

    # Finalização
    total_duration = time.time() - start_time
    duration_str = _format_timedelta(datetime.timedelta(seconds=int(total_duration)))

    global LAST_BROADCAST_STATS
    LAST_BROADCAST_STATS = {
        "date": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
        "message": f"[Multi-idioma] {multi_texts.get('pt', '')[:80]}...",
        "success": total_success_all,
        "failed": total_failed_all,
        "total": total_users_all,
        "duration": duration_str,
    }

    try:
        await bot.edit_message_text(
            chat_id=status_chat_id,
            message_id=status_message_id,
            text=_render_progress_text(is_final=True),
            parse_mode="HTML",
        )
    except Exception:
        pass


async def handle_broadcast_multi_input(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    """Intercepta mensagens de texto do admin durante a coleta de mensagens multi-idioma."""
    user = update.effective_user
    if not user or user.id != ADMIN_ID:
        return False

    if "broadcast_multi_step" not in context.user_data:
        return False

    message = update.message
    if not message or not message.text:
        return False

    text_raw = message.text.strip()
    if text_raw in ("/cancel", "❌ Cancelar", "Cancelar"):
        context.user_data.pop("broadcast_multi_step", None)
        context.user_data.pop("broadcast_multi_texts", None)
        context.user_data.pop("broadcast_payload", None)
        await message.reply_html("❌ <b>Broadcast multi-idioma cancelado.</b>")
        return True

    step = context.user_data.get("broadcast_multi_step", 0)
    texts = context.user_data.get("broadcast_multi_texts", {})

    # Captura o texto com formatação HTML
    html_text = message.text_html

    curr_code, curr_label = BROADCAST_MULTI_LANGUAGES[step]
    texts[curr_code] = html_text
    context.user_data["broadcast_multi_texts"] = texts

    next_step = step + 1
    if next_step < len(BROADCAST_MULTI_LANGUAGES):
        context.user_data["broadcast_multi_step"] = next_step
        next_code, next_label = BROADCAST_MULTI_LANGUAGES[next_step]

        cancel_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancelar", callback_data="broadcast_multi_cancel")]
        ])

        await message.reply_html(
            f"✅ <b>{curr_label} salvo!</b>\n\n"
            f"🌐 <b>Broadcast Multi-idioma ({next_step + 1}/{len(BROADCAST_MULTI_LANGUAGES)})</b>\n\n"
            f"Agora envie o texto em {next_label}:",
            reply_markup=cancel_kb,
        )
        return True

    # Se chegou ao fim dos 7 idiomas
    context.user_data.pop("broadcast_multi_step", None)

    # Conta usuários por idioma no banco de dados
    counts = {}
    async with aiosqlite.connect(DB_FILE) as db:
        for code, label in BROADCAST_MULTI_LANGUAGES:
            if code == "en":
                sql = """
                    SELECT COUNT(*) FROM users
                    WHERE user_id != ? AND (
                        custom_language = 'en'
                        OR (
                            custom_language IS NULL
                            AND (
                                language_code LIKE 'en%'
                                OR SUBSTR(language_code, 1, 2) NOT IN ('pt', 'es', 'it', 'ru', 'ar', 'fr', 'uk')
                            )
                        )
                    )
                """
                async with db.execute(sql, (ADMIN_ID,)) as cursor:
                    row = await cursor.fetchone()
                    counts["en"] = row[0] if row else 0
            else:
                sql = """
                    SELECT COUNT(*) FROM users
                    WHERE user_id != ? AND (
                        custom_language = ?
                        OR (custom_language IS NULL AND language_code LIKE ?)
                    )
                """
                async with db.execute(sql, (ADMIN_ID, code, f"{code}%")) as cursor:
                    row = await cursor.fetchone()
                    counts[code] = row[0] if row else 0

    total_recipients = sum(counts.values())

    lines = [
        "📢 <b>Confirmação de Broadcast Multi-idioma</b>\n",
        f"👥 <b>Total de destinatários:</b> {total_recipients} usuários\n",
        "📊 <b>Distribuição por Idioma:</b>",
    ]
    for code, label in BROADCAST_MULTI_LANGUAGES:
        c = counts.get(code, 0)
        lines.append(f"• {label}: <b>{c}</b> usuários")

    lines.append("\n<b>Deseja iniciar o disparo para todos os idiomas agora?</b>")

    confirm_kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🚀 Iniciar Envio Multi-idioma", callback_data="broadcast_multi_confirm:yes"),
            InlineKeyboardButton("❌ Cancelar", callback_data="broadcast_multi_cancel"),
        ]
    ])

    await message.reply_html("\n".join(lines), reply_markup=confirm_kb)
    return True


async def handle_broadcast_multi_cancel(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Cancela o fluxo de broadcast multi-idioma."""
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        return
    context.user_data.pop("broadcast_multi_step", None)
    context.user_data.pop("broadcast_multi_texts", None)
    context.user_data.pop("broadcast_payload", None)
    await query.edit_message_text("❌ <b>Broadcast multi-idioma cancelado.</b>", parse_mode="HTML")


async def handle_broadcast_multi_confirm(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Inicia o disparo em background para cada idioma."""
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        return

    multi_texts = context.user_data.get("broadcast_multi_texts")
    base_payload = context.user_data.get("broadcast_payload", {"type": "text"})

    if not multi_texts:
        await query.edit_message_text("⚠️ <b>Sessão expirada.</b> Inicie o /broadcast novamente.", parse_mode="HTML")
        return

    context.user_data.pop("broadcast_multi_texts", None)
    context.user_data.pop("broadcast_payload", None)

    # Busca todos os usuários e agrupa por idioma
    grouped_users: dict[str, list[tuple[int, str]]] = {code: [] for code, _ in BROADCAST_MULTI_LANGUAGES}

    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT user_id, username, custom_language, language_code FROM users WHERE user_id != ?", (ADMIN_ID,)) as cursor:
            rows = await cursor.fetchall()
            for uid, uname, custom_lang, lang_code in rows:
                resolved = "en"
                if custom_lang in ("pt", "es", "it", "fr", "ru", "ar", "uk", "en"):
                    resolved = custom_lang
                elif lang_code:
                    prefix = lang_code[:2].lower()
                    if prefix in ("pt", "es", "it", "fr", "ru", "ar", "uk"):
                        resolved = prefix
                grouped_users[resolved].append((uid, uname or ""))

    total_users_all = sum(len(u_list) for u_list in grouped_users.values())
    if total_users_all == 0:
        await query.edit_message_text("⚠️ <b>Nenhum usuário encontrado no banco de dados.</b>", parse_mode="HTML")
        return

    await query.edit_message_text("🚀 <b>Iniciando Broadcast Multi-idioma em background...</b>", parse_mode="HTML")

    asyncio.create_task(
        _broadcast_multi_task(
            context.bot,
            grouped_users,
            multi_texts,
            base_payload,
            query.message.chat_id,
            query.message.message_id,
        )
    )


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envia uma mensagem para todos os usuários registrados (Apenas Admin)."""
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return

    payload = {}

    # 1. Se for resposta a uma mensagem, copia ela
    if update.message.reply_to_message:
        payload = {
            "type": "copy",
            "from_chat_id": update.message.chat_id,
            "message_id": update.message.reply_to_message.message_id,
        }

    # 2. Se tiver mídia na mensagem do comando (Caption contém o comando)
    elif update.message.caption:
        html_caption = update.message.caption_html
        parts_html = html_caption.split(maxsplit=1)
        new_caption = parts_html[1] if len(parts_html) > 1 else ""
        payload = {
            "type": "copy",
            "from_chat_id": update.message.chat_id,
            "message_id": update.message.message_id,
            "caption": new_caption,
        }

    # 3. Se for apenas texto
    elif update.message.text:
        parts = update.message.text.split(maxsplit=1)
        if len(parts) < 2:
            await update.message.reply_html(
                "⚠️ <b>Uso incorreto.</b>\nExemplo: <code>/broadcast Olá a todos!</code>\nOu responda a uma mensagem/envie mídia com a legenda."
            )
            return
        html_text = update.message.text_html
        parts_html = html_text.split(maxsplit=1)
        payload = {"type": "text", "text": parts_html[1]}

    else:
        await update.message.reply_html("⚠️ Formato não suportado para broadcast.")
        return

    # Salva o payload no contexto do usuário para usar após a seleção do idioma
    context.user_data["broadcast_payload"] = payload

    # Cria o teclado de seleção de idioma com opção Multi-idioma
    keyboard = [
        [
            InlineKeyboardButton("🌐 Multi-idioma", callback_data="broadcast:multi"),
            InlineKeyboardButton("📢 Todos (Texto Único)", callback_data="broadcast:all"),
        ],
        [InlineKeyboardButton("🇸🇦 العربية", callback_data="broadcast:ar")],
        [
            InlineKeyboardButton("🇧🇷 Português", callback_data="broadcast:pt"),
            InlineKeyboardButton("🇺🇸 English (+Outros)", callback_data="broadcast:en"),
        ],
        [
            InlineKeyboardButton("🇪🇸 Español", callback_data="broadcast:es"),
            InlineKeyboardButton("🇮🇹 Italiano", callback_data="broadcast:it"),
        ],
        [
            InlineKeyboardButton("🇷🇺 Русский", callback_data="broadcast:ru"),
            InlineKeyboardButton("🇺🇦 Українська", callback_data="broadcast:uk"),
        ],
        [
            InlineKeyboardButton("🇫🇷 Français", callback_data="broadcast:fr"),
            InlineKeyboardButton("❌ Cancelar", callback_data="broadcast:cancel"),
        ],
    ]
    await update.message.reply_html(
        "📢 <b>Configuração de Broadcast</b>\n\n"
        "Selecione o público-alvo para esta mensagem:\n"
        "• <b>Multi-idioma:</b> Solicita a mensagem traduzida em cada idioma e dispara para cada usuário no seu idioma respectivo.\n"
        "• <b>Individual:</b> Dispara a mensagem atual apenas para os usuários do idioma escolhido.\n"
        "• <b>Todos:</b> Dispara a mensagem atual para todos sem distinção.",
        reply_markup=get_admin_markup(keyboard),
    )


async def handle_broadcast_selection(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Processa a seleção de idioma e solicita confirmação."""
    query = update.callback_query
    await query.answer()
    user = query.from_user

    if user.id != ADMIN_ID:
        return

    target = query.data.split(":")[1]

    # Verifica cancelamento
    if target == "cancel":
        context.user_data.pop("broadcast_payload", None)
        await query.edit_message_text(
            "❌ <b>Broadcast cancelado.</b>", parse_mode="HTML"
        )
        return

    # Inicia fluxo Multi-idioma
    if target == "multi":
        context.user_data["broadcast_multi_step"] = 0
        context.user_data["broadcast_multi_texts"] = {}

        first_code, first_label = BROADCAST_MULTI_LANGUAGES[0]
        cancel_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancelar", callback_data="broadcast_multi_cancel")]
        ])

        await query.edit_message_text(
            f"🌐 <b>Broadcast Multi-idioma (1/{len(BROADCAST_MULTI_LANGUAGES)})</b>\n\n"
            f"Envie a mensagem em {first_label}:\n\n"
            f"<i>(Você pode usar formatação HTML como negrito, itálico, links e emojis)</i>",
            parse_mode="HTML",
            reply_markup=cancel_kb,
        )
        return

    # Recupera o payload
    payload = context.user_data.get("broadcast_payload")
    if not payload:
        await query.edit_message_text(
            "⚠️ <b>Sessão expirada.</b> Por favor, inicie o comando /broadcast novamente.",
            parse_mode="HTML",
        )
        return

    # Define a query SQL baseada na seleção
    sql = ""
    params = ()
    target_name = ""

    if target == "all":
        sql = "SELECT user_id, username FROM users WHERE user_id != ?"
        params = (ADMIN_ID,)
        target_name = "Todos os usuários"
    elif target == "en":
        # Inglês + Idiomas não suportados (Fallback)
        sql = """
            SELECT user_id, username FROM users
            WHERE user_id != ? AND (
                custom_language = 'en'
                OR (
                    custom_language IS NULL
                    AND (
                        language_code LIKE 'en%'
                        OR SUBSTR(language_code, 1, 2) NOT IN ('pt', 'es', 'it', 'ru', 'ar', 'fr', 'uk')
                    )
                )
            )
        """
        params = (ADMIN_ID,)
        target_name = "Inglês + Outros"
    else:
        # Idiomas específicos (pt, es, it, ru, ar, fr, uk)
        sql = """
            SELECT user_id, username FROM users
            WHERE user_id != ? AND (
                custom_language = ?
                OR (custom_language IS NULL AND language_code LIKE ?)
            )
        """
        params = (ADMIN_ID, target, f"{target}%")
        lang_map = {
            "pt": "Português",
            "es": "Espanhol",
            "it": "Italiano",
            "fr": "Français",
            "ru": "Russo",
            "uk": "Ucraniano",
            "ar": "Árabe",
        }
        target_name = lang_map.get(target, target)

    # Executa a busca para contagem
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute(sql, params) as cursor:
            users = await cursor.fetchall()

    if not users:
        await query.edit_message_text(
            f"⚠️ <b>Nenhum usuário encontrado para o filtro:</b> {target_name}",
            parse_mode="HTML",
        )
        return

    # Salva dados para a confirmação
    context.user_data["broadcast_sql"] = sql
    context.user_data["broadcast_params"] = params
    context.user_data["broadcast_target_name"] = target_name

    # Prepara a prévia
    preview = ""
    if payload.get("type") == "text":
        preview = payload["text"]
    elif payload.get("type") == "copy":
        caption = payload.get("caption", "")
        preview = f"[Mídia/Mensagem Copiada] {caption}"

    if len(preview) > 150:
        preview = preview[:147] + "..."

    msg_text = (
        f"📢 <b>Confirmação de Broadcast</b>\n\n"
        f"🎯 <b>Público:</b> {target_name}\n"
        f"👥 <b>Destinatários:</b> {len(users)}\n\n"
        f"📝 <b>Prévia:</b>\n<i>{html.escape(preview)}</i>\n\n"
        f"<b>Deseja enviar agora?</b>"
    )

    keyboard = [
        [
            InlineKeyboardButton("✅ Enviar", callback_data="broadcast_confirm:yes"),
            InlineKeyboardButton("❌ Cancelar", callback_data="broadcast_confirm:no"),
        ]
    ]

    await query.edit_message_text(
        msg_text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_broadcast_confirmation(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Executa o broadcast após confirmação."""
    query = update.callback_query
    await query.answer()
    user = query.from_user

    if user.id != ADMIN_ID:
        return

    action = query.data.split(":")[1]

    if action == "no":
        context.user_data.pop("broadcast_payload", None)
        context.user_data.pop("broadcast_sql", None)
        context.user_data.pop("broadcast_params", None)
        context.user_data.pop("broadcast_target_name", None)
        await query.edit_message_text(
            "❌ <b>Broadcast cancelado.</b>", parse_mode="HTML"
        )
        return

    # Recupera dados
    payload = context.user_data.get("broadcast_payload")
    sql = context.user_data.get("broadcast_sql")
    params = context.user_data.get("broadcast_params")
    target_name = context.user_data.get("broadcast_target_name")

    if not payload or not sql:
        await query.edit_message_text("⚠️ <b>Sessão expirada.</b>", parse_mode="HTML")
        return

    # Limpa contexto
    context.user_data.pop("broadcast_payload", None)
    context.user_data.pop("broadcast_sql", None)
    context.user_data.pop("broadcast_params", None)
    context.user_data.pop("broadcast_target_name", None)

    # Busca usuários novamente
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute(sql, params) as cursor:
            users = await cursor.fetchall()

    if not users:
        await query.edit_message_text(
            "⚠️ <b>Nenhum usuário encontrado no momento.</b>", parse_mode="HTML"
        )
        return

    await query.edit_message_text(
        f"📢 <b>Iniciando broadcast para: {target_name} ({len(users)} usuários)...</b>",
        parse_mode="HTML",
    )

    # Inicia a tarefa em background
    asyncio.create_task(
        _broadcast_task(
            context.bot, users, payload, query.message.chat_id, query.message.message_id
        )
    )


async def broadcast_user_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Envia mensagem/mídia para um usuário específico (Apenas Admin)."""
    user = update.effective_user
    user_id = user.id
    if user_id != ADMIN_ID:
        return

    # Determina o texto base para parsing (texto ou legenda)
    text_content = update.message.text or update.message.caption or ""
    parts = text_content.split(maxsplit=2)

    html_content = ""
    if update.message.text:
        html_content = update.message.text_html
    elif update.message.caption:
        html_content = update.message.caption_html

    html_parts = html_content.split(maxsplit=2) if html_content else []

    # Se for reply, o target é o primeiro argumento. Se não, também.
    # Ex: /broadcast_usuario 12345 msg...
    # Ex Reply: /broadcast_usuario 12345

    target_str = None
    if len(parts) >= 2:
        target_str = parts[1]

    if not target_str:
        await update.message.reply_html(
            "⚠️ Uso: <code>/broadcast_usuario [id/@user] [mensagem]</code>\nVocê também pode responder a uma mensagem ou enviar mídia com o comando na legenda.",
            reply_markup=get_admin_markup()
        )
        return

    # Resolve target
    target_uid = None
    if target_str.isdigit():
        target_uid = int(target_str)
    else:
        username = target_str.lstrip("@")
        async with aiosqlite.connect(DB_FILE) as db:
            async with db.execute(
                "SELECT user_id FROM users WHERE username LIKE ?", (username,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    target_uid = row[0]

    if not target_uid:
        await update.message.reply_html("❌ Usuário não encontrado no banco de dados.", reply_markup=get_admin_markup())
        return

    try:
        # 1. Reply
        if update.message.reply_to_message:
            await context.bot.copy_message(
                chat_id=target_uid,
                from_chat_id=update.message.chat_id,
                message_id=update.message.reply_to_message.message_id,
            )
            await update.message.reply_html(
                f"✅ Mensagem copiada para <code>{target_uid}</code>."
            )

        # 2. Mídia com legenda (Comando na legenda)
        elif update.message.caption:
            new_caption = html_parts[2] if len(html_parts) > 2 else ""
            await context.bot.copy_message(
                chat_id=target_uid,
                from_chat_id=update.message.chat_id,
                message_id=update.message.message_id,
                caption=new_caption,
                parse_mode="HTML",
            )
            await update.message.reply_html(
                f"✅ Mídia enviada para <code>{target_uid}</code>."
            )

        # 3. Texto
        elif update.message.text:
            if len(parts) < 3:
                await update.message.reply_html("⚠️ Digite a mensagem a ser enviada.")
                return
            msg = html_parts[2]
            await context.bot.send_message(
                chat_id=target_uid, text=msg, parse_mode="HTML"
            )
            await update.message.reply_html(
                f"✅ Mensagem enviada para <code>{target_uid}</code>."
            )

    except Exception as e:
        await update.message.reply_html(f"❌ Erro ao enviar: {e}")


async def broadcast_last_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Exibe o resultado do último broadcast (Apenas Admin)."""
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return

    if not LAST_BROADCAST_STATS:
        await update.message.reply_html(
            "ℹ️ Nenhum broadcast registrado desde o início do bot."
        )
        return

    stats = LAST_BROADCAST_STATS
    # Trunca mensagem longa para exibição
    msg_preview = stats["message"]
    if len(msg_preview) > 100:
        msg_preview = msg_preview[:97] + "..."

    msg = (
        f"📢 <b>Último Broadcast</b>\n"
        f"📅 <b>Data:</b> {stats['date']}\n"
        f"⏱ <b>Duração:</b> {stats['duration']}\n\n"
        f"✅ <b>Sucesso:</b> {stats['success']}\n"
        f"❌ <b>Falhas:</b> {stats['failed']}\n"
        f"👥 <b>Total processado:</b> {stats['total']}\n\n"
        f"📝 <b>Mensagem:</b>\n<i>{html.escape(msg_preview)}</i>"
    )
    await update.message.reply_html(msg, reply_markup=get_admin_markup())


async def logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envia as últimas linhas do log (Apenas Admin)."""
    user = update.effective_user
    user_id = user.id
    if user_id != ADMIN_ID:
        return

    lines_to_read = 50
    if context.args:
        try:
            lines_to_read = int(context.args[0])
        except ValueError:
            await update.message.reply_html(
                "⚠️ <b>Valor inválido.</b> Use: <code>/logs 50</code>",
                reply_markup=get_admin_markup()
            )
            return

    log_file = "bot.log"
    if not os.path.exists(log_file):
        await update.message.reply_html("❌ <b>Arquivo de log não encontrado.</b>", reply_markup=get_admin_markup())
        return

    try:
        def _read_tail_log(filepath: str, max_lines: int) -> str:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                lines = deque(f, maxlen=max_lines)
                return "".join(lines)

        content = await asyncio.to_thread(_read_tail_log, log_file, lines_to_read)

        if not content:
            await update.message.reply_html("ℹ️ <b>O log está vazio.</b>", reply_markup=get_admin_markup())
            return

        if len(content) > 4000:
            f_bytes = io.BytesIO(content.encode("utf-8"))
            f_bytes.name = "logs.txt"
            await update.message.reply_document(
                document=f_bytes, caption=f"📋 Últimas {lines_to_read} linhas do log.",
                reply_markup=get_admin_markup()
            )
        else:
            await update.message.reply_html(
                f"📋 <b>Últimas {lines_to_read} linhas do log:</b>\n\n<pre>{html.escape(content)}</pre>",
                reply_markup=get_admin_markup()
            )
    except Exception as e:
        logger.error(f"Erro ao ler logs: {e}")
        await update.message.reply_html(f"❌ <b>Erro ao ler logs:</b> {e}", reply_markup=get_admin_markup())




async def restart_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reinicia o processo do bot (Apenas Admin)."""
    user = update.effective_user
    if user.id != ADMIN_ID:
        return

    await update.message.reply_html(
        "🔄 <b>Reiniciando o bot...</b>\nEstarei de volta em alguns segundos!",
        reply_markup=get_admin_markup()
    )

    # Pequena pausa para garantir que a mensagem seja enviada antes de reiniciar
    await asyncio.sleep(1)

    # Reinicia o processo atual substituindo-o pelo novo
    os.execl(sys.executable, sys.executable, *sys.argv)


async def restart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reinicia o bot a partir de um botão (Apenas Admin)."""
    query = update.callback_query
    await query.answer()

    user = query.from_user
    if user.id != ADMIN_ID:
        return

    # Edita a mensagem existente para confirmar o reinício
    await query.edit_message_text(
        "🔄 <b>Reiniciando o bot...</b>\nEstarei de volta em alguns segundos!",
        parse_mode="HTML",
        reply_markup=get_admin_markup()
    )

    # Pequena pausa para garantir que a mensagem seja enviada antes de reiniciar
    await asyncio.sleep(1)

    # Reinicia o processo atual substituindo-o pelo novo
    os.execl(sys.executable, sys.executable, *sys.argv)


async def handle_lib_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lida com o clique no botão para atualizar uma biblioteca."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if user_id != ADMIN_ID:
        return

    lib_name = query.data.split(":", 1)[1]

    try:
        # Remove os botões e informa sobre a atualização
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_html(
            f"🔄 <b>Atualizando {lib_name}...</b> Isso pode levar um momento."
        )
    except Exception as e:
        logger.error(f"Erro ao editar mensagem de atualização: {e}")

    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "pip",
        "install",
        "--upgrade",
        lib_name,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode == 0:
        # Executa a atualização do requirements.txt em uma thread para não bloquear
        await asyncio.to_thread(update_requirements_file, lib_name)

        success_msg = (
            f"✅ <b>{lib_name} atualizado com sucesso!</b>\n\n"
            f"O arquivo <code>requirements.txt</code> foi atualizado.\n\n"
            f"É altamente recomendado reiniciar o bot para aplicar as mudanças."
        )
        keyboard = [
            [InlineKeyboardButton("🔄 Reiniciar Agora", callback_data="restart_bot")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.message.reply_html(success_msg, reply_markup=reply_markup)
    else:
        error_msg = (
            f"❌ <b>Falha ao atualizar {lib_name}.</b>\n\n"
            f"<b>Erro:</b>\n<pre>{html.escape(stderr.decode('utf-8', 'ignore'))}</pre>"
        )
        await query.message.reply_html(error_msg)


async def pause_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Pausa o bot para manutenção (Apenas Admin)."""
    user = update.effective_user
    if user.id != ADMIN_ID:
        return

    global BOT_PAUSED
    if BOT_PAUSED:
        await update.message.reply_html("⚠️ O bot já está pausado.")
        return

    BOT_PAUSED = True
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute(
            "INSERT OR REPLACE INTO system_config (key, value) VALUES ('paused', '1')"
        )
        await db.commit()

    await update.message.reply_html(
        "⏸ <b>Bot Pausado</b>\nNovas imagens não serão processadas.",
        reply_markup=get_admin_markup()
    )
    logger.info(f"Bot pausado por {user.first_name} ({user.id})")



async def send_daily_summary_report(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envia um relatório das últimas 24h para o admin com estatísticas detalhadas."""
    if not ADMIN_ID:
        return

    try:
        async with aiosqlite.connect(DB_FILE) as db:
            # 1. Estatísticas de Novos Usuários
            query_new_users = "SELECT COUNT(*) FROM users WHERE joined_at > DATETIME('now', '-24 hours')"
            query_prev_new_users = "SELECT COUNT(*) FROM users WHERE joined_at <= DATETIME('now', '-24 hours') AND joined_at > DATETIME('now', '-48 hours')"
            query_total_prev = "SELECT COUNT(*) FROM users WHERE joined_at <= DATETIME('now', '-24 hours')"

            # 2. Usuários Ativos
            query_active_users = "SELECT COUNT(DISTINCT user_id) FROM activity_logs WHERE timestamp > DATETIME('now', '-24 hours')"

            # 3. Erros do Sistema
            query_errors = "SELECT COUNT(*) FROM error_logs WHERE timestamp > DATETIME('now', '-24 hours')"

            # 4. Top 10 Usuários
            query_users = """
                SELECT user_id, COUNT(*) as total
                FROM activity_logs
                WHERE timestamp > DATETIME('now', '-24 hours')
                AND user_id != ?
                GROUP BY user_id
                ORDER BY total DESC
                LIMIT 10
            """
            # 5. Top 10 Ações
            query_actions = """
                SELECT action, COUNT(*) as total
                FROM activity_logs
                WHERE timestamp > DATETIME('now', '-24 hours')
                AND user_id != ?
                GROUP BY action
                ORDER BY total DESC
                LIMIT 10
            """

            async with db.execute(query_new_users) as cursor:
                new_users = (await cursor.fetchone())[0]

            async with db.execute(query_prev_new_users) as cursor:
                prev_new_users = (await cursor.fetchone())[0]

            async with db.execute(query_total_prev) as cursor:
                total_prev = (await cursor.fetchone())[0]

            async with db.execute(query_active_users) as cursor:
                active_users_count = (await cursor.fetchone())[0]

            async with db.execute(query_errors) as cursor:
                errors_count = (await cursor.fetchone())[0]

            # 4. Total de ações (exclui admin)
            query_total_actions = "SELECT COUNT(*) FROM activity_logs WHERE timestamp > DATETIME('now', '-24 hours') AND user_id != ?"
            async with db.execute(query_total_actions, (ADMIN_ID,)) as cursor:
                total_actions_count = (await cursor.fetchone())[0]

            async with db.execute(query_users, (ADMIN_ID,)) as cursor:
                top_users = await cursor.fetchall()

            async with db.execute(query_actions, (ADMIN_ID,)) as cursor:
                top_actions = await cursor.fetchall()

        # Cálculo de Crescimento (Comparação com o Total de Usuários de Ontem)
        if total_prev > 0:
            growth = (new_users / total_prev) * 100
            growth_str = f"+{growth:.1f}%"
        else:
            growth_str = "∞ (Início)" if new_users > 0 else "0%"

        msg = "📊 <b>Relatório Diário - Últimas 24h</b>\n\n"

        msg += "📈 <b>Estatísticas de Crescimento:</b>\n"
        msg += f"- Novos Usuários: <b>{new_users}</b> ({growth_str} vs. {prev_new_users} ontem)\n\n"

        msg += "👥 <b>Engajamento:</b>\n"
        msg += f"- Usuários Ativos (24h): <b>{active_users_count}</b>\n"
        msg += f"- Total de Ações (24h): <b>{total_actions_count}</b>\n"
        msg += "<b>Top 10 Usuários:</b>\n"
        if not top_users:
            msg += "<i>Nenhuma atividade registrada.</i>\n"
        for i, (uid, count) in enumerate(top_users, 1):
            msg += f"{i}. ID:<code>{uid}</code>: <b>{count}</b> ações\n"

        msg += "\n⚡️ <b>Top 10 Ações:</b>\n"
        if not top_actions:
            msg += "<i>Nenhuma ação registrada.</i>\n"
        for i, (action, count) in enumerate(top_actions, 1):
            msg += f"{i}. {action}: <b>{count}</b>\n"

        msg += f"\n🔴 <b>Saúde do Sistema:</b>\n"
        msg += f"- Erros Registrados (24h): <b>{errors_count}</b>"

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=msg,
            parse_mode="HTML",
            reply_markup=get_admin_markup()
        )
        logger.info("Relatório diário enviado com sucesso.")

    except Exception as e:
        logger.error(f"Erro ao gerar/enviar relatório diário: {e}")



async def _resume_notification_task(bot, all_users, status_chat_id, status_message_id):
    """Tarefa em background para notificar usuários sobre a retomada em lotes concorrentes."""
    success_count = 0
    fail_count = 0
    total_users = len(all_users)
    start_time = time.time()
    last_update_time = start_time

    BATCH_SIZE = 20
    BATCH_DELAY = 1.2

    async def _send_resume(uid, lang_code, custom_lang):
        nonlocal success_count, fail_count
        if uid == ADMIN_ID:
            return

        target_lang = custom_lang
        if not target_lang and lang_code:
            target_lang = lang_code.split("-")[0].lower()
        if not target_lang:
            target_lang = "en"

        text = TRANSLATIONS.get(target_lang, {}).get("maintenance_ended")
        if not text:
            text = TRANSLATIONS.get("en", {}).get("maintenance_ended")
        if not text:
            text = "✅ <b>Maintenance ended!</b>"

        try:
            await bot.send_message(chat_id=uid, text=text, parse_mode="HTML")
            success_count += 1
        except Exception:
            fail_count += 1

    for i in range(0, total_users, BATCH_SIZE):
        batch = all_users[i:i + BATCH_SIZE]
        tasks = [_send_resume(uid, lang_code, custom_lang) for uid, lang_code, custom_lang in batch]
        await asyncio.gather(*tasks, return_exceptions=True)

        processed = min(i + len(batch), total_users)
        current_time = time.time()

        # Atualiza o status a cada 5 segundos ou ao concluir
        if current_time - last_update_time >= 5 or processed == total_users:
            elapsed = current_time - start_time
            if processed > 0:
                avg_time = elapsed / processed
                remaining = total_users - processed
                est_seconds = remaining * avg_time
                est_str = _format_timedelta(
                    datetime.timedelta(seconds=int(est_seconds))
                )
                percent = (processed / total_users) * 100

                try:
                    await bot.edit_message_text(
                        chat_id=status_chat_id,
                        message_id=status_message_id,
                        text=f"📢 <b>Notificando usuários (Background)...</b>\n\n"
                        f"✅ Enviados: {success_count}\n"
                        f"❌ Falhas: {fail_count}\n"
                        f"📊 Progresso: {processed}/{total_users} ({percent:.1f}%)\n"
                        f"⏱ Estimativa: {est_str}",
                        parse_mode="HTML",
                    )
                except Exception:
                    pass
            last_update_time = current_time

        if processed < total_users:
            await asyncio.sleep(BATCH_DELAY)

    total_duration = time.time() - start_time
    duration_str = _format_timedelta(datetime.timedelta(seconds=int(total_duration)))

    global LAST_BROADCAST_STATS
    LAST_BROADCAST_STATS = {
        "date": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
        "message": "Aviso de Retomada (Manutenção Encerrada)",
        "success": success_count,
        "failed": fail_count,
        "total": total_users,
        "duration": duration_str,
    }

    await bot.edit_message_text(
        chat_id=status_chat_id,
        message_id=status_message_id,
        text=f"✅ <b>Manutenção encerrada!</b>\n\n"
        f"⏱ Duração: {duration_str}\n"
        f"✅ Notificados: {success_count}\n"
        f"❌ Falhas: {fail_count}",
        parse_mode="HTML",
    )


async def resume_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Retoma o funcionamento do bot (Apenas Admin)."""
    user = update.effective_user
    if user.id != ADMIN_ID:
        return

    global BOT_PAUSED
    if not BOT_PAUSED:
        await update.message.reply_html("⚠️ O bot já está rodando.")
        return

    BOT_PAUSED = False
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute(
            "INSERT OR REPLACE INTO system_config (key, value) VALUES ('paused', '0')"
        )
        # Busca usuários da fila de manutenção para notificar
        async with db.execute("""
            SELECT mq.user_id, u.language_code, u.custom_language
            FROM maintenance_queue mq
            LEFT JOIN users u ON mq.user_id = u.user_id
        """) as cursor:
            target_users = await cursor.fetchall()

        # Limpa a fila
        await db.execute("DELETE FROM maintenance_queue")
        await db.commit()

    await update.message.reply_html("▶️ <b>Bot retomado!</b> O funcionamento voltou ao normal.")
    logger.info(f"Bot retomado por {user.first_name} ({user.id})")

    # Notifica usuários em background
    if target_users:
        status_msg = await update.message.reply_html(
            f"📢 <b>Notificando {len(target_users)} usuários que tentaram interagir...</b>"
        )
        asyncio.create_task(
            _resume_notification_task(
                context.bot, target_users, status_msg.chat_id, status_msg.message_id
            )
        )
    else:
        await update.message.reply_html(
            "ℹ️ <b>Nenhum usuário tentou interagir durante a manutenção.</b>"
        )


async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Bane um usuário por ID ou Username (Apenas Admin)."""
    user = update.effective_user
    if user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_html(
            "⚠️ <b>Uso incorreto.</b>\nExemplo: <code>/banir 123456 Spam</code> ou <code>/banir @usuario Spam</code>",
            reply_markup=get_admin_markup()
        )
        return

    target = context.args[0]
    reason = (
        " ".join(context.args[1:]) if len(context.args) > 1 else "Violação das regras"
    )
    target_id = None

    async with aiosqlite.connect(DB_FILE) as db:
        # Tenta resolver username se começar com @
        if target.startswith("@"):
            username = target[1:]
            # Busca case-insensitive
            async with db.execute(
                "SELECT user_id FROM users WHERE username LIKE ?", (username,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    target_id = row[0]
        elif target.isdigit():
            target_id = int(target)

        if target_id:
            if target_id == ADMIN_ID:
                await update.message.reply_text("❌ Você não pode banir a si mesmo.", reply_markup=get_admin_markup())
                return

            await db.execute(
                "INSERT OR REPLACE INTO banned_users (user_id, reason) VALUES (?, ?)",
                (target_id, reason),
            )
            await db.commit()
            await update.message.reply_html(
                f"🚫 Usuário <code>{target_id}</code> foi <b>banido</b> com sucesso.",
                reply_markup=get_admin_markup()
            )
            logger.info(f"Usuário {target_id} banido por {user.id}. Razão: {reason}")
        else:
            await update.message.reply_html("❌ Usuário não encontrado no banco de dados. Tente usar o ID numérico.", reply_markup=get_admin_markup())


async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove o banimento de um usuário (Apenas Admin)."""
    user = update.effective_user
    if user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text("⚠️ Uso: /desbanir <user_id>")
        return

    target = context.args[0]
    if not target.isdigit():
        await update.message.reply_text(
            "⚠️ Por favor, forneça o ID numérico do usuário."
        )
        return

    target_id = int(target)
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("DELETE FROM banned_users WHERE user_id = ?", (target_id,))
        await db.commit()

    await update.message.reply_html(
        f"✅ Usuário <code>{target_id}</code> foi <b>desbanido</b>.",
        reply_markup=get_admin_markup()
    )


async def set_workers_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Define o número de workers simultâneos (Apenas Admin)."""
    user = update.effective_user
    if user.id != ADMIN_ID:
        return

    global PROCESS_POOL, PROCESSING_SEMAPHORE

    if not context.args:
        current = "1"
        async with aiosqlite.connect(DB_FILE) as db:
            async with db.execute(
                "SELECT value FROM system_config WHERE key = 'max_workers'"
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    current = row[0]
        await update.message.reply_html(
            f"⚙️ <b>Workers atuais:</b> {current}\nUse: <code>/processos [n]</code> para alterar (Ex: <code>/processos 2</code>).",
            reply_markup=get_admin_markup()
        )
        return

    try:
        new_workers = int(context.args[0])
        if new_workers < 1 or new_workers > 8:
            await update.message.reply_html("⚠️ O valor deve ser entre 1 e 8.", reply_markup=get_admin_markup())
            return
    except ValueError:
        await update.message.reply_html("⚠️ Valor inválido.", reply_markup=get_admin_markup())
        return

    # Atualiza DB
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute(
            "INSERT OR REPLACE INTO system_config (key, value) VALUES ('max_workers', ?)",
            (str(new_workers),),
        )
        await db.commit()

    # Atualiza Runtime (Recria o Pool)
    if PROCESS_POOL:
        PROCESS_POOL.shutdown(wait=False)

    PROCESS_POOL = concurrent.futures.ProcessPoolExecutor(max_workers=new_workers)
    PROCESSING_SEMAPHORE = asyncio.Semaphore(new_workers)

    await update.message.reply_html(
        f"✅ <b>Workers atualizados para {new_workers}!</b>\nO bot agora processa até {new_workers} imagens simultaneamente.",
        reply_markup=get_admin_markup()
    )
    logger.info(f"Admin {user.id} alterou max_workers para {new_workers}")


async def cache_usage_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Monitora o uso do cache (Disco e RAM) (Apenas Admin)."""
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return

    cache_dir = "cache"
    total_size = 0
    file_count = 0

    if os.path.exists(cache_dir):
        for f in os.listdir(cache_dir):
            f_path = os.path.join(cache_dir, f)
            if os.path.isfile(f_path):
                total_size += os.path.getsize(f_path)
                file_count += 1

    total_size_mb = total_size / (1024 * 1024)

    # RAM usage
    process = psutil.Process(os.getpid())
    ram_usage_mb = process.memory_info().rss / (1024 * 1024)

    msg = (
        f"📊 <b>Status do Cache</b>\n\n"
        f"📂 <b>Disco:</b> {total_size_mb:.2f} MB ({file_count} arquivos)\n"
        f"🧠 <b>RAM (Processo):</b> {ram_usage_mb:.2f} MB"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Reiniciar bot", callback_data="restart_bot")],
        [InlineKeyboardButton("🗑️ Deletar do chat", callback_data="close_msg")],
    ])
    await update.message.reply_html(msg, reply_markup=keyboard)


async def cache_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Exibe os principais consumidores observáveis de RAM (Apenas Admin)."""
    user = update.effective_user
    if user.id != ADMIN_ID:
        return

    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    children = process.children(recursive=True)
    children_rss = sum(child.memory_info().rss for child in children)

    def size_mb(value: int) -> float:
        return value / (1024 * 1024)

    cache_size = 0
    cache_files = 0
    if os.path.exists("cache"):
        for filename in os.listdir("cache"):
            filepath = os.path.join("cache", filename)
            if os.path.isfile(filepath):
                cache_size += os.path.getsize(filepath)
                cache_files += 1

    pending_logs_size = sum(sys.getsizeof(item) for item in PENDING_LOGS)
    tip_cache_size = sum(
        sys.getsizeof(key) + sys.getsizeof(value)
        for key, value in TIP_IMAGE_CACHE.items()
    )
    user_data_count = sum(
        len(data)
        for data in getattr(context.application, "user_data", {}).values()
        if isinstance(data, dict)
    )

    msg = (
        "🧠 <b>Diagnóstico de RAM</b>\n\n"
        f"📌 <b>Processo principal:</b> {size_mb(memory_info.rss):.2f} MB RSS\n"
        f"📦 <b>Memória virtual:</b> {size_mb(memory_info.vms):.2f} MB VMS\n"
        f"👶 <b>Processos filhos:</b> {len(children)} ({size_mb(children_rss):.2f} MB RSS)\n\n"
        f"🖼️ <b>TIP_IMAGE_CACHE:</b> {len(TIP_IMAGE_CACHE)} itens, ~{size_mb(tip_cache_size):.2f} MB\n"
        f"📝 <b>PENDING_LOGS:</b> {len(PENDING_LOGS)} itens, ~{size_mb(pending_logs_size):.2f} MB\n"
        f"👥 <b>PROCESSING_QUEUE:</b> {len(PROCESSING_QUEUE)} itens\n"
        f"💾 <b>context.user_data:</b> ~{user_data_count} entradas\n"
        f"📂 <b>cache/ em disco:</b> {cache_files} arquivos, {size_mb(cache_size):.2f} MB"
    )
    await update.message.reply_html(msg, reply_markup=get_admin_markup())


async def queue_status_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Exibe o status da fila de processamento (Apenas Admin)."""
    user = update.effective_user
    if user.id != ADMIN_ID:
        return

    if not CURRENT_PROCESSING and not PROCESSING_QUEUE:
        await update.message.reply_html("✅ A fila está vazia.")
        return

    current_txt = (
        f"{CURRENT_PROCESSING[1]} ({CURRENT_PROCESSING[0]})"
        if CURRENT_PROCESSING
        else "N/A"
    )
    count = len(PROCESSING_QUEUE)
    total_time = (count + (1 if CURRENT_PROCESSING else 0)) * ESTIMATED_TIME_PER_JOB

    msg = (
        f"📊 <b>Status da Fila</b>\n\n"
        f"🔄 <b>Processando:</b> {current_txt}\n"
        f"👥 <b>Na fila:</b> {count}\n"
        f"⏱ <b>Tempo total est.:</b> {total_time}s"
    )

    if PROCESSING_QUEUE:
        msg += "\n"
        for i, (uid, name) in enumerate(PROCESSING_QUEUE):
            msg += f"{i + 1}. {html.escape(name)} ({uid})\n"

    await update.message.reply_html(msg, reply_markup=get_admin_markup())


async def list_banned_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Lista todos os usuários banidos (Apenas Admin)."""
    user = update.effective_user
    if user.id != ADMIN_ID:
        return

    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute(
            "SELECT user_id, reason, banned_at FROM banned_users"
        ) as cursor:
            rows = await cursor.fetchall()

    if not rows:
        await update.message.reply_html("✅ Nenhum usuário banido.", reply_markup=get_admin_markup())
        return

    msg = "🚫 <b>Lista de Usuários Banidos:</b>\n\n"
    for row in rows:
        uid, reason, date = row
        msg += f"👤 <code>{uid}</code>\n📅 {date}\n📝 {reason}\n\n"

    await update.message.reply_html(msg, reply_markup=get_admin_markup())


async def clear_cache_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Limpa o cache de arquivos e força a coleta de lixo da RAM (Apenas Admin)."""
    user = update.effective_user
    user_id = user.id
    if user_id != ADMIN_ID:
        return

    msg = await update.message.reply_html("🧹 <b>Iniciando limpeza...</b>")

    # Limpeza de Disco
    cache_dir = "cache"
    deleted_files = 0
    freed_space = 0

    if os.path.exists(cache_dir):
        for f in os.listdir(cache_dir):
            f_path = os.path.join(cache_dir, f)
            try:
                if os.path.isfile(f_path):
                    size = os.path.getsize(f_path)
                    os.remove(f_path)
                    deleted_files += 1
                    freed_space += size
            except Exception as e:
                logger.error(f"Erro ao deletar {f_path}: {e}")

    # Limpeza de RAM (Garbage Collection)
    gc.collect()

    freed_mb = freed_space / (1024 * 1024)

    await msg.edit_text(
        "✅ <b>Limpeza Concluída!</b>\n\n"
        f"🗑️ <b>Disco:</b> {deleted_files} arquivos removidos ({freed_mb:.2f} MB liberados).\n"
        f"🧠 <b>RAM:</b> Garbage Collector executado.",
        parse_mode="HTML",
        reply_markup=get_admin_markup()
    )


async def handle_get_document_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Envia a imagem gerada como documento (sem compressão do Telegram)."""
    query = update.callback_query
    await query.answer()

    filename = query.data.split(":", 1)[1]
    # Segurança básica de path traversal
    filename = os.path.basename(filename)
    filepath = os.path.join("cache", filename)

    # Proteção IDOR: Verifica se o arquivo pertence ao usuário
    if not filename.startswith(f"merged_{query.from_user.id}_"):
        await query.message.reply_text(get_text(user, context, "err_access_denied"))
        return

    if os.path.exists(filepath):
        # Notifica admin sobre a ação
        await register_interaction(
            query.from_user, context, f"Baixou arquivo sem compactação: {filename}"
        )

        await query.message.reply_document(
            document=open(filepath, "rb"),
            caption=get_text(
                query.from_user, context, "success_caption", direction="file"
            ),
        )
    else:
        # Se o arquivo já foi limpo pelo cleanup
        await query.message.reply_text(
            get_text(query.from_user, context, "file_expired")
        )


def _convert_to_pdf_task(image_bytes: bytes) -> bytes:
    """Converte bytes de imagem para bytes de PDF (executado em processo separado)."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
    except Image.DecompressionBombError as e:
        logger.error(f"Ataque de Decompression Bomb detectado em _convert_to_pdf_task: {e}")
        raise ValueError(
            "A imagem é uma 'bomba de descompressão' e não pode ser processada."
        ) from e
    # PDF não suporta transparência nativa da mesma forma que PNG, converter para RGB
    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")

    output = io.BytesIO()
    img.save(output, format="PDF", resolution=300.0, quality=100)
    return output.getvalue()


async def handle_get_pdf_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Converte a imagem em cache para PDF e envia."""
    query = update.callback_query
    await query.answer()

    filename = query.data.split(":", 1)[1]
    filename = os.path.basename(filename)  # Segurança
    filepath = os.path.join("cache", filename)

    # Proteção IDOR: Verifica se o arquivo pertence ao usuário
    if not filename.startswith(f"merged_{query.from_user.id}_"):
        await query.message.reply_text(get_text(user, context, "err_access_denied"))
        return

    if os.path.exists(filepath):
        # Notifica admin sobre a ação
        await register_interaction(query.from_user, context, f"Baixou PDF: {filename}")

        await query.message.reply_chat_action("upload_document")

        # Lê o arquivo do disco
        with open(filepath, "rb") as f:
            file_bytes = f.read()

        # Processa a conversão em outro processo para não bloquear o loop
        loop = asyncio.get_running_loop()
        try:
            pdf_bytes = await loop.run_in_executor(
                PROCESS_POOL, _convert_to_pdf_task, file_bytes
            )

            pdf_filename = os.path.splitext(filename)[0] + ".pdf"
            await query.message.reply_document(
                document=io.BytesIO(pdf_bytes),
                filename=pdf_filename,
                caption=get_text(query.from_user, context, "pdf_btn"),
            )
        except Exception as e:
            logger.error(f"Erro na conversão PDF: {e}")
            await query.message.reply_text(
                get_text(query.from_user, context, "pdf_error")
            )
    else:
        await query.message.reply_text(
            get_text(query.from_user, context, "file_expired")
        )


def _create_zip_task(file_path: str, filename_inside: str) -> bytes:
    """Cria um arquivo ZIP contendo o arquivo especificado."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(file_path, arcname=filename_inside)
    return buffer.getvalue()


async def handle_get_zip_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Compacta a imagem em cache em um ZIP e envia."""
    query = update.callback_query
    await query.answer()

    filename = query.data.split(":", 1)[1]
    filename = os.path.basename(filename)
    filepath = os.path.join("cache", filename)

    # Proteção IDOR: Verifica se o arquivo pertence ao usuário
    if not filename.startswith(f"merged_{query.from_user.id}_"):
        await query.message.reply_text(get_text(user, context, "err_access_denied"))
        return

    if os.path.exists(filepath):
        await register_interaction(query.from_user, context, f"Baixou ZIP: {filename}")
        await query.message.reply_chat_action("upload_document")

        loop = asyncio.get_running_loop()
        try:
            zip_bytes = await loop.run_in_executor(
                PROCESS_POOL, _create_zip_task, filepath, filename
            )

            zip_filename = os.path.splitext(filename)[0] + ".zip"
            await query.message.reply_document(
                document=io.BytesIO(zip_bytes),
                filename=zip_filename,
                caption=get_text(query.from_user, context, "zip_caption"),
            )
        except Exception as e:
            logger.error(f"Erro na criação do ZIP: {e}")
            await query.message.reply_text(
                get_text(query.from_user, context, "zip_error")
            )
    else:
        await query.message.reply_text(
            get_text(query.from_user, context, "file_expired")
        )


async def cleanup_old_images(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove imagens antigas do banco de dados (mais de 24h) para liberar espaço."""
    try:
        async with aiosqlite.connect(DB_FILE) as db:
            # SQLite datetime('now') retorna UTC. Removemos registros mais velhos que 1 dia.
            cursor = await db.execute(
                "DELETE FROM user_images WHERE received_at < datetime('now', '-1 day')"
            )
            # Limpa registros de regeneração órfãos (usuários inativos há mais de 24h)
            cursor_merge = await db.execute(
                "DELETE FROM last_merge_files WHERE user_id IN (SELECT user_id FROM users WHERE last_interaction < datetime('now', '-1 day'))"
            )
            cursor_pdf = await db.execute(
                "DELETE FROM user_pdfs WHERE received_at < datetime('now', '-1 day')"
            )
            await db.commit()
            if cursor.rowcount > 0:
                logger.info(
                    f"Limpeza automática: {cursor.rowcount} imagens antigas removidas."
                )
            if cursor_merge.rowcount > 0:
                logger.info(
                    f"Limpeza automática: {cursor_merge.rowcount} registros de regeneração removidos."
                )

        # Limpeza da pasta cache (arquivos > 20 minutos)
        cache_dir = "cache"
        deleted_files = 0
        if os.path.exists(cache_dir):
            now = time.time()
            for f in os.listdir(cache_dir):
                f_path = os.path.join(cache_dir, f)
                if os.path.isfile(f_path) and now - os.path.getmtime(f_path) > 1200:
                    try:
                        os.remove(f_path)
                        deleted_files += 1
                    except Exception:
                        pass
        if deleted_files > 0:
            logger.info(f"Limpeza de cache: {deleted_files} arquivos removidos.")

        # Limpeza de RAM: Remove entradas antigas do rate limit (mais de 1 hora)
        current_ts = time.time()
        expired_usage = [
            uid for uid, ts in LAST_MERGE_USAGE.items() if current_ts - ts > 3600
        ]
        for uid in expired_usage:
            del LAST_MERGE_USAGE[uid]
        if expired_usage:
            logger.info(
                f"Limpeza de RAM: {len(expired_usage)} registros de rate limit removidos."
            )

    except Exception as e:
        logger.error(f"Erro na limpeza automática de imagens: {e}")


async def cleanup_old_logs(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove logs de atividade antigos (mais de 40 dias)."""
    try:
        async with aiosqlite.connect(DB_FILE) as db:
            cursor = await db.execute(
                "DELETE FROM activity_logs WHERE timestamp < datetime('now', '-40 days')"
            )
            await db.commit()
            if cursor.rowcount > 0:
                logger.info(
                    f"Limpeza de logs: {cursor.rowcount} registros antigos removidos."
                )
    except Exception as e:
        logger.error(f"Erro na limpeza de logs antigos: {e}")








async def _clean_blocked_users_task(bot, users, status_chat_id, status_message_id):
    """Tarefa em background para limpar usuários bloqueados."""
    removed_count = 0
    total_users = len(users)
    start_time = time.time()

    # Rate Limit configuration
    BATCH_SIZE = 20
    BATCH_DELAY = 1.5

    for i, (uid, name) in enumerate(users):
        # Pula o admin
        if uid == ADMIN_ID:
            continue

        try:
            # Tenta enviar uma ação de chat. Se bloqueado, gera Forbidden.
            await bot.send_chat_action(chat_id=uid, action="typing")
        except Forbidden:
            # Usuário bloqueou o bot
            async with aiosqlite.connect(DB_FILE) as db:
                await db.execute("DELETE FROM users WHERE user_id = ?", (uid,))
                await db.commit()
            removed_count += 1
            logger.info(f"Usuário removido (Bloqueou o bot): {uid} - {name}")
        except Exception:
            # Ignora outros erros (ex: chat não encontrado, erro de rede temporário)
            pass

        # Rate limiting e atualização de status
        if (i + 1) % BATCH_SIZE == 0:
            await asyncio.sleep(BATCH_DELAY)
            if status_chat_id and status_message_id:
                try:
                    elapsed_time = time.time() - start_time
                    elapsed_mins = int(elapsed_time // 60)
                    elapsed_secs = int(elapsed_time % 60)

                    time_per_user = elapsed_time / (i + 1)
                    remain_time = time_per_user * (total_users - (i + 1))
                    remain_mins = int(remain_time // 60)
                    remain_secs = int(remain_time % 60)

                    await bot.edit_message_text(
                        chat_id=status_chat_id,
                        message_id=status_message_id,
                        text=(
                            f"🧹 <b>Verificando (Background)...</b>\n"
                            f"Progresso: {i + 1}/{total_users}\n"
                            f"Removidos: {removed_count}\n"
                            f"⏱️ Tempo Percorrido: {elapsed_mins:02d}:{elapsed_secs:02d}\n"
                            f"⏳ Tempo Restante: {remain_mins:02d}:{remain_secs:02d}"
                        ),
                        parse_mode="HTML",
                    )
                except Exception as e:
                    logger.debug(f"Erro ao atualizar status da limpeza: {e}")
        else:
            await asyncio.sleep(0.05)

    elapsed_time = time.time() - start_time
    elapsed_mins = int(elapsed_time // 60)
    elapsed_secs = int(elapsed_time % 60)

    if status_chat_id and status_message_id:
        try:
            await bot.edit_message_text(
                chat_id=status_chat_id,
                message_id=status_message_id,
                text=(
                    f"✅ <b>Limpeza Concluída!</b>\n\n"
                    f"👥 Total verificado: {total_users}\n"
                    f"🚫 Removidos: {removed_count}\n"
                    f"⏱️ Tempo Total: {elapsed_mins:02d}:{elapsed_secs:02d}"
                ),
                parse_mode="HTML",
                reply_markup=get_admin_markup()
            )
        except Exception as e:
            logger.error(f"Erro ao atualizar mensagem final de limpeza: {e}")


async def scheduled_clean_blocked_users_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Executa a limpeza automática de usuários bloqueados todo domingo às 03:00 (Horário de Brasília)."""
    logger.info("Iniciando limpeza semanal automática de usuários bloqueados...")
    status_chat_id = None
    status_message_id = None

    if ADMIN_ID:
        try:
            status_msg = await context.bot.send_message(
                chat_id=ADMIN_ID,
                text="🧹 <b>Iniciando limpeza semanal automática de usuários bloqueados (Agendada)...</b>",
                parse_mode="HTML",
                reply_markup=get_admin_markup(),
            )
            status_chat_id = status_msg.chat_id
            status_message_id = status_msg.message_id
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem inicial de limpeza agendada: {e}")

    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT user_id, first_name FROM users") as cursor:
            users = await cursor.fetchall()

    await _clean_blocked_users_task(
        context.bot, users, status_chat_id, status_message_id
    )


async def clean_blocked_users_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Verifica e remove usuários que bloquearam o bot (Apenas Admin)."""
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return

    status_msg = await update.effective_message.reply_html(
        "🧹 <b>Iniciando verificação de usuários bloqueados em segundo plano...</b>",
        reply_markup=get_admin_markup()
    )

    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT user_id, first_name FROM users") as cursor:
            users = await cursor.fetchall()

    asyncio.create_task(
        _clean_blocked_users_task(
            context.bot, users, status_msg.chat_id, status_msg.message_id
        )
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Loga o erro e notifica o usuário e o admin."""

    # Salva o erro no banco de dados
    try:
        user_id = (
            update.effective_user.id
            if isinstance(update, Update) and update.effective_user
            else None
        )
        username = (
            update.effective_user.username
            if isinstance(update, Update) and update.effective_user
            else None
        )
        tb_str = "".join(
            traceback.format_exception(None, context.error, context.error.__traceback__)
        )

        # Filtra erros técnicos específicos para não poluir o banco de dados
        error_msg = str(context.error)
        ignore_list = [
            "Conflict: terminated by other getUpdates request",
            "httpx.ReadError",
            "httpx.ConnectError",
            "Timed out",
            "Query is too old and response timeout expired or query id is invalid"
        ]

        should_ignore = any(ignore in error_msg for ignore in ignore_list)

        if not should_ignore:
            async with aiosqlite.connect(DB_FILE) as db:
                await db.execute(
                    "INSERT INTO error_logs (user_id, username, error_message, traceback) VALUES (?, ?, ?, ?)",
                    (user_id, username, error_msg, tb_str),
                )
                await db.commit()
    except Exception as e:
        logger.error(f"Erro ao salvar log de erro no DB: {e}")

    # Se for erro de rede, apenas avisa no log sem traceback completo e retorna
    if isinstance(context.error, NetworkError):
        logger.warning(f"⚠️ Erro de Conexão (NetworkError): {context.error}")
        return

    logger.error("Exceção ao lidar com update:", exc_info=context.error)

    # Tratamento específico para Conflito (Duas instâncias) e Erros de Rede
    if isinstance(context.error, Conflict):
        logger.critical(
            get_text(None, None, "err_conflict") # get_text handles None user/context
        )
        if isinstance(update, Update) and update.effective_message:
            try:
                await update.effective_message.reply_html(
                    get_text(update.effective_user, context, "conflict_error")
                )
            except Exception:
                pass
        return

    # Tratamento para Query Expirada (Botão antigo)
    if "Query is too old" in error_msg:
        if isinstance(update, Update) and update.effective_message:
            try:
                await update.effective_message.reply_html(
                    get_text(update.effective_user, context, "err_query_too_old")
                )
            except Exception:
                pass
        return

    # Notifica o usuário
    if isinstance(update, Update) and update.effective_message:
        user_msg = get_text(update.effective_user, context, "unexpected_error")
        try:
            await update.effective_message.reply_html(user_msg)
        except Exception:
            # Se não conseguir enviar mensagem para o usuário (ex: bloqueou o bot), apenas ignora
            pass

    # Notifica o admin
    if ADMIN_ID and not should_ignore:
        try:
            # Formata o traceback
            tb_list = traceback.format_exception(
                None, context.error, context.error.__traceback__
            )
            tb_string = "".join(tb_list)

            user_info = "identidade omitida"
            action = "N/A"

            if isinstance(update, Update):
                if update.effective_message:
                    if update.effective_message.photo or update.effective_message.document:
                        action = "Envio de mídia"
                    elif update.effective_message.text or update.effective_message.caption:
                        action = "Mensagem textual"
                elif update.callback_query:
                    action = "Interação com botão"

            message = (
                "🚨 <b>ERRO DETECTADO</b>\n\n"
                f"<b>Ação:</b> {html.escape(action)}\n"
                f"<b>Erro técnico:</b> {html.escape(str(context.error))}"
            )

            await context.bot.send_message(
                chat_id=ADMIN_ID, text=message, parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Falha ao notificar admin sobre erro: {e}")


async def support_reminder_task(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envia uma única mensagem de apoio após 7 dias ou ao atingir a cota."""
    try:
        async with aiosqlite.connect(DB_FILE) as db:
            query = """
                SELECT user_id, COALESCE(custom_language, language_code), images_since_last_ad
                FROM users
                WHERE support_reminder_sent = 0
                  AND user_id != ?
                  AND date(joined_at) <= date('now', '-7 days')
            """
            async with db.execute(query, (ADMIN_ID, AD_THRESHOLD)) as cursor:
                eligible_users = await cursor.fetchall()

        sent_count = 0
        for user_id, lang, images_since_last_ad in eligible_users:
            try:
                lang = lang or "pt"
                msg = get_text_by_lang(lang, "weekly_ad_reminder_msg")
                btn_text = get_text_by_lang(lang, "btn_free_ad")
                keyboard = [[InlineKeyboardButton(
                    btn_text,
                    web_app=WebAppInfo(url=get_miniapp_ad_url(lang, "voluntary")),
                )]]
                await context.bot.send_message(
                    chat_id=user_id,
                    text=msg,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="HTML",
                )
                async with aiosqlite.connect(DB_FILE) as db2:
                    await db2.execute(
                        "UPDATE users SET support_reminder_sent = 1 WHERE user_id = ?",
                        (user_id,),
                    )
                    await db2.commit()
                sent_count += 1
                await asyncio.sleep(0.05)
            except Exception as e:
                logger.debug(f"Não foi possível enviar lembrete de apoio para {user_id}: {e}")

        if sent_count and ADMIN_ID:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"🔔 Lembrete de apoio enviado a {sent_count} usuário(s).",
            )
    except Exception as e:
        logger.error(f"Erro no support_reminder_task: {e}", exc_info=True)


async def check_promo_task(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Verifica e envia mensagem promocional para usuários após 24h."""
    try:
        async with aiosqlite.connect(DB_FILE) as db:
            # Failsafe: Garante colunas (Runtime Migration)
            async with db.execute("PRAGMA table_info(users)") as cursor:
                columns = [row[1] for row in await cursor.fetchall()]
            if "joined_at" not in columns:
                await db.execute("ALTER TABLE users ADD COLUMN joined_at TIMESTAMP")
                await db.execute(
                    "UPDATE users SET joined_at = CURRENT_TIMESTAMP WHERE joined_at IS NULL"
                )
                await db.commit()
            if "promo_sent" not in columns:
                await db.execute(
                    "ALTER TABLE users ADD COLUMN promo_sent INTEGER DEFAULT 0"
                )
                await db.commit()

            # Seleciona usuários elegíveis: joined_at < 24h atrás E promo_sent = 0
            # joined_at pode ser NULL para usuários muito antigos se a migração falhar em setar default,
            # mas definimos DEFAULT CURRENT_TIMESTAMP na migração, então eles terão data de "hoje" e receberão amanhã.
            query = """
                SELECT user_id, first_name, username, COALESCE(custom_language, language_code, 'en') as lang
                FROM users
                WHERE promo_sent = 0
                AND joined_at <= datetime('now', '-1 day')
                LIMIT 50
            """
            async with db.execute(query) as cursor:
                users = await cursor.fetchall()

        if not users:
            return

        for uid, first_name, username, lang in users:
            try:
                # Cria um objeto User fake para aproveitar a lógica do get_text
                fake_user = User(
                    id=uid,
                    first_name=first_name or "User",
                    is_bot=False,
                    username=username,
                    language_code=lang,
                )
                msg = get_text(fake_user, None, "promo_everydaycrypto")

                await context.bot.send_message(chat_id=uid, text=msg)

                # Marca como enviado
                async with aiosqlite.connect(DB_FILE) as db:
                    await db.execute(
                        "UPDATE users SET promo_sent = 1 WHERE user_id = ?", (uid,)
                    )
                    await db.commit()

                # Notifica o Admin
                if ADMIN_ID:
                    try:
                        safe_name = html.escape(first_name or "User")
                        username_display = f"@{html.escape(username)}" if username else "N/A"
                        await context.bot.send_message(
                            chat_id=ADMIN_ID,
                            text=f"📢 <b>Mensagem de divulgação do EverydayCrypto enviada:</b> {safe_name} | {username_display} | <code>{uid}</code> | 🌐 {lang}",
                            parse_mode="HTML",
                        )
                    except Exception as e:
                        logger.error(
                            f"Falha ao notificar admin sobre envio de promo para {uid}: {e}"
                        )

                await asyncio.sleep(0.5)  # Evita flood limits
            except (Forbidden, BadRequest) as e:
                # Se o usuário bloqueou o bot ou a conta foi desativada, marca como enviado para não travar a fila
                async with aiosqlite.connect(DB_FILE) as db:
                    await db.execute(
                        "UPDATE users SET promo_sent = 1 WHERE user_id = ?", (uid,)
                    )
                    await db.commit()
                logger.warning(f"Usuário bloqueou ou inválido para promo {uid}: {e}")
            except Exception as e:
                # Para erros temporários/transientes, não marca como enviado para tentar novamente no próximo ciclo
                logger.error(f"Erro temporário ao enviar promo para {uid}: {e}")

    except Exception as e:
        logger.error(f"Erro na tarefa de promo: {e}")


async def check_martiancat_promo_task(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Verifica e envia mensagem promocional do MartianCat para usuários após 7 dias de cadastro."""
    try:
        async with aiosqlite.connect(DB_FILE) as db:
            # Failsafe: Garante colunas (Runtime Migration)
            async with db.execute("PRAGMA table_info(users)") as cursor:
                columns = [row[1] for row in await cursor.fetchall()]
            if "promo_martiancat_sent" not in columns:
                await db.execute(
                    "ALTER TABLE users ADD COLUMN promo_martiancat_sent INTEGER DEFAULT 0"
                )
                await db.commit()

            # Seleciona usuários elegíveis: joined_at <= 7 dias atrás E promo_martiancat_sent = 0
            query = """
                SELECT user_id, first_name, username, COALESCE(custom_language, language_code, 'en') as lang
                FROM users
                WHERE promo_martiancat_sent = 0
                AND joined_at <= datetime('now', '-7 days')
                LIMIT 50
            """
            async with db.execute(query) as cursor:
                users = await cursor.fetchall()

        if not users:
            return

        for uid, first_name, username, lang in users:
            try:
                fake_user = User(
                    id=uid,
                    first_name=first_name or "User",
                    is_bot=False,
                    username=username,
                    language_code=lang,
                )
                msg = get_text(fake_user, None, "promo_martiancat")
                btn_text = get_text(fake_user, None, "btn_martiancat")
                keyboard = [
                    [
                        InlineKeyboardButton(
                            btn_text,
                            url="https://martiancat.space",
                        )
                    ]
                ]

                await context.bot.send_message(
                    chat_id=uid,
                    text=msg,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="HTML",
                )

                # Marca como enviado
                async with aiosqlite.connect(DB_FILE) as db:
                    await db.execute(
                        "UPDATE users SET promo_martiancat_sent = 1 WHERE user_id = ?", (uid,)
                    )
                    await db.commit()

                # Notifica o Admin
                if ADMIN_ID:
                    try:
                        safe_name = html.escape(first_name or "User")
                        username_display = f"@{html.escape(username)}" if username else "N/A"
                        await context.bot.send_message(
                            chat_id=ADMIN_ID,
                            text=f"📢 <b>Mensagem de divulgação do MartianCat enviada:</b> {safe_name} | {username_display} | <code>{uid}</code> | 🌐 {lang}",
                            parse_mode="HTML",
                        )
                    except Exception as e:
                        logger.error(
                            f"Falha ao notificar admin sobre envio de promo MartianCat para {uid}: {e}"
                        )

                await asyncio.sleep(0.5)  # Evita flood limits
            except (Forbidden, BadRequest) as e:
                # Se o usuário bloqueou o bot ou a conta foi desativada, marca como enviado para não travar a fila
                async with aiosqlite.connect(DB_FILE) as db:
                    await db.execute(
                        "UPDATE users SET promo_martiancat_sent = 1 WHERE user_id = ?", (uid,)
                    )
                    await db.commit()
                logger.warning(f"Usuário bloqueou ou inválido para promo MartianCat {uid}: {e}")
            except Exception as e:
                # Para erros temporários/transientes, não marca como enviado para tentar novamente no próximo ciclo
                logger.error(f"Erro temporário ao enviar promo MartianCat para {uid}: {e}")

    except Exception as e:
        logger.error(f"Erro na tarefa de promo MartianCat: {e}")



# --- SISTEMA DE CONTRIBUIÇÕES (AJUDÔMETRO) ---

@base_handler_checks
async def contribute_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Exibe o menu de doações globais."""
    user = update.effective_user
    await register_interaction(user, context, "Abriu menu de contribuição")

    keyboard = [
        [
            InlineKeyboardButton(get_text(user, context, "btn_stars_50"), callback_data="contribute:stars:50"),
            InlineKeyboardButton(get_text(user, context, "btn_stars_250"), callback_data="contribute:stars:250"),
        ],
        [
            InlineKeyboardButton(get_text(user, context, "btn_stars_500"), callback_data="contribute:stars:500"),
            InlineKeyboardButton(get_text(user, context, "btn_crypto"), callback_data="contribute:crypto"),
        ],
        [
            InlineKeyboardButton(get_text(user, context, "btn_free_ad"), web_app=WebAppInfo(url=get_miniapp_ad_url(context.user_data.get("custom_language") or user.language_code, "voluntary"))),
            InlineKeyboardButton(get_text(user, context, "btn_ton_usdt"), callback_data="contribute:ton_shop"),
        ],
        [
            InlineKeyboardButton(get_text(user, context, "btn_ajudometro"), callback_data="contribute:ajudometro"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    msg = get_text(user, context, "contribute_msg")

    # Adiciona barra de progresso se houver meta
    goal_stats = await get_monthly_goal_stats()
    if goal_stats["goal"] > 0:
        msg += "\n" + get_text(
            user, context, "monthly_goal_progresso",
            bar=goal_stats["bar"],
            percent=goal_stats["percent"],
            current=goal_stats["current"],
            goal=goal_stats["goal"]
        )

    # We should reply_html and if possible answer the callback query or reply straight
    if update.message:
        await update.message.reply_html(msg, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.reply_html(msg, reply_markup=reply_markup)

async def handle_contribute_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lida com as opções do menu de contribuição."""
    query = update.callback_query
    user = query.from_user
    try:
        data = query.data.split(":")
        logger.info(f"Callback de contribuição recebido: {query.data} do user {user.id}")

        if len(data) < 2:
            await query.answer("Erro nos dados do callback.")
            return

        action = data[1]

        if action == "stars":
            amount = int(data[2])
            title = get_text(user, context, "payment_invoice_title")
            description = get_text(user, context, "payment_invoice_desc")
            payload = f"donation_{user.id}_{amount}"
            currency = "XTR"
            price = 1
            prices = [LabeledPrice(title, amount * price)]

            try:
                await context.bot.send_invoice(
                    chat_id=query.message.chat_id,
                    title=title,
                    description=description,
                    payload=payload,
                    provider_token="", # Vazio para Telegram Stars
                    currency=currency,
                    prices=prices,
                )
                await query.answer()
            except Exception as e:
                logger.error(f"Erro ao enviar fatura de Stars: {e}")
                await query.answer()

        elif action == "crypto":
            await query.answer()
            back_keyboard = [[InlineKeyboardButton(get_text(user=user, context=context, key="btn_back"), callback_data="contribute:menu")]]
            reply_markup = InlineKeyboardMarkup(back_keyboard)

            # Edita a mensagem atual em vez de enviar uma nova, para manter o histórico limpo
            await query.edit_message_text(
                text=get_text(user=user, context=context, key="crypto_msg"),
                reply_markup=reply_markup,
                parse_mode="HTML"
            )

        elif action == "ton_shop":
            await query.answer()
            if not TON_WALLET_ADDRESS or not TONCENTER_API_KEY or not TON_USDT_MASTER:
                await query.edit_message_text(
                    text=get_text(user=user, context=context, key="ton_payment_unavailable"),
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(get_text(user=user, context=context, key="btn_back"), callback_data="contribute:menu")
                    ]]),
                    parse_mode="HTML",
                )
                return

            keyboard = []
            for amount_usdt, stars_equivalent in TON_USDT_PACKAGES:
                key = "ton_donation_1" if amount_usdt == 1.0 else "ton_donation_5" if amount_usdt == 5.0 else "ton_donation_10"
                keyboard.append([
                    InlineKeyboardButton(
                        get_text(
                            user,
                            context,
                            key,
                            amount=f"{amount_usdt:.2f}",
                            stars=stars_equivalent,
                        ),
                        callback_data=f"contribute:ton_pack:{amount_usdt:.2f}:{stars_equivalent}",
                    )
                ])
            keyboard.append([
                InlineKeyboardButton(get_text(user=user, context=context, key="btn_back"), callback_data="contribute:menu")
            ])
            await query.edit_message_text(
                text=get_text(user, context, "ton_shop_menu"),
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML",
            )

        elif action == "ton_pack":
            if len(data) < 4:
                await query.answer("Erro nos dados do callback.")
                return

            if not TON_WALLET_ADDRESS or not TONCENTER_API_KEY or not TON_USDT_MASTER:
                await query.answer(get_text(user=user, context=context, key="ton_payment_unavailable"), show_alert=True)
                return

            try:
                amount_usdt = float(data[2])
                stars_equivalent = int(data[3])
            except ValueError:
                await query.answer("Valor inválido.")
                return

            await query.answer()
            deposit_id = "UI-" + uuid.uuid4().hex[:8].upper()
            expires_at = datetime.datetime.now() + datetime.timedelta(hours=2)
            expires_str = expires_at.strftime("%H:%M")

            ok = await create_ton_deposit(deposit_id, user.id, amount_usdt, stars_equivalent)
            if not ok:
                await query.edit_message_text(
                    text=get_text(user=user, context=context, key="ton_payment_error"),
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(get_text(user=user, context=context, key="btn_back"), callback_data="contribute:ton_shop")
                    ]]),
                    parse_mode="HTML",
                )
                return

            await query.edit_message_text(
                text=get_text(
                    user,
                    context,
                    "ton_payment_text",
                    amount=f"{amount_usdt:.2f}",
                    stars=stars_equivalent,
                    address=TON_WALLET_ADDRESS,
                    code=deposit_id,
                    expires=expires_str,
                ),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(get_text(user=user, context=context, key="btn_back"), callback_data="contribute:ton_shop")
                ]]),
                parse_mode="HTML",
            )

        elif action == "menu":
            await query.answer()
            await contribute_command(update, context)

        elif action == "ajudometro":
            await query.answer()
            await top_donors_command(update, context, send_new_msg=False)

    except Exception as e:
        logger.error(f"Erro no handle_contribute_callback: {e}")
        await query.answer("Ocorreu um erro ao processar sua ação.")

async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responde à query de pre-checkout para doações."""
    query = update.pre_checkout_query
    if query.invoice_payload.startswith("donation_"):
        await query.answer(ok=True)
    else:
        await query.answer(ok=False, error_message="Something went wrong...")

async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Processa o pagamento concluído e atualiza o banco de dados."""
    user = update.effective_user
    payment = update.message.successful_payment
    amount = payment.total_amount

    # Atualiza o status de doador no DB
    try:
        async with aiosqlite.connect(DB_FILE) as db:
            await db.execute(
                "UPDATE users SET total_donated_stars = total_donated_stars + ?, premium_until = ? WHERE user_id = ?",
                (amount, (datetime.datetime.now() + datetime.timedelta(days=180)).isoformat(), user.id)
            )
            await db.execute(
                "INSERT INTO donation_history (user_id, amount_stars, currency) VALUES (?, ?, ?)",
                (user.id, amount, 'stars')
            )

            async with db.execute("SELECT total_donated_stars, total_voluntary_ads FROM users WHERE user_id = ?", (user.id,)) as cursor:
                row = await cursor.fetchone()
            if row:
                stars, voluntary_ads = row
                total = (stars or 0) + ((voluntary_ads or 0) / 5.0)
                status = "🌟 Iniciante"
                if total >= 1000:
                    status = "👑 Lenda"
                elif total >= 500:
                    status = "💎 Ouro"
                elif total >= 250:
                    status = "🥈 Prata"
                elif total >= 50:
                    status = "🥉 Bronze"

                await db.execute("UPDATE users SET donor_status = ? WHERE user_id = ?", (status, user.id))
            await db.commit()

            # Verifica meta mensal
            asyncio.create_task(check_and_notify_goal_reached(context))
    except Exception as e:
        logger.error(f"Erro ao salvar pagamento do user {user.id}: {e}")

    await update.message.reply_html(
        get_text(user, context, "payment_success", amount=amount)
    )

    # Notifica o ADMIN
    if ADMIN_ID:
        try:
            admin_msg = (
                "💰 <b>Nova doação recebida!</b>\n\n"
                f"⭐️ <b>Quantidade:</b> {amount} Stars\n"
                f"📅 <b>Data:</b> {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
            )
            await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Falha ao notificar admin sobre doação de {user.id}: {e}")

@base_handler_checks
async def top_donors_command(update: Update, context: ContextTypes.DEFAULT_TYPE, send_new_msg: bool = True) -> None:
    """Exibe o Ajudômetro (Ranking global de doadores)."""
    user = update.effective_user
    await register_interaction(user, context, "Visualizou o Ajudômetro")

    try:
        async with aiosqlite.connect(DB_FILE) as db:
            # 1. Ranking Global Top 10 (Filtrando Admin)
            async with db.execute(
                """SELECT first_name, username,
                          (total_donated_stars + (total_voluntary_ads / 5.0)) AS total_score,
                          donor_status
                   FROM users
                   WHERE (total_donated_stars > 0 OR total_voluntary_ads > 0) AND user_id != ?
                   ORDER BY total_score DESC, total_donated_stars DESC LIMIT 10""",
                (ADMIN_ID,)
            ) as cursor:
                rows = await cursor.fetchall()

            # 2. Ranking Mensal Top 10 (Filtrando Admin e Mês Atual)
            async with db.execute(
                """SELECT u.first_name, u.username, SUM(dh.amount_stars) as monthly_total
                   FROM donation_history dh
                   JOIN users u ON dh.user_id = u.user_id
                   WHERE dh.timestamp >= date('now', 'start of month') AND u.user_id != ?
                   GROUP BY dh.user_id
                   ORDER BY monthly_total DESC LIMIT 10""",
                (ADMIN_ID,)
            ) as cursor:
                monthly_rows = await cursor.fetchall()

            # 3. Estatísticas do Usuário Atual (Rank e Percentil) - Excluindo Admin
            async with db.execute("SELECT COUNT(*) FROM users WHERE user_id != ?", (ADMIN_ID,)) as cursor:
                total_users = (await cursor.fetchone())[0]

            # Pegamos as estrelas do usuário atual (incluindo ads virtuais)
            async with db.execute(
                "SELECT total_donated_stars, total_voluntary_ads FROM users WHERE user_id = ?", (user.id,)
            ) as cursor:
                user_row = await cursor.fetchone()
                user_stars = (user_row[0] or 0) + ((user_row[1] or 0) / 5.0) if user_row else 0.0

            async with db.execute(
                "SELECT COUNT(*) FROM users WHERE (total_donated_stars + (total_voluntary_ads / 5.0)) > ? AND user_id != ?", (user_stars, ADMIN_ID)
            ) as cursor:
                higher_donors = (await cursor.fetchone())[0]
                user_rank = higher_donors + 1

            # Percentil: Se sou #1 de 3, sou melhor que (3-1)/3 = 66.7%
            percentile = 0
            if total_users > 0:
                percentile = round(((total_users - user_rank) / total_users) * 100, 1)

        # Monta rankings
        ranking_text = ""
        if rows:
            for i, row in enumerate(rows, 1):
                name = html.escape(row[0] or "User")
                score = row[2]
                status = get_donor_status_display(score=score, raw_status=row[3], user=user, context=context)
                score_str = f"{score:.1f}" if score % 1 != 0 else f"{int(score)}"
                medal = "🏅"
                if i == 1: medal = "🥇"
                elif i == 2: medal = "🥈"
                elif i == 3: medal = "🥉"
                ranking_text += f"{medal} #<b>{i}</b> {name} - {status} ({score_str} ⭐️)\n"

        monthly_ranking_text = ""
        if monthly_rows:
            for i, row in enumerate(monthly_rows, 1):
                name = html.escape(row[0] or "User")
                stars = row[2]
                stars_str = f"{stars:.1f}" if stars % 1 != 0 else f"{int(stars)}"
                medal = "🏅"
                if i == 1: medal = "🥇"
                elif i == 2: medal = "🥈"
                elif i == 3: medal = "🥉"
                monthly_ranking_text += f"{medal} #<b>{i}</b> {name} ({stars_str} ⭐️)\n"

        now = datetime.datetime.now()
        month_name = get_text(user, context, f"month_{now.month}")
        current_month_year = f"{month_name} {now.year}"

        msg = get_text(user, context, "ajudometro_msg", ranking=ranking_text or "---")
        msg += "\n\n" + get_text(user, context, "ajudometro_monthly_title", month=current_month_year)
        msg += "\n" + (monthly_ranking_text or "ℹ️ " + get_text(user, context, "ajudometro_empty"))

        if user.id != ADMIN_ID:
            if user_stars > 0:
                msg += get_text(user, context, "rank_stats", rank=user_rank, total=total_users, percent=percentile)
            else:
                msg += "\n\n" + get_text(user, context, "ajudometro_no_stars")

        if send_new_msg and update.message:
            await update.message.reply_html(msg)
        elif update.callback_query:
            await context.bot.send_message(chat_id=update.callback_query.message.chat_id, text=msg, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Erro ao carregar o ajudômetro: {e}")


async def get_monthly_goal_stats() -> dict:
    """Retorna estatísticas da meta mensal (USD)."""
    try:
        async with aiosqlite.connect(DB_FILE) as db:
            # 1. Busca a meta no system_config
            async with db.execute("SELECT value FROM system_config WHERE key = 'monthly_goal_usd'") as cursor:
                row = await cursor.fetchone()
                goal = float(row[0]) if row and row[0] else 0.0

            if goal <= 0:
                return {"goal": 0, "current": 0, "percent": 0, "bar": ""}

            # 2. Soma as doações do mês atual (1 star = 0.01 USD)
            async with db.execute(
                "SELECT SUM(amount_stars) FROM donation_history WHERE timestamp >= date('now', 'start of month')"
            ) as cursor:
                total_stars = (await cursor.fetchone())[0] or 0
                current_usd = total_stars * 0.01

            percent = min(100, round((current_usd / goal) * 100))

            # 3. Gera a barra de progresso (10 blocos)
            filled = round(percent / 10)
            bar = "█" * filled + "░" * (10 - filled)

            return {
                "goal": goal,
                "current": round(current_usd, 2),
                "percent": percent,
                "bar": f"[{bar}]"
            }
    except Exception as e:
        logger.error(f"Erro ao calcular meta mensal: {e}")
        return {"goal": 0, "current": 0, "percent": 0, "bar": ""}

async def check_and_notify_goal_reached(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Verifica se a meta foi atingida e notifica os doadores do mês."""
    try:
        stats = await get_monthly_goal_stats()
        if stats["goal"] <= 0 or stats["percent"] < 100:
            return

        current_month = datetime.datetime.now().strftime("%Y-%m")
        config_key = f"goal_notified_{current_month}"

        async with aiosqlite.connect(DB_FILE) as db:
            # Verifica se já notificou este mês
            async with db.execute("SELECT 1 FROM system_config WHERE key = ?", (config_key,)) as cursor:
                if await cursor.fetchone():
                    return

            # Registra que notificou
            await db.execute("INSERT OR REPLACE INTO system_config (key, value) VALUES (?, ?)", (config_key, "1"))
            await db.commit()

            # Busca todos os doadores do mês atual
            async with db.execute(
                "SELECT DISTINCT user_id FROM donation_history WHERE timestamp >= date('now', 'start of month')"
            ) as cursor:
                donor_ids = [row[0] for row in await cursor.fetchall()]

        # Notifica cada doador (usa o idioma do usuário se possível)
        for user_id in donor_ids:
            try:
                # Busca idioma do usuário
                async with aiosqlite.connect(DB_FILE) as db:
                    async with db.execute("SELECT language_code FROM users WHERE user_id = ?", (user_id,)) as cursor:
                        row = await cursor.fetchone()
                        lang = row[0] if row else "pt"

                # Mock de context simulado para get_text (ou usa os literais se necessário)
                # Melhor usar uma versão simplificada de get_text ou injetar o bot diretamente
                msg = get_text_by_lang(lang, "monthly_goal_reached_msg", goal=stats['goal'])
                await context.bot.send_message(chat_id=user_id, text=msg, parse_mode="HTML")
            except Exception as e:
                logger.error(f"Erro ao notificar user {user_id} sobre meta: {e}")

    except Exception as e:
        logger.error(f"Erro em check_and_notify_goal_reached: {e}")

async def saldo_estrelas_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Consulta o histórico oficial de transações de Stars (Apenas Admin)."""
    user = update.effective_user
    if user.id != ADMIN_ID:
        return

    try:
        # Busca transações via API (limite de 100 por padrão, pegamos as 100 últimas)
        transactions_obj = await context.bot.get_star_transactions()
        transactions = transactions_obj.transactions

        if not transactions:
            await update.message.reply_html("ℹ️ Nenhuma transação encontrada na API.", reply_markup=get_admin_markup())
            return

        total_received = 0
        tx_list_text = ""

        # O Telegram retorna as mais recentes primeiro
        # Pegamos as 10 últimas para exibir no log rápido
        display_txs = transactions[:10]

        for tx in transactions:
            # Somente transações de entrada (recebimento de estrelas)
            if tx.amount > 0:
                total_received += tx.amount

        for tx in display_txs:
            dt_str = tx.date.strftime("%d/%m %H:%M")
            user_tx = f"User {tx.source.user.id}" if tx.source and tx.source.user else "System/Other"
            tx_list_text += f"📅 {dt_str} | <b>{tx.amount} ⭐️</b>\n👤 {user_tx} | <code>{tx.id}</code>\n\n"

        msg = "💎 <b>Histórico Oficial de Estrelas (Telegram)</b>\n\n"
        msg += f"💰 <b>Total Recebido (API):</b> {total_received} ⭐️ (~${total_received * 0.01:.2f} USD)\n\n"
        msg += tx_list_text

        await update.message.reply_html(msg, reply_markup=get_admin_markup())

    except Exception as e:
        logger.error(f"Erro ao consultar saldo de estrelas: {e}")
        await update.message.reply_html(f"❌ Erro ao consultar API de Estrelas: {str(e)}", reply_markup=get_admin_markup())


def get_donor_tier_key(score: float = None, raw_status: str = None) -> str:
    """Retorna a chave de tradução correspondente ao nível de doador."""
    if score is not None:
        try:
            val = float(score)
            if val >= 1000:
                return "donor_tier_legend"
            if val >= 500:
                return "donor_tier_gold"
            if val >= 250:
                return "donor_tier_silver"
            if val >= 50:
                return "donor_tier_bronze"
            return "donor_tier_beginner"
        except (ValueError, TypeError):
            pass

    if raw_status:
        st = str(raw_status).lower()
        if "lenda" in st or "legend" in st:
            return "donor_tier_legend"
        if "ouro" in st or "gold" in st:
            return "donor_tier_gold"
        if "prata" in st or "silver" in st:
            return "donor_tier_silver"
        if "bronze" in st:
            return "donor_tier_bronze"
        if "iniciante" in st or "beginner" in st:
            return "donor_tier_beginner"

    return "donor_tier_beginner"


def get_donor_status_display(score: float = None, raw_status: str = None, user=None, context=None) -> str:
    """Retorna o status do apoiador traduzido no contexto do usuário."""
    tier_key = get_donor_tier_key(score=score, raw_status=raw_status)
    return get_text(user, context, tier_key)


def get_donor_status_display_by_lang(score: float = None, raw_status: str = None, lang_code: str = "pt") -> str:
    """Retorna o status do apoiador traduzido baseado no código de idioma."""
    tier_key = get_donor_tier_key(score=score, raw_status=raw_status)
    return get_text_by_lang(lang_code, tier_key)


def calculate_donor_status(total_score: float) -> str:
    """Retorna o status do apoiador com base no total equivalente em estrelas."""
    if total_score >= 1000:
        return "👑 Lenda"
    if total_score >= 500:
        return "💎 Ouro"
    if total_score >= 250:
        return "🥈 Prata"
    if total_score >= 50:
        return "🥉 Bronze"
    return "🌟 Iniciante"


async def create_ton_deposit(deposit_id: str, user_id: int, amount_usdt: float, amount_stars: int) -> bool:
    """Cria uma solicitação pendente para doação em USDT na rede TON."""
    try:
        async with aiosqlite.connect(DB_FILE) as db:
            await db.execute(
                """
                INSERT INTO ton_deposits (id, user_id, amount_usdt, amount_stars)
                VALUES (?, ?, ?, ?)
                """,
                (deposit_id, user_id, amount_usdt, amount_stars),
            )
            await db.commit()
            return True
    except Exception as e:
        logger.error(f"Erro ao criar depósito TON {deposit_id}: {e}")
        return False


async def get_pending_ton_deposits() -> list[aiosqlite.Row]:
    """Retorna depósitos USDT-TON pendentes."""
    try:
        async with aiosqlite.connect(DB_FILE) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM ton_deposits WHERE status = 'pending' ORDER BY created_at ASC"
            ) as cursor:
                return await cursor.fetchall()
    except Exception as e:
        logger.error(f"Erro ao buscar depósitos TON pendentes: {e}")
        return []


async def expire_old_ton_deposits() -> int:
    """Expira depósitos TON pendentes com mais de 2 horas."""
    try:
        async with aiosqlite.connect(DB_FILE) as db:
            cursor = await db.execute(
                """
                UPDATE ton_deposits
                SET status = 'expired'
                WHERE status = 'pending'
                  AND created_at < datetime('now', '-2 hours')
                """
            )
            await db.commit()
            return cursor.rowcount
    except Exception as e:
        logger.error(f"Erro ao expirar depósitos TON antigos: {e}")
        return 0


async def confirm_ton_deposit(deposit_id: str, tx_hash: str) -> tuple[bool, int, int, str, str, str]:
    """Confirma um depósito TON e registra a contribuição no Ajudômetro."""
    try:
        premium_until = (datetime.datetime.now() + datetime.timedelta(days=180)).isoformat()
        async with aiosqlite.connect(DB_FILE) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT id, user_id, amount_stars, status
                FROM ton_deposits
                WHERE id = ?
                """,
                (deposit_id,),
            ) as cursor:
                deposit = await cursor.fetchone()

            if not deposit or deposit["status"] != "pending":
                return False, 0, 0, "", "", ""

            user_id = deposit["user_id"]
            amount_stars = int(deposit["amount_stars"])

            cursor = await db.execute(
                """
                UPDATE ton_deposits
                SET status = 'confirmed',
                    confirmed_at = CURRENT_TIMESTAMP,
                    tx_hash = ?
                WHERE id = ? AND status = 'pending'
                """,
                (tx_hash, deposit_id),
            )
            if cursor.rowcount != 1:
                await db.rollback()
                return False, user_id, 0, "", "", ""

            await db.execute(
                """
                UPDATE users
                SET total_donated_stars = COALESCE(total_donated_stars, 0) + ?,
                    premium_until = ?
                WHERE user_id = ?
                """,
                (amount_stars, premium_until, user_id),
            )
            await db.execute(
                "INSERT INTO donation_history (user_id, amount_stars, currency) VALUES (?, ?, ?)",
                (user_id, amount_stars, "usdt_ton"),
            )

            async with db.execute(
                """
                SELECT first_name,
                       username,
                       COALESCE(custom_language, language_code, 'pt') AS lang,
                       COALESCE(total_donated_stars, 0) AS total_stars,
                       COALESCE(total_voluntary_ads, 0) AS total_ads
                FROM users
                WHERE user_id = ?
                """,
                (user_id,),
            ) as cursor:
                user_row = await cursor.fetchone()

            total_stars = user_row["total_stars"] if user_row else amount_stars
            total_ads = user_row["total_ads"] if user_row else 0
            status = calculate_donor_status(total_stars + (total_ads / 5.0))
            await db.execute(
                "UPDATE users SET donor_status = ? WHERE user_id = ?",
                (status, user_id),
            )
            await db.commit()

            lang = user_row["lang"] if user_row else "pt"
            username = user_row["username"] if user_row else ""
            status_localized = get_donor_status_display_by_lang(score=total_stars + (total_ads / 5.0), lang_code=lang)
            return True, user_id, amount_stars, status_localized, lang or "pt", username or ""
    except Exception as e:
        logger.error(f"Erro ao confirmar depósito TON {deposit_id}: {e}")
        return False, 0, 0, "", "", ""


async def check_ton_deposits_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Verifica depósitos USDT-TON pendentes na Toncenter e confirma doações."""
    if not TON_WALLET_ADDRESS or not TONCENTER_API_KEY or not TON_USDT_MASTER:
        return

    try:
        expired = await expire_old_ton_deposits()
        if expired:
            logger.info(f"TON: {expired} depósito(s) expirado(s).")

        pending = await get_pending_ton_deposits()
        if not pending:
            return

        params = {
            "account": TON_WALLET_ADDRESS,
            "jetton_master": TON_USDT_MASTER,
            "direction": "in",
            "limit": 50,
            "offset": 0,
        }
        headers = {"X-API-Key": TONCENTER_API_KEY}
        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(
                "https://toncenter.com/api/v3/jetton/transfers",
                params=params,
                headers=headers,
            ) as resp:
                if resp.status != 200:
                    logger.warning(f"TON: Toncenter retornou status {resp.status}.")
                    return
                data = await resp.json()

        transfers = data.get("jetton_transfers") or data.get("transfers") or []
        if not transfers:
            return

        pending_map = {row["id"]: row for row in pending}
        for tx in transfers:
            comment = (tx.get("comment") or "").strip()
            if not comment:
                forward_payload = tx.get("forward_payload") or {}
                if isinstance(forward_payload, dict):
                    comment = (forward_payload.get("text") or "").strip()

            if comment not in pending_map:
                continue

            try:
                amount_raw = int(tx.get("amount") or 0)
            except (TypeError, ValueError):
                logger.warning(f"TON: valor inválido para depósito {comment}: {tx.get('amount')}")
                continue

            amount_usdt = amount_raw / 1_000_000
            expected = float(pending_map[comment]["amount_usdt"])
            if amount_usdt < expected * 0.99:
                logger.warning(
                    f"TON: depósito {comment} recebeu {amount_usdt:.2f} USDT, "
                    f"mas esperava {expected:.2f}."
                )
                continue

            tx_hash = (
                tx.get("transaction_hash")
                or tx.get("hash")
                or tx.get("trace_id")
                or f"{comment}:{amount_raw}"
            )
            success, user_id, amount_stars, status, lang, username = await confirm_ton_deposit(comment, tx_hash)
            if not success:
                continue

            logger.info(f"TON: depósito {comment} confirmado para user {user_id} ({amount_stars} stars).")
            try:
                msg = get_text_by_lang(
                    lang,
                    "ton_payment_confirmed",
                    amount=f"{amount_usdt:.2f}",
                    stars=amount_stars,
                    status=status,
                )
                await context.bot.send_message(chat_id=user_id, text=msg, parse_mode="HTML")
            except Exception as notify_err:
                logger.error(f"TON: erro ao notificar usuário {user_id}: {notify_err}")

            if ADMIN_ID:
                try:
                    user_label = f"@{username}" if username else str(user_id)
                    await context.bot.send_message(
                        chat_id=ADMIN_ID,
                        text=(
                            "💰 <b>Doação USDT-TON Confirmada!</b>\n"
                            f"👤 Usuário: {html.escape(user_label)} [<code>{user_id}</code>]\n"
                            f"💵 Valor: <b>{amount_usdt:.2f} USDT</b>\n"
                            f"⭐️ Equivalente: <b>{amount_stars}</b>\n"
                            f"🔗 TX: <code>{html.escape(str(tx_hash)[:48])}</code>"
                        ),
                        parse_mode="HTML",
                    )
                except Exception as admin_err:
                    logger.error(f"TON: erro ao notificar admin: {admin_err}")

            asyncio.create_task(check_and_notify_goal_reached(context))
            pending_map.pop(comment, None)

    except Exception as e:
        logger.error(f"Erro no job de depósitos TON: {e}", exc_info=True)


def get_text_by_lang(lang_code: str, key: str, **kwargs) -> str:
    """Versão do get_text que usa código de idioma bruto, com normalização e cache."""
    base_lang = lang_code.split("-")[0].lower() if lang_code else "en"

    langs_to_try = []
    if lang_code: langs_to_try.append(lang_code)
    if base_lang not in langs_to_try: langs_to_try.append(base_lang)
    for l in ["en", "pt"]:
        if l not in langs_to_try:
            langs_to_try.append(l)

    text = None
    for lang in langs_to_try:
        if lang in TRANSLATIONS:
            text = TRANSLATIONS[lang].get(key)
            if text:
                break

    if not text:
        return key

    kwargs["version"] = VERSION
    try:
        return text.format(**kwargs)
    except:
        return text

async def meta_mensal_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Define a meta mensal de arrecadação em USD (Apenas Admin)."""
    user = update.effective_user
    if user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_html("⚠️ Uso: <code>/meta_mensal [valor_usd]</code>", reply_markup=get_admin_markup())
        return

    try:
        usd_value = float(context.args[0].replace(',', '.'))
        async with aiosqlite.connect(DB_FILE) as db:
            await db.execute(
                "INSERT OR REPLACE INTO system_config (key, value) VALUES ('monthly_goal_usd', ?)",
                (str(usd_value),)
            )
            await db.commit()

        await update.message.reply_html(f"✅ Meta mensal definida para <b>${usd_value} USD</b>.", reply_markup=get_admin_markup())
    except ValueError:
        await update.message.reply_html("⚠️ Uso: <code>/meta_mensal [valor_usd]</code>", reply_markup=get_admin_markup())


async def validar_doacao_cripto_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Valida manualmente uma doação via cripto usando USD (Apenas Admin)."""
    user = update.effective_user
    if user.id != ADMIN_ID:
        return

    if not context.args or len(context.args) < 2:
        await update.message.reply_html("⚠️ <b>Uso:</b> <code>/validar_doacao_cripto [ID] [VALOR_USD]</code>", reply_markup=get_admin_markup())
        return

    try:
        target_id = int(context.args[0])
        usd_amount = float(context.args[1].replace(',', '.'))
        # 1 Star = 0.01 USD -> Stars = USD * 100
        amount_stars = int(usd_amount * 100)
    except ValueError:
        await update.message.reply_html("⚠️ <b>Erro:</b> Valor USD inválido.", reply_markup=get_admin_markup())
        return

    try:
        async with aiosqlite.connect(DB_FILE) as db:
            # Busca o usuário alvo
            async with db.execute("SELECT first_name, language_code, total_donated_stars, total_voluntary_ads FROM users WHERE user_id = ?", (target_id,)) as cursor:
                row = await cursor.fetchone()

            if not row:
                await update.message.reply_html("❌ Usuário não encontrado no banco de dados.", reply_markup=get_admin_markup())
                return

            name = row[0] or "User"
            user_lang = row[1] or "pt"
            current_stars = row[2] or 0
            voluntary_ads = row[3] or 0

            # Atualiza o status de doador no DB
            await db.execute(
                "UPDATE users SET total_donated_stars = total_donated_stars + ?, premium_until = ? WHERE user_id = ?",
                (amount_stars, (datetime.datetime.now() + datetime.timedelta(days=180)).isoformat(), target_id)
            )
            await db.execute(
                "INSERT INTO donation_history (user_id, amount_stars, currency) VALUES (?, ?, ?)",
                (target_id, amount_stars, 'crypto_usd')
            )

            # Recalcula status
            new_total = (current_stars + amount_stars) + (voluntary_ads / 5.0)
            status = "🌟 Iniciante"
            if new_total >= 1000: status = "👑 Lenda"
            elif new_total >= 500: status = "💎 Ouro"
            elif new_total >= 250: status = "🥈 Prata"
            elif new_total >= 50: status = "🥉 Bronze"

            await db.execute("UPDATE users SET donor_status = ? WHERE user_id = ?", (status, target_id))
            await db.commit()

            # Notifica o Admin
            await update.message.reply_html(
                f"✅ <b>Crédito Realizado!</b>\nO usuário <b>{name}</b> ({target_id}) recebeu <b>{amount_stars} estrelas</b>.\nNovo Status: <b>{status}</b>",
                reply_markup=get_admin_markup()
            )

            # Notifica o Usuário Alvo
            try:
                status_localized = get_donor_status_display_by_lang(score=new_total, lang_code=user_lang)
                msg_user = get_text_by_lang(user_lang, "admin_credit_notify_user", amount=amount_stars, status=status_localized)
                await context.bot.send_message(chat_id=target_id, text=msg_user, parse_mode="HTML")
            except Exception as e:
                logger.error(f"Erro ao notificar usuário de crédito: {e}")

            # Verifica meta mensal
            asyncio.create_task(check_and_notify_goal_reached(context))

    except Exception as e:
        logger.error(f"Erro ao creditar doação: {e}")
        await update.message.reply_text(f"Erro fatal: {e}")




def main() -> None:
    """Inicia o bot."""
    # Carrega as traduções
    load_translations()

    telegram_request = HTTPXRequest(
        connect_timeout=TELEGRAM_CONNECT_TIMEOUT,
        read_timeout=TELEGRAM_READ_TIMEOUT,
        write_timeout=TELEGRAM_WRITE_TIMEOUT,
        pool_timeout=TELEGRAM_POOL_TIMEOUT,
        media_write_timeout=TELEGRAM_WRITE_TIMEOUT,
        proxy=TELEGRAM_PROXY,
    )
    get_updates_request = HTTPXRequest(
        connect_timeout=TELEGRAM_CONNECT_TIMEOUT,
        read_timeout=TELEGRAM_POLL_TIMEOUT + TELEGRAM_READ_TIMEOUT,
        write_timeout=TELEGRAM_WRITE_TIMEOUT,
        pool_timeout=TELEGRAM_POOL_TIMEOUT,
        proxy=TELEGRAM_PROXY,
    )

    # Cria o Application
    application = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .request(telegram_request)
        .get_updates_request(get_updates_request)
        .post_init(post_init)
        .build()
    )

    # Middleware Global: Captura TODAS as interações antes dos comandos específicos
    # group=-1 garante que execute antes dos handlers padrão (group=0)
    application.add_handler(TypeHandler(Update, global_logging_middleware), group=-1)

    # Adiciona os handlers

    # --- Sistema de Tickets ---
    _ticket_btn_texts = [
        v.get("menu_support_tickets", "")
        for v in TRANSLATIONS.values()
        if v.get("menu_support_tickets")
    ]
    ticket_conv = tickets_mod.build_ticket_conversation_handler(_ticket_btn_texts)
    application.add_handler(ticket_conv, group=1)
    for h in tickets_mod.get_ticket_admin_handlers():
        application.add_handler(h, group=1)
    # Handler de texto para admin acessar gestão de tickets via teclado admin
    application.add_handler(
        MessageHandler(
            filters.TEXT & filters.Regex(r"Gestão de Tickets"),
            tickets_mod.admin_tickets_menu
        ),
        group=1
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("anuncios_qtd", set_ad_threshold))
    application.add_handler(CommandHandler("contribute", contribute_command))
    application.add_handler(CommandHandler("apoiar", contribute_command))
    application.add_handler(CommandHandler("top_donors", top_donors_command))
    application.add_handler(CommandHandler("ajudometro", top_donors_command))
    application.add_handler(CallbackQueryHandler(handle_contribute_callback, pattern=r"^contribute:"))
    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))

    application.add_handler(CommandHandler("version", version_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(
        CommandHandler("merge_vertically", merge_vertically_command)
    )
    application.add_handler(
        CommandHandler("merge_horizontally", merge_horizontally_command)
    )

    application.add_handler(CommandHandler("cancel", cancel_command))
    application.add_handler(CommandHandler("relatorio", report_command))
    application.add_handler(CommandHandler("relatorio_uso", usage_report_graph_command))

    application.add_handler(CommandHandler("validar_doacao_cripto", validar_doacao_cripto_command))
    application.add_handler(CommandHandler("meta_mensal", meta_mensal_command))
    application.add_handler(CommandHandler("saldo_estrelas", saldo_estrelas_command))
    application.add_handler(CommandHandler("ferramentas", tools_menu_command))
    application.add_handler(CommandHandler("censor", censor_menu_command))
    application.add_handler(CommandHandler("censura", censor_menu_command))

    application.add_handler(CommandHandler("diagnostico", diagnostic_command))
    application.add_handler(CommandHandler("backup_db", backup_db_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(
        MessageHandler(filters.CaptionRegex(r"^/broadcast(?:\s|$)"), broadcast_command)
    )
    application.add_handler(CommandHandler("broadcast_usuario", broadcast_user_command))
    application.add_handler(
        MessageHandler(
            filters.CaptionRegex(r"^/broadcast_usuario(?:\s|$)"), broadcast_user_command
        )
    )
    application.add_handler(CommandHandler("broadcast_ultimo", broadcast_last_command))
    application.add_handler(CommandHandler("logs", logs_command))

    application.add_handler(CommandHandler("restart", restart_command))
    application.add_handler(CommandHandler("reiniciar", restart_command))
    application.add_handler(CommandHandler("pausar", pause_command))
    application.add_handler(CommandHandler("retomar", resume_command))

    application.add_handler(CommandHandler("banir", ban_command))
    application.add_handler(CommandHandler("desbanir", unban_command))
    application.add_handler(CommandHandler("listar_banidos", list_banned_command))

    application.add_handler(CommandHandler("processos", set_workers_command))
    application.add_handler(CommandHandler("cache", cache_command))
    application.add_handler(CommandHandler("status_fila", queue_status_command))
    application.add_handler(CommandHandler("limpar_cache", clear_cache_command))
    application.add_handler(
        CommandHandler("limpar_db_bloqueados", clean_blocked_users_command)
    )

    application.add_handler(
        CallbackQueryHandler(restart_callback, pattern=r"^restart_bot$")
    )
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(
        CallbackQueryHandler(handle_lib_update, pattern=r"^update_lib:")
    )
    application.add_handler(
        CallbackQueryHandler(handle_format_callback, pattern=r"^set_fmt:")
    )
    application.add_handler(
        CallbackQueryHandler(handle_settings_navigation, pattern=r"^settings_nav:")
    )
    application.add_handler(
        CallbackQueryHandler(handle_language_callback, pattern=r"^set_lang:")
    )
    application.add_handler(
        CallbackQueryHandler(handle_language_init_callback, pattern=r"^set_lang_init:")
    )
    application.add_handler(
        CallbackQueryHandler(handle_borders_navigation, pattern=r"^borders_nav:")
    )
    application.add_handler(
        CallbackQueryHandler(
            handle_border_color_callback, pattern=r"^set_border_color:"
        )
    )
    application.add_handler(
        CallbackQueryHandler(handle_bgcolor_callback, pattern=r"^set_bg:")
    )
    application.add_handler(
        CallbackQueryHandler(handle_grid_columns_callback, pattern=r"^grid_cols:")
    )
    application.add_handler(
        CallbackQueryHandler(handle_autoresize_callback, pattern=r"^set_resize:")
    )
    application.add_handler(
        CallbackQueryHandler(handle_get_document_callback, pattern=r"^get_doc:")
    )
    application.add_handler(
        CallbackQueryHandler(handle_get_pdf_callback, pattern=r"^get_pdf:")
    )
    application.add_handler(
        CallbackQueryHandler(handle_get_zip_callback, pattern=r"^get_zip:")
    )
    application.add_handler(
        CallbackQueryHandler(handle_regen_callback, pattern=r"^regen:")
    )
    application.add_handler(
        CallbackQueryHandler(handle_reverse_callback, pattern=r"^reverse:")
    )
    application.add_handler(
        CallbackQueryHandler(handle_delete_image_callback, pattern=r"^del_img:")
    )
    application.add_handler(
        CallbackQueryHandler(handle_search_image_callback, pattern=r"^search_img:")
    )
    application.add_handler(
        CallbackQueryHandler(handle_read_qr_callback, pattern=r"^read_qr:")
    )
    application.add_handler(
        CallbackQueryHandler(handle_video_to_gif_confirm_callback, pattern=r"^video_to_gif_confirm:")
    )
    application.add_handler(
        CallbackQueryHandler(handle_video_to_gif_cancel_callback, pattern=r"^video_to_gif_cancel:")
    )
    application.add_handler(
        CallbackQueryHandler(handle_delete_pdf_callback, pattern=r"^del_pdf:")
    )
    application.add_handler(
        CallbackQueryHandler(handle_clear_all_callback, pattern=r"^clear_all:")
    )

    application.add_handler(
        CallbackQueryHandler(diagnostic_command, pattern=r"^refresh_diagnostic$")
    )

    rembg_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(remove_bg_choose_format, pattern=r"^rembg:")],
        states={
            REMBG_AGRESSIVENESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, remove_bg_process)]
        },
        fallbacks=[CommandHandler("cancel", remove_bg_cancel)],
    )
    application.add_handler(rembg_conv_handler)

    # ConversationHandler para Meme
    meme_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("meme", meme_start),
            CallbackQueryHandler(meme_receive_image, pattern=r"^meme:(use_last|new)$"),
        ],
        states={
            MEME_IMAGE: [
                MessageHandler(filters.PHOTO, meme_receive_image),
                MessageHandler(filters.Document.IMAGE, meme_receive_image),
            ],
            MEME_TOP_TEXT: [
                CallbackQueryHandler(meme_receive_top_text, pattern=r"^meme:skip_top$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, meme_receive_top_text)
            ],
            MEME_BOTTOM_TEXT: [
                CallbackQueryHandler(meme_receive_bottom_text, pattern=r"^meme:skip_bottom$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, meme_receive_bottom_text)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", meme_cancel),
            CallbackQueryHandler(meme_cancel, pattern=r"^meme:cancel$")
        ],
    )
    application.add_handler(meme_conv_handler)
    application.add_handler(
        CallbackQueryHandler(meme_resize_callback, pattern=r"^meme:resize:")
    )

    application.add_handler(
        CallbackQueryHandler(handle_move_pdf_callback, pattern=r"^move_pdf:")
    )
    application.add_handler(
        CallbackQueryHandler(handle_move_image_callback, pattern=r"^move:")
    )
    application.add_handler(
        CallbackQueryHandler(handle_about_callback, pattern=r"^about_")
    )
    application.add_handler(
        CallbackQueryHandler(handle_close_msg_callback, pattern=r"^close_msg$")
    )
    application.add_handler(
        CallbackQueryHandler(handle_converter_callback, pattern=r"^convert:")
    )
    application.add_handler(
        CallbackQueryHandler(handle_ocr_language_callback, pattern=r"^ocr_lang:")
    )
    application.add_handler(
        CallbackQueryHandler(handle_ocr_advanced_callback, pattern=r"^ocr_adv:")
    )
    application.add_handler(
        CallbackQueryHandler(handle_pdf_orientation_callback, pattern=r"^pdf_make:")
    )
    application.add_handler(
        CallbackQueryHandler(handle_censor_callback, pattern=r"^censor_blur:")
    )

    application.add_handler(
        CallbackQueryHandler(handle_broadcast_selection, pattern=r"^broadcast:")
    )
    application.add_handler(
        CallbackQueryHandler(
            handle_broadcast_confirmation, pattern=r"^broadcast_confirm:"
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            handle_broadcast_multi_cancel, pattern=r"^broadcast_multi_cancel$"
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            handle_broadcast_multi_confirm, pattern=r"^broadcast_multi_confirm:"
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            handle_sticker_convert_callback, pattern=r"^sticker_convert:"
        )
    )
    application.add_handler(
        CallbackQueryHandler(handle_gif_menu_callback, pattern=r"^gif_action:")
    )
    application.add_handler(
        CallbackQueryHandler(handle_gif_settings_callback, pattern=r"^gif_set:")
    )
    application.add_handler(
        CallbackQueryHandler(handle_gif_conv_callback, pattern=r"^gif_conv:")
    )
    application.add_handler(
        CallbackQueryHandler(handle_gif_extraction_sub_callback, pattern=r"^gif_ext:")
    )
    application.add_handler(
        CallbackQueryHandler(handle_media_confirm_callback, pattern=r"^(vid_to_gif_confirm|gif_to_video_confirm|video_to_gif_cancel):")
    )
    # Handler para PDF
    application.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))

    # Handler para callbacks de PDF
    application.add_handler(
        CallbackQueryHandler(handle_pdf_action_callback, pattern=r"^pdf_action:")
    )
    application.add_handler(
        CallbackQueryHandler(handle_pdf_ocr_lang_callback, pattern=r"^pdf_ocr_lang:")
    )

    # Handler para DOCX
    DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    application.add_handler(
        MessageHandler(filters.Document.MimeType(DOCX_MIME), handle_docx)
    )
    application.add_handler(
        CallbackQueryHandler(handle_docx_action_callback, pattern=r"^docx_action:")
    )
    application.add_handler(
        CallbackQueryHandler(handle_delete_docx_callback, pattern=r"^del_docx:")
    )
    application.add_handler(
        CallbackQueryHandler(handle_move_docx_callback, pattern=r"^move_docx:")
    )
    application.add_handler(
        CallbackQueryHandler(handle_qrcode_add_text_callback, pattern=r"^qrcode_add_text:")
    )
    application.add_handler(
        CallbackQueryHandler(watermark_callback_handler, pattern=r"^wm_")
    )
    application.add_handler(
        CallbackQueryHandler(tools_menu_command, pattern=r"^back_tools$")
    )

    # Handler para Stickers (antes de invalid_file)
    application.add_handler(MessageHandler(filters.Sticker.ALL, handle_sticker))

    # Handler para Video/GIF (Conversão) - Deve vir antes de invalid_file
    application.add_handler(MessageHandler(filters.VIDEO | filters.ANIMATION | filters.Document.VIDEO | filters.VIDEO_NOTE, handle_media_for_gif))

    # Aceita fotos comprimidas E documentos que sejam imagens
    application.add_handler(
        MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_image)
    )

    # Rejeita arquivos que não sejam imagens (Documentos genéricos, Vídeo, Áudio, Voz)
    _DOCX_MIME_FILTER = filters.Document.MimeType(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    application.add_handler(
        MessageHandler(
            filters.VIDEO
            | filters.AUDIO
            | filters.VOICE
            | filters.ANIMATION
            | (
                filters.Document.ALL
                & ~filters.Document.IMAGE
                & ~filters.Document.PDF
                & ~_DOCX_MIME_FILTER
            ),
            handle_invalid_file,
        )
    )

    # Aceita texto para o fluxo de configuração (ex: definir qualidade)
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input)
    )

    # Tratamento de erros global
    application.add_error_handler(error_handler)

    # Agenda a limpeza do banco de dados e cache a cada 10 minutos (600 segundos)
    if application.job_queue:
        application.job_queue.run_repeating(cleanup_old_images, interval=600, first=60)
        # Agenda backup automático a cada 24 horas (86400 segundos)
        application.job_queue.run_repeating(
            scheduled_backup_db, interval=86400, first=86400
        )
        # Agenda a gravação dos logs em lote a cada 60 segundos
        application.job_queue.run_repeating(flush_activity_logs, interval=60, first=30)

        # Agenda o relatório diário para as 21:00 (Horário de Brasília / UTC-3)
        # 21:00 Brasília = 00:00 UTC (dependendo do servidor estar em UTC)
        # Vamos usar explicitamente 21:00 local se o sistema estiver em Horário de Brasília
        from datetime import time as dt_time
        target_time = dt_time(hour=21, minute=0, second=0)
        application.job_queue.run_daily(
            send_daily_summary_report,
            time=target_time,
            days=(0, 1, 2, 3, 4, 5, 6) # Todos os dias
        )
        # Agenda a limpeza de logs antigos a cada 24 horas
        application.job_queue.run_repeating(cleanup_old_logs, interval=86400, first=300)
        # Agenda limpeza semanal de usuários bloqueados todo domingo às 03:00 (Horário de Brasília / UTC-3)
        from zoneinfo import ZoneInfo
        clean_blocked_time = dt_time(hour=3, minute=0, second=0, tzinfo=ZoneInfo("America/Sao_Paulo"))
        application.job_queue.run_daily(
            scheduled_clean_blocked_users_job,
            time=clean_blocked_time,
            days=(6,) # 6 = Domingo
        )
        # Agenda verificação de promo a cada 1 hora
        application.job_queue.run_repeating(check_promo_task, interval=3600, first=60)
        # Agenda verificação de promo MartianCat a cada 1 hora
        application.job_queue.run_repeating(check_martiancat_promo_task, interval=3600, first=90)
        # Verifica diariamente o lembrete único de apoio após 7 dias de uso.
        # O caso de cota atingida é disparado imediatamente em check_ad_quota_reached.
        application.job_queue.run_repeating(support_reminder_task, interval=86400, first=60)
        # Verifica depósitos USDT-TON pendentes para apoio via @wallet
        application.job_queue.run_repeating(check_ton_deposits_job, interval=60, first=180)

    # Inicia o bot
    log_telegram_connectivity_check()
    logger.info(
        "Iniciando o bot... poll_timeout=%ss bootstrap_retries=%s connect_timeout=%ss",
        TELEGRAM_POLL_TIMEOUT,
        TELEGRAM_BOOTSTRAP_RETRIES,
        TELEGRAM_CONNECT_TIMEOUT,
    )
    application.run_polling(
        timeout=TELEGRAM_POLL_TIMEOUT,
        bootstrap_retries=TELEGRAM_BOOTSTRAP_RETRIES,
    )


if __name__ == "__main__":
    main()
