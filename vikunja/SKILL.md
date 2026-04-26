---
name: vikunja
description: Manage tasks in Vikunja - create tasks, view todos, modify tasks, and complete tasks. MUST USE when user mentions Vikunja, "创建任务", "添加待办", "我的任务", "完成任务", "查看待办", "修改任务", or wants to manage todo items in their Vikunja instance.
---

# Vikunja Task Manager

Help users manage their Vikunja tasks. The Python client script at `scripts/vikunja_client.py` handles all API interactions.

## Configuration

Ensure `config.json` exists in the skill directory with:
```json
{
  "base_url": "https://your-vikunja-instance.com/api/v1",
  "username": "your_username",
  "password": "your_password"
}
```

## User Commands & Actions

### 1. View Tasks

**今日及逾期待办（含无截止时间）：**

触发词："查看我的待办", "查看待办", "我的任务", "今日待办", "显示待办", "显示今日待办"

执行：`python3 scripts/vikunja_client.py tasks`（默认 today_or_earlier，包含无截止时间的任务）

**所有待办：**

触发词："所有待办", "显示所有待办", "全部待办", "查看所有待办"

执行：`python3 scripts/vikunja_client.py tasks all`

输出格式：按项目分组，每个任务显示 `[ID] Title (相对时间)`，逾期任务带 ⚠️

### 2. Create Task

**Command patterns:** "创建任务...", "添加待办...", "新建任务..."

**Extract from user input:**
- **Title:** Task content (e.g., "买牛奶")
- **Project:** If specified (e.g., "放在工作项目里"), otherwise default to "收件箱"
- **Due date:** Parse from phrases like:
  - "明天", "后天", "3天后"
  - "下周三", "这周五"
  - "明天下午3点"
  - "12月31日"
- **Description:** Optional additional details

**Action:**
- Parse date using `DateParser`
- Get or create project
- Create task via API
- Confirm creation with task ID

### 3. Complete Task

**触发词：** "完成任务X", "标记X为已完成", "完成XXX", "设置为已完成", "标记为完成"

**支持批量：** 可同时完成多个任务，如 "59 308 342 设置为已完成"

**执行：** `python3 scripts/vikunja_client.py complete <task_id> [task_id2] ... [--show=my|all|none]`

**行为：** 标记待办完成后，自动显示剩余待办（默认显示今日+逾期+无截止时间的待办）

**参数：**
- `--show=my`（默认）：完成后显示剩余待办（今日+逾期+无截止时间）
- `--show=all`：完成后显示所有剩余待办
- `--show=none`：完成后不显示剩余待办

**输出：** 完成状态 + 剩余待办表格

### 4. Modify Task

**Command patterns:** "修改任务X...", "把X改成...", "任务X的截止时间改成..."

**Extract from user input:**
- Task reference (ID or keywords)
- Fields to update: title, description, project, due date

**Action:**
- Locate task by ID or search
- Update specified fields
- Confirm changes

## Output Format

Tasks display with relative time:
- Today/tomorrow/day after tomorrow
- X days ago (with ⚠️ for overdue)
- X days within/after

## Smart Behaviors

**Project selection:**
- User specified → Use that project
- Not specified → Default to "收件箱"
- Content-based (optional): Auto-suggest based on keywords

**Date parsing:**
- Use `DateParser` to convert Chinese date expressions to ISO 8601
- Default time is 09:00 if not specified
- "无截止时间" means no due date

**Error handling:**
- If config missing: Prompt user to set up credentials
- If project not found: Show available projects
- If task not found: Show current task list for reference
