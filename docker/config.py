"""DNS管理系统配置文件 - Docker版本"""
import os

# MySQL数据库配置 (从环境变量读取，支持Docker网络)
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'mysql'),
    'port': int(os.environ.get('DB_PORT', 3306)),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', 'Dw.2016%'),
    'database': os.environ.get('DB_NAME', 'dns'),
    'charset': 'utf8'
}

# Web服务配置
WEB_PORT = int(os.environ.get('WEB_PORT', 8088))
SECRET_KEY = os.environ.get('SECRET_KEY', 'dns-admin-secret-key-2024-docker')
COOKIE_MAX_AGE = 600  # 分钟

# DNS服务配置
DNS_PORT = int(os.environ.get('DNS_PORT', 53))
DNS_CACHE_TTL = 60  # 秒
UPSTREAM_DNS = ['180.76.76.76', '223.5.5.5', '119.29.29.29']
ENABLE_FORWARD = True
ENABLE_CONDITIONAL_FORWARD = False

# 后台设置
ADMIN_NAME = os.environ.get('ADMIN_NAME', '深圳科技')
ADMIN_PORT = WEB_PORT
LOGIN_IPS = []  # 空表示不限制
