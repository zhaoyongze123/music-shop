# 音悦阁生产部署文档

本文档面向项目交付、服务器运维和 GitHub Actions 自动化部署，覆盖以下内容：

- 服务器准备
- 环境变量配置
- 首次部署
- 自动化部署
- 回滚策略
- 常见排障

## 1. 部署目标

生产环境部署目标如下：

1. 使用阿里云 ECS 作为单机生产节点
2. 通过 Docker Compose 管理 Flask、PostgreSQL、Nginx
3. 通过 GitHub Actions 自动同步代码并完成应用更新
4. 保留最小回滚能力，部署失败时能够恢复上一版本镜像

## 2. 服务器信息

以下信息为当前项目生产部署约定：

| 项目 | 值 |
|------|----|
| 服务器系统 | Ubuntu 22.04 |
| 部署目录 | `/opt/music-shop` |
| SSH 用户 | `root` |
| Web 容器 | `music-web` |
| DB 容器 | `music-db` |
| 生产编排文件 | `docker-compose.prod.yml` |

## 3. 网络与端口

| 端口 | 服务 | 说明 |
|------|------|------|
| `22` | SSH | 运维登录 |
| `80` | Nginx | HTTP 入口 |
| `443` | Nginx | HTTPS 入口 |
| `5000` | Flask | Web 应用内部服务 |
| `5432` | PostgreSQL | 数据库内部服务 |
| `3000` | Dify Web/Nginx | Dify 入口 |
| `5001` | Dify API | Dify API 服务 |

建议安全组最少放行：

- `22`
- `80`
- `443`

如果 Dify 需要独立外部访问，再按需开放 `3000` / `5001`。

## 4. 首次部署前准备

### 4.1 安装 Docker 和 Compose

```bash
apt update && apt upgrade -y
curl -fsSL https://get.docker.com | sh
apt install docker-compose-plugin -y

docker --version
docker compose version
```

### 4.2 创建部署目录

```bash
mkdir -p /opt/music-shop
```

### 4.3 上传代码

可选方式：

```bash
# 方式 1
scp -r ./music-shop root@服务器IP:/opt/music-shop

# 方式 2
git clone 仓库地址 /opt/music-shop

# 方式 3（推荐）
rsync -az --progress ./ root@服务器IP:/opt/music-shop
```

## 5. 环境变量

项目不应把生产 `.env` 提交到仓库，建议只在服务器保留。

示例：

```env
FLASK_ENV=production
SECRET_KEY=replace-with-strong-secret

POSTGRES_USER=postgres
POSTGRES_PASSWORD=replace-with-strong-password
POSTGRES_DB=musicdb

GITHUB_CLIENT_ID=your-client-id
GITHUB_CLIENT_SECRET=your-client-secret

DIFIFY_API_URL=http://8.130.33.113:3000/v1
DIFIFY_API_KEY=your-dify-app-key
```

创建方式：

```bash
cd /opt/music-shop
cp .env.example .env
vi .env
```

## 6. 首次部署步骤

### 6.1 构建并启动

```bash
cd /opt/music-shop
docker compose -f docker-compose.prod.yml build web
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml ps
```

### 6.2 初始化数据库

```bash
docker exec -it music-web python init_db.py
```

### 6.3 基础验证

```bash
curl http://127.0.0.1:5000/api/products
docker logs --tail 100 music-web
docker compose -f docker-compose.prod.yml ps
```

## 7. 自动化部署（GitHub Actions）

项目已内置三套工作流：

| 工作流 | 文件 | 用途 |
|--------|------|------|
| CI | `.github/workflows/ci.yml` | 语法检查与导入冒烟测试 |
| Deploy Production | `.github/workflows/deploy.yml` | push main 自动部署 |
| Rollback Production | `.github/workflows/rollback.yml` | 手动回滚 |

### 7.1 需要的 GitHub Secrets

仓库需配置：

| Secret | 说明 |
|--------|------|
| `SSH_HOST` | 服务器 IP 或域名 |
| `SSH_PORT` | SSH 端口 |
| `SSH_USER` | SSH 用户 |
| `SSH_PRIVATE_KEY` | 用于部署的私钥 |
| `DEPLOY_PATH` | 服务器部署目录 |

### 7.2 自动部署流程

当代码 push 到 `main` 时：

1. GitHub Actions 检出代码
2. 安装 Python 依赖
3. 执行 `py_compile` 语法检查
4. 通过 SSH 和 `rsync` 同步代码到服务器
5. 在服务器执行：
   - `docker compose build web`
   - `docker compose up -d web`
6. 执行健康检查：
   - `curl http://127.0.0.1:5000/api/products`
7. 若失败，尝试自动回滚到上一镜像

## 8. 回滚策略

### 8.1 自动回滚

部署工作流会在更新前记录当前 `music-web` 容器镜像 ID。

如果新版本部署后健康检查失败：

1. 将旧镜像重新标记为 `music-web:latest`
2. 使用 `docker compose up -d --no-build web` 恢复旧版本

### 8.2 手动回滚

可以通过 GitHub Actions 手动触发 `Rollback Production`：

- 传入 `image_id`
- 或留空，默认使用 `.deploy-meta/previous_image.txt`

服务器保存的部署元信息目录：

```bash
/opt/music-shop/.deploy-meta/
```

其中通常包含：

- `current_image.txt`
- `previous_image.txt`
- `current_sha.txt`
- `target_sha.txt`

## 9. 生产更新建议

推荐的更新顺序：

1. 在功能分支完成代码修改
2. 提交 PR
3. CI 通过后合并到 `main`
4. GitHub Actions 自动部署
5. 检查线上日志和关键接口

关键验证项：

```bash
curl -I https://你的域名
curl https://你的域名/api/products
curl https://你的域名/robots.txt
curl https://你的域名/sitemap.xml
docker logs --tail 120 music-web
```

## 10. 常见问题排查

### 10.1 容器启动成功但页面 502 / 504

排查顺序：

1. `docker compose ps`
2. `docker logs music-web`
3. `docker logs music-nginx`
4. 检查 Nginx upstream 是否指向正确端口

### 10.2 Dify 聊天接口 401 / 400

重点检查：

- `DIFIFY_API_URL`
- `DIFIFY_API_KEY`
- Dify App 是否已发布
- 模型供应商插件是否安装成功

### 10.3 编辑产品时上传图片 500

历史问题根因：

- 图片曾被写入只读的 `static/` 挂载目录

当前修复方式：

- 文件写入 `/app/uploads/products`
- 通过 `/uploads/<path:filename>` 提供访问

### 10.4 GitHub Actions 同步后部署失败

重点检查：

1. GitHub Secrets 是否完整
2. 服务器私钥是否匹配
3. `DEPLOY_PATH` 是否正确
4. 服务器是否已安装 `docker compose`
5. `.env` 是否已在服务器上存在

## 11. 不应提交到 Git 的内容

以下目录属于运行时数据，必须忽略：

- `dify/volumes/app/storage/`
- `dify/volumes/db/data/`
- `dify/volumes/redis/data/`
- `uploads/`
- `instance/`
- `output/`

这些文件现在已经加入 `.gitignore`，并建议从 Git 索引中彻底移除。

## 12. 运维常用命令

```bash
# 查看服务状态
docker compose -f docker-compose.prod.yml ps

# 查看 web 日志
docker logs --tail 120 music-web

# 重建 web
docker compose -f docker-compose.prod.yml build web
docker compose -f docker-compose.prod.yml up -d web

# 查看当前镜像
docker inspect music-web --format '{{.Image}}'

# 查看部署元信息
ls -lah /opt/music-shop/.deploy-meta
cat /opt/music-shop/.deploy-meta/current_sha.txt
cat /opt/music-shop/.deploy-meta/current_image.txt
```
