---
name: review
description: 장을 리뷰한다. 목적 달성, 장면 경제, 속도, 인물 목소리, 연속성, SF 논리를 보고 고쳐쓰기를 제안한다. 여러 장은 병렬로 리뷰한다.
argument-hint: "[장 번호 | 범위 3-7 | all]"
---

장 리뷰. 인자: $ARGUMENTS (없으면 가장 최근에 수정한 장)

## 단일 장
1. `PLUGIN` = 이 스킬 Base directory의 `../..`. `packs/chNN.md`가 없으면 먼저 만든다 (`context_pack.py --chapter N`).
2. 호출:
   ```
   Agent(subagent_type: "novel-wiki:chapter-reviewer",
         prompt: "PLUGIN=<경로>, PROJECT=<경로>. chNN 리뷰. 작가가 특히 걱정하는 점: <있으면>")
   ```
3. 판정과 상위 항목을 보여주고 묻는다: "어떤 제안을 적용할까요? (번호 선택 / 전부 / 직접 고칠게요)"
4. 적용은 writer 에이전트에게 Edit로 맡긴다. 플롯이나 설정이 바뀌는 수정이면 적용 후 재-ingest를 안내한다.

## 여러 장 (`all`, 범위)
- 각 장의 팩을 먼저 만든다 (스크립트라 빠르다).
- chapter-reviewer를 **장마다 병렬로** 호출한다 (한 메시지에 여러 Agent 호출). 리뷰는 읽기만 하므로 순서와 무관하다.
- 결과를 모아 `reviews/review-summary-YYYY-MM-DD.md`에 표로 정리한다: 장 | 판정 | 상위 문제 | 리포트 경로. 여러 장에 반복되는 패턴(예: 매 장 끝 경구, 중반 속도 처짐)을 따로 뽑는다.
