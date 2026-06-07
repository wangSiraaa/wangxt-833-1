#!/bin/bash

echo "========================================"
echo "  药店处方流转审方API服务 - 启动脚本"
echo "========================================"
echo ""

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

if [ ! -d "venv" ]; then
    echo "[1/4] 创建Python虚拟环境..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "❌ 创建虚拟环境失败，请检查Python是否安装正确"
        exit 1
    fi
    echo "✅ 虚拟环境创建成功"
fi

echo ""
echo "[2/4] 激活虚拟环境..."
source venv/bin/activate
echo "✅ 虚拟环境已激活"

echo ""
echo "[3/4] 安装依赖..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "❌ 依赖安装失败"
    exit 1
fi
echo "✅ 依赖安装完成"

echo ""
echo "[4/4] 启动API服务..."
echo ""
echo "服务地址: http://localhost:8000"
echo "API文档: http://localhost:8000/docs"
echo "健康检查: http://localhost:8000/health"
echo ""
echo "按 Ctrl+C 停止服务"
echo "========================================"
echo ""

export PYTHONPATH="$PROJECT_DIR"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
