@echo off
chcp 65001 >nul
echo ========================================
echo   PHM设备故障预测与健康管理系统启动脚本
echo ========================================
echo.

echo [1/5] 检查Docker环境...
docker --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Docker，请先安装Docker Desktop并启动
    pause
    exit /b 1
)
echo Docker环境: OK
echo.

echo [2/5] 检查Docker Compose...
docker compose version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Docker Compose
    pause
    exit /b 1
)
echo Docker Compose: OK
echo.

echo [3/5] 创建必要的目录...
if not exist "lstm-service\models" mkdir "lstm-service\models"
if not exist "lstm-service\data\history" mkdir "lstm-service\data\history"
echo 目录创建完成
echo.

echo [4/5] 构建并启动所有服务（首次启动约需10-20分钟，LSTM模型训练需较长时间）...
echo.
echo 服务列表:
echo   - InfluxDB (时序数据库)
echo   - LSTM预测服务 (剩余寿命预测)
echo   - 根因分析服务 (故障诊断)
echo   - Cloud Backend (Go云端后端)
echo   - Edge Node (边缘节点模拟)
echo   - Frontend (Vue前端界面)
echo.
echo 注意事项:
echo   1. LSTM服务首次启动会生成数据并训练模型，请耐心等待
echo   2. 所有服务启动完成后，访问 http://localhost 查看前端
echo   3. InfluxDB管理界面: http://localhost:8086 (admin/admin123)
echo.

docker compose up -d --build

echo.
echo [5/5] 等待服务启动...
timeout /t 10 /nobreak >nul

echo.
echo ========================================
echo   服务启动命令已执行！
echo ========================================
echo.
echo 查看服务状态: docker compose ps
echo 查看日志: docker compose logs -f [服务名]
echo 停止所有服务: docker compose down
echo.
echo 前端访问地址: http://localhost
echo InfluxDB管理: http://localhost:8086 (admin/admin123)
echo.
echo 正在启动中，请稍候2-5分钟后访问前端...
pause
