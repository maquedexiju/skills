#!/usr/bin/env python3
"""
思源笔记同步脚本

执行同步或获取同步状态。

用法:
    python sync.py          # 执行同步
    python sync.py --info   # 获取同步状态
"""

import argparse
import json
import os
import sys
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


def api_call(endpoint: str, payload: dict = None) -> dict:
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
    response = opener.open(req)
    return json.loads(response.read().decode("utf-8"))


def perform_sync():
    """执行同步"""
    print("Executing sync...")
    result = api_call("sync/performSync")
    
    if result.get("code") != 0:
        print(f"Error: {result.get('msg', 'Unknown error')}")
        sys.exit(1)
    
    print("Sync completed successfully.")
    
    # 获取同步状态
    get_sync_info()


def get_sync_info():
    """获取同步状态"""
    result = api_call("sync/getSyncInfo")
    
    if result.get("code") != 0:
        print(f"Error: {result.get('msg', 'Unknown error')}")
        sys.exit(1)
    
    data = result.get("data", {})
    if not data:
        print("No sync info available.")
        return
    
    print("\nSync Status:")
    print(f"  Kernel: {data.get('kernel', 'N/A')}")
    print(f"  Stats: {data.get('stat', 'N/A')}")
    
    synced = data.get("synced")
    if synced:
        import datetime
        dt = datetime.datetime.fromtimestamp(synced / 1000)
        print(f"  Last Sync: {dt.strftime('%Y-%m-%d %H:%M:%S')}")


def main():
    parser = argparse.ArgumentParser(description="思源同步")
    parser.add_argument("--info", action="store_true", help="获取同步状态")
    args = parser.parse_args()
    
    if not TOKEN:
        print("Error: No token configured. Check config.json.")
        sys.exit(1)
    
    if args.info:
        get_sync_info()
    else:
        perform_sync()


if __name__ == "__main__":
    main()