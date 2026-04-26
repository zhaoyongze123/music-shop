"""
Flask 主应用 - 音乐设备电商网站
"""
import os
import math
from functools import wraps
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, session, Response, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
import requests

from config import config
from models import db, User, Category, Product, Order, OrderItem, CartItem
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# ===========================================
# 知识库类 - 基于 TF-IDF + SiliconFlow LLM RAG
# ===========================================
class KnowledgeBase:
    """本地知识库 + SiliconFlow LLM"""

    # SiliconFlow API 配置
    SILICONFLOW_API_KEY = 'sk-kqhkdrtkctlymgoiuhbyhtokwdwdqpdjgofjjbxxgyhmhyav'
    SILICONFLOW_API_URL = 'https://api.siliconflow.cn/v1/chat/completions'
    LLM_MODEL = 'Qwen/Qwen2.5-7B-Instruct'

    SYSTEM_PROMPT = """你是一个专业的音频设备客服助手，名为"音悦阁小助手"。
你有丰富的音频设备知识，包括耳机、音箱等各类产品。
请根据以下知识库内容回答用户的问题。如果知识库中没有相关信息，请说明并建议联系人工客服。
回答要专业、友好、有帮助。"""

    def __init__(self, kb_file='products_kb.md'):
        self.kb_file = kb_file
        self.chunks = []
        self.vectorizer = TfidfVectorizer(max_features=1000, ngram_range=(1, 2))
        self._load_knowledge_base()

    def _load_knowledge_base(self):
        """加载知识库文件并分块"""
        try:
            with open(self.kb_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # 按标题和章节分割
            sections = re.split(r'\n(?=## )', content)

            for section in sections:
                if len(section.strip()) > 50:
                    # 进一步按段落分割
                    paragraphs = re.split(r'\n(?=#### |### |\n\n)', section)
                    for para in paragraphs:
                        para = para.strip()
                        if len(para) > 30:
                            self.chunks.append(para)

            # 如果分割太少，按固定长度分割
            if len(self.chunks) < 10:
                with open(self.kb_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                lines = content.split('\n')
                current_chunk = []
                for line in lines:
                    current_chunk.append(line)
                    if len('\n'.join(current_chunk)) > 500:
                        chunk_text = '\n'.join(current_chunk).strip()
                        if chunk_text:
                            self.chunks.append(chunk_text)
                        current_chunk = []
                if current_chunk:
                    chunk_text = '\n'.join(current_chunk).strip()
                    if chunk_text:
                        self.chunks.append(chunk_text)

        except FileNotFoundError:
            self.chunks = []

    def search(self, query, top_k=3):
        """搜索最相关的知识库片段"""
        if not self.chunks:
            return []

        try:
            # 计算 TF-IDF
            tfidf_matrix = self.vectorizer.fit_transform(self.chunks + [query])
            query_vector = tfidf_matrix[-1]
            content_vectors = tfidf_matrix[:-1]

            # 计算相似度
            similarities = cosine_similarity(query_vector, content_vectors)[0]

            # 获取 top_k 最相似的
            top_indices = np.argsort(similarities)[-top_k:][::-1]

            results = []
            for idx in top_indices:
                if similarities[idx] > 0.05:  # 阈值
                    results.append({
                        'content': self.chunks[idx],
                        'score': float(similarities[idx])
                    })
            return results
        except Exception:
            return []

    def _call_llm(self, context, question):
        """调用 SiliconFlow LLM"""
        try:
            import urllib.request
            import json

            # 限制上下文长度，避免 LLM 输出混乱
            max_context_len = 2000
            if len(context) > max_context_len:
                context = context[:max_context_len] + "\n\n(...)"

            data = {
                'model': self.LLM_MODEL,
                'messages': [
                    {'role': 'system', 'content': self.SYSTEM_PROMPT},
                    {'role': 'user', 'content': f"请根据以下知识库内容回答用户问题。\n\n知识库：\n{context}\n\n用户问题：{question}"}
                ],
                'temperature': 0.7,
                'max_tokens': 400
            }

            req = urllib.request.Request(
                self.SILICONFLOW_API_URL,
                data=json.dumps(data).encode('utf-8'),
                headers={
                    'Authorization': f'Bearer {self.SILICONFLOW_API_KEY}',
                    'Content-Type': 'application/json'
                },
                method='POST'
            )

            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result['choices'][0]['message']['content']

        except Exception as e:
            print(f"LLM 调用失败: {e}")
            return None

    def answer(self, question):
        """基于知识库 + LLM 回答问题"""
        results = self.search(question, top_k=3)

        if not results:
            return "抱歉，我在知识库中没有找到相关信息。建议您联系客服获取帮助。"

        # 构建上下文
        context = "\n\n".join([r['content'] for r in results])

        # 调用 LLM
        llm_answer = self._call_llm(context, question)

        if llm_answer:
            return llm_answer

        # 如果 LLM 调用失败，返回知识库内容
        return f"根据产品知识库，我找到了一些相关信息：\n\n{results[0]['content'][:800]}...\n\n如需了解更多，请联系我们的客服。"

# 创建知识库实例
kb = KnowledgeBase()


def _build_dify_chat_endpoint():
    """构建 Dify chat-messages 接口地址，兼容是否已包含 /v1。"""
    base_url = (app.config.get('DIFIFY_API_URL') or '').strip()
    if not base_url:
        raise ValueError('未配置 DIFIFY_API_URL')

    normalized = base_url.rstrip('/')
    if normalized.endswith('/chat-messages'):
        return normalized
    if normalized.endswith('/v1'):
        return f'{normalized}/chat-messages'
    return f'{normalized}/v1/chat-messages'


def _build_dify_user_id():
    """为 Dify 生成稳定的 end user 标识。"""
    if current_user.is_authenticated:
        return f'musicshop-user-{current_user.id}'

    anon_id = session.get('anon_chat_user_id')
    if not anon_id:
        import secrets
        anon_id = f'musicshop-guest-{secrets.token_hex(8)}'
        session['anon_chat_user_id'] = anon_id
    return anon_id


def _call_dify_chat(message, conversation_id=None):
    """调用已发布的 Dify Chat App。"""
    api_key = (app.config.get('DIFIFY_API_KEY') or '').strip()
    if not api_key or api_key == 'your-dify-api-key':
        raise ValueError('未配置有效的 DIFIFY_API_KEY')

    endpoint = _build_dify_chat_endpoint()
    payload = {
        'inputs': {},
        'query': message,
        'response_mode': 'blocking',
        'user': _build_dify_user_id()
    }
    if conversation_id:
        payload['conversation_id'] = conversation_id

    response = requests.post(
        endpoint,
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        },
        json=payload,
        timeout=90
    )

    if response.status_code >= 400:
        detail = response.text.strip() or f'HTTP {response.status_code}'
        raise RuntimeError(f'Dify 请求失败: {detail}')

    data = response.json()
    answer = data.get('answer')
    if not answer:
        raise RuntimeError(f'Dify 返回异常: {data}')

    return {
        'answer': answer,
        'conversation_id': data.get('conversation_id')
    }

# Flask 应用
app = Flask(__name__)
app.config.from_object(config[os.environ.get('FLASK_ENV', 'default')])
UPLOAD_ROOT = os.path.join(app.root_path, 'uploads')
PRODUCT_UPLOAD_DIR = os.path.join(UPLOAD_ROOT, 'products')

# 初始化扩展
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = '请先登录'

# GitHub OAuth 配置
GITHUB_CLIENT_ID = app.config['GITHUB_OAUTH_CLIENT_ID']
GITHUB_CLIENT_SECRET = app.config['GITHUB_OAUTH_CLIENT_SECRET']


def save_product_image(image_file):
    """保存产品图片到可写卷，并返回可访问 URL。"""
    filename = secure_filename(image_file.filename)
    os.makedirs(PRODUCT_UPLOAD_DIR, exist_ok=True)
    filepath = os.path.join(PRODUCT_UPLOAD_DIR, filename)
    image_file.save(filepath)
    return url_for('uploaded_file', filename=f'products/{filename}')


@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """提供上传文件访问。"""
    return send_from_directory(UPLOAD_ROOT, filename)


@app.route('/login/github')
def github_login():
    """发起 GitHub OAuth 登录"""
    import secrets
    state = secrets.token_hex(16)
    session['oauth_state'] = state

    # 强制使用 https
    callback_url = 'https://musicshop.zyzsharehub.cn/github/callback'
    github_auth_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}"
        f"&redirect_uri={callback_url}"
        f"&scope=read:user"
        f"&state={state}"
    )
    return redirect(github_auth_url)


@app.route('/github/callback')
def github_callback():
    """GitHub OAuth 回调处理"""
    # 验证 state
    state = request.args.get('state')
    if state != session.get('oauth_state'):
        flash('OAuth 状态验证失败', 'error')
        return redirect(url_for('login'))

    code = request.args.get('code')
    if not code:
        flash('未收到授权码', 'error')
        return redirect(url_for('login'))

    # 用 code 换取 access_token
    import urllib.parse
    token_url = 'https://github.com/login/oauth/access_token'
    callback_url = 'https://musicshop.zyzsharehub.cn/github/callback'
    token_data = {
        'client_id': GITHUB_CLIENT_ID,
        'client_secret': GITHUB_CLIENT_SECRET,
        'code': code,
        'redirect_uri': callback_url
    }

    try:
        token_resp = requests.post(token_url, data=token_data, headers={'Accept': 'application/json'}, timeout=10)
        token_result = token_resp.json()

        if 'error' in token_result:
            flash(f"获取 token 失败: {token_result.get('error_description', token_result.get('error'))}", 'error')
            return redirect(url_for('login'))

        access_token = token_result.get('access_token')

        # 获取用户信息
        user_resp = requests.get(
            'https://api.github.com/user',
            headers={
                'Authorization': f"Bearer {access_token}",
                'Accept': 'application/json'
            },
            timeout=10
        )
        user_data = user_resp.json()

        github_id = str(user_data.get('id'))
        username = user_data.get('login') or user_data.get('name')
        avatar_url = user_data.get('avatar_url')
        email = user_data.get('email')

        # 查找或创建用户
        user = User.query.filter_by(github_id=github_id).first()

        if not user:
            user = User(
                username=username,
                email=email,
                avatar_url=avatar_url,
                github_id=github_id
            )
            db.session.add(user)
            db.session.commit()
            user.set_admin()
            db.session.commit()
            flash(f'欢迎 {username}！您是第 {user.id} 位用户', 'success')
        else:
            flash(f'欢迎回来 {user.username}！', 'success')

        login_user(user)
        next_page = session.get('next') or url_for('index')
        return redirect(next_page)

    except requests.RequestException as e:
        flash(f'网络错误: {str(e)}', 'error')
        return redirect(url_for('login'))


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ==================== 页面路由 ====================

@app.route('/')
def index():
    """首页"""
    # 获取推荐产品
    featured_products = Product.query.filter_by(
        is_active=True,
        is_featured=True
    ).limit(8).all()

    # 获取分类
    categories = Category.query.all()

    # 获取新品
    new_products = Product.query.filter_by(
        is_active=True
    ).order_by(Product.created_at.desc()).limit(4).all()

    return render_template('index.html',
                           featured_products=featured_products,
                           new_products=new_products,
                           categories=categories)


@app.route('/mothers-day')
def mothers_day():
    """母亲节专题页"""
    # 获取精选产品用于展示
    featured_products = Product.query.filter_by(
        is_active=True
    ).order_by(Product.created_at.desc()).limit(4).all()

    # 如果没有产品，使用一些示例数据
    if not featured_products:
        featured_products = []

    return render_template('mothers_day.html',
                           featured_products=featured_products)


@app.route('/products')
def products():
    """产品列表"""
    page = request.args.get('page', 1, type=int)
    category_slug = request.args.get('category')
    sort = request.args.get('sort', 'newest')
    search = request.args.get('q', '')

    query = Product.query.filter_by(is_active=True)

    # 分类筛选
    if category_slug:
        category = Category.query.filter_by(slug=category_slug).first()
        if category:
            query = query.filter_by(category_id=category.id)

    # 搜索
    if search:
        query = query.filter(
            db.or_(
                Product.name.ilike(f'%{search}%'),
                Product.brand.ilike(f'%{search}%'),
                Product.description.ilike(f'%{search}%')
            )
        )

    # 排序
    if sort == 'price_low':
        query = query.order_by(Product.price.asc())
    elif sort == 'price_high':
        query = query.order_by(Product.price.desc())
    elif sort == 'sales':
        query = query.order_by(Product.sold_count.desc())
    else:  # newest
        query = query.order_by(Product.created_at.desc())

    # 分页
    per_page = 12
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    products = pagination.items

    categories = Category.query.all()

    return render_template('products.html',
                           products=pagination,
                           pagination=pagination,
                           categories=categories,
                           current_category=category_slug,
                           current_sort=sort,
                           search_query=search)


@app.route('/product/<int:product_id>')
def product_detail(product_id):
    """产品详情"""
    product = Product.query.get_or_404(product_id)

    # 获取同分类的其他产品
    related_products = Product.query.filter(
        Product.category_id == product.category_id,
        Product.id != product.id,
        Product.is_active == True
    ).limit(4).all()

    # 生成 JSON-LD 结构化数据
    product_jsonld = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": product.name,
        "description": product.description or "",
        "image": product.image_url or "",
        "brand": {
            "@type": "Brand",
            "name": product.brand
        },
        "sku": str(product.id),
        "url": url_for('product_detail', product_id=product.id, _external=True),
        "offers": {
            "@type": "Offer",
            "url": url_for('product_detail', product_id=product.id, _external=True),
            "priceCurrency": "CNY",
            "price": float(product.price),
            "availability": "https://schema.org/InStock" if product.stock > 0 else "https://schema.org/OutOfStock",
            "seller": {
                "@type": "Organization",
                "name": "音悦阁"
            }
        }
    }

    # 添加规格属性
    if product.specs:
        product_jsonld["additionalProperty"] = [
            {"@type": "PropertyValue", "name": key, "value": value}
            for key, value in product.specs.items() if value
        ]

    return render_template('product.html',
                           product=product,
                           related_products=related_products,
                           product_jsonld=product_jsonld)


@app.route('/search')
def search():
    """搜索结果"""
    query = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)

    if query:
        products = Product.query.filter(
            Product.is_active == True,
            db.or_(
                Product.name.ilike(f'%{query}%'),
                Product.brand.ilike(f'%{query}%'),
                Product.description.ilike(f'%{query}%')
            )
        ).paginate(page=page, per_page=12, error_out=False)
    else:
        products = None

    return render_template('search.html', products=products, query=query)


@app.route('/cart')
@login_required
def cart():
    """购物车"""
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()

    total = sum(item.subtotal for item in cart_items)

    return render_template('cart.html', cart_items=cart_items, total=total)


@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    """结算"""
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()

    if not cart_items:
        flash('购物车是空的', 'warning')
        return redirect(url_for('cart'))

    total = sum(item.subtotal for item in cart_items)

    if request.method == 'POST':
        # 模拟支付 - 直接成功
        order = create_order(current_user.id, cart_items)
        flash(f'订单 {order.order_number} 创建成功！', 'success')
        return redirect(url_for('order_success', order_id=order.id))

    return render_template('checkout.html', cart_items=cart_items, total=total)


@app.route('/order/<int:order_id>/success')
@login_required
def order_success(order_id):
    """订单成功"""
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        abort(403)

    return render_template('order_success.html', order=order)


@app.route('/orders')
@login_required
def orders():
    """订单历史"""
    page = request.args.get('page', 1, type=int)
    orders = Order.query.filter_by(
        user_id=current_user.id
    ).order_by(Order.created_at.desc()).paginate(page=page, per_page=10, error_out=False)

    return render_template('orders.html', orders=orders)


@app.route('/order/<int:order_id>')
@login_required
def order_detail(order_id):
    """订单详情"""
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        abort(403)

    return render_template('order_detail.html', order=order)


# ==================== 认证路由 ====================

@app.route('/login')
def login():
    """登录页"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    return render_template('login.html')


@app.route('/github/authorized')
def github_authorized():
    """GitHub OAuth 回调"""
    if not github.authorized:
        flash('GitHub 授权失败', 'error')
        return redirect(url_for('login'))

    resp = github.get('/user')
    if not resp.ok:
        flash('获取用户信息失败', 'error')
        return redirect(url_for('login'))

    github_data = resp.json()
    github_id = str(github_data.get('id'))
    username = github_data.get('login') or github_data.get('name')
    avatar_url = github_data.get('avatar_url')
    email = github_data.get('email')

    # 查找或创建用户
    user = User.query.filter_by(github_id=github_id).first()

    if not user:
        # 新用户
        user = User(
            username=username,
            email=email,
            avatar_url=avatar_url,
            github_id=github_id
        )
        db.session.add(user)
        db.session.commit()

        # 检查是否是第一个用户（设为管理员）
        user.set_admin()
        db.session.commit()

        flash(f'欢迎 {username}！您是第 {user.id} 位用户', 'success')
    else:
        flash(f'欢迎回来 {user.username}！', 'success')

    login_user(user)

    # 重定向到之前页面或首页
    next_page = session.get('next') or url_for('index')
    return redirect(next_page)


@app.route('/logout')
@login_required
def logout():
    """登出"""
    logout_user()
    flash('已退出登录', 'info')
    return redirect(url_for('index'))


# ==================== 管理后台路由 ====================

@app.route('/admin')
@login_required
def admin_index():
    """管理后台首页"""
    if not current_user.is_admin:
        flash('需要管理员权限', 'error')
        return redirect(url_for('index'))

    from datetime import datetime, timedelta

    # 基础统计
    total_users = User.query.count()
    total_products = Product.query.count()
    total_orders = Order.query.count()
    total_revenue = db.session.query(db.func.sum(Order.total_amount)).filter(
        Order.status == 'paid'
    ).scalar() or 0

    # 最近订单
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()

    # ==================== 数据分析 ====================

    # 1. 每周销量（过去 8 周）
    weekly_labels = []
    weekly_data = []
    today = datetime.now()
    for i in range(7, -1, -1):
        week_start = today - timedelta(days=today.weekday() + 7 * i)
        week_end = week_start + timedelta(days=7)
        week_label = week_start.strftime('%m/%d')
        weekly_labels.append(week_label)
        week_count = Order.query.filter(
            Order.created_at >= week_start,
            Order.created_at < week_end
        ).count()
        weekly_data.append(week_count)

    # 2. 每月销量（过去 6 个月）
    monthly_labels = []
    monthly_data = []
    for i in range(5, -1, -1):
        # 使用 calendar 模块正确计算月初和月末
        import calendar
        month_date = today.replace(day=1) - timedelta(days=30 * i)
        month_start = month_date.replace(day=1)
        # 正确计算下月第一天
        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1, day=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1, day=1)
        monthly_labels.append(month_start.strftime('%Y-%m'))
        month_count = Order.query.filter(
            Order.created_at >= month_start,
            Order.created_at < month_end,
            Order.status == 'paid'
        ).with_entities(db.func.sum(Order.total_amount)).scalar() or 0
        monthly_data.append(float(month_count))

    # 3. 产品销量排行（Top 10）
    top_products = db.session.query(
        Product.name,
        Product.brand,
        db.func.sum(OrderItem.quantity).label('sold')
    ).select_from(Product).join(
        OrderItem, OrderItem.product_id == Product.id
    ).join(
        Order, Order.id == OrderItem.order_id
    ).filter(
        Order.status == 'paid'
    ).group_by(Product.id).order_by(
        db.func.sum(OrderItem.quantity).desc()
    ).limit(10).all()

    top_product_labels = [p.name[:20] for p in top_products]
    top_product_data = [int(p.sold) for p in top_products]

    # 4. 分类销量占比
    category_sales = db.session.query(
        Category.name,
        db.func.sum(OrderItem.quantity).label('sold')
    ).select_from(Category).join(
        Product, Product.category_id == Category.id
    ).join(
        OrderItem, OrderItem.product_id == Product.id
    ).join(
        Order, Order.id == OrderItem.order_id
    ).filter(
        Order.status == 'paid'
    ).group_by(Category.id).all()

    category_labels = [c.name for c in category_sales] if category_sales else ['暂无数据']
    category_data = [int(c.sold) for c in category_sales] if category_sales else [0]

    # 5. 本月 vs 上月对比
    this_month_start = today.replace(day=1)
    if today.month == 1:
        last_month_start = today.replace(year=today.year - 1, month=12, day=1)
    else:
        last_month_start = today.replace(month=today.month - 1, day=1)
    last_month_end = this_month_start

    this_month_orders = Order.query.filter(
        Order.created_at >= this_month_start,
        Order.status == 'paid'
    ).count()

    last_month_orders = Order.query.filter(
        Order.created_at >= last_month_start,
        Order.created_at < last_month_end,
        Order.status == 'paid'
    ).count()

    this_month_revenue = Order.query.filter(
        Order.created_at >= this_month_start,
        Order.status == 'paid'
    ).with_entities(db.func.sum(Order.total_amount)).scalar() or 0

    last_month_revenue = Order.query.filter(
        Order.created_at >= last_month_start,
        Order.created_at < last_month_end,
        Order.status == 'paid'
    ).with_entities(db.func.sum(Order.total_amount)).scalar() or 0

    # 计算增长率
    order_growth = ((this_month_orders - last_month_orders) / last_month_orders * 100) if last_month_orders else 0
    revenue_growth = ((float(this_month_revenue) - float(last_month_revenue)) / float(last_month_revenue) * 100) if last_month_revenue else 0

    # 6. 库存预警（库存 < 10 的产品）
    low_stock_products = Product.query.filter(
        Product.stock < 10,
        Product.is_active == True
    ).all()

    return render_template('admin/index.html',
                           total_users=total_users,
                           total_products=total_products,
                           total_orders=total_orders,
                           total_revenue=total_revenue,
                           recent_orders=recent_orders,
                           weekly_labels=weekly_labels,
                           weekly_data=weekly_data,
                           monthly_labels=monthly_labels,
                           monthly_data=monthly_data,
                           top_product_labels=top_product_labels,
                           top_product_data=top_product_data,
                           category_labels=category_labels,
                           category_data=category_data,
                           this_month_orders=this_month_orders,
                           order_growth=order_growth,
                           this_month_revenue=this_month_revenue,
                           revenue_growth=revenue_growth,
                           low_stock_products=low_stock_products)


@app.route('/admin/products')
@login_required
def admin_products():
    """产品管理"""
    if not current_user.is_admin:
        abort(403)

    page = request.args.get('page', 1, type=int)
    products = Product.query.order_by(Product.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )

    return render_template('admin/products.html', products=products)


@app.route('/admin/products/new', methods=['GET', 'POST'])
@login_required
def admin_product_new():
    """新建产品"""
    if not current_user.is_admin:
        abort(403)

    if request.method == 'POST':
        # 处理图片上传
        image_url = request.form.get('image_url')
        image_file = request.files.get('image_file')
        if image_file and image_file.filename:
            image_url = save_product_image(image_file)

        # 处理规格JSON（用户友好的格式）
        specs_json = request.form.get('specs_json', '{}')

        product = Product(
            name=request.form.get('name'),
            brand=request.form.get('brand'),
            model=request.form.get('model'),
            description=request.form.get('description'),
            price=float(request.form.get('price')),
            original_price=float(request.form.get('original_price')) if request.form.get('original_price') else None,
            category_id=int(request.form.get('category_id')) if request.form.get('category_id') else None,
            stock=int(request.form.get('stock', 0)),
            specs=specs_json,
            image_url=image_url,
            is_active='is_active' in request.form
        )
        db.session.add(product)
        db.session.commit()
        flash('产品创建成功', 'success')
        return redirect(url_for('admin_products'))

    categories = Category.query.all()
    return render_template('admin/product_form.html', product=None, categories=categories)


@app.route('/admin/products/<int:product_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_product_edit(product_id):
    """编辑产品"""
    if not current_user.is_admin:
        abort(403)

    product = Product.query.get_or_404(product_id)

    if request.method == 'POST':
        product.name = request.form.get('name')
        product.brand = request.form.get('brand')
        product.model = request.form.get('model')
        product.description = request.form.get('description')
        product.price = float(request.form.get('price'))
        if request.form.get('original_price'):
            product.original_price = float(request.form.get('original_price'))
        product.category_id = int(request.form.get('category_id')) if request.form.get('category_id') else None
        product.stock = int(request.form.get('stock', 0))

        # 处理规格JSON
        product.specs = request.form.get('specs_json', '{}')

        # 处理图片上传
        image_file = request.files.get('image_file')
        if image_file and image_file.filename:
            product.image_url = save_product_image(image_file)
        elif request.form.get('image_url'):
            product.image_url = request.form.get('image_url')

        product.is_active = 'is_active' in request.form

        db.session.commit()
        flash('产品更新成功', 'success')
        return redirect(url_for('admin_products'))

    categories = Category.query.all()
    return render_template('admin/product_form.html', product=product, categories=categories)


@app.route('/admin/products/<int:product_id>/delete', methods=['POST'])
@login_required
def admin_product_delete(product_id):
    """删除产品"""
    if not current_user.is_admin:
        abort(403)

    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash('产品已删除', 'success')
    return redirect(url_for('admin_products'))


@app.route('/admin/orders')
@login_required
def admin_orders():
    """订单管理"""
    if not current_user.is_admin:
        abort(403)

    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')

    query = Order.query
    if status:
        query = query.filter_by(status=status)

    orders = query.order_by(Order.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )

    return render_template('admin/orders.html', orders=orders, current_status=status)


@app.route('/admin/orders/<int:order_id>/update-status', methods=['POST'])
@login_required
def admin_order_update_status(order_id):
    """更新订单状态"""
    if not current_user.is_admin:
        abort(403)

    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')

    if new_status in ['pending', 'paid', 'shipped', 'completed', 'cancelled']:
        order.status = new_status
        db.session.commit()
        flash(f'订单状态已更新为 {new_status}', 'success')

    return redirect(url_for('admin_orders'))


# ==================== API 路由 ====================

@app.route('/api/cart/add', methods=['POST'])
@login_required
def api_cart_add():
    """添加到购物车"""
    data = request.get_json()
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)

    product = Product.query.get_or_404(product_id)

    # 检查库存
    if product.stock < quantity:
        return jsonify({'success': False, 'message': '库存不足'})

    # 检查是否已在购物车
    cart_item = CartItem.query.filter_by(
        user_id=current_user.id,
        product_id=product_id
    ).first()

    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = CartItem(
            user_id=current_user.id,
            product_id=product_id,
            quantity=quantity
        )
        db.session.add(cart_item)

    db.session.commit()

    return jsonify({'success': True, 'message': '已添加到购物车'})


@app.route('/api/cart/update', methods=['POST'])
@login_required
def api_cart_update():
    """更新购物车数量"""
    data = request.get_json()
    cart_id = data.get('cart_id')
    quantity = data.get('quantity')

    cart_item = CartItem.query.filter_by(
        id=cart_id,
        user_id=current_user.id
    ).first_or_404()

    if quantity <= 0:
        db.session.delete(cart_item)
    else:
        cart_item.quantity = quantity

    db.session.commit()

    return jsonify({'success': True})


@app.route('/api/cart/remove', methods=['POST'])
@login_required
def api_cart_remove():
    """从购物车移除"""
    data = request.get_json()
    cart_id = data.get('cart_id')

    cart_item = CartItem.query.filter_by(
        id=cart_id,
        user_id=current_user.id
    ).first()

    if cart_item:
        db.session.delete(cart_item)
        db.session.commit()

    return jsonify({'success': True})


@app.route('/api/chat', methods=['POST'])
def api_chat():
    """AI 聊天接口（Dify Chat App）"""
    data = request.get_json()
    message = data.get('message', '')
    conversation_id = data.get('conversation_id')

    if not message:
        return jsonify({'error': '消息不能为空'}), 400

    try:
        result = _call_dify_chat(message, conversation_id=conversation_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'AI 服务暂时不可用: {str(e)}'}), 500


@app.route('/api/products')
def api_products():
    """产品列表 API"""
    category_id = request.args.get('category_id', type=int)
    featured = request.args.get('featured', type=bool)

    query = Product.query.filter_by(is_active=True)

    if category_id:
        query = query.filter_by(category_id=category_id)

    if featured:
        query = query.filter_by(is_featured=True)

    products = query.limit(20).all()

    return jsonify([p.to_dict() for p in products])


@app.route('/api/search/suggestions')
def api_search_suggestions():
    """搜索建议 API - 返回实时搜索建议"""
    query = request.args.get('q', '').strip()

    if not query:
        return jsonify({'suggestions': []})

    # 搜索产品
    products = Product.query.filter(
        Product.is_active == True,
        db.or_(
            Product.name.ilike(f'%{query}%'),
            Product.brand.ilike(f'%{query}%'),
            Product.description.ilike(f'%{query}%')
        )
    ).limit(8).all()

    suggestions = []
    for product in products:
        suggestions.append({
            'name': product.name,
            'brand': product.brand,
            'category': product.category.name if product.category else '',
            'price': float(product.price) if product.price else 0,
            'image': product.image_url or '',
            'url': url_for('product_detail', product_id=product.id)
        })

    # 如果没有产品结果，添加分类和品牌的建议
    if not suggestions and len(query) >= 2:
        # 搜索匹配的分类
        categories = Category.query.filter(
            Category.name.ilike(f'%{query}%')
        ).limit(3).all()

        for cat in categories:
            suggestions.append({
                'name': f'{cat.name} 系列',
                'brand': '',
                'category': '分类',
                'price': 0,
                'image': '',
                'url': url_for('products', category=cat.slug)
            })

    return jsonify({'suggestions': suggestions})


# ==================== 辅助函数 ====================

def create_order(user_id, cart_items):
    """创建订单"""
    from datetime import datetime
    import random
    import string

    # 生成订单号
    order_number = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}{''.join(random.choices(string.digits, k=4))}"

    # 计算总金额
    total_amount = sum(item.subtotal for item in cart_items)

    # 创建订单
    order = Order(
        order_number=order_number,
        user_id=user_id,
        total_amount=total_amount,
        status='paid',  # 模拟支付直接成功
        payment_method='模拟支付',
        paid_at=datetime.utcnow()
    )
    db.session.add(order)

    # 创建订单项并扣减库存
    for cart_item in cart_items:
        order_item = OrderItem(
            order=order,
            product_id=cart_item.product_id,
            quantity=cart_item.quantity,
            unit_price=cart_item.product.price,
            subtotal=cart_item.product.price * cart_item.quantity
        )
        db.session.add(order_item)

        # 扣减库存
        cart_item.product.stock -= cart_item.quantity
        cart_item.product.sold_count += cart_item.quantity

    db.session.commit()

    # 清空购物车
    CartItem.query.filter_by(user_id=user_id).delete()
    db.session.commit()

    return order


# ==================== SEO 路由 ====================

@app.route('/robots.txt')
def robots_txt():
    """robots.txt - 允许爬虫访问，屏蔽管理后台"""
    content = """User-agent: *
Allow: /
Disallow: /admin/
Disallow: /orders/
Disallow: /order/
Disallow: /cart/
Disallow: /checkout/
Disallow: /api/
Disallow: /github/

Sitemap: {scheme}://{host}/sitemap.xml
""".format(scheme=request.scheme, host=request.host)
    return Response(content, mimetype='text/plain')


@app.route('/sitemap.xml')
def sitemap_xml():
    """sitemap.xml - XML 站点地图"""
    from datetime import datetime

    urls = []

    # 首页
    urls.append({
        'loc': url_for('index', _external=True),
        'changefreq': 'daily',
        'priority': '1.0'
    })

    # 产品列表
    urls.append({
        'loc': url_for('products', _external=True),
        'changefreq': 'daily',
        'priority': '0.9'
    })

    # 所有产品详情页
    for product in Product.query.filter_by(is_active=True).all():
        product_url = url_for('product_detail', product_id=product.id, _external=True)
        urls.append({
            'loc': product_url,
            'lastmod': product.updated_at.strftime('%Y-%m-%d') if product.updated_at else None,
            'changefreq': 'weekly',
            'priority': '0.8'
        })

    # 所有分类
    for category in Category.query.all():
        cat_url = url_for('products', category_slug=category.slug, _external=True)
        urls.append({
            'loc': cat_url,
            'changefreq': 'weekly',
            'priority': '0.7'
        })

    # 生成 XML
    xml = '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'''
    for url in urls:
        xml += f'''
  <url>
    <loc>{url['loc']}</loc>'''
        if url.get('lastmod'):
            xml += f'''
    <lastmod>{url['lastmod']}</lastmod>'''
        xml += f'''
    <changefreq>{url['changefreq']}</changefreq>
    <priority>{url['priority']}</priority>
  </url>'''
    xml += '''
</urlset>'''

    return Response(xml, mimetype='application/xml')


# ==================== 启动 ====================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5005))
    app.run(host='0.0.0.0', port=port, debug=True)
