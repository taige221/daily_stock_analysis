#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dynamic theme event radar runner.

Usage:
    python3 scripts/run_theme_alert.py
    python3 scripts/run_theme_alert.py --themes deepseek,semiconductor
    python3 scripts/run_theme_alert.py --board-code BK1188
    python3 scripts/run_theme_alert.py --board-code 000858.DC
    python3 scripts/run_theme_alert.py --board-name DeepSeek概念
    python3 scripts/run_theme_alert.py --board-name AI应用
    python3 scripts/run_theme_alert.py --board-code 000858.DC --strategy-mode holding
    python3 scripts/run_theme_alert.py --days 3 --include-untriggered
    python3 scripts/run_theme_alert.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable, List

# Add repo root to import path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_config, setup_env
from src.core.theme_alert_pipeline import ThemeAlertPipeline
from src.logging_config import setup_logging
from src.schemas.theme_event import ThemeAlertResultSchema, ThemeDefinitionSchema, ThemeEventSchema
from src.search_service import SearchService
from src.services.theme_expansion_service import ThemeExpansionService
from src.services.theme_event_scanner import ThemeEventScanner
from src.services.theme_registry_service import ThemeRegistryService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="运行动态主题事件雷达")
    parser.add_argument(
        "--themes",
        type=str,
        default="",
        help="指定主题 id，逗号分隔；为空时扫描全部启用主题",
    )
    parser.add_argument(
        "--board-code",
        type=str,
        default="",
        help="直接指定板块/题材代码，逗号分隔，例如 BK1188 或 000858.DC；会跳过新闻触发并直接按成分股回放",
    )
    parser.add_argument(
        "--board-name",
        type=str,
        default="",
        help="直接指定板块/题材名称，逗号分隔；会先匹配板块或题材代码，再按成分股回放",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="新闻时间窗口（天）",
    )
    parser.add_argument(
        "--max-results-per-keyword",
        type=int,
        default=5,
        help="每个关键词最多取回的新闻条数",
    )
    parser.add_argument(
        "--include-untriggered",
        action="store_true",
        help="包含未触发事件的主题",
    )
    parser.add_argument(
        "--max-expanded-candidates",
        type=int,
        default=30,
        help="主题触发后扩池评估的最大股票数",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="输出完整 JSON",
    )
    parser.add_argument(
        "--strategy-mode",
        type=str,
        default="",
        choices=["event", "holding"],
        help="技术评估口径：event=事件追踪型，holding=题材持有型",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="输出调试日志",
    )
    return parser.parse_args()


def build_pipeline() -> ThemeAlertPipeline:
    config = get_config()
    search_service = SearchService(
        bocha_keys=config.bocha_api_keys,
        tavily_keys=config.tavily_api_keys,
        anspire_keys=config.anspire_api_keys,
        brave_keys=config.brave_api_keys,
        serpapi_keys=config.serpapi_keys,
        minimax_keys=config.minimax_api_keys,
        searxng_base_urls=config.searxng_base_urls,
        searxng_public_instances_enabled=config.searxng_public_instances_enabled,
        news_max_age_days=config.news_max_age_days,
        news_strategy_profile=getattr(config, "news_strategy_profile", "short"),
    )
    event_scanner = ThemeEventScanner(search_service=search_service)
    expansion_service = ThemeExpansionService(search_service=search_service)
    return ThemeAlertPipeline(
        event_scanner=event_scanner,
        expansion_service=expansion_service,
    )


def parse_theme_ids(raw: str) -> List[str]:
    return [item.strip() for item in (raw or "").split(",") if item.strip()]


def parse_csv_values(raw: str) -> List[str]:
    return [item.strip() for item in (raw or "").split(",") if item.strip()]


def build_direct_board_themes(
    board_codes: List[str],
    board_names: List[str],
    *,
    registry_service: ThemeRegistryService | None = None,
    strategy_mode: str = "",
) -> List[ThemeDefinitionSchema]:
    themes: List[ThemeDefinitionSchema] = []
    registry_themes = registry_service.list_themes(enabled_only=False) if registry_service else []
    for board_code in board_codes:
        normalized_code = str(board_code or "").strip().upper()
        if not normalized_code:
            continue
        inherited_mappings = {}
        inherited_names: List[str] = []
        for registered_theme in registry_themes:
            registered_codes = {
                str(code or "").strip().upper()
                for code in getattr(registered_theme, "concept_board_codes", [])
            }
            if normalized_code not in registered_codes:
                continue
            inherited_mappings.update(getattr(registered_theme, "board_code_mappings", {}) or {})
            inherited_names.extend(
                [
                    str(name or "").strip()
                    for name in getattr(registered_theme, "concept_board_names", [])
                    if str(name or "").strip()
                ]
            )
        theme = ThemeDefinitionSchema(
                id=f"board_{normalized_code.lower()}",
                name=normalized_code,
                enabled=True,
                priority=0,
                keywords=[],
                stock_pool=[],
                concept_board_codes=[normalized_code],
                concept_board_names=list(dict.fromkeys(inherited_names)),
                board_code_mappings=inherited_mappings,
            )
        if strategy_mode:
            theme.signal_rules.strategy_mode = strategy_mode
        themes.append(theme)
    for board_name in board_names:
        normalized_name = str(board_name or "").strip()
        if not normalized_name:
            continue
        inherited_codes: List[str] = []
        inherited_mappings = {}
        for registered_theme in registry_themes:
            registered_names = {
                str(name or "").strip()
                for name in getattr(registered_theme, "concept_board_names", [])
            }
            if normalized_name not in registered_names:
                continue
            inherited_codes.extend(
                [
                    str(code or "").strip().upper()
                    for code in getattr(registered_theme, "concept_board_codes", [])
                    if str(code or "").strip()
                ]
            )
            inherited_mappings.update(getattr(registered_theme, "board_code_mappings", {}) or {})
        theme = ThemeDefinitionSchema(
                id=f"board_name_{normalized_name}",
                name=normalized_name,
                enabled=True,
                priority=0,
                keywords=[],
                stock_pool=[],
                concept_board_codes=list(dict.fromkeys(inherited_codes)),
                concept_board_names=[normalized_name],
                board_code_mappings=inherited_mappings,
            )
        if strategy_mode:
            theme.signal_rules.strategy_mode = strategy_mode
        themes.append(theme)
    return themes


def apply_strategy_mode(
    themes: Iterable[ThemeDefinitionSchema],
    strategy_mode: str,
) -> List[ThemeDefinitionSchema]:
    if not strategy_mode:
        return list(themes)

    adjusted: List[ThemeDefinitionSchema] = []
    for theme in themes:
        copied = theme.model_copy(deep=True)
        copied.signal_rules.strategy_mode = strategy_mode
        adjusted.append(copied)
    return adjusted


def run_direct_board_replay(
    pipeline: ThemeAlertPipeline,
    direct_themes: List[ThemeDefinitionSchema],
    *,
    days: int,
    max_expanded_candidates: int,
) -> ThemeAlertResultSchema:
    result = ThemeAlertResultSchema(scanned_theme_ids=[theme.id for theme in direct_themes])
    for theme in direct_themes:
        if theme.concept_board_codes:
            target = ",".join(theme.concept_board_codes)
            reason = f"用户直接指定板块代码: {target}"
        else:
            target = ",".join(theme.concept_board_names)
            reason = f"用户直接指定板块名称: {target}"
        event = ThemeEventSchema(
            theme_id=theme.id,
            theme_name=theme.name,
            event_score=100,
            triggered=True,
            trigger_reason=reason,
            matched_keywords=[],
            matched_news_count=0,
            news_items=[],
        )
        result.events.append(event)
        stock_pool = pipeline.stock_pool_service.get_stock_pool(theme)
        candidate_pool = pipeline.expansion_service.expand_theme(
            theme,
            event,
            stock_pool,
            days=days,
            max_candidates=max_expanded_candidates,
        )
        signals = pipeline.signal_service.evaluate_theme(theme, event, candidate_pool)
        result.signals.extend(signals)
    return result


def print_summary(result) -> None:
    print("=== Theme Alert Summary ===")
    print("scanned_themes:", len(result.scanned_theme_ids))
    print("events:", len(result.events))
    print("signals:", len(result.signals))
    print("")

    if result.events:
        print("=== Events ===")
        for event in result.events:
            status = "TRIGGERED" if event.triggered else "SKIPPED"
            print(
                f"- [{status}] {event.theme_name} ({event.theme_id}) "
                f"score={event.event_score} news={event.matched_news_count} "
                f"keywords={','.join(event.matched_keywords) or '-'}"
            )
            print(f"  reason: {event.trigger_reason}")
        print("")

    if result.signals:
        print("=== Signals ===")
        for signal in result.signals:
            print(
                f"- {signal.theme_name} | {signal.stock_code} {signal.stock_name or ''} "
                f"| {signal.signal_level}"
            )
            print(
                "  metrics: "
                f"pct_chg={signal.metrics.get('pct_chg')} "
                f"volume_ratio={signal.metrics.get('volume_ratio')} "
                f"bias_ma5={signal.metrics.get('bias_ma5')} "
                f"resonance={signal.metrics.get('resonance_count')}"
            )
            for reason in signal.reasons:
                print(f"  reason: {reason}")


def main() -> int:
    args = parse_args()
    setup_env()
    setup_logging(debug=args.debug, log_dir=get_config().log_dir)

    pipeline = build_pipeline()
    registry_service = ThemeRegistryService()
    direct_board_themes = build_direct_board_themes(
        parse_csv_values(args.board_code),
        parse_csv_values(args.board_name),
        registry_service=registry_service,
        strategy_mode=args.strategy_mode,
    )
    if direct_board_themes:
        result = run_direct_board_replay(
            pipeline,
            direct_board_themes,
            days=args.days,
            max_expanded_candidates=args.max_expanded_candidates,
        )
    else:
        theme_ids = parse_theme_ids(args.themes)
        extra_themes = None
        effective_theme_ids = theme_ids or None
        if args.strategy_mode:
            if theme_ids:
                selected = [
                    theme
                    for theme_id in theme_ids
                    for theme in [registry_service.get_theme(theme_id)]
                    if theme is not None and theme.enabled
                ]
            else:
                selected = registry_service.list_themes(enabled_only=True)
            extra_themes = apply_strategy_mode(selected, args.strategy_mode)
            effective_theme_ids = []
        result = pipeline.run(
            theme_ids=effective_theme_ids,
            extra_themes=extra_themes,
            days=args.days,
            max_results_per_keyword=args.max_results_per_keyword,
            max_expanded_candidates=args.max_expanded_candidates,
            triggered_only=not args.include_untriggered,
        )

    if args.json:
        print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2, default=str))
    else:
        print_summary(result)

    return 0


if __name__ == "__main__":
    sys.exit(main())
