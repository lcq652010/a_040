package handlers

import (
	"log"
	"net/http"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"

	"phm-system/cloud-backend/models"
	"phm-system/cloud-backend/services"
)

type DataHandler struct {
	influxDBService    *services.InfluxDBService
	webSocketHub       *services.WebSocketHub
	lstmService        *services.LSTMService
	rootCauseService   *services.RootCauseService
}

func NewDataHandler(
	influxDBService *services.InfluxDBService,
	webSocketHub *services.WebSocketHub,
	lstmService *services.LSTMService,
	rootCauseService *services.RootCauseService,
) *DataHandler {
	return &DataHandler{
		influxDBService:  influxDBService,
		webSocketHub:     webSocketHub,
		lstmService:      lstmService,
		rootCauseService: rootCauseService,
	}
}

func (h *DataHandler) ReceiveData(c *gin.Context) {
	var data models.DeviceData
	if err := c.ShouldBindJSON(&data); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid JSON: " + err.Error()})
		return
	}

	if data.Timestamp.IsZero() {
		data.Timestamp = time.Now()
	}

	if err := h.influxDBService.WriteDeviceData(&data); err != nil {
		log.Printf("Failed to write device data: %v", err)
	}

	h.webSocketHub.BroadcastDeviceUpdate(&data)

	if data.IsAnomaly {
		alert := &models.AlertMessage{
			DeviceID:   data.DeviceID,
			DeviceType: data.DeviceType,
			AlertType:  "anomaly_detected",
			Level:      determineAlertLevel(data.AnomalyScore),
			Message:    "异常数据检测到，异常分数: " + strconv.FormatFloat(data.AnomalyScore, 'f', 2, 64),
			Timestamp:  time.Now(),
		}
		h.webSocketHub.BroadcastAlert(alert)
	}

	go h.processDeviceAnalysis(data)

	c.JSON(http.StatusOK, gin.H{
		"status":    "success",
		"device_id": data.DeviceID,
		"timestamp": data.Timestamp,
	})
}

func (h *DataHandler) processDeviceAnalysis(data models.DeviceData) {
	recentData, err := h.influxDBService.QueryRecentData(data.DeviceID, 20)
	if err != nil {
		log.Printf("Failed to query recent data for device %s: %v", data.DeviceID, err)
	} else {
		prediction, err := h.lstmService.PredictRUL(data.DeviceID, data.DeviceType, recentData)
		if err != nil {
			log.Printf("Failed to predict RUL for device %s: %v", data.DeviceID, err)
		} else {
			h.webSocketHub.BroadcastRULUpdate(prediction)
		}
	}

	anomalyData := []models.DeviceData{data}
	if len(recentData) > 0 {
		anomalyData = append(anomalyData, recentData...)
	}

	rootCause, err := h.rootCauseService.AnalyzeRootCause(data.DeviceID, data.DeviceType, anomalyData)
	if err != nil {
		log.Printf("Failed to analyze root cause for device %s: %v", data.DeviceID, err)
	} else {
		h.webSocketHub.BroadcastRootCause(rootCause)
	}
}

func determineAlertLevel(score float64) string {
	switch {
	case score >= 0.9:
		return "critical"
	case score >= 0.7:
		return "warning"
	case score >= 0.5:
		return "notice"
	default:
		return "info"
	}
}

func (h *DataHandler) GetDeviceList(c *gin.Context) {
	devices := []models.DeviceInfo{
		{
			DeviceID:    "AC-001",
			DeviceType:  "air_compressor",
			DeviceName:  "空压机",
			Location:    "动力车间-A区",
			Status:      "running",
			InstallDate: "2023-06-15",
		},
		{
			DeviceID:    "CP-001",
			DeviceType:  "centrifugal_pump",
			DeviceName:  "离心泵",
			Location:    "供水车间-1号泵站",
			Status:      "running",
			InstallDate: "2023-03-20",
		},
		{
			DeviceID:    "FN-001",
			DeviceType:  "fan",
			DeviceName:  "风机",
			Location:    "通风车间-主风机房",
			Status:      "running",
			InstallDate: "2022-11-08",
		},
		{
			DeviceID:    "CV-001",
			DeviceType:  "conveyor",
			DeviceName:  "传送带",
			Location:    "装配车间-2号线",
			Status:      "running",
			InstallDate: "2024-01-12",
		},
		{
			DeviceID:    "CT-001",
			DeviceType:  "cooling_tower",
			DeviceName:  "冷却塔",
			Location:    "冷却系统-室外平台",
			Status:      "running",
			InstallDate: "2023-09-30",
		},
	}

	c.JSON(http.StatusOK, gin.H{
		"devices": devices,
		"total":   len(devices),
	})
}

func (h *DataHandler) GetDeviceData(c *gin.Context) {
	deviceID := c.Param("id")
	if deviceID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "device id is required"})
		return
	}

	limitStr := c.DefaultQuery("limit", "100")
	limit, err := strconv.Atoi(limitStr)
	if err != nil || limit <= 0 {
		limit = 100
	}

	data, err := h.influxDBService.QueryRecentData(deviceID, limit)
	if err != nil {
		log.Printf("Failed to query device data: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to query device data"})
		return
	}

	if data == nil {
		data = []models.DeviceData{}
	}

	c.JSON(http.StatusOK, gin.H{
		"device_id": deviceID,
		"count":     len(data),
		"data":      data,
	})
}

func (h *DataHandler) GetDeviceRUL(c *gin.Context) {
	deviceID := c.Param("id")
	if deviceID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "device id is required"})
		return
	}

	deviceType := c.DefaultQuery("device_type", "pump")

	recentData, err := h.influxDBService.QueryRecentData(deviceID, 20)
	if err != nil {
		log.Printf("Failed to query recent data: %v", err)
		recentData = []models.DeviceData{}
	}

	prediction, err := h.lstmService.PredictRUL(deviceID, deviceType, recentData)
	if err != nil {
		log.Printf("Failed to predict RUL: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to predict RUL: " + err.Error()})
		return
	}

	h.webSocketHub.BroadcastRULUpdate(prediction)

	c.JSON(http.StatusOK, prediction)
}

func (h *DataHandler) AnalyzeRootCause(c *gin.Context) {
	deviceID := c.Param("id")
	if deviceID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "device id is required"})
		return
	}

	var req struct {
		DeviceType string              `json:"device_type"`
		AnomalyData []models.DeviceData `json:"anomaly_data"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		req.DeviceType = c.DefaultQuery("device_type", "pump")
	}

	if req.AnomalyData == nil || len(req.AnomalyData) == 0 {
		recentData, err := h.influxDBService.QueryRecentData(deviceID, 10)
		if err == nil {
			req.AnomalyData = recentData
		}
	}

	if req.AnomalyData == nil {
		req.AnomalyData = []models.DeviceData{}
	}

	result, err := h.rootCauseService.AnalyzeRootCause(deviceID, req.DeviceType, req.AnomalyData)
	if err != nil {
		log.Printf("Failed to analyze root cause: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to analyze root cause: " + err.Error()})
		return
	}

	h.webSocketHub.BroadcastRootCause(result)

	c.JSON(http.StatusOK, result)
}
