@echo off
chcp 65001 >nul
title 一键部署

echo.
echo ==============================================
echo     小桔充电数据集成服务 - 一键部署
echo ==============================================
echo.

cd /d "%~dp0.."

echo 开始部署流程...
echo.

echo [Step 1/3] 安装依赖...
call deploy\install_dependencies.bat
if %errorlevel% neq 0 (
    echo 依赖安装失败，部署终止
    pause
    exit /b 1
)

echo.
echo [Step 2/3] 停止可能运行的服务...
call deploy\stop_service.bat

echo.
echo [Step 3/3] 启动服务...
call deploy\start_service.bat

echo.
echo 部署完成！
pause