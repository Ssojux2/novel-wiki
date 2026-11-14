---
name: deslop
description: 한국어 소설 원고의 AI 티와 기계적 문장(번역투, LLM 클리셰, 필터어, 반복어, 단조로운 문장 길이, 대사 태그)을 찾아 고친다. 탐지 모드와 수정 모드가 있다.
argument-hint: "<장 번호 | 범위 | all> [detect|rewrite]"
---

AI 티 제거. 인자: $ARGUMENTS (모드 기본값: detect)

author-toolkit의 avoid-ai-writing(탐지/수정 2모드)과 prose-mechanics(결정론적 감사)를 한국어로 다시 만든 것이다.

## 빠른 스캔 (에이전트 없이)
`PLUGIN` = 이 스킬 Base directory의 `../..`
```bash
python3 PLUGIN/scripts/deslop_ko.py manuscript/chNN.md --write
```
점수와 '꼭 고칠 것'을 요약해 보여준다. 작가가 원하면 아래 전체 과정으로 넘어간다.

## 전체 과정
```
Agent(subagent_type: "novel-wiki:deslop-editor",
      prompt: "PLUGIN=<경로>, PROJECT=<경로>. 파일: manuscript/chNN.md. 모드: detect|rewrite")
```
- 여러 장이면 장마다 **병렬로** 호출한다 (장끼리 독립적).
- rewrite 전에 작가에게 확인한다. git이 있으면 커밋 상태를 확인하고, 없으면 수정 전에 `reviews/backup-chNN-날짜.md`로 원본을 복사해 둔다.

## 작가 고유 금지어
자주 쓰는 말버릇을 `reviews/crutch-words.txt`에 한 줄에 하나씩 넣으면 Tier 1로 함께 잡는다. deslop 결과에서 반복되는 단어를 보고 등록을 제안한다.

## 순서 권장
퇴고 순서는 구조(review) → 연속성(lint) → 문장(deslop)이다. 곧 잘려 나갈 장면을 다듬지 않도록 deslop은 마지막에 한다.
