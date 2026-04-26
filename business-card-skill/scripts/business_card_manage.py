import json
import os
import sys
import uuid
import argparse
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# --- 数据模型 ---
# 获取脚本所在目录，确保数据库文件与脚本在同一目录下
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_PATH = os.path.join(SCRIPT_DIR, "cards.json")
class BusinessCard(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str
    company: Optional[str] = ""
    title: Optional[str] = ""
    phone: Optional[str] = ""
    email: Optional[str] = ""
    address: Optional[str] = ""
    tags: List[str] = [] # 标签列表
    extra_info: Dict[str, Any] = Field(default_factory=dict)

class CardDB:
    def __init__(self, path=None):
        self.path = path or DEFAULT_DB_PATH
        self.cards = self._load()

    def _load(self):
        if not os.path.exists(self.path): return []
        with open(self.path, "r", encoding="utf-8") as f:
            try:
                return [BusinessCard(**item) for item in json.load(f)]
            except: return []

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump([c.model_dump() for c in self.cards], f, ensure_ascii=False, indent=4)

# --- CLI 逻辑 ---
def main():
    db = CardDB()
    parser = argparse.ArgumentParser(description="名片管理命令行工具")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # 1. Add - 添加名片
    add_parser = subparsers.add_parser("add", help="添加名片")
    add_parser.add_argument("--name", required=True)
    add_parser.add_argument("--company")
    add_parser.add_argument("--phone")
    add_parser.add_argument("--tags", help="标签，用逗号分隔，例如 '供应商,上海,技术'")
    add_parser.add_argument("--extra", help='JSON 格式的额外信息')

    # 2. List - 列出所有
    subparsers.add_parser("list", help="列出所有名片")

    # 3. Search - 搜索 (支持姓名、公司、标签)
    search_parser = subparsers.add_parser("search", help="搜索名片")
    search_parser.add_argument("query", help="关键词（姓名、公司或标签）")

    # 4. Delete - 删除
    del_parser = subparsers.add_parser("del", help="删除名片")
    del_parser.add_argument("id", help="名片 ID")

    args = parser.parse_args()

    if args.command == "add":
        # 处理标签：将 "A,B,C" 转为 ["A", "B", "C"]
        tag_list = [t.strip() for t in args.tags.split(",")] if args.tags else []
        
        extra = json.loads(args.extra) if args.extra else {}
        
        card = BusinessCard(
            name=args.name, 
            company=args.company or "", 
            phone=args.phone or "",
            tags=tag_list,
            extra_info=extra
        )
        db.cards.append(card)
        db.save()
        print(f"✅ 成功添加: [{card.id}] {card.name} | 标签: {card.tags}")

    elif args.command == "list":
        for c in db.cards:
            tags_str = f"[{','.join(c.tags)}]" if c.tags else ""
            print(f"{c.id} | {c.name.ljust(8)} | {c.company.ljust(12)} | {tags_str}")

    elif args.command == "search":
        q = args.query.lower()
        # 搜索逻辑：匹配姓名、公司或标签列表中的任何一项
        results = [
            c for c in db.cards 
            if q in c.name.lower() 
            or q in c.company.lower() 
            or any(q in t.lower() for t in c.tags)
        ]
        
        if not results:
            print("未找到匹配项。")
        else:
            for c in results:
                print(f"找到: {c.id} | {c.name} | {c.company} | 标签: {c.tags} | 备注: {c.extra_info}")

    elif args.command == "del":
        original_count = len(db.cards)
        db.cards = [c for c in db.cards if c.id != args.id]
        if len(db.cards) < original_count:
            db.save()
            print(f"🗑️ 已删除 ID 为 {args.id} 的名片。")
        else:
            print(f"⚠️ 未找到 ID 为 {args.id} 的名片。")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()