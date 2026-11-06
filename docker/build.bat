@echo off
chcp 65001 >nul
echo ==========================================
echo   DNS管理系统 Docker 构建脚本
echo ==========================================
echo.

cd /d "%~dp0"

echo [1/4] 检查Docker环境...
docker --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未检测到Docker，请先安装Docker Desktop
    pause
    exit /b 1
)

echo [2/4] 复制配置文件...
copy /Y config.py ..\config.py >nul

echo [3/4] 构建Docker镜像...
docker-compose build

echo [4/4] 启动服务...
docker-compose up -d

echo.
echo ==========================================
echo   构建完成！
echo ==========================================
echo.
echo   Web管理后台: http://localhost:8088
echo   默认账号: admin / admin
echo.
echo   查看日志: docker-compose logs -f
echo   停止服务: docker-compose down
echo.
pause
