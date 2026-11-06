# DNS管理系统 Docker镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制项目文件
COPY . .

# 暴露端口
# 8088 - Web管理后台
# 53   - DNS服务 (UDP)
EXPOSE 8088
EXPOSE 53/udp

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Shanghai

# 启动命令
CMD ["python", "main.py"]
