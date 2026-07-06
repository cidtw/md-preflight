# Design References

[`VoltAgent/awesome-design-md`](https://github.com/VoltAgent/awesome-design-md) 컬렉션에서
MD Preflight UI에 관련성이 높은 브랜드 `DESIGN.md`를 사본으로 보관한다.
프로젝트 루트의 합성 결과물 [`../../DESIGN.md`](../../DESIGN.md)가 정본이고,
이 폴더는 그 근거가 된 **원본 참고 자료**다.

| 파일 | 무엇을 참고했나 |
|---|---|
| `vercel.DESIGN.md` | near-white ink-on-white 팔레트, 파랑 단일 액센트, 시맨틱 색(error/warning), Geist 타이포 |
| `linear_app.DESIGN.md` | 조밀한 hairline·surface 위계, 음수 트래킹, "그림자 대신 톤" 깊이, 프로덕트 밀도 (라이트로 이식) |
| `sentry.DESIGN.md` | 이슈·심각도 중심 리스트 UI 패턴 — severity 색 코딩·좌측 accent bar |
| `stripe.DESIGN.md` | 금액·수치·표 신뢰 표현 (마진/가격 데이터 참고) |
| `supabase.DESIGN.md` | 개발자 대시보드 데이터 밀도·테이블 참고 |

## 다른 브랜드가 필요하면

컬렉션 전체(74개)는 워크스페이스에 클론되어 있다:

```
../../../../awesome-design-md/design-md/<brand>/DESIGN.md   # workspace/awesome-design-md
```

필요한 브랜드를 이 폴더로 복사한 뒤 루트 `DESIGN.md`의 `## Sources & References`에 근거를 남긴다.
