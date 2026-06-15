FROM golang:1.21-alpine AS builder

RUN apk add --no-cache git

WORKDIR /app

ENV GOPROXY=https://goproxy.cn,direct

COPY go.mod go.sum* ./
COPY . .

RUN go mod tidy
RUN CGO_ENABLED=0 GOOS=linux go build -o cloud-backend .

FROM alpine:3.19

RUN apk add --no-cache wget ca-certificates

WORKDIR /app

COPY --from=builder /app/cloud-backend .

EXPOSE 8080

CMD ["./cloud-backend"]
