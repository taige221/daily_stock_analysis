# -*- coding: utf-8 -*-

from src.schemas.theme_event import (
    ThemeAlertResultSchema,
    ThemeDefinitionSchema,
    ThemeEventSchema,
    ThemeStockSignalSchema,
)
from src.services.theme_picker_service import ThemePickerService
from api.v1.schemas.theme_picker import ThemePickerScanRequest


class _FakeRegistry:
    def __init__(self, themes):
        self._themes = themes

    def list_themes(self, *, enabled_only=False):
        if enabled_only:
            return [theme for theme in self._themes if theme.enabled]
        return list(self._themes)

    def get_theme(self, theme_id):
        for theme in self._themes:
            if theme.id == theme_id:
                return theme
        return None


class _FakePipeline:
    def __init__(self, result):
        self._result = result

    def run(self, **kwargs):
        return self._result


class _FakeStockPoolService:
    def get_stock_pool(self, theme):
        return []


class _FakeExpansionService:
    def expand_theme(self, theme, event, stock_pool, max_candidates):
        return [theme.id]


class _FakeSignalService:
    def evaluate_theme(self, theme, event, candidate_pool):
        return [
            ThemeStockSignalSchema(
                theme_id=theme.id,
                theme_name=theme.name,
                stock_code="688629.SH",
                stock_name="华丰科技",
                signal_level="持有候选",
                triggered=True,
                reasons=[f"{theme.id}: 趋势底座完整"],
                metrics={
                    "trend_score": 68 if theme.id == "board_bk1188" else 67,
                    "pct_chg": 2.8,
                    "volume_ratio": 1.2,
                    "turnover_rate": 18.6,
                    "buy_signal": "买入",
                },
            )
        ]


class _FakeDirectPipeline:
    def __init__(self):
        self.stock_pool_service = _FakeStockPoolService()
        self.expansion_service = _FakeExpansionService()
        self.signal_service = _FakeSignalService()


class _FakeDailyBar:
    def __init__(self, *, close, high, ma10, ma20, pct_chg):
        self.close = close
        self.high = high
        self.ma10 = ma10
        self.ma20 = ma20
        self.pct_chg = pct_chg


class _FakeDb:
    def __init__(self, records):
        self._records = records

    def get_latest_data(self, code, days=21):
        return list(self._records.get(code, []))[:days]


def test_theme_picker_scan_builds_stock_response():
    theme = ThemeDefinitionSchema(
        id="deepseek",
        name="DeepSeek",
        enabled=True,
        concept_board_codes=["BK1188"],
        concept_board_names=["DeepSeek概念"],
        board_code_mappings={"BK1188": "000771.DC"},
    )
    result = ThemeAlertResultSchema(
        scanned_theme_ids=["deepseek"],
        events=[
            ThemeEventSchema(
                theme_id="deepseek",
                theme_name="DeepSeek",
                event_score=100,
                triggered=True,
                trigger_reason="ok",
                matched_keywords=["DeepSeek", "DeepSeek-V4"],
                matched_news_count=10,
                news_items=[],
            )
        ],
        signals=[
            ThemeStockSignalSchema(
                theme_id="deepseek",
                theme_name="DeepSeek",
                stock_code="688629.SH",
                stock_name="华丰科技",
                signal_level="持有候选",
                triggered=True,
                reasons=["MA10 仍在 MA20 上方", "MA20 维持向上", "趋势底座完整"],
                metrics={
                    "current_price": 136.0,
                    "trend_score": 68,
                    "pct_chg": 2.8,
                    "volume_ratio": 1.2,
                    "turnover_rate": 18.6,
                    "trend_status": "bullish",
                    "buy_signal": "买入",
                    "ma5": 135.2,
                    "ma10": 131.7,
                    "ma20": 122.3,
                    "bias_ma5": 1.8,
                    "bias_ma10": 3.1,
                    "bias_ma20": 7.6,
                    "recent_strong_days": 1,
                    "recent_high": 147.2,
                    "resonance_count": 2,
                },
            )
        ],
    )
    service = ThemePickerService(
        registry_service=_FakeRegistry([theme]),
        pipeline=_FakePipeline(result),
    )

    response = service.scan(
        ThemePickerScanRequest(
            theme_id="deepseek",
            strategy_mode="holding",
            max_candidates=8,
        )
    )

    assert response["query"]["theme_id"] == "deepseek"
    assert response["theme_insight"]["theme_name"] == "DeepSeek"
    assert response["theme_insight"]["board_mapping_path"] == "BK1188 -> 000771.DC"
    assert len(response["stocks"]) == 1
    assert response["stocks"][0]["stock_code"] == "688629.SH"
    assert response["stocks"][0]["signal_level"] == "持有候选"
    assert response["stocks"][0]["current_price"] == 136.0
    assert response["stocks"][0]["support_level"] == 131.7
    assert response["stocks"][0]["pressure_level"] == 147.2
    assert response["selected_stock"] is not None
    assert response["selected_stock"]["stock_code"] == "688629.SH"
    assert response["selected_stock"]["ma10"] == 131.7
    assert response["selected_stock"]["current_price"] == 136.0
    assert response["selected_stock"]["pressure_level"] == 147.2
    assert response["selected_stock"]["selected_reasons"]


def test_theme_picker_list_themes_returns_enabled_items():
    themes = [
        ThemeDefinitionSchema(id="deepseek", name="DeepSeek", enabled=True),
        ThemeDefinitionSchema(id="disabled", name="Disabled", enabled=False),
    ]
    service = ThemePickerService(
        registry_service=_FakeRegistry(themes),
        pipeline=_FakePipeline(ThemeAlertResultSchema()),
    )

    response = service.list_themes()

    assert [item["id"] for item in response["items"]] == ["deepseek"]


def test_direct_board_themes_dedup_same_board_code_and_name():
    theme = ThemeDefinitionSchema(
        id="deepseek",
        name="DeepSeek",
        enabled=True,
        concept_board_codes=["BK1188"],
        concept_board_names=["DeepSeek概念"],
        board_code_mappings={"BK1188": "000771.DC"},
    )
    service = ThemePickerService(
        registry_service=_FakeRegistry([theme]),
        pipeline=_FakePipeline(ThemeAlertResultSchema()),
    )

    themes = service._build_direct_board_themes(
        ["BK1188"],
        ["DeepSeek概念"],
        strategy_mode="holding",
    )

    assert len(themes) == 1
    assert themes[0].concept_board_codes == ["BK1188"]
    assert themes[0].concept_board_names == ["DeepSeek概念"]


def test_theme_picker_scan_dedupes_duplicate_stock_codes_in_direct_mode():
    theme = ThemeDefinitionSchema(
        id="deepseek",
        name="DeepSeek",
        enabled=True,
        concept_board_codes=["BK1188"],
        concept_board_names=["DeepSeek概念"],
        board_code_mappings={"BK1188": "000771.DC"},
    )
    service = ThemePickerService(
        registry_service=_FakeRegistry([theme]),
        pipeline=_FakeDirectPipeline(),
    )

    response = service.scan(
        ThemePickerScanRequest(
            board_code="BK1188",
            board_name="DeepSeek概念",
            strategy_mode="holding",
            max_candidates=8,
        )
    )

    assert len(response["stocks"]) == 1
    assert response["stocks"][0]["stock_code"] == "688629.SH"
    assert response["theme_insight"]["board_candidate_count"] == 1


def test_normalize_response_payload_backfills_stock_key_levels_from_selected_stock():
    payload = {
        "stocks": [
            {
                "rank": 1,
                "stock_code": "688629.SH",
                "stock_name": "华丰科技",
                "signal_level": "持有候选",
            }
        ],
        "selected_stock": {
            "stock_code": "688629.SH",
            "stock_name": "华丰科技",
            "current_price": 136.0,
            "support_level": 131.7,
            "pressure_level": 147.2,
        },
        "theme_insight": {
            "theme_name": "DeepSeek",
            "board_candidate_count": 1,
        },
    }

    normalized, changed = ThemePickerService.normalize_response_payload(payload)

    assert changed is True
    assert normalized is not None
    assert normalized["source_info"]["response_schema_version"] == 2
    assert normalized["source_info"]["history_repaired"] is True
    assert normalized["stocks"][0]["current_price"] == 136.0
    assert normalized["stocks"][0]["support_level"] == 131.7
    assert normalized["stocks"][0]["pressure_level"] == 147.2


def test_normalize_response_payload_backfills_key_levels_from_daily_data():
    payload = {
        "stocks": [
            {
                "rank": 1,
                "stock_code": "603019.SH",
                "stock_name": "中科曙光",
                "signal_level": "主题触发",
            }
        ],
        "selected_stock": {
            "stock_code": "603019.SH",
            "stock_name": "中科曙光",
            "theme_relevance": "high",
        },
        "theme_insight": {
            "theme_name": "DeepSeek",
            "board_candidate_count": 1,
        },
    }
    fake_db = _FakeDb(
        {
            "603019.SH": [
                _FakeDailyBar(close=62.5, high=63.0, ma10=60.2, ma20=58.4, pct_chg=2.1),
                _FakeDailyBar(close=61.2, high=64.8, ma10=59.9, ma20=58.1, pct_chg=1.2),
                _FakeDailyBar(close=60.8, high=64.1, ma10=59.4, ma20=57.9, pct_chg=5.6),
            ]
        }
    )

    normalized, changed = ThemePickerService.normalize_response_payload(payload, db=fake_db)

    assert changed is True
    assert normalized is not None
    assert normalized["source_info"]["key_levels_backfilled"] is True
    assert normalized["source_info"]["pricing_source"] == "daily_only"
    assert normalized["stocks"][0]["current_price"] == 62.5
    assert normalized["stocks"][0]["support_level"] == 60.2
    assert normalized["stocks"][0]["pressure_level"] == 64.8
    assert normalized["selected_stock"]["current_price"] == 62.5
    assert normalized["selected_stock"]["ma10"] == 60.2
    assert normalized["selected_stock"]["pressure_level"] == 64.8
