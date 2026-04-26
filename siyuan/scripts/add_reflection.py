#!/usr/bin/env python3
"""
思源笔记新增感悟脚本

在当周周报的"本周感悟"章节添加一条感悟记录。

用法:
    python add_reflection.py "今天学到了新知识"
    python add_reflection.py "标题\n\n正文内容" --no-sync
"""

import argparse
import json
import os
import sys
from datetime import datetime
from urllib import request as r

# 从 config.json 读取配置
CONFIG_PATHS = [
    os.path.expanduser("~/.openclaw/workspace/skills/siyuan/config.json"),
    os.path.expanduser("~/.config/siyuan/config.json"),
    os.path.expanduser("~/.siyuan/config.json"),
]

def load_config():
    """加载配置文件"""
    for path in CONFIG_PATHS:
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)
    return {
        "api_url": "http://127.0.0.1:6806",
        "token": "",
        "default_notebook": ""
    }

config = load_config()
API_URL = config.get("api_url", "http://127.0.0.1:6806")
TOKEN = config.get("token", "")


def api_call(endpoint: str, payload: dict) -> dict:
    """调用思源 API"""
    req = r.Request(
        f"{API_URL}/api/{endpoint}",
        headers={
            "Authorization": f"Token {TOKEN}",
            "Content-Type": "application/json"
        },
        method="POST",
        data=json.dumps(payload).encode("utf-8")
    )
    
    opener = r.build_opener(r.HTTPHandler())
    response = opener.open(req)
    return json.loads(response.read().decode("utf-8"))


def perform_sync():
    """新增感悟后触发同步"""
    req = r.Request(
        f"{API_URL}/api/sync/performSync",
        headers={
            "Authorization": f"Token {TOKEN}",
            "Content-Type": "application/json"
        },
        method="POST",
        data=json.dumps({}).encode("utf-8")
    )
    
    opener = r.build_opener(r.HTTPHandler())
    response = opener.open(req)
    result = json.loads(response.read().decode("utf-8"))
    
    if result.get("code") == 0:
        print("Sync triggered successfully.")
    else:
        print(f"Sync warning: {result.get('msg', 'Unknown error')}")


def parse_content(content: str):
    """解析输入内容，分离标题和正文
    
    输入格式：
    - 单行：仅标题
    - 多行（用空行分隔）：第一行为标题，其余为正文
    
    返回：(title_part, body_part)
    """
    # 处理 shell 传入的字面 \n 字符
    # Shell 命令中 "text\nmore" 会被当作字面字符串 "text\nmore"
    # 需要将其转换为真正的换行符
    content = content.replace('\\n', '\n')
    
    lines = content.strip().split("\n")
    
    # 找空行分隔
    title_part = ""
    body_part = ""
    
    for i, line in enumerate(lines):
        if line.strip() == "":
            # 空行后是正文
            title_part = "\n".join(lines[:i]).strip()
            body_part = "\n".join(lines[i+1:]).strip()
            break
    
    if not title_part:
        # 没有空行，整个内容作为标题
        title_part = content.strip()
    
    return title_part, body_part


def add_reflection(content: str):
    """添加本周感悟"""
    # 计算当前周数
    today = datetime.today()
    year = today.year
    week_num = today.isocalendar()[1]
    
    hpath = f"/生活记录/{year}/{year} 年第 {week_num:02d} 周"
    
    # 解析标题和正文
    title_part, body_part = parse_content(content)
    
    # 构建完整标题（包含日期）
    title = f"### {today.strftime('%Y.%m.%d')} {title_part}"
    
    print(f"Adding reflection to: {hpath}")
    print(f"Title: {title_part}")
    if body_part:
        print(f"Body: {body_part[:50]}...")
    
    # SQL 查询定位"本周感悟"标题块
    sql = f"SELECT * FROM blocks WHERE content LIKE '%本周感悟%' AND type='h' AND hpath='{hpath}' LIMIT 1"
    result = api_call("query/sql", {"stmt": sql})
    
    if result.get("code") != 0:
        print(f"Error: {result.get('msg', 'Query failed')}")
        sys.exit(1)
    
    blocks = result.get("data", [])
    if not blocks:
        print(f"Error: 未找到本周感悟标题块，请先创建周报")
        sys.exit(1)
    
    header_id = blocks[0]["id"]
    
    # 获取子块
    result = api_call("block/getChildBlocks", {"id": header_id})
    
    if result.get("code") != 0:
        print(f"Error: {result.get('msg', 'Get child blocks failed')}")
        sys.exit(1)
    
    children = result.get("data", [])
    
    # 找到最后一个子块的位置
    if children:
        previous_id = children[-1]["id"]
    else:
        previous_id = header_id
    
    # 构建感悟内容（思源超级块格式）
    # {{{ 是超级块开始，}}} 是超级块结束
    # 格式：
    # {{{
    # ### 标题
    # 
    # 正文内容
    # }}}
    # {: style="..." memo="生活感悟"}
    
    md_lines = [
        "{{{",      # 超级块开始
        title,      # 标题行
        ""          # 空行
    ]
    
    if body_part:
        md_lines.append(body_part)
    
    md_lines.extend([
        "",         # 空行
        "}}}",      # 超级块结束
        "{: style=\"background-color: rgba(144, 144, 144, 0.1); border-radius: 10px;padding-left: 10px; padding-right: 10px;padding-bottom: 10px; margin-bottom:10px;\" memo=\"生活感悟\"}"
    ])
    
    md = "\n".join(md_lines)
    
    # 插入感悟
    result = api_call("block/insertBlock", {
        "dataType": "markdown",
        "data": md,
        "previousID": previous_id
    })
    
    if result.get("code") != 0:
        print(f"Error: {result.get('msg', 'Insert failed')}")
        sys.exit(1)
    
    # 获取新创建的块 ID
    data = result.get("data")
    new_id = None
    if data:
        # insertBlock 返回的是操作列表
        if isinstance(data, list) and len(data) > 0:
            ops = data[0].get("doOperations", [])
            if ops and len(ops) > 0:
                new_id = ops[0].get("id", "")
        # 直接返回 data
        elif isinstance(data, dict):
            new_id = data.get("id", "")
    
    print(f"Added reflection: {title}")
    if new_id:
        print(f"Block ID: {new_id}")
        print(f"Open: siyuan://blocks/{new_id}")
    return new_id


def main():
    parser = argparse.ArgumentParser(description="新增本周感悟")
    parser.add_argument("content", help="感悟内容（标题或标题\\n\\n正文）")
    parser.add_argument("--no-sync", action="store_true", help="新增后不触发同步")
    args = parser.parse_args()
    
    if not TOKEN:
        print("Error: No token configured. Check config.json.")
        sys.exit(1)
    
    # 添加感悟
    block_id = add_reflection(args.content)
    
    # 触发同步
    if not args.no_sync and block_id:
        print("\nTriggering sync...")
        perform_sync()


if __name__ == "__main__":
    main()