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

type RootCauseService struct {
	baseURL    string
	httpClient *http.Client
}

func NewRootCauseService(baseURL string) *RootCauseService {
	return &RootCauseService{
		baseURL: baseURL,
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

type AnalyzeRootCauseRequest struct {
	DeviceID    string              `json:"device_id"`
	DeviceType  string              `json:"device_type"`
	AnomalyData []models.DeviceData `json:"anomaly_data"`
}

type AnalyzeRootCauseResponse struct {
	DeviceID     string              `json:"device_id"`
	DeviceType   string              `json:"device_type"`
	RootCauses   []models.RootCauseItem `json:"root_causes"`
	PrimaryCause string              `json:"primary_cause"`
	Severity     string              `json:"severity"`
	Suggestions  []string            `json:"suggestions"`
}

func (s *RootCauseService) AnalyzeRootCause(deviceID, deviceType string, anomalyData []models.DeviceData) (*models.RootCauseResult, error) {
	reqBody := AnalyzeRootCauseRequest{
		DeviceID:    deviceID,
		DeviceType:  deviceType,
		AnomalyData: anomalyData,
	}

	jsonData, err := json.Marshal(reqBody)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	url := fmt.Sprintf("%s/api/root-cause/analyze", s.baseURL)
	req, err := http.NewRequest("POST", url, bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")

	resp, err := s.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to call root cause service: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("root cause service returned status %d: %s", resp.StatusCode, string(body))
	}

	var respData AnalyzeRootCauseResponse
	if err := json.NewDecoder(resp.Body).Decode(&respData); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	result := &models.RootCauseResult{
		DeviceID:     respData.DeviceID,
		DeviceType:   respData.DeviceType,
		RootCauses:   respData.RootCauses,
		PrimaryCause: respData.PrimaryCause,
		Severity:     respData.Severity,
		Suggestions:  respData.Suggestions,
		Timestamp:    time.Now(),
	}

	if result.RootCauses == nil {
		result.RootCauses = []models.RootCauseItem{}
	}
	if result.Suggestions == nil {
		result.Suggestions = []string{}
	}

	return result, nil
}
