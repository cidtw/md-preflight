# ADR 0001: Input adapter → canonical frames (X/Z)

**Status**: Accepted  
**Date**: 2026-07-14  
**Tickets**: T56 (this ADR), T57 (role mapping UI)

## Context

Midterm feedback: promotions of any kind/form should still be refinable for preflight.  
Alpha locked upload UX and judgment language to three fixed slots (promotion / product master / inventory).  
Column aliases (T48) only relax header *names*, not role assignment or multi-file intake.

## Decision

1. **Keep the judgment model** — three **canonical frames** + join + deterministic rules (D3).  
2. **Open the input surface** via an **adapter** that maps arbitrary uploads into those frames.  
3. Do **not** adopt free-form / LLM judgment of arbitrary schemas (option Y).  
4. Evolve via roadmap Z: aliases → **role mapping (T57)** → multi-sheet split → type profiles → channel retrieve.

## Terminology

| Term | Meaning |
|------|---------|
| **Frame** | Internal judgment table: `promotion_plan` · `product_master` · `inventory` |
| **Role** | User-facing assignment of an upload artifact *to* a frame |
| **Mapping** | Confirmed Role→Frame link (plus column alias renames inside a frame) |
| **Adapter** | Ingest-front pipeline: detect → propose → user confirm → build `PreflightContext` |
| **Artifact** | One uploaded file (T57); later a sheet/chunk (T58+) |

## Consequences

- API preflight still consumes three named files after mapping (stable contract for rules).  
- UI allows N artifacts; run is enabled only when each frame has exactly one assigned artifact.  
- Role detection is deterministic (header signature scores), never LLM.  
- Report may later record role mappings for audit (T59); T57 records mapping in session UI first.

## Rejected alternatives

- Dropping frames for dynamic schemas / LLM classification of risk (breaks D3 and rule assets).  
- Soft-requiring only one of three frames (rules and join assume all three).

## Follow-ups

- T57: N-file upload + auto role detect + manual confirm  
- T58: multi-sheet workbook split  
- T59: persist mapping on `PreflightReport`  
- T60: promotion-type profiles (optional fields / rule packs)
