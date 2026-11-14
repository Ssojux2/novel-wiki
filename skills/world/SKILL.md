---
name: world
description: SF 세계관을 설계해 바이블의 rules/tech/factions/places 페이지로 만든다. One Big Lie, 기술의 능력·한계·비용, 연쇄 효과, 제도를 다룬다.
argument-hint: "[주제: 예) 차폐막 기술, 본사 조직]"
---

세계관 설계. 인자: $ARGUMENTS

`novel-wiki:world-architect` 에이전트에 맡긴다. 이 대화는 작가와의 질문·답을 중계한다.

## 절차
1. `PLUGIN` = 이 스킬 Base directory의 `../..`. 프로젝트 절대 경로를 확인한다.
2. 에이전트를 호출한다:
   ```
   Agent(subagent_type: "novel-wiki:world-architect",
         prompt: "PLUGIN=<경로>, PROJECT=<경로>. 주제: <인자 또는 '전체 세계관 1차 설계'>.
                  작가 답변: <지금까지 받은 답>. 질문이 필요하면 질문만 반환하라.")
   ```
3. 에이전트가 질문을 반환하면 작가에게 그대로 묻고, 답을 붙여 다시 호출한다 (`SendMessage`로 이어가도 된다).
4. 페이지가 만들어지면 결과를 요약해 보여준다: One Big Lie 한 문장, 새 페이지 목록, 플롯 압력 후보(★).

## 주의
- 아직 원고에 없는 설정은 `status: planned`로 둔다. 원고에 등장하면 ingest가 상태 표를 채운다.
- 수치는 근거를 남긴다. 외삽은 외삽이라고 표시한다.
