# Archive Notice — md-preflight / 발주맞춤 · OrderFit

| 항목 | 값 |
|------|-----|
| **상태** | **ARCHIVED** (공식 마감) |
| **마감일** | **2026-07-22** |
| **기간** | 2026-07-02 ~ 2026-07-22 |
| **가시성** | GitHub **public** archive |
| **레포** | https://github.com/cidtw/md-preflight |
| **제품명** | 발주맞춤 · OrderFit |
| **시연 (참고)** | https://baljumatch.vercel.app |

## 무엇을 동결하는가

1. **v1** — 프로모션/MD 사전검수 UI (`archive/v1-md-preflight/`, tag `archive/v1-md-preflight`)
2. **피벗 이후** — 매장 특화 ROP 제품 (브랜치 `pivot/project-direction`)
   - 3단 파이프라인 (input → analyze → output)
   - 발주 레버 (ROP · SS · Q · 서비스 레벨)
   - 시연·발표 자료 · 근거 문서 (`docs/evidence/`, decks)

## 브랜치 정책 (마감 시점)

| 브랜치 | 역할 |
|--------|------|
| `main` | 마감 후 공개 열람용 정본 (피벗 결과 포함, fast-forward) |
| `pivot/project-direction` | 피벗 개발 히스토리 (동일 커밋 라인) |
| tag `archive/v1-md-preflight` | v1 스냅샷 복원용 |

## 하지 않는 것

- 신규 기능·버그픽스·이슈 트래킹
- 운영 SLA / 시연 URL 상시 보장
- 시크릿·로컬 handoff·`.env*` 커밋 (gitignore 유지)

## 복원 (참고)

```bash
git clone https://github.com/cidtw/md-preflight.git
cd md-preflight
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

v1만 보려면:

```bash
git checkout archive/v1-md-preflight
```

---

*Closed 2026-07-22. Public GitHub archive.*
