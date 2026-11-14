# novel-wiki

LLM Wiki 패턴을 바탕으로 만든 **한국어 장편 SF 집필 플러그인**입니다. Claude Code용입니다.

> 작가는 원고(canon)를 쓰고, LLM은 원고에서 스토리 바이블을 컴파일합니다.
> 집필 전에는 바이블에서 그 장에 필요한 것만 "직전 장 끝 시점"의 상태로 뽑아 씁니다.

## 설계

### 세 플러그인/패턴에서 가져온 것

| 출처 | 가져온 것 | 버린 것 |
|---|---|---|
| **LLM Wiki v2** (Karpathy 패턴) | raw → wiki → schema 3레이어, Ingest·Query·Lint, `_index`/`_log`, 모순 표기 | 범용 entities/concepts 분류 → 소설용 분류로 교체 |
| **howells/fiction** | 집필 루프(쓰기 → 리뷰 → 수정), 역할별 에이전트, `go`(세션 재개), 장 단위 병렬 처리, 작법 원칙, 연속성 항목, 원고 합본(build) 개념 | EPUB 출력(→ docx로 교체), 표지·제목 생성, 실존 비평가 페르소나, 영문 스타일 가이드 |
| **author-toolkit** | 스토리 바이블을 세션 간 상태로 쓰는 방식, 세션 노트, 브레인스톰 → 선별 → 초고 사이클, 하드 SF 원칙, 지식 상태 추적, 감사 Finding 스키마, AI 티 탐지/수정 2모드 | 논픽션 스킬, 아키타입 분류, 영문 단어 목록 |

### 새로 만든 것
- **시간축 상태 (World Model)**: 인물·장소·세력·기술 페이지마다 `## 상태 변화` 표를 둡니다. 장별 변화분만 적으면 `state_at.py`가 임의의 장 시점 상태를 계산합니다.
- **맥락 팩**: `context_pack.py`가 아웃라인에 등장하는 개체만 골라 직전 장 끝 시점 상태, 관련 규칙, 열린 복선, 직전 장 꼬리를 한 파일로 묶습니다. writer 에이전트는 이 팩만 정본으로 씁니다.
- **대장(ledger)**: `timeline.md`(이야기 내 시각), `threads.md`(복선 심기·회수), `terms.md`(고유명사 정본 표기)
- **기계 린트**: 깨진 링크, 고아 페이지, 미반영 장, 사망 인물 재등장, 시간 역행, 기한 지난 복선, 금지 표기
- **한국어 AI 티 사전**: 번역투, LLM 클리셰("형언할 수 없는", "정적이 흘렀다", "그것은 시작에 불과했다"), 필터어, 주어 대명사 남발, 문장 길이 단조로움, 부사형 대사 태그
- **문장 호흡과 묘사 문체**: 노벨문학상·휴고상 수상작에서 비평가들이 짚어 온 기법을 일곱 모드로 정리했습니다. 장문누적(크러스너호르커이), 반복리듬(포세), 감각정밀(한강), 기억굴절(이시구로), 민족지(르 귄), 이인칭(제미신), 고밀도(깁슨)입니다. 같은 장면을 일곱 모드로 바꿔 쓴 예문을 보고 고를 수 있습니다. `breath_ko.py`가 서술문 평균 길이, 장문 비율, 짧은 문장 연속 구간을 재서 `CLAUDE.md`의 호흡 프로필과 비교하고, stylist 에이전트가 사실은 그대로 두고 문장만 다시 씁니다. 원작 문장은 옮기지 않고 기법만 씁니다.
- **docx 합본**: `build_docx.py`가 표준 라이브러리만으로 Word 파일을 만듭니다 (Word·pandoc 불필요). 공모전·읽기·검토 프리셋, 원고지 매수 추정, 빌드 전 점검(연속성 경고, AI 티 점수, TODO 표시)을 제공합니다.
- **SessionStart 훅**: 소설 프로젝트 폴더에서 세션을 열면 현황(미반영 장, 열린 복선, 지난 세션 노트)이 자동으로 들어옵니다.

### 판단은 LLM, 셈은 스크립트
반복되고 정답이 있는 일(상태 접기, 링크 검사, 패턴 탐지, 맥락 조립)은 Python 스크립트(표준 라이브러리만 사용)가 합니다. 해석이 필요한 일(지식 위반, 규칙 위반, 리뷰, 고쳐쓰기)만 에이전트가 맡습니다. 같은 검사를 매번 LLM이 다시 계산하지 않으니 토큰이 덜 들고 결과도 일정합니다.

## 프로젝트 구조

```
my-novel/
├── CLAUDE.md                 집필 규칙 (시점·시제·문체·소유권)
├── manuscript/ch01.md …      원고 = canon (작가)
├── notes/                    자료조사·메모 = raw (작가)
├── outline/
│   ├── architecture.md       전제·주제·결말·One Big Lie·비트
│   └── chNN.md               장 비트 (frontmatter로 등장 개체·복선 지정)
├── bible/                    스토리 바이블 = wiki (LLM 전용)
│   ├── _overview.md _index.md _log.md
│   ├── characters/ places/ factions/ tech/   ← 상태 변화 표
│   ├── rules/ arcs/ chapters/
│   ├── timeline.md threads.md terms.md
│   └── _templates/
├── packs/                    맥락 팩 (자동 생성)
├── reviews/                  리뷰·린트·deslop 리포트
├── builds/YYYY-MM-DD/        합본 docx (결과물)
└── sessions/                 세션 노트
```

## 명령

| 명령 | 하는 일 |
|---|---|
| `/novel-wiki:init` | 프로젝트 생성 |
| `/novel-wiki:go` | 세션 시작, 다음 할 일 추천 |
| `/novel-wiki:plan` | 전제·주제·결말·One Big Lie 설계 |
| `/novel-wiki:world` | SF 세계관 → rules/tech/factions/places |
| `/novel-wiki:outline` | 장 비트 + 복선 배치 |
| `/novel-wiki:pack N` | N장 맥락 팩 |
| `/novel-wiki:write N` | 브레인스톰 → 선별 → 초고 |
| `/novel-wiki:ingest N` | 원고를 바이블에 컴파일 |
| `/novel-wiki:review N` | 장 리뷰 |
| `/novel-wiki:lint` | 연속성 검사 |
| `/novel-wiki:breath N` | 호흡 측정·장문 묘사로 다시 쓰기 (`setup`으로 프로필) |
| `/novel-wiki:deslop N` | AI 티 감사/수정 |
| `/novel-wiki:critique` | 전체 비평 |
| `/novel-wiki:build` | 원고 → docx 합본 |

## 집필 루프

```
go → pack N → write N → (작가 수정) → ingest N → review N → 고쳐쓰기 → breath N → deslop N
                                         └ 5장마다 lint
완성 → critique → 개고 → build
```

**최종본은 `manuscript/`입니다.** 바이블·아웃라인·리포트는 작업 도구이고 책에 들어가지 않습니다. `/novel-wiki:build`가 원고를 장 순서대로 묶어 `builds/날짜/제목-프리셋.docx`를 만듭니다. 고칠 게 있으면 docx가 아니라 원고를 고치고 다시 빌드합니다.

| 프리셋 | 용도 | 판형 · 글자 · 줄간격 |
|---|---|---|
| `contest` | 공모전·투고 | A4 · 11pt · 160%, 표지에 원고지 매수 |
| `reading` | 읽기용 | 신국판 · 10.5pt · 170% |
| `review` | 검토·인쇄 | A4 넓은 여백 · 11pt · 200%, 머리글에 빌드 날짜 |

## 에이전트

writer(opus) · stylist(opus) · bible-keeper(sonnet) · continuity-checker(sonnet) · chapter-reviewer(sonnet) · deslop-editor(sonnet) · world-architect(opus) · sf-critic(opus)

## 스크립트 단독 사용

```bash
python3 scripts/init_novel.py --path ./my-novel --title "제목"
python3 scripts/state_at.py --project . --at ch10 --entity 한서윤
python3 scripts/state_at.py --project . --at 10 --all
python3 scripts/context_pack.py --project . --chapter 12 --scene 2
python3 scripts/lint_bible.py --project .
python3 scripts/deslop_ko.py manuscript/ch03.md --write
python3 scripts/breath_ko.py manuscript/ch03.md --write
python3 scripts/build_docx.py --project . --preset contest --author "필명" --strict
```

## 설치

```bash
# 로컬
claude --plugin-dir ./novel-wiki

# GitHub에 올린 뒤
/plugin marketplace add Ssojux2/novel-wiki
/plugin install novel-wiki@novel-wiki
```

Python 3.10 이상이 필요합니다. 외부 패키지는 쓰지 않습니다.

## 라이선스
MIT. howells/fiction(MIT), rhavekost/author-toolkit(MIT), conorbronsdon/avoid-ai-writing(MIT)의 구조와 아이디어를 참고했습니다 → [ATTRIBUTION.md](ATTRIBUTION.md)
