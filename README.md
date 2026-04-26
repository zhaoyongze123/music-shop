# 音悦阁 - Flask 电商网站与 Dify 智能客服

音悦阁是一个基于 Flask 的轻量级音频设备电商网站，覆盖前台展示、购物车、订单管理、后台 CRUD、基础 SEO，以及通过 Dify 接入的智能客服能力。

当前项目主要用于展示以下能力：

- 基于 Flask 的完整网站开发
- PostgreSQL 数据建模与基础查询
- Docker Compose 生产部署
- Dify Chat App 与知识库问答集成
- 线上问题排查与修复
- GitHub Actions 自动化部署

## 1. 功能概览

### 前台功能

- 首页展示
- 产品列表 / 分类筛选 / 排序
- 产品详情页
- 搜索建议与关键词搜索
- 购物车
- 模拟结算与下单
- 订单历史
- GitHub OAuth 登录
- 全站智能客服

### 后台功能

- 管理员首页统计
- 产品新增 / 编辑 / 删除
- 图片上传
- 订单管理
- 订单状态更新

### SEO 能力

- 页面级 `title` / `description` / `keywords`
- Open Graph 标签
- `robots.txt`
- `sitemap.xml`
- 产品 `slug` 字段预留

### AI 能力

- Flask `/api/chat` 统一聊天入口
- 转发到已发布的 Dify Chat App
- 透传 `conversation_id`
- 支持多轮会话
- 知识库问答

## 2. 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python Flask |
| 数据库 | PostgreSQL |
| ORM | SQLAlchemy |
| 鉴权 | Flask-Login + GitHub OAuth |
| 前端 | Jinja2 + Bootstrap 5 + 原生 JavaScript |
| AI | Dify Chat App |
| 部署 | Docker Compose + Nginx |
| 自动化 | GitHub Actions |

## 3. 项目结构

```text
.
├── app.py                     # Flask 主应用
├── models.py                  # 数据模型
├── config.py                  # 配置文件
├── init_db.py                 # 数据初始化
├── requirements.txt           # Python 依赖
├── Dockerfile                 # Web 镜像构建
├── docker-compose.yml         # 本地开发编排
├── docker-compose.prod.yml    # 生产环境编排
├── nginx/                     # Nginx 配置
├── templates/                 # 前后台模板
├── static/                    # 静态资源
├── uploads/                   # 上传文件目录（运行时）
├── dify/                      # Dify 相关文件
└── .github/workflows/         # GitHub Actions
```

## 4. 核心路由

| 路由 | 说明 |
|------|------|
| `/` | 首页 |
| `/products` | 产品列表 |
| `/product/<id>` | 产品详情 |
| `/search` | 搜索页 |
| `/cart` | 购物车 |
| `/checkout` | 结算 |
| `/orders` | 订单历史 |
| `/admin` | 后台首页 |
| `/admin/products` | 产品管理 |
| `/admin/orders` | 订单管理 |
| `/api/chat` | AI 聊天接口 |
| `/robots.txt` | SEO 爬虫规则 |
| `/sitemap.xml` | SEO 站点地图 |

## 5. 数据模型

项目核心模型如下：

- `User`：用户、GitHub OAuth、管理员标识
- `Category`：商品分类
- `Product`：商品、品牌、库存、规格、图片、SEO slug
- `Order`：订单主表
- `OrderItem`：订单明细
- `CartItem`：购物车项目

示例索引设计：

```sql
CREATE UNIQUE INDEX idx_products_slug ON products(slug);
CREATE INDEX idx_products_category_id ON products(category_id);
CREATE INDEX idx_products_is_active ON products(is_active);
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created_at ON orders(created_at);
```

## 6. 本地开发

### 6.1 安装依赖

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 6.2 配置环境变量

创建 `.env`：

```bash
cp .env.example .env
```

推荐至少包含：

```env
FLASK_ENV=development
SECRET_KEY=replace-with-your-secret-key
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/musicdb
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
DIFIFY_API_URL=http://localhost:3000/v1
DIFIFY_API_KEY=your-dify-app-key
```

### 6.3 启动数据库

```bash
docker run -d \
  --name music-db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=musicdb \
  -p 5432:5432 \
  postgres:15
```

### 6.4 初始化数据库

```bash
python init_db.py
```

### 6.5 启动应用

```bash
flask run
```

默认访问：

- 网站首页：[http://localhost:5000](http://localhost:5000)

## 7. Dify 集成说明

当前 Flask 后端已经不再使用本地知识库直接回答，而是统一调用已发布的 Dify Chat App。

聊天链路如下：

1. 前端请求 `/api/chat`
2. Flask 读取 `message` 和 `conversation_id`
3. Flask 调用 Dify `chat-messages`
4. Dify 返回 `answer` 与新的 `conversation_id`
5. Flask 原样返回给前端

相关实现点：

- 兼容 `DIFIFY_API_URL=http://host`
- 兼容 `DIFIFY_API_URL=http://host/v1`
- 自动生成匿名用户 `user` 标识
- 支持多轮会话上下文

## 8. 图片上传说明

后台产品编辑和新建支持图片上传。

当前策略：

- 上传文件保存到可写目录 `/app/uploads/products`
- 通过 `/uploads/<path:filename>` 路由提供访问
- 避免写入只读 `static/` 挂载目录导致线上 500

## 9. 生产部署

### 9.1 生产编排

生产部署使用：

```bash
docker compose -f docker-compose.prod.yml up -d
```

主要服务：

- `music-web`：Flask Web 应用
- `music-db`：PostgreSQL
- `music-nginx`：Nginx 反向代理
- `dify-nginx`：Dify 入口代理（按需）

### 9.2 常用命令

```bash
# 启动
docker compose -f docker-compose.prod.yml up -d

# 构建并重启 Web
docker compose -f docker-compose.prod.yml build web
docker compose -f docker-compose.prod.yml up -d web

# 查看日志
docker compose -f docker-compose.prod.yml logs -f web

# 查看状态
docker compose -f docker-compose.prod.yml ps
```

## 10. GitHub Actions 自动化部署

项目已提供工作流：

- 文件路径：`.github/workflows/deploy.yml`
- 触发方式：
  - push 到 `main`
  - 手动触发 `workflow_dispatch`

### 10.1 工作流做什么

1. 检出代码
2. 建立 SSH 连接
3. 使用 `rsync` 同步仓库到服务器
4. 在服务器执行：
   - `docker compose -f docker-compose.prod.yml build web`
   - `docker compose -f docker-compose.prod.yml up -d web`

### 10.2 需要配置的 GitHub Secrets

在仓库 `Settings -> Secrets and variables -> Actions` 中配置：

| Secret | 说明 |
|--------|------|
| `SSH_HOST` | 服务器 IP 或域名 |
| `SSH_PORT` | SSH 端口，通常是 `22` |
| `SSH_USER` | 服务器用户，如 `root` |
| `SSH_PRIVATE_KEY` | 部署私钥内容 |
| `DEPLOY_PATH` | 服务器部署目录，如 `/opt/music-shop` |

### 10.3 同步排除项

工作流默认不会同步以下内容：

- `.git/`
- `.github/`
- `.env`
- `uploads/`
- `instance/`
- `output/`
- `.playwright-cli/`
- `dify/volumes/db/data/`
- `dify/volumes/redis/data/`

这样做是为了避免把本地临时文件、密钥文件、数据库运行数据错误部署到服务器。

## 11. README 面向的交付说明

如果你是把这个项目作为面试交付物，建议同时准备：

- 前台页面截图
- 后台 CRUD 截图
- Dify 问答截图
- 服务器部署截图
- GitHub Actions 成功执行截图
- Nginx / Docker / API 验证结果

## 12. 已解决的线上问题

项目当前已完成以下关键修复：

- Dify 控制台 401 / token 问题
- Dify provider 插件缺失问题
- Flask `/api/chat` 改为调用 Dify Chat App
- 产品图片上传写只读目录导致的 500 问题
- 生产环境图片上传改为走 `/uploads/` 可写目录

## 13. License

MIT
