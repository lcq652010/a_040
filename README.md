# PHM设备故障预测与健康管理系统

## 系统概述

本系统为工业车间设计的**设备故障预测与健康管理（Prognostics and Health Management, PHM）系统**，实现从边缘数据采集到云端智能分析的完整闭环。

## 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                            前端 (Vue + ECharts)                     │
│  设备健康仪表盘 | 振动频谱图 | RUL趋势图 | 告警面板 | 根因分析      │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ WebSocket / HTTP
┌──────────────────────────────▼──────────────────────────────────────┐
│                        云端后端 (Go + Gin)                          │
│  HTTP接收 | InfluxDB存储 | WebSocket推送 | LSTM调用 | 根因分析调度   │
└──────────┬───────────────────────┬──────────────────┬───────────────┘
           │                       │                  │
┌──────────▼──────────┐  ┌────────▼────────┐  ┌──────▼─────────────┐
│   InfluxDB          │  │  LSTM服务       │  │  根因分析服务      │
│   时序数据库        │  │  RUL剩余寿命    │  │  历史案例匹配      │
│   (v2.7)            │  │  预测 (Python)  │  │  (Python)         │
└─────────────────────┘  └─────────────────┘  └────────────────────┘
           ▲
           │ HTTP (异常数据上传)
┌──────────┴──────────────────────────────────────────────────────────┐
│                      边缘节点 (Python)                               │
│  空压机 | 离心泵 | 风机 | 传送带 | 冷却塔  (5台设备模拟)             │
│  每10秒采集 + 孤立森林异常检测 + 异常数据云端上传                    │
└─────────────────────────────────────────────────────────────────────┘
```

## 功能特性

### 1. 边缘节点层
- **5台关键设备模拟**：空压机、离心泵、风机、传送带、冷却塔
- **多维度数据采集**：振动(mm/s)、温度(℃)、电流(A)、转速(rpm)、声发射(dB)
- **实时异常检测**：轻量化孤立森林(Isolation Forest)模型，边缘侧实时判断
- **采集频率**：每10秒一次，异常时才上传原始数据（节省带宽）

### 2. 云端数据层
- **数据接收**：Go + Gin HTTP接口，高并发处理
- **时序存储**：InfluxDB 2.7，优化时序数据写入与查询
- **实时推送**：WebSocket，毫秒级推送到前端

### 3. 智能分析层
- **剩余寿命预测(RUL)**：LSTM深度学习模型，基于滑动窗口时间序列预测
- **故障根因分析**：基于22+历史案例库的余弦相似度+加权欧氏距离匹配
- **健康度评分**：多维度融合的设备健康指数

### 4. 前端可视化
- **设备健康仪表盘**：实时健康度、RUL剩余寿命
- **振动频谱分析**：FFT频谱图 + 5项指标实时趋势
- **RUL趋势预测**：历史曲线 + 预测区间 + 告警阈值
- **告警管理**：三级告警（严重/警告/注意）
- **根因分析展示**：Top3匹配原因 + 解决方案建议

## 快速启动

### 环境要求
- Docker Desktop 4.0+ (需开启WSL2后端)
- 至少 8GB 内存（LSTM训练需要较大内存）
- 至少 20GB 可用磁盘空间
- Windows 10/11 或 Linux/MacOS

### 一键启动（推荐）

**Windows:**
```powershell
# 双击运行或在PowerShell中执行
.\start.bat
```

**Linux/MacOS:**
```bash
chmod +x start.sh
./start.sh
```

### 手动Docker Compose启动

```bash
# 构建并启动所有服务
docker compose up -d --build

# 查看服务状态
docker compose ps

# 查看LSTM训练日志（首次启动需要较长时间）
docker compose logs -f lstm-service

# 查看边缘节点数据采集日志
docker compose logs -f edge-node
```

### 停止服务

```bash
# 停止但保留数据
docker compose down

# 停止并清除所有数据（慎用！）
docker compose down -v
```

## 访问地址

启动完成后，通过以下地址访问各模块：

| 模块 | 地址 | 账号/说明 |
|------|------|-----------|
| **前端可视化** | http://localhost | 无需登录 |
| **InfluxDB管理** | http://localhost:8086 | admin / admin123 |
| **Go后端API** | http://localhost:8080/health | 健康检查 |
| **LSTM服务API** | http://localhost:5000/api/health | 健康检查 |
| **根因分析API** | http://localhost:5001/health | 健康检查 |

## API接口文档

### 云端后端 (Go :8080)

#### 1. 接收边缘节点数据
```http
POST /api/data
Content-Type: application/json

{
  "device_id": "AC-001",
  "device_type": "air_compressor",
  "timestamp": "2024-06-15T10:30:00Z",
  "vibration": 4.56,
  "temperature": 68.2,
  "current": 22.5,
  "speed": 2890,
  "acoustic_emission": 78.3,
  "is_anomaly": true,
  "anomaly_score": -0.78
}
```

#### 2. 获取设备列表
```http
GET /api/devices
```

#### 3. 查询设备历史数据
```http
GET /api/devices/{device_id}/data?limit=100
```

#### 4. 触发RUL预测
```http
GET /api/devices/{device_id}/rul
```

#### 5. 触发根因分析
```http
POST /api/devices/{device_id}/root-cause
Content-Type: application/json

{
  "anomaly_data": {
    "vibration": 6.5,
    "temperature": 82.0,
    "current": 28.5,
    "speed": 2650,
    "acoustic_emission": 85.0
  }
}
```

#### 6. WebSocket实时推送
```
ws://localhost:8080/api/ws
```

消息类型：
- `device_update` - 设备数据更新
- `rul_update` - RUL预测结果更新
- `alert` - 告警消息
- `root_cause` - 根因分析结果

### LSTM预测服务 (Python :5000)

```http
POST /api/predict/rul
Content-Type: application/json

{
  "device_id": "AC-001",
  "device_type": "compressor",
  "recent_data": [
    {"vibration": 1.2, "temperature": 45, "current": 10, "speed": 1500, "acoustic": 55},
    ...
  ]
}
```

### 根因分析服务 (Python :5001)

```http
POST /api/root-cause/analyze
Content-Type: application/json

{
  "device_id": "CP-001",
  "device_type": "pump",
  "anomaly_data": {
    "vibration": 6.8,
    "temperature": 78.5,
    "current": 26.3,
    "speed": 1420,
    "acoustic": 82.0
  }
}
```

## 设备参数配置

### 5台关键设备正常运行范围

| 设备 | 设备ID | 振动(mm/s) | 温度(℃) | 电流(A) | 转速(rpm) | 声发射(dB) |
|------|--------|-----------|---------|---------|-----------|-----------|
| 空压机 | AC-001 | 2.0-5.0 | 55-75 | 15-25 | 2800-3000 | 70-85 |
| 离心泵 | CP-001 | 1.0-3.5 | 40-65 | 8-18 | 1400-1500 | 55-72 |
| 风机 | FN-001 | 1.5-4.5 | 35-60 | 5-15 | 900-1100 | 60-78 |
| 传送带 | CV-001 | 0.5-2.5 | 30-50 | 3-10 | 50-150 | 45-65 |
| 冷却塔 | CT-001 | 1.0-3.0 | 25-45 | 10-20 | 700-900 | 50-70 |

## 目录结构

```
phm-system/
├── docker-compose.yml         # Docker Compose编排配置
├── .env                       # 环境变量
├── start.bat                  # Windows启动脚本
├── start.sh                   # Linux/Mac启动脚本
├── stop.bat                   # Windows停止脚本
├── stop.sh                    # Linux/Mac停止脚本
├── README.md                  # 项目文档
│
├── edge-node/                 # 边缘节点模块 (Python)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── config.py              # 设备配置
│   ├── main.py                # 主程序入口
│   ├── anomaly_detector.py    # 孤立森林异常检测
│   └── devices/
│       ├── base_device.py     # 设备基类
│       ├── air_compressor.py  # 空压机
│       ├── centrifugal_pump.py# 离心泵
│       ├── fan.py             # 风机
│       ├── conveyor.py        # 传送带
│       └── cooling_tower.py   # 冷却塔
│
├── cloud-backend/             # 云端后端模块 (Go)
│   ├── Dockerfile
│   ├── go.mod
│   ├── main.go
│   ├── config/                # 配置
│   ├── models/                # 数据模型
│   ├── services/              # 服务层
│   │   ├── influxdb_service.go
│   │   ├── websocket_service.go
│   │   ├── lstm_service.go
│   │   └── rootcause_service.go
│   └── handlers/              # 请求处理
│
├── lstm-service/              # LSTM预测服务 (Python)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── config.py
│   ├── main.py                # Flask API服务
│   ├── data/
│   │   └── generate_history.py# 历史数据生成
│   ├── model/
│   │   ├── lstm_model.py      # LSTM模型定义
│   │   └── train.py           # 训练流程
│   ├── models/                # 训练好的模型(自动生成)
│   └── data/history/          # 历史数据(自动生成)
│
├── root-cause-service/        # 根因分析服务 (Python)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   ├── case_base.py           # 22+历史故障案例库
│   └── similarity_matcher.py  # 相似度匹配算法
│
└── frontend/                  # 前端模块 (Vue 3 + ECharts)
    ├── Dockerfile
    ├── nginx.conf
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── main.js
        ├── App.vue
        ├── style.css
        ├── utils/             # API和WebSocket工具
        └── components/
            ├── Dashboard.vue
            ├── DeviceHealthGauge.vue
            ├── VibrationSpectrum.vue
            ├── RULTrendChart.vue
            ├── AlertPanel.vue
            └── RootCausePanel.vue
```

## 技术栈详解

### 边缘计算层
| 技术 | 用途 | 说明 |
|------|------|------|
| **Python 3.11** | 边缘节点开发 | 轻量、数据处理能力强 |
| **Scikit-learn Isolation Forest** | 异常检测 | 无需标签、低延迟、适合边缘部署 |
| **NumPy/SciPy** | 数据处理 | 信号模拟、噪声生成 |

### 云端后端层
| 技术 | 用途 | 说明 |
|------|------|------|
| **Go 1.21 + Gin** | API服务 | 高并发、低延迟、编译型语言 |
| **InfluxDB 2.7** | 时序数据库 | 专为时序数据优化，写入查询性能优异 |
| **Gorilla WebSocket** | 实时通信 | 成熟稳定的WebSocket库 |

### AI分析层
| 技术 | 用途 | 说明 |
|------|------|------|
| **TensorFlow/Keras LSTM** | 剩余寿命预测 | 擅长处理时间序列依赖关系 |
| **Flask** | AI服务API | 轻量Python Web框架 |
| **Scikit-learn + SciPy** | 相似度计算 | 余弦相似度、加权欧氏距离 |

### 前端展示层
| 技术 | 用途 | 说明 |
|------|------|------|
| **Vue 3 (Composition API)** | 前端框架 | 响应式、组件化、上手快 |
| **Apache ECharts 5.5** | 图表可视化 | 功能强大、图表类型丰富 |
| **Vite 5** | 构建工具 | 极速冷启动、热更新 |
| **Nginx** | 生产部署 | 高性能Web服务器+反向代理 |

### 基础设施
| 技术 | 用途 |
|------|------|
| **Docker + Docker Compose** | 容器化部署，一键启动 |
| **Alpine Linux** | 最小化基础镜像，减小体积 |

## 典型使用流程

1. **系统启动**：`docker compose up -d` → LSTM自动生成1周数据并训练模型
2. **边缘模拟**：edge-node每10秒采集5台设备数据，孤立森林检测异常
3. **异常上传**：检测到异常后，边缘节点将数据POST到云端
4. **数据存储**：Go后端写入InfluxDB，同时通过WebSocket广播
5. **智能分析**：异步调用LSTM做RUL预测 + 根因分析服务匹配案例
6. **前端展示**：实时更新仪表盘、图表、告警面板

## 常见问题

### Q: LSTM服务启动很慢？
A: 首次启动需要：①生成每台设备6万+条历史数据 ②训练5个LSTM模型（每个约100 epoch）。预计耗时10-30分钟，取决于CPU性能。可通过`docker compose logs -f lstm-service`查看训练进度。

### Q: 前端看不到实时数据？
A: 检查edge-node日志确认是否有异常产生（只有异常数据才会上传）。可临时降低异常检测阈值提高异常频率。

### Q: InfluxDB登录失败？
A: 首次创建后凭据为admin/admin123。如果之前启动过但清理不彻底，执行`docker compose down -v`清理数据卷后重新启动。

### Q: Windows下Docker内存不足？
A: 在Docker Desktop → Settings → Resources中将内存调整到8GB以上。

## 许可协议

本项目仅用于演示和学习目的。
