import os
from dotenv import load_dotenv

# 优先加载环境变量
load_dotenv(override=True)


class Config:
    """基础配置"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

    # 数据库
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://postgres:postgres@localhost:5432/musicdb'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # GitHub OAuth
    GITHUB_OAUTH_CLIENT_ID = os.environ.get('GITHUB_CLIENT_ID') or 'your-github-client-id'
    GITHUB_OAUTH_CLIENT_SECRET = os.environ.get('GITHUB_CLIENT_SECRET') or 'your-github-client-secret'

    # Dify API
    DIFIFY_API_URL = os.environ.get('DIFIFY_API_URL') or 'http://localhost:8080'
    DIFIFY_API_KEY = os.environ.get('DIFIFY_API_KEY') or 'your-dify-api-key'

    # MiniMax API
    MINIMAX_API_KEY = os.environ.get('MINIMAX_API_KEY') or 'your-minimax-api-key'

    # 分页
    ITEMS_PER_PAGE = 12


class DevelopmentConfig(Config):
    """开发环境"""
    DEBUG = True


class ProductionConfig(Config):
    """生产环境"""
    DEBUG = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
