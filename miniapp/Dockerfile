# Dockerfile para o Mini App (Backend Go + Frontend)
# Estágio de Build
FROM golang:1.27-alpine AS builder

WORKDIR /app

# Instala gcc/musl necessários para compilar sqlite3 via CGO
RUN apk add --no-cache gcc musl-dev

# Copia os arquivos de dependência
COPY go.mod go.sum ./
RUN go mod download

# Copia o restante do código
COPY . .

# Compila o binário com CGO, necessário para github.com/mattn/go-sqlite3
RUN CGO_ENABLED=1 GOOS=linux go build -o miniapp-server main.go

# Estágio de Execução (Imagem super leve)
FROM alpine:latest
RUN apk --no-cache add ca-certificates tzdata

WORKDIR /app

# Copia o binário do estágio de build
COPY --from=builder /app/miniapp-server .

# Copia a pasta do frontend (public)
COPY --from=builder /app/public ./public

# Define a porta padrão
ENV PORT=3000

# Expõe a porta
EXPOSE 3000

# Comando para iniciar o servidor
CMD ["./miniapp-server"]
