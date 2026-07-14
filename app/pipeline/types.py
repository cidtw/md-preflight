"""Shared contracts: input template → ROP analysis → recommendation report."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ParamType = Literal["number", "string", "boolean"]
ParameterValue = str | int | float | bool


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


class KnowledgeSignals(BaseModel):
    """Deterministic KB match results (Agent-AI-shaped, no live LLM required)."""

    logistics_delay_days: float
    safety_z_factor: float
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


class StoreSummary(BaseModel):
    product_name: str
    store_type_label: str
    store_size_label: str
    avg_ticket_label: str
    location_dong: str
    trade_area_label: str
    accessibility_label: str


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
