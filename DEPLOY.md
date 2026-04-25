# 阿里云部署指南

## 目录
- [一、阿里云服务器购买与配置](#一阿里云服务器购买与配置)
- [二、域名解析配置](#二域名解析配置)
- [三、服务器环境准备](#三服务器环境准备)
- [四、项目部署](#四项目部署)
- [五、SSL 证书配置](#五ssl-证书配置)
- [六、验证与测试](#六验证与测试)

---

## 一、阿里云服务器购买与配置

### 1.1 购买 ECS 实例
1. 登录 [阿里云 ECS 控制台](https://ecs.console.aliyun.com)
2. 点击「创建实例」
3. 配置选择：
   - **地域**：选择离用户最近的地域
   - **实例规格**：2核4GB（≤4核8GB要求）
   - **镜像**：Ubuntu 22.04 LTS（推荐）或 CentOS 8
   - **存储**：40GB SSD
   - **网络**：公网带宽「按使用流量」，带宽峰值 100Mbps
   - **安全组**：开放 22（SSH）、80（HTTP）、443（HTTPS）端口

### 1.2 设置 root 密码并记录 IP
```bash
# 重置密码（控制台 → 实例 → 更多 → 密码/密钥 → 重置密码）
# 记录公网 IP，例如：47.92.xxx.xxx
```

---

## 二、域名解析配置

### 2.1 在阿里云域名控制台添加解析
1. 进入 [云解析 DNS 控制台](https://dns.console.aliyun.com)
2. 选择你的域名，点击「添加记录」

| 记录类型 | 主机记录 | 记录值 | TTL |
|---------|---------|--------|-----|
| A | @ | 你的服务器公网IP | 600 |
| A | www | 你的服务器公网IP | 600 |
| A | api | 你的服务器公网IP | 600 |
| A | dify | 你的服务器公网IP | 600 |

### 2.2 验证解析生效
```bash
ping 你的域名
nslookup 你的域名
```

---

## 三、服务器环境准备

### 3.1 SSH 连接到服务器
```bash
ssh root@你的服务器IP
```

### 3.2 安装 Docker 和 Docker Compose
```bash
# 更新系统
apt update && apt upgrade -y

# 安装 Docker
curl -fsSL https://get.docker.com | sh

# 安装 Docker Compose
apt install docker-compose -y

# 验证安装
docker --version
docker-compose --version
```

### 3.3 配置 Docker 加速（可选）
```bash
mkdir -p /etc/docker
cat > /etc/docker/daemon.json << EOF
{
  "registry-mirrors": [
    "https://mirror.ccs.tencentyun.com",
    "https://docker.mirrors.ustc.edu.cn"
  ]
}
EOF

systemctl daemon-reload
systemctl restart docker
```

---

## 四、项目部署

### 4.1 上传项目到服务器
```bash
# 方法1：使用 scp 上传（本地执行）
scp -r ./项目目录 root@你的服务器IP:/opt/music-shop

# 方法2：使用 Git 克隆
git clone 你的仓库地址 /opt/music-shop

# 方法3：使用 rsync（推荐，大文件）
rsync -avz --progress ./项目目录 root@你的服务器IP:/opt/music-shop
```

### 4.2 配置环境变量
```bash
cd /opt/music-shop

# 复制并编辑环境变量文件
cp .env.example .env

# 编辑 .env 文件
cat > .env << EOF
# Flask 配置
SECRET_KEY=你的随机密钥
FLASK_ENV=production

# 数据库配置
POSTGRES_USER=postgres
POSTGRES_PASSWORD=设置强密码
POSTGRES_DB=musicdb

# GitHub OAuth（如果使用）
GITHUB_CLIENT_ID=你的ClientID
GITHUB_CLIENT_SECRET=你的ClientSecret

# Dify 配置（重要！）
DIFIFY_API_URL=http://dify-api:80
DIFY_API_KEY=你的Dify API Key
EOF
```

### 4.3 构建和启动
```bash
cd /opt/music-shop

# 构建镜像
docker-compose -f docker-compose.prod.yml build

# 启动服务（后台运行）
docker-compose -f docker-compose.prod.yml up -d

# 查看服务状态
docker-compose -f docker-compose.prod.yml ps

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f
```

### 4.4 初始化数据库
```bash
# 进入 web 容器执行数据库初始化
docker exec -it music-web flask db upgrade

# 或者执行初始化脚本
docker exec -it music-web python init_db.py
```

---

## 五、SSL 证书配置

### 5.1 申请免费 SSL 证书（阿里云）
1. 进入 [SSL 证书控制台](https://yundun.console.aliyun.com)
2. 点击「免费证书」→「立即购买」→ 「DV 单域名证书」
3. 填写域名信息，提交审核

### 5.2 下载证书
1. 审核通过后，点击「下载」
2. 选择「Nginx」类型
3. 解压得到 `.key` 和 `.pem` 文件

### 5.3 上传证书到服务器
```bash
# 在本地执行
scp your_domain.com.key root@你的服务器IP:/opt/music-shop/nginx/ssl/
scp your_domain.com.pem root@你的服务器IP:/opt/music-shop/nginx/ssl/

# 在服务器上重命名
cd /opt/music-shop/nginx/ssl/
mv your_domain.com.pem server.crt
mv your_domain.com.key server.key
chmod 600 server.key
```

### 5.4 配置 Nginx HTTPS
```bash
# 编辑 nginx.conf，取消 HTTPS server 块的注释
vi /opt/music-shop/nginx/nginx.conf
```

将 HTTPS server 配置取消注释并修改：
```nginx
server {
    listen 443 ssl http2;
    server_name 你的域名;

    ssl_certificate /etc/nginx/ssl/server.crt;
    ssl_certificate_key /etc/nginx/ssl/server.key;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;

    # ... 其他配置同 HTTP
}

# 强制 HTTPS
server {
    listen 80;
    server_name 你的域名;
    return 301 https://$host$request_uri;
}
```

### 5.5 重启 Nginx
```bash
docker-compose -f docker-compose.prod.yml restart nginx
```

---

## 六、验证与测试

### 6.1 本地测试
```bash
# 测试 HTTP
curl http://你的域名

# 测试 API
curl http://你的域名/api/products

# 测试 Dify
curl http://你的域名:8080/v1/ping
```

### 6.2 浏览器测试
1. 访问 `http://你的域名` → 应该看到网站首页
2. 访问 `http://你的域名:8080` → 应该看到 Dify 控制台
3. 测试用户注册、登录、产品浏览等功能

### 6.3 日志排查
```bash
# 查看所有服务日志
docker-compose -f docker-compose.prod.yml logs

# 查看特定服务
docker-compose -f docker-compose.prod.yml logs web
docker-compose -f docker-compose.prod.yml logs nginx

# 实时查看
docker-compose -f docker-compose.prod.yml logs -f --tail=100
```

---

## 七、运维命令

```bash
# 停止服务
docker-compose -f docker-compose.prod.yml stop

# 重启服务
docker-compose -f docker-compose.prod.yml restart

# 更新代码后重新构建
git pull
docker-compose -f docker-compose.prod.yml build web
docker-compose -f docker-compose.prod.yml up -d

# 查看资源使用
docker stats

# 进入容器
docker exec -it music-web /bin/bash

# 清理未使用的资源
docker system prune -f
```

---

## 八、常见问题

### Q1: 端口被占用
```bash
# 查看端口占用
netstat -tlnp | grep 80

# 杀死进程
kill -9 <PID>
```

### Q2: 数据库连接失败
```bash
# 检查数据库状态
docker exec -it music-db psql -U postgres -d musicdb

# 检查连接
docker exec -it music-web env | grep DATABASE
```

### Q3: Dify 无法访问
```bash
# Dify 需要较大内存，确保服务器至少 4GB 内存
# 检查 Dify 服务
docker ps | grep dify
docker logs dify-api
```

### Q4: SSL 证书失效
```bash
# 检查证书文件
ls -la /opt/music-shop/nginx/ssl/

# 重新加载 Nginx
docker exec music-nginx nginx -s reload
```

---

## 九、部署检查清单

- [ ] 阿里云 ECS 实例运行中
- [ ] 域名解析生效
- [ ] 安全组开放 80/443/8080 端口
- [ ] Docker 和 Docker Compose 已安装
- [ ] 项目代码已上传
- [ ] .env 环境变量已配置
- [ ] 数据库已初始化
- [ ] SSL 证书已配置（可选）
- [ ] 浏览器访问正常
