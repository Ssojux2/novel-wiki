---
name: ingest
description: 탈고한 장을 스토리 바이블에 컴파일한다(LLM Wiki의 Ingest). 장 요약, 상태 변화, 타임라인, 복선, 고유명사, 색인을 갱신한다. 여러 장은 순서대로 처리한다.
argument-hint: "<장 번호 | 범위 1-5 | pending>"
---

바이블 컴파일. 인자: $ARGUMENTS
- `pending`이면 lint가 '미반영'이나 '재-ingest 권장'으로 표시한 장 전부

## 절차
1. `PLUGIN` = 이 스킬 Base directory의 `../..`. 대상 장 목록을 정한다.
2. **장 순서대로 하나씩** bible-keeper를 호출한다. 앞 장의 상태가 뒷 장의 기준이 되므로 병렬로 처리하지 않는다:
   ```
   Agent(subagent_type: "novel-wiki:bible-keeper",
         prompt: "PLUGIN=<경로>, PROJECT=<경로>. chNN ingest.
                  승인된 새 설정: <write 단계에서 작가가 승인한 목록, 있으면>.
                  거절된 설정(기록 금지): <있으면>.")
   ```
3. 장마다 반환된 요약을 보여준다. **⚠️ 모순·확인 필요** 항목은 작가에게 묻고, 답을 받아 bible-keeper에게 수정시킨다.
4. 끝나면 확인한다:
   ```bash
   python3 PLUGIN/scripts/lint_bible.py --project . --no-write
   ```
   ingest 관련 경고가 남아 있으면 처리한다.

## 기존 원고를 처음 컴파일할 때 (예: 20장)
- 장이 많아도 순서대로 처리한다. 5장마다 작가에게 중간 결과를 보여주고, 인물 이름 표기나 페이지 단위가 마음에 드는지 확인받는다. 초반에 형식을 잡아야 뒤에서 고칠 일이 줄어든다.
- 다 끝나면 `/novel-wiki:lint`를 권한다.
