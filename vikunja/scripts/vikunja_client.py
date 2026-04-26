#!/usr/bin/env python3
"""
Vikunja API Client

A Python client for interacting with Vikunja task management API.
"""

import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
import requests


class VikunjaClient:
    """Client for Vikunja API."""

    def __init__(self, base_url: Optional[str] = None, username: Optional[str] = None,
                 password: Optional[str] = None):
        """
        Initialize client with credentials.

        Priority: 1) Parameters 2) Environment variables 3) Config file
        """
        self.base_url = base_url or os.getenv('VIKUNJA_URL') or self._load_config('base_url')
        self.username = username or os.getenv('VIKUNJA_USERNAME') or self._load_config('username')
        self.password = password or os.getenv('VIKUNJA_PASSWORD') or self._load_config('password')
        self.token = None
        self._token_expires = None

    def _load_config(self, key: str) -> Optional[str]:
        """Load configuration from config file."""
        config_paths = [
            Path(__file__).parent.parent / 'config.json',  # skill 目录优先
            Path.home() / '.config' / 'vikunja' / 'config.json',
            Path.home() / '.vikunja' / 'config.json',
        ]
        for path in config_paths:
            if path.exists():
                try:
                    with open(path) as f:
                        config = json.load(f)
                        return config.get(key)
                except (json.JSONDecodeError, IOError):
                    pass
        return None

    def _get_headers(self) -> Dict[str, str]:
        """Get headers with authentication."""
        if not self.token:
            self.login()
        return {"Authorization": f"Bearer {self.token}"}

    def login(self) -> str:
        """Authenticate and get token."""
        login_data = {
            "long_token": True,
            "username": self.username,
            "password": self.password
        }
        response = requests.post(f"{self.base_url}/login", json=login_data)
        response.raise_for_status()
        data = response.json()
        self.token = data.get("token")
        return self.token

    def get_projects(self) -> List[Dict[str, Any]]:
        """Get all projects."""
        response = requests.get(
            f"{self.base_url}/projects",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    def get_project_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Find project by name (case-insensitive)."""
        projects = self.get_projects()
        for project in projects:
            if project.get('title', '').lower() == name.lower():
                return project
        return None

    def get_or_create_project(self, name: str) -> Dict[str, Any]:
        """Get project by name or create it if not exists."""
        project = self.get_project_by_name(name)
        if project:
            return project

        # Create new project
        response = requests.put(
            f"{self.base_url}/projects",
            json={"title": name},
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    def get_tasks(self, project_id: Optional[int] = None, done: bool = False,
                  due_filter: Optional[str] = 'today_or_earlier') -> List[Dict[str, Any]]:
        """
        Get tasks from a project or all projects.

        Args:
            project_id: Specific project ID, or None for all projects
            done: Filter by done status (False for pending tasks)
            due_filter: Filter by due date:
                       - 'today_or_earlier' (default): today + overdue tasks
                       - 'today': only due today
                       - 'overdue': only past due
                       - 'upcoming': only future tasks
                       - 'all' or None: all pending tasks
        """
        # Get all tasks first
        if project_id:
            params = {"filter": f"done={str(done).lower()}"}
            response = requests.get(
                f"{self.base_url}/projects/{project_id}/tasks",
                params=params,
                headers=self._get_headers()
            )
            response.raise_for_status()
            all_tasks = response.json()
        else:
            # Get tasks from all projects
            all_tasks = []
            projects = self.get_projects()
            for project in projects:
                try:
                    tasks = self.get_tasks(project['id'], done=done, due_filter='all')
                    for task in tasks:
                        task['project_title'] = project.get('title', 'Unknown')
                    all_tasks.extend(tasks)
                except requests.RequestException:
                    pass

        # Apply due date filter if specified
        if due_filter and due_filter != 'all':
            from datetime import timezone
            now = datetime.now(timezone.utc)
            today = now.replace(hour=0, minute=0, second=0, microsecond=0)

            filtered_tasks = []
            for task in all_tasks:
                due_str = task.get('due_date')
                # Vikunja returns '0001-01-01T00:00:00Z' for tasks without due date (Go zero value)
                if not due_str or due_str == '0001-01-01T00:00:00Z':
                    # Tasks without due date: show in default view (my todos) and 'all'
                    if due_filter in ('today_or_earlier', 'all'):
                        filtered_tasks.append(task)
                    continue

                try:
                    due_dt = datetime.fromisoformat(due_str.replace('Z', '+00:00'))
                    due_date = due_dt.replace(hour=0, minute=0, second=0, microsecond=0)
                    diff_days = (due_date - today).days

                    if due_filter == 'today' and diff_days == 0:
                        filtered_tasks.append(task)
                    elif due_filter == 'overdue' and diff_days < 0:
                        filtered_tasks.append(task)
                    elif due_filter == 'today_or_earlier' and diff_days <= 0:
                        filtered_tasks.append(task)
                    elif due_filter == 'upcoming' and diff_days > 0:
                        filtered_tasks.append(task)
                except (ValueError, TypeError):
                    pass

            return filtered_tasks

        return all_tasks

    def create_task(self, title: str, project_id: int = 1,
                    description: str = "", due_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new task.

        Args:
            title: Task title
            project_id: Project ID (default: 1 for inbox)
            description: Task description
            due_date: ISO 8601 formatted datetime string
        """
        task_data = {
            "title": title,
            "description": description
        }

        if due_date:
            task_data["due_date"] = due_date

        response = requests.put(
            f"{self.base_url}/projects/{project_id}/tasks",
            json=task_data,
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    def update_task(self, task_id: int, title: Optional[str] = None,
                    description: Optional[str] = None,
                    project_id: Optional[int] = None,
                    due_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Update an existing task.

        Args:
            task_id: Task ID to update
            title: New title (optional)
            description: New description (optional)
            project_id: New project ID (optional)
            due_date: New due date (optional)
        """
        update_data = {}
        if title is not None:
            update_data["title"] = title
        if description is not None:
            update_data["description"] = description
        if project_id is not None:
            update_data["project_id"] = project_id
        if due_date is not None:
            update_data["due_date"] = due_date

        response = requests.post(
            f"{self.base_url}/tasks/{task_id}",
            json=update_data,
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    def complete_task(self, task_id: int) -> Dict[str, Any]:
        """Mark a task as completed."""
        response = requests.post(
            f"{self.base_url}/tasks/{task_id}",
            json={"done": True},
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    def delete_task(self, task_id: int) -> None:
        """Delete a task."""
        response = requests.delete(
            f"{self.base_url}/tasks/{task_id}",
            headers=self._get_headers()
        )
        response.raise_for_status()


class DateParser:
    """Parse Chinese date expressions into ISO 8601 format."""

    def __init__(self):
        self.now = datetime.now()

    def parse(self, date_str: str, default_time: str = "09:00") -> Optional[str]:
        """
        Parse date expression and return ISO 8601 formatted datetime.

        Returns None if no date could be parsed.
        """
        if not date_str:
            return None

        date_str = date_str.strip().lower()

        # Check for "no date" expressions
        if any(x in date_str for x in ['无', '不设置', '无截止', '无时间', '不']):
            return None

        # Parse time first
        time_match = self._extract_time(date_str)
        hour, minute = time_match if time_match else self._parse_time(default_time)

        # Parse date
        target_date = self._parse_date(date_str)
        if target_date:
            target_date = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            return target_date.strftime('%Y-%m-%dT%H:%M:%SZ')

        return None

    def _extract_time(self, text: str) -> Optional[tuple]:
        """Extract time from text. Returns (hour, minute) or None."""
        # Pattern: 下午3点, 下午3:30, 15:00, 3点, 3:30
        patterns = [
            (r'(下午|晚上|傍晚)\s*(\d+)\s*[点:](\d*)', self._pm_time),
            (r'(上午|早上|早晨)\s*(\d+)\s*[点:](\d*)', self._am_time),
            (r'(\d{1,2}):(\d{2})', self._direct_time),
            (r'(\d+)\s*[点:](\d*)', self._cn_time),
        ]

        for pattern, parser in patterns:
            match = re.search(pattern, text)
            if match:
                return parser(match)
        return None

    def _pm_time(self, match) -> tuple:
        hour = int(match.group(2))
        minute = int(match.group(3)) if match.group(3) else 0
        if hour < 12:
            hour += 12
        return (hour, minute)

    def _am_time(self, match) -> tuple:
        hour = int(match.group(2))
        minute = int(match.group(3)) if match.group(3) else 0
        return (hour, minute)

    def _direct_time(self, match) -> tuple:
        return (int(match.group(1)), int(match.group(2)))

    def _cn_time(self, match) -> tuple:
        hour = int(match.group(1))
        minute_str = match.group(2)
        minute = int(minute_str) if minute_str else 0
        return (hour, minute)

    def _parse_time(self, time_str: str) -> tuple:
        """Parse HH:MM format."""
        parts = time_str.split(':')
        return (int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)

    def _parse_date(self, text: str) -> Optional[datetime]:
        """Parse date part."""
        today = self.now.date()

        # 明天
        if '明天' in text:
            return datetime.combine(today + timedelta(days=1), datetime.min.time())

        # 后天
        if '后天' in text:
            return datetime.combine(today + timedelta(days=2), datetime.min.time())

        # 大后天
        if '大后天' in text:
            return datetime.combine(today + timedelta(days=3), datetime.min.time())

        # X天后
        match = re.search(r'(\d+)\s*天后', text)
        if match:
            days = int(match.group(1))
            return datetime.combine(today + timedelta(days=days), datetime.min.time())

        # 下周X
        weekday_map = {
            '一': 0, '二': 1, '三': 2, '四': 3, '五': 4, '六': 5, '日': 6,
            '天': 6, '七': 6,
            '1': 0, '2': 1, '3': 2, '4': 3, '5': 4, '6': 5, '7': 6
        }
        match = re.search(r'下[周|星期|礼拜]([一二三四五六日天1234567])', text)
        if match:
            target_weekday = weekday_map.get(match.group(1))
            if target_weekday is not None:
                days_ahead = target_weekday - today.weekday() + 7
                return datetime.combine(today + timedelta(days=days_ahead), datetime.min.time())

        # 本周X/这周X
        match = re.search(r'[这本][周|星期|礼拜]([一二三四五六日天1234567])', text)
        if match:
            target_weekday = weekday_map.get(match.group(1))
            if target_weekday is not None:
                days_ahead = target_weekday - today.weekday()
                if days_ahead <= 0:  # Today or past this week
                    days_ahead += 7
                return datetime.combine(today + timedelta(days=days_ahead), datetime.min.time())

        # YYYY-MM-DD or YYYY/MM/DD
        match = re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', text)
        if match:
            year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
            return datetime(year, month, day)

        # MM月DD日
        match = re.search(r'(\d{1,2})\s*月\s*(\d{1,2})\s*[日号]?', text)
        if match:
            month, day = int(match.group(1)), int(match.group(2))
            year = today.year
            # If date has passed this year, assume next year
            try:
                result = datetime(year, month, day)
                if result.date() < today:
                    result = datetime(year + 1, month, day)
                return result
            except ValueError:
                pass

        # 今天
        if '今天' in text:
            return datetime.combine(today, datetime.min.time())

        return None


def smart_project_selection(task_title: str, description: str = "") -> str:
    """
    Intelligently select project based on task content.

    Returns project name suggestion.
    """
    text = (task_title + " " + description).lower()

    # Work-related keywords
    work_keywords = ['工作', '项目', '会议', '报告', '客户', '同事', '老板',
                     '邮件', '周报', '月报', '汇报', '讨论', 'review', 'deadline']
    if any(kw in text for kw in work_keywords):
        return '工作'

    # Study-related keywords
    study_keywords = ['学习', '课程', '考试', '作业', '论文', '阅读', '书',
                      '笔记', '复习', '预习', 'study', 'book']
    if any(kw in text for kw in study_keywords):
        return '学习'

    # Shopping keywords
    shopping_keywords = ['买', '购物', '采购', '下单', '订购', 'shop', 'buy']
    if any(kw in text for kw in shopping_keywords):
        return '购物'

    # Default to inbox
    return '收件箱'


def format_relative_time(due_dt: datetime) -> str:
    """Format datetime as relative time (今天, 明天, 3天内, X天前等)."""
    now = datetime.now(due_dt.tzinfo) if due_dt.tzinfo else datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    due_date = due_dt.replace(hour=0, minute=0, second=0, microsecond=0)

    diff_days = (due_date - today).days
    time_str = due_dt.strftime('%H:%M')

    # Future dates
    if diff_days == 0:
        return f"今天 {time_str}"
    elif diff_days == 1:
        return f"明天 {time_str}"
    elif diff_days == 2:
        return f"后天 {time_str}"
    elif 3 <= diff_days <= 7:
        return f"{diff_days}天内 ({time_str})"
    elif diff_days > 7:
        weeks = diff_days // 7
        if weeks <= 4:
            return f"{weeks}周后 ({time_str})"
        else:
            return due_dt.strftime('%m月%d日 %H:%M')

    # Past dates (overdue)
    elif diff_days == -1:
        return f"昨天 {time_str} ⚠️"
    elif diff_days == -2:
        return f"前天 {time_str} ⚠️"
    elif -7 < diff_days < 0:
        return f"{abs(diff_days)}天前 ⚠️"
    else:
        return due_dt.strftime('%m月%d日 %H:%M') + " ⚠️"


def format_task_list(tasks: List[Dict[str, Any]]) -> str:
    """Format tasks as tables, one per project."""
    if not tasks:
        return "暂无待办任务"

    # Group by project
    by_project = {}
    for task in tasks:
        project = task.get('project_title', '未知项目')
        if project not in by_project:
            by_project[project] = []
        by_project[project].append(task)

    lines = []
    for project, proj_tasks in sorted(by_project.items()):
        # Sort tasks: with due date first, then by due date
        def sort_key(t):
            due = t.get('due_date')
            return (0, due) if due else (1, '')
        sorted_tasks = sorted(proj_tasks, key=sort_key)

        # Prepare table rows
        rows = []
        for task in sorted_tasks:
            task_id = task.get('id', '?')
            title = task.get('title', '无标题')
            due = task.get('due_date')
            if due and due != '0001-01-01T00:00:00Z':
                try:
                    due_dt = datetime.fromisoformat(due.replace('Z', '+00:00'))
                    due_str = format_relative_time(due_dt)
                except:
                    due_str = due
            else:
                due_str = "无截止时间"
            rows.append([str(task_id), title, due_str])

        # Calculate column widths
        id_width = max(len(r[0]) for r in rows) + 2
        title_width = max(len(r[1]) for r in rows) + 2
        due_width = max(len(r[2]) for r in rows) + 2
        # Cap title width for readability
        title_width = min(title_width, 50)

        # Build table
        lines.append(f"\n📋 **{project}**")
        lines.append("| ID | 任务 | 时间 |")
        lines.append(f"|{'-' * (id_width-1)}|{'-' * (title_width-1)}|{'-' * (due_width-1)}|")
        for row in rows:
            # Truncate title if too long
            title_display = row[1][:title_width-3] + "..." if len(row[1]) > title_width-2 else row[1]
            lines.append(f"| {row[0]} | {title_display} | {row[2]} |")

    return '\n'.join(lines)


# CLI interface for testing
if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python vikunja_client.py <command> [args]")
        print("Commands:")
        print("  projects                  - List all projects")
        print("  tasks [filter]            - List tasks (filters: today, overdue, all)")
        print("  create <title> [project] [due_date]  - Create a task")
        print("  complete <task_id>        - Complete a task")
        sys.exit(1)

    client = VikunjaClient()
    cmd = sys.argv[1]

    if cmd == 'projects':
        projects = client.get_projects()
        for p in projects:
            print(f"{p['id']}: {p['title']}")

    elif cmd == 'tasks':
        due_filter = sys.argv[2] if len(sys.argv) > 2 else 'today_or_earlier'
        tasks = client.get_tasks(due_filter=due_filter)
        print(format_task_list(tasks))

    elif cmd == 'create':
        if len(sys.argv) < 3:
            print("Usage: create <title> [project] [due_date]")
            sys.exit(1)
        title = sys.argv[2]
        project_name = sys.argv[3] if len(sys.argv) > 3 else '收件箱'
        due_str = sys.argv[4] if len(sys.argv) > 4 else None

        project = client.get_or_create_project(project_name)

        parser = DateParser()
        due_date = parser.parse(due_str) if due_str else None

        task = client.create_task(title, project['id'], due_date=due_date)
        print(f"Created task: {task['title']} (ID: {task['id']})")

    elif cmd == 'complete':
        if len(sys.argv) < 3:
            print("Usage: complete <task_id> [task_id2] ... [--show <filter>]")
            print("  --show my: 显示剩余待办（今日+逾期+无截止时间）")
            print("  --show all: 显示所有剩余待办")
            print("  --show none: 不显示剩余待办")
            sys.exit(1)
        
        # Parse task IDs and show filter
        task_ids = []
        show_filter = 'my'  # default
        for arg in sys.argv[2:]:
            if arg.startswith('--show='):
                show_filter = arg.split('=')[1]
            elif arg == '--show':
                show_filter = sys.argv[sys.argv.index('--show') + 1] if sys.argv.index('--show') + 1 < len(sys.argv) else 'my'
            elif arg not in ('my', 'all', 'none'):
                try:
                    task_ids.append(int(arg))
                except ValueError:
                    pass
        
        # Complete tasks
        completed = []
        for task_id in task_ids:
            try:
                result = client.complete_task(task_id)
                completed.append(f"[{task_id}] {result['title']}")
            except Exception as e:
                completed.append(f"[{task_id}] Failed: {e}")
        print("Completed:\n" + "\n".join(completed))
        
        # Show remaining tasks
        if show_filter != 'none':
            due_filter = 'all' if show_filter == 'all' else 'today_or_earlier'
            remaining = client.get_tasks(due_filter=due_filter)
            print("\n" + format_task_list(remaining))
