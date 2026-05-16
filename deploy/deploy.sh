#!/bin/bash
set -e

echo "=========================================="
echo "  小桔充电数据集成服务部署脚本"
echo "=========================================="

WORK_DIR=$(cd "$(dirname "$0")/.." && pwd)
cd "$WORK_DIR"

echo "1. 检查 Python 环境..."
if ! command -v python3 &> /dev/null; then
    echo "   ✗ 未找到 Python3，请先安装"
    exit 1
fi
echo "   ✓ Python3 版本: $(python3 --version)"

echo "2. 创建虚拟环境..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "   ✓ 虚拟环境创建成功"
else
    echo "   ✓ 虚拟环境已存在"
fi

echo "3. 激活虚拟环境并安装依赖..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "   ✓ 依赖安装完成"

echo "4. 创建数据目录..."
mkdir -p data
echo "   ✓ 数据目录创建成功"

echo "5. 检查端口 8100..."
if lsof -Pi :8100 -s