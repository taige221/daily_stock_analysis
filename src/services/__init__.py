# -*- coding: utf-8 -*-
"""
===================================
服务层模块初始化
===================================

职责：
1. 声明可导出的服务类（延迟导入，避免启动时拉入 LLM 等重依赖）

使用方式：
    直接从子模块导入，例如:
    from src.services.history_service import HistoryService
"""


def __getattr__(name: str):
    """延迟导入：仅在通过 src.services.X 访问时才加载对应子模块。"""
    _lazy_map = {
        "AnalysisService": "src.services.analysis_service",
        "BacktestService": "src.services.backtest_service",
        "HistoryService": "src.services.history_service",
        "StockService": "src.services.stock_service",
        "TaskService": "src.services.task_service",
        "get_task_service": "src.services.task_service",
        "ThemeRegistryService": "src.services.theme_registry_service",
        "ThemeEventScanner": "src.services.theme_event_scanner",
        "ThemeStockPoolService": "src.services.theme_stock_pool_service",
        "ThemeBoardResolverService": "src.services.theme_board_resolver_service",
        "ThemeExpansionService": "src.services.theme_expansion_service",
        "ThemeSignalService": "src.services.theme_signal_service",
        "ThemePickerService": "src.services.theme_picker_service",
        "ThemePickerTaskService": "src.services.theme_picker_task_service",
        "get_theme_picker_task_service": "src.services.theme_picker_task_service",
    }
    if name in _lazy_map:
        import importlib
        module = importlib.import_module(_lazy_map[name])
        return getattr(module, name)
    raise AttributeError(f"module 'src.services' has no attribute {name!r}")


__all__ = [
    "AnalysisService",
    "BacktestService",
    "HistoryService",
    "StockService",
    "TaskService",
    "get_task_service",
    "ThemeRegistryService",
    "ThemeEventScanner",
    "ThemeStockPoolService",
    "ThemeBoardResolverService",
    "ThemeExpansionService",
    "ThemeSignalService",
    "ThemePickerService",
    "ThemePickerTaskService",
    "get_theme_picker_task_service",
]
