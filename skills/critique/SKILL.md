---
name: critique
description: 완성된 원고(또는 1부·2부 같은 큰 단위)를 문예 비평 수준으로 평가한다. 구조, 인물 아크, 주제, SF 아이디어의 인간화, 복선 경제, 문장을 보고 개고 우선순위를 낸다.
argument-hint: "[범위]"
---

전체 비평. 인자: $ARGUMENTS (없으면 원고 전체)

## 준비
1. 미반영 장이 있으면 먼저 ingest한다. 비평가는 장 요약으로 구조를 파악하기 때문이다.
2. `PLUGIN` = 이 스킬 Base directory의 `../..`. 기계 자료를 미리 만든다:
   ```bash
   python3 PLUGIN/scripts/lint_bible.py --project .
   python3 PLUGIN/scripts/deslop_ko.py manuscript/*.md --json > reviews/deslop-all.json
   ```

## 호출
```
Agent(subagent_type: "novel-wiki:sf-critic",
      prompt: "PLUGIN=<경로>, PROJECT=<경로>. 범위: <…>.
               참고 자료: reviews/lint-<날짜>.md, reviews/deslop-all.json")
```

## 결과
비평 에세이의 핵심 주장, 강점 3, 약점 3, 개고 우선순위 5를 보여준다. 이어서 묻는다: "개고 1순위부터 아웃라인을 다시 잡을까요?" → `/novel-wiki:outline`
