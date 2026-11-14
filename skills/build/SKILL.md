---
name: build
description: manuscript/의 장 파일을 한 권의 Word(.docx) 원고로 합본한다. 공모전·투고용(contest), 읽기용(reading), 검토·인쇄용(review) 프리셋과 원고지 매수 추정, 빌드 전 점검(연속성·AI 티·작업 표시)을 제공한다.
argument-hint: "[contest|reading|review] [범위 1-10] [--strict]"
---

docx 합본. 인자: $ARGUMENTS (기본: contest, 전체 장)

## 최종본은 어디서 나오나
- 원고 `manuscript/chNN.md`가 정본이다. 퇴고(review 적용, deslop 수정)도 이 파일들을 직접 고친다.
- 이 명령은 그 파일들을 장 순서대로 묶어 `builds/YYYY-MM-DD/제목-프리셋.docx`를 만든다. 바이블, 아웃라인, 리포트는 들어가지 않는다.
- docx는 결과물일 뿐이다. 수정은 항상 `manuscript/`에서 하고 다시 빌드한다. docx에서 고치면 다음 빌드 때 덮어써진다.

## 실행
`PLUGIN` = 이 스킬 Base directory의 `../..`
```bash
python3 PLUGIN/scripts/build_docx.py --project . --preset <프리셋> [--from N --to M] [--author "필명"] [--strict]
```
Python 표준 라이브러리만 쓴다. Word, pandoc, python-docx가 없어도 된다.

| 프리셋 | 용도 | 판형 | 글자 | 줄간격 |
|---|---|---|---|---|
| `contest` | 공모전·투고 | A4 | 11pt | 160% |
| `reading` | 읽기용 (단행본 느낌) | 신국판 152×225mm | 10.5pt | 170% |
| `review` | 검토·인쇄·첨삭 | A4, 넓은 여백 | 11pt | 200%, 머리글에 빌드 날짜 |

연재 회차 공개본: `--from N --to N --preset reading --no-title-page --txt` → 플랫폼에 붙여 넣을 `.txt`도 함께 생긴다.

세부 조정: `--font "함초롬바탕"`, `--size 10`, `--spacing 180`, `--chapter-label "제{n}장"`, `--no-title-page`, `--title`, `--out 경로.docx`

## 빌드 전 점검 (기본으로 켜짐)
- 연속성 경고 (lint 경고급)
- AI 티 점수 70 미만인 장
- 원고에 남은 `TODO`, `TK`, `???` 표시

점검은 알려주기만 하고 빌드는 진행한다. `--strict`를 주면 문제가 있을 때 빌드를 멈춘다. **공모전 제출본은 `--strict`로 빌드하기를 권한다.**

## 원고 작성 규칙 (빌드 품질에 영향)
- 첫 줄 `# 장 제목`은 장 제목이 된다. 없으면 `--chapter-label` 형식(기본 "N장")을 쓴다.
- 장면 구분은 단독 줄 `* * *`. 가운데 정렬로 변환된다.
- 문단은 빈 줄로 나눈다. 문단 안의 줄바꿈은 이어 붙여진다.
- `**굵게**`, `*기울임*`이 반영된다. `<!-- 주석 -->`, `%% 메모 %%`, `[[링크]]` 표시는 지워진다.

## 빌드 후
- 함께 생성되는 `.build.md`에 수록 장, 분량, 원고지 매수(공백 포함 글자 수 ÷ 200, 추정치), 점검 결과가 남는다.
- 원고지 매수는 추정치다. 공모전마다 세는 기준(공백 포함 여부, 200자 원고지 칸 규칙)이 다르니 요강을 확인하라고 안내한다.
- 공모전 요강에 글꼴, 크기, 여백 규정이 있으면 옵션으로 맞추고, 그 설정을 `CLAUDE.md`에 적어 두게 한다.
- `bible/_log.md`에 `## [날짜] build | 프리셋 · 범위` 항목을 남긴다.
