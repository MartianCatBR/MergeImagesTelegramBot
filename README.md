<div align="center">

# 🖼️ MergeImages Telegram Bot

### Image and document tools inside Telegram

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-26A5E4?style=flat-square&logo=telegram&logoColor=white)](https://core.telegram.org/bots)
[![Mini App](https://img.shields.io/badge/Telegram-Mini%20App-26A5E4?style=flat-square&logo=telegram&logoColor=white)](miniapp/)
[![Languages](https://img.shields.io/badge/Languages-8%20supported-6C5CE7?style=flat-square)](#supported-languages)

[**📜 Privacy policy**](PRIVACY_POLICY.md) &nbsp;•&nbsp;
[**🔍 Privacy audit**](PRIVACY_OPEN_SOURCE_AUDIT.md)

</div>

---

## ✨ What it does

MergeImages handles common image and document tasks directly in Telegram:

- Merge images vertically, horizontally, or as a grid
- Convert and compress images
- Process PDF and DOCX files
- Extract text with OCR
- Remove image and document metadata
- Create GIFs, memes, QR codes, ZIP files, and stickers
- Edit images through a Telegram Mini App
- Open support tickets and view personal usage statistics

The bot has multilingual menus and messages, with support for eight languages.

## ⚡ Quick start

### Requirements

- Python 3.11 or newer
- Tesseract OCR
- A Telegram bot token
- Go, if you plan to run the Mini App

### Install

```bash
git clone https://github.com/MartianCatBR/MergeImagesTelegramBot.git
cd MergeImagesTelegramBot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Install Tesseract separately and make sure it is available in your system PATH.

### Configure

Set the required environment variables:

```env
TELEGRAM_TOKEN=your_telegram_bot_token
ADMIN_ID=your_telegram_user_id
```

For the Mini App, also configure the allowed origin:

```env
MINIAPP_ALLOWED_ORIGINS=https://your-miniapp-domain.example
```

### Run

```bash
source venv/bin/activate
python3 UnifyImages.py
```

The bot creates its local database and runtime directories when needed.

## 📱 Mini App

The Mini App source is in [`miniapp/`](miniapp/). From that directory:

```bash
cd miniapp
gofmt -w main.go
go test ./...
go run .
```

Set `MINIAPP_ALLOWED_ORIGINS` to the real origin used by the Mini App. The server validates Telegram `initData`; CORS alone is not authentication.

## 🛡️ Privacy

The bot keeps basic usage metrics for service administration. General activity logs do not need to store usernames. Support tickets are handled differently because the user opens them to request help: ticket text, public name, username, and Telegram ID may be shown to the administrator.

Visual search asks for confirmation before sending an image to external services such as Telegra.ph, Catbox.moe, and Google Lens. Those services have their own privacy and retention policies.

Do not commit tokens, `.env` files, databases, logs, backups, virtual environments, or production data. The repository includes a `.gitignore` for local files and generated data.

Privacy policies are available in:

- [English](privacy_policy_en.md)
- [Portuguese](privacy_policy_pt.md)
- [Spanish](privacy_policy_es.md)
- [French](privacy_policy_fr.md)
- [Italian](privacy_policy_it.md)
- [Arabic](privacy_policy_ar.md)
- [Russian](privacy_policy_ru.md)
- [Ukrainian](privacy_policy_uk.md)

## 🌍 Supported languages

- 🇺🇸 English
- 🇧🇷 Português
- 🇪🇸 Español
- 🇫🇷 Français
- 🇮🇹 Italiano
- 🇸🇦 العربية
- 🇷🇺 Русский
- 🇺🇦 Українська

## 📬 Support and contributions

Bug reports, suggestions, and code contributions are welcome through GitHub Issues and pull requests.

Before opening an issue, please avoid including bot tokens, database files, private user content, or other sensitive information.

## 📄 License

No license file has been added yet. Add a license before presenting the repository as reusable open-source software.

</div>
