---
name: novel-wiki
description: 한국어 장편 소설(특히 SF) 집필을 LLM Wiki 방식으로 돕는 허브 스킬. "N장 써줘", "이어서 써줘", "바이블에 반영해줘", "설정 충돌 찾아줘", "AI 티 빼줘", "세계관 잡아줘", "소설 프로젝트 시작" 같은 요청이나 bible/·manuscript/ 폴더가 있는 프로젝트에서 사용한다.
---

# novel-wiki

LLM Wiki 패턴을 소설에 적용한다: **작가가 원고(canon)를 쓰고, LLM이 원고에서 스토리 바이블을 컴파일한다.** 집필 전에는 바이블에서 그 장에 필요한 것만 "직전 장 끝 시점" 상태로 뽑아 맥락 팩을 만든다.

## 경로
- 이 스킬의 Base directory에서 두 단계 위가 플러그인 루트다 (`<base>/../..`). 아래에서 `PLUGIN`이라 부른다.
- 스크립트: `PLUGIN/scripts/`, 레퍼런스: `PLUGIN/references/`
- 서브에이전트를 부를 때는 프롬프트에 `PLUGIN`과 프로젝트의 **절대 경로**를 꼭 넣는다.

## 명령
| 명령 | 단계 | 하는 일 |
|---|---|---|
| `/novel-wiki:init` | 시작 | 프로젝트 폴더·바이블·CLAUDE.md 생성 |
| `/novel-wiki:go` | 세션 시작 | 현황 로드 + 다음 할 일 하나 추천 |
| `/novel-wiki:weekly N` | 연재 | 한 회차 전체 루틴: 이전 회차 참조 검토 → 같은 파일 다듬기(스냅샷) → 확정·ingest → 공개본 docx·txt |
| `/novel-wiki:plan` | 설계 | 전제·주제·결말·One Big Lie (소크라테스식 문답) |
| `/novel-wiki:world` | 설계 | SF 세계관 → rules/tech/factions/places |
| `/novel-wiki:outline` | 설계 | 장별 비트 + 복선 배치 |
| `/novel-wiki:pack N` | Query | N장 맥락 팩 생성 |
| `/novel-wiki:write N` | 집필 | 브레인스톰 → 선별 → 초고 |
| `/novel-wiki:ingest N` | Ingest | 원고를 바이블에 컴파일 |
| `/novel-wiki:review N` | 퇴고 | 장 리뷰 (발전·라인·인물·연속성) |
| `/novel-wiki:lint` | Lint | 연속성 검사 (기계 + 판단) |
| `/novel-wiki:breath N` | 퇴고 | 문장 호흡 측정, 일곱 묘사 모드로 장문화 (`setup`으로 프로필 설정) |
| `/novel-wiki:deslop N` | 퇴고 | 한국어 AI 티·문장 감사/수정 |
| `/novel-wiki:critique` | 완성 | 원고 전체 비평 |
| `/novel-wiki:build` | 출판 | manuscript/를 한 권의 .docx로 합본 (공모전·읽기·검토 프리셋) |

## 주간 연재 루프 (한 회차 = 한 파일)
```
작가가 manuscript/chNN.md 작성 → /novel-wiki:weekly N
  스냅샷(원고) → 이전 회차 기반 검토 → review 적용 → breath → deslop (단계마다 스냅샷)
  → 변경 내역 확인 → 확정 → ingest → 공개본 → 연재 기록
```
같은 파일을 고치지만 `reviews/snapshots/chNN/`에 단계별 사본이 쌓이므로 언제든 비교(`diff`)하고 되돌릴(`restore`) 수 있다.

## 집필 루프
```
go → pack N → write N → (작가 수정) → ingest N → review N → 고쳐쓰기 → breath N → deslop N
                                         └ 5장마다 lint
완성 → critique → 개고 → build (docx)
```
- **최종본 = `manuscript/`**. 바이블·아웃라인·리포트는 작업 도구일 뿐 책에 들어가지 않는다. `build`는 원고를 묶어 docx를 만들 뿐이니, 수정은 항상 원고에서 하고 다시 빌드한다.
- **ingest를 건너뛰지 않는다.** 다음 장의 맥락 팩이 이전 장의 상태 변화에 의존한다.
- 쓰기와 ingest는 장 순서대로 한다. 리뷰·deslop·린트 판단은 장 단위로 병렬 처리할 수 있다.

## 에이전트
| 에이전트 | 용도 | 모델 |
|---|---|---|
| `novel-wiki:writer` | 원고 집필·고쳐쓰기 | opus |
| `novel-wiki:bible-keeper` | ingest | sonnet |
| `novel-wiki:continuity-checker` | 판단 린트 | sonnet |
| `novel-wiki:chapter-reviewer` | 장 리뷰 | sonnet |
| `novel-wiki:stylist` | 호흡·묘사 문체 | opus |
| `novel-wiki:deslop-editor` | AI 티 제거 | sonnet |
| `novel-wiki:world-architect` | SF 세계관 | opus |
| `novel-wiki:sf-critic` | 전체 비평 | opus |

## 자연어 요청 라우팅
- "12장 써줘" → pack 12가 없거나 오래됐으면 먼저 만든 뒤 write 12
- "이 장 반영해줘" / 장을 다 썼다는 말 → ingest
- "서윤이 이 시점에 뭘 알아?" → `state_at.py --at chNN --entity 서윤`으로 답한다 (바이블을 통째로 읽지 않는다)
- "설정 꼬인 데 있어?" → lint
- "문장이 짧다" / "호흡을 길게" / "묘사를 풍부하게" / "문체 바꿔줘" → breath (프로필이 기본값이면 먼저 setup)
- "AI 같아" / "문장 다듬어줘" → deslop
- "이번 주 회차 검토" / "N화 올릴 준비" → weekly
- "원래대로 돌려줘" / "뭐가 바뀌었어?" → `snapshot.py restore` / `snapshot.py diff`
- "최종본 뽑아줘" / "공모전 제출용 파일" / "워드로" → build
- 바이블에 대한 질문 → `bible/_index.md`부터 읽고 필요한 페이지만 연다. 가치 있는 답은 `bible/arcs/`나 해당 페이지에 저장할지 제안한다 (위키의 Query → 축적)

## 레퍼런스
`craft-core.md` 작법 · `bible-schema.md` 데이터 형식과 ingest 절차 · `sf-worldbuilding.md` SF 세계관 · `continuity-checklist.md` 연속성 · `review-rubric.md` 리뷰 · `korean-ai-isms.md` AI 티 · `prose-breath.md` 호흡과 묘사 문체

## 세션 연속성
- 시작: 플러그인의 SessionStart 훅이 현황을 넣어 준다. 자세한 상태는 `/novel-wiki:go`로 본다.
- 끝: `sessions/YYYY-MM-DD_주제.md`에 2~5문장(무엇을 했고, 무엇을 정했고, 어디서 멈췄는지)을 남기고, `bible/_log.md`에 기록한다.
