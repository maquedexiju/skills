---
name: siyuan
description: 思源笔记知识管理工具集成。用于读取、查询、创建和修改思源笔记中的文档和块。触发场景：(1) 思源笔记、siyuan、笔记管理；(2) "创建周报"、"新建周报"；(3) "同步思源"；(4) "新增感悟"；(5) "处理图片"、"压缩图片"、"网络图片转本地"、"图片本地化"。创建新文档前需阅读 document_tree.txt 确定路径，新建前后会自动执行同步确保云端一致性。
---

# 思源笔记 Skill

用于与思源笔记（Siyuan Note）进行交互，支持读取、查询、创建和修改笔记内容。

**⚠️ 创建新文档前的必须操作**：阅读 `~/.claude/skills/siyuan/document_tree.txt` 了解完整文档结构，根据[文档分类选择策略](#文档分类选择策略重要)选择正确路径。**禁止**仅凭关键词猜测路径。

## 核心概念

### 工作区（Workspace）
思源笔记使用工作区文件夹存储数据，包含：
- `data/` - 笔记本和文档数据
- `assets/` - 资源文件（图片、附件等）
- `snippets/` - 代码片段
- `templates/` - 模板文件
- `widgets/` - 小组件

### 数据层级
```
工作区
└── 笔记本（Notebook）
    └── 文档（Document）- .sy 文件
        └── 块（Block）- 内容单元
```

### 块类型
- `d` - 文档块
- `h` - 标题块（h1-h6）
- `p` - 段落块
- `c` - 代码块
- `t` - 表格块
- `l` - 列表块
- `m` - 数学公式块
- 更多...

### 标识符
- **Notebook ID**: 笔记本的唯一标识
- **Block ID**: 块的唯一标识（22位字母数字）
- **Path**: 文档路径，如 `/foo/bar`
- **HPath**: 人类可读路径，如 `笔记本/文件夹/文档`

## 配置要求

### 1. 启动思源笔记并开启 API

确保思源笔记正在运行，并在 **设置 → 关于** 中启用 API：
- 默认 API 端点：`http://127.0.0.1:6806`
- 获取 API Token（在设置 → 关于中查看）

### 2. 配置文件（推荐）

创建 `config.json` 文件，skill 会按以下顺序查找：
1. `~/.config/siyuan/config.json`
2. `~/.siyuan/config.json`
3. skill 目录下的 `config.json`
4. 当前目录的 `config.json`

配置文件格式：
```json
{
  "api_url": "https://your-siyuan-server:port",
  "token": "your-api-token",
  "default_notebook": "笔记本ID"
}
```

### 3. 环境变量（可选）

环境变量优先级高于配置文件：
```bash
export SIYUAN_API_URL="http://127.0.0.1:6806"
export SIYUAN_TOKEN="your-api-token"
```

## API 端点

所有请求使用 POST 方法，Content-Type: application/json

### 笔记本操作

| 操作 | 端点 | 说明 |
|------|------|------|
| 列出 | `/api/notebook/lsNotebooks` | 获取所有笔记本 |
| 创建 | `/api/notebook/createNotebook` | `{name: "笔记本名"}` |
| 打开 | `/api/notebook/openNotebook` | `{notebook: "id"}` |
| 重命名 | `/api/notebook/renameNotebook` | `{notebook: "id", name: "新名称"}` |

### 文档操作

| 操作 | 端点 | 说明 |
|------|------|------|
| 创建 | `/api/filetree/createDocWithMd` | `{notebook, path, markdown}` |
| 读取 | `/api/export/exportMdContent` | 导出为 Markdown |
| 重命名 | `/api/filetree/renameDocByID` | `{id, title}` |
| 移动 | `/api/filetree/moveDocsByID` | `{fromIDs, toID}` |
| 获取子文档 | `/api/filetree/getIDsByHPath` | `{notebook, path}` |

### 块操作

| 操作 | 端点 | 说明 |
|------|------|------|
| 插入 | `/api/block/insertBlock` | `{dataType, data, nextID/parentID}` |
| 追加 | `/api/block/appendBlock` | `{dataType, data, parentID}` |
| 前置 | `/api/block/prependBlock` | `{dataType, data, parentID}` |
| 更新 | `/api/block/updateBlock` | `{dataType, data, id}` |
| 获取子块 | `/api/block/getChildBlocks` | `{id}` |
| 获取 Kramdown | `/api/block/getBlockKramdown` | `{id}` |

### 查询操作

| 操作 | 端点 | 说明 |
|------|------|------|
| SQL 查询 | `/api/query/sql` | `{stmt: "SQL语句"}` |
| 搜索内容 | 使用 SQL | `SELECT * FROM blocks WHERE content LIKE '%关键词%'` |

## 常用 SQL 查询

```sql
-- 搜索包含关键词的块
SELECT * FROM blocks WHERE content LIKE '%关键词%'

-- 获取文档的所有子块
SELECT * FROM blocks WHERE root_id = '文档ID' ORDER BY sort

-- 获取特定类型的块
SELECT * FROM blocks WHERE type = 'h'  -- 标题
SELECT * FROM blocks WHERE type = 'c'  -- 代码块

-- 获取最近修改的块
SELECT * FROM blocks ORDER BY updated DESC LIMIT 10

-- 获取笔记本列表
SELECT * FROM notebooks

-- 获取文档树
SELECT * FROM blocks WHERE type = 'd' AND box = '笔记本ID'
```

## 使用工作流程

### 1. 阅读笔记

**步骤：**
1. 使用 `/api/notebook/lsNotebooks` 获取笔记本列表
2. 使用 `/api/filetree/getIDsByHPath` 或 SQL 查询找到目标文档
3. 使用 `/api/export/exportMdContent` 导出文档内容为 Markdown

**示例：**
```json
// 获取笔记本列表
POST /api/notebook/lsNotebooks
{}

// 导出文档
POST /api/export/exportMdContent
{"id": "文档块ID"}
```

### 2. 查询笔记

**步骤：**
1. 使用 SQL 查询搜索内容
2. 可选：先列出笔记本缩小范围

**示例：**
```json
// SQL 搜索
POST /api/query/sql
{"stmt": "SELECT id, content, path FROM blocks WHERE content LIKE '%项目计划%'"}
```

### 3. 新建笔记

**⚠️ 重要：新建文档前后必须执行同步！**

**步骤：**
1. **【同步前】执行同步，确保云端最新状态**
   ```bash
   python ~/.openclaw/workspace/skills/siyuan/scripts/sync.py
   ```
2. **阅读 `document_tree.txt` 了解现有结构，根据分类策略确定最佳路径**
3. 确定目标笔记本（如不存在可先创建）
4. 使用 `/api/filetree/createDocWithMd` 创建文档
5. **【同步后】执行同步，确保新文档上传到云端**
   ```bash
   python ~/.openclaw/workspace/skills/siyuan/scripts/sync.py
   ```

**示例：**
```bash
# 1. 同步前
python ~/.openclaw/workspace/skills/siyuan/scripts/sync.py

# 2. 阅读文档树确定路径
cat ~/.openclaw/workspace/skills/siyuan/document_tree.txt
```

```json
// 3. 创建新文档
POST /api/filetree/createDocWithMd
{
  "notebook": "笔记本ID",
  "path": "/读书笔记/如何阅读一本书",
  "markdown": "# 如何阅读一本书\n\n这是一本关于阅读方法论的经典著作..."
}

// 在文档中追加块
POST /api/block/appendBlock
{
  "dataType": "markdown",
  "data": "## 第一章 阅读的层次\n\n阅读分为四个层次...",
  "parentID": "文档块ID"
}
```

```bash
# 4. 同步后
python ~/.openclaw/workspace/skills/siyuan/scripts/sync.py
```

### 4. 修改笔记

**步骤：**
1. 先查询获取目标块的 ID
2. 使用 `/api/block/updateBlock` 更新内容
3. 或使用 `/api/attr/setBlockAttrs` 设置属性

**示例：**
```json
// 更新块内容
POST /api/block/updateBlock
{
  "dataType": "markdown",
  "data": "更新后的内容",
  "id": "块ID"
}

// 设置块属性
POST /api/attr/setBlockAttrs
{
  "id": "块ID",
  "attrs": {
    "custom-tags": "重要,待办"
  }
}
```

## 请求头

所有请求需要包含：

```
Content-Type: application/json
Authorization: Token {your-api-token}
```

## 响应格式

```json
{
  "code": 0,      // 0 表示成功，非零表示错误
  "msg": "",      // 错误消息（成功时为空）
  "data": {}      // 响应数据
}
```

## 注意事项

1. **Block ID**: 思源笔记使用 22 位的唯一标识符，查询时需获取正确的 ID
2. **Markdown 格式**: 创建和更新时使用标准 Markdown 语法
3. **Kramdown**: 思源内部使用 Kramdown 格式（Markdown 的超集）
4. **父子关系**: 使用 `parentID`、`previousID`、`nextID` 控制块的位置
5. **笔记本必须打开**: 某些操作需要笔记本处于打开状态
6. **路径格式**: 使用 `/` 作为分隔符，如 `/folder/document`

## 文档树功能

提供了一个独立的脚本来获取和缓存文档树结构，方便在创建文档时决定放置位置。

### 使用脚本获取文档树

```bash
# 基本用法 - 获取文档树并保存
python scripts/get_document_tree.py

# 打印格式化的树结构
python scripts/get_document_tree.py --pretty

# 为新文档获取路径建议
python scripts/get_document_tree.py --suggest "项目计划书"
```

### 输出文件

运行后会生成以下文件：

| 文件 | 说明 |
|------|------|
| `document_tree.json` | 完整的层级树结构（JSON） |
| `document_tree.txt` | **文本格式的树状目录（推荐 AI 阅读）** |
| `document_index.json` | 扁平索引，便于快速查找 |

### 文档分类选择策略（重要）

**⚠️ 前置要求**：在使用本策略之前，**必须先阅读 `document_tree.txt`** 获取当前完整的文档树结构。

```bash
# 确保文档树已更新
python ~/.claude/skills/siyuan/scripts/get_document_tree.py

# 阅读文档树（必须执行）
cat ~/.claude/skills/siyuan/document_tree.txt
```

当需要创建新文档时，**必须遵循以下决策流程**：

#### 步骤 1：确定内容领域（顶层分类）

| 内容类型 | 目标顶层目录 | 示例 |
|---------|------------|------|
| 编程代码、技术栈、开发工具 | **程序与编程** | Python, Linux, Shell |
| 产品方法论、工作流程、职场技能 | **工作/产品工具书** | 需求分析, 项目管理 |
| AI、机器学习、深度学习 | **人工智能** 或 **人工智能 AI** | Prompt, PyTorch |
| 读书、国学、生活技能 | **生活知识** | 摄影, 易经, 健身 |
| 日常记录、日记、随想 | **生活记录** | 日记, 周记 |
| 财经、投资、理财 | **金融与经济** | 股票, 基金 |
| 写作、创作、表达 | **写手梦** | 故事, 随笔 |
| 图书管理、阅读清单 | **图书库** | 书单, 读书笔记 |
| 新闻、时事、行业动态 | **新闻** | 科技新闻, 行业资讯 |

#### 步骤 2：确定技术栈/子领域（二级分类）

在 **程序与编程** 下：
- Linux/Mac 系统相关 → **Linux & Mac**
- Python → **Python**
- 前端技术 → **HTML CSS JS**
- Swift/Apple 开发 → **Swift**
- Shell 脚本 → **Shell**
- 数据库 → **SQL**

#### 步骤 3：确定内容类型（三级分类）

在 **Linux & Mac** 下：
- 系统服务安装配置 → **服务安装、使用/系统基础服务**
- 系统设置管理 → **系统设置、管理**
- 编译构建 → **编译**
- 库依赖 → **一些库**
- 知识概念 → **一些知识**

#### 常见错误示例

❌ **错误**：Xvfb 使用指南 → `工作/周边知识/工具使用/`  
✅ **正确**：Xvfb 使用指南 → `程序与编程/Linux & Mac/服务安装、使用/系统基础服务/`

**原因**：Xvfb 是 Linux 系统基础服务，不是通用的办公效率工具。

#### 快速决策清单

创建文档前问自己：
1. **这是什么领域的内容？**（技术/工作/生活/AI/财经）
2. **涉及什么技术栈？**（Linux/Python/AI 等）
3. **内容类型是什么？**（教程/配置/笔记/代码）
4. **查看 `document_tree.txt` 找到最匹配的位置**

### 在 AI 对话中使用文档树

**重要前提**：当用户想要创建新文档时，**必须先执行以下步骤**，不可跳过：

```bash
# 1. 更新文档树缓存
python ~/.claude/skills/siyuan/scripts/get_document_tree.py

# 2. 阅读 document_tree.txt 了解完整结构（必须使用文本格式）
cat ~/.claude/skills/siyuan/document_tree.txt

# 3. 根据上述分类策略确定最佳位置
# 4. 创建文档到正确路径
```

**为什么必须使用 document_tree.txt？**
- JSON 格式（document_tree.json）需要代码解析，不便于直接阅读层级关系
- 文本格式（document_tree.txt）以树状结构展示，AI 可以直接理解文档层级
- 通过阅读文本格式，可以快速定位到最具体的子分类

**禁止行为**：
- ❌ 不阅读文档树就猜测路径
- ❌ 仅凭关键词匹配确定位置（如看到"工具"就放到"工具使用"）
- ❌ 使用 SQL 查询代替阅读完整文档树

---

## 同步功能

### 执行同步

**触发**：用户要求"同步思源"、"强制同步"、"执行同步"

思源提供以下同步 API：

| API | 说明 |
|------|------|
| `/api/sync/performSync` | **执行同步**（强制同步） |
| `/api/sync/getSyncInfo` | 获取同步状态信息 |
| `/api/sync/setSyncEnable` | 设置同步开关 |

**API 调用**：
```bash
curl -X POST "$API/api/sync/performSync" \
  -H "Authorization: Token $TOKEN" \
  -d '{}'
```

**返回**：
```json
{"code": 0, "msg": "", "data": null}  // 成功
```

**获取同步状态**：
```bash
curl -X POST "$API/api/sync/getSyncInfo" \
  -H "Authorization: Token $TOKEN" \
  -d '{}'
```

**返回示例**：
```json
{
  "code": 0,
  "data": {
    "kernel": "zndajwo",
    "stat": "上传/下载文件数 0/1, 发送/接收字节数 0 B/304.78 kB",
    "synced": 1776177772596  // 最后同步时间戳
  }
}
```

**使用脚本**：
```bash
python scripts/sync.py          # 执行同步
python scripts/sync.py --info   # 获取同步状态
```

---

## 周报功能

### 创建每周周报

**触发**：用户要求"创建周报"、"新建周报"、"本周周报"

**功能**：
1. 计算本周日期范围（周一到周日）
2. 创建周报文档，包含预设模板
3. 文档路径：`/生活记录/{年份}/{年份} 年第 {周数} 周`

**周报模板结构**：
```markdown
MM.DD - MM.DD  # 日期范围标题

## 大事件（做了什么）
- 【技能提升】你长进了吗？
- 做了什么

## 琐事
{{{col  # 三栏布局
家人 | 烹饪 | 生活状态
}}}

## 目标
{{{col  # 三栏布局
工作 | 成长&运动 | 其他
}}}

## 记录
{{{col  # 周一到周日的状态卡片
}}}

## 本周感悟
```

**使用脚本**：
```bash
# 本周周报
python scripts/create_weekly_report.py

# 上周周报（参数 -1）
python scripts/create_weekly_report.py -1

# 下周周报（参数 1）
python scripts/create_weekly_report.py 1
```

**配置**：
- 笔记本 ID：`20230227175506-lr8im3j`
- API Token：从 config.json 获取或脚本内置

**API 调用**：
```bash
curl -X POST "$API/api/filetree/createDocWithMd" \
  -H "Authorization: Token $TOKEN" \
  -d '{
    "notebook": "20230227175506-lr8im3j",
    "path": "/生活记录/2026/2026 年第 15 周",
    "markdown": "周报内容..."
  }'
```


### 新增本周感悟

**触发**：用户要求"新增感悟"、"添加感悟"、"本周感悟"

**功能**：在当周周报的"本周感悟"章节添加一条感悟记录。

**流程**：
1. 计算当前年份和周数
2. SQL 查询定位"本周感悟"标题块
3. 获取子块，找到最后一个位置
4. 用 `insertBlock` API 在末尾插入新感悟
5. 触发同步

**感悟格式**：
```markdown
{{{col
### 2026.04.14 感悟内容
}}}}
{: style="background-color: rgba(144, 144, 144, 0.1); border-radius: 10px;..." memo="生活感悟"}
```

**使用脚本**：
```bash
# 单行感悟（仅标题）
python scripts/add_reflection.py "今天学到了新知识"

# 多行感悟（标题 + 正文，用空行分隔）
python scripts/add_reflection.py "标题

正文内容"

# 包含列表的感悟
python scripts/add_reflection.py "标题

1. 第一点
2. 第二点
3. 第三点"

# 不触发同步
python scripts/add_reflection.py "感悟内容" --no-sync
```

**换行说明**：
- 脚本会自动将字面 `\n` 转换为真正的换行符
- Shell 命令中传入 `"标题\n\n正文"` 或直接使用真正的换行均可
- 标题与正文之间需要**空行**（即 `\n\n`）分隔

---


---

## 图片处理功能

**触发**：用户要求"处理图片"、"压缩图片"、"网络图片转本地"、"图片本地化"

**功能**：统一处理笔记中的图片，支持两种操作：

1. **网络图片本地化**：将 http/https 链接的图片下载并上传到思源本地
2. **图片压缩**：压缩思源本地图片，减小体积

可单独执行，也可组合执行（先迁移网络图片，再压缩所有图片）。

### 支持格式

- **Markdown 图片**：`![alt](https://example.com/image.png)` 或 `![alt](assets/xxx.webp)`
- **HTML 图片**：`<img src="https://...">` 或 `<img src="assets/...">`

### 使用方式

```bash
# 处理文档中所有图片（先迁移网络图片，再压缩本地图片）
python scripts/process_images.py --doc "文档ID或标题"

# 仅迁移网络图片
python scripts/process_images.py --doc "文档ID" --migrate

# 仅压缩本地图片
python scripts/process_images.py --doc "文档ID" --compress

# 仅检测，不实际处理
python scripts/process_images.py --doc "文档ID" --dry-run

# 处理单个网络图片
python scripts/process_images.py --url "https://example.com/image.png"

# 处理单个本地图片（压缩）
python scripts/process_images.py --asset "assets/xxx.webp"
```

### 压缩逻辑

- 短边小于 360px：不压缩
- 短边大于 720px：缩放到短边 720px（最多压缩到 1/3）
- 输出格式：WebP（高质量压缩）
- 压缩比例 < 1%：跳过

### 示例输出

```
Processing document: 20260413104438-gf63hee
Found 37 blocks
Found 3 network images, 5 local images

  Processing network image: https://example.com/image1.png
    Downloaded: 156.2KB
    New path: /assets/migrated_imgs/image1.webp

  Processing local image: assets/screenshot.webp
    Original: 250.5KB
    Short side: 1379px
    Compressed: 73.0%, Final: 67.5KB
    New path: /assets/migrated_imgs/screenshot.webp

==================================================
Summary:
  Network images: 3
  Migrated: 3
  Local images: 5
  Compressed: 3
  Bytes saved: 412.5KB (0.41MB)
  Blocks updated: 5
```

### 注意事项

1. 网络图片需要能正常访问（部分网站可能需要登录）
2. 上传后图片保存在 `/assets/migrated_imgs/` 目录
3. 大图片下载可能需要较长时间（默认超时 10 秒）
4. 处理失败的图片会跳过，继续处理其他图片
5. 默认执行全部操作（迁移 + 压缩），可用 --migrate 或 --compress 单独执行

---

## 示例任务

### 列出所有笔记本
```bash
curl -X POST http://127.0.0.1:6806/api/notebook/lsNotebooks \
  -H "Content-Type: application/json" \
  -H "Authorization: Token xxx" \
  -d '{}'
```

### 搜索包含"会议"的块
```bash
curl -X POST http://127.0.0.1:6806/api/query/sql \
  -H "Content-Type: application/json" \
  -H "Authorization: Token xxx" \
  -d '{"stmt": "SELECT id, content, box FROM blocks WHERE content LIKE '%会议%' LIMIT 20"}'
```

### 创建新文档
```bash
curl -X POST http://127.0.0.1:6806/api/filetree/createDocWithMd \
  -H "Content-Type: application/json" \
  -H "Authorization: Token xxx" \
  -d '{
    "notebook": "20210808180117-c6z4yyn",
    "path": "/日记/2024-01-15",
    "markdown": "# 2024年1月15日\n\n今天的工作内容..."
  }'
```
