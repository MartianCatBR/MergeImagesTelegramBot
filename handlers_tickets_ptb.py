"""
handlers_tickets_ptb.py
========================
Sistema de suporte via tickets para python-telegram-bot.
Adaptado de handlers_tickets.py (aiogram) para o bot UnifyImages.

Estado da conversa:
  TICKET_MAIN          (0) — menu principal de tickets mostrado
  TICKET_CHOOSE_CATEGORY (1) — aguardando escolha de categoria
  TICKET_WRITE_TEXT    (2) — aguardando texto do ticket
  ADMIN_WRITE_REPLY    (3) — admin digitando resposta
"""

import asyncio
import html
import io
import logging

import aiosqlite
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

logger = logging.getLogger(__name__)

# ============================================================
# Dependências injetadas pelo bot principal
# ============================================================
_DB_FILE: str = ""
_ADMIN_ID: int = 0
_get_text = None
_TRANSLATIONS: dict = {}


def setup_tickets_module(db_file: str, admin_id: int, get_text_fn, translations: dict):
    """Chamado no post_init() para injetar dependências do bot principal."""
    global _DB_FILE, _ADMIN_ID, _get_text, _TRANSLATIONS
    _DB_FILE = db_file
    _ADMIN_ID = admin_id
    _get_text = get_text_fn
    _TRANSLATIONS = translations


# ============================================================
# Estados do ConversationHandler
# ============================================================
TICKET_MAIN, TICKET_CHOOSE_CATEGORY, TICKET_WRITE_TEXT, ADMIN_WRITE_REPLY = range(4)


# ============================================================
# Helpers de tradução
# ============================================================
def _t(user, context, key: str, lang: str = None, **kwargs) -> str:
    return _get_text(user, context, key, lang=lang, **kwargs)


def _t_lang(lang: str, key: str, **kwargs) -> str:
    """Obtém tradução pelo código de idioma (sem user/context)."""
    text = None
    # Normaliza o idioma (ex: 'pt-br' -> 'pt')
    base_lang = lang.split("-")[0].lower() if lang else "en"
    
    for l in [lang, base_lang, "en", "pt"]:
        if l and l in _TRANSLATIONS:
            text = _TRANSLATIONS[l].get(key)
            if text:
                break
    if not text:
        return key
    try:
        return text.format(**kwargs)
    except Exception:
        return text


# ============================================================
# Teclados inline
# ============================================================
def _kb_ticket_main(user, context) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(_t(user, context, "ticket_btn_new"), callback_data="ticket:new")],
        [InlineKeyboardButton(_t(user, context, "ticket_btn_my_open"), callback_data="ticket:opened")],
        [InlineKeyboardButton(_t(user, context, "ticket_btn_my_closed"), callback_data="ticket:closed")],
        [InlineKeyboardButton(_t(user, context, "btn_close"), callback_data="ticket:close")],
    ])


def _kb_categories(user, context) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(_t(user, context, "ticket_cat_bug"), callback_data="ticket_cat:bug"),
            InlineKeyboardButton(_t(user, context, "ticket_cat_suggest"), callback_data="ticket_cat:suggest"),
        ],
        [
            InlineKeyboardButton(_t(user, context, "ticket_cat_question"), callback_data="ticket_cat:question"),
            InlineKeyboardButton(_t(user, context, "ticket_cat_account"), callback_data="ticket_cat:account"),
        ],
        [InlineKeyboardButton(_t(user, context, "ticket_cat_other"), callback_data="ticket_cat:other")],
        [InlineKeyboardButton(_t(user, context, "btn_back"), callback_data="ticket:main")],
    ])


def _kb_admin_main() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Listar Pendentes", callback_data="admin_ticket:pending")],
        [InlineKeyboardButton("🗃️ Listar Concluídos", callback_data="admin_ticket:closed")],
        [InlineKeyboardButton("❌ Fechar", callback_data="admin_ticket:close")],
    ])


def _kb_admin_ticket_actions(ticket_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Concluir / Responder", callback_data=f"admin_ticket_done:{ticket_id}")],
        [InlineKeyboardButton("🗑️ Ignorar (Sem notificar)", callback_data=f"admin_ticket_ignore:{ticket_id}")],
    ])


# ============================================================
# HANDLERS USUÁRIO — dentro do ConversationHandler
# ============================================================

async def ticket_main_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point via botão de texto. Exibe o menu principal de suporte."""
    user = update.effective_user
    msg = _t(user, context, "ticket_support_title") + "\n\n" + _t(user, context, "ticket_support_intro")
    await update.message.reply_html(msg, reply_markup=_kb_ticket_main(user, context))
    return TICKET_MAIN  # ← Permanece na conversa esperando ação inline


async def cb_ticket_main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point ou volta ao menu principal de tickets via callback. Limpa estados temporários."""
    query = update.callback_query
    await query.answer()
    user = query.from_user
    context.user_data.pop("ticket_category", None)
    context.user_data.pop("ticket_cat_name", None)
    msg = _t(user, context, "ticket_support_title") + "\n\n" + _t(user, context, "ticket_support_intro")
    
    # Se originado do help_open_tickets, responde como nova mensagem para preservar o HTML de ajuda
    if query.data == "help_open_tickets":
        await query.message.reply_html(msg, reply_markup=_kb_ticket_main(user, context))
    else:
        await query.message.edit_text(msg, reply_markup=_kb_ticket_main(user, context), parse_mode="HTML")
    return TICKET_MAIN


async def cb_ticket_close(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Fecha/deleta a mensagem do menu de tickets."""
    query = update.callback_query
    await query.answer()
    try:
        await query.message.delete()
    except Exception:
        pass
    return ConversationHandler.END


async def cb_ticket_new(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia abertura de novo ticket — verifica limite de 5 abertos."""
    query = update.callback_query
    await query.answer()
    user = query.from_user

    async with aiosqlite.connect(_DB_FILE) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM support_tickets WHERE user_id = ? AND status = 'open'",
            (user.id,)
        ) as cursor:
            row = await cursor.fetchone()
            open_count = row[0] if row else 0

    if open_count >= 5:
        await query.answer(
            _t(user, context, "ticket_limit_reached", count=open_count),
            show_alert=True
        )
        return TICKET_MAIN

    await query.message.edit_text(
        _t(user, context, "ticket_choose_category"),
        reply_markup=_kb_categories(user, context)
    )
    return TICKET_CHOOSE_CATEGORY


async def cb_ticket_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Usuário escolheu a categoria — pede o texto do ticket."""
    query = update.callback_query
    await query.answer()
    user = query.from_user

    category = query.data.split(":")[1]
    cat_keys = {
        "bug": "ticket_cat_bug",
        "suggest": "ticket_cat_suggest",
        "question": "ticket_cat_question",
        "account": "ticket_cat_account",
        "other": "ticket_cat_other",
    }
    cat_name = _t(user, context, cat_keys.get(category, "ticket_cat_other"))

    context.user_data["ticket_category"] = category
    context.user_data["ticket_cat_name"] = cat_name

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(_t(user, context, "btn_back"), callback_data="ticket:main")
    ]])
    await query.message.edit_text(
        _t(user, context, "ticket_input_prompt", cat_name=cat_name),
        reply_markup=kb,
        parse_mode="HTML"
    )
    return TICKET_WRITE_TEXT


async def msg_ticket_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recebe o texto do ticket e salva no banco."""
    user = update.effective_user
    text = update.message.text.strip()

    if len(text) > 3000:
        await update.message.reply_html(
            _t(user, context, "ticket_msg_too_long", length=len(text))
        )
        return TICKET_WRITE_TEXT

    category = context.user_data.get("ticket_category", "other")
    cat_name = context.user_data.get("ticket_cat_name", "Outro")

    async with aiosqlite.connect(_DB_FILE) as db:
        cursor = await db.execute(
            "INSERT INTO support_tickets (user_id, category, text) VALUES (?, ?, ?)",
            (user.id, category, text)
        )
        ticket_id = cursor.lastrowid
        await db.commit()

    context.user_data.pop("ticket_category", None)
    context.user_data.pop("ticket_cat_name", None)

    await update.message.reply_html(
        _t(user, context, "ticket_created_ok", ticket_id=ticket_id, cat_name=cat_name),
        reply_markup=_kb_ticket_main(user, context)
    )

    # O usuário abriu um ticket para solicitar atendimento; por isso o
    # administrador recebe a mensagem e os dados necessários para contato.
    user_info = html.escape(user.full_name)
    if user.username:
        user_info += f" (@{html.escape(user.username)})"
    admin_msg = (
        f"🎫 <b>NOVO TICKET #{ticket_id}</b>\n\n"
        f"👤 {user_info} [<code>{user.id}</code>]\n"
        f"🗂 Categoria: {html.escape(category)}\n\n"
        f"📝 <b>Mensagem:</b>\n{html.escape(text)}"
    )
    try:
        await update.get_bot().send_message(
            _ADMIN_ID, admin_msg,
            reply_markup=_kb_admin_ticket_actions(ticket_id),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Erro ao notificar admin sobre ticket #{ticket_id}: {e}")

    return TICKET_MAIN


async def cb_ticket_opened(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Lista os tickets abertos do usuário."""
    query = update.callback_query
    await query.answer()
    user = query.from_user

    async with aiosqlite.connect(_DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM support_tickets WHERE user_id = ? AND status = 'open' ORDER BY created_at DESC",
            (user.id,)
        ) as cursor:
            tickets = await cursor.fetchall()

    if not tickets:
        await query.answer(_t(user, context, "ticket_no_open"), show_alert=True)
        return TICKET_MAIN

    cat_keys = {
        "bug": "ticket_cat_bug", "suggest": "ticket_cat_suggest",
        "question": "ticket_cat_question", "account": "ticket_cat_account",
        "other": "ticket_cat_other"
    }

    try:
        await query.message.delete()
    except Exception:
        pass

    for t in tickets[:5]:
        cat_localized = _t(user, context, cat_keys.get(t["category"], "ticket_cat_other"))
        text_preview = html.escape(t["text"][:500])
        msg = _t(
            user, context, "ticket_item_open",
            id=t["id"], category=cat_localized,
            date=t["created_at"], text=text_preview
        )
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                _t(user, context, "ticket_btn_cancel"),
                callback_data=f"ticket_cancel:{t['id']}"
            )
        ]])
        await context.bot.send_message(chat_id=user.id, text=msg, reply_markup=kb, parse_mode="HTML")
        await asyncio.sleep(0.05)

    # Reenvia menu principal (nova mensagem, pois a anterior foi deletada)
    menu_msg = _t(user, context, "ticket_support_title") + "\n\n" + _t(user, context, "ticket_support_intro")
    await context.bot.send_message(
        chat_id=user.id, text=menu_msg, reply_markup=_kb_ticket_main(user, context), parse_mode="HTML"
    )
    return TICKET_MAIN


async def cb_ticket_cancel_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Usuário cancela um dos seus tickets abertos."""
    query = update.callback_query
    ticket_id = int(query.data.split(":")[1])
    user = query.from_user

    async with aiosqlite.connect(_DB_FILE) as db:
        await db.execute(
            "UPDATE support_tickets SET status = 'cancelled', closed_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?",
            (ticket_id, user.id)
        )
        await db.commit()

    await query.answer(f"Ticket #{ticket_id} cancelado.", show_alert=True)
    try:
        await query.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    return TICKET_MAIN


async def cb_ticket_closed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Lista os tickets fechados do usuário."""
    query = update.callback_query
    await query.answer()
    user = query.from_user

    async with aiosqlite.connect(_DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM support_tickets WHERE user_id = ? AND status IN ('closed', 'ignored') ORDER BY closed_at DESC",
            (user.id,)
        ) as cursor:
            tickets = await cursor.fetchall()

    if not tickets:
        await query.answer(_t(user, context, "ticket_no_closed"), show_alert=True)
        return TICKET_MAIN

    msg = _t(user, context, "ticket_closed_title") + "\n\n"
    for t in tickets[:5]:
        msg += f"🎫 <b>#{t['id']}</b> ({t['category']})\n📝 {html.escape(t['text'][:80])}...\n\n"

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(_t(user, context, "btn_back"), callback_data="ticket:main")
    ]])
    await query.message.edit_text(msg, reply_markup=kb, parse_mode="HTML")

    if len(tickets) > 5:
        txt = "HISTÓRICO DE TICKETS\n" + "=" * 40 + "\n\n"
        for t in tickets:
            txt += (
                f"Ticket #{t['id']} | Categoria: {t['category']} | Status: {t['status']}\n"
                f"Criado em: {t['created_at']} | Fechado em: {t['closed_at']}\n"
                f"Mensagem: {t['text']}\n"
            )
            if t["admin_reply"]:
                txt += f"Resposta Admin: {t['admin_reply']}\n"
            txt += "-" * 40 + "\n"

        doc = io.BytesIO(txt.encode("utf-8"))
        doc.name = "historico_tickets.txt"
        try:
            await query.get_bot().send_document(
                user.id, doc,
                caption=_t(user, context, "ticket_history_caption")
            )
        except Exception as e:
            logger.error(f"Erro ao enviar histórico de tickets ao user {user.id}: {e}")

    return TICKET_MAIN


# ============================================================
# HANDLERS ADMIN — gestão via standalone handlers
# ============================================================

async def _admin_ticket_menu_text() -> str:
    async with aiosqlite.connect(_DB_FILE) as db:
        async with db.execute(
            """SELECT
                   SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END),
                   SUM(CASE WHEN status IN ('closed', 'ignored', 'cancelled') THEN 1 ELSE 0 END)
               FROM support_tickets"""
        ) as cursor:
            row = await cursor.fetchone()

    pending_count = row[0] or 0 if row else 0
    completed_count = row[1] or 0 if row else 0
    return (
        "🎫 <b>Gestão de Tickets</b>\n\n"
        f"⏳ <b>Pendentes de resposta:</b> {pending_count}\n"
        f"✅ <b>Concluídos:</b> {completed_count}\n\n"
        "Selecione uma opção:"
    )


async def admin_tickets_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Exibe o menu de gestão de tickets para o admin (via botão do teclado admin)."""
    if update.effective_user.id != _ADMIN_ID:
        return ConversationHandler.END
    await update.message.reply_html(
        await _admin_ticket_menu_text(),
        reply_markup=_kb_admin_main()
    )
    return ConversationHandler.END


async def cb_admin_ticket_main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query.from_user.id != _ADMIN_ID:
        await query.answer()
        return
    await query.answer()
    await query.message.edit_text(
        await _admin_ticket_menu_text(),
        reply_markup=_kb_admin_main(),
        parse_mode="HTML"
    )


async def cb_admin_close(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    try:
        await query.message.delete()
    except Exception:
        pass


async def cb_admin_pending(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query.from_user.id != _ADMIN_ID:
        await query.answer()
        return
    await query.answer()

    async with aiosqlite.connect(_DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM support_tickets WHERE status = 'open' ORDER BY created_at ASC"
        ) as cursor:
            tickets = await cursor.fetchall()

    if not tickets:
        await query.answer("Nenhum ticket pendente 🎉", show_alert=True)
        return

    try:
        await query.message.delete()
    except Exception:
        pass

    for t in tickets[:5]:
        uid = t["user_id"]
        try:
            chat = await query.get_bot().get_chat(uid)
            user_info = html.escape(chat.full_name)
            if chat.username:
                user_info += f" (@{html.escape(chat.username)})"
        except Exception:
            user_info = "Desconhecido"

        msg = (
            f"🎫 <b>TICKET PENDENTE #{t['id']}</b>\n\n"
            f"👤 {user_info} [<code>{uid}</code>]\n"
            f"🗂 Categoria: {html.escape(t['category'])}\n"
            f"🕒 {html.escape(t['created_at'])}\n\n"
            f"📝 <b>Mensagem:</b>\n{html.escape(t['text'])}"
        )
        await context.bot.send_message(
            chat_id=query.message.chat_id, text=msg, reply_markup=_kb_admin_ticket_actions(t["id"]), parse_mode="HTML"
        )
        await asyncio.sleep(0.1)

    if len(tickets) > 5:
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"<i>Há {len(tickets)} tickets abertos no total. Conclua os atuais para ver mais.</i>",
            parse_mode="HTML",
            reply_markup=_kb_admin_main()
        )


async def cb_admin_closed_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query.from_user.id != _ADMIN_ID:
        await query.answer()
        return
    await query.answer()

    async with aiosqlite.connect(_DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM support_tickets WHERE status IN ('closed', 'ignored', 'cancelled') ORDER BY closed_at DESC"
        ) as cursor:
            tickets = await cursor.fetchall()

    if not tickets:
        await query.answer("Nenhum ticket concluído ainda.", show_alert=True)
        return

    msg = "✅ <b>Últimos tickets concluídos/ignorados:</b>\n\n"
    for t in tickets[:5]:
        msg += (
            f"🎫 <b>#{t['id']}</b> ({t['status']}) — "
            f"User <code>{t['user_id']}</code>\n"
            f"📝 {html.escape(t['text'][:500])}\n\n"
        )

    await query.message.edit_text(
        msg,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Voltar", callback_data="admin_ticket:main")
        ]]),
        parse_mode="HTML"
    )

    if len(tickets) > 5:
        txt = "HISTÓRICO DE TODOS OS TICKETS FECHADOS\n" + "=" * 40 + "\n\n"
        for t in tickets:
            txt += (
                f"Ticket #{t['id']} | User: {t['user_id']} | Cat: {t['category']} | Status: {t['status']}\n"
                f"Criado: {t['created_at']} | Fechado: {t['closed_at']}\n"
                f"Mensagem: {t['text']}\nAdmin Reply: {t['admin_reply']}\n"
                + "-" * 40 + "\n"
            )
        doc = io.BytesIO(txt.encode("utf-8"))
        doc.name = "historico_admin_tickets.txt"
        try:
            await query.get_bot().send_document(
                _ADMIN_ID, doc, caption="Arquivo completo gerado."
            )
        except Exception:
            pass


async def cb_admin_ignore(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    ticket_id = int(query.data.split(":")[1])

    async with aiosqlite.connect(_DB_FILE) as db:
        await db.execute(
            "UPDATE support_tickets SET status = 'ignored', closed_at = CURRENT_TIMESTAMP WHERE id = ?",
            (ticket_id,)
        )
        await db.commit()

    try:
        await query.message.edit_text(
            query.message.text_html + "\n\n<i>🗑️ Ignorado pelo admin.</i>",
            reply_markup=None,
            parse_mode="HTML"
        )
    except Exception:
        pass
    await query.answer("Ignorado. (O usuário não foi avisado).")


async def cb_admin_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin clica em 'Concluir / Responder'. Bug/suggest auto-fecha; outros pede texto."""
    query = update.callback_query
    ticket_id = int(query.data.split(":")[1])

    async with aiosqlite.connect(_DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM support_tickets WHERE id = ?", (ticket_id,)
        ) as cursor:
            ticket = await cursor.fetchone()

    if not ticket or ticket["status"] != "open":
        await query.answer("Este ticket já não está aberto.", show_alert=True)
        return

    cat = ticket["category"]
    uid = ticket["user_id"]
    bot = query.get_bot()

    if cat in ("bug", "suggest"):
        if cat == "bug":
            reply_text, reply_key, label = "Fix Automático", "ticket_admin_bug_fixed", "Bug corrigido"
        else:
            reply_text, reply_key, label = "Sugestão Implementada", "ticket_admin_suggest_impl", "Sugestão implementada"

        async with aiosqlite.connect(_DB_FILE) as db:
            await db.execute(
                "UPDATE support_tickets SET status = 'closed', closed_at = CURRENT_TIMESTAMP, admin_reply = ? WHERE id = ?",
                (reply_text, ticket_id)
            )
            await db.commit()

        try:
            await query.message.edit_text(
                query.message.text_html + f"\n\n<i>✅ {label}. Usuário notificado.</i>",
                reply_markup=None, parse_mode="HTML"
            )
        except Exception:
            pass
        await query.answer(f"{label}.")

        user_lang = "pt"
        async with aiosqlite.connect(_DB_FILE) as db:
            async with db.execute(
                "SELECT custom_language, language_code FROM users WHERE user_id = ?", (uid,)
            ) as cur:
                row = await cur.fetchone()
                if row:
                    user_lang = row[0] or row[1] or "pt"

        try:
            await bot.send_message(uid, _t_lang(user_lang, reply_key, ticket_id=ticket_id), parse_mode="HTML")
        except Exception:
            pass

    else:
        # Pede texto manual — armazena estado no user_data do ADMIN
        context.user_data["admin_replying_ticket"] = ticket_id
        context.user_data["admin_reply_target_user"] = uid

        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Cancelar", callback_data="admin_cancel_reply")
        ]])
        try:
            await query.message.edit_text(
                query.message.text_html + "\n\n<b>✏️ Digite a resposta para enviar a este usuário:</b>",
                parse_mode="HTML",
                reply_markup=kb
            )
        except Exception:
            pass
        await query.answer()
        # Armazena flag para o handler genérico de texto tratar a resposta
        context.user_data["admin_awaiting_reply"] = True


async def cb_admin_cancel_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer("Cancelado.")
    context.user_data.pop("admin_replying_ticket", None)
    context.user_data.pop("admin_reply_target_user", None)
    context.user_data.pop("admin_awaiting_reply", None)
    try:
        await query.message.edit_text(
            query.message.text_html + "\n<i>(Cancelado)</i>",
            reply_markup=None, parse_mode="HTML"
        )
    except Exception:
        pass


async def msg_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Tenta capturar a resposta do admin ao ticket.
    Retorna True se processou, False se não era uma resposta de ticket.
    Deve ser chamado no handle_text_input principal ANTES do roteamento normal,
    apenas quando o user é ADMIN_ID e context.user_data['admin_awaiting_reply'] está True.
    """
    if update.effective_user.id != _ADMIN_ID:
        return False
    if not context.user_data.get("admin_awaiting_reply"):
        return False

    admin_text = update.message.text.strip()
    if not admin_text:
        return True  # Consome mas não processa

    ticket_id = context.user_data.get("admin_replying_ticket")
    uid = context.user_data.get("admin_reply_target_user")

    if not ticket_id or not uid:
        await update.message.reply_text("❌ Erro: dados da sessão perdidos. Tente novamente.")
        context.user_data.pop("admin_awaiting_reply", None)
        return True

    async with aiosqlite.connect(_DB_FILE) as db:
        await db.execute(
            "UPDATE support_tickets SET status = 'closed', closed_at = CURRENT_TIMESTAMP, admin_reply = ? WHERE id = ?",
            (admin_text, ticket_id)
        )
        await db.commit()

    context.user_data.pop("admin_replying_ticket", None)
    context.user_data.pop("admin_reply_target_user", None)
    context.user_data.pop("admin_awaiting_reply", None)

    await update.message.reply_html(
        f"✅ Resposta enviada ao ticket #{ticket_id} do usuário <code>{uid}</code>."
    )

    user_lang = "pt"
    async with aiosqlite.connect(_DB_FILE) as db:
        async with db.execute(
            "SELECT custom_language, language_code FROM users WHERE user_id = ?", (uid,)
        ) as cur:
            row = await cur.fetchone()
            if row:
                user_lang = row[0] or row[1] or "pt"

    header = _t_lang(user_lang, "ticket_admin_reply_header", ticket_id=ticket_id)
    msg_user = f"{header}\n\n{html.escape(admin_text)}"
    try:
        await update.get_bot().send_message(uid, msg_user, parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(
            f"⚠️ Não foi possível notificar o usuário (pode ter bloqueado o bot). Erro: {e}"
        )
    return True


# ============================================================
# Fábrica do ConversationHandler
# ============================================================

def build_ticket_conversation_handler(ticket_text_keys: list[str]) -> ConversationHandler:
    """
    Constrói o ConversationHandler do sistema de tickets.
    ticket_text_keys: lista de todos os textos do botão em todos os idiomas.
    """
    import re
    # Se a lista estiver vazia, usa um padrão que nunca coincide para evitar capturar tudo
    if not ticket_text_keys or not any(ticket_text_keys):
        pattern = r"$.^" # Nunca coincide
    else:
        pattern = "|".join(re.escape(t) for t in ticket_text_keys if t)

    return ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.TEXT & filters.Regex(pattern),
                ticket_main_message
            ),
            CallbackQueryHandler(cb_ticket_main, pattern=r"^help_open_tickets$"),
        ],
        states={
            TICKET_MAIN: [
                CallbackQueryHandler(cb_ticket_new, pattern=r"^ticket:new$"),
                CallbackQueryHandler(cb_ticket_opened, pattern=r"^ticket:opened$"),
                CallbackQueryHandler(cb_ticket_closed, pattern=r"^ticket:closed$"),
                CallbackQueryHandler(cb_ticket_close, pattern=r"^ticket:close$"),
                CallbackQueryHandler(cb_ticket_cancel_user, pattern=r"^ticket_cancel:\d+$"),
                CallbackQueryHandler(cb_ticket_main, pattern=r"^ticket:main$"),
            ],
            TICKET_CHOOSE_CATEGORY: [
                CallbackQueryHandler(cb_ticket_category, pattern=r"^ticket_cat:"),
                CallbackQueryHandler(cb_ticket_main, pattern=r"^ticket:main$"),
            ],
            TICKET_WRITE_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, msg_ticket_text),
                CallbackQueryHandler(cb_ticket_main, pattern=r"^ticket:main$"),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(cb_ticket_close, pattern=r"^ticket:close$"),
        ],
        per_message=False,
        allow_reentry=True,
    )


def get_ticket_admin_handlers() -> list:
    """
    Retorna lista de CallbackQueryHandlers para o painel admin.
    Estes ficam fora do ConversationHandler de usuário.
    """
    return [
        CallbackQueryHandler(cb_admin_ticket_main, pattern=r"^admin_ticket:main$"),
        CallbackQueryHandler(cb_admin_pending, pattern=r"^admin_ticket:pending$"),
        CallbackQueryHandler(cb_admin_closed_list, pattern=r"^admin_ticket:closed$"),
        CallbackQueryHandler(cb_admin_close, pattern=r"^admin_ticket:close$"),
        CallbackQueryHandler(cb_admin_ignore, pattern=r"^admin_ticket_ignore:\d+$"),
        CallbackQueryHandler(cb_admin_done, pattern=r"^admin_ticket_done:\d+$"),
        CallbackQueryHandler(cb_admin_cancel_reply, pattern=r"^admin_cancel_reply$"),
    ]
