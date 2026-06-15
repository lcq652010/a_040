package config

import (
	"os"
	"strconv"

	"github.com/joho/godotenv"
)

type InfluxDBConfig struct {
	URL    string
	Token  string
	Org    string
	Bucket string
}

type Config struct {
	InfluxDB           InfluxDBConfig
	ServerPort         int
	LSTMServiceURL     string
	RootCauseServiceURL string
}

func LoadConfig() (*Config, error) {
	_ = godotenv.Load()

	cfg := &Config{
		InfluxDB: InfluxDBConfig{
			URL:    getEnv("INFLUXDB_URL", "http://influxdb:8086"),
			Token:  getEnv("INFLUXDB_TOKEN", "my-token"),
			Org:    getEnv("INFLUXDB_ORG", "phm-org"),
			Bucket: getEnv("INFLUXDB_BUCKET", "phm-data"),
		},
		ServerPort:         getEnvAsInt("SERVER_PORT", 8080),
		LSTMServiceURL:     getEnv("LSTM_SERVICE_URL", "http://lstm-service:5000"),
		RootCauseServiceURL: getEnv("ROOT_CAUSE_SERVICE_URL", "http://root-cause-service:5001"),
	}

	return cfg, nil
}

func getEnv(key, defaultValue string) string {
	if value, exists := os.LookupEnv(key); exists {
		return value
	}
	return defaultValue
}

func getEnvAsInt(key string, defaultValue int) int {
	if value, exists := os.LookupEnv(key); exists {
		if intVal, err := strconv.Atoi(value); err == nil {
			return intVal
		}
	}
	return defaultValue
}
