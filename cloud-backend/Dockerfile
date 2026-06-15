FROM golang:1.21-alpine AS builder

WORKDIR /app

COPY go.mod ./
RUN go mod tidy

COPY . .

RUN CGO_ENABLED=0 GOOS=linux go build -o cloud-backend .

FROM alpine:3.19

RUN apk add --no-cache wget ca-certificates

WORKDIR /app

COPY --from=builder /app/cloud-backend .

EXPOSE 8080

CMD ["./cloud-backend"]
