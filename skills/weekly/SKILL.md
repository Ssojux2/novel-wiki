---
name: weekly
description: 주간 연재 한 회차를 처음부터 공개본까지 처리하는 루틴. 작가가 manuscript/chNN.md를 쓰면, 이전 회차를 참조해 검토하고 같은 파일을 단계별로 다듬는다(스냅샷으로 되돌리기 가능). 바이블 반영과 회차 공개본(docx·txt) 빌드, 연재 기록까지 이어서 처리한다. "이번 주 회차 검토", "N화 연재 준비", "이번 화 올릴 수 있게" 같은 요청에 쓴다.
argument-hint: "<회차 번호> [--quick]"
---

주간 연재 루틴. 인자: $ARGUMENTS (없으면 가장 최근에 수정된 회차)

**원칙: 한 회차 = 한 파일 (`manuscript/chNN.md`).** 같은 파일을 단계별로 고친다. 그 대신 단계마다 스냅샷을 남겨, 언제든 작가의 원문과 비교하고 되돌릴 수 있게 한다. 검토는 이번 화만 보지 않고, 이전 회차 원문과 바이블을 근거로 한다.

`PLUGIN` = 이 스킬 Base directory의 `../..`. 스크립트는 모두 `PLUGIN/scripts/`에 있다.

## 0. 준비 (확인만, 수정 없음)
1. 회차 N을 확정한다. `CLAUDE.md`의 `## 연재 설정`(요일, 회당 분량, 참조 회차 수, 플랫폼)을 읽는다. 없으면 한 번 묻고 채운다.
2. 직전 화(N-1)가 바이블에 반영됐는지 확인한다 (`bible/chapters/ch(N-1).md`). 안 됐으면 **먼저 N-1을 ingest한다.** 이전 회차가 검토의 근거이기 때문이다.
3. 작가 원문을 보존한다:
   ```bash
   python3 PLUGIN/scripts/snapshot.py --project . save chNN 원고
   ```

## 1. 이전 회차 기반 검토
```bash
python3 PLUGIN/scripts/serial_review_pack.py --project . --chapter N
python3 PLUGIN/scripts/context_pack.py --project . --chapter N
```
- `packs/review-chNN.md`: 회차 추세(분량·호흡·대사 비율·AI 티 점수), 지난 화 마지막 ↔ 이번 화 시작, 직전 화 전문과 이전 회차 요약, 독자 기억 거리(오래 안 나온 인물·장소), 이전 회차와 겹치는 표현, 열린 복선
- `packs/chNN.md`: N-1 끝 시점의 인물 상태 (연속성 근거)

리뷰어를 호출한다:
```
Agent(subagent_type: "novel-wiki:chapter-reviewer",
      prompt: "PLUGIN=<경로>, PROJECT=<경로>. chNN 연재 회차 리뷰.
               연재 검토 팩: packs/review-chNN.md, 맥락 팩: packs/chNN.md. 연재 축을 포함해 검토하라.")
```
판정과 상위 항목을 보여주고, 적용할 제안을 작가가 고르게 한다. **플롯·설정이 바뀌는 제안은 작가가 직접 고르거나 직접 고친다.**

## 2. 다듬기 (같은 파일, 단계마다 스냅샷)
작가가 고른 것만, 아래 순서로 진행한다. 각 단계 **전에** `snapshot.py save chNN <단계명>`을 실행한다.
1. **review 적용**: 고른 제안을 writer에게 Edit로 적용시킨다 (`novel-wiki:writer`, 고쳐쓰기 모드).
2. **breath**: `breath_ko.py`로 재고 목표에 못 미치면 `novel-wiki:stylist`에게 맡긴다. 이번 화 호흡이 이전 회차 평균과 크게 다르면(검토 팩 1번 경고) 이전 회차에 맞추는 것을 우선한다. 연재 문체의 일관성이 먼저다.
3. **deslop**: `novel-wiki:deslop-editor`를 rewrite 모드로 호출한다. 이전 회차와 겹치는 표현(검토 팩 5번) 가운데 의도하지 않은 반복도 함께 고친다.

`--quick`이면 1~2단계 리뷰를 생략하고 breath 측정과 deslop만 한다.

## 3. 변경 확인
```bash
python3 PLUGIN/scripts/snapshot.py --project . diff chNN --write
```
원문 대비 바뀐 문단을 전후로 보여준다. 작가가 되돌리고 싶은 항목이 있으면:
- 특정 문단만 → 해당 부분을 원문으로 Edit
- 전체 → `snapshot.py restore chNN 원고` (현재 상태도 스냅샷으로 남긴 뒤 되돌린다)

## 4. 확정 처리
작가가 "확정"하면:
1. **ingest**: `novel-wiki:bible-keeper`로 N화를 바이블에 반영한다. 다음 주 검토의 근거가 된다.
2. **기계 린트**: `lint_bible.py --no-write`로 경고급만 확인한다.
3. **공개본 빌드**:
   ```bash
   python3 PLUGIN/scripts/build_docx.py --project . --from N --to N --preset reading --no-title-page --txt
   ```
   `builds/날짜/` 아래에 docx와 플랫폼에 붙여 넣을 txt가 생긴다.
4. **연재 기록**: `bible/serial.md` 표에 한 줄을 추가한다 (회차, 공개 예정일, 분량, 이번 화의 훅 한 줄, 다음 화로 넘기는 질문). 독자 반응은 나중에 작가가 알려주면 그 행에 채운다.
5. **세션 노트**: `sessions/YYYY-MM-DD_chNN.md`에 2~5문장, `bible/_log.md`에 `## [날짜] weekly | chNN`.

## 마무리 보고
```
chNN 연재 준비 완료
- 검토: 판정 / 적용한 제안 N개
- 호흡: 18자 → 52자 · AI 티: 72 → 91 · 변경 비중 34% (reviews/changes-chNN-날짜.md)
- 바이블: 상태 갱신 N, 복선 심음/회수
- 공개본: builds/날짜/…docx, …txt
- 다음 화 메모: 이번 화 훅 / 회수 기한이 다가온 복선 / 오래 안 나온 인물
```
