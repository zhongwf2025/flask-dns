# DNS管理系统 Docker 部署指南

## 目录结构

```
docker/
├── Dockerfile           # Docker镜像构建文件
├── docker-compose.yml   # Docker Compose 配置文件
├── config.py            # Docker专用配置 (使用环境变量)
├── .dockerignore        # 构建忽略文件
├── build.bat            # Windows构建脚本
├── build.sh             # Linux/Mac构建脚本
└── README.md            # 本文件
```

## 快速开始

### Windows 用户

1. 双击运行 `build.bat` 构建并启动
2. 或手动执行：
   ```powershell
   cd D:\py\dns\docker
   docker-compose build
   docker-compose up -d
   ```

### Linux/Mac 用户

```bash
cd /path/to/dns/docker
chmod +x build.sh
./build.sh
```

## 服务说明

| 服务 | 端口 | 说明 |
|------|------|------|
| Web管理后台 | 8088 | http://localhost:8088 |
| DNS服务 | 53/UDP | DNS查询端口 |
| MySQL | 53306 | 数据库连接端口 |

## 默认账号

- 用户名: `admin`
- 密码: `admin`

## 常用命令

```bash
# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 重启服务
docker-compose restart

# 停止服务
docker-compose down

# 停止并删除数据卷
docker-compose down -v

# 重新构建镜像
docker-compose build --no-cache
```

## 配置说明

编辑 `config.py` 或通过环境变量修改配置：

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| DB_HOST | mysql | 数据库主机 |
| DB_PORT | 3306 | 数据库端口 |
| DB_USER | root | 数据库用户 |
| DB_PASSWORD | Dw.2016% | 数据库密码 |
| DB_NAME | dns | 数据库名称 |
| WEB_PORT | 8088 | Web服务端口 |
| DNS_PORT | 53 | DNS服务端口 |
| ADMIN_NAME | 深圳科技 | 后台名称 |

## 数据持久化

MySQL数据存储在 `mysql_data` 卷中，容器删除后数据不会丢失。

如需备份数据：
```bash
docker exec dns-mysql mysqldump -u root -pDw.2016% dns > backup.sql
```

## 故障排查

1. 如果MySQL启动失败，检查端口53306是否被占用
2. 如果DNS服务无法启动，检查端口53是否被占用，或修改映射端口
3. 查看应用日志：`docker-compose logs dns-app`
4. 查看数据库日志：`docker-compose logs mysql`
