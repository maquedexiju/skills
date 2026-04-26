---
name: memos
description: Interact with Memos - a self-hosted note-taking app. Use when user wants to (1) Create a new memo/note, (2) List or search memos, (3) Get or update existing memos, (4) Quick capture ideas to Memos. Requires config.json setup.
---

# Memos

Interact with a self-hosted Memos instance via its REST API.

## Setup

Edit `config.json` in the skill folder:
```json
{
  "url": "https://your-memos-instance.com",
  "token": "your-access-token"
}
```

Get token from Memos: Settings > Access Tokens > Create new token

## Quick Start

Create a memo:
```bash
python ~/.openclaw/workspace/skills/memos/scripts/memos.py create "Your memo content"
```

## Commands

### Create

```bash
memos.py create <content> [--visibility PRIVATE|PROTECTED|PUBLIC] [--pinned]
```

默认 visibility 为 PROTECTED（工作区可见）。

**注意：**
1. 一条消息中的所有内容应建在一个 memo 里，不要拆分成多条。即使有多点内容，也保持在同一条 memo 中。
2. **严格保留用户输入的原始格式**，包括编号（1. 2. 3.）、换行、空格、缩进等，不做任何格式修改。

### List

```bash
memos.py list [--limit <n>] [--filter <expr>]
```

### Get

```bash
memos.py get <memo_id>
```

### Delete

```bash
memos.py delete <memo_id>
```

## Script

See `scripts/memos.py` for the CLI tool.