# Kakao Local API로 정확한 위치 · POI 구축 가이드

Google Maps를 제거하고 **카카오 로컬 REST API**로 주소 좌표 변환 + 주변 유동 유발 시설(POI) 조회를 합니다.

## 1. 카카오 개발자 콘솔 설정

1. [Kakao Developers](https://developers.kakao.com/) 로그인  
2. **내 애플리케이션** → **애플리케이션 추가하기**  
3. 앱 선택 → **앱 키** 탭 → **REST API 키** 복사  
4. (권장) **제품 설정**에서 사용 API 확인 — Local은 REST 키로 호출  
5. 키 보안: REST 키는 **서버 전용**. 프론트에 넣지 말 것  

> 브라우저 JavaScript 키가 아니라 **REST API 키**가 필요합니다.

## 2. 로컬 환경 변수

`.env.local` (gitignore 됨):

```bash
KAKAO_REST_API_KEY=여기에_REST_API_키
# 또는
MDPREFLIGHT_KAKAO_REST_API_KEY=여기에_REST_API_키

# 선택: 반경(m), 기본 500
MDPREFLIGHT_GEO_RADIUS_M=500
```

```bash
uv run uvicorn app.main:app --reload --port 8000
```

## 3. Vercel 환경 변수

Project **md-preflight** → Settings → Environment Variables:

| Name | Environment |
|------|-------------|
| `KAKAO_REST_API_KEY` | Production (필요 시 Preview) |

추가 후 **Redeploy** 필수 (기존 배포는 옛 env를 씀).

```bash
vercel env add KAKAO_REST_API_KEY production
vercel deploy --prod --yes
```

## 4. 호출 흐름 (코드)

```
store_address
    │
    ▼
GET /v2/local/search/address.json     ← 좌표 (x=경도, y=위도)
    │
    ├─ GET /v2/local/search/category.json  (SW8 지하철, MT1 마트, SC4 학교 …)
    └─ GET /v2/local/search/keyword.json   (query=버스정류장)
    │
    ▼
foot_traffic_index = Σ w(cat)*exp(-d/250) / 4   → [0,1]
    │
    ▼
safety_z += 0.35 * foot_traffic_index
```

구현 파일: `app/pipeline/analyze/geo_enrichment.py`  
설정: `app/core/config.py` → `kakao_rest_api_key`

### 카테고리 매핑

| Kakao code | 의미 | 내부 category |
|------------|------|----------------|
| SW8 | 지하철역 | transit_rail |
| (keyword) 버스정류장 | 버스 | transit_bus |
| MT1 / CS2 | 대형마트 / 편의점 | retail_anchor |
| SC4 / AC5 | 학교 / 학원 | education |
| AT4 / CT1 | 관광명소 / 문화시설 | landmark |
| PO3 / BK9 | 공공기관 / 은행 | office |

## 5. 실패 시 동작

| 상황 | 결과 |
|------|------|
| 키 없음 | fallback, 행정동 점수만, HTTP 200 |
| 주소 0건 | fallback + guidance |
| 주변 검색 실패 | 좌표만 있을 수 있음, index=0 |
| 체크 안 함 | geo 비활성, 기존 파이프라인 |

## 6. 스모크 테스트

```bash
curl -s -X POST http://127.0.0.1:8000/api/evaluate \
  -H 'content-type: application/json' \
  -d '{
    "parameters": {
      "product_name": "냉장 간편식",
      "store_type": "convenience",
      "store_size": "cv_s",
      "avg_ticket": "t_le_8k",
      "location_dong": "서울시 마포구 서교동",
      "use_precise_location": true,
      "store_address": "서울시 마포구 양화로 45",
      "trade_area": "office",
      "accessibility": "indoor",
      "daily_demand": 12,
      "standard_lead_time_days": 2,
      "standard_rop": 15
    }
  }' | jq '.calc.geo | {provider, used_fallback, foot_traffic_index, pois: (.pois|length), notes}'
```

성공 예:

```json
{
  "provider": "kakao",
  "used_fallback": false,
  "foot_traffic_index": 0.42,
  "pois": 12
}
```

## 7. Google에서 이전 체크리스트

- [ ] Vercel에서 `GOOGLE_MAPS_API_KEY` 제거(선택)  
- [ ] `KAKAO_REST_API_KEY` Production 등록  
- [ ] 재배포  
- [ ] UI: 세부 정보 → 정확한 위치 사용 → 도로명 주소 → 분석  
- [ ] 결과 근거에 **Kakao Local** 블록·POI 목록 확인  

## 8. 참고 링크

- [로컬 REST API 가이드](https://developers.kakao.com/docs/latest/ko/local/dev-guide)  
- [카테고리 검색](https://developers.kakao.com/docs/latest/ko/local/dev-guide#search-by-category)  
- [키워드 검색](https://developers.kakao.com/docs/latest/ko/local/dev-guide#search-by-keyword)  
