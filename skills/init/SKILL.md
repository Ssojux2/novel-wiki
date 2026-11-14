---
name: init
description: 새 소설 프로젝트를 만든다. manuscript/·bible/·outline/ 구조, CLAUDE.md 집필 규칙, 바이블 템플릿을 생성한다.
argument-hint: "[경로] [제목]"
---

새 novel-wiki 프로젝트를 초기화한다. 인자: $ARGUMENTS

## 절차
1. 경로와 제목을 확인한다. 인자에 없으면 묻는다. 시점(POV), 시제, 목표 분량, 작가 고유 문체 규칙도 한 번에 물어본다. 모르면 "(미정)"으로 두고 진행한다.
2. 실행한다 (`PLUGIN` = 이 스킬 Base directory의 `../..`):
   ```bash
   python3 PLUGIN/scripts/init_novel.py --path <경로> --title "<제목>" --genre "SF 장편" --pov "<시점>" --tense "<시제>" --length "<분량>" --style "<문체 규칙>"
   ```
   이미 있는 파일은 덮어쓰지 않으므로, 기존 폴더에 다시 실행해도 안전하다.
3. 기존 원고가 있으면 `manuscript/ch01.md` 형식(장 번호가 파일명에 들어가게)으로 옮기도록 안내한다. 파일명에 `ch` + 숫자만 있으면 뒤에 제목이 붙어도 된다 (`ch03-침수.md`).
4. 기존 자료(설정 메모, 자료조사)는 `notes/`에 넣는다.
5. git 사용을 권한다 (`git init`). 바이블 변경 이력이 곧 세계관의 변천사가 된다.

## 다음 단계 안내
- 원고가 없으면 → `/novel-wiki:plan` → `/novel-wiki:world` → `/novel-wiki:outline`
- 원고가 이미 있으면 → `/novel-wiki:ingest 1-N`으로 ch01부터 순서대로 바이블을 컴파일
