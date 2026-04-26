#!/usr/bin/env python3
"""
思源笔记 API 辅助脚本
简化与 Siyuan Note API 的交互
"""

import os
import sys
import json
import argparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

DEFAULT_API_URL = "http://127.0.0.1:6806"

# 全局配置缓存
_config = None


def load_config():
    """加载配置文件"""
    global _config
    if _config is not None:
        return _config

    # 配置文件搜索路径（按优先级）
    config_paths = [
        os.path.expanduser("~/.config/siyuan/config.json"),
        os.path.expanduser("~/.siyuan/config.json"),
        os.path.join(os.path.dirname(__file__), "..", "config.json"),  # skill 目录
        "./config.json",
    ]

    for path in config_paths:
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    _config = json.load(f)
                    return _config
            except (json.JSONDecodeError, IOError):
                continue

    _config = {}
    return _config


def get_config_value(key, default=None):
    """获取配置值"""
    config = load_config()
    return config.get(key, default)


def get_api_token():
    """获取 API Token（优先环境变量，其次配置文件）"""
    return os.environ.get("SIYUAN_TOKEN") or get_config_value("token", "")


def get_api_url():
    """获取 API URL（优先环境变量，其次配置文件，最后默认值）"""
    return os.environ.get("SIYUAN_API_URL") or get_config_value("api_url", DEFAULT_API_URL)


def get_default_notebook():
    """获取默认笔记本 ID"""
    return get_config_value("default_notebook", "")


def api_call(endpoint, data=None):
    """
    调用思源笔记 API

    Args:
        endpoint: API 端点路径（如 /api/notebook/lsNotebooks）
        data: 请求数据（字典）

    Returns:
        API 响应的 data 字段
    """
    url = get_api_url() + endpoint
    token = get_api_token()

    headers = {
        "Content-Type": "application/json"
    }
    if token:
        headers["Authorization"] = f"Token {token}"

    payload = json.dumps(data or {}).encode("utf-8")

    try:
        req = Request(url, data=payload, headers=headers, method="POST")
        with urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))

            if result.get("code") != 0:
                print(f"API Error: {result.get('msg', 'Unknown error')}", file=sys.stderr)
                sys.exit(1)

            return result.get("data")
    except HTTPError as e:
        print(f"HTTP Error: {e.code} - {e.reason}", file=sys.stderr)
        sys.exit(1)
    except URLError as e:
        print(f"Connection Error: {e.reason}", file=sys.stderr)
        print("请确保思源笔记正在运行且 API 已启用", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"JSON Parse Error: {e}", file=sys.stderr)
        sys.exit(1)


def list_notebooks():
    """列出所有笔记本"""
    data = api_call("/api/notebook/lsNotebooks")
    notebooks = data.get("notebooks", [])

    print("笔记本列表：")
    print("-" * 50)
    for nb in notebooks:
        status = "[打开]" if nb.get("closed") == 0 else "[关闭]"
        print(f"{status} {nb.get('name')}")
        print(f"    ID: {nb.get('id')}")
        print()

    return notebooks


def search_blocks(keyword, limit=20):
    """搜索包含关键词的块"""
    # 使用 SQL 查询
    sql = f"SELECT id, type, content, box, path FROM blocks WHERE content LIKE '%{keyword}%' LIMIT {limit}"
    data = api_call("/api/query/sql", {"stmt": sql})

    blocks = data.get("blocks", [])
    print(f"搜索 '{keyword}' 找到 {len(blocks)} 个结果：")
    print("-" * 50)

    for block in blocks:
        block_type = block.get("type", "?")
        content = block.get("content", "")[:100].replace("\n", " ")
        print(f"[{block_type}] {content}...")
        print(f"    ID: {block.get('id')}")
        print()

    return blocks


def create_document(notebook_id, path, markdown):
    """创建新文档"""
    data = api_call("/api/filetree/createDocWithMd", {
        "notebook": notebook_id,
        "path": path,
        "markdown": markdown
    })

    print(f"文档创建成功！")
    print(f"路径: {path}")
    return data


def get_document_content(doc_id):
    """获取文档内容（Markdown 格式）"""
    data = api_call("/api/export/exportMdContent", {"id": doc_id})

    content = data.get("content", "")
    print(content)
    return content


def update_block(block_id, content):
    """更新块内容"""
    data = api_call("/api/block/updateBlock", {
        "dataType": "markdown",
        "data": content,
        "id": block_id
    })

    print(f"块更新成功！ID: {block_id}")
    return data


def append_block(parent_id, content):
    """在父块下追加新块"""
    data = api_call("/api/block/appendBlock", {
        "dataType": "markdown",
        "data": content,
        "parentID": parent_id
    })

    print(f"块追加成功！")
    return data


def sql_query(query):
    """执行 SQL 查询"""
    data = api_call("/api/query/sql", {"stmt": query})

    # 检查结果是否是 blocks
    if "blocks" in data:
        blocks = data["blocks"]
        print(f"查询返回 {len(blocks)} 条记录：")
        print("-" * 50)
        for block in blocks:
            print(json.dumps(block, ensure_ascii=False, indent=2))
            print()
        return blocks
    else:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return data


def main():
    parser = argparse.ArgumentParser(description="思源笔记 API 工具")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # 列出笔记本
    subparsers.add_parser("list-notebooks", help="列出所有笔记本")

    # 搜索
    search_parser = subparsers.add_parser("search", help="搜索块内容")
    search_parser.add_argument("keyword", help="搜索关键词")
    search_parser.add_argument("--limit", type=int, default=20, help="返回结果数量限制")

    # 获取文档
    get_parser = subparsers.add_parser("get-doc", help="获取文档内容")
    get_parser.add_argument("doc_id", help="文档块 ID")

    # 创建文档
    create_parser = subparsers.add_parser("create-doc", help="创建新文档")
    create_parser.add_argument("notebook_id", help="笔记本 ID")
    create_parser.add_argument("path", help="文档路径，如 /folder/document")
    create_parser.add_argument("markdown", help="文档 Markdown 内容（或文件路径）")

    # SQL 查询
    sql_parser = subparsers.add_parser("sql", help="执行 SQL 查询")
    sql_parser.add_argument("query", help="SQL 查询语句")

    # 更新块
    update_parser = subparsers.add_parser("update-block", help="更新块内容")
    update_parser.add_argument("block_id", help="块 ID")
    update_parser.add_argument("content", help="新内容（Markdown）")

    # 追加块
    append_parser = subparsers.add_parser("append-block", help="追加块")
    append_parser.add_argument("parent_id", help="父块 ID")
    append_parser.add_argument("content", help="内容（Markdown）")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # 执行命令
    if args.command == "list-notebooks":
        list_notebooks()
    elif args.command == "search":
        search_blocks(args.keyword, args.limit)
    elif args.command == "get-doc":
        get_document_content(args.doc_id)
    elif args.command == "create-doc":
        # 检查 markdown 是否是文件
        if os.path.isfile(args.markdown):
            with open(args.markdown, "r", encoding="utf-8") as f:
                markdown = f.read()
        else:
            markdown = args.markdown
        create_document(args.notebook_id, args.path, markdown)
    elif args.command == "sql":
        sql_query(args.query)
    elif args.command == "update-block":
        update_block(args.block_id, args.content)
    elif args.command == "append-block":
        append_block(args.parent_id, args.content)


if __name__ == "__main__":
    main()
