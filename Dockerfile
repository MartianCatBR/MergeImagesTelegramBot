FROM python:3.14-slim

# Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# Argumento para forçar a invalidação do cache do Docker build se necessário
ARG CACHEBUST=2026-09-17

# Instala dependências do sistema necessárias para a biblioteca Pillow (processamento de imagem)
# - libjpeg62-turbo-dev: para suporte a JPEG
# - zlib1g-dev: para suporte a PNG
# - libwebp-dev: para suporte a WEBP
# - libtiff5-dev: para suporte a TIFF
# - tesseract-ocr e pacotes de idioma: para funcionalidade de OCR
# --no-install-recommends reduz o tamanho da imagem
RUN apt-get update && apt-get install -y --no-install-recommends \
  curl libjpeg62-turbo-dev zlib1g-dev libwebp-dev libtiff5-dev libgl1 libglib2.0-0 \
  tesseract-ocr \
  libreoffice-writer libreoffice-calc libreoffice-impress && \
  mkdir -p /usr/share/tesseract-ocr/5/tessdata /usr/share/tessdata && \
  for lang in eng por spa ita rus ara fra ukr osd; do \
  curl -sSL -o /usr/share/tesseract-ocr/5/tessdata/${lang}.traineddata \
  https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/${lang}.traineddata && \
  cp /usr/share/tesseract-ocr/5/tessdata/${lang}.traineddata /usr/share/tessdata/${lang}.traineddata; \
  done && \
  rm -rf /var/lib/apt/lists/*

# Copia o binário do uv a partir da imagem oficial (escrito em Rust, ~10x mais rápido que pip)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copia o arquivo de requisitos e instala as dependências via uv
# --system: instala no Python do sistema (sem venv, igual ao comportamento anterior do pip)
# --no-cache: mantém a imagem menor
COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

# Copia o código fonte do bot para o contêiner
COPY . .

# Comando para iniciar o bot
CMD ["python", "UnifyImages.py"]
