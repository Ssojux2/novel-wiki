#!/usr/bin/env python3
"""novel-wiki 프로젝트 초기화.

사용: python3 init_novel.py --path ./my-novel --title "박무도시" [--genre SF] [--pov "3인칭 제한"] [--tense 과거형]
이미 있는 파일은 덮어쓰지 않는다.
"""
import argparse
import datetime as dt
import shutil
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
TPL = PLUGIN / "templates"

DIRS = [
    "manuscript", "notes", "outline", "packs", "reviews", "sessions", "builds",
    "bible/characters", "bible/places", "bible/factions", "bible/tech",
    "bible/rules", "bible/arcs", "bible/chapters", "bible/_templates",
]


def render(src: Path, dst: Path, ctx: dict) -> bool:
    if dst.exists():
        return False
    text = src.read_text(encoding="utf-8")
    for k, v in ctx.items():
        text = text.replace("{{" + k + "}}", v)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(text, encoding="utf-8")
    return True


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--genre", default="SF 장편")
    ap.add_argument("--pov", default="(미정)")
    ap.add_argument("--tense", default="과거형")
    ap.add_argument("--length", default="(미정)")
    ap.add_argument("--style", default="(없음)")
    ap.add_argument("--author", default="(미정)")
    a = ap.parse_args()

    root = Path(a.path).expanduser().resolve()
    ctx = {
        "TITLE": a.title, "GENRE": a.genre, "POV": a.pov, "TENSE": a.tense,
        "LENGTH": a.length, "STYLE_NOTES": a.style, "AUTHOR": a.author, "DATE": dt.date.today().isoformat(),
    }
    created, skipped = [], []
    for d in DIRS:
        (root / d).mkdir(parents=True, exist_ok=True)

    pairs = [
        (TPL / "CLAUDE.md", root / "CLAUDE.md"),
        (TPL / "outline/architecture.md", root / "outline/architecture.md"),
        (TPL / "outline/chapter.md", root / "outline/_chapter-template.md"),
    ]
    for name in ["_overview.md", "_index.md", "_log.md", "timeline.md", "threads.md", "terms.md", "serial.md"]:
        pairs.append((TPL / "bible" / name, root / "bible" / name))
    for p in sorted((TPL / "bible/_templates").glob("*.md")):
        pairs.append((p, root / "bible/_templates" / p.name))

    for src, dst in pairs:
        (created if render(src, dst, ctx) else skipped).append(str(dst.relative_to(root)))

    gi = root / ".gitignore"
    if not gi.exists():
        gi.write_text("packs/\nbuilds/\n.DS_Store\n", encoding="utf-8")

    print(f"프로젝트: {root}")
    print(f"생성 {len(created)}개, 기존 유지 {len(skipped)}개")
    for c in created:
        print(f"  + {c}")
    for s in skipped:
        print(f"  = {s} (이미 있음)")
    print("\n다음: outline/architecture.md 채우기 → /novel-wiki:plan")


if __name__ == "__main__":
    main()
