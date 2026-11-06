#!/bin/bash

echo "=========================================="
echo "  DNS管理系统 Docker 镜像打包脚本"
echo "=========================================="
echo ""

cd "$(dirname "$0")/.."

echo "[1/3] 构建Docker镜像..."
docker build -f docker/Dockerfile -t dns-manager:latest .

if [ $? -ne 0 ]; then
    echo "错误: 镜像构建失败"
    exit 1
fi

echo ""
echo "[2/3] 导出镜像为tar包..."
docker save -o docker/dns.tar dns-manager:latest

if [ $? -ne 0 ]; then
    echo "错误: 镜像导出失败"
    exit 1
fi

echo ""
echo "[3/3] 获取文件大小..."
ls -lh docker/dns.tar

echo ""
echo "=========================================="
echo "  打包完成！"
echo "=========================================="
echo ""
echo "  镜像文件: docker/dns.tar"
echo ""
echo "  使用方法:"
echo "    docker load -i dns.tar"
echo "    docker run -d -p 8088:8088 -p 53:53/udp --name dns-app dns-manager:latest"
echo ""
