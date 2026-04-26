---
name: freshrss-filter
description: Filter FreshRSS unread RSS entries. MUST USE when user mentions RSS filtering, FreshRSS, "filter my RSS", "清理 RSS", "RSS 太多了", or wants to clean up/mark read RSS items. Automatically filters PT sites (TTG/M-Team/TCCF) and uses AI to judge remaining entries. Executes full workflow without user confirmation.
compatibility:
  - python3
  - requests library
  - FreshRSS with Google Reader API enabled
---

# FreshRSS Filter

获取 FreshRSS 未读条目，本地黑名单过滤后，由 AI 判断并自动标记已读。

## 触发方式（必须）

当用户说以下话时**必须**触发此 skill：
- "过滤我的 RSS"
- "freshrss filter"
- "清理 RSS 未读"
- "帮我看看 RSS"
- "RSS 太多了"
- "标记 RSS 已读"
- "运行 freshrss-filter"

## 工作流程（全自动）

### Step 1: 获取数据并本地过滤

执行：
```bash
python3 ~/.openclaw/workspace/skills/freshrss-filter/freshrss_tool.py fetch
```

本地自动过滤并标记：
- **Feed 黑名单**: `ttg`, `tccf`, `m-team` 等 PT 站 → 自动标记已读
- **作者黑名单**: 特定作者 → 自动标记已读
- **内容黑名单**: 正则匹配的内容 → 自动标记已读

输出包含：
- `log_file`: 日志文件路径（后续 mark 需使用）
- `stats`: 过滤统计
- `candidates`: 剩余候选条目（供 AI 判断）

### Step 2: AI 判断候选条目

根据 `prompt.md` 过滤标准，直接判断候选条目：

**过滤**（标记已读）：
- 八卦/闲聊：个人情感、婚姻、生育话题
- 无信息量：水贴、纯主观感受
- 个人记录：游记、旅游分享
- 纯引流广告（无实质信息）

**保留**（不标记）：
- 职场经验、求职、工作相关
- 技术问题、编程、工具使用
- 软件/开源项目推荐
- 实用信息、政策解读
- 招聘信息
- **服务供应商信息**（AI中转、ChatGPT订阅、机场等）

### Step 3: 执行 AI 过滤标记

直接执行，无需用户确认：
```bash
python3 ~/.openclaw/workspace/skills/freshrss-filter/freshrss_tool.py mark \
  --ids "id1,id2,id3" \
  --log-file "<fetch返回的log_file路径>" \
  --details '[{"title":"标题1","reason":"原因1"},{"title":"标题2","reason":"原因2"}]'
```

### Step 4: 输出结果

输出简洁汇总：
- 黑名单过滤数量
- AI 过滤数量 + 主要原因
- 剩余未读数量
- 日志文件路径

## 配置文件

- `~/.openclaw/workspace/skills/freshrss-filter/config.json` - FreshRSS 连接配置
- `~/.openclaw/workspace/skills/freshrss-filter/feed_blacklist.txt` - 来源正则黑名单
- `~/.openclaw/workspace/skills/freshrss-filter/author_blacklist.txt` - 作者正则黑名单  
- `~/.openclaw/workspace/skills/freshrss-filter/content_blacklist.txt` - 内容正则黑名单
- `~/.openclaw/workspace/skills/freshrss-filter/prompt.md` - 详细过滤标准
- `~/.openclaw/workspace/skills/freshrss-filter/logs/filter_YYYYMMDD_HHMMSS.log` - 操作日志

## 示例

**用户**: 过滤我的 RSS

**Claude**: 
```bash
# Step 1: fetch
python3 ~/.openclaw/workspace/skills/freshrss-filter/freshrss_tool.py fetch
```

[分析候选条目...]

```bash
# Step 3: mark（直接执行）
python3 ~/.openclaw/workspace/skills/freshrss-filter/freshrss_tool.py mark \
  --ids "id1,id2,id3" \
  --log-file "/path/to/filter_xxx.log" \
  --details '[{"title":"生小孩的意义","reason":"个人情感故事"},{"title":"日本游记","reason":"游记"}]'
```

✅ **过滤完成**
- 黑名单自动过滤: 54 条 (TTG/M-Team/TCCF)
- AI 过滤: 12 条 (个人情感 5条、游记 3条、闲聊 4条)
- 剩余未读: 152 条
- 日志: `logs/filter_20260413_xxx.log`