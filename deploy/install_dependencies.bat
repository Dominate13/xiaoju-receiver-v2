@echo off
chcp 65001 >nul
title 安装依赖

echo.
echo ==============================================
echo     小桔充电数据集成服务 - 依赖安装脚本
echo ==============================================
echo.

cd /d "%~dp0.."

echo 1. 检查 Python 环境...
python --version 2>NUL
if %errorlevel% neq 0 (
    echo 错误: 未找到 Python 环境
    echo 请先安装 Python 3.9+，并确保添加到系统 PATH
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo.
echo 2. 创建虚拟环境...
if not exist "venv" (
    python -m venv venv
    if %errorlevel% neq 0 (
        echo 错误: 创建虚拟环境失败
        pause
        exit /b 1
    )
    echo ✓ 虚拟环境创建成功
) else (
    echo ✓ 虚拟环境已存在
)

echo.
echo 3. 激活虚拟环境并安装依赖...
call venv\Scripts\activate.bat

echo 正在安装依赖包（使用国内镜像加速）...
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

if %errorlevel% equ 0 (
    echo.
    echo ✓ 依赖安装成功
) else (
    echo.
    echo ✗ 依赖安装失败
    pause
    exit /b 1
)

echo.
echo 4. 检查数据库目录...
if not exist "data" (
    mkdir data
    echo ✓ 创建数据目录成功
) else (
    echo ✓ 数据目录已存在
)

echo.
echo ==============================================
echo     依赖安装完成！
echo ==============================================
echo.
echo 下一步：运行 start_service.bat 启动服务
echo.
pause