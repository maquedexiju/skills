#!/usr/bin/env python3
"""
思源笔记周报创建脚本

创建每周周报文档，包含预设模板。

用法:
    python create_weekly_report.py       # 本周
    python create_weekly_report.py -1    # 上周
    python create_weekly_report.py 1     # 下周
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
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
    # 默认配置
    return {
        "api_url": "http://127.0.0.1:6806",
        "token": "",
        "default_notebook": ""
    }

config = load_config()
API_URL = config.get("api_url", "http://127.0.0.1:6806")
TOKEN = config.get("token", "")
NOTEBOOK = config.get("default_notebook", "")


def calculate_week_range(adjust: int = 0) -> tuple:
    """计算周日期范围"""
    today = datetime.today()
    target = today + timedelta(weeks=adjust)
    
    # 获取周一（isocalendar()[2] 是星期几，1=周一）
    monday = target - timedelta(days=target.isocalendar()[2] - 1)
    sunday = monday + timedelta(days=6)
    
    year = target.year
    week_num = target.isocalendar()[1]
    
    return year, week_num, monday, sunday


def generate_report_template(monday: datetime, sunday: datetime) -> str:
    """生成周报模板"""
    date_range = f"{monday.strftime('%m.%d')} - {sunday.strftime('%m.%d')}"

    # 加载模板配置
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    TEMPLATE_PATH = os.path.join(SCRIPT_DIR, "weekly_template.py")

    family_members = []
    goals_template = None
    report_path_template = "/生活记录/{year}/{year} 年第 {week_num:02d} 周"

    if os.path.exists(TEMPLATE_PATH):
        import importlib.util
        spec = importlib.util.spec_from_file_location("weekly_template", TEMPLATE_PATH)
        template_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(template_module)
        family_members = getattr(template_module, "FAMILY_MEMBERS", [])
        goals_template = getattr(template_module, "GOALS_TEMPLATE", None)
        report_path_template = getattr(template_module, "REPORT_PATH_TEMPLATE", report_path_template)

    # 构建家人部分
    family_section = "\n".join([f"- {name}：{note}" for name, note in family_members]) if family_members else "- 家人："

    # 琐事部分
    summary = f'''
{{{col
{{{row
{{{{
家人
{{: style="color: #ffffff;background-color: #4c5870; padding-left: 10px;"}}

{family_section}
}}}}
{{: memo="家人"}}
{{{{
烹饪
{{: style="color: #ffffff;background-color: #4c5870; padding-left: 10px;"}}
- 带饭：
- 周末做饭：
}}}}
{{: memo="烹饪"}}
}}}}
{{: style="width: 66%; flex: none;"}}
{{{{
生活状态
{{: style="color: #ffffff;background-color: #4c5870; padding-left: 10px;"}}
- 睡眠：短/正常/长
- 通勤：短/正常/长
- 娱乐：短/正常/长
}}}}
{{: memo="生活状态"}}
}}}}
'''

    # 目标部分
    goals = goals_template if goals_template else '''
{{{col
{{{
工作
{: style="color: #ffffff;background-color: #07689f; padding-left: 10px;"}
- [ ] 工作事项1
}}}
{{{
成长 & 运动 ⭐
{: style="color: #ffffff;background-color: #07689f; padding-left: 10px;"}
- [ ] 量化：
- [ ] 读书：书名-页码，0/50
}}}
{{{
其他
{: style="color: #ffffff;background-color: #07689f; padding-left: 10px;"}
- [ ] 社交
- [ ] 聚焦：一件事、番茄钟、反黑洞
}}}
}}}
{: memo="目标"}
'''
    
    # 每日记录部分
    days = '''
{{{col
{{{
周一 ·
{: style="color: #ffffff;background-color: #079F89; padding-left: 10px;" memo="今日状态"}

-
}}}
{{{
周二 ·
{: style="color: #ffffff;background-color: #079F89; padding-left: 10px;" memo="今日状态"}

-
}}}
{{{
周三 ·
{: style="color: #ffffff;background-color: #079F89; padding-left: 10px;" memo="今日状态"}

-
}}}
}}}

{{{col
{{{
周四 ·
{: style="color: #ffffff;background-color: #079F89; padding-left: 10px;" memo="今日状态"}

-
}}}
{{{
周五 ·
{: style="color: #ffffff;background-color: #079F89; padding-left: 10px;" memo="今日状态"}

-
}}}
{{{
周六 ·
{: style="color: #ffffff;background-color: #079F89; padding-left: 10px;" memo="今日状态"}

-
}}}
}}}

{{{col
{{{
周日 ·
{: style="color: #ffffff;background-color: #079F89; padding-left: 10px;" memo="今日状态"}

-

}}}
{{{
{: style="color: #ffffff;background-color: #ffffff;opacity:0%;"}
}}}
{{{
{: style="color: #ffffff;background-color: #ffffff;opacity:0%;"}
}}}
}}}'''
    
    # 大事件部分
    bigdeal = '''- 【技能提升】你长进了吗？（没有删掉）
- 做了什么（这行删掉）
{: memo="做了什么"}'''
    
    # 组合完整模板
    content = f'''
## 大事件（做了什么）

{bigdeal}

## 琐事

{summary}

## 目标

{goals}

## 记录

`状态：工作 | 自我 | 均衡 | 休息 | 陪伴 | 频废 | 松弛`

{days}

## 本周感悟

'''
    
    return date_range + content


def create_report(year: int, week_num: int, markdown: str) -> str:
    """调用思源 API 创建周报"""
    # 加载模板配置获取路径格式
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    TEMPLATE_PATH = os.path.join(SCRIPT_DIR, "weekly_template.py")

    report_path_template = "/生活记录/{year}/{year} 年第 {week_num:02d} 周"
    if os.path.exists(TEMPLATE_PATH):
        import importlib.util
        spec = importlib.util.spec_from_file_location("weekly_template", TEMPLATE_PATH)
        template_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(template_module)
        report_path_template = getattr(template_module, "REPORT_PATH_TEMPLATE", report_path_template)

    path = report_path_template.format(year=year, week_num=week_num)
    
    payload = {
        "notebook": NOTEBOOK,
        "path": path,
        "markdown": markdown
    }
    
    req = r.Request(
        f"{API_URL}/api/filetree/createDocWithMd",
        headers={
            "Authorization": f"Token {TOKEN}",
            "Content-Type": "application/json"
        },
        method="POST",
        data=json.dumps(payload).encode("utf-8")
    )
    
    opener = r.build_opener(r.HTTPHandler())
    response = opener.open(req)
    result = json.loads(response.read().decode("utf-8"))
    
    if result.get("code") != 0:
        print(f"Error: {result.get('msg', 'Unknown error')}")
        sys.exit(1)
    
    doc_id = result["data"]
    return doc_id, path


def perform_sync():
    """创建周报后执行同步"""
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


def main():
    parser = argparse.ArgumentParser(description="创建思源周报")
    parser.add_argument("adjust", nargs="?", type=int, default=0,
                        help="周数调整（-1=上周, 1=下周）")
    parser.add_argument("--no-sync", action="store_true",
                        help="创建后不触发同步")
    args = parser.parse_args()
    
    # 计算周范围
    year, week_num, monday, sunday = calculate_week_range(args.adjust)
    
    print(f"Creating weekly report for Week {week_num} of {year}")
    print(f"Date range: {monday.strftime('%Y-%m-%d')} to {sunday.strftime('%Y-%m-%d')}")
    
    # 生成模板
    markdown = generate_report_template(monday, sunday)
    
    # 创建文档
    doc_id, path = create_report(year, week_num, markdown)
    
    print(f"Created: {path}")
    print(f"Document ID: {doc_id}")
    print(f"Open: siyuan://blocks/{doc_id}")
    
    # 创建后触发同步
    if not args.no_sync and TOKEN:
        print("\nTriggering sync...")
        perform_sync()


if __name__ == "__main__":
    main()