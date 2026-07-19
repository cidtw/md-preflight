"""Demo store catalog for presentation builds.

Primary source: Kakao census around the home anchor
(경기도 고양시 덕양구 세솔로 25) — see demo_anchor_survey.py.

Falls back to on-disk snapshot (data/demo_anchor_survey.json) when the API
key is missing. Yeoksam hardcoded profiles are retired.
"""

# pyright: reportAny=false, reportUnknownVariableType=false, reportUnknownArgumentType=false

from __future__ import annotations

from typing import cast

from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.pipeline.demo_anchor_survey import (
    DEFAULT_ANCHOR_ADDRESS,
    load_survey_snapshot,
    survey_anchor_stores,
    surveyed_to_demo_cards,
)
from app.pipeline.types import ParameterValue


class VerifiedDemoStore(BaseModel):
    """One store profile shown as a first-class demo target."""

    id: str
    title: str
    store_label: str
    blurb: str
    highlight: str
    verification_note: str
    expected: dict[str, ParameterValue] = Field(default_factory=dict)
    parameters: dict[str, ParameterValue]
    channel: str = ""
    distance_m: float = 0.0
    foot_traffic_index: float = 0.0


def _as_param_dict(raw: object) -> dict[str, ParameterValue]:
    out: dict[str, ParameterValue] = {}
    if not isinstance(raw, dict):
        return out
    mapping = cast(dict[object, object], raw)
    for key_obj, value in mapping.items():
        key = str(key_obj)
        if isinstance(value, (str, int, float, bool)):
            out[key] = value
    return out


def _as_float_field(raw: object, default: float = 0.0) -> float:
    if isinstance(raw, bool):
        return default
    if isinstance(raw, (int, float)):
        return float(raw)
    return default


def _cards_to_models(cards: list[dict[str, object]]) -> list[VerifiedDemoStore]:
    out: list[VerifiedDemoStore] = []
    for card in cards:
        params = _as_param_dict(card.get("parameters"))
        expected = _as_param_dict(card.get("expected"))
        out.append(
            VerifiedDemoStore(
                id=str(card.get("id") or ""),
                title=str(card.get("title") or ""),
                store_label=str(card.get("storeLabel") or card.get("store_label") or ""),
                blurb=str(card.get("blurb") or ""),
                highlight=str(card.get("highlight") or ""),
                verification_note=str(
                    card.get("verificationNote") or card.get("verification_note") or "",
                ),
                expected=expected,
                parameters=params,
                channel=str(card.get("channel") or ""),
                distance_m=_as_float_field(card.get("distance_m")),
                foot_traffic_index=_as_float_field(card.get("foot_traffic_index")),
            ),
        )
    return [s for s in out if s.id and s.parameters]


def list_verified_demo_stores(*, live: bool = False) -> list[VerifiedDemoStore]:
    """Return census-based demo stores.

    Default uses on-disk snapshot (fast UI). Pass live=True to re-query Kakao
    (slow; use survey-anchor endpoint for full refresh).
    """
    if not live:
        snap = load_survey_snapshot()
        if snap is not None and snap.stores:
            return _cards_to_models(surveyed_to_demo_cards(snap))
    settings = get_settings()
    key = settings.kakao_rest_api_key
    if key:
        result = survey_anchor_stores(api_key=key, anchor_address=DEFAULT_ANCHOR_ADDRESS)
        if result.stores:
            return _cards_to_models(surveyed_to_demo_cards(result))
    snap = load_survey_snapshot()
    if snap is not None and snap.stores:
        return _cards_to_models(surveyed_to_demo_cards(snap))
    return []


def get_verified_demo_store(store_id: str) -> VerifiedDemoStore | None:
    sid = store_id.strip()
    if not sid:
        return None
    for store in list_verified_demo_stores(live=False):
        if store.id == sid:
            return store
    return None
