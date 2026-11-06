#!/bin/bash
# DNS管理系统 远程部署脚本
# 服务器: 10.10.0.232
# 目标: 上传文件并构建Docker镜像到 /data/ai/dns/dns.tar

SERVER_IP="10.10.0.232"
SERVER_USER="root"
SERVER_DIR="/data/ai/dns"
LOCAL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "=========================================="
echo "  DNS管理系统 远程部署脚本"
echo "=========================================="
echo ""
echo "服务器: ${SERVER_USER}@${SERVER_IP}"
echo "本地目录: ${LOCAL_DIR}"
echo "目标目录: ${SERVER_DIR}"
echo ""

# 检查SSH连接
echo "[1/6] 检查SSH连接..."
if ! ssh -o ConnectTimeout=5 -o BatchMode=yes ${SERVER_USER}@${SERVER_IP} "echo '连接成功'" 2>/dev/null; then
    echo "提示: 需要输入密码 ${SERVER_PASS}"
fi

# 创建远程目录
echo ""
echo "[2/6] 创建远程目录..."
ssh ${SERVER_USER}@${SERVER_IP} "mkdir -p ${SERVER_DIR}"

# 上传Python文件
echo ""
echo "[3/6] 上传Python源文件..."
scp ${LOCAL_DIR}/*.py ${SERVER_USER}@${SERVER_IP}:${SERVER_DIR}/
scp ${LOCAL_DIR}/requirements.txt ${SERVER_USER}@${SERVER_IP}:${SERVER_DIR}/

# 上传模板和静态文件
echo ""
echo "[4/6] 上传模板和静态文件..."
scp -r ${LOCAL_DIR}/templates ${SERVER_USER}@${SERVER_IP}:${SERVER_DIR}/
scp -r ${LOCAL_DIR}/static ${SERVER_USER}@${SERVER_IP}:${SERVER_DIR}/

# 上传Dockerfile
echo ""
echo "[5/6] 上传Dockerfile..."
scp ${LOCAL_DIR}/docker/Dockerfile ${SERVER_USER}@${SERVER_IP}:${SERVER_DIR}/

# 构建镜像
echo ""
echo "[6/6] 在服务器上构建Docker镜像..."
ssh ${SERVER_USER}@${SERVER_IP} << 'ENDSSH'
cd /data/ai/dns
echo "开始构建镜像..."
docker build -t dns-manager:latest .

if [ $? -eq 0 ]; then
    echo "镜像构建成功！"
    echo "导出镜像为tar包..."
    docker save -o dns.tar dns-manager:latest
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "=========================================="
        echo "  部署完成！"
        echo "=========================================="
        echo ""
        ls -lh dns.tar
        echo ""
        echo "镜像位置: /data/ai/dns/dns.tar"
        echo ""
        echo "使用方法:"
        echo "  docker load -i /data/ai/dns/dns.tar"
        echo "  docker run -d -p 8088:8088 -p 53:53/udp --name dns-app dns-manager:latest"
    else
        echo "错误: 镜像导出失败"
        exit 1
    fi
else
    echo "错误: 镜像构建失败"
    exit 1
fi
ENDSSH

echo ""
echo "部署脚本执行完成！"
