package models

import "time"

type DeviceData struct {
	DeviceID         string    `json:"device_id"`
	DeviceType       string    `json:"device_type"`
	Timestamp        time.Time `json:"timestamp"`
	Vibration        float64   `json:"vibration"`
	Temperature      float64   `json:"temperature"`
	Current          float64   `json:"current"`
	Speed            float64   `json:"speed"`
	AcousticEmission float64   `json:"acoustic_emission"`
	IsAnomaly        bool      `json:"is_anomaly"`
	AnomalyScore     float64   `json:"anomaly_score"`
}

type RULPrediction struct {
	DeviceID    string    `json:"device_id"`
	RULSteps    int       `json:"rul_steps"`
	RULMinutes  float64   `json:"rul_minutes"`
	RULHours    float64   `json:"rul_hours"`
	Confidence  float64   `json:"confidence"`
	HealthScore float64   `json:"health_score"`
	AlertLevel  string    `json:"alert_level"`
	Timestamp   time.Time `json:"timestamp"`
}

type RootCauseItem struct {
	Parameter   string  `json:"parameter"`
	Contribution float64 `json:"contribution"`
	Description string  `json:"description"`
}

type RootCauseResult struct {
	DeviceID    string          `json:"device_id"`
	DeviceType  string          `json:"device_type"`
	RootCauses  []RootCauseItem `json:"root_causes"`
	PrimaryCause string         `json:"primary_cause"`
	Severity    string          `json:"severity"`
	Suggestions []string        `json:"suggestions"`
	Timestamp   time.Time       `json:"timestamp"`
}

type BatchWebSocketMessage struct {
	Type      string                   `json:"type"`
	Items     []map[string]interface{} `json:"items"`
	Count     int                      `json:"count"`
	Timestamp time.Time                `json:"timestamp"`
}

type WebSocketMessage struct {
	Type      string      `json:"type"`
	Data      interface{} `json:"data"`
	Timestamp time.Time   `json:"timestamp"`
}

type AlertMessage struct {
	DeviceID   string    `json:"device_id"`
	DeviceType string    `json:"device_type"`
	AlertType  string    `json:"alert_type"`
	Level      string    `json:"level"`
	Message    string    `json:"message"`
	Timestamp  time.Time `json:"timestamp"`
}

type DeviceInfo struct {
	DeviceID    string `json:"device_id"`
	DeviceType  string `json:"device_type"`
	DeviceName  string `json:"device_name"`
	Location    string `json:"location"`
	Status      string `json:"status"`
	InstallDate string `json:"install_date"`
}
