#!/usr/bin/env python3
"""
Batch import relations from correlations.md data.
"""

import sqlite3
import json
from pathlib import Path
from init_db import DB_PATH

# New entities to add
NEW_ENTITIES = [
    # Energy & Power
    ("power-consumption", "电力消耗", "Power Consumption", "commodity", "energy", "indicator", "TWh", "用电量"),
    ("logistics-cost", "物流成本", "Logistics Cost", "industry", "transport", "indicator", "index", "运输成本指数"),
    ("chemical-cost", "化工成本", "Chemical Cost", "industry", "chemical", "indicator", "index", "化工原料成本"),
    ("thermal-power-profit", "火电利润", "Thermal Power Profit", "industry", "energy", "indicator", "margin", "火力发电利润"),
    
    # Interest Rate
    ("real-interest-rate", "实际利率", "Real Interest Rate", "policy", "central-bank", "indicator", "%", "扣除通胀后的实际利率"),
    
    # Metals
    ("platinum", "铂金", "Platinum", "commodity", "precious-metal", "asset", "USD/oz", "贵金属，汽车催化剂"),
    
    # Industry
    ("auto-industry", "汽车行业", "Auto Industry", "industry", "automotive", "industry", None, "汽车制造业"),
    ("economic-prosperity", "经济景气", "Economic Prosperity", "macro", "growth", "indicator", "index", "经济景气度"),
    ("new-energy-industry", "新能源产业", "New Energy Industry", "industry", "energy", "industry", None, "新能源相关产业"),
    ("construction-infra", "地产基建", "Construction & Infra", "industry", "property", "industry", None, "房地产与基础设施建设"),
    ("battery-industry", "电池产业", "Battery Industry", "industry", "manufacturing", "industry", None, "动力电池产业"),
    
    # Events related
    ("military-industry", "军工", "Military Industry", "industry", "defense", "industry", None, "国防军工"),
    ("shipping-insurance", "航运保险", "Shipping Insurance", "industry", "finance", "indicator", "index", "航运保险费率"),
    ("freight-rate", "海运费", "Freight Rate", "industry", "transport", "indicator", "USD/TEU", "海运运费"),
    
    # Agriculture
    ("feed-cost", "饲料成本", "Feed Cost", "commodity", "agriculture", "indicator", "USD/ton", "畜牧饲料成本"),
    ("livestock-cost", "畜牧成本", "Livestock Cost", "commodity", "agriculture", "indicator", "index", "畜牧业成本"),
    ("ethanol", "乙醇", "Ethanol", "commodity", "energy", "asset", "USD/gallon", "燃料乙醇"),
    ("edible-oil", "食用油", "Edible Oil", "commodity", "agriculture", "asset", "USD/ton", "植物油"),
    ("soy-meal", "豆粕", "Soybean Meal", "commodity", "agriculture", "asset", "USD/ton", "饲料原料"),
    ("pork-cycle", "猪周期", "Pork Cycle", "commodity", "agriculture", "indicator", "index", "生猪价格周期"),
    
    # Finance
    ("bond-price", "债券价格", "Bond Price", "asset", "fixed-income", "asset", "price", "债券市场价格"),
    ("high-valuation-stocks", "高估值股票", "High Valuation Stocks", "asset", "equity", "indicator", "PE", "高估值股票表现"),
    ("emerging-market-currency", "新兴市场货币", "EM Currency", "currency", "emerging-market", "indicator", "index", "新兴市场货币指数"),
    ("export-enterprise", "出口企业", "Export Enterprise", "industry", "trade", "industry", None, "出口导向型企业"),
    ("import-cost", "进口成本", "Import Cost", "macro", "trade", "indicator", "index", "进口成本指数"),
    ("capital-outflow", "资本外流", "Capital Outflow", "macro", "capital", "indicator", "USD bn", "资金流出量"),
    
    # Tech
    ("chip", "芯片", "Chip/Semiconductor", "industry", "technology", "industry", None, "芯片半导体"),
    ("optical-module", "光模块", "Optical Module", "industry", "technology", "industry", None, "光通信模块"),
    ("ev-battery", "锂电池", "EV Battery", "industry", "manufacturing", "industry", None, "动力电池"),
    ("charging-pile", "充电桩", "Charging Pile", "industry", "infrastructure", "industry", None, "电动车充电设施"),
    ("lithium-ore", "锂矿", "Lithium Ore", "commodity", "industrial-metal", "asset", "USD/ton", "锂矿石"),
    
    # Real Estate
    ("building-materials", "建材", "Building Materials", "industry", "construction", "industry", None, "建筑材料"),
    ("home-appliance", "家电", "Home Appliance", "industry", "consumer", "industry", None, "家用电器"),
    ("decoration", "家装", "Decoration", "industry", "consumer", "industry", None, "家居装修"),
    ("furniture", "家具", "Furniture", "industry", "consumer", "industry", None, "家具用品"),
    ("rent", "租金", "Rent", "macro", "housing", "indicator", "index", "房租价格指数"),
    
    # Policy
    ("infrastructure-investment", "基建投资", "Infrastructure Investment", "policy", "fiscal", "indicator", "CNY bn", "基建投资额"),
    ("construction-machinery", "工程机械", "Construction Machinery", "industry", "manufacturing", "industry", None, "工程机械"),
    ("tax-cut", "减税", "Tax Cut", "policy", "fiscal", "event", None, "减税政策"),
    ("corporate-profit", "企业利润", "Corporate Profit", "macro", "earnings", "indicator", "%", "企业盈利水平"),
    ("subsidy-policy", "补贴政策", "Subsidy Policy", "policy", "fiscal", "event", None, "行业补贴政策"),
    
    # Market
    ("stock-market", "股市", "Stock Market", "index", "equity", "indicator", "index", "股票市场指数"),
    ("bond-market", "债市", "Bond Market", "index", "fixed-income", "indicator", "yield", "债券市场收益率"),
    ("inflation-expectation", "加息预期", "Rate Hike Expectation", "policy", "central-bank", "indicator", "%", "加息概率预期"),
    
    # Medical
    ("pharmaceutical", "医药", "Pharmaceutical", "industry", "healthcare", "industry", None, "医药行业"),
    ("protective-equipment", "防护用品", "Protective Equipment", "industry", "healthcare", "industry", None, "口罩、防护服等"),
    ("online-services", "线上服务", "Online Services", "industry", "internet", "industry", None, "互联网服务"),
    
    # Agriculture continued
    ("water-conservancy", "水利建设", "Water Conservancy", "industry", "infrastructure", "industry", None, "水利工程"),
    ("food-processing", "食品加工", "Food Processing", "industry", "consumer", "industry", None, "食品加工业"),
    ("alternative-meat", "替代肉类", "Alternative Meat", "commodity", "agriculture", "asset", "price", "禽肉、牛羊肉等替代品"),
    ("pig-feed", "猪饲料", "Pig Feed", "commodity", "agriculture", "asset", "USD/ton", "生猪饲料"),
]

# Relations to add
RELATIONS = [
    # Energy
    ("ai-compute", "up", "power-consumption", "up", "positive", "AI训练、数据中心扩张 → 用电量激增", "strong", "immediate"),
    ("oil-crude", "up", "logistics-cost", "up", "positive", "运输成本增加 → 商品价格承压", "strong", "immediate"),
    ("natural-gas", "up", "chemical-cost", "up", "positive", "化工原料成本上升", "medium", "short-term"),
    ("coal", "up", "thermal-power-profit", "down", "negative", "发电成本上升，电价若不调则利润受损", "medium", "short-term"),
    
    # Precious Metals
    ("gold", "up", "silver", "up", "positive", "同为避险资产，白银波动更大", "medium", "immediate"),
    ("gold", "up", "usd-index", "down", "negative", "美元走弱 → 黄金相对升值", "strong", "immediate"),
    ("gold", "up", "real-interest-rate", "down", "negative", "利率下降 → 持有黄金成本降低", "strong", "immediate"),
    ("platinum", "up", "auto-industry", "up", "positive", "铂金用于汽车催化剂", "medium", "short-term"),
    
    # Industrial Metals
    ("copper", "up", "economic-prosperity", "up", "positive", "铜博士反映宏观经济需求", "strong", "short-term"),
    ("copper", "up", "new-energy-industry", "up", "positive", "电动车、光伏用铜量大", "strong", "long-term"),
    ("aluminum", "up", "construction-infra", "up", "positive", "建筑用铝需求", "medium", "short-term"),
    ("nickel", "up", "battery-industry", "up", "positive", "动力电池原料", "strong", "short-term"),
    
    # Geopolitics - War
    ("war", "up", "military-industry", "up", "positive", "战争 → 军工需求增加", "strong", "immediate"),
    ("war", "up", "oil-crude", "up", "positive", "战争 → 能源紧张", "strong", "immediate"),
    ("war", "up", "logistics-cost", "up", "positive", "运输成本上升、贸易路线中断", "strong", "immediate"),
    ("war", "up", "freight-rate", "up", "positive", "海运运费上涨", "medium", "immediate"),
    ("war", "up", "shipping-insurance", "up", "positive", "风险溢价上升", "medium", "immediate"),
    
    # Geopolitics - Sanction
    ("sanction", "up", "emerging-market-currency", "down", "negative", "被制裁国资产下跌", "medium", "immediate"),
    
    # Disaster
    ("natural-disaster", "up", "corn", "up", "positive", "产量受损、运输受阻", "medium", "immediate"),
    ("natural-disaster", "up", "wheat", "up", "positive", "农产品供应紧张", "medium", "immediate"),
    ("pandemic", "up", "pharmaceutical", "up", "positive", "医药需求增加", "strong", "immediate"),
    ("pandemic", "up", "protective-equipment", "up", "positive", "口罩、防护服需求激增", "strong", "immediate"),
    ("pandemic", "up", "online-services", "up", "positive", "线上消费场景增加", "strong", "immediate"),
    ("natural-disaster", "up", "water-conservancy", "up", "positive", "水利建设需求增加", "medium", "long-term"),
    
    # Interest Rate
    ("fed-rate", "up", "bond-price", "down", "negative", "利率上升 → 债券收益率升、价格跌", "strong", "immediate"),
    ("fed-rate", "up", "high-valuation-stocks", "down", "negative", "折现率上升 → 未来现金流估值下降", "strong", "short-term"),
    ("fed-rate", "up", "bank", "up", "positive", "息差扩大", "strong", "short-term"),
    ("fed-rate", "down", "real-estate", "up", "positive", "资金成本降低", "strong", "short-term"),
    ("usd-index", "up", "emerging-market-currency", "down", "negative", "资本回流美国", "strong", "immediate"),
    
    # Fiscal Policy
    ("infrastructure-investment", "up", "building-materials", "up", "positive", "需求拉动", "strong", "short-term"),
    ("infrastructure-investment", "up", "construction-machinery", "up", "positive", "工程机械需求增加", "strong", "short-term"),
    ("tax-cut", "up", "corporate-profit", "up", "positive", "可支配收入增加", "medium", "short-term"),
    ("subsidy-policy", "up", "new-energy-industry", "up", "positive", "行业景气度提升", "strong", "short-term"),
    
    # Tech
    ("ai-compute", "up", "semiconductor", "up", "positive", "GPU需求激增", "strong", "immediate"),
    ("ai-compute", "up", "data-center", "up", "positive", "基础设施扩张", "strong", "short-term"),
    ("ai-compute", "up", "optical-module", "up", "positive", "数据中心建设带动光模块需求", "medium", "short-term"),
    ("ev", "up", "ev-battery", "up", "positive", "电池需求", "strong", "immediate"),
    ("ev", "up", "lithium-ore", "up", "positive", "锂矿需求增加", "strong", "immediate"),
    ("ev", "up", "charging-pile", "up", "positive", "配套设施需求", "medium", "long-term"),
    ("semiconductor", "up", "optical-module", "up", "positive", "产业链联动", "medium", "short-term"),
    
    # Real Estate
    ("real-estate", "up", "building-materials", "up", "positive", "下游需求拉动", "strong", "short-term"),
    ("real-estate", "up", "home-appliance", "up", "positive", "家电需求增加", "medium", "short-term"),
    ("real-estate", "down", "decoration", "down", "positive", "消费需求萎缩", "medium", "immediate"),
    ("real-estate", "down", "furniture", "down", "positive", "消费需求萎缩", "medium", "immediate"),
    ("real-estate", "up", "rent", "up", "positive", "成本传导", "medium", "short-term"),
    
    # Agriculture
    ("wheat", "up", "feed-cost", "up", "positive", "饲料成本传导", "medium", "short-term"),
    ("feed-cost", "up", "livestock-cost", "up", "positive", "畜牧成本上升", "medium", "short-term"),
    ("corn", "up", "ethanol", "up", "positive", "替代能源需求", "medium", "short-term"),
    ("soybean", "up", "edible-oil", "up", "positive", "加工产品联动", "medium", "immediate"),
    ("soybean", "up", "soy-meal", "up", "positive", "豆粕价格联动", "medium", "immediate"),
    ("pork-cycle", "up", "pig-feed", "up", "positive", "需求溢出", "medium", "immediate"),
    ("pork-cycle", "up", "alternative-meat", "up", "positive", "替代肉类需求增加", "medium", "immediate"),
    
    # Cross Market
    ("stock-market", "up", "bond-market", "down", "negative", "风险偏好上升 → 债券吸引力下降", "medium", "immediate"),
    ("oil-crude", "up", "cpi", "up", "positive", "通胀传导", "strong", "short-term"),
    ("cpi", "up", "inflation-expectation", "up", "positive", "政策响应", "strong", "immediate"),
    ("vix", "up", "stock-market", "down", "negative", "风险资产跌", "strong", "immediate"),
    ("vix", "up", "gold", "up", "positive", "避险资产涨", "strong", "immediate"),
    
    # Currency
    ("usd-cny", "up", "export-enterprise", "up", "positive", "汇率优势", "medium", "short-term"),
    ("usd-cny", "up", "import-cost", "up", "positive", "进口原材料贵了", "medium", "immediate"),
    ("capital-outflow", "up", "stock-market", "down", "negative", "资金撤离", "strong", "immediate"),
    ("capital-outflow", "up", "bond-market", "down", "negative", "资金撤离", "strong", "immediate"),
]


def add_entities(conn, entities):
    """Add entities to database."""
    cursor = conn.cursor()
    added = 0
    for entity in entities:
        try:
            cursor.execute("""
                INSERT INTO entities (id, name, name_en, category, subcategory, type, unit, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, entity)
            added += 1
        except sqlite3.IntegrityError:
            pass  # Entity already exists
    conn.commit()
    return added


def add_relations(conn, relations):
    """Add relations to database."""
    cursor = conn.cursor()
    added = 0
    errors = []
    
    for rel in relations:
        primary_id, primary_dir, secondary_id, secondary_dir, rel_type, logic, strength, lag = rel
        
        # Check if entities exist
        cursor.execute("SELECT id FROM entities WHERE id = ?", (primary_id,))
        if not cursor.fetchone():
            errors.append(f"Primary entity '{primary_id}' not found")
            continue
        
        cursor.execute("SELECT id FROM entities WHERE id = ?", (secondary_id,))
        if not cursor.fetchone():
            errors.append(f"Secondary entity '{secondary_id}' not found")
            continue
        
        # Generate ID
        import hashlib
        from datetime import datetime
        hash_input = f"{primary_id}-{secondary_id}-{datetime.now().isoformat()}"
        hash_suffix = hashlib.md5(hash_input.encode()).hexdigest()[:6]
        rel_id = f"rel-{primary_id}-{secondary_id}-{hash_suffix}"
        
        try:
            cursor.execute("""
                INSERT INTO relations (id, primary_id, primary_direction, secondary_id, secondary_direction, relation_type, strength, logic, lag)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (rel_id, primary_id, primary_dir, secondary_id, secondary_dir, rel_type, strength, logic, lag))
            added += 1
        except sqlite3.IntegrityError:
            pass  # Relation already exists
    
    conn.commit()
    return added, errors


def main():
    print("Starting batch import...")
    
    conn = sqlite3.connect(DB_PATH)
    
    # Add entities
    print(f"\n1. Adding {len(NEW_ENTITIES)} entities...")
    entities_added = add_entities(conn, NEW_ENTITIES)
    print(f"   ✅ Added {entities_added} new entities")
    
    # Add relations
    print(f"\n2. Adding {len(RELATIONS)} relations...")
    relations_added, errors = add_relations(conn, RELATIONS)
    print(f"   ✅ Added {relations_added} new relations")
    
    if errors:
        print(f"\n   ⚠️  Errors ({len(errors)}):")
        for err in errors[:10]:
            print(f"      - {err}")
    
    # Summary
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM entities")
    total_entities = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM relations")
    total_relations = cursor.fetchone()[0]
    
    print(f"\n📊 Database Summary:")
    print(f"   - Total entities: {total_entities}")
    print(f"   - Total relations: {total_relations}")
    
    conn.close()
    print("\n✅ Import complete!")


if __name__ == "__main__":
    main()