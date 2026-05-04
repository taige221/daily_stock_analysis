# Theme Stock Picker Frontend Plan

## 目标

WebUI V1 的目标不是做“主题回放实验台”，而是做一个面向选股结果的页面：

1. 输入主题
2. 结合板块与新闻理解主题
3. 输出优质股票候选
4. 解释每只股票为什么入选

页面定位应是：

- `主题选股`
- 副标题：`通过主题、板块与新闻筛选优质股票`


## V1 设计原则

### 1. 结果优先，不以调试为中心

主区域优先展示：

- 优质股票列表
- 推荐等级
- 入选理由
- 风险提示

调试信息只保留在次级区域，不作为页面主视觉。

### 2. 主题理解要可解释

在结果出现之前，页面需要先回答三件事：

- 系统识别到了什么主题
- 主题映射到了哪个板块
- 当前主题的新闻催化强不强

### 3. 与现有 CLI 能力对齐

V1 只承接当前已存在的能力：

- 主题 ID
- 板块代码
- 板块名称
- `event / holding` 两种策略模式
- 候选数量上限

不在 V1 内新增复杂配置编辑、历史任务中心或大规模管理能力。


## 页面定位

页面名称建议：

- `ThemeStockPickerPage`

路由建议：

- `/theme-picker`


## 现有 Web 结构研判

基于当前 `apps/dsa-web/` 代码结构，现有一级路由均挂在 `Shell` 下：

- `/`：首页
- `/chat`：问股
- `/portfolio`：持仓
- `/backtest`：回测
- `/settings`：设置

当前主导航也对应这 5 个一级入口，因此 `主题选股` 最合适的接入方式是：

- 作为新的一级路由：`/theme-picker`
- 作为新的一级导航项：`主题选股`

不建议：

- 挂在首页内部作为二级区域长期承载
- 放进设置页或回测页下
- 做成隐藏工具页

原因：

- 它的业务语义和首页单票分析、问股、持仓、回测同级
- 它是一个独立的筛选工作流，而不是某个现有页面的附属面板
- 当前 `Shell + SidebarNav + Route` 结构已经天然适合再加一个一级入口


## 页面信息结构

### 1. 顶部输入区

用途：发起一次主题选股。

字段：

- `主题名称`
- `板块代码`
- `板块名称`
- `策略模式`
- `候选上限`
- 推荐主题 Chips
- `开始筛选` 按钮

输入优先级建议：

- `主题名称`
- `板块代码`
- `板块名称`

若多项同时填写，默认优先级：

- `主题名称 > 板块代码 > 板块名称`

### 2. 主题理解区

用途：展示系统对输入主题的理解结果。

包含三张卡片：

- `ThemeRecognitionCard`
  - 识别主题
  - 命中关键词
- `BoardMappingCard`
  - 板块映射路径
  - 板块成分股数量
- `NewsHeatCard`
  - 新闻条数
  - 热度等级
  - 主要催化摘要

### 3. 优质股票结果区

用途：作为页面主区域，输出最终候选股票。

优先展示：

- 股票名称 / 代码
- 推荐等级
- 当前形态
- 入选理由
- 风险提示

支持：

- 默认按推荐等级排序
- 可切换按涨跌幅 / 趋势分排序
- 点击某只股票后展开详情

### 4. 个股详情区

用途：解释“为什么是这只票”。

应包含：

- 题材关联度
- 技术结构
- 新闻摘要
- 关键位置
- 风险提示
- 为什么入选

### 5. 数据来源与说明区

用途：补充说明数据源与 fallback 情况。

展示：

- 当前使用的数据源标签
- 是否命中缓存
- 是否自动切换 fallback
- 简短说明文案

此区域默认弱化展示，不应呈现成开发调试控制台。


## 组件树

```text
ThemeStockPickerPage
├─ PageHeader
│  ├─ ProductTitle
│  └─ ProductSubtitle
├─ ThemeSearchPanel
│  ├─ ThemeInput
│  ├─ BoardCodeInput
│  ├─ BoardNameInput
│  ├─ StrategyModeSelect
│  ├─ CandidateLimitInput
│  ├─ SuggestionChips
│  └─ RunScanButton
├─ ThemeInsightStrip
│  ├─ ThemeRecognitionCard
│  ├─ BoardMappingCard
│  └─ NewsHeatCard
├─ MainContent
│  ├─ StockResultSection
│  │  ├─ SectionHeader
│  │  ├─ StockResultToolbar
│  │  └─ StockResultTable
│  │     └─ StockResultRow*
│  └─ StockDetailPanel
│     ├─ StockHeader
│     ├─ ThemeRelationCard
│     ├─ TechnicalStructureCard
│     ├─ NewsSummaryCard
│     ├─ KeyLevelsCard
│     └─ WhySelectedCard
└─ DataSourceFooter
   ├─ SourcePills
   └─ SourceExplanation
```


## 区块职责

### PageHeader

职责：

- 明确页面定位
- 提供统一标题和副标题

文案建议：

- 标题：`主题选股`
- 副标题：`通过主题、板块与新闻筛选优质股票`

### ThemeSearchPanel

职责：

- 作为页面唯一主操作区
- 承载主题输入和筛选动作

交互建议：

- `开始筛选` 为主按钮
- 推荐主题 Chips 支持一键填充

### ThemeInsightStrip

职责：

- 在结果展示前，先解释系统识别到的主题上下文

输出内容必须尽量简短，可视化优先。

### StockResultSection

职责：

- 页面主视觉中心
- 展示经过主题、板块、新闻和技术筛选后的优质股票

### StockResultRow

建议字段：

- 排名
- 股票名称
- 股票代码
- 推荐等级 Badge
- 当前形态
- 入选理由
- 风险提示
- 小型趋势图

### StockDetailPanel

职责：

- 为用户提供“解释性信息”
- 帮助用户判断是否继续跟踪这只股票

建议拆分为卡片：

- `ThemeRelationCard`
- `TechnicalStructureCard`
- `NewsSummaryCard`
- `KeyLevelsCard`
- `WhySelectedCard`

### DataSourceFooter

职责：

- 补充说明数据源使用情况
- 说明是否命中缓存和 fallback

V1 不做复杂日志面板，只保留摘要化说明。


## 页面状态

建议统一支持：

- `idle`
- `loading`
- `success`
- `empty`
- `error`


## 推荐展示字段

### 结果列表字段

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
- `data_completeness`

### 详情区字段

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


## 布局建议

### 顶部

- 页面标题
- 输入区

### 中部

- 左：优质股票结果
- 右：个股详情

### 次级信息区

- 主题理解卡片
- 数据来源与说明

布局重点：

- 左侧看结果
- 右侧看原因
- 上方负责输入
- 下方负责补充说明


## 入口设计

### V1 主入口

建议将该功能整合到当前 `apps/dsa-web/` 中，并作为正式页面提供入口：

- 页面路由：`/theme-picker`
- 导航名称：`主题选股`

原因：

- 这是当前系统的新增能力，不是独立产品
- 与现有数据源、分析链路、认证和页面框架共用
- 适合先以一个独立页面的形式渐进上线

### 增强入口

除主导航外，V1 可预留以下增强入口：

- 首页快捷入口
  - 文案建议：`按主题筛选优质股票`
- 板块/新闻/市场复盘页联动入口
  - 支持带入：
    - 主题名称
    - 板块代码
    - 策略模式

V1 不要求全部实现，但在页面设计和路由参数上应预留兼容能力。


## 出口设计

### 页面内出口

V1 至少应支持以下页面内出口：

1. 股票结果行点击
   - 打开右侧个股详情区

2. 详情区底部动作
   - `查看个股详情`
   - `加入观察池`

### 业务闭环出口

该页面的结果不应停留在“看完就结束”，建议与现有业务链路对接：

- 跳转到现有个股详情/分析页
- 将候选股加入观察池或自选池
- 从结果页发起单股深度分析

V1 最小闭环建议：

- 导航进入 `主题选股`
- 得到候选股结果
- 点击查看详情
- 将股票加入观察池或跳转个股详情页


## 导航放置建议

### V1 建议

在当前 Web 主导航中新增一级入口：

- `主题选股`

建议放置顺序：

- `首页`
- `主题选股`
- `问股`
- `持仓`
- `回测`
- `设置`

排序理由：

- `首页` 仍然是通用默认入口
- `主题选股` 与首页单票分析同属“发现 / 筛选”链路，应放在偏前位置
- `问股` 更像对已选股票的跟进动作，应位于主题筛选之后
- `持仓 / 回测 / 设置` 仍保留为后续管理和系统功能

不建议：

- 作为隐藏工具页
- 只放在实验区或调试菜单中
- 新开独立 Web 项目

### 后续可扩展方向

若该能力后续稳定并形成常用路径，可继续扩展：

- 首页常用功能卡片
- 市场复盘页内联推荐入口
- 板块页 / 新闻页一键跳转到主题选股


## V1 暂不做

- 主题配置管理页
- 历史任务中心
- 全量回放记录页
- 多用户配置系统
- 复杂图表分析中心
- 前端内置调试控制台


## 实现优先级

### Phase 1

- 页面骨架
- 输入区
- 结果列表假数据布局
- 详情区假数据布局

### Phase 2

- 接入主题筛选接口
- 打通输入区到结果列表
- 接入详情区动态切换

### Phase 3

- 补 Theme Insight Strip
- 补 Data Source Footer
- 补空态、失败态、加载态


## 下一步

前端实现前，建议继续补两份配套设计：

1. API 契约
2. 组件 props 设计

这样可以避免页面先搭起来后，字段结构反复调整。
