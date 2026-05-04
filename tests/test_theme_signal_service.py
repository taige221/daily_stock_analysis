# -*- coding: utf-8 -*-

from types import SimpleNamespace

import pandas as pd

from src.schemas.theme_event import ThemeSignalRuleSchema
from src.services.theme_signal_service import ThemeSignalService


def _make_trend_result(
    *,
    ma5: float = 10.4,
    ma10: float = 10.0,
    ma20: float = 9.6,
    signal_score: float = 62.0,
    buy_signal: str = "买入",
):
    return SimpleNamespace(
        ma5=ma5,
        ma10=ma10,
        ma20=ma20,
        signal_score=signal_score,
        buy_signal=SimpleNamespace(value=buy_signal),
        trend_status=SimpleNamespace(value="多头排列"),
        bias_ma5=1.2,
    )


def test_holding_prequalification_accepts_pullback_above_ma20():
    service = ThemeSignalService.__new__(ThemeSignalService)
    rule = ThemeSignalRuleSchema(strategy_mode="holding")
    df = pd.DataFrame(
        [
            {"close": 9.8, "ma10": 9.7, "ma20": 9.4, "pct_chg": 1.2},
            {"close": 10.1, "ma10": 9.9, "ma20": 9.5, "pct_chg": 5.8},
            {"close": 9.95, "ma10": 10.0, "ma20": 9.6, "pct_chg": -0.6},
        ]
    )
    trend_result = _make_trend_result(ma5=10.1, ma10=10.0, ma20=9.6, signal_score=61.0, buy_signal="持有")

    prequalified, reasons = service._check_prequalification(df, trend_result, rule)

    assert prequalified is True
    assert "未满足 MA5 > MA10 > MA20" not in reasons
    assert any("未破 MA20" in reason for reason in reasons)


def test_holding_prequalification_accepts_near_flat_ma20_and_support_band():
    service = ThemeSignalService.__new__(ThemeSignalService)
    rule = ThemeSignalRuleSchema(strategy_mode="holding")
    df = pd.DataFrame(
        [
            {"close": 9.95, "ma10": 9.8, "ma20": 9.60, "pct_chg": 1.5},
            {"close": 10.08, "ma10": 9.95, "ma20": 9.58, "pct_chg": 5.3},
            {"close": 9.47, "ma10": 9.88, "ma20": 9.56, "pct_chg": -1.1},
        ]
    )
    trend_result = _make_trend_result(ma10=9.88, ma20=9.56, signal_score=50.0, buy_signal="持有")

    prequalified, reasons = service._check_prequalification(df, trend_result, rule)

    assert prequalified is True
    assert any("支撑带内" in reason for reason in reasons)


def test_holding_trigger_does_not_require_intraday_volume_spike():
    service = ThemeSignalService.__new__(ThemeSignalService)
    rule = ThemeSignalRuleSchema(strategy_mode="holding", min_volume_ratio=1.5)
    df = pd.DataFrame(
        [
            {"high": 10.0},
            {"high": 10.2},
            {"high": 10.3},
        ]
    )
    trend_result = _make_trend_result(signal_score=63.0, buy_signal="买入")
    metrics = {
        "current_price": 9.58,
        "pct_chg": 1.1,
        "volume_ratio": 0.92,
        "ma20": 9.7,
    }

    triggered, reasons = service._check_intraday_trigger(
        df=df,
        metrics=metrics,
        trend_result=trend_result,
        rule=rule,
    )

    assert triggered is True
    assert any("不作为持有型硬门槛" in reason for reason in reasons)
    assert any("可接受支撑带" in reason for reason in reasons)


def test_holding_finalize_marks_pullback_zone_as_watchlist():
    service = ThemeSignalService.__new__(ThemeSignalService)
    rule = ThemeSignalRuleSchema(strategy_mode="holding")
    theme = SimpleNamespace(id="ai_app", name="AI应用")
    item = {
        "stock_code": "000034.SZ",
        "stock_name": "神州数码",
        "prequalified": True,
        "triggered": True,
        "metrics": {
            "current_price": 9.72,
            "pct_chg": 1.2,
            "ma10": 10.05,
            "ma20": 9.8,
            "bias_ma5": 1.0,
            "bias_ma10": -0.5,
            "trend_score": 64.0,
        },
        "reasons": ["满足多头排列底座"],
    }

    signal = service._finalize_signal(theme, item, resonance_count=1, rule=rule)

    assert signal.signal_level == "低吸观察"
    assert any("分批介入" in reason for reason in signal.reasons)
