"""
初始化数据库并添加示例数据
"""
import json
from app import app
from models import db, User, Category, Product

# 示例产品数据
PRODUCTS = [
    # 耳机
    {
        'name': 'Sony WH-1000XM5 无线降噪耳机',
        'brand': 'Sony',
        'model': 'WH-1000XM5',
        'description': '行业领先降噪技术，30小时续航，搭载 V1 处理器和 8 麦克风系统，为您带来沉浸式音乐体验。支持 LDAC 高解析度音频传输。',
        'price': 2699,
        'original_price': 2999,
        'category': '耳机',
        'stock': 50,
        'is_featured': True,
        'specs': {
            '驱动单元': '30mm',
            '频响范围': '4 Hz - 40,000 Hz',
            '降噪': 'AI智能降噪',
            '续航': '30小时',
            '蓝牙': '5.2',
            '支持的编解码器': 'LDAC / AAC / SBC',
            '重量': '250g',
            '颜色': '黑色、银色'
        },
        'image_url': 'https://images.unsplash.com/photo-1618366712010-f4ae9c647dcb?w=400'
    },
    {
        'name': 'Bose QuietComfort Ultra 头戴式耳机',
        'brand': 'Bose',
        'model': 'QC Ultra',
        'description': 'Bose 旗舰降噪耳机，支持空间音频，CustomTune 声音校准技术，为您量身定制完美音质。24小时超长续航。',
        'price': 3299,
        'original_price': 3499,
        'category': '耳机',
        'stock': 30,
        'is_featured': True,
        'specs': {
            '降噪': '顶级消噪',
            '空间音频': '支持',
            '续航': '24小时',
            '蓝牙': '5.3',
            '重量': '250g',
            '颜色': '黑色、白色、沙色'
        },
        'image_url': 'https://images.unsplash.com/photo-1546435770-a3e426bf472b?w=400'
    },
    {
        'name': 'Apple AirPods Pro (第二代)',
        'brand': 'Apple',
        'model': 'AirPods Pro 2',
        'description': '全新升级的 AirPods Pro，搭载 H2 芯片，支持自适应降噪和通透模式，6小时单次续航，配合充电盒可达30小时。',
        'price': 1799,
        'original_price': 1899,
        'category': '耳机',
        'stock': 100,
        'is_featured': True,
        'specs': {
            '芯片': 'H2',
            '降噪': '自适应降噪',
            '续航': '6小时（单次）/ 30小时（配合充电盒）',
            '防水': 'IPX4',
            '蓝牙': '5.3',
            '充电': 'MagSafe / Qi / Apple Watch充电器'
        },
        'image_url': 'https://images.unsplash.com/photo-1600294037681-c80b4cb5b434?w=400'
    },
    {
        'name': 'JBL Tune 510BT 无线头戴式耳机',
        'brand': 'JBL',
        'model': 'Tune 510BT',
        'description': 'JBL 经典音质，40小时续航，轻便可折叠设计，一键语音助手。性价比之选。',
        'price': 299,
        'original_price': 399,
        'category': '耳机',
        'stock': 80,
        'specs': {
            '驱动单元': '32mm',
            '频响范围': '20 Hz - 20,000 Hz',
            '续航': '40小时',
            '蓝牙': '5.0',
            '重量': '160g',
            '颜色': '黑色、白色、蓝色、粉色'
        },
        'image_url': 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400'
    },
    {
        'name': 'Sennheiser HD 660S2 Hi-Fi耳机',
        'brand': '森海塞尔',
        'model': 'HD 660S2',
        'description': '发烧级开放式 Hi-Fi 耳机，传承森海塞尔经典音质，适合古典乐、爵士乐等高要求音乐欣赏。',
        'price': 7999,
        'category': '耳机',
        'stock': 10,
        'is_featured': True,
        'specs': {
            '类型': '开放式动圈',
            '阻抗': '300 Ω',
            '频响范围': '8 Hz - 41,500 Hz',
            'THD': '<0.04%',
            '重量': '260g（不含线缆）',
            '线缆': '可拆卸6.35mm + 4.4mm'
        },
        'image_url': 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400'
    },
    # 音响
    {
        'name': 'Bose SoundLink Flex 蓝牙音箱',
        'brand': 'Bose',
        'model': 'SoundLink Flex',
        'description': '便携蓝牙音箱，IP67防水防尘，12小时续航，PositionIQ 技术自动优化音质。户外必备。',
        'price': 1299,
        'original_price': 1499,
        'category': '音响',
        'stock': 40,
        'is_featured': True,
        'specs': {
            '防水防尘': 'IP67',
            '续航': '12小时',
            '蓝牙': '5.1',
            '重量': '600g',
            '颜色': '黑色、白色、蓝色、鼠尾草绿',
            '充电': 'USB-C'
        },
        'image_url': 'https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=400'
    },
    {
        'name': 'JBL Flip 6 便携蓝牙音箱',
        'brand': 'JBL',
        'model': 'Flip 6',
        'description': 'JBL 经典便携音箱，12小时续航，IP67防水，PartyBoost 连接多台音箱。',
        'price': 999,
        'original_price': 1199,
        'category': '音响',
        'stock': 60,
        'specs': {
            '防水防尘': 'IP67',
            '续航': '12小时',
            '功率': '20W RMS',
            '蓝牙': '5.1',
            '重量': '540g',
            '颜色': '黑色、蓝色、红色、灰色'
        },
        'image_url': 'https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=400'
    },
    {
        'name': 'JBL PartyBox 310 派对音箱',
        'brand': 'JBL',
        'model': 'PartyBox 310',
        'description': '派对级音箱，240W峰值功率，灯光秀，12小时续航，麦克风和吉他输入。',
        'price': 3999,
        'category': '音响',
        'stock': 15,
        'is_featured': True,
        'specs': {
            '功率': '240W RMS',
            '续航': '12小时',
            '灯光': 'RGB灯光秀',
            '蓝牙': '5.1',
            '输入': '麦克风、吉他、游戏机',
            '重量': '17.5kg'
        },
        'image_url': 'https://images.unsplash.com/photo-1545454065-415b8e5d1b37?w=400'
    },
    {
        'name': 'Sony SRS-XB13 便携蓝牙音箱',
        'brand': 'Sony',
        'model': 'SRS-XB13',
        'description': '超便携音箱，EXTRA BASS 低音增强，16小时续航，IP67防水。',
        'price': 349,
        'category': '音响',
        'stock': 100,
        'specs': {
            'EXTRA BASS': '支持',
            '续航': '16小时',
            '防水防尘': 'IP67',
            '蓝牙': '5.0',
            '重量': '250g',
            '颜色': '黑色、蓝色、珊瑚橙、淡蓝色'
        },
        'image_url': 'https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=400'
    },
    # 配件
    {
        'name': 'AirPods Pro 无线充电盒',
        'brand': 'Apple',
        'model': 'MagSafe',
        'description': 'AirPods Pro 专用无线充电盒，支持 MagSafe 磁吸充电。',
        'price': 799,
        'category': '配件',
        'stock': 50,
        'specs': {
            '充电方式': 'MagSafe / Qi / Apple Watch',
            '兼容': 'AirPods Pro (第二代)'
        },
        'image_url': 'https://images.unsplash.com/photo-1588423771073-b8903fbb85b5?w=400'
    },
    {
        'name': '索尼 Sony IER-Z7R Hi-Fi 入耳式耳机线',
        'brand': 'Sony',
        'model': 'IER-Z7R',
        'description': '发烧级可更换耳机线，4.4mm平衡线缆，高纯度无氧铜。',
        'price': 1299,
        'category': '配件',
        'stock': 20,
        'specs': {
            '长度': '约1.2m',
            '接口': '4.4mm平衡 / 3.5mm',
            '材质': '高纯度无氧铜镀银'
        },
        'image_url': 'https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=400'
    }
]


def init_database():
    """初始化数据库"""
    with app.app_context():
        # 创建所有表
        db.create_all()
        print("数据库表已创建")

        # 检查是否已有数据
        if Product.query.first():
            print("数据库已有数据，跳过初始化")
            return

        # 创建分类
        categories = {}
        for name in ['耳机', '音响', '配件']:
            cat = Category(name=name, slug=name, description=f'{name}类产品')
            db.session.add(cat)
            categories[name] = cat
        db.session.commit()
        print("分类已创建")

        # 创建产品
        for p in PRODUCTS:
            cat_name = p.pop('category')
            product = Product(
                category_id=categories[cat_name].id,
                **p
            )
            db.session.add(product)

        db.session.commit()
        print(f"已创建 {len(PRODUCTS)} 个产品")

        print("数据库初始化完成！")


if __name__ == '__main__':
    init_database()
