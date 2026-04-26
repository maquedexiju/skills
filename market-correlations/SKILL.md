---
name: market-correlations
description: 市场关联关系知识库，使用 SQLite 数据库存储实体和关系。用于：(1) 分析新闻事件影响时查找关联链条；(2) 判断事件对相关资产/行业的传导效应；(3) 管理关联关系数据（增删改查）。触发场景："分析XX事件对市场的影响"、"XX上涨会带动什么"、"添加关联关系"、"查询黄金相关的关联"等。
---

# Market Correlations - 市场关联分析

使用 SQLite 数据库存储市场关联关系，支持实体管理、关系查询和影响链分析。

## 数据库结构

### entities 表（实体）
- id, name, name_en, category, subcategory, type, unit, description
- aliases（别名）, metadata（元数据）

### relations 表（关系）
- primary_id, primary_direction, secondary_id, secondary_direction
- relation_type（positive/negative/mixed/conditional）
- strength（strong/medium/weak）
- logic, mechanism, lag, confidence, source, tags, notes

### categories 表（类别）
- id, name, name_en, parent_id, description

## 脚本位置

```
scripts/
├── init_db.py           # 初始化数据库
├── entity_manager.py    # 实体 CRUD
└── relation_manager.py  # 关系 CRUD + 查询
```

## 实体管理

### 添加实体

```bash
python scripts/entity_manager.py add \
  --id oil-crude \
  --name 原油 \
  --name-en "Crude Oil" \
  --category commodity \
  --subcategory energy \
  --type asset \
  --unit "USD/barrel" \
  --description "石油，能源核心"
```

### 查询实体

```bash
# 按ID查询
python scripts/entity_manager.py get --id gold

# 列出类别下所有实体
python scripts/entity_manager.py list --category commodity

# 搜索实体
python scripts/entity_manager.py search 黄金
```

### 更新实体

```bash
python scripts/entity_manager.py update --id gold --description "避险资产、贵金属、央行储备"
```

### 删除实体

```bash
python scripts/entity_manager.py delete --id gold
# 注意：有关系的实体无法删除，需先删除关系
```

## 关系管理

### 添加关系

```bash
python scripts/relation_manager.py add \
  --primary gold \
  --primary-dir up \
  --secondary silver \
  --secondary-dir up \
  --type positive \
  --logic "同为避险资产，白银波动更大" \
  --strength medium \
  --lag immediate
```

**参数说明：**
- `--primary-dir` / `--secondary-dir`：up / down / stable
- `--type`：positive（正相关）/ negative（负相关）/ mixed（混合）/ conditional（条件性）
- `--strength`：strong / medium / weak
- `--lag`：immediate / short-term / long-term
- `--confidence`：high / medium / low

### 查询关系

```bash
# 按ID查询
python scripts/relation_manager.py get --id rel-gold-silver-xxx

# 查询某实体相关的所有关系
python scripts/relation_manager.py list --entity gold

# 按类型筛选
python scripts/relation_manager.py list --type positive

# 按类别筛选
python scripts/relation_manager.py list --category commodity
```

### 更新关系

```bash
python scripts/relation_manager.py update \
  --id rel-gold-silver-xxx \
  --strength strong \
  --logic "同为避险资产，白银波动更大，工业需求增加波动性"
```

### 删除关系

```bash
python scripts/relation_manager.py delete --id rel-gold-silver-xxx
```

### 查询关联链

```bash
# 查找从某实体出发的多层关联
python scripts/relation_manager.py chain --entity gold --depth 3
```

## 已有数据

### 类别（9个）
- commodity（商品资产）：23个实体
- industry（行业）：32个实体
- macro（宏观经济）：9个实体
- policy（政策）：7个实体
- event（事件）：4个实体
- currency（货币）：3个实体
- index（指数）：2个实体
- asset（资产）：2个实体

### 实体（82个）
包括：黄金、白银、原油、天然气、煤炭、铜、铝、镍、锂、铂金、玉米、小麦、大豆、美元指数、GDP、CPI、PMI、VIX、美联储利率、实际利率、战争、疫情、算力、芯片、数据中心、新能源车、半导体、房地产、物流、银行、军工、火电利润、化工成本、饲料成本等。

### 关系（65条）
- 正相关：53条
- 负相关：12条

**强度分布：**
- 强：34条
- 中：31条

**时间滞后分布：**
- 即时：36条
- 短期：25条
- 长期：4条

## 分析流程

当分析新闻事件时：

1. **识别事件实体**
   ```bash
   python scripts/entity_manager.py search 战争
   ```

2. **查找相关关系**
   ```bash
   python scripts/relation_manager.py list --entity war
   ```

3. **查找影响链**
   ```bash
   python scripts/relation_manager.py chain --entity war --depth 3
   ```

4. **综合分析输出**
   ```
   【事件】战争爆发
   【直接影响】军工↑、能源↑
   【间接影响】物流成本↑（能源传导）→ 制造业承压
   【关联逻辑】...
   【风险提示】...
   ```

## 数据维护

### 初始化数据库

```bash
python scripts/init_db.py
```

### 数据库位置

```
data/market_correlations.db
```

---

_结构化存储，逻辑清晰，数据驱动。_