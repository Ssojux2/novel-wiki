---
name: lint
description: 원고와 바이블의 연속성을 검사한다. 기계 린트(깨진 링크, 사망 인물 재등장, 시간 역행, 기한 지난 복선, 고유명사 표기)와 판단 린트(지식 상태·세계 규칙·부상·이동 시간 위반)를 함께 수행한다.
argument-hint: "[범위: 예) 1-10] [--quick]"
---

연속성 검사 (LLM Wiki의 Lint). 인자: $ARGUMENTS

## --quick: 기계 린트만
`PLUGIN` = 이 스킬 Base directory의 `../..`
```bash
python3 PLUGIN/scripts/lint_bible.py --project .
```
`reviews/lint-YYYY-MM-DD.md`가 생긴다. 경고부터 요약해서 보여준다.

## 기본: 기계 + 판단
```
Agent(subagent_type: "novel-wiki:continuity-checker",
      prompt: "PLUGIN=<경로>, PROJECT=<경로>. 범위: <인자 또는 전체>.")
```
장이 많으면(15장 이상) 범위를 5장씩 나눠 continuity-checker를 **병렬로** 호출하고, 결과 리포트들을 하나로 합친다. 단, 장 경계를 넘는 모순(예: 3장에서 다친 팔이 9장에서 멀쩡함)을 놓치지 않도록 상태표 기반 검사는 각 에이전트가 전체 바이블을 기준으로 하게 한다.

## 결과 처리
보고 후 항목별로 처리 방향을 작가와 정한다:
- **원고를 고친다** → writer에게 Edit 지시 → 해당 장 재-ingest
- **바이블을 고친다** → bible-keeper에게 지시
- **의도된 것이다** → 해당 바이블 페이지에 `> 의도: …` 메모를 남겨 다음 린트에서 같은 지적이 반복되지 않게 한다

`_log.md`에 `lint` 항목과 처리 결과를 남긴다. 집필 중에는 5장마다 실행하기를 권한다.
