#!/usr/bin/env python3
"""한 파일을 고쳐 나가는 방식의 안전장치: 단계마다 원고 스냅샷을 남기고, 변경 내역을 비교한다.
스냅샷은 지우지 않고 쌓기만 한다 (reviews/snapshots/chNN/).

사용:
  python3 snapshot.py --project . save ch12 원고          # 단계 이름: 원고, review, breath, deslop …
  python3 snapshot.py --project . list ch12
  python3 snapshot.py --project . diff ch12 [--from 원고|1] [--to 현재|3] [--write]
  python3 snapshot.py --project . restore ch12 <번호|단계>  # 현재 원고도 먼저 스냅샷으로 남긴 뒤 되돌림
"""
from __future__ import annotations

import argparse
import datetime as dt
import difflib
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bible_lib import ch_label, ch_num, manuscript_chapters  # noqa: E402


def snap_dir(root: Path, n: int) -> Path:
    return root / "reviews" / "snapshots" / ch_label(n)


def snaps(root: Path, n: int) -> list[Path]:
    d = snap_dir(root, n)
    return sorted(d.glob("*.md")) if d.exists() else []


def pick(root: Path, n: int, key: str | None, default_first: bool) -> Path | None:
    items = snaps(root, n)
    if not items:
        return None
    if key is None:
        return items[0] if default_first else items[-1]
    if key.isdigit():
        i = int(key) - 1
        return items[i] if 0 <= i < len(items) else None
    hits = [p for p in items if p.stem.split("-", 2)[-1] == key]
    return hits[0] if hits else None


def paras(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def save(root: Path, n: int, src: Path, step: str) -> Path:
    d = snap_dir(root, n)
    d.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    dst = d / f"{stamp}-{re.sub(r'[^0-9A-Za-z가-힣_]', '_', step)}.md"
    shutil.copy2(src, dst)
    return dst


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    ap.add_argument("cmd", choices=["save", "list", "diff", "restore"])
    ap.add_argument("chapter")
    ap.add_argument("step", nargs="?")
    ap.add_argument("--from", dest="frm")
    ap.add_argument("--to")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()

    root = Path(a.project).resolve()
    n = ch_num(a.chapter)
    chapters = manuscript_chapters(root)
    if n not in chapters:
        sys.exit(f"{ch_label(n)} 원고가 없습니다.")
    src = chapters[n]

    if a.cmd == "save":
        dst = save(root, n, src, a.step or "snapshot")
        print(f"스냅샷 저장: {dst.relative_to(root)}")
        return

    if a.cmd == "list":
        items = snaps(root, n)
        if not items:
            print("스냅샷 없음")
        for i, p in enumerate(items, 1):
            print(f"{i}. {p.stem}  ({len(p.read_text(encoding='utf-8')):,}자)")
        return

    if a.cmd == "restore":
        target = pick(root, n, a.step, default_first=True)
        if target is None:
            sys.exit("되돌릴 스냅샷을 찾지 못했습니다. list로 확인하세요.")
        backup = save(root, n, src, "restore-전")
        shutil.copy2(target, src)
        print(f"{src.relative_to(root)} ← {target.name} 로 되돌림 (직전 상태는 {backup.name}에 보관)")
        return

    # diff
    old_p = pick(root, n, a.frm, default_first=True)
    if old_p is None:
        sys.exit("비교할 스냅샷이 없습니다. 먼저 save 하세요.")
    new_p = src if a.to in (None, "현재") else pick(root, n, a.to, default_first=False)
    old, new = paras(old_p.read_text(encoding="utf-8")), paras(new_p.read_text(encoding="utf-8"))
    sm = difflib.SequenceMatcher(a=old, b=new, autojunk=False)
    blocks, changed_chars = [], 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        o, nw = "\n\n".join(old[i1:i2]), "\n\n".join(new[j1:j2])
        changed_chars += max(len(o), len(nw))
        blocks.append((tag, i1 + 1, o, nw))
    total = max(sum(len(p) for p in old), 1)
    label = {"replace": "수정", "delete": "삭제", "insert": "추가"}
    lines = [f"# 변경 내역 — {ch_label(n)}", "",
             f"- 기준: `{old_p.name}` → 비교: `{new_p.name if new_p != src else '현재 원고'}`",
             f"- 바뀐 문단 묶음 {len(blocks)}개 · 변경 비중 약 {100 * changed_chars / total:.0f}%",
             "- 되돌리려면: `snapshot.py restore " + ch_label(n) + " <번호|단계>` 또는 해당 문단만 원문으로 Edit", ""]
    for k, (tag, pos, o, nw) in enumerate(blocks, 1):
        lines.append(f"## {k}. {label[tag]} (기준 문단 {pos})")
        if o:
            lines.append("**전**\n" + "\n".join(f"> {x}" for x in o.splitlines()))
        if nw:
            lines.append("**후**\n" + "\n".join(f"> {x}" for x in nw.splitlines()))
        lines.append("")
    report = "\n".join(lines)
    if a.write:
        out = root / "reviews" / f"changes-{ch_label(n)}-{dt.date.today().isoformat()}.md"
        out.write_text(report + "\n", encoding="utf-8")
        print(f"리포트: {out.relative_to(root)}")
    print(report)


if __name__ == "__main__":
    main()
