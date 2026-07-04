# T1 — 미커밋 작업 보존 + 서브모듈 정리

## 우선순위
P0 (최우선). 현재 룰 4개·llm/report 서비스·README 등 핵심 작업물이 **어떤 커밋에도 없이 워킹트리에만** 존재한다. 소실 위험이 있으므로 다른 어떤 티켓보다 먼저 처리한다.

## 배경 (중요 — 오해 금지)
- 정본 = `projects/md-preflight` (standalone clone, remote `github.com/cidtw/md-preflight.git`).
- `projects/antigravity/md-preflight` 는 **다른 프로젝트가 아니라 같은 레포의 git submodule**이며 초기 커밋 `5050e23`에 pin된 stale 상태다.
- 즉 "antigravity가 구버전"인 이유는 정본의 최신 작업이 아직 커밋/푸시되지 않았기 때문이다.
- 따라서 "중복 디렉터리를 옮긴다"는 접근은 **틀렸고 위험하다**(상위 레포의 submodule 참조가 깨진다). 아래 순서대로만 진행한다.

## 범위 파일
- `projects/md-preflight/` (git 작업만; 소스 코드 내용 변경 없음)
- `projects/antigravity/` (submodule 정리 시)

## 작업 단계
### Step 1 — 정본의 미커밋 작업 보존 (필수)
1. `projects/md-preflight`에서 `git status`로 변경/미추적 파일 확인.
2. 논리 단위로 나눠 커밋한다(한 방에 몰지 말 것):
   - 신규 룰: `app/rules/benefit_condition.py`, `app/rules/inbound_date.py`, `app/rules/inventory.py`, `app/rules/margin_rate.py` + `app/rules/__init__.py` + 관련 테스트
   - 서비스: `app/services/llm_service.py`(fallback), `app/services/report_service.py`, `validation_engine.py` 변경
   - 설정: `app/core/rule_config.py`
   - 문서/메타: `README.md`, `AGENTS.md`, `docs/`, `handoff/`
3. 각 커밋 전 검증 3종 통과 확인.
4. `git push origin main` (remote 접근 가능 시). 접근 불가면 핸드오프 노트에 "push 대기"로 명시.

### Step 2 — 서브모듈 정리 (사용자 확인된 방침: archive/정리, 삭제 아님)
antigravity 상위 레포는 별도 워크스페이스다. md-preflight 포트폴리오 작업은 정본에서만 한다는 것을 명확히 한다. 아래 중 **안전한 A안을 기본**으로 하고, 판단이 서면 실행, 애매하면 핸드오프에 옵션만 정리하고 멈춘다.
- **A안 (권장, 비파괴)**: 정본을 push한 뒤, `projects/antigravity`에서 `git submodule update --remote md-preflight`로 submodule 포인터를 최신 커밋으로 전진시킨다. 두 워킹카피가 같은 상태가 되어 "구버전 혼선"이 사라진다.
- **B안**: antigravity 워크스페이스가 이 포트폴리오와 무관하다면, `projects/antigravity`에서 `git submodule deinit md-preflight`로 워킹카피를 비워 혼선 소지를 제거한다(참조는 유지). 상위 레포 커밋 필요.
- **금지**: `projects/antigravity/md-preflight`를 `mv`/`rm`으로 직접 이동·삭제하지 말 것 (submodule 참조 파손).

## 완료 기준
- 정본 `projects/md-preflight`의 워킹트리가 clean(`git status` 깨끗), 모든 핵심 작업이 커밋됨.
- 검증 3종 통과 상태에서 커밋됨.
- antigravity submodule이 A안(포인터 전진) 또는 B안(deinit)으로 정리되었거나, 실행 불가 사유가 핸드오프에 기록됨.

## 테스트 기준
- 커밋 후 정본에서 `uv run pytest` → 17개(또는 그 이상) 통과 유지.
- `git log --oneline`에 논리 단위 커밋들이 남아 있음(초기 커밋 1개만이 아님).

## 가드레일
- 소스 코드 로직을 이 티켓에서 바꾸지 않는다(순수 git 위생 작업).
- force push 금지. 히스토리 재작성 금지.
