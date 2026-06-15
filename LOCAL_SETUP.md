# PHM System - Local Development Setup Guide

## 1. Prerequisites

- Python 3.7+
- Go 1.21+
- Node.js 18+
- InfluxDB 2.7+
- (Optional) Docker Desktop

## 2. Service Ports

| Service | Port | Description |
|---------|------|-------------|
| InfluxDB | 8086 | Time-series database |
| LSTM Service | 5000 | Python Flask - RUL prediction |
| Root Cause Service | 5001 | Python Flask - Root cause analysis |
| Cloud Backend | 8080 | Go Gin - API gateway + WebSocket |
| Frontend | 5173 (dev) / 80 | Vue + ECharts dashboard |

## 3. Step-by-Step Startup

### Step 1: Install InfluxDB

**Option A: Docker (recommended)**
```bash
docker run -d \
  --name phm-influxdb \
  -p 8086:8086 \
  -e DOCKER_INFLUXDB_INIT_MODE=setup \
  -e DOCKER_INFLUXDB_INIT_USERNAME=admin \
  -e DOCKER_INFLUXDB_INIT_PASSWORD=password123 \
  -e DOCKER_INFLUXDB_INIT_ORG=phm-org \
  -e DOCKER_INFLUXDB_INIT_BUCKET=device_data \
  -e DOCKER_INFLUXDB_INIT_ADMIN_TOKEN=phm-token-12345 \
  influxdb:2.7-alpine
```

**Option B: Local install**
- Download from https://portal.influxdata.com/downloads/
- Start `influxd`
- Run initial setup with `influx setup`

### Step 2: Configure Environment

Create `.env` file in project root (already provided):
```
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=phm-token-12345
INFLUXDB_ORG=phm-org
INFLUXDB_BUCKET=device_data
LSTM_SERVICE_URL=http://localhost:5000
ROOT_CAUSE_SERVICE_URL=http://localhost:5001
FRONTEND_PORT=80
```

### Step 3: Start LSTM Service

```bash
cd lstm-service
pip install -r requirements.txt
python main.py
```
Verify: `curl http://localhost:5000/api/health`

Note: TensorFlow is required for LSTM predictions.
- Without TensorFlow: service runs but returns mock predictions
- With TensorFlow: full LSTM + transfer learning

### Step 4: Start Root Cause Service

```bash
cd root-cause-service
pip install -r requirements.txt
python main.py
```
Verify: `curl http://localhost:5001/health`

### Step 5: Start Cloud Backend (Go)

```bash
cd cloud-backend
go mod tidy
go build -o cloud-backend.exe .
./cloud-backend.exe
```
Verify: `curl http://localhost:8080/health`

### Step 6: Start Edge Nodes (5 devices)

```bash
cd edge-node
pip install -r requirements.txt
python main.py
```
This starts 5 simulated devices (AC-001 through CT-001) that collect data every 10 seconds and upload anomalies.

### Step 7: Start Frontend (dev mode)

```bash
cd frontend
npm install
npm run dev
```
Open: http://localhost:5173

## 4. Verify Full Data Flow

1. Edge nodes collect data every 10 seconds
2. Isolation Forest detects anomalies locally
3. Anomalous data uploads to cloud backend
4. Backend stores in InfluxDB
5. Backend calls LSTM service for RUL prediction
6. Backend calls root cause service for analysis
7. Results pushed via WebSocket (with 50ms frame merging)
8. Frontend renders dashboard with rAF throttling

## 5. Run E2E Tests

```bash
pip install requests
python tests/e2e_test.py --skip-start --skip-cleanup
```

## 6. Run Unit Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

## 7. Docker Alternative

For one-click startup with all services:
```bash
docker compose up -d --build
docker compose logs -f
```

## 8. Troubleshooting

### InfluxDB connection errors
- Check InfluxDB is running: `curl http://localhost:8086/health`
- Verify token in .env matches
- Check bucket exists: `influx bucket list`

### Go build errors
- Ensure Go 1.21+: `go version`
- Set GOPROXY in China: `$env:GOPROXY = "https://goproxy.cn,direct"`
- Run `go mod tidy` to download dependencies

### Frontend build errors
- Ensure Node.js 18+: `node -v`
- Delete node_modules and reinstall: `rm -rf node_modules && npm install`

### Python import errors
- Install dependencies: `pip install -r requirements.txt`
- Check PYTHONPATH if running from different directory
