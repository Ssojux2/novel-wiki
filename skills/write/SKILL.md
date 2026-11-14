---
name: write
description: 맥락 팩을 바탕으로 N장(또는 장면)을 쓴다. 비트 브레인스톰 → 작가 선별 → writer 에이전트 초고 → 새 설정 확인 순서로 진행한다.
argument-hint: "<장 번호> [장면 번호] [--fast]"
---

집필. 인자: $ARGUMENTS

author-toolkit fiction-workshop의 브레인스톰 → 선별 → 초고 → 다듬기 사이클과 howells/fiction의 writer 에이전트를 결합했다.

## 0. 준비
- `PLUGIN` = 이 스킬 Base directory의 `../..`, 프로젝트 절대 경로 확인
- 직전 장이 ingest됐는지 확인한다 (`bible/chapters/ch(N-1).md` 존재). 없으면 먼저 ingest를 권한다.
- `packs/chNN.md`가 없거나 바이블보다 오래됐으면 `context_pack.py`를 실행한다.
- 팩을 읽는다.

## 1. 브레인스톰 (`--fast`면 생략)
장면별로 비트 후보 5~10개를 짧은 한 줄씩 제시한다: 도입 훅, 핵심 순간, 대사 한 줄, 감각 디테일, 마무리 이미지. SF 장면이면 "기술의 실패 모드가 만드는 순간"을 하나 이상 넣는다.
→ 작가에게 묻는다: "어떤 걸 살리고, 합치고, 버릴까요?"

## 2. 초고
```
Agent(subagent_type: "novel-wiki:writer",
      prompt: "PLUGIN=<경로>, PROJECT=<경로>. chNN [장면 S] 집필.
               맥락 팩: packs/chNN.md. 선택된 비트: <목록>. 작가 메모: <있으면>.
               목표 분량: <있으면>.")
```
장 전체는 장면 순서대로 쓰므로 병렬로 쪼개지 않는다.

## 3. 반환 확인
- writer의 **새 설정 후보**를 작가에게 보여주고 하나씩 승인/수정/삭제를 받는다. 승인된 것은 ingest 때 바이블에 들어간다. 거절된 것은 writer에게 Edit로 고치게 한다.
- 작가에게 물을 것이 있으면 전달한다.

## 4. 다듬기
작가 피드백 → writer에게 Edit 지시 (전체 재작성 금지). 거의 바뀌지 않는 패스가 3번 이어지면 "무엇을 덜어낼까요?"를 묻는다.

## 5. 마무리 안내
작가가 장을 확정하면 → `/novel-wiki:ingest N` → `/novel-wiki:review N`
