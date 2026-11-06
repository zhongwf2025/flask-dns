========================================
DNS管理系统 远程部署指南
服务器: 10.10.0.232
目标目录: /data/ai/dns
========================================

【方式一】使用Git Bash执行自动部署脚本
----------------------------------------
1. 安装Git for Windows (如果还没有)
2. 右键打开 Git Bash
3. 执行以下命令:

   cd /d/py/dns/docker
   chmod +x deploy.sh
   ./deploy.sh

4. 按提示输入密码: root123456


【方式二】手动执行命令
----------------------------------------

步骤1: 上传文件到服务器

  scp D:\py\dns\*.py root@10.10.0.232:/data/ai/dns/
  scp D:\py\dns\*.txt root@10.10.0.232:/data/ai/dns/
  scp -r D:\py\dns\templates root@10.10.0.232:/data/ai/dns/
  scp -r D:\py\dns\static root@10.10.0.232:/data/ai/dns/
  scp D:\py\dns\docker\Dockerfile root@10.10.0.232:/data/ai/dns/
  
  密码: root123456

步骤2: SSH登录服务器

  ssh root@10.10.0.232
  密码: root123456

步骤3: 在服务器上构建镜像

  cd /data/ai/dns
  docker build -t dns-manager:latest .

步骤4: 导出镜像为tar包

  docker save -o dns.tar dns-manager:latest
  ls -lh dns.tar

步骤5: 验证

  docker images | grep dns-manager


【方式三】使用PowerShell逐条执行
----------------------------------------

# 上传文件
scp -r D:\py\dns\*.py root@10.10.0.232:/data/ai/dns/
scp -r D:\py\dns\requirements.txt root@10.10.0.232:/data/ai/dns/
scp -r D:\py\dns\templates root@10.10.0.232:/data/ai/dns/
scp -r D:\py\dns\static root@10.10.0.232:/data/ai/dns/
scp D:\py\dns\docker\Dockerfile root@10.10.0.232:/data/ai/dns/

# 远程执行构建命令
ssh root@10.10.0.232 "cd /data/ai/dns && docker build -t dns-manager:latest . && docker save -o dns.tar dns-manager:latest && ls -lh dns.tar"


========================================
构建完成后
========================================

镜像位置: 10.10.0.232:/data/ai/dns/dns.tar

使用镜像:
  # 在任意服务器上加载镜像
  docker load -i dns.tar
  
  # 运行容器
  docker run -d \
    --name dns-app \
    -p 8088:8088 \
    -p 53:53/udp \
    -e DB_HOST=10.10.0.232 \
    -e DB_PORT=53306 \
    -e DB_USER=root \
    -e DB_PASSWORD=root123456 \
    dns-manager:latest

访问: http://服务器IP:8088
账号: admin / admin


========================================
常见问题
========================================

Q: SSH首次连接需要确认?
A: 输入 yes 确认

Q: Docker未安装?
A: 在服务器上执行: yum install -y docker-ce docker-ce-cli containerd.io
   或: apt-get install -y docker-ce docker-ce-cli containerd.io

Q: 权限不足?
A: 确保使用root用户或具有sudo权限的用户


项目结构
D:\py\dns\
├── main.py              # 主入口
├── app.py               # Flask Web应用 (1120行，含所有路由和API)
├── dns_server.py        # DNS服务器核心 (UDP 53端口)
├── config.py            # 配置文件
├── init_db.py           # 数据库初始化脚本 (20+张表)
├── requirements.txt     # Python依赖
├── static/
│   ├── css/style.css    # 青绿色主题样式
│   └── js/app.js        # 前端通用脚本
└── templates/           # 14个HTML模板
    ├── base.html, login.html, index.html
    ├── domain.html, record.html, ptr.html
    ├── forward.html, cfw.html, server.html
    ├── query.html, ranking.html, latest.html
    ├── admin_settings.html, system_settings.html
    └── change_password.html

功能模块
模块	功能
解析管理	域名解析（增删改查A/AAAA/CNAME/MX/NS/TXT记录）、反向解析（PTR记录）
转发管理	递归转发开关/缓存时间/上级DNS设置、条件转发规则管理
节点管理	DNS节点设备的增删改查
查询统计	24小时查询流量图表、域名查询排行前30、最新100条查询记录
系统设置	后台名称/端口/登录IP限制、Cookie时间/DNS端口、修改密码

启动方式
# 1. 安装依赖
pip install flask pymysql psutil

# 2. 配置数据库（编辑 config.py 中的 MySQL 连接信息）
# 3. 初始化数据库（首次运行自动创建）
python init_db.py

# 4. 启动服务
python main.py
启动后访问 http://127.0.0.1:8088，默认账号 admin / admin。
