"""DNS管理系统配置文件"""

# MySQL数据库配置
DB_CONFIG = {
    'host': '10.10.0.232',
    'port': 53306,
    'user': 'root',
    'password': 'root123456',
    'database': 'dns',
    'charset': 'utf8'
}

# Web服务配置
WEB_PORT = 8088
SECRET_KEY = 'dns-admin-secret-key-2024'
COOKIE_MAX_AGE = 600  # 分钟

# DNS服务配置
DNS_PORT = 53
DNS_CACHE_TTL = 60  # 秒
UPSTREAM_DNS = ['180.76.76.76', '223.5.5.5', '119.29.29.29']
ENABLE_FORWARD = True
ENABLE_CONDITIONAL_FORWARD = False

# 后台设置
ADMIN_NAME = 'zhongwf'
ADMIN_PORT = 8088
LOGIN_IPS = []  # 空表示不限制
