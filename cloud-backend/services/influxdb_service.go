package services

import (
	"context"
	"fmt"
	"time"

	"github.com/influxdata/influxdb-client-go/v2"
	"github.com/influxdata/influxdb-client-go/v2/api"
	"github.com/influxdata/influxdb-client-go/v2/api/write"
	"github.com/influxdata/influxdb-client-go/v2/domain"

	"phm-system/cloud-backend/config"
	"phm-system/cloud-backend/models"
)

type InfluxDBService struct {
	client       influxdb2.Client
	writeAPI     api.WriteAPIBlocking
	queryAPI     api.QueryAPI
	org          string
	bucket       string
}

func NewInfluxDBService(cfg *config.InfluxDBConfig) (*InfluxDBService, error) {
	client := influxdb2.NewClient(cfg.URL, cfg.Token)

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	orgAPI := client.OrganizationsAPI()
	orgs, err := orgAPI.FindOrgsByName(ctx, cfg.Org)
	if err != nil || len(orgs) == 0 {
		_, createErr := orgAPI.CreateOrgWithName(ctx, cfg.Org)
		if createErr != nil {
		}
	}

	bucketAPI := client.BucketsAPI()
	orgResult, _ := orgAPI.FindOrgByName(ctx, cfg.Org)
	var orgID string
	if orgResult != nil {
		orgID = *orgResult.Id
	}

	buckets, err := bucketAPI.FindBucketsByName(ctx, cfg.Bucket)
	if err != nil || len(buckets) == 0 {
		retentionDays := 30
		_, createErr := bucketAPI.CreateBucketWithName(ctx, orgResult, cfg.Bucket, domain.RetentionRule{
			EverySeconds: int64(retentionDays * 24 * 3600),
			Type:         domain.RetentionRuleTypeExpire,
		})
		if createErr != nil {
		}
		_ = orgID
	}

	service := &InfluxDBService{
		client:   client,
		writeAPI: client.WriteAPIBlocking(cfg.Org, cfg.Bucket),
		queryAPI: client.QueryAPI(cfg.Org),
		org:      cfg.Org,
		bucket:   cfg.Bucket,
	}

	return service, nil
}

func (s *InfluxDBService) WriteDeviceData(data *models.DeviceData) error {
	point := write.NewPointWithMeasurement("device_data").
		AddTag("device_id", data.DeviceID).
		AddTag("device_type", data.DeviceType).
		AddField("vibration", data.Vibration).
		AddField("temperature", data.Temperature).
		AddField("current", data.Current).
		AddField("speed", data.Speed).
		AddField("acoustic_emission", data.AcousticEmission).
		AddField("is_anomaly", data.IsAnomaly).
		AddField("anomaly_score", data.AnomalyScore).
		SetTime(data.Timestamp)

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	return s.writeAPI.WritePoint(ctx, point)
}

func (s *InfluxDBService) QueryRecentData(deviceID string, limit int) ([]models.DeviceData, error) {
	fluxQuery := fmt.Sprintf(`
		from(bucket: "%s")
			|> range(start: -7d)
			|> filter(fn: (r) => r._measurement == "device_data" and r.device_id == "%s")
			|> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
			|> sort(columns: ["_time"], desc: true)
			|> limit(n: %d)
	`, s.bucket, deviceID, limit)

	return s.executeQuery(fluxQuery)
}

func (s *InfluxDBService) QueryDeviceHistory(deviceID string, duration string) ([]models.DeviceData, error) {
	fluxQuery := fmt.Sprintf(`
		from(bucket: "%s")
			|> range(start: -%s)
			|> filter(fn: (r) => r._measurement == "device_data" and r.device_id == "%s")
			|> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
			|> sort(columns: ["_time"], desc: false)
	`, s.bucket, duration, deviceID)

	return s.executeQuery(fluxQuery)
}

func (s *InfluxDBService) executeQuery(query string) ([]models.DeviceData, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	result, err := s.queryAPI.Query(ctx, query)
	if err != nil {
		return nil, err
	}

	var dataList []models.DeviceData

	for result.Next() {
		record := result.Record()

		item := models.DeviceData{
			DeviceID:   record.ValueByKey("device_id").(string),
			DeviceType: record.ValueByKey("device_type").(string),
			Timestamp:  record.Time(),
		}

		if val, ok := record.ValueByKey("vibration").(float64); ok {
			item.Vibration = val
		}
		if val, ok := record.ValueByKey("temperature").(float64); ok {
			item.Temperature = val
		}
		if val, ok := record.ValueByKey("current").(float64); ok {
			item.Current = val
		}
		if val, ok := record.ValueByKey("speed").(float64); ok {
			item.Speed = val
		}
		if val, ok := record.ValueByKey("acoustic_emission").(float64); ok {
			item.AcousticEmission = val
		}
		if val, ok := record.ValueByKey("is_anomaly").(bool); ok {
			item.IsAnomaly = val
		}
		if val, ok := record.ValueByKey("anomaly_score").(float64); ok {
			item.AnomalyScore = val
		}

		dataList = append(dataList, item)
	}

	if result.Err() != nil {
		return dataList, result.Err()
	}

	return dataList, nil
}

func (s *InfluxDBService) Close() {
	if s.client != nil {
		s.client.Close()
	}
}
