#!/usr/bin/env python3
"""SessionStart 훅: novel-wiki 프로젝트 폴더에서만 짧은 현황을 컨텍스트로 넣는다.
프로젝트가 아니면 아무것도 출력하지 않는다.
"""
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def main() -> None:
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    if not (root / "bible" / "_index.md").exists():
        return
    try:
        from bible_lib import ch_label, ch_num, manuscript_chapters, read_tsv_table
        chapters = manuscript_chapters(root)
        latest = max(chapters) if chapters else 0
        ingested = sorted(ch_num(p.stem) for p in (root / "bible/chapters").glob("*.md") if ch_num(p.stem))
        pending = [ch_label(n) for n in chapters if n not in ingested]
        threads = read_tsv_table(root / "bible/threads.md", "복선")
        open_t = [t for t in threads if t.get("상태", "").strip() == "open"]
        log = (root / "bible/_log.md").read_text(encoding="utf-8")
        recent = re.findall(r"^## \[.*$", log, flags=re.M)[-3:]
        sessions = sorted((root / "sessions").glob("*.md"))
        last_session = sessions[-1].read_text(encoding="utf-8").strip()[:400] if sessions else ""
        print("[novel-wiki] 소설 프로젝트 감지")
        print(f"- 원고: {len(chapters)}장 (최신 {ch_label(latest) if latest else '-'}) / 바이블 반영: {len(ingested)}장")
        if pending:
            print(f"- 미반영 장: {', '.join(pending)} → /novel-wiki:ingest")
        print(f"- 열린 복선: {len(open_t)}개")
        from bible_lib import load_serial_config
        conf = load_serial_config(root)
        if conf["day"] and "미정" not in conf["day"]:
            print(f"- 연재: 매주 {conf['day']} · 다음 회차 {ch_label(latest + 1)} · /novel-wiki:weekly {latest}  (최신 화 검토가 남았다면)")
        if recent:
            print("- 최근 작업: " + " / ".join(r.lstrip('# ') for r in recent))
        if last_session:
            print(f"- 지난 세션 노트({sessions[-1].name}): {last_session}")
        print("세션을 시작하면 /novel-wiki:go 로 다음 할 일을 정리할 수 있다.")
    except Exception as e:  # 훅은 절대 세션을 막지 않는다
        print(f"[novel-wiki] 현황 요약 실패: {e}")


if __name__ == "__main__":
    main()
