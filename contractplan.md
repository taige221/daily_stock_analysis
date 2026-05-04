# Theme Stock Picker Contract Plan

## 目标

本文件用于对齐 WebUI V1 “主题选股”页面与后端 API 的字段契约，减少前后端并行开发时的反复调整。

适用范围：

- 前端页面：[frontendplan.md](/Users/pengfeihao/code/daily_stock_analysis/frontendplan.md:1)
- 后端聚合接口：[backendplan.md](/Users/pengfeihao/code/daily_stock_analysis/backendplan.md:1)


## 契约原则

### 1. 页面优先

字段命名以页面消费为中心，不直接暴露底层 pipeline 的原始结构。

### 2. 结构稳定优先

V1 优先追加字段，不轻易删除或重命名既有字段。

### 3. 空值可接受

对于实时行情、新闻摘要、板块映射等可能缺失的字段，允许返回：

- `null`
- `[]`
- `""`

不建议因为单个字段缺失使整个响应失败。

### 4. 调试信息次级化

对前端开放的数据应优先面向产品展示，调试类信息应统一放在 `source_info` 或次级字段中。


## 主接口

建议主接口：

- `POST /api/v1/theme-picker/scan`
- `GET /api/v1/theme-picker/status/{task_id}`
- `GET /api/v1/theme-picker/history`
- `POST /api/v1/theme-picker/retry/{task_id}`


## 请求契约

### ThemePickerScanRequest

```json
{
  "theme_id": "deepseek",
  "theme_name": "DeepSeek",
  "board_code": "BK1188",
  "board_name": "DeepSeek概念",
  "strategy_mode": "holding",
  "max_candidates": 8,
  "include_untriggered": false
}
```

### 字段定义

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `theme_id` | `string` | 否 | 注册表中的主题 ID |
| `theme_name` | `string` | 否 | 用户直接输入的主题名称 |
| `board_code` | `string` | 否 | 板块代码，如 `BK1188` / `000858.DC` |
| `board_name` | `string` | 否 | 板块名称，如 `DeepSeek概念` / `AI应用` |
| `strategy_mode` | `string` | 否 | `event` 或 `holding`，默认 `event` |
| `max_candidates` | `integer` | 否 | 最终参与筛选的候选股上限 |
| `include_untriggered` | `boolean` | 否 | 是否保留未触发主题结果 |

### 请求约束

- `theme_id / theme_name / board_code / board_name` 至少一个非空
- `strategy_mode` 仅允许：
  - `event`
  - `holding`
- `max_candidates` 建议范围：
  - `1 ~ 50`


## 提交响应契约

### ThemePickerTaskAccepted

```json
{
  "task_id": "theme_task_xxx",
  "status": "pending",
  "message": "主题选股任务已接受"
}
```

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `task_id` | `string` | 异步任务 ID |
| `status` | `string` | 初始状态，通常为 `pending` |
| `message` | `string` | 提交反馈 |


## 状态查询响应契约

### ThemePickerTaskStatus

```json
{
  "task_id": "theme_task_xxx",
  "status": "completed",
  "progress": 100,
  "message": "主题选股完成",
  "result": {
    "query": {},
    "theme_insight": {},
    "stocks": [],
    "selected_stock": {},
    "source_info": {},
    "empty_reason": null
  }
}
```

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `task_id` | `string` | 异步任务 ID |
| `status` | `string` | `pending / processing / completed / failed` |
| `progress` | `integer` | 进度百分比 |
| `message` | `string \| null` | 当前状态说明 |
| `result` | `ThemePickerScanResponse \| null` | 仅在 `completed` 时返回 |
| `error` | `string \| null` | 仅在 `failed` 时返回 |
| `created_at` | `string` | 创建时间 |
| `started_at` | `string \| null` | 开始时间 |
| `completed_at` | `string \| null` | 完成时间 |


## 历史与重试契约

### ThemePickerTaskHistoryItem

额外约定：

- `can_retry`：前端是否展示“重新筛选”按钮
- 当前仅对 `completed / failed` 返回 `true`

### Retry

`POST /api/v1/theme-picker/retry/{task_id}` 的提交响应结构与 `scan` 相同：

```json
{
  "task_id": "theme_task_retry_xxx",
  "status": "pending",
  "message": "已基于历史任务 xxx 重新加入队列"
}
```


## 最终结果契约

### ThemePickerScanResponse

```json
{
  "query": {},
  "theme_insight": {},
  "stocks": [],
  "selected_stock": {},
  "source_info": {},
  "empty_reason": null
}
```


## query

用于前端回显本次输入。

### ThemePickerQuery

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `theme_id` | `string \| null` | 实际使用的主题 ID |
| `theme_name` | `string \| null` | 实际主题名 |
| `board_code` | `string \| null` | 实际板块代码 |
| `board_name` | `string \| null` | 实际板块名称 |
| `strategy_mode` | `string` | 实际策略模式 |
| `max_candidates` | `integer` | 实际候选上限 |


## theme_insight

对应前端主题理解区。

### ThemeInsight

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `theme_name` | `string` | 当前识别到的主题名称 |
| `event_status` | `string` | `triggered` / `untriggered` / `unresolved` |
| `event_score` | `number \| null` | 事件分数 |
| `matched_keywords` | `string[]` | 命中关键词 |
| `news_count` | `integer` | 命中新闻数 |
| `heat_level` | `string \| null` | `high` / `medium` / `low` |
| `board_mapping_path` | `string \| null` | 板块映射路径说明 |
| `board_candidate_count` | `integer \| null` | 板块成分股数量 |
| `primary_catalyst` | `string \| null` | 主要催化摘要 |

### 字段说明

- `event_status`
  - `triggered`：主题已触发
  - `untriggered`：主题识别到，但未满足触发阈值
  - `unresolved`：板块/主题解析失败或数据异常

- `heat_level`
  - 由新闻数、关键词命中数和事件分数聚合得出
  - V1 允许后端先给简单分级


## stocks

对应前端“优质股票”结果区。

### ThemePickerStockItem

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `rank` | `integer` | 排名 |
| `stock_code` | `string` | 标准股票代码，如 `688629.SH` |
| `stock_name` | `string` | 股票名称 |
| `signal_level` | `string` | 推荐等级 |
| `current_pattern` | `string \| null` | 当前形态摘要 |
| `selection_reason` | `string` | 入选理由 |
| `risk_note` | `string \| null` | 风险提示 |
| `trend_score` | `number \| null` | 趋势分 |
| `pct_chg` | `number \| null` | 当前涨跌幅 |
| `volume_ratio` | `number \| null` | 量比 |
| `turnover_rate` | `number \| null` | 换手率 |
| `buy_signal` | `string \| null` | 技术信号 |
| `data_completeness` | `string \| null` | `full_realtime` / `partial_realtime` / `daily_only` |
| `mini_reasons` | `string[]` | 简短理由数组 |

### signal_level 建议值

- `优先关注`
- `持有候选`
- `低吸观察`
- `主题触发`
- `不宜追高`

V1 中允许后端先基于现有 signal 做映射，不要求底层原始值与页面文案完全一致。


## selected_stock

对应前端右侧详情区。

### ThemePickerSelectedStock

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `stock_code` | `string` | 股票代码 |
| `stock_name` | `string` | 股票名称 |
| `theme_relevance` | `string \| null` | 题材关联度，如 `high/medium/low` |
| `current_price` | `number \| null` | 当前价格 |
| `pct_chg` | `number \| null` | 当前涨跌幅 |
| `volume_ratio` | `number \| null` | 量比 |
| `turnover_rate` | `number \| null` | 换手率 |
| `trend_score` | `number \| null` | 趋势分 |
| `trend_status` | `string \| null` | 趋势状态摘要 |
| `buy_signal` | `string \| null` | 技术信号 |
| `current_pattern` | `string \| null` | 当前形态摘要 |
| `data_completeness` | `string \| null` | `full_realtime / partial_realtime / daily_only` |
| `resonance_count` | `integer \| null` | 同主题共振数量 |
| `ma5` | `number \| null` | 5 日均线 |
| `ma10` | `number \| null` | 10 日均线 |
| `ma20` | `number \| null` | 20 日均线 |
| `bias_ma5` | `number \| null` | 相对 MA5 乖离率 |
| `bias_ma10` | `number \| null` | 相对 MA10 乖离率 |
| `bias_ma20` | `number \| null` | 相对 MA20 乖离率 |
| `recent_strong_days` | `integer \| null` | 最近强势日数量 |
| `support_level` | `number \| null` | 支撑位 |
| `pressure_level` | `number \| null` | 压力位 |
| `news_summary` | `string[]` | 新闻摘要列表 |
| `selected_reasons` | `string[]` | 入选原因列表 |
| `risk_reasons` | `string[]` | 风险原因列表 |
| `data_sources` | `object` | 数据来源 |

### data_sources

```json
{
  "daily": "tushare",
  "realtime": "tencent",
  "board": "tushare_dc",
  "news": "search_service"
}
```

字段均允许为空。


## source_info

对应前端底部“数据来源与说明”区。

### ThemePickerSourceInfo

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `board_source` | `string \| null` | 当前板块主来源 |
| `board_fallback_used` | `boolean` | 是否使用了 fallback |
| `cache_hit` | `boolean \| null` | 是否命中缓存 |
| `source_pills` | `string[]` | 数据源标签 |
| `note` | `string \| null` | 简短说明 |


## empty_reason

当 `stocks=[]` 时可选返回。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `empty_reason` | `string \| null` | 无结果原因 |

示例：

- `未识别到有效主题`
- `板块成分股为空`
- `候选股均未满足当前筛选条件`


## 状态与兼容约定

### 1. 空态

以下字段允许为空：

- `selected_stock`
- `theme_insight.primary_catalyst`
- `stocks[*].pct_chg`
- `stocks[*].volume_ratio`
- `source_info.cache_hit`

### 2. 默认选中股票

若 `stocks` 非空：

- `selected_stock` 默认返回第 1 名股票详情

若 `stocks` 为空：

- `selected_stock = null`

### 3. 字段追加原则

V1 后续若要扩展：

- 优先追加字段
- 不删除现有字段
- 不修改现有字段含义


## 前后端映射建议

### 前端区块与字段对应

| 前端区块 | 对应字段 |
| --- | --- |
| `ThemeSearchPanel` | 请求体字段 |
| `ThemeInsightStrip` | `theme_insight` |
| `StockResultSection` | `stocks` |
| `StockDetailPanel` | `selected_stock` |
| `DataSourceFooter` | `source_info` |


## 后端聚合建议

由 `ThemePickerService` 负责：

1. 将 pipeline 原始 event 转换为 `theme_insight`
2. 将 signal 列表排序并映射为 `stocks`
3. 选出默认详情股票生成 `selected_stock`
4. 汇总板块源、缓存与 fallback 信息生成 `source_info`

不建议在 endpoint 中直接拼装这些结构。


## 下一步

字段契约确定后，后续实现顺序建议：

1. 新增 `api/v1/schemas/theme_picker.py`
2. 按本契约实现 `ThemePickerService`
3. 新增 `POST /api/v1/theme-picker/scan`
4. 新增 `GET /api/v1/theme-picker/themes`
