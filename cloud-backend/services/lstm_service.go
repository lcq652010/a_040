package services

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

	"phm-system/cloud-backend/models"
)

type LSTMService struct {
	baseURL    string
	httpClient *http.Client
}

func NewLSTMService(baseURL string) *LSTMService {
	return &LSTMService{
		baseURL: baseURL,
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

type PredictRULRequest struct {
	DeviceID   string              `json:"device_id"`
	DeviceType string              `json:"device_type"`
	RecentData []models.DeviceData `json:"recent_data"`
}

type PredictRULResponseInner struct {
	RULSteps    int     `json:"rul_steps"`
	RULMinutes  float64 `json:"rul_minutes"`
	RULHours    float64 `json:"rul_hours"`
	Confidence  float64 `json:"confidence"`
	HealthScore float64 `json:"health_score"`
	AlertLevel  string  `json:"alert_level"`
}

type PredictRULResponse struct {
	Success    bool                    `json:"success"`
	DeviceID   string                  `json:"device_id"`
	Prediction PredictRULResponseInner `json:"prediction"`
}

func (s *LSTMService) PredictRUL(deviceID, deviceType string, recentData []models.DeviceData) (*models.RULPrediction, error) {
	reqBody := PredictRULRequest{
		DeviceID:   deviceID,
		DeviceType: deviceType,
		RecentData: recentData,
	}

	jsonData, err := json.Marshal(reqBody)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	url := fmt.Sprintf("%s/api/predict/rul", s.baseURL)
	req, err := http.NewRequest("POST", url, bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")

	resp, err := s.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to call LSTM service: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("LSTM service returned status %d: %s", resp.StatusCode, string(body))
	}

	var respData PredictRULResponse
	if err := json.NewDecoder(resp.Body).Decode(&respData); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	prediction := &models.RULPrediction{
		DeviceID:    respData.DeviceID,
		RULSteps:    respData.Prediction.RULSteps,
		RULMinutes:  respData.Prediction.RULMinutes,
		RULHours:    respData.Prediction.RULHours,
		Confidence:  respData.Prediction.Confidence,
		HealthScore: respData.Prediction.HealthScore,
		AlertLevel:  respData.Prediction.AlertLevel,
		Timestamp:   time.Now(),
	}

	if prediction.DeviceID == "" {
		prediction.DeviceID = deviceID
	}

	return prediction, nil
}
