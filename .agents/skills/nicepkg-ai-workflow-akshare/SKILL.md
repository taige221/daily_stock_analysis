---
name: akshare
description: 使用 akshare 获取中国金融市场实时数据和历史数据。当需要查询A股、港股、美股、指数、基金、期货等金融产品的实时行情、历史数据、财务报表时使用该技能。
license: MIT
metadata:
  author: Alice
  version: 1.0.0
  category: finance
  language: python
---

# Akshare 财经数据技能

此技能允许 Alice 使用 akshare 库获取中国金融市场的实时和历史数据，包括股票、指数、基金、期货等各类金融产品。

## 核心功能

- **实时行情 (realtime)**: 获取股票/指数的实时行情数据
- **历史数据 (history)**: 获取股票/指数的历史K线数据
- **指数行情 (index)**: 获取各类指数（上证、深证、创业板等）的行情
- **板块数据 (sector)**: 获取行业板块和概念板块数据
- **财务数据 (financial)**: 获取个股财务指标和报表数据

## 使用方法

### 命令行接口

脚本位置：

```bash
python .agents/skills/nicepkg-ai-workflow-akshare/akshare_tool.py ...
```

支持的查询模式：

- `realtime`: 股票或指数实时行情
- `history`: 股票历史 K 线
- `index-overview`: A 股主要指数概览
- `sector-top`: 热门行业/概念板块排行
- `info`: 个股基本资料
- `financial`: 个股财务指标

#### 1. 查询股票实时行情

```bash
python .agents/skills/nicepkg-ai-workflow-akshare/akshare_tool.py --code 000001
python .agents/skills/nicepkg-ai-workflow-akshare/akshare_tool.py --code 600519
```

#### 2. 查询指数实时行情

```bash
python .agents/skills/nicepkg-ai-workflow-akshare/akshare_tool.py --code 000300 --type index
python .agents/skills/nicepkg-ai-workflow-akshare/akshare_tool.py --code 399006 --type index
```

#### 3. 查询历史 K 线

```bash
python .agents/skills/nicepkg-ai-workflow-akshare/akshare_tool.py --code 000001 --mode history --start 20260101
python .agents/skills/nicepkg-ai-workflow-akshare/akshare_tool.py --code 600519 --mode history --period weekly --start 20250101
```

说明：

- `--period` 支持 `daily` / `weekly` / `monthly`
- `--start` / `--end` 格式为 `YYYYMMDD`

#### 4. 查看 A 股主要指数概览

```bash
python .agents/skills/nicepkg-ai-workflow-akshare/akshare_tool.py --mode index-overview
```

#### 5. 查看热门板块排行

```bash
python .agents/skills/nicepkg-ai-workflow-akshare/akshare_tool.py --mode sector-top
```

说明：

- 该模式内部依赖东方财富板块接口
- 若当前网络、代理或上游接口不稳定，可能出现超时或 `ProxyError`

#### 6. 查询个股基本资料

```bash
python .agents/skills/nicepkg-ai-workflow-akshare/akshare_tool.py --code 000001 --mode info
```

#### 7. 查询财务指标

```bash
python .agents/skills/nicepkg-ai-workflow-akshare/akshare_tool.py --code 000001 --mode financial
```

### 板块相关补充

当前这个 skill 自带的 CLI 没有直接提供“按概念板块名称/代码拉成分股”的命令，但在同一 Python 环境下可以直接调用 `akshare`：

```bash
python -c "import akshare as ak; print(ak.stock_board_concept_info_ths(symbol='DeepSeek概念').head())"
```

已验证：

- `DeepSeek概念` 这种**名称**可用于 `stock_board_concept_info_ths`
- 同花顺概念代码如 `309184`，在当前 `AkShare` 封装下**不能直接作为 `symbol` 传入**
- 同花顺原始详情页 `http://q.10jqka.com.cn/gn/detail/code/<code>/` 在当前网络环境下可能返回 `403 Forbidden`

### 返回结果说明

- CLI 默认输出 Markdown 表格，适合直接贴给用户或写入报告
- 若返回“未找到代码”或“获取数据出错”，优先检查：
  - 股票代码是否正确
  - 当前数据源网络是否可达
  - 是否命中了东方财富/同花顺的上游限制
