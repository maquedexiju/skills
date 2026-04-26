#!/usr/bin/env python3
"""
Market Correlations Database Initialization

Creates SQLite database with entities and relations tables.
"""

import sqlite3
import os
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "market_correlations.db"

SCHEMA_STATEMENTS = [
    # Categories table
    "CREATE TABLE IF NOT EXISTS categories (id TEXT PRIMARY KEY, name TEXT NOT NULL, name_en TEXT, parent_id TEXT, description TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (parent_id) REFERENCES categories(id))",
    
    # Entities table
    "CREATE TABLE IF NOT EXISTS entities (id TEXT PRIMARY KEY, name TEXT NOT NULL, name_en TEXT, category TEXT NOT NULL, subcategory TEXT, type TEXT, unit TEXT, description TEXT, aliases TEXT, metadata TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
    
    # Entities indexes
    "CREATE INDEX IF NOT EXISTS idx_entities_category ON entities(category)",
    "CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name)",
    
    # Relations table
    "CREATE TABLE IF NOT EXISTS relations (id TEXT PRIMARY KEY, primary_id TEXT NOT NULL, primary_direction TEXT NOT NULL, secondary_id TEXT NOT NULL, secondary_direction TEXT NOT NULL, relation_type TEXT NOT NULL, strength TEXT, logic TEXT NOT NULL, mechanism TEXT, lag TEXT, confidence TEXT, source TEXT, tags TEXT, notes TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (primary_id) REFERENCES entities(id), FOREIGN KEY (secondary_id) REFERENCES entities(id))",
    
    # Relations indexes
    "CREATE INDEX IF NOT EXISTS idx_relations_primary ON relations(primary_id)",
    "CREATE INDEX IF NOT EXISTS idx_relations_secondary ON relations(secondary_id)",
    "CREATE INDEX IF NOT EXISTS idx_relations_type ON relations(relation_type)",
]

# Default categories to insert
DEFAULT_CATEGORIES = [
    ("commodity", "商品资产", "Commodity", None, "大宗商品、资源类资产"),
    ("currency", "货币", "Currency", None, "货币、汇率相关"),
    ("macro", "宏观经济", "Macro", None, "宏观经济指标"),
    ("policy", "政策", "Policy", None, "财政政策、货币政策"),
    ("event", "事件", "Event", None, "地缘政治、灾害等事件"),
    ("industry", "行业", "Industry", None, "行业板块"),
    ("index", "指数", "Index", None, "各类市场指数"),
    ("asset", "资产", "Asset", None, "可投资资产"),
    ("indicator", "指标", "Indicator", None, "经济指标、技术指标"),
]

# Default entities to insert (common ones)
DEFAULT_ENTITIES = [
    # Commodities - Precious Metals
    ("gold", "黄金", "Gold", "commodity", "precious-metal", "asset", "USD/oz", "避险资产、贵金属"),
    ("silver", "白银", "Silver", "commodity", "precious-metal", "asset", "USD/oz", "贵金属，波动性更高"),
    
    # Commodities - Energy
    ("oil-crude", "原油", "Crude Oil", "commodity", "energy", "asset", "USD/barrel", "石油，能源核心"),
    ("natural-gas", "天然气", "Natural Gas", "commodity", "energy", "asset", "USD/MMBtu", "天然气"),
    ("coal", "煤炭", "Coal", "commodity", "energy", "asset", "USD/ton", "煤炭"),
    
    # Commodities - Industrial Metals
    ("copper", "铜", "Copper", "commodity", "industrial-metal", "asset", "USD/ton", "铜博士，反映经济景气"),
    ("aluminum", "铝", "Aluminum", "commodity", "industrial-metal", "asset", "USD/ton", "工业金属"),
    ("nickel", "镍", "Nickel", "commodity", "industrial-metal", "asset", "USD/ton", "电池原料"),
    ("lithium", "锂", "Lithium", "commodity", "industrial-metal", "asset", "USD/ton", "动力电池核心材料"),
    
    # Commodities - Agriculture
    ("corn", "玉米", "Corn", "commodity", "agriculture", "asset", "USD/bushel", "粮食作物"),
    ("wheat", "小麦", "Wheat", "commodity", "agriculture", "asset", "USD/bushel", "粮食作物"),
    ("soybean", "大豆", "Soybean", "commodity", "agriculture", "asset", "USD/bushel", "油料作物"),
    
    # Currency
    ("usd-index", "美元指数", "USD Index", "currency", "index", "index", None, "美元相对强弱"),
    ("usd-cny", "美元人民币", "USD/CNY", "currency", "exchange-rate", "indicator", None, "人民币汇率"),
    
    # Macro
    ("gdp", "GDP", "GDP", "macro", "growth", "indicator", "%", "经济增长指标"),
    ("cpi", "CPI", "CPI", "macro", "inflation", "indicator", "%", "通胀指标"),
    ("pmi", "PMI", "PMI", "macro", "business", "indicator", "index", "采购经理人指数"),
    ("vix", "VIX恐慌指数", "VIX", "macro", "volatility", "index", "index", "市场恐慌程度"),
    
    # Policy
    ("fed-rate", "美联储利率", "Fed Rate", "policy", "central-bank", "indicator", "%", "联邦基金利率"),
    ("pbc-rate", "中国央行利率", "PBC Rate", "policy", "central-bank", "indicator", "%", "存贷款基准利率"),
    
    # Events
    ("war", "战争", "War", "event", "geopolitics", "event", None, "军事冲突"),
    ("pandemic", "疫情", "Pandemic", "event", "health", "event", None, "公共卫生事件"),
    ("natural-disaster", "自然灾害", "Natural Disaster", "event", "environment", "event", None, "洪水、干旱、地震等"),
    ("sanction", "制裁", "Sanction", "event", "geopolitics", "event", None, "经济制裁"),
    
    # Industry
    ("ai-compute", "算力", "AI Compute", "industry", "technology", "indicator", None, "AI计算能力需求"),
    ("data-center", "数据中心", "Data Center", "industry", "technology", "indicator", None, "数据中心产业"),
    ("ev", "新能源汽车", "EV", "industry", "automotive", "industry", None, "电动车产业"),
    ("semiconductor", "半导体", "Semiconductor", "industry", "technology", "industry", None, "芯片产业"),
    ("real-estate", "房地产", "Real Estate", "industry", "property", "industry", None, "房地产行业"),
    ("logistics", "物流", "Logistics", "industry", "transport", "industry", None, "物流运输"),
    ("bank", "银行", "Bank", "industry", "finance", "industry", None, "银行业"),
]


def init_database(db_path: Path = None, insert_defaults: bool = True):
    """Initialize the database with schema and optionally default data."""
    
    if db_path is None:
        db_path = DB_PATH
    
    # Create data directory if not exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create tables
    for statement in SCHEMA_STATEMENTS:
        cursor.execute(statement)
    
    if insert_defaults:
        # Insert default categories
        cursor.executemany(
            "INSERT OR IGNORE INTO categories (id, name, name_en, parent_id, description) VALUES (?, ?, ?, ?, ?)",
            DEFAULT_CATEGORIES
        )
        
        # Insert default entities
        cursor.executemany(
            "INSERT OR IGNORE INTO entities (id, name, name_en, category, subcategory, type, unit, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            DEFAULT_ENTITIES
        )
    
    conn.commit()
    conn.close()
    
    print(f"✅ Database initialized at: {db_path}")
    if insert_defaults:
        print(f"   - {len(DEFAULT_CATEGORIES)} categories inserted")
        print(f"   - {len(DEFAULT_ENTITIES)} entities inserted")


def get_db_path() -> Path:
    """Return the database path."""
    return DB_PATH


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Initialize market correlations database")
    parser.add_argument("--path", type=str, help="Custom database path")
    parser.add_argument("--no-defaults", action="store_true", help="Skip inserting default data")
    
    args = parser.parse_args()
    
    db_path = Path(args.path) if args.path else None
    init_database(db_path, insert_defaults=not args.no_defaults)