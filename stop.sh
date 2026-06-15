#!/bin/bash

echo "========================================"
echo "  停止PHM系统所有服务"
echo "========================================"
echo ""

echo "正在停止所有服务..."
docker compose down

echo ""
echo "所有服务已停止"
echo ""
echo "如需清理数据卷，请执行: docker compose down -v"
