"""Shared contracts: input template → ROP analysis → recommendation report."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ParamType = Literal["number", "string", "boolean"]
ParameterValue = str | int | float | bool
PoiCategory = Literal[
    "transit_rail",
    "transit_bus",
    "landmark",
    "education",
    "office",
    "retail_anchor",
    "other",
]


class ParameterOption(BaseModel):
    value: str
    label: str


class ParameterSpec(BaseModel):
    """One field in the public input template."""

    key: str
    label: str
    type: ParamType
    required: bool = True
    description: str = ""
    minimum: float | None = None
    maximum: float | None = None
    options: list[ParameterOption] | None = None
    allowed_values: list[str] | None = None


class InputTemplate(BaseModel):
    id: str
    title: str
    description: str
    version: str
    parameters: list[ParameterSpec]


class ValidatedInput(BaseModel):
    template_id: str
    template_version: str
    parameters: dict[str, ParameterValue]
    guidance: list[str] = Field(default_factory=list)


class ScoreBreakdown(BaseModel):
    capa_score: int
    demand_concentration: int
    turnover_weight: float
    supply_difficulty: int
    demand_volatility: int
    accessibility_lt_delta_days: float


class NearbyPoi(BaseModel):
    category: PoiCategory
    name: str
    distance_m: float


class GeoEnrichment(BaseModel):
    """Map-API enrichment for precise store address (Kakao Local)."""

    enabled: bool = False
    lat: float | None = None
    lng: float | None = None
    pois: list[NearbyPoi] = Field(default_factory=list)
    foot_traffic_index: float = Field(default=0.0, ge=0.0, le=1.0)
    provider: str = "none"
    used_fallback: bool = True
    notes: list[str] = Field(default_factory=list)
    address_queried: str | None = None
    radius_m: int = 500


class KnowledgeSignals(BaseModel):
    """Deterministic KB match results (Agent-AI-shaped, no live LLM required)."""

    logistics_delay_days: float
    safety_z_factor: float
    safety_z_base: float = 0.0
    foot_traffic_index: float = 0.0
    foot_traffic_peak_note: str
    logistics_issue_note: str
    demand_risk_note: str
    search_query: str


class CalcBreakdown(BaseModel):
    standard_lead_time_days: float
    recommended_lead_time_days: float
    lead_time_delta_days: float
    standard_rop: float
    recommended_rop: float
    rop_delta: float
    daily_demand: float
    base_safety_stock: float
    store_safety_stock: float
    recommended_rop_raw: float
    capa_capped: bool
    max_rop_cap: float | None = None
    multi_order_suggestion: str | None = None
    scores: ScoreBreakdown
    knowledge: KnowledgeSignals
    geo: GeoEnrichment = Field(default_factory=GeoEnrichment)


class StoreSummary(BaseModel):
    product_name: str
    store_type_label: str
    store_size_label: str
    avg_ticket_label: str
    location_dong: str
    trade_area_label: str
    accessibility_label: str
    use_precise_location: bool = False
    store_address: str | None = None


class ComparisonRow(BaseModel):
    metric: str
    standard_value: float
    recommended_value: float
    delta: float
    unit: str
    delta_label: str


class ComparisonDashboard(BaseModel):
    rows: list[ComparisonRow]
    rop_guidance: str


class EvidenceBlock(BaseModel):
    id: str
    title: str
    calc_summary: str
    points: list[str]


class RecommendationResult(BaseModel):
    """Full output-stage payload for the ROP redesign service."""

    recommendation: str
    template_id: str
    template_version: str
    guidance: list[str] = Field(default_factory=list)
    summary: StoreSummary
    comparison: ComparisonDashboard
    evidence: list[EvidenceBlock]
    calc: CalcBreakdown
