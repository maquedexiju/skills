#!/usr/bin/env python3
"""
Add aliases to entities for better search.
"""

import sqlite3
import json
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent))
from init_db import DB_PATH

# Entity aliases mapping
ENTITY_ALIASES = {
    # Commodity - Precious Metals
    "gold": ["金子", "金", "Au", "gold", "金价", "黄金价格"],
    "silver": ["银子", "Ag", "silver", "银价", "白银价格"],
    "platinum": ["Pt", "铂", "白金"],
    
    # Commodity - Energy
    "oil-crude": ["原油价格", "石油", "crude", "油价", "布伦特", "WTI"],
    "natural-gas": ["天然气价格", "gas", "天然气期货"],
    "coal": ["煤炭价格", "动力煤", "焦煤"],
    "power-consumption": ["用电量", "电力需求", "耗电量", "用电"],
    "ethanol": ["乙醇燃料", "燃料乙醇"],
    
    # Commodity - Industrial Metals
    "copper": ["铜价", "铜博士", "Cu", "沪铜"],
    "aluminum": ["铝价", "Al", "沪铝"],
    "nickel": ["镍价", "Ni", "沪镍"],
    "lithium": ["锂价", "碳酸锂", "锂盐"],
    "lithium-ore": ["锂矿石", "锂精矿", "锂矿价格"],
    
    # Commodity - Agriculture
    "corn": ["玉米价格", "玉米期货"],
    "wheat": ["小麦价格", "小麦期货"],
    "soybean": ["大豆价格", "豆子", "黄豆", "大豆期货"],
    "edible-oil": ["植物油", "食用油价格", "豆油", "菜油"],
    "soy-meal": ["豆粕价格", "豆粕期货", "饲料豆粕"],
    "pig-feed": ["生猪饲料", "猪饲料价格"],
    "pork-cycle": ["猪周期价格", "生猪价格", "猪肉价格", "猪价"],
    "feed-cost": ["饲料成本", "养殖饲料成本"],
    "livestock-cost": ["养殖成本", "畜牧养殖成本"],
    "alternative-meat": ["禽肉", "牛羊肉", "替代蛋白"],
    
    # Currency
    "usd-index": ["美元指数DXY", "美指", "DXY", "美元强弱"],
    "usd-cny": ["人民币汇率", "美元人民币汇率", "汇率", "RMB", "CNY"],
    "emerging-market-currency": ["新兴市场货币", "EM货币", "发展中国家货币"],
    
    # Macro
    "gdp": ["GDP增长率", "经济增长", "国内生产总值"],
    "cpi": ["CPI指数", "消费者物价指数", "通胀率", "物价指数"],
    "pmi": ["采购经理人指数", "制造业PMI", "PMI指数"],
    "vix": ["恐慌指数", "波动率指数", "VIX指数", "市场恐慌"],
    "economic-prosperity": ["经济景气度", "经济繁荣", "经济状况"],
    "capital-outflow": ["资金外流", "资本流出", "外资撤离"],
    "corporate-profit": ["企业盈利", "公司利润", "企业利润率"],
    "import-cost": ["进口成本指数", "进口价格"],
    "rent": ["房租", "租金价格", "房租指数"],
    
    # Policy
    "fed-rate": ["美联储利率", "联邦基金利率", "Fed利率", "美联储加息", "美联储降息", "美国利率"],
    "pbc-rate": ["央行利率", "中国央行利率", "存贷款利率", "LPR", "基准利率"],
    "real-interest-rate": ["实际利率", "真实利率", "扣除通胀利率"],
    "inflation-expectation": ["加息预期", "利率预期", "政策预期"],
    "infrastructure-investment": ["基建投资额", "基础设施投资", "基建支出"],
    "tax-cut": ["减税政策", "税收减免", "降税"],
    "subsidy-policy": ["补贴政策", "行业补贴", "政府补贴"],
    
    # Event
    "war": ["战争冲突", "军事冲突", "地缘冲突", "战争爆发"],
    "pandemic": ["疫情爆发", "传染病", "公共卫生事件", "新冠", "疫情"],
    "natural-disaster": ["自然灾害", "灾害", "洪水", "干旱", "地震"],
    "sanction": ["经济制裁", "贸易制裁", "制裁措施"],
    
    # Industry - Tech
    "ai-compute": ["AI算力", "算力需求", "计算能力", "GPU算力", "数据中心算力"],
    "semiconductor": ["芯片产业", "半导体行业", "芯片", "IC"],
    "chip": ["芯片", "GPU", "CPU", "处理器", "芯片制造"],
    "data-center": ["数据中心产业", "IDC", "机房", "数据中心建设"],
    "optical-module": ["光模块产业", "光通信", "光器件"],
    
    # Industry - Auto & Energy
    "ev": ["电动车", "电动汽车", "新能源汽车", "NEV", "电动车产业"],
    "ev-battery": ["动力电池", "锂电池产业", "电池", "EV电池"],
    "battery-industry": ["电池产业", "电池制造", "电池行业"],
    "charging-pile": ["充电桩建设", "充电设施", "充电站"],
    "new-energy-industry": ["新能源产业", "清洁能源", "可再生能源"],
    
    # Industry - Real Estate
    "real-estate": ["房地产行业", "楼市", "房地产市场", "地产"],
    "construction-infra": ["地产基建", "基建地产", "建筑基建"],
    "building-materials": ["建筑材料", "水泥", "建材行业", "建材价格"],
    "home-appliance": ["家电行业", "家用电器", "家电消费"],
    "decoration": ["家装行业", "家居装修", "装修"],
    "furniture": ["家具行业", "家具消费", "家居"],
    
    # Industry - Others
    "bank": ["银行业", "银行股", "商业银行"],
    "military-industry": ["军工行业", "国防军工", "军工股"],
    "logistics": ["物流行业", "物流运输", "快递"],
    "logistics-cost": ["物流成本指数", "运输成本", "运费"],
    "freight-rate": ["海运运费", "海运费", "运费指数", "集装箱运费"],
    "shipping-insurance": ["航运保险费", "海运保险", "船舶保险"],
    "pharmaceutical": ["医药行业", "制药", "医药股"],
    "protective-equipment": ["防护用品", "口罩", "防护服", "防疫物资"],
    "online-services": ["互联网服务", "线上平台", "电商"],
    "auto-industry": ["汽车制造业", "汽车行业", "车企"],
    "chemical-cost": ["化工成本", "化工原料成本", "化工品成本"],
    "thermal-power-profit": ["火电利润率", "火力发电利润", "火电盈利"],
    "construction-machinery": ["工程机械行业", "挖掘机", "工程设备"],
    "water-conservancy": ["水利工程", "水利建设", "水利投资"],
    "food-processing": ["食品加工业", "食品加工", "食品制造"],
    "export-enterprise": ["出口企业", "出口导向企业", "外贸企业"],
    
    # Asset & Index
    "stock-market": ["股票市场", "股市指数", "A股", "美股", "股市行情"],
    "bond-market": ["债券市场", "债市行情", "债券收益率"],
    "bond-price": ["债券价格指数", "债券行情"],
    "high-valuation-stocks": ["高估值股票", "高PE股票", "成长股"],
}


def add_aliases(conn):
    """Add aliases to entities."""
    cursor = conn.cursor()
    updated = 0
    
    for entity_id, aliases in ENTITY_ALIASES.items():
        cursor.execute('''
            UPDATE entities 
            SET aliases = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (json.dumps(aliases, ensure_ascii=False), entity_id))
        
        if cursor.rowcount > 0:
            updated += 1
    
    conn.commit()
    return updated


def main():
    print("开始添加别名...")
    
    conn = sqlite3.connect(DB_PATH)
    
    # Add aliases
    updated = add_aliases(conn)
    print(f"✅ 更新了 {updated} 个实体的别名")
    
    # Verify
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, aliases FROM entities WHERE aliases IS NOT NULL LIMIT 5")
    
    print("\n示例：")
    for row in cursor.fetchall():
        print(f"  {row[1]} ({row[0]}): {row[2]}")
    
    conn.close()
    print("\n✅ 别名添加完成")


if __name__ == "__main__":
    main()