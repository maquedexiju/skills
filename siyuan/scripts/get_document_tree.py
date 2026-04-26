#!/usr/bin/env python3
"""
思源笔记文档树获取工具 - 目录层级版
只获取有子文档的目录结构，不保存末梢文档
"""

import os
import sys
import json
from urllib.request import Request, urlopen
from datetime import datetime
from collections import defaultdict

# 加载配置
config = {}

def load_config():
    """加载配置文件"""
    global config
    if config:
        return config

    config_paths = [
        os.path.expanduser("~/.config/siyuan/config.json"),
        os.path.expanduser("~/.siyuan/config.json"),
        os.path.join(os.path.dirname(__file__), "..", "config.json"),
        "./config.json",
    ]

    for path in config_paths:
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    return config
            except (json.JSONDecodeError, IOError):
                continue

    config = {}
    return config


def get_api_token():
    return os.environ.get("SIYUAN_TOKEN") or config.get("token", "")


def get_api_url():
    return os.environ.get("SIYUAN_API_URL") or config.get("api_url", "http://127.0.0.1:6806")


def api_call(endpoint, data=None):
    """调用思源笔记 API"""
    url = get_api_url() + endpoint
    token = get_api_token()

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Token {token}"

    payload = json.dumps(data or {}).encode("utf-8")

    try:
        req = Request(url, data=payload, headers=headers, method="POST")
        with urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
            if result.get("code") != 0:
                print(f"API Error: {result.get('msg', 'Unknown error')}", file=sys.stderr)
                return None
            return result.get("data")
    except Exception as e:
        print(f"Error calling {endpoint}: {e}", file=sys.stderr)
        return None


def get_notebooks():
    """获取所有笔记本"""
    data = api_call("/api/notebook/lsNotebooks")
    if not data:
        return []
    return data.get("notebooks", [])


def get_top_level_documents():
    """获取所有顶层文档"""
    sql = """
    SELECT id, content as title, path, created, updated
    FROM blocks
    WHERE type = 'd'
    AND path LIKE '/%.sy'
    AND (length(path) - length(replace(path, '/', ''))) = 1
    ORDER BY content
    """
    data = api_call("/api/query/sql", {"stmt": sql})
    if isinstance(data, list):
        return data
    return data.get("blocks", []) if data else []


def get_child_documents(parent_id):
    """获取指定文档的直接子文档"""
    # 先获取父文档的信息
    parent_sql = f"SELECT id, path FROM blocks WHERE id = '{parent_id}'"
    parent_data = api_call("/api/query/sql", {"stmt": parent_sql})
    if not parent_data:
        return []

    parent = parent_data[0] if isinstance(parent_data, list) else parent_data
    parent_path = parent.get('path', '')

    # 计算父文档的深度（斜杠数量）
    # path like "/xxx/yyy.sy" -> depth = 2
    parent_depth = parent_path.count('/')

    # 获取子文档（path 以父路径开头，且深度 = 父深度 + 1）
    all_children = []
    offset = 0
    limit = 100

    # 移除 .sy 后缀获取基础路径
    base_path = parent_path[:-3] if parent_path.endswith('.sy') else parent_path

    while True:
        sql = f"""
        SELECT id, content as title, path, created, updated
        FROM blocks
        WHERE type = 'd'
        AND path LIKE '{base_path}/%.sy'
        AND (length(path) - length(replace(path, '/', ''))) = {parent_depth + 1}
        ORDER BY path
        LIMIT {limit} OFFSET {offset}
        """
        data = api_call("/api/query/sql", {"stmt": sql})
        if not data:
            break

        children = data if isinstance(data, list) else data.get("blocks", [])
        if not children:
            break

        all_children.extend(children)

        if len(children) < limit:
            break

        offset += limit

    return all_children


def has_children(doc_id):
    """检查文档是否有子文档"""
    sql = f"""
    SELECT COUNT(*) as count FROM blocks
    WHERE type = 'd'
    AND path LIKE '/{doc_id}/%.sy'
    LIMIT 1
    """
    data = api_call("/api/query/sql", {"stmt": sql})
    if isinstance(data, list) and len(data) > 0:
        return data[0].get("count", 0) > 0
    return False


def build_directory_tree(doc_id, doc_title, doc_path, depth=0, max_depth=5):
    """
    递归构建目录树，只保留有子文档的节点
    返回目录节点或 None（如果是末梢文档）
    """
    # 获取子文档
    children = get_child_documents(doc_id)

    # 构建节点
    node = {
        "id": doc_id,
        "title": doc_title,
        "path": doc_path,
        "depth": depth,
        "child_count": len(children)
    }

    if not children:
        # 末梢文档，不保留
        return None

    # 递归处理子文档
    subdirectories = []
    for child in children:
        child_node = build_directory_tree(
            child['id'],
            child['title'],
            child['path'],
            depth + 1,
            max_depth
        )
        if child_node:
            subdirectories.append(child_node)

    if subdirectories:
        node["subdirectories"] = subdirectories
        node["subdirectory_count"] = len(subdirectories)
    else:
        # 所有子文档都是末梢，此节点作为叶子目录保留
        node["subdirectories"] = []
        node["subdirectory_count"] = 0

    return node


def save_tree(tree, output_dir=None):
    """保存文档树到文件（JSON 和 文本格式）"""
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), "..")

    os.makedirs(output_dir, exist_ok=True)

    # 保存 JSON 格式
    tree_file = os.path.join(output_dir, "document_tree.json")
    with open(tree_file, "w", encoding="utf-8") as f:
        json.dump(tree, f, ensure_ascii=False, indent=2)

    # 保存文本格式（更易读，适合 AI 直接阅读）
    text_file = os.path.join(output_dir, "document_tree.txt")
    with open(text_file, "w", encoding="utf-8") as f:
        f.write(f"思源笔记文档树结构\n")
        f.write(f"生成时间: {tree['generated_at']}\n")
        f.write(f"API: {tree['api_url']}\n")
        f.write("=" * 60 + "\n\n")

        for nb in tree.get("notebooks", []):
            status = "[关闭]" if nb.get('closed') else "[打开]"
            f.write(f"📓 {status} {nb['name']}\n")

            for dir_node in nb.get("directories", []):
                write_text_tree(f, dir_node, indent=1)

            f.write("\n")

    return tree_file, text_file


def write_text_tree(f, node, indent=0):
    """递归写入文本格式的树"""
    prefix = "    " * indent
    has_children = node.get("subdirectories") and len(node["subdirectories"]) > 0

    if has_children:
        f.write(f"{prefix}📁 {node['title']}/\n")
        for child in node["subdirectories"]:
            write_text_tree(f, child, indent + 1)
    else:
        f.write(f"{prefix}📁 {node['title']}/\n")


def print_tree(node, indent=0):
    """打印目录树"""
    prefix = "  " * indent
    if node.get("subdirectories"):
        print(f"{prefix}📁 {node['title']} ({node['child_count']} 个直接子项, {node['subdirectory_count']} 个子目录)")
        for child in node.get("subdirectories", []):
            print_tree(child, indent + 1)
    else:
        print(f"{prefix}📁 {node['title']} ({node['child_count']} 个直接子项)")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="思源笔记目录树获取工具")
    parser.add_argument("--output", "-o", help="输出目录", default=None)
    parser.add_argument("--max-depth", "-d", type=int, default=10, help="最大递归深度")
    parser.add_argument("--notebook", "-n", help="指定笔记本ID（否则使用默认）")
    parser.add_argument("--pretty", "-p", action="store_true", help="打印格式化的树结构")

    args = parser.parse_args()

    # 加载配置
    load_config()

    print("正在获取目录树...")
    print(f"API: {get_api_url()}")

    # 获取笔记本信息
    notebooks = get_notebooks()
    if not notebooks:
        print("错误：无法获取笔记本列表", file=sys.stderr)
        sys.exit(1)

    print(f"找到 {len(notebooks)} 个笔记本")

    # 构建完整的目录树
    tree = {
        "version": "2.0",
        "generated_at": datetime.now().isoformat(),
        "api_url": get_api_url(),
        "total_notebooks": len(notebooks),
        "notebooks": []
    }

    for nb in notebooks:
        nb_id = nb['id']
        nb_name = nb['name']

        print(f"\n处理笔记本: {nb_name} ({nb_id})")

        # 获取该笔记本的顶层文档
        top_docs = get_top_level_documents()
        # 过滤出属于该笔记本的文档
        nb_top_docs = [d for d in top_docs if d.get('box') == nb_id or not d.get('box')]

        print(f"  顶层文档: {len(nb_top_docs)} 个")

        nb_node = {
            "id": nb_id,
            "name": nb_name,
            "icon": nb.get('icon', ''),
            "closed": nb.get('closed', 0) == 1,
            "directories": []
        }

        for doc in nb_top_docs:
            dir_tree = build_directory_tree(
                doc['id'],
                doc['title'],
                doc['path'],
                depth=0,
                max_depth=args.max_depth
            )
            if dir_tree:
                nb_node["directories"].append(dir_tree)

        print(f"  有子文档的目录: {len(nb_node['directories'])} 个")
        tree["notebooks"].append(nb_node)

    # 保存到文件
    tree_file, text_file = save_tree(tree, args.output)
    print(f"\n✅ 目录树已保存:")
    print(f"   JSON: {tree_file}")
    print(f"   文本: {text_file}")

    # 打印统计
    total_dirs = sum(len(nb.get('directories', [])) for nb in tree['notebooks'])
    print(f"\n统计:")
    print(f"  笔记本数: {len(tree['notebooks'])}")
    print(f"  顶层目录数: {total_dirs}")

    # 打印树结构
    if args.pretty:
        print("\n" + "=" * 60)
        print("目录树结构（仅显示有子文档的目录）:")
        print("=" * 60)

        for nb in tree["notebooks"]:
            print(f"\n📓 {'[关闭]' if nb['closed'] else '[打开]'} {nb['name']}")
            for dir_node in nb.get("directories", []):
                print_tree(dir_node)


if __name__ == "__main__":
    main()
