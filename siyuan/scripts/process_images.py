#!/usr/bin/env python3
"""
思源笔记图片统一处理脚本

支持两种处理模式：
1. 网络图片本地化：将 http/https 链接的图片下载并上传到思源本地
2. 图片压缩：压缩思源本地图片，减小体积

可以单独执行，也可以组合执行（先迁移网络图片，再压缩所有图片）

用法:
    # 网络图片本地化
    python process_images.py --doc "文档ID" --migrate
    
    # 图片压缩
    python process_images.py --doc "文档ID" --compress
    
    # 先迁移再压缩（推荐）
    python process_images.py --doc "文档ID" --migrate --compress
    
    # 仅检测，不实际处理
    python process_images.py --doc "文档ID" --migrate --compress --dry-run
    
    # 处理单个图片
    python process_images.py --url "https://..."          # 下载并上传网络图片
    python process_images.py --asset "assets/xxx.webp"   # 压缩本地图片
"""

import argparse
import json
import os
import re
import sys
from io import BytesIO
from urllib import request as r
from urllib.parse import urlparse
from datetime import datetime

try:
    from PIL import Image, UnidentifiedImageError
except ImportError:
    print("Error: PIL not installed. Run: pip install Pillow")
    sys.exit(1)

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Error: BeautifulSoup not installed. Run: pip install beautifulsoup4")
    sys.exit(1)

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

# 图片上传路径
ASSET_SAVE_PATH = "/assets/migrated_imgs/"

# 压缩参数
MIN_SHORT_SIDE = 360      # 短边小于此值不压缩
TARGET_SHORT_SIDE = 720   # 短边大于此值时缩放到此值
MAX_COMPRESS_RATIO = 3    # 最大压缩比例（最多压缩到 1/3）
MIN_COMPRESS_GAIN = 0.01  # 压缩增益小于此值跳过


# ==================== API 调用 ====================

def api_call(endpoint: str, payload: dict = None, raw: bool = False):
    """调用思源 API"""
    if payload is None:
        payload = {}

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
    response = opener.open(req, timeout=15)

    if raw:
        return response.read()
    return json.loads(response.read().decode("utf-8"))


def find_doc_by_title(title: str) -> str:
    """通过标题查找文档 ID"""
    sql = f"SELECT id FROM blocks WHERE content LIKE '%{title}%' AND type='d' LIMIT 1"
    result = api_call("query/sql", {"stmt": sql})
    if result.get("code") != 0 or not result.get("data"):
        return ""
    return result["data"][0]["id"]


def get_child_blocks(doc_id: str) -> list:
    """获取文档的所有子块"""
    result = api_call("block/getChildBlocks", {"id": doc_id})
    if result.get("code") != 0:
        return []
    return result.get("data", [])


def get_block_kramdown(block_id: str) -> str:
    """获取块的 Kramdown 内容"""
    result = api_call("block/getBlockKramdown", {"id": block_id})
    if result.get("code") != 0:
        return ""
    return result.get("data", {}).get("kramdown", "")


def update_block_content(block_id: str, new_content: str) -> bool:
    """更新思源块的内容"""
    try:
        result = api_call("block/updateBlock", {
            "id": block_id,
            "data": new_content,
            "dataType": "markdown"
        })
        if result.get("code") == 0:
            return True
        else:
            print(f"    Block update failed: {result.get('msg')}")
            return False
    except Exception as e:
        print(f"    Block update error: {e}")
        return False


# ==================== 图片下载 ====================

def download_network_image(img_url: str, timeout: int = 10) -> bytes:
    """下载网络图片（http/https 链接）"""
    try:
        req = r.Request(
            img_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )
        opener = r.build_opener(r.HTTPHandler())
        response = opener.open(req, timeout=timeout)
        return response.read()
    except Exception as e:
        print(f"    Download failed: {e}")
        return None


def download_siyuan_asset(asset_path: str) -> bytes:
    """从思源下载本地图片"""
    try:
        # 去掉前导斜杠
        path = asset_path.lstrip("/")
        result = api_call("file/getFile", {"path": f"/data/{path}"}, raw=True)
        return result
    except Exception as e:
        print(f"    Download from SiYuan failed: {e}")
        return None


# ==================== 图片上传 ====================

def upload_to_siyuan(image_data: bytes, filename: str) -> str:
    """上传图片到思源
    
    返回思源内的图片路径，失败返回空字符串
    """
    boundary = "----WebKitFormBoundaryProcess"
    body = BytesIO()

    # 文件部分
    body.write(f"--{boundary}\r\n".encode())
    body.write(f'Content-Disposition: form-data; name="file[]"; filename="{filename}"\r\n'.encode())
    body.write(f"Content-Type: image/webp\r\n\r\n".encode())
    body.write(image_data)
    body.write(f"\r\n".encode())

    # 路径参数
    body.write(f"--{boundary}\r\n".encode())
    body.write(b'Content-Disposition: form-data; name="assetsDirPath"\r\n\r\n')
    body.write(ASSET_SAVE_PATH.encode())
    body.write(f"\r\n--{boundary}--\r\n".encode())

    req = r.Request(
        f"{API_URL}/api/asset/upload",
        headers={
            "Authorization": f"Token {TOKEN}",
            "Content-Type": f"multipart/form-data; boundary={boundary}"
        },
        method="POST",
        data=body.getvalue()
    )

    opener = r.build_opener(r.HTTPHandler())
    response = opener.open(req, timeout=15)
    result = json.loads(response.read().decode("utf-8"))

    if result.get("code") != 0:
        print(f"    Upload failed: {result.get('msg', 'Unknown error')}")
        return ""

    # 从 succMap 获取路径（返回不带前导斜杠的格式，如 assets/xxx）
    succ_map = result.get("data", {}).get("succMap", {})
    if succ_map:
        for key, path in succ_map.items():
            # 去掉前导斜杠，返回 assets/... 格式
            return path.lstrip("/")

    return ""


# ==================== 图片压缩 ====================

def compress_image(image_data: bytes) -> tuple:
    """压缩图片
    
    返回：(压缩后的数据, 压缩比例)
    """
    try:
        img = Image.open(BytesIO(image_data))
    except UnidentifiedImageError:
        return None, 0

    width, height = img.size
    short_side = min(width, height)

    # 太小的图片不压缩
    if short_side < MIN_SHORT_SIDE:
        return None, 0

    initial_size = len(image_data)

    # 转换格式
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    # 大图片缩放
    if short_side > TARGET_SHORT_SIDE:
        compress_ratio = TARGET_SHORT_SIDE / short_side
        if compress_ratio < 1 / MAX_COMPRESS_RATIO:
            compress_ratio = 1 / MAX_COMPRESS_RATIO
        img = img.resize((int(width * compress_ratio), int(height * compress_ratio)))

    # 输出为 WebP
    output = BytesIO()
    img.save(output, "WEBP", method=6)

    final_data = output.getvalue()
    final_size = len(final_data)
    ratio = 1 - (final_size / initial_size)

    # 压缩效果不明显则跳过
    if ratio < MIN_COMPRESS_GAIN:
        return None, 0

    return final_data, ratio


# ==================== 图片解析 ====================

def parse_all_images(content: str) -> dict:
    """解析内容中的所有图片
    
    返回：{
        'network': [(alt, url), ...],  # 网络图片
        'local': [path, ...]           # 本地图片
    }
    """
    result = {'network': [], 'local': []}

    # 1. Markdown 图片语法
    md_pattern = r'!\[(.*?)\]\((.*?)\)'
    md_matches = re.findall(md_pattern, content)
    for alt, path in md_matches:
        if path.startswith(('http://', 'https://')):
            result['network'].append((alt, path))
        elif path.startswith('assets/') or path.startswith('/assets/'):
            path = path.lstrip('/')
            result['local'].append(path)

    # 2. HTML img 标签
    soup = BeautifulSoup(content, "html.parser")
    img_tags = soup.find_all("img")
    for img in img_tags:
        src = img.get("src", "")
        if src.startswith(('http://', 'https://')):
            result['network'].append((img.get("alt", ""), src))
        elif src.startswith('assets/') or src.startswith('/assets/'):
            src = src.lstrip('/')
            result['local'].append(src)

    return result


# ==================== 图片处理 ====================

def process_network_image(url: str, alt: str = "", dry_run: bool = False) -> tuple:
    """处理单个网络图片
    
    返回：(新路径, 文件大小KB) 或 (None, 0)
    """
    print(f"\n  Processing network image: {url[:60]}{'...' if len(url) > 60 else ''}")
    
    # 下载
    image_data = download_network_image(url)
    if not image_data:
        print("    Skip: download failed")
        return None, 0

    size_kb = len(image_data) / 1024
    print(f"    Downloaded: {size_kb:.1f}KB")

    if dry_run:
        return None, size_kb

    # 生成文件名
    parsed_url = urlparse(url)
    original_name = os.path.basename(parsed_url.path)
    if not original_name:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        original_name = f"migrated_{timestamp}.png"
    
    # 清理文件名
    original_name = re.sub(r'[^\w\-\.]', '_', original_name)
    if len(original_name) > 100:
        ext = os.path.splitext(original_name)[1] or '.png'
        original_name = original_name[:90] + ext
    
    # 转为 webp 格式
    if not original_name.endswith('.webp'):
        original_name = os.path.splitext(original_name)[0] + '.webp'

    # 上传
    new_path = upload_to_siyuan(image_data, original_name)
    if not new_path:
        print("    Skip: upload failed")
        return None, 0

    print(f"    New path: {new_path}")
    return new_path, size_kb


def process_local_image(asset_path: str, dry_run: bool = False) -> tuple:
    """处理单个本地图片（压缩）
    
    返回：(新路径, 节省字节) 或 (None, 0)
    """
    print(f"\n  Processing local image: {asset_path}")

    # 下载
    image_data = download_siyuan_asset(asset_path)
    if not image_data:
        print("    Skip: download failed")
        return None, 0

    initial_size = len(image_data)
    size_kb = initial_size / 1024
    print(f"    Original: {size_kb:.1f}KB")

    # 检测尺寸
    try:
        img = Image.open(BytesIO(image_data))
        short_side = min(img.size)
        print(f"    Short side: {short_side}px")
    except UnidentifiedImageError:
        print("    Skip: cannot read image")
        return None, 0

    if dry_run:
        return None, initial_size

    # 压缩
    compressed_data, ratio = compress_image(image_data)
    if not compressed_data:
        print("    Skip: no compression needed (too small or already optimized)")
        return None, 0

    final_size = len(compressed_data)
    saved_bytes = initial_size - final_size
    print(f"    Compressed: {ratio:.1%}, Final: {final_size / 1024:.1f}KB")

    # 上传
    filename = os.path.basename(asset_path)
    if not filename.endswith('.webp'):
        filename = os.path.splitext(filename)[0] + '.webp'

    new_path = upload_to_siyuan(compressed_data, filename)
    if not new_path:
        print("    Skip: upload failed")
        return None, 0

    print(f"    New path: {new_path}")
    return new_path, saved_bytes


def process_block(block: dict, do_migrate: bool, do_compress: bool, dry_run: bool = False) -> dict:
    """处理单个块的图片
    
    返回统计信息
    """
    block_id = block.get("id")
    block_type = block.get("type")
    content = block.get("markdown", "") or block.get("content", "")

    if not block_id or not content:
        return {"processed": 0, "updated": False}

    stats = {"processed": 0, "updated": False, "bytes_saved": 0}

    # 解析图片
    images = parse_all_images(content)
    if not images['network'] and not images['local']:
        return stats

    new_content = content

    # 处理网络图片
    if do_migrate and images['network']:
        for alt, url in images['network']:
            new_path, size_kb = process_network_image(url, alt, dry_run)
            if new_path:
                # 替换链接（new_path 已是 assets/... 格式）
                old_str = f"![{alt}]({url})"
                new_str = f"![{alt}]({new_path})"
                new_content = new_content.replace(old_str, new_str)
                stats["processed"] += 1
            elif dry_run and size_kb > 0:
                stats["processed"] += 1

    # 处理本地图片（包括刚迁移的）
    if do_compress:
        # 重新解析更新后的内容
        if new_content != content:
            images = parse_all_images(new_content)
        
        for asset_path in images['local']:
            new_path, saved = process_local_image(asset_path, dry_run)
            if new_path:
                # 替换链接（统一为 assets/... 格式，不带前导斜杠）
                old_path = asset_path.lstrip("/")
                new_content = new_content.replace(f"/{old_path}", new_path)
                new_content = new_content.replace(old_path, new_path)
                stats["processed"] += 1
                stats["bytes_saved"] += saved
            elif dry_run and saved > 0:
                stats["processed"] += 1

    # 更新块
    if not dry_run and new_content != content and stats["processed"] > 0:
        if update_block_content(block_id, new_content):
            stats["updated"] = True

    return stats


def process_document(doc_id: str, do_migrate: bool, do_compress: bool, dry_run: bool = False):
    """处理文档中的所有图片"""
    print(f"Processing document: {doc_id}")

    blocks = get_child_blocks(doc_id)
    if not blocks:
        print("Error: Could not get document blocks")
        return

    print(f"Found {len(blocks)} blocks")

    total_stats = {
        "network_images": 0,
        "local_images": 0,
        "processed": 0,
        "migrated": 0,
        "compressed": 0,
        "bytes_saved": 0,
        "blocks_updated": 0
    }

    # 先统计
    for block in blocks:
        content = block.get("markdown", "") or block.get("content", "")
        images = parse_all_images(content)
        total_stats["network_images"] += len(images['network'])
        total_stats["local_images"] += len(images['local'])

    print(f"Found {total_stats['network_images']} network images, {total_stats['local_images']} local images")

    if total_stats["network_images"] == 0 and total_stats["local_images"] == 0:
        print("No images to process")
        return

    # 处理每个块
    for block in blocks:
        stats = process_block(block, do_migrate, do_compress, dry_run)
        total_stats["processed"] += stats["processed"]
        total_stats["bytes_saved"] += stats["bytes_saved"]
        if stats["updated"]:
            total_stats["blocks_updated"] += 1

    # 分类统计
    if do_migrate:
        total_stats["migrated"] = total_stats["network_images"]
    if do_compress:
        total_stats["compressed"] = total_stats["local_images"]

    # 打印统计
    print("\n" + "=" * 50)
    print("Summary:")
    
    if do_migrate:
        print(f"  Network images: {total_stats['network_images']}")
        if dry_run:
            print(f"  Can be migrated: {total_stats['network_images']}")
        else:
            print(f"  Migrated: {total_stats['migrated']}")
    
    if do_compress:
        print(f"  Local images: {total_stats['local_images']}")
        if dry_run:
            print(f"  Can be compressed: {total_stats['local_images']}")
        else:
            print(f"  Compressed: {total_stats['compressed']}")
            if total_stats['bytes_saved'] > 0:
                print(f"  Bytes saved: {total_stats['bytes_saved'] / 1024:.1f}KB ({total_stats['bytes_saved'] / 1024 / 1024:.2f}MB)")
    
    print(f"  Blocks updated: {total_stats['blocks_updated']}")


def process_single_url(url: str):
    """处理单个网络图片 URL"""
    print(f"Processing URL: {url}")

    image_data = download_network_image(url)
    if not image_data:
        print("Error: Failed to download")
        return

    size_kb = len(image_data) / 1024
    print(f"Downloaded: {size_kb:.1f}KB")

    parsed_url = urlparse(url)
    filename = os.path.basename(parsed_url.path)
    if not filename:
        filename = f"migrated_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
    if not filename.endswith('.webp'):
        filename = os.path.splitext(filename)[0] + '.webp'

    siyuan_path = upload_to_siyuan(image_data, filename)
    if siyuan_path:
        print(f"Success! New path: {siyuan_path}")
    else:
        print("Error: Failed to upload")


def process_single_asset(asset_path: str):
    """处理单个本地图片"""
    print(f"Processing asset: {asset_path}")

    image_data = download_siyuan_asset(asset_path)
    if not image_data:
        print("Error: Failed to download from SiYuan")
        return

    initial_size = len(image_data)
    print(f"Original size: {initial_size / 1024:.1f}KB")

    compressed_data, ratio = compress_image(image_data)
    if not compressed_data:
        print("No compression needed")
        return

    final_size = len(compressed_data)
    print(f"Compressed by {ratio:.1%}, Final: {final_size / 1024:.1f}KB")

    filename = os.path.basename(asset_path)
    if not filename.endswith('.webp'):
        filename = os.path.splitext(filename)[0] + '.webp'

    new_path = upload_to_siyuan(compressed_data, filename)
    if new_path:
        print(f"Success! New path: {new_path}")
        print(f"Saved: {(initial_size - final_size) / 1024:.1f}KB")


def main():
    parser = argparse.ArgumentParser(description="思源笔记图片统一处理")
    parser.add_argument("--doc", help="文档 ID 或标题")
    parser.add_argument("--url", help="单个网络图片 URL")
    parser.add_argument("--asset", help="单个本地图片路径 (assets/xxx.webp)")
    parser.add_argument("--migrate", action="store_true", help="迁移网络图片到本地")
    parser.add_argument("--compress", action="store_true", help="压缩本地图片")
    parser.add_argument("--dry-run", action="store_true", help="仅检测，不实际处理")
    args = parser.parse_args()

    if not TOKEN:
        print("Error: No token configured. Check config.json.")
        sys.exit(1)

    # 单个图片处理
    if args.url:
        process_single_url(args.url)
        return

    if args.asset:
        process_single_asset(args.asset)
        return

    # 文档处理
    if args.doc:
        # 默认：如果没指定任何操作，则执行全部
        do_migrate = args.migrate or (not args.migrate and not args.compress)
        do_compress = args.compress or (not args.migrate and not args.compress)

        # 查找文档
        doc_id = args.doc
        try:
            test_result = api_call('block/getChildBlocks', {'id': args.doc})
            if test_result.get('code') == 0 and test_result.get('data'):
                doc_id = args.doc
            else:
                raise ValueError('Not a valid ID')
        except:
            found_id = find_doc_by_title(args.doc)
            if found_id:
                doc_id = found_id
                print(f"Found document ID: {doc_id}")
            else:
                print(f"Error: Could not find document '{args.doc}'")
                sys.exit(1)

        process_document(doc_id, do_migrate, do_compress, args.dry_run)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()