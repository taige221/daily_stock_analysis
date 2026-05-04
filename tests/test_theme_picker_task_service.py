# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import tempfile
import time
from datetime import datetime, timedelta

from api.v1.schemas.theme_picker import ThemePickerScanRequest
from src.config import Config
from src.storage import DatabaseManager
from src.services.theme_picker_task_service import (
    ThemePickerTaskStatus,
    ThemePickerTaskService,
    get_theme_picker_task_service,
)


def setup_function():
    ThemePickerTaskService.reset_instance()
    DatabaseManager.reset_instance()
    Config._instance = None


def teardown_function():
    ThemePickerTaskService.reset_instance()
    DatabaseManager.reset_instance()
    Config._instance = None


def _configure_temp_db(temp_dir: tempfile.TemporaryDirectory) -> None:
    os.environ["DATABASE_PATH"] = os.path.join(temp_dir.name, "theme_picker_task_history.db")
    os.environ["THEME_PICKER_TASK_HISTORY_RETENTION_DAYS"] = "30"
    os.environ["THEME_PICKER_TASK_HISTORY_CLEANUP_BATCH_SIZE"] = "200"
    Config._instance = None
    DatabaseManager.reset_instance()
    ThemePickerTaskService.reset_instance()


def test_theme_picker_task_service_completes_with_result(monkeypatch):
    from src.services.theme_picker_service import ThemePickerService

    with tempfile.TemporaryDirectory() as temp_dir:
        _configure_temp_db(temp_dir)
        service = get_theme_picker_task_service()

        def fake_scan(self, request):
            return {
                "query": {
                    "theme_id": request.theme_id,
                    "theme_name": request.theme_name or "DeepSeek",
                    "board_code": request.board_code,
                    "board_name": request.board_name,
                    "strategy_mode": request.strategy_mode,
                    "max_candidates": request.max_candidates,
                },
                "theme_insight": {
                    "theme_name": "DeepSeek",
                    "event_status": "triggered",
                    "event_score": 100,
                    "matched_keywords": ["DeepSeek"],
                    "news_count": 2,
                    "heat_level": "high",
                    "board_mapping_path": "BK1188 -> 000771.DC -> tushare",
                    "board_candidate_count": 3,
                    "primary_catalyst": "模型发布",
                },
                "stocks": [],
                "selected_stock": None,
                "source_info": {
                    "board_source": "tushare_dc",
                    "board_fallback_used": True,
                    "cache_hit": False,
                    "source_pills": ["tushare"],
                    "note": "ok",
                },
                "empty_reason": "暂无结果",
            }

        monkeypatch.setattr(ThemePickerService, "scan", fake_scan)

        task = service.submit_scan(
            ThemePickerScanRequest(
                board_code="BK1188",
                strategy_mode="holding",
                max_candidates=8,
            )
        )

        deadline = time.time() + 3
        latest = None
        while time.time() < deadline:
            latest = service.get_task(task.task_id)
            if latest and latest.status == ThemePickerTaskStatus.COMPLETED:
                break
            time.sleep(0.05)

        assert latest is not None
        assert latest.status == ThemePickerTaskStatus.COMPLETED
        assert latest.result is not None
        assert latest.result["theme_insight"]["theme_name"] == "DeepSeek"


def test_theme_picker_task_service_lists_recent_history(monkeypatch):
    from src.services.theme_picker_service import ThemePickerService

    with tempfile.TemporaryDirectory() as temp_dir:
        _configure_temp_db(temp_dir)
        service = get_theme_picker_task_service()

        def fake_scan(self, request):
            return {
                "query": {
                    "theme_id": request.theme_id,
                    "theme_name": request.theme_name or "AI应用",
                    "board_code": request.board_code,
                    "board_name": request.board_name,
                    "strategy_mode": request.strategy_mode,
                    "max_candidates": request.max_candidates,
                },
                "theme_insight": {
                    "theme_name": request.theme_name or "AI应用",
                    "event_status": "triggered",
                    "event_score": 88,
                    "matched_keywords": ["AI应用"],
                    "news_count": 3,
                    "heat_level": "medium",
                    "board_mapping_path": "000858.DC -> tushare",
                    "board_candidate_count": 12,
                    "primary_catalyst": "题材轮动",
                },
                "stocks": [
                    {
                        "rank": 1,
                        "stock_code": "000034.SZ",
                        "stock_name": "神州数码",
                        "signal_level": "持有候选",
                        "selection_reason": "趋势较强",
                        "mini_reasons": ["MA10 在 MA20 上方"],
                    }
                ],
                "selected_stock": None,
                "source_info": {
                    "board_source": "tushare_dc",
                    "board_fallback_used": False,
                    "cache_hit": False,
                    "source_pills": ["tushare"],
                    "note": "ok",
                },
                "empty_reason": None,
            }

        monkeypatch.setattr(ThemePickerService, "scan", fake_scan)

        task = service.submit_scan(
            ThemePickerScanRequest(
                theme_name="AI应用",
                board_code="000858.DC",
                strategy_mode="holding",
                max_candidates=8,
            )
        )

        deadline = time.time() + 3
        while time.time() < deadline:
            latest = service.get_task(task.task_id)
            if latest and latest.status == ThemePickerTaskStatus.COMPLETED:
                break
            time.sleep(0.05)

        history = service.list_tasks(limit=5)
        assert history
        matched = next((item for item in history if item.task_id == task.task_id), None)
        assert matched is not None
        assert matched.result is not None
        assert matched.result["query"]["board_code"] == "000858.DC"


def test_theme_picker_task_service_can_restore_from_db_after_memory_cleanup(monkeypatch):
    from src.services.theme_picker_service import ThemePickerService

    with tempfile.TemporaryDirectory() as temp_dir:
        _configure_temp_db(temp_dir)
        service = get_theme_picker_task_service()

        def fake_scan(self, request):
            return {
                "query": {
                    "theme_id": request.theme_id,
                    "theme_name": request.theme_name or "DeepSeek",
                    "board_code": request.board_code,
                    "board_name": request.board_name,
                    "strategy_mode": request.strategy_mode,
                    "max_candidates": request.max_candidates,
                },
                "theme_insight": {
                    "theme_name": "DeepSeek",
                    "event_status": "triggered",
                    "event_score": 95,
                    "matched_keywords": ["DeepSeek", "DeepSeek-V4"],
                    "news_count": 4,
                    "heat_level": "high",
                    "board_mapping_path": "BK1188 -> 000771.DC -> tushare",
                    "board_candidate_count": 8,
                    "primary_catalyst": "模型发布",
                },
                "stocks": [
                    {
                        "rank": 1,
                        "stock_code": "688629.SH",
                        "stock_name": "华丰科技",
                        "signal_level": "优先关注",
                        "selection_reason": "题材强相关",
                        "mini_reasons": ["回踩后企稳"],
                    }
                ],
                "selected_stock": None,
                "source_info": {
                    "board_source": "tushare_dc",
                    "board_fallback_used": True,
                    "cache_hit": False,
                    "source_pills": ["tushare"],
                    "note": "ok",
                },
                "empty_reason": None,
            }

        monkeypatch.setattr(ThemePickerService, "scan", fake_scan)

        task = service.submit_scan(
            ThemePickerScanRequest(
                board_code="BK1188",
                strategy_mode="holding",
                max_candidates=8,
            )
        )

        deadline = time.time() + 3
        while time.time() < deadline:
            latest = service.get_task(task.task_id)
            if latest and latest.status == ThemePickerTaskStatus.COMPLETED:
                break
            time.sleep(0.05)

        service._tasks.clear()

        restored = service.get_task(task.task_id)
        assert restored is not None
        assert restored.status == ThemePickerTaskStatus.COMPLETED
        assert restored.result is not None
        assert restored.result["stocks"][0]["stock_name"] == "华丰科技"

        history = service.list_tasks(limit=5)
        matched = next((item for item in history if item.task_id == task.task_id), None)
        assert matched is not None
        assert matched.result is not None
        assert matched.result["theme_insight"]["board_mapping_path"] == "BK1188 -> 000771.DC -> tushare"


def test_theme_picker_task_service_repairs_duplicate_stocks_from_persisted_history():
    with tempfile.TemporaryDirectory() as temp_dir:
        _configure_temp_db(temp_dir)
        db = DatabaseManager.get_instance()
        task_id = "persisted-duplicate-task"
        result_payload = {
            "query": {
                "theme_id": None,
                "theme_name": "DeepSeek",
                "board_code": "BK1188",
                "board_name": "DeepSeek概念",
                "strategy_mode": "holding",
                "max_candidates": 8,
            },
            "theme_insight": {
                "theme_name": "DeepSeek",
                "event_status": "triggered",
                "event_score": 95,
                "matched_keywords": ["DeepSeek"],
                "news_count": 4,
                "heat_level": "high",
                "board_mapping_path": "BK1188 -> 000771.DC -> tushare",
                "board_candidate_count": 2,
                "primary_catalyst": "模型发布",
            },
            "stocks": [
                {
                    "rank": 1,
                    "stock_code": "688629.SH",
                    "stock_name": "华丰科技",
                    "signal_level": "优先关注",
                    "selection_reason": "题材强相关",
                    "mini_reasons": ["回踩后企稳"],
                },
                {
                    "rank": 2,
                    "stock_code": "688629.SH",
                    "stock_name": "华丰科技",
                    "signal_level": "优先关注",
                    "selection_reason": "题材强相关",
                    "mini_reasons": ["MA20 维持向上"],
                },
            ],
            "selected_stock": None,
            "source_info": {
                "board_source": "tushare_dc",
                "board_fallback_used": True,
                "cache_hit": False,
                "source_pills": ["tushare"],
                "note": "ok",
            },
            "empty_reason": None,
        }
        db.save_theme_picker_task_history(
            task_id=task_id,
            status="completed",
            progress=100,
            message="主题选股完成",
            request_payload={
                "board_code": "BK1188",
                "board_name": "DeepSeek概念",
                "strategy_mode": "holding",
                "max_candidates": 8,
            },
            result_payload=result_payload,
            created_at=datetime.now(),
            completed_at=datetime.now(),
        )

        service = get_theme_picker_task_service()
        restored = service.get_task(task_id)

        assert restored is not None
        assert restored.result is not None
        assert len(restored.result["stocks"]) == 1
        assert restored.result["stocks"][0]["stock_code"] == "688629.SH"
        assert restored.result["stocks"][0]["mini_reasons"] == ["回踩后企稳", "MA20 维持向上"]
        assert restored.result["theme_insight"]["board_candidate_count"] == 1

        persisted = db.get_theme_picker_task_history(task_id)
        persisted_result = db._safe_json_loads(persisted.result_payload)
        assert len(persisted_result["stocks"]) == 1
        assert persisted_result["theme_insight"]["board_candidate_count"] == 1


def test_theme_picker_task_service_recovers_unfinished_tasks_after_restart(monkeypatch):
    from src.services.theme_picker_service import ThemePickerService

    with tempfile.TemporaryDirectory() as temp_dir:
        _configure_temp_db(temp_dir)
        db = DatabaseManager.get_instance()
        db.save_theme_picker_task_history(
            task_id="recover-me",
            status="processing",
            progress=40,
            message="处理中",
            request_payload={
                "theme_id": None,
                "theme_name": "DeepSeek",
                "board_code": "BK1188",
                "board_name": "DeepSeek概念",
                "strategy_mode": "holding",
                "max_candidates": 8,
                "include_untriggered": False,
            },
            created_at=datetime.now(),
            started_at=datetime.now(),
        )

        def fake_scan(self, request):
            return {
                "query": {
                    "theme_id": request.theme_id,
                    "theme_name": request.theme_name or "DeepSeek",
                    "board_code": request.board_code,
                    "board_name": request.board_name,
                    "strategy_mode": request.strategy_mode,
                    "max_candidates": request.max_candidates,
                },
                "theme_insight": {
                    "theme_name": "DeepSeek",
                    "event_status": "triggered",
                    "event_score": 99,
                    "matched_keywords": ["DeepSeek"],
                    "news_count": 3,
                    "heat_level": "high",
                    "board_mapping_path": "BK1188 -> 000771.DC -> tushare",
                    "board_candidate_count": 5,
                    "primary_catalyst": "模型发布",
                },
                "stocks": [],
                "selected_stock": None,
                "source_info": {
                    "board_source": "tushare_dc",
                    "board_fallback_used": True,
                    "cache_hit": False,
                    "source_pills": ["tushare"],
                    "note": "recovered",
                },
                "empty_reason": "暂无结果",
            }

        monkeypatch.setattr(ThemePickerService, "scan", fake_scan)

        ThemePickerTaskService.reset_instance()
        service = get_theme_picker_task_service()

        deadline = time.time() + 3
        latest = None
        while time.time() < deadline:
            latest = service.get_task("recover-me")
            if latest and latest.status == ThemePickerTaskStatus.COMPLETED:
                break
            time.sleep(0.05)

        assert latest is not None
        assert latest.status == ThemePickerTaskStatus.COMPLETED
        assert latest.result is not None
        assert latest.message == "主题选股完成"


def test_theme_picker_task_service_retries_from_history(monkeypatch):
    from src.services.theme_picker_service import ThemePickerService

    with tempfile.TemporaryDirectory() as temp_dir:
        _configure_temp_db(temp_dir)
        service = get_theme_picker_task_service()

        def fake_scan(self, request):
            return {
                "query": {
                    "theme_id": request.theme_id,
                    "theme_name": request.theme_name or "AI应用",
                    "board_code": request.board_code,
                    "board_name": request.board_name,
                    "strategy_mode": request.strategy_mode,
                    "max_candidates": request.max_candidates,
                },
                "theme_insight": {
                    "theme_name": request.theme_name or "AI应用",
                    "event_status": "triggered",
                    "event_score": 80,
                    "matched_keywords": ["AI应用"],
                    "news_count": 2,
                    "heat_level": "medium",
                    "board_mapping_path": "000858.DC -> tushare",
                    "board_candidate_count": 6,
                    "primary_catalyst": "题材轮动",
                },
                "stocks": [],
                "selected_stock": None,
                "source_info": {
                    "board_source": "tushare_dc",
                    "board_fallback_used": False,
                    "cache_hit": False,
                    "source_pills": ["tushare"],
                    "note": "retry",
                },
                "empty_reason": None,
            }

        monkeypatch.setattr(ThemePickerService, "scan", fake_scan)

        original = service.submit_scan(
            ThemePickerScanRequest(
                theme_name="AI应用",
                board_code="000858.DC",
                strategy_mode="holding",
                max_candidates=8,
            )
        )

        deadline = time.time() + 3
        while time.time() < deadline:
            latest = service.get_task(original.task_id)
            if latest and latest.status == ThemePickerTaskStatus.COMPLETED:
                break
            time.sleep(0.05)

        retried = service.retry_task(original.task_id)
        assert retried.task_id != original.task_id
        assert retried.request_payload["board_code"] == "000858.DC"

        deadline = time.time() + 3
        retried_latest = None
        while time.time() < deadline:
            retried_latest = service.get_task(retried.task_id)
            if retried_latest and retried_latest.status == ThemePickerTaskStatus.COMPLETED:
                break
            time.sleep(0.05)

        assert retried_latest is not None
        assert retried_latest.status == ThemePickerTaskStatus.COMPLETED


def test_theme_picker_task_service_cleans_up_expired_terminal_history(monkeypatch):
    from src.services.theme_picker_service import ThemePickerService

    with tempfile.TemporaryDirectory() as temp_dir:
        _configure_temp_db(temp_dir)
        os.environ["THEME_PICKER_TASK_HISTORY_RETENTION_DAYS"] = "1"
        os.environ["THEME_PICKER_TASK_HISTORY_CLEANUP_BATCH_SIZE"] = "50"
        Config._instance = None
        DatabaseManager.reset_instance()
        ThemePickerTaskService.reset_instance()
        db = DatabaseManager.get_instance()

        old_time = datetime.now() - timedelta(days=5)
        db.save_theme_picker_task_history(
            task_id="expired-task",
            status="completed",
            progress=100,
            message="旧结果",
            request_payload={"theme_name": "DeepSeek"},
            result_payload={"query": {"theme_name": "DeepSeek"}},
            created_at=old_time,
            completed_at=old_time,
        )

        def fake_scan(self, request):
            return {
                "query": {
                    "theme_id": request.theme_id,
                    "theme_name": request.theme_name or "DeepSeek",
                    "board_code": request.board_code,
                    "board_name": request.board_name,
                    "strategy_mode": request.strategy_mode,
                    "max_candidates": request.max_candidates,
                },
                "theme_insight": {
                    "theme_name": "DeepSeek",
                    "event_status": "triggered",
                    "event_score": 90,
                    "matched_keywords": ["DeepSeek"],
                    "news_count": 1,
                    "heat_level": "high",
                    "board_mapping_path": "BK1188 -> 000771.DC -> tushare",
                    "board_candidate_count": 3,
                    "primary_catalyst": "模型发布",
                },
                "stocks": [],
                "selected_stock": None,
                "source_info": {
                    "board_source": "tushare_dc",
                    "board_fallback_used": True,
                    "cache_hit": False,
                    "source_pills": ["tushare"],
                    "note": "cleanup",
                },
                "empty_reason": None,
            }

        monkeypatch.setattr(ThemePickerService, "scan", fake_scan)

        service = get_theme_picker_task_service()
        task = service.submit_scan(
            ThemePickerScanRequest(
                board_code="BK1188",
                strategy_mode="holding",
                max_candidates=8,
            )
        )

        deadline = time.time() + 3
        while time.time() < deadline:
            latest = service.get_task(task.task_id)
            if latest and latest.status == ThemePickerTaskStatus.COMPLETED:
                break
            time.sleep(0.05)

        assert db.get_theme_picker_task_history("expired-task") is None


def test_theme_picker_task_service_lists_latest_completed_by_recent_activity(monkeypatch):
    from src.services.theme_picker_service import ThemePickerService

    with tempfile.TemporaryDirectory() as temp_dir:
        _configure_temp_db(temp_dir)
        db = DatabaseManager.get_instance()
        older_created = datetime.now() - timedelta(hours=2)
        newer_completed = datetime.now() - timedelta(minutes=5)
        db.save_theme_picker_task_history(
            task_id="older-created-but-newer-completed",
            status="completed",
            progress=100,
            message="较新完成",
            request_payload={"theme_name": "新能源"},
            result_payload={
                "query": {"theme_name": "新能源", "strategy_mode": "holding", "max_candidates": 8},
                "theme_insight": {"theme_name": "新能源", "event_status": "triggered"},
                "stocks": [],
                "selected_stock": None,
                "source_info": {},
            },
            created_at=older_created,
            completed_at=newer_completed,
        )
        db.save_theme_picker_task_history(
            task_id="newer-created-but-older-completed",
            status="completed",
            progress=100,
            message="较早完成",
            request_payload={"theme_name": "DeepSeek"},
            result_payload={
                "query": {"theme_name": "DeepSeek", "strategy_mode": "holding", "max_candidates": 8},
                "theme_insight": {"theme_name": "DeepSeek", "event_status": "triggered"},
                "stocks": [],
                "selected_stock": None,
                "source_info": {},
            },
            created_at=datetime.now() - timedelta(hours=1),
            completed_at=datetime.now() - timedelta(minutes=20),
        )

        service = get_theme_picker_task_service()
        tasks = service.list_tasks(limit=2)

        assert tasks[0].task_id == "older-created-but-newer-completed"
