---
name: pack
description: N장(또는 장면) 집필용 맥락 팩을 만든다. 아웃라인, 등장 개체의 고정 설정과 직전 장 끝 시점 상태, 관련 세계 규칙, 열린 복선, 최근 타임라인, 직전 장 꼬리를 한 파일로 묶는다.
argument-hint: "<장 번호> [장면 번호] [추가 인물...]"
---

맥락 팩 생성 (LLM Wiki의 Query 단계). 인자: $ARGUMENTS

## 실행
`PLUGIN` = 이 스킬 Base directory의 `../..`
```bash
python3 PLUGIN/scripts/context_pack.py --project . --chapter <N> [--scene <S>] [--with <이름> ...]
```
결과: `packs/chNN.md` 또는 `packs/chNN-sS.md`

## 확인 후 보고
팩을 읽고 작가에게 짧게 보고한다:
- 포함된 인물·장소·기술과 각자의 핵심 상태 (부상, 사망, 새로 알게 된 것)
- ⏰ 기한이 된 복선, ★ 이번 장에서 회수할 복선
- ⚠️ 경고: 아웃라인 없음, architecture 비어 있음, 바이블에 없는 이름, 사망 인물 포함
- 빠진 게 있어 보이면 (아웃라인에 언급됐는데 팩에 없는 인물 등) `--with`로 다시 만들지 묻는다

## 원칙
- 팩은 **그 장의 유일한 정본**이다. writer는 팩 밖의 바이블을 읽지 않는다. 그래서 팩이 정확해야 한다.
- 직전 장이 아직 ingest되지 않았다면 팩의 상태가 낡은 것이다. 먼저 `/novel-wiki:ingest N-1`을 권한다.
