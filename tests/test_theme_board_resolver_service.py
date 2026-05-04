# -*- coding: utf-8 -*-

import pandas as pd
from pathlib import Path

from src.schemas.theme_event import ThemeDefinitionSchema, ThemeEventSchema
from src.services.theme_board_resolver_service import ThemeBoardResolverService
from src.services.theme_expansion_service import ThemeExpansionService


def test_theme_board_resolver_uses_explicit_board_code(monkeypatch):
    service = ThemeBoardResolverService()
    calls = []

    def _fake_fetch(board_code: str):
        calls.append(board_code)
        return ["688629.SH", "300229.SZ"]

    monkeypatch.setattr(service, "_fetch_board_constituent_codes", _fake_fetch)

    theme = ThemeDefinitionSchema(
        id="deepseek",
        name="DeepSeek",
        concept_board_codes=["BK1188"],
    )

    candidates = service.resolve_theme_candidates(theme, max_candidates=10)

    assert calls == ["BK1188"]
    assert candidates == ["688629.SH", "300229.SZ"]


def test_theme_board_resolver_matches_board_name(monkeypatch):
    service = ThemeBoardResolverService()
    board_index_df = pd.DataFrame(
        [
            {"板块名称": "DeepSeek概念", "板块代码": "BK1188"},
        ]
    )
    service._board_index_df = board_index_df
    service._board_name_to_code = {"DeepSeek概念": "BK1188"}
    service._normalized_board_name_to_code = {"deepseek": "BK1188"}

    calls = []

    def _fake_fetch(board_code: str):
        calls.append(board_code)
        return ["688629.SH"]

    monkeypatch.setattr(service, "_fetch_board_constituent_codes", _fake_fetch)

    theme = ThemeDefinitionSchema(
        id="deepseek",
        name="DeepSeek",
        concept_board_names=["DeepSeek概念股"],
    )

    candidates = service.resolve_theme_candidates(theme, max_candidates=10)

    assert calls == ["BK1188"]
    assert candidates == ["688629.SH"]


def test_theme_board_resolver_uses_explicit_dc_theme_code(monkeypatch):
    service = ThemeBoardResolverService()
    calls = []

    def _fake_fetch(theme_code: str):
        calls.append(theme_code)
        return ["000034.SZ", "002230.SZ"]

    monkeypatch.setattr(service, "_fetch_dc_theme_constituent_codes", _fake_fetch)

    theme = ThemeDefinitionSchema(
        id="ai",
        name="AI应用",
        concept_board_codes=["000858.DC"],
    )

    candidates = service.resolve_theme_candidates(theme, max_candidates=10)

    assert calls == ["000858.DC"]
    assert candidates == ["000034.SZ", "002230.SZ"]


def test_theme_board_resolver_uses_explicit_board_to_dc_mapping(monkeypatch):
    service = ThemeBoardResolverService()
    em_calls = []
    dc_calls = []

    monkeypatch.setattr(
        service,
        "_fetch_board_constituent_codes",
        lambda board_code: em_calls.append(board_code) or [],
    )
    monkeypatch.setattr(
        service,
        "_fetch_dc_theme_constituent_codes",
        lambda theme_code: dc_calls.append(theme_code) or ["688629.SH", "688256.SH"],
    )

    theme = ThemeDefinitionSchema(
        id="deepseek",
        name="DeepSeek",
        concept_board_codes=["BK1188"],
        board_code_mappings={"BK1188": "000771.DC"},
    )

    candidates = service.resolve_theme_candidates(theme, max_candidates=10)

    assert em_calls == ["BK1188"]
    assert dc_calls == ["000771.DC"]
    assert candidates == ["688629.SH", "688256.SH"]


def test_theme_board_resolver_uses_global_board_to_dc_mapping(monkeypatch, tmp_path: Path):
    service = ThemeBoardResolverService()
    service.global_mapping_path = tmp_path / "theme_board_mappings.json"
    service.example_global_mapping_path = tmp_path / "theme_board_mappings.example.json"
    service.global_mapping_path.write_text(
        '{"mappings": {"BK1188": "000771.DC"}}',
        encoding="utf-8",
    )
    em_calls = []
    dc_calls = []

    monkeypatch.setattr(
        service,
        "_fetch_board_constituent_codes",
        lambda board_code: em_calls.append(board_code) or [],
    )
    monkeypatch.setattr(
        service,
        "_fetch_dc_theme_constituent_codes",
        lambda theme_code: dc_calls.append(theme_code) or ["688629.SH"],
    )

    theme = ThemeDefinitionSchema(
        id="board_bk1188",
        name="BK1188",
        concept_board_codes=["BK1188"],
    )

    candidates = service.resolve_theme_candidates(theme, max_candidates=10)

    assert em_calls == ["BK1188"]
    assert dc_calls == ["000771.DC"]
    assert candidates == ["688629.SH"]


def test_theme_board_resolver_matches_dc_theme_name(monkeypatch):
    service = ThemeBoardResolverService()
    dc_theme_index_df = pd.DataFrame(
        [
            {"题材名称": "AI应用", "题材代码": "000858.DC", "交易日期": "20260428"},
        ]
    )
    service._apply_dc_theme_index(dc_theme_index_df)

    calls = []

    def _fake_fetch(theme_code: str):
        calls.append(theme_code)
        return ["000034.SZ"]

    monkeypatch.setattr(service, "_fetch_dc_theme_constituent_codes", _fake_fetch)

    theme = ThemeDefinitionSchema(
        id="ai",
        name="AI应用",
        concept_board_names=["人工智能应用"],
    )

    candidates = service.resolve_theme_candidates(theme, max_candidates=10)

    assert calls == ["000858.DC"]
    assert candidates == ["000034.SZ"]


def test_theme_expansion_uses_board_candidates_before_text_fallback(monkeypatch):
    service = ThemeExpansionService(search_service=None)

    monkeypatch.setattr(
        service.board_resolver,
        "resolve_theme_candidates",
        lambda theme, max_candidates=30: ["688629.SH", "300229.SZ"],
    )

    def _fail_search(**kwargs):
        raise AssertionError("text fallback should not run when board candidates exist")

    monkeypatch.setattr(service, "_search_query", _fail_search)

    theme = ThemeDefinitionSchema(id="deepseek", name="DeepSeek")
    event = ThemeEventSchema(theme_id="deepseek", theme_name="DeepSeek", triggered=True)

    candidates = service.expand_theme(
        theme,
        event,
        ["603019.SH"],
        max_candidates=10,
    )

    assert candidates == ["603019.SH", "688629.SH", "300229.SZ"]


def test_theme_expansion_filters_unconfirmed_text_codes(monkeypatch):
    service = ThemeExpansionService(search_service=None)

    monkeypatch.setattr(
        service,
        "_get_stock_universe",
        lambda: [
            {"code": "688629.SH", "name": "华丰科技"},
            {"code": "300229.SZ", "name": "拓尔思"},
        ],
    )

    extracted = service._extract_candidate_signals_from_text(
        "DeepSeek 概念股包括 688629、300229，同时出现 885749 这样的非股票编码"
    )

    assert extracted == {
        "688629.SH": 2,
        "300229.SZ": 2,
    }


def test_theme_board_resolver_saves_constituent_cache(monkeypatch, tmp_path: Path):
    service = ThemeBoardResolverService()
    service.cache_path = tmp_path / "theme_board_cache.json"

    import akshare as ak

    monkeypatch.setattr(
        ak,
        "stock_board_concept_cons_em",
        lambda symbol: pd.DataFrame([{"代码": "688629"}, {"代码": "300229"}]),
    )

    codes = service._fetch_board_constituent_codes("BK1188")

    assert codes == ["688629.SH", "300229.SZ"]
    payload = service._load_cache_payload()
    assert payload["board_constituents"]["BK1188"]["codes"] == ["688629.SH", "300229.SZ"]


def test_theme_board_resolver_falls_back_to_cached_constituents(tmp_path: Path):
    service = ThemeBoardResolverService()
    service.cache_path = tmp_path / "theme_board_cache.json"
    service._save_cached_board_constituents("BK1188", ["688629.SH", "300229.SZ"])

    def _raise():
        raise RuntimeError("network down")

    import akshare as ak

    original = ak.stock_board_concept_cons_em
    ak.stock_board_concept_cons_em = lambda symbol: _raise()
    try:
        codes = service._fetch_board_constituent_codes("BK1188")
    finally:
        ak.stock_board_concept_cons_em = original

    assert codes == ["688629.SH", "300229.SZ"]


def test_theme_board_resolver_ignores_expired_board_constituent_cache(tmp_path: Path, monkeypatch):
    service = ThemeBoardResolverService()
    service.cache_path = tmp_path / "theme_board_cache.json"
    service._save_cached_board_constituents("BK1188", ["688629.SH", "300229.SZ"])

    payload = service._load_cache_payload()
    payload["board_constituents"]["BK1188"]["cached_at"] = 100
    service._save_cache_payload(payload)

    monkeypatch.setattr(
        "src.services.theme_board_resolver_service.get_config",
        lambda: type("Cfg", (), {"theme_board_cache_ttl_seconds": 10})(),
    )
    monkeypatch.setattr("src.services.theme_board_resolver_service.time.time", lambda: 1000.0)

    codes = service._load_cached_board_constituents("BK1188")

    assert codes == []


def test_theme_board_resolver_saves_dc_theme_constituent_cache(monkeypatch, tmp_path: Path):
    service = ThemeBoardResolverService()
    service.cache_path = tmp_path / "theme_board_cache.json"
    service._dc_theme_trade_dates["000858.DC"] = "20260428"

    class _FakeClient:
        def query(self, api_name: str, fields: str = "", **kwargs):
            assert api_name == "dc_concept_cons"
            assert kwargs["theme_code"] == "000858.DC"
            assert kwargs["trade_date"] == "20260428"
            return pd.DataFrame(
                [
                    {"ts_code": "000034.SZ", "trade_date": "20260428"},
                    {"ts_code": "002230.SZ", "trade_date": "20260428"},
                ]
            )

    monkeypatch.setattr(service, "_get_tushare_client", lambda: _FakeClient())

    codes = service._fetch_dc_theme_constituent_codes("000858.DC")

    assert codes == ["000034.SZ", "002230.SZ"]
    payload = service._load_cache_payload()
    assert payload["dc_theme_constituents"]["000858.DC"]["codes"] == ["000034.SZ", "002230.SZ"]


def test_theme_board_resolver_falls_back_to_cached_dc_theme_constituents(tmp_path: Path):
    service = ThemeBoardResolverService()
    service.cache_path = tmp_path / "theme_board_cache.json"
    service._save_cached_dc_theme_constituents("000858.DC", ["000034.SZ", "002230.SZ"])

    def _raise():
        raise RuntimeError("network down")

    monkeypatch_target = service
    monkeypatch_target._get_tushare_client = lambda: (_raise())  # type: ignore[method-assign]
    codes = service._fetch_dc_theme_constituent_codes("000858.DC")

    assert codes == ["000034.SZ", "002230.SZ"]


def test_theme_board_resolver_ignores_expired_dc_constituent_cache(tmp_path: Path, monkeypatch):
    service = ThemeBoardResolverService()
    service.cache_path = tmp_path / "theme_board_cache.json"
    service._save_cached_dc_theme_constituents("000858.DC", ["000034.SZ", "002230.SZ"])

    payload = service._load_cache_payload()
    payload["dc_theme_constituents"]["000858.DC"]["cached_at"] = 100
    service._save_cache_payload(payload)

    monkeypatch.setattr(
        "src.services.theme_board_resolver_service.get_config",
        lambda: type("Cfg", (), {"theme_board_cache_ttl_seconds": 10})(),
    )
    monkeypatch.setattr("src.services.theme_board_resolver_service.time.time", lambda: 1000.0)

    codes = service._load_cached_dc_theme_constituents("000858.DC")

    assert codes == []
