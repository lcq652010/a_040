package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"syscall"
	"time"

	"github.com/gin-gonic/gin"

	"phm-system/cloud-backend/config"
	"phm-system/cloud-backend/handlers"
	"phm-system/cloud-backend/services"
)

func main() {
	cfg, err := config.LoadConfig()
	if err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}

	log.Printf("Configuration loaded:")
	log.Printf("  InfluxDB URL: %s", cfg.InfluxDB.URL)
	log.Printf("  InfluxDB Org: %s", cfg.InfluxDB.Org)
	log.Printf("  InfluxDB Bucket: %s", cfg.InfluxDB.Bucket)
	log.Printf("  LSTM Service: %s", cfg.LSTMServiceURL)
	log.Printf("  Root Cause Service: %s", cfg.RootCauseServiceURL)
	log.Printf("  Server Port: %d", cfg.ServerPort)

	influxDBService, err := services.NewInfluxDBService(&cfg.InfluxDB)
	if err != nil {
		log.Printf("Warning: Failed to initialize InfluxDB service: %v", err)
		log.Println("Continuing without InfluxDB connection...")
	}
	if influxDBService != nil {
		defer influxDBService.Close()
	}

	webSocketHub := services.NewWebSocketHub()
	go webSocketHub.Run()

	lstmService := services.NewLSTMService(cfg.LSTMServiceURL)
	rootCauseService := services.NewRootCauseService(cfg.RootCauseServiceURL)

	dataHandler := handlers.NewDataHandler(
		influxDBService,
		webSocketHub,
		lstmService,
		rootCauseService,
	)

	r := setupRouter(cfg, dataHandler, webSocketHub)

	addr := fmt.Sprintf("0.0.0.0:%d", cfg.ServerPort)
	srv := &http.Server{
		Addr:         addr,
		Handler:      r,
		ReadTimeout:  60 * time.Second,
		WriteTimeout: 60 * time.Second,
		IdleTimeout:  120 * time.Second,
	}

	go func() {
		log.Printf("Starting cloud-backend server on %s", addr)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Failed to start server: %v", err)
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit
	log.Println("Shutting down server...")

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := srv.Shutdown(ctx); err != nil {
		log.Fatalf("Server forced to shutdown: %v", err)
	}

	log.Println("Server exited gracefully")
}

func setupRouter(cfg *config.Config, dataHandler *handlers.DataHandler, webSocketHub *services.WebSocketHub) *gin.Engine {
	gin.SetMode(gin.ReleaseMode)
	r := gin.Default()

	r.Use(corsMiddleware())

	r.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"status":  "ok",
			"service": "cloud-backend",
			"version": "1.0.0",
			"port":    cfg.ServerPort,
			"time":    time.Now().Format(time.RFC3339),
		})
	})

	api := r.Group("/api")
	{
		api.POST("/data", dataHandler.ReceiveData)
		api.GET("/devices", dataHandler.GetDeviceList)

		devices := api.Group("/devices/:id")
		{
			devices.GET("/data", dataHandler.GetDeviceData)
			devices.GET("/rul", dataHandler.GetDeviceRUL)
			devices.POST("/root-cause", dataHandler.AnalyzeRootCause)
		}
	}

	r.GET("/api/ws", webSocketHub.HandleWebSocket)

	r.GET("/", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"service": "PHM Cloud Backend",
			"version": "1.0.0",
			"endpoints": []string{
				"GET  /health",
				"POST /api/data",
				"GET  /api/devices",
				"GET  /api/devices/:id/data?limit=100",
				"GET  /api/devices/:id/rul",
				"POST /api/devices/:id/root-cause",
				"GET  /api/ws",
			},
		})
	})

	return r
}

func corsMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		origin := c.Request.Header.Get("Origin")
		if origin == "" {
			origin = "*"
		}

		c.Writer.Header().Set("Access-Control-Allow-Origin", origin)
		c.Writer.Header().Set("Access-Control-Allow-Credentials", "true")
		c.Writer.Header().Set("Access-Control-Allow-Headers",
			"Content-Type, Content-Length, Accept-Encoding, X-CSRF-Token, Authorization, accept, origin, Cache-Control, X-Requested-With")
		c.Writer.Header().Set("Access-Control-Allow-Methods",
			"GET, POST, PUT, PATCH, DELETE, OPTIONS, HEAD")
		c.Writer.Header().Set("Access-Control-Max-Age", "86400")
		c.Writer.Header().Set("Access-Control-Expose-Headers",
			"Content-Length, Content-Type, Authorization")

		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(http.StatusNoContent)
			return
		}

		c.Next()
	}
}

func init() {
	portEnv := os.Getenv("PORT")
	if portEnv != "" && os.Getenv("SERVER_PORT") == "" {
		if _, err := strconv.Atoi(portEnv); err == nil {
			os.Setenv("SERVER_PORT", portEnv)
		}
	}
}
