"""
数据库模型 - 音乐设备电商网站
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """用户模型"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    avatar_url = db.Column(db.String(500))
    github_id = db.Column(db.String(100), unique=True)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关系
    orders = db.relationship('Order', backref='user', lazy='dynamic')

    def set_admin(self):
        """设置为管理员（第一个注册的用户）"""
        # 检查是否是第一个用户
        first_user = User.query.order_by(User.id).first()
        if first_user and first_user.id == self.id:
            self.is_admin = True
        elif not first_user:
            self.is_admin = True

    def __repr__(self):
        return f'<User {self.username}>'


class Category(db.Model):
    """产品分类"""
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)

    # 关系
    products = db.relationship('Product', backref='category', lazy='dynamic')

    def __repr__(self):
        return f'<Category {self.name}>'


class Product(db.Model):
    """产品模型"""
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    brand = db.Column(db.String(100), nullable=False)  # 品牌: Sony, Bose, JBL...
    model = db.Column(db.String(100))  # 型号
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    original_price = db.Column(db.Numeric(10, 2))  # 原价（用于显示折扣）

    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    stock = db.Column(db.Integer, default=0)  # 库存
    sold_count = db.Column(db.Integer, default=0)  # 销量

    # 产品规格 (JSON 格式存储)
    specs = db.Column(db.JSON)

    # 图片
    image_url = db.Column(db.String(500))
    images = db.Column(db.JSON)  # 多张图片

    # 状态
    is_active = db.Column(db.Boolean, default=True)
    is_featured = db.Column(db.Boolean, default=False)  # 推荐产品
    slug = db.Column(db.String(300), unique=True, index=True)  # SEO URL slug

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    order_items = db.relationship('OrderItem', backref='product', lazy='dynamic')

    def __repr__(self):
        return f'<Product {self.name}>'

    def generate_slug(self):
        """从名称生成 SEO 友好的 slug"""
        import re
        # 转换为小写，替换非字母数字为连字符
        slug = self.name.lower()
        slug = re.sub(r'[^\w\s-]', '', slug)  # 移除特殊字符
        slug = re.sub(r'[-\s]+', '-', slug)   # 连字符替换空格
        slug = slug.strip('-')[:200]           # 限制长度
        return slug

    def to_dict(self):
        """转换为字典（API 返回用）"""
        return {
            'id': self.id,
            'name': self.name,
            'brand': self.brand,
            'model': self.model,
            'description': self.description,
            'price': float(self.price),
            'original_price': float(self.original_price) if self.original_price else None,
            'category': self.category.name if self.category else None,
            'stock': self.stock,
            'specs': self.specs,
            'image_url': self.image_url,
            'is_active': self.is_active,
            'is_featured': self.is_featured
        }


class Order(db.Model):
    """订单模型"""
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False)  # 订单号

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # 金额
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    discount_amount = db.Column(db.Numeric(10, 2), default=0)

    # 地址信息（简化版）
    recipient_name = db.Column(db.String(100))
    recipient_phone = db.Column(db.String(20))
    shipping_address = db.Column(db.Text)

    # 状态: pending, paid, shipped, completed, cancelled
    status = db.Column(db.String(20), default='pending')

    # 支付信息
    payment_method = db.Column(db.String(50))  # 模拟支付
    paid_at = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    items = db.relationship('OrderItem', backref='order', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Order {self.order_number}>'

    def to_dict(self):
        return {
            'id': self.id,
            'order_number': self.order_number,
            'total_amount': float(self.total_amount),
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'items': [item.to_dict() for item in self.items]
        }


class OrderItem(db.Model):
    """订单项模型"""
    __tablename__ = 'order_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)

    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)  # 下单时的价格
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)  # 小计

    def __repr__(self):
        return f'<OrderItem {self.id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'product_name': self.product.name if self.product else None,
            'quantity': self.quantity,
            'unit_price': float(self.unit_price),
            'subtotal': float(self.subtotal)
        }


class CartItem(db.Model):
    """购物车项（会话级存储，也可以用 Redis）"""
    __tablename__ = 'cart_items'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)

    # 关系
    product = db.relationship('Product', backref='cart_items')

    def __repr__(self):
        return f'<CartItem {self.id}>'

    @property
    def subtotal(self):
        if self.product:
            return self.product.price * self.quantity
        return 0


def init_db(app):
    """初始化数据库"""
    db.init_app(app)
    with app.app_context():
        db.create_all()
