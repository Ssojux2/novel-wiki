---
name: go
description: 소설 프로젝트 세션을 시작한다. 진행 상황, 미반영 장, 열린 복선, 지난 세션 노트를 읽고 지금 할 일 하나를 추천한다.
argument-hint: "[프로젝트 경로]"
---

세션을 재개한다. 인자: $ARGUMENTS (없으면 현재 폴더)

## 현재 상태
- 최근 커밋: !`git log --oneline -3 2>/dev/null || echo "git 없음"`
- 최근 작업 로그: !`grep "^## \[" bible/_log.md 2>/dev/null | tail -5 || echo "로그 없음"`

## 할 일
1. 읽는다 (바이블 전체를 읽지 않는다):
   - `CLAUDE.md`, `bible/_overview.md`, `bible/_index.md`
   - `sessions/`의 최신 노트 1~2개
   - `outline/architecture.md`의 전제와 결말
2. 기계 린트로 현황을 뽑는다:
   ```bash
   python3 PLUGIN/scripts/lint_bible.py --project . --no-write
   ```
   (`PLUGIN` = 이 스킬 Base directory의 `../..`)
3. 우선순위를 정해 **하나만** 추천한다:
   1. 미반영 장이 있으면 → ingest (다음 집필이 이걸 기다린다)
   2. 경고급 린트(사망 인물 재등장, 시간 역행, 기한 지난 복선)가 있으면 → 해결
   3. 지난 세션 노트에 미해결 질문이 있으면 → 작가에게 묻기
   4. 다음 장 아웃라인이 없으면 → outline
   5. 그 외 → 다음 장 pack + write
4. 지난 세션의 열린 질문을 나열하고, 오늘 어떤 걸 다룰지 작가에게 묻는다.

## 출력
```markdown
## 「제목」 — 세션 시작
**전제:** 한 문장
**진행:** 원고 N장 / 바이블 반영 N장 / 아웃라인 N장 / 열린 복선 N
**지난 세션:** 한두 문장

## 지금 할 일: [하나]
이유 한 줄
→ `/novel-wiki:명령 인자`

## 열린 질문
- …
```
