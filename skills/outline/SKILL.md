---
name: outline
description: 장별 비트를 만든다. 각 장의 목적, 장면, 등장 인물·장소, 심을 복선과 회수할 복선을 outline/chNN.md에 기록한다.
argument-hint: "[범위: 예) 1-10, 12]"
---

아웃라인 작성. 인자: $ARGUMENTS (없으면 다음 미작성 장부터 5장)

## 읽는다
`outline/architecture.md`(큰 비트), `bible/_overview.md`, `bible/threads.md`, 기존 `outline/chNN.md`, 최근 장 요약 `bible/chapters/`

## 장마다 정한다 (`outline/_chapter-template.md` 형식)
- frontmatter: `pov`, `characters`, `places`, `threads_plant`, `threads_payoff` — **context_pack.py가 이걸로 맥락을 고른다.** 이름은 바이블 파일명이나 별칭과 같게 쓴다.
- 이 장이 하는 일: 플롯 / 인물 변화 / 독자가 끝에 알게 되는 것
- 장면 3~5개: 각 장면이 최소 두 가지 일을 하게
- 마지막 문단의 훅

## 복선 설계
- 새로 심을 복선은 `bible/threads.md`에 `open`으로 미리 등록하고 `회수 예정` 장을 적는다 (id: T__ 이어서).
- 회수 예정이 이 범위에 있는 복선은 해당 장의 `threads_payoff`에 넣는다.
- 큰 반전은 최소 2~3장 앞에 단서를 나눠 심는다.

## 점검
- architecture의 비트 위치와 장 번호가 맞는지
- 주인공이 수동적으로 끌려가기만 하는 장이 3장 이상 이어지지 않는지
- 비슷한 기능의 장면이 연달아 반복되지 않는지

작가와 한 장씩 확인하며 쓴다. 범위가 크면 먼저 장마다 한 줄 요약을 보여주고, 승인을 받은 뒤 상세화한다. `_log.md`에 기록한다.
