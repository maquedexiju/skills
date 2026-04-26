#!/usr/bin/env python3
"""
Memos CLI - Interact with Memos note-taking app via REST API.

Usage:
    memos.py create <content> [--visibility <level>] [--pinned]
    memos.py list [--limit <n>] [--filter <expr>]
    memos.py get <memo_id>
    memos.py delete <memo_id>

Config: Edit config.json in the skill folder, or set environment variables:
    MEMOS_URL  - Base URL (e.g., https://memos.example.com)
    MEMOS_TOKEN - Access token from Settings > Access Tokens
"""

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# Skill directory (where config.json lives)
SKILL_DIR = Path(__file__).parent.parent


def get_config():
    """Get Memos configuration from config file or environment."""
    # Try config file first
    config_file = SKILL_DIR / "config.json"
    url = ""
    token = ""
    
    if config_file.exists():
        try:
            with open(config_file) as f:
                config = json.load(f)
                url = config.get("url", "").rstrip("/")
                token = config.get("token", "")
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not read config.json: {e}", file=sys.stderr)
    
    # Skip placeholder values
    if url == "https://your-memos-instance.com" or not url:
        url = os.environ.get("MEMOS_URL", "").rstrip("/")
    if token == "your-access-token-here" or not token:
        token = os.environ.get("MEMOS_TOKEN", "")
    
    if not url:
        print("Error: Memos URL not configured. Edit config.json or set MEMOS_URL", file=sys.stderr)
        sys.exit(1)
    if not token:
        print("Error: Memos token not configured. Edit config.json or set MEMOS_TOKEN", file=sys.stderr)
        sys.exit(1)
    
    return url, token


def make_request(method, path, data=None):
    """Make HTTP request to Memos API."""
    base_url, token = get_config()
    url = f"{base_url}{path}"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    
    body = json.dumps(data).encode("utf-8") if data else None
    
    req = Request(url, data=body, headers=headers, method=method)
    
    try:
        with urlopen(req, timeout=30) as response:
            if response.status == 204:
                return None
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        print(f"HTTP Error {e.code}: {error_body}", file=sys.stderr)
        sys.exit(1)
    except URLError as e:
        print(f"URL Error: {e.reason}", file=sys.stderr)
        sys.exit(1)


def create_memo(content, visibility="PRIVATE", pinned=False):
    """Create a new memo."""
    # Normalize visibility input (enum values: PRIVATE, PROTECTED, PUBLIC)
    vis_upper = visibility.upper()
    valid_visibilities = ["PRIVATE", "PROTECTED", "PUBLIC"]
    
    if vis_upper not in valid_visibilities:
        vis_upper = "PRIVATE"
    
    payload = {
        "content": content,
        "visibility": vis_upper,
        "state": "NORMAL",
    }
    
    if pinned:
        payload["pinned"] = True
    
    result = make_request("POST", "/api/v1/memos", payload)
    
    print("Memo created successfully!")
    print(f"  ID: {result.get('name', 'N/A')}")
    print(f"  Content: {content[:100]}{'...' if len(content) > 100 else ''}")
    return result


def list_memos(limit=10, filter_expr=None):
    """List memos."""
    params = [f"pageSize={limit}"]
    if filter_expr:
        params.append(f"filter={filter_expr}")
    
    path = f"/api/v1/memos?{'&'.join(params)}"
    result = make_request("GET", path)
    
    memos = result.get("memos", [])
    
    if not memos:
        print("No memos found.")
        return
    
    print(f"Found {len(memos)} memo(s):\n")
    for memo in memos:
        name = memo.get("name", "unknown")
        content = memo.get("content", "")
        visibility = memo.get("visibility", "UNKNOWN")
        pinned = "📌 " if memo.get("pinned") else ""
        
        # Extract ID from name (format: memos/{id})
        memo_id = name.split("/")[-1] if "/" in name else name
        
        print(f"{pinned}[{memo_id}] ({visibility})")
        print(f"  {content[:80]}{'...' if len(content) > 80 else ''}")
        print()


def get_memo(memo_id):
    """Get a specific memo."""
    path = f"/api/v1/memos/{memo_id}"
    result = make_request("GET", path)
    
    print(f"Memo: {result.get('name', 'N/A')}")
    print(f"Visibility: {result.get('visibility', 'N/A')}")
    print(f"Pinned: {result.get('pinned', False)}")
    print(f"Created: {result.get('createTime', 'N/A')}")
    print(f"\nContent:\n{result.get('content', '')}")


def delete_memo(memo_id):
    """Delete a memo."""
    # Remove 'memos/' prefix if present (from list output format)
    if memo_id.startswith("memos/"):
        memo_id = memo_id.split("/")[-1]
    path = f"/api/v1/memos/{memo_id}"
    make_request("DELETE", path)
    print(f"Memo {memo_id} deleted successfully.")


def main():
    parser = argparse.ArgumentParser(
        description="Memos CLI - Interact with Memos note-taking app"
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new memo")
    create_parser.add_argument("content", help="Memo content (Markdown)")
    create_parser.add_argument(
        "--visibility", "-v",
        choices=["PRIVATE", "PROTECTED", "PUBLIC"],
        default="PROTECTED",
        help="Memo visibility (default: PROTECTED)"
    )
    create_parser.add_argument(
        "--pinned", "-p",
        action="store_true",
        help="Pin the memo"
    )
    
    # List command
    list_parser = subparsers.add_parser("list", help="List memos")
    list_parser.add_argument(
        "--limit", "-l",
        type=int,
        default=10,
        help="Number of memos to return (default: 10)"
    )
    list_parser.add_argument(
        "--filter", "-f",
        help="CEL filter expression"
    )
    
    # Get command
    get_parser = subparsers.add_parser("get", help="Get a memo")
    get_parser.add_argument("memo_id", help="Memo ID")
    
    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a memo")
    delete_parser.add_argument("memo_id", help="Memo ID")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == "create":
        create_memo(args.content, args.visibility, args.pinned)
    elif args.command == "list":
        list_memos(args.limit, args.filter)
    elif args.command == "get":
        get_memo(args.memo_id)
    elif args.command == "delete":
        delete_memo(args.memo_id)


if __name__ == "__main__":
    main()