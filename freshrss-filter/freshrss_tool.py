#!/usr/bin/env python3
"""
FreshRSS 过滤 Skill - 数据工具

使用方法：
  python freshrss_tool.py fetch              # 获取条目（供 Claude 判断）
  python freshrss_tool.py mark --ids id1,id2  # 标记已读
  python freshrss_tool.py stats              # 统计
"""

import json
import re
import sys
import argparse
import requests
from pathlib import Path
from collections import Counter
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "config.json"
FEED_BLACKLIST_FILE = SCRIPT_DIR / "feed_blacklist.txt"
AUTHOR_BLACKLIST_FILE = SCRIPT_DIR / "author_blacklist.txt"
CONTENT_BLACKLIST_FILE = SCRIPT_DIR / "content_blacklist.txt"
LOGS_DIR = SCRIPT_DIR / "logs"

# ============ 配置加载 ============

def load_config():
    if not CONFIG_FILE.exists():
        print(f"❌ 配置文件不存在: {CONFIG_FILE}", file=sys.stderr)
        sys.exit(1)
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_content_blacklist():
    """加载内容正则黑名单"""
    return load_regex_patterns(CONTENT_BLACKLIST_FILE)

def load_feed_blacklist():
    """加载来源正则黑名单"""
    return load_regex_patterns(FEED_BLACKLIST_FILE)

def load_author_blacklist():
    """加载作者正则黑名单"""
    return load_regex_patterns(AUTHOR_BLACKLIST_FILE)

def load_regex_patterns(filepath):
    """通用函数：从文件加载正则表达式"""
    patterns = []
    if not filepath.exists():
        return patterns
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                try:
                    patterns.append(re.compile(line, re.IGNORECASE))
                except re.error as e:
                    print(f"⚠️ 无效正则: {line} - {e}", file=sys.stderr)
    return patterns

# ============ 日志 ============

# 当前会话的日志文件（按时间戳生成）
CURRENT_LOG_FILE = None
LOG_STATS = {}

def init_log(log_file=None):
    """初始化日志文件（按时间戳命名，或使用指定的日志文件）"""
    global CURRENT_LOG_FILE, LOG_STATS
    LOGS_DIR.mkdir(exist_ok=True)
    
    if log_file:
        # 使用指定的日志文件（追加模式，从日志解析之前的统计）
        CURRENT_LOG_FILE = Path(log_file)
        # 尝试从日志文件解析之前的统计
        LOG_STATS = parse_stats_from_log(CURRENT_LOG_FILE)
        if not LOG_STATS:
            LOG_STATS = {
                'start_time': datetime.now().isoformat(),
                'total': 0, 'feed_filtered': 0, 'author_filtered': 0,
                'content_filtered': 0, 'blacklist_marked': 0, 'marked': 0
            }
    else:
        # 创建新的日志文件
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        CURRENT_LOG_FILE = LOGS_DIR / f"filter_{timestamp}.log"
        LOG_STATS = {
            'start_time': datetime.now().isoformat(),
            'total': 0, 'feed_filtered': 0, 'author_filtered': 0,
            'content_filtered': 0, 'blacklist_marked': 0, 'marked': 0
        }
        with open(CURRENT_LOG_FILE, 'w', encoding='utf-8') as f:
            f.write(f"[{LOG_STATS['start_time']}] FreshRSS Filter Session Started\n")
            f.write("=" * 70 + "\n")
    return CURRENT_LOG_FILE

def parse_stats_from_log(log_file):
    """从日志文件解析之前的统计数据"""
    stats = {
        'start_time': '',
        'total': 0, 'feed_filtered': 0, 'author_filtered': 0,
        'content_filtered': 0, 'blacklist_marked': 0, 'marked': 0
    }
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # 解析日志行
            for line in content.split('\n'):
                if line.startswith('[') and 'Session Started' in line:
                    stats['start_time'] = line.split(']')[0][1:]
                if '获取到' in line and '条未读' in line:
                    match = re.search(r'获取到 (\d+) 条', line)
                    if match:
                        stats['total'] = int(match.group(1))
                if 'Feed黑名单过滤:' in line:
                    match = re.search(r'(\d+) 条', line)
                    if match:
                        stats['feed_filtered'] = int(match.group(1))
                if '作者黑名单过滤:' in line:
                    match = re.search(r'(\d+) 条', line)
                    if match:
                        stats['author_filtered'] = int(match.group(1))
                if '内容黑名单过滤:' in line:
                    match = re.search(r'(\d+) 条', line)
                    if match:
                        stats['content_filtered'] = int(match.group(1))
                if '自动标记黑名单过滤条目:' in line:
                    match = re.search(r'(\d+) 条', line)
                    if match:
                        stats['blacklist_marked'] = int(match.group(1))
    except Exception:
        pass
    return stats

def log(msg):
    """记录日志并打印到 stderr"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"[{timestamp}] {msg}"
    print(log_msg, file=sys.stderr)
    if CURRENT_LOG_FILE:
        with open(CURRENT_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_msg + '\n')

def log_stat(key, value):
    """更新统计"""
    LOG_STATS[key] = value

def finalize_log():
    """完成日志，写入统计"""
    if not CURRENT_LOG_FILE:
        return
    LOG_STATS['end_time'] = datetime.now().isoformat()
    total_marked = LOG_STATS.get('blacklist_marked', 0) + LOG_STATS.get('marked', 0)
    remaining = LOG_STATS.get('total', 0) - total_marked
    with open(CURRENT_LOG_FILE, 'a', encoding='utf-8') as f:
        f.write("\n" + "=" * 70 + "\n")
        f.write("过滤统计:\n")
        f.write(f"  总条目: {LOG_STATS.get('total', 0)}\n")
        f.write(f"  来源黑名单: {LOG_STATS.get('feed_filtered', 0)}\n")
        f.write(f"  作者黑名单: {LOG_STATS.get('author_filtered', 0)}\n")
        f.write(f"  内容黑名单: {LOG_STATS.get('content_filtered', 0)}\n")
        f.write(f"  黑名单自动标记: {LOG_STATS.get('blacklist_marked', 0)}\n")
        f.write(f"  AI过滤标记: {LOG_STATS.get('marked', 0)}\n")
        f.write(f"  总计标记: {total_marked}\n")
        f.write(f"  剩余未读: {remaining}\n")
        f.write(f"  日志文件: {CURRENT_LOG_FILE.name}\n")
        f.write("=" * 70 + "\n")
    print(f"\n📝 日志已保存: {CURRENT_LOG_FILE}", file=sys.stderr)

# ============ FreshRSS 客户端 ============

class FreshRSSClient:
    def __init__(self):
        config = load_config()
        self.base_url = config["freshrss_url"].rstrip('/')
        self.username = config["username"]
        self.password = config["api_password"]
        self.api_base = f"{self.base_url}/api/greader.php"
        self.session = None

    def authenticate(self):
        self.session = requests.Session()
        auth_url = f"{self.api_base}/accounts/ClientLogin"
        resp = self.session.post(auth_url, data={
            'Email': self.username,
            'Passwd': self.password,
            'service': 'reader'
        }, timeout=10)

        if resp.status_code != 200:
            print(f"❌ 认证失败: {resp.status_code}", file=sys.stderr)
            return False

        auth_info = dict(line.split('=', 1) for line in resp.text.strip().split('\n') if '=' in line)
        auth_token = auth_info.get('Auth')
        self.session.headers.update({'Authorization': f"GoogleLogin auth={auth_token}"})
        return True

    def get_unread_entries(self, limit=1000):
        """获取未读条目"""
        url = f"{self.api_base}/reader/api/0/stream/contents/user/-/state/com.google/reading-list"
        params = {'output': 'json', 'n': limit, 'r': 'n', 'xt': 'user/-/state/com.google/read'}
        resp = self.session.get(url, params=params, timeout=30)

        if resp.status_code != 200:
            log(f"获取条目失败: {resp.status_code}")
            return []

        items = resp.json().get('items', [])
        entries = []

        for item in items:
            summary = item.get('summary', {})
            content = item.get('content', {})
            text = content.get('content', '') or summary.get('content', '')
            origin = item.get('origin', {})
            alternates = item.get('alternate', [])

            entries.append({
                'id': item.get('id', ''),
                'title': item.get('title', ''),
                'author': item.get('author', ''),
                'content': text,
                'feed_name': origin.get('title', ''),
                'feed_url': origin.get('htmlUrl', ''),
                'url': alternates[0].get('href', '') if alternates else '',
                'published': item.get('published', 0)
            })

        return entries

    def mark_as_read(self, entry_ids):
        """标记条目为已读"""
        if not entry_ids:
            return 0

        token_url = f"{self.api_base}/reader/api/0/token"
        token_resp = self.session.get(token_url, timeout=10)
        token = token_resp.text.strip() if token_resp.status_code == 200 else ''

        url = f"{self.api_base}/reader/api/0/edit-tag"
        success = 0

        for entry_id in entry_ids:
            resp = self.session.post(url, data={
                'i': entry_id,
                'a': 'user/-/state/com.google/read',
                'T': token
            }, timeout=10)
            if resp.status_code == 200:
                success += 1

        return success

# ============ 过滤逻辑 ============

def filter_by_feed(entries, feed_patterns):
    """按 Feed 来源过滤（支持正则）"""
    filtered = []
    remaining = []

    for entry in entries:
        feed_name = entry['feed_name']
        matched = False
        matched_pattern = None

        for pattern in feed_patterns:
            if pattern.search(feed_name):
                matched = True
                matched_pattern = pattern.pattern
                break

        if matched:
            entry['filter_reason'] = f'来源黑名单: {matched_pattern[:30]}'
            filtered.append(entry)
        else:
            remaining.append(entry)

    return filtered, remaining

def filter_by_author(entries, author_patterns):
    """按作者过滤（支持正则）"""
    if not author_patterns:
        return [], entries

    filtered = []
    remaining = []

    for entry in entries:
        author = entry.get('author', '')
        matched = False
        matched_pattern = None

        for pattern in author_patterns:
            if pattern.search(author):
                matched = True
                matched_pattern = pattern.pattern
                break

        if matched:
            entry['filter_reason'] = f'作者黑名单: {matched_pattern[:30]}'
            filtered.append(entry)
        else:
            remaining.append(entry)

    return filtered, remaining

def filter_by_content(entries, patterns):
    """按内容正则过滤"""
    filtered = []
    remaining = []

    for entry in entries:
        text = f"{entry['title']} {entry['content'][:500]}"
        matched = False
        matched_pattern = None

        for pattern in patterns:
            if pattern.search(text):
                matched = True
                matched_pattern = pattern.pattern
                break

        if matched:
            entry['filter_reason'] = f'内容黑名单: {matched_pattern[:30]}'
            filtered.append(entry)
        else:
            remaining.append(entry)

    return filtered, remaining

# ============ 格式化输出 ============

def format_entry(entry, index):
    """格式化条目为易读格式"""
    date = datetime.fromtimestamp(entry['published']).strftime('%m-%d %H:%M') if entry['published'] else 'N/A'
    title = entry['title'][:70] + '...' if len(entry['title']) > 70 else entry['title']
    content = entry['content'][:150].replace('\n', ' ').strip() if entry['content'] else '无内容'

    return {
        'index': index,
        'id': entry['id'],
        'date': date,
        'feed': entry['feed_name'],
        'title': title,
        'content_preview': content + '...' if len(entry['content']) > 150 else content
    }

def group_by_feed(entries):
    groups = {}
    for entry in entries:
        feed = entry['feed_name']
        if feed not in groups:
            groups[feed] = []
        groups[feed].append(entry)
    return groups

# ============ 命令 ============

def cmd_fetch(args):
    """获取条目供 Claude 判断"""
    # 初始化日志
    log_file = init_log()
    log(f"日志文件: {log_file.name}")

    client = FreshRSSClient()
    if not client.authenticate():
        sys.exit(1)

    # 获取条目
    entries = client.get_unread_entries()
    log_stat('total', len(entries))
    log(f"获取到 {len(entries)} 条未读")

    if not entries:
        print("✅ 没有未读条目")
        finalize_log()
        return

    # 1. Feed 黑名单过滤
    feed_patterns = load_feed_blacklist()
    feed_filtered, after_feed = filter_by_feed(entries, feed_patterns)
    log_stat('feed_filtered', len(feed_filtered))
    log(f"Feed黑名单过滤: {len(feed_filtered)} 条")

    # 2. 作者黑名单过滤
    author_patterns = load_author_blacklist()
    author_filtered, after_author = filter_by_author(after_feed, author_patterns)
    log_stat('author_filtered', len(author_filtered))
    log(f"作者黑名单过滤: {len(author_filtered)} 条")

    # 3. 内容黑名单过滤
    patterns = load_content_blacklist()
    content_filtered, after_content = filter_by_content(after_author, patterns)
    log_stat('content_filtered', len(content_filtered))
    log(f"内容黑名单过滤: {len(content_filtered)} 条")

    # 自动标记黑名单过滤的条目为已读
    blacklist_ids = [e['id'] for e in feed_filtered + author_filtered + content_filtered]
    if blacklist_ids:
        log(f"自动标记黑名单过滤条目: {len(blacklist_ids)} 条")
        # 写入黑名单过滤详情到日志
        with open(CURRENT_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write("\n--- 黑名单过滤条目详情 ---\n")
            for e in feed_filtered:
                f.write(f"[Feed黑名单] {e['title'][:80]} | 原因: {e.get('filter_reason', 'N/A')}\n")
            for e in author_filtered:
                f.write(f"[作者黑名单] {e['title'][:80]} | 作者: {e.get('author', 'N/A')} | 原因: {e.get('filter_reason', 'N/A')}\n")
            for e in content_filtered:
                f.write(f"[内容黑名单] {e['title'][:80]} | 原因: {e.get('filter_reason', 'N/A')}\n")
            f.write("--- 黑名单过滤条目详情结束 ---\n")
        marked = client.mark_as_read(blacklist_ids)
        log_stat('blacklist_marked', marked)
        log(f"成功标记: {marked} 条")

    # 统计
    groups = group_by_feed(after_content)

    # 输出 JSON（给 Claude 解析）- 只保留候选条目
    output = {
        'log_file': str(log_file),
        'stats': {
            'total': len(entries),
            'feed_filtered': len(feed_filtered),
            'author_filtered': len(author_filtered),
            'content_filtered': len(content_filtered),
            'blacklist_marked': len(blacklist_ids) if blacklist_ids else 0,
            'remaining': len(after_content)
        },
        'candidates': {}
    }

    # 准备候选条目（按 feed 分组）
    index = 1
    for feed, items in sorted(groups.items(), key=lambda x: -len(x[1])):
        feed_entries = []
        for item in items:
            formatted = format_entry(item, index)
            feed_entries.append({
                'index': index,
                'id': item['id'],
                'title': formatted['title'],
                'date': formatted['date'],
                'content_preview': formatted['content_preview'],
                'url': item['url']
            })
            index += 1
        output['candidates'][feed] = feed_entries

    print(json.dumps(output, ensure_ascii=False, indent=2))
    finalize_log()

def cmd_mark(args):
    """标记条目为已读"""
    if not args.ids:
        print("❌ 请提供 --ids 参数", file=sys.stderr)
        sys.exit(1)

    ids = [id.strip() for id in args.ids.split(',')]

    # 初始化日志（使用指定的日志文件或创建新的）
    log_file = init_log(args.log_file)
    if args.log_file:
        log(f"继续写入日志: {log_file.name}")
    else:
        log(f"日志文件: {log_file.name}")

    # 如果提供了详情，写入日志
    if args.details:
        details = json.loads(args.details)
        with open(CURRENT_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write("\n--- AI过滤条目详情 ---\n")
            for item in details:
                f.write(f"[AI过滤] {item.get('title', 'N/A')[:80]} | 原因: {item.get('reason', 'N/A')}\n")
            f.write("--- AI过滤条目详情结束 ---\n")

    client = FreshRSSClient()
    if not client.authenticate():
        sys.exit(1)

    log(f"标记 {len(ids)} 条为已读")
    success = client.mark_as_read(ids)
    # AI 过滤标记数量
    log_stat('marked', success)
    log(f"成功标记 {success} 条")
    finalize_log()

    result = {'success': success, 'total': len(ids), 'failed': len(ids) - success}
    print(json.dumps(result, ensure_ascii=False))

def cmd_stats(args):
    """统计"""
    client = FreshRSSClient()
    if not client.authenticate():
        sys.exit(1)

    entries = client.get_unread_entries()
    feeds = Counter(e['feed_name'] for e in entries)

    output = {
        'total': len(entries),
        'feeds': [{'name': name, 'count': count} for name, count in feeds.most_common()]
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))

# ============ 主入口 ============

def main():
    parser = argparse.ArgumentParser(description='FreshRSS 过滤工具')
    parser.add_argument('command', choices=['fetch', 'mark', 'stats'], help='命令')
    parser.add_argument('--ids', help='要标记的 ID（逗号分隔）')
    parser.add_argument('--details', help='AI过滤详情 JSON: [{"title":"...", "reason":"..."}]')
    parser.add_argument('--log-file', help='继续写入指定的日志文件（fetch 返回的路径）')
    args = parser.parse_args()

    if args.command == 'fetch':
        cmd_fetch(args)
    elif args.command == 'mark':
        cmd_mark(args)
    elif args.command == 'stats':
        cmd_stats(args)

if __name__ == "__main__":
    main()
