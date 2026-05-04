# Theme Stock Picker Backend Plan

## 目标

WebUI V1 的后端目标不是暴露一个“回放脚本接口”，而是提供一层面向页面消费的主题选股聚合 API。

核心流程：

1. 接收主题或板块输入
2. 运行主题雷达筛选链路
3. 生成前端可直接渲染的结构化结果
4. 输出主题理解、优质股票列表、单票详情和数据来源说明

V1 后端应尽量复用现有主题雷达能力，不另起一套筛选引擎。


## 设计原则

### 1. 薄 API 封装

后端不直接把 CLI 行为暴露给前端，也不把页面字段拼装写在 endpoint 中。

建议结构：

- `ThemeAlertPipeline` 负责主题扫描与筛选
- `ThemePickerService` 负责聚合为前端页面结构
- `theme_picker` endpoint 只负责参数接收与响应返回

### 2. 结果导向而非调试导向

主接口返回的数据要以页面展示为中心，优先输出：

- 主题理解
- 优质股票结果
- 推荐等级
- 入选理由
- 风险提示

调试字段只保留必要摘要，不直接暴露内部日志流。

### 3. 优先复用现有主题雷达主链路

当前仓库已经具备以下核心能力：

- `ThemeAlertPipeline`
- `ThemeEventScanner`
- `ThemeBoardResolverService`
- `ThemeExpansionService`
- `ThemeSignalService`

V1 后端应基于这些模块构建，不新增平行实现。

### 4. 异步优先

`/theme-picker/scan` 的一次完整筛选可能超过前端 `30s` 超时，因此 V1 需要先走异步任务模式。

V1 交互改为：

1. 前端提交筛选请求
2. 后端返回 `202 + task_id`
3. 前端轮询任务状态
4. 任务完成后返回最终结果

V1 先不引入专门的 SSE 流或长期任务中心，但要保证扫描接口本身不再被请求超时打断。


## 路由设计

建议新增路由前缀：

- `/api/v1/theme-picker`

建议新增 endpoint 文件：

- `api/v1/endpoints/theme_picker.py`

并在：

- `api/v1/router.py`

中挂载该路由。


## API 设计

### 1. POST `/api/v1/theme-picker/scan`

用途：

- 页面点击“开始筛选”时提交一次异步主题选股任务

请求体建议：

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

约束建议：

- `theme_id / theme_name / board_code / board_name` 至少提供一个
- 默认输入优先级：
  - `theme_id`
  - `board_code`
  - `board_name`
  - `theme_name`

响应体建议：

```json
{
  "task_id": "theme_task_xxx",
  "status": "pending",
  "message": "主题选股任务已接受"
}
```

### 2. GET `/api/v1/theme-picker/status/{task_id}`

用途：

- 查询异步任务状态
- 任务完成时返回完整主题选股结果

响应体建议：

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
    "source_info": {}
  }
}
```

### 3. GET `/api/v1/theme-picker/themes`

用途：

- 返回当前注册表中可用主题
- 用于前端主题 chips / 建议输入

直接复用：

- `ThemeRegistryService.list_themes(enabled_only=True)`

### 4. GET `/api/v1/theme-picker/history`

用途：

- 返回最近的主题选股历史
- 供前端“历史记录”入口恢复过去结果

### 5. POST `/api/v1/theme-picker/retry/{task_id}`

用途：

- 基于历史任务的原始请求参数重新提交一次选股任务
- 仅允许重试 `completed / failed` 的历史任务

### 6. 单票详情接口

V1 暂不强制单独拆分。

优先方案：

- 主扫描接口中直接返回默认选中股票详情

后续如需拆分，可增加：

- `GET /api/v1/theme-picker/stocks/{stock_code}`


## 响应结构设计

### 1. query

职责：

- 用于前端回显本次输入参数

建议字段：

- `theme_id`
- `theme_name`
- `board_code`
- `board_name`
- `strategy_mode`
- `max_candidates`

### 2. theme_insight

职责：

- 对应前端主题理解区三张卡片

建议字段：

- `theme_name`
- `event_status`
- `event_score`
- `matched_keywords`
- `news_count`
- `heat_level`
- `board_mapping_path`
- `board_candidate_count`
- `primary_catalyst`

### 3. stocks

职责：

- 对应前端“优质股票”主结果区

每项建议字段：

- `rank`
- `stock_code`
- `stock_name`
- `signal_level`
- `current_pattern`
- `selection_reason`
- `risk_note`
- `trend_score`
- `pct_chg`
- `volume_ratio`
- `turnover_rate`
- `buy_signal`
- `data_completeness`
- `mini_reasons`

### 4. selected_stock

职责：

- 对应前端右侧个股详情区

建议字段：

- `stock_code`
- `stock_name`
- `theme_relevance`
- `trend_score`
- `buy_signal`
- `ma5`
- `ma10`
- `ma20`
- `bias_ma5`
- `bias_ma10`
- `bias_ma20`
- `recent_strong_days`
- `support_level`
- `pressure_level`
- `news_summary`
- `selected_reasons`
- `risk_reasons`
- `data_sources`

### 5. source_info

职责：

- 对应前端底部“数据来源与说明”

建议字段：

- `board_source`
- `board_fallback_used`
- `cache_hit`
- `source_pills`
- `note`


## 内部模块设计

### 1. 新增 service：`ThemePickerService`

建议文件：

- `src/services/theme_picker_service.py`

职责：

- 接收前端请求参数
- 复用 `ThemeAlertPipeline`
- 将原始 `ThemeAlertResultSchema` 转换成 WebUI 所需结构
- 统一排序
- 统一推荐等级文案
- 聚合数据来源说明

不建议在 endpoint 内直接进行复杂字段拼装。

### 2. 复用 `ThemeAlertPipeline`

建议直接复用：

- `src/core/theme_alert_pipeline.py`

由 `ThemePickerService` 来负责：

- 解析前端输入
- 构造或加载主题定义
- 调用 pipeline
- 聚合输出

### 3. 主题构造逻辑

建议从当前 CLI 临时主题构造逻辑中抽公共方法，避免：

- CLI 一套
- API 一套

目标是让：

- `--themes deepseek`
- `--board-code BK1188`
- API `theme_id / board_code / board_name`

都复用同一套主题解析与映射规则。


## 输入解析策略

### 情况 1：传了 `theme_id`

行为：

- 直接从注册表加载主题
- 继承：
  - `concept_board_codes`
  - `concept_board_names`
  - `board_code_mappings`
  - `signal_rules`

### 情况 2：只传了 `board_code`

行为：

- 优先尝试命中现有主题注册表
- 若命中则继承其局部配置
- 若未命中则构造临时主题

### 情况 3：只传了 `board_name`

行为：

- 优先尝试命中已注册主题
- 若没有，则构造临时主题并交给板块解析链路

### 情况 4：只传了 `theme_name`

行为：

- 构造临时主题
- 用名称作为：
  - `theme.name`
  - `keywords`
  - `concept_board_names`


## 处理流程

建议内部处理顺序：

1. 解析请求参数
2. 解析或构造主题定义
3. 调用 `ThemeAlertPipeline.run(...)`
4. 获取 `ThemeAlertResultSchema`
5. 交给 `ThemePickerService` 聚合为页面响应结构
6. 返回 JSON

整体流程：

```text
ThemePickerEndpoint
-> ThemePickerService
-> ThemeAlertPipeline
-> ThemeEventScanner / ThemeBoardResolverService / ThemeExpansionService / ThemeSignalService
-> ThemePickerService 格式化聚合
-> JSON Response
```


## 错误处理策略

### 输入错误

建议返回：

- `400`

场景：

- 主题/板块参数都为空
- `strategy_mode` 非法
- `max_candidates` 越界

### 板块解析失败

建议：

- 返回 `200`
- 但 `theme_insight.event_status` 标记异常状态
- 并在 `source_info.note` 中附带说明

不建议因为单一板块解析失败直接使整个页面请求报错。

### 无候选结果

建议：

- 返回 `200`
- `stocks=[]`
- 返回 `empty_reason`

### 上游数据源异常

建议：

- 返回 `200`
- `source_info.board_fallback_used=true`
- `source_info.note` 写明已切换到 fallback


## Schema 文件建议

建议新增：

- `api/v1/schemas/theme_picker.py`

建议包含：

- `ThemePickerScanRequest`
- `ThemePickerQuerySchema`
- `ThemeInsightSchema`
- `ThemePickerStockItemSchema`
- `ThemePickerSelectedStockSchema`
- `ThemePickerSourceInfoSchema`
- `ThemePickerScanResponse`
- `ThemePickerThemeListItemSchema`


## 与前端页面的对应关系

### ThemeSearchPanel

依赖：

- `POST /theme-picker/scan`
- `GET /theme-picker/themes`

### ThemeInsightStrip

依赖：

- `theme_insight`

### StockResultSection

依赖：

- `stocks`

### StockDetailPanel

依赖：

- `selected_stock`

### DataSourceFooter

依赖：

- `source_info`


## V1 暂不做

- 异步任务队列
- SSE 流式进度
- 历史任务存储
- 结果持久化策略
- 前端专用调试日志接口
- 多用户配置隔离


## 实现顺序

### Phase 1

- 新增 `theme_picker` schemas
- 新增 `theme_picker` endpoint

### Phase 2

- 新增 `ThemePickerService`
- 打通 `POST /scan`

### Phase 3

- 补 `GET /themes`
- 补统一错误结构
- 补排序与默认选中股票逻辑


## 下一步

在正式写后端代码前，建议继续补一份：

1. 前后端字段契约清单

这样在实现 API 和前端页面时，字段命名可以一次对齐，减少反复调整。
