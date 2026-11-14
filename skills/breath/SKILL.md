---
name: breath
description: 문장 호흡을 측정하고 길고 깊은 묘사 문체로 바꾼다. 노벨문학상·휴고상 수상작에서 뽑은 일곱 모드(장문누적, 반복리듬, 감각정밀, 기억굴절, 민족지, 이인칭, 고밀도) 가운데 골라 적용한다. "문장이 너무 짧다", "호흡을 길게", "묘사를 풍부하게", "문체 바꿔줘" 같은 요청에 쓴다.
argument-hint: "<setup | 장 번호 | 범위> [analyze|rewrite] [모드]"
---

문장 호흡 조정. 인자: $ARGUMENTS (기본: analyze)

`PLUGIN` = 이 스킬 Base directory의 `../..`. 기준 문서는 `PLUGIN/references/prose-breath.md`다.

## setup — 호흡 프로필 정하기
1. `prose-breath.md`의 **같은 장면을 일곱 모드로 쓴 예문**을 작가에게 보여주고 묻는다:
   - 이 작품의 기본으로 삼을 모드 1~2개
   - 장면별로 쓸 모드 (묘사 / 액션 / 회상 / 세계설명 / 고립)
   - 이인칭을 쓸 인물 줄기가 있는지 (구조 결정이므로 `outline/architecture.md`에도 적는다)
2. 이미 쓴 장이 있으면 `breath_ko.py`로 현재 평균을 재서, 목표를 현실적으로 제안한다 (보통 현재보다 1.5~2.5배).
3. 프로젝트 `CLAUDE.md`의 `## 호흡 프로필` 섹션을 채운다 (없으면 추가한다):
   ```
   ## 호흡 프로필
   - 목표 평균 문장 길이: 55        ← 서술문 기준, 공백 포함 글자 수
   - 장문(80자 이상) 비율 목표: 30
   - 짧은 문장(20자 이하) 연속 허용: 2
   - 기본 모드: 감각정밀, 장문누적
   - 장면별 모드: 묘사=장문누적, 액션=고밀도, 회상=기억굴절, 세계설명=민족지, 고립=반복리듬
   ```
   writer, stylist, chapter-reviewer, deslop이 모두 이 섹션을 읽는다.

## analyze — 측정만
```bash
python3 PLUGIN/scripts/breath_ko.py manuscript/chNN.md --write
```
판정, 길이 분포, 고칠 후보 상위 구간을 보여준다. 여러 장이면 장마다 평균을 표로 비교하고, 호흡이 짧은 장 순으로 정렬한다.

## rewrite — 다시 쓰기
1. 먼저 analyze로 후보를 보여주고, 어느 구간을 어떤 모드로 바꿀지 확인받는다. 작가가 모드를 지정하면 그 모드를 우선한다.
2. 원고를 보존한다: git이 있으면 커밋 상태를 확인하고, 없으면 `reviews/backup-chNN-날짜.md`로 복사한다.
3. 호출:
   ```
   Agent(subagent_type: "novel-wiki:stylist",
         prompt: "PLUGIN=<경로>, PROJECT=<경로>. 파일: manuscript/chNN.md.
                  범위: <전체 | L120~180>. 모드: <지정 모드 또는 '프로필 따름'>.")
   ```
   여러 장은 장마다 병렬로 호출해도 된다 (사실을 바꾸지 않으므로 장끼리 독립적이다).
4. 반환된 전후 비교를 보여주고, 되돌릴 구간이 있으면 stylist에게 Edit로 되돌리게 한다.
5. 문체만 바뀌고 사실은 그대로이므로 재-ingest는 필요 없다. 단, stylist가 '작가 확인 필요'로 올린 항목은 처리한다.

## 권장 흐름
초고 → (ingest) → review → **breath rewrite** → deslop → build.
호흡을 먼저 늘리고 AI 티를 나중에 지운다. 장문을 쓰는 과정에서 생긴 상투어를 deslop이 마지막에 걸러낸다.
