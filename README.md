# 音悦阁 - 音乐设备电商网站

基于 Flask 的音乐设备电商网站，支持产品展示、购物车、订单、GitHub OAuth 登录和 AI 聊天机器人。

## 功能特性

- ✅ 产品展示（耳机、音响、配件）
- ✅ 产品分类、搜索、筛选
- ✅ 购物车、模拟支付
- ✅ 订单管理
- ✅ GitHub OAuth 登录
- ✅ AI 聊天机器人（RAG 知识库）
- ✅ 响应式设计

## 技术栈

- 后端: Python Flask
- 数据库: PostgreSQL + pgvector
- 前端: Bootstrap 5 + Vue.js
- AI: Dify + MiniMax API
- 部署: Docker Compose

## 快速开始

### 1. 安装依赖

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入实际值
```

### 3. 创建 GitHub OAuth App

1. 访问 https://github.com/settings/developers
2. 点击 "New OAuth App"
3. 填写信息:
   - Application name: 音悦阁 (本地)
   - Homepage URL: http://localhost:5000
   - Authorization callback URL: http://localhost:5000/github/authorized
4. 获取 Client ID 和 Client Secret
5. 填入 .env 文件

### 4. 启动数据库

```bash
# 使用 Docker
docker run -d \
  --name music-db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=musicdb \
  -p 5432:5432 \
  pgvector/pgvector:pg15
```

### 5. 初始化数据库

```bash
python init_db.py
```

### 6. 运行应用

```bash
flask run
```

访问 http://localhost:5000

## Docker 部署

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

## 项目结构

```
├── app.py              # 主应用
├── models.py           # 数据模型
├── config.py           # 配置文件
├── requirements.txt    # Python 依赖
├── init_db.py          # 数据库初始化
├── Dockerfile
├── docker-compose.yml
├── templates/          # HTML 模板
│   ├── base.html
│   ├── index.html
│   ├── products.html
│   ├── product.html
│   ├── cart.html
│   ├── checkout.html
│   ├── orders.html
│   ├── login.html
│   └── admin/          # 管理后台模板
└── static/            # 静态文件
    ├── css/
    ├── js/
    └── images/
```

## 页面路由

| 路由 | 说明 |
|------|------|
| `/` | 首页 |
| `/products` | 产品列表 |
| `/product/<id>` | 产品详情 |
| `/cart` | 购物车 |
| `/checkout` | 结算 |
| `/orders` | 订单历史 |
| `/login` | 登录 |
| `/admin` | 管理后台 |
| `/admin/products` | 产品管理 |
| `/admin/orders` | 订单管理 |

## AI 聊天机器人

聊天机器人基于 Dify 平台构建，支持 RAG（检索增强生成）。

当前 Flask 后端的 `/api/chat` 会直接调用已发布的 Dify Chat App，并透传 `conversation_id` 以保持多轮上下文。

配置步骤:
1. 部署 Dify (docker-compose.yml 中已包含)
2. 创建知识库，上传产品文档
3. 创建应用，配置 MiniMax API
4. 获取 API Key 填入 .env

## License

MIT
