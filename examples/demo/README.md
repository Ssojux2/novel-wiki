# 데모 프로젝트

린트와 AI 티 탐지가 무엇을 잡는지 보여주려고 일부러 오류를 넣은 3장짜리 예제입니다.

```bash
cd examples/demo
python3 ../../scripts/state_at.py --at ch03 --entity 서윤
python3 ../../scripts/context_pack.py --chapter 4
python3 ../../scripts/lint_bible.py          # 사망 인물 재등장, 시간 역행, 기한 지난 복선, 금지 표기
python3 ../../scripts/deslop_ko.py manuscript/ch01.md
```

## 주간 연재 데모 (ch04~ch06)
```bash
python3 ../../scripts/serial_review_pack.py --chapter 6   # 박소장 5주 만의 재등장, ch01과 겹치는 표현, 분량 추세
python3 ../../scripts/snapshot.py save ch06 원고
python3 ../../scripts/snapshot.py diff ch06
python3 ../../scripts/build_docx.py --from 6 --to 6 --preset reading --no-title-page --txt
```
