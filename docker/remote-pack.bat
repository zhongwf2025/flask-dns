@echo off
chcp 65001 >nul
echo ==========================================
echo   DNS管理系统 远程服务器Docker打包脚本
echo ==========================================
echo.

set SERVER_IP=10.10.0.232
set SERVER_USER=root
set SERVER_PASS=Dw.2016%
set SERVER_DIR=/data/ai/dns
set LOCAL_DIR=%~dp0..

echo 服务器: %SERVER_USER%@%SERVER_IP%
echo 目标目录: %SERVER_DIR%
echo.

echo [1/5] 检查SSH连接...
ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "echo SSH连接成功" 2>nul
if errorlevel 1 (
    echo 错误: 无法连接到服务器，请检查网络和SSH配置
    pause
    exit /b 1
)

echo.
echo [2/5] 在服务器上创建目录...
ssh %SERVER_USER%@%SERVER_IP% "mkdir -p %SERVER_DIR%"

echo.
echo [3/5] 上传项目文件...
scp -r "%LOCAL_DIR%\*.py" %SERVER_USER%@%SERVER_IP%:%SERVER_DIR%/
scp -r "%LOCAL_DIR%\*.txt" %SERVER_USER%@%SERVER_IP%:%SERVER_DIR%/
scp -r "%LOCAL_DIR%\templates" %SERVER_USER%@%SERVER_IP%:%SERVER_DIR%/
scp -r "%LOCAL_DIR%\static" %SERVER_USER%@%SERVER_IP%:%SERVER_DIR%/
scp "%LOCAL_DIR%\docker\Dockerfile" %SERVER_USER%@%SERVER_IP%:%SERVER_DIR%/

echo.
echo [4/5] 在服务器上构建Docker镜像...
ssh %SERVER_USER%@%SERVER_IP% "cd %SERVER_DIR% && docker build -t dns-manager:latest ."

echo.
echo [5/5] 导出镜像为tar包...
ssh %SERVER_USER%@%SERVER_IP% "cd %SERVER_DIR% && docker save -o dns.tar dns-manager:latest"

echo.
echo ==========================================
echo   打包完成！
echo ==========================================
echo.
echo   镜像位置: %SERVER_USER%@%SERVER_IP%:%SERVER_DIR%/dns.tar
echo.
echo   如需下载到本地:
echo     scp %SERVER_USER%@%SERVER_IP%:%SERVER_DIR%/dns.tar D:\py\dns\docker\
echo.
echo   使用方法:
echo     docker load -i dns.tar
echo     docker run -d -p 8088:8088 -p 53:53/udp --name dns-app dns-manager:latest
echo.
pause
