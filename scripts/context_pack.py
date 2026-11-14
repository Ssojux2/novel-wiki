#!/usr/bin/env python3
"""장면/장 집필용 맥락 팩 생성 (LLM Wiki의 Query 단계).

바이블 전체 대신, N장을 쓰는 데 필요한 것만 'N-1장 끝 시점' 상태로 묶는다.

사용: python3 context_pack.py --project . --chapter 12 [--scene 3] [--with 이름 --with 이름]
결과: packs/ch12.md (또는 packs/ch12-s3.md)
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bible_lib import (  # noqa: E402
    STATEFUL_DIRS, ch_label, ch_num, find_entity, format_state, load_bible, load_page,
    manuscript_chapters, mentions, read_tsv_table, split_frontmatter, state_at,
)

TAIL_CHARS = 1500


def section(body: str, *keywords: str, limit: int = 1200) -> str:
    lines = body.splitlines()
    out, grab, level = [], False, 0
    for line in lines:
        m = re.match(r"^(#+)\s+(.*)", line)
        if m:
            lv = len(m.group(1))
            if grab and lv <= level:
                break
            if not grab and any(k in m.group(2) for k in keywords):
                grab, level = True, lv
                continue
        if grab:
            if line.strip().startswith("<!--") or re.match(r"^\s*-\s*[^:]*:\s*$", line):
                continue  # 주석과 빈 템플릿 항목은 건너뜀
            out.append(line)
    text = "\n".join(out).strip()
    return text[:limit] + (" …" if len(text) > limit else "")


def find_outline(root: Path, n: int) -> Path | None:
    for p in sorted((root / "outline").glob("*.md")):
        if p.name.startswith("_"):
            continue
        if ch_num(p.stem) == n:
            return p
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    ap.add_argument("--chapter", required=True)
    ap.add_argument("--scene", default=None)
    ap.add_argument("--with", dest="extra", action="append", default=[])
    a = ap.parse_args()

    root = Path(a.project).resolve()
    n = ch_num(a.chapter)
    if n is None:
        sys.exit(f"장 번호를 해석할 수 없음: {a.chapter}")
    prev = n - 1
    bible = load_bible(root)
    chapters = manuscript_chapters(root)

    # 1) 아웃라인
    outline_path = find_outline(root, n)
    outline_meta, outline_body = ({}, "")
    if outline_path:
        outline_meta, outline_body = split_frontmatter(outline_path.read_text(encoding="utf-8"))

    # 2) 등장 대상 고르기: 아웃라인 frontmatter + 본문 언급 + --with + (아웃라인 없으면) 직전 장 언급
    probe = outline_body + "\n" + " ".join(a.extra)
    for key in ("characters", "places", "factions", "tech"):
        v = outline_meta.get(key)
        if isinstance(v, list):
            probe += "\n" + " ".join(v)
    if not outline_path and prev in chapters:
        probe += "\n" + chapters[prev].read_text(encoding="utf-8")

    picked = {d: [p for p in bible[d] if mentions(probe, p.names)] for d in STATEFUL_DIRS}
    rules_hit = [p for p in bible["rules"] if mentions(probe, p.names)]
    missing = [x for x in a.extra if find_entity(bible, x) is None]

    # 3) 문서 조립
    out = []
    label = ch_label(n) + (f"-s{a.scene}" if a.scene else "")
    out.append(f"# 맥락 팩 — {label}")
    out.append(
        f"\n> 기준 시점: **{ch_label(prev)} 끝**. 이 팩에 있는 것만 정본이다. "
        "여기 없는 설정이 필요하면 지어내지 말고 작가에게 묻거나 '새 설정 후보'로 보고한다.\n"
    )

    arch = root / "outline/architecture.md"
    if arch.exists():
        _, ab = split_frontmatter(arch.read_text(encoding="utf-8"))
        axis = [(kw, section(ab, kw, limit=500)) for kw in ("전제", "주제", "SF 설계", "결말", "톤")]
        axis = [(kw, s) for kw, s in axis if s]
        if axis:
            out.append("## 작품 축")
            out += [f"### {kw}\n{s}" for kw, s in axis]
        else:
            out.append("## 작품 축\n⚠️ outline/architecture.md가 비어 있음 → /novel-wiki:plan 권장")

    out.append("\n## 이번 장 아웃라인")
    if outline_path:
        out.append(f"(출처: {outline_path.relative_to(root)})")
        if a.scene:
            out.append(f"**집필 대상: 장면 {a.scene}**")
        out.append(outline_body.strip()[:2500])
    else:
        out.append("⚠️ 아웃라인 없음. 작가에게 이번 장의 목적을 먼저 확인할 것.")

    if prev >= 1:
        cs = root / "bible/chapters" / f"{ch_label(prev)}.md"
        if cs.exists():
            _, cb = split_frontmatter(cs.read_text(encoding="utf-8"))
            out.append(f"\n## 직전 장 요약 ({ch_label(prev)})\n" + section(cb, "요약", limit=800))
        if prev in chapters:
            txt = chapters[prev].read_text(encoding="utf-8").strip()
            out.append(f"\n## 직전 장 마지막 부분 ({ch_label(prev)}, 문체·흐름 연결용)\n```text\n…{txt[-TAIL_CHARS:]}\n```")

    titles = {"characters": "인물", "places": "장소", "factions": "세력", "tech": "기술"}
    for d in STATEFUL_DIRS:
        if not picked[d]:
            continue
        out.append(f"\n## {titles[d]} — 고정 설정 + {ch_label(max(prev,0))} 끝 상태")
        for p in picked[d]:
            fixed = section(p.body, "고정 설정", "작동 원리", "능력과 한계", limit=700)
            st = state_at(p, max(prev, 0))
            if st.get("dead"):
                out.append(f"\n### ⚠️ {p.title} — 이미 사망 처리됨. 등장시키려면 회상/기록이어야 한다")
            else:
                out.append(f"\n### {p.title}")
            if fixed:
                out.append(fixed)
            out.append(format_state(p, max(prev, 0)))

    out.append("\n## 세계 규칙")
    if bible["rules"]:
        for p in bible["rules"]:
            rule = section(p.body, "규칙", limit=200).splitlines()
            one = next((r for r in rule if r.strip()), "(내용 없음)")
            star = " ★이번 장 관련" if p in rules_hit else ""
            out.append(f"- **{p.title}**{star}: {one}")
        for p in rules_hit:
            out.append(f"\n### {p.title} (상세)\n" + section(p.body, "함의", "예외", limit=600))
    else:
        out.append("(등록된 규칙 없음)")

    threads = read_tsv_table(root / "bible/threads.md", "복선")
    payoff_ids = set(outline_meta.get("threads_payoff") or [])
    open_rows = []
    for t in threads:
        planted = ch_num(t.get("심은 장"))
        if t.get("상태", "").strip() != "open" or planted is None or planted > prev:
            continue
        due = ch_num(t.get("회수 예정"))
        mark = ""
        if t.get("id") in payoff_ids:
            mark = " ★이번 장 회수 예정(아웃라인)"
        elif due is not None and due <= n:
            mark = " ⏰회수 기한 도래"
        open_rows.append(f"- {t.get('id')}: {t.get('복선·떡밥')} (심음 {t.get('심은 장')}, 예정 {t.get('회수 예정') or '-'}){mark}")
    out.append("\n## 열린 복선")
    out += open_rows or ["(없음)"]

    tl = [r for r in read_tsv_table(root / "bible/timeline.md", "사건") if (ch_num(r.get("장")) or 0) <= prev]
    out.append("\n## 최근 타임라인")
    out += [f"- {r.get('장')} | {r.get('이야기 내 시각')} | {r.get('사건')} @ {r.get('장소')}" for r in tl[-6:]] or ["(없음)"]

    terms = read_tsv_table(root / "bible/terms.md", "용어")
    if terms:
        out.append("\n## 고유명사 정본 표기")
        out += [f"- {t.get('정본')} (금지: {t.get('금지 변형') or '-'})" for t in terms]

    if missing:
        out.append("\n## ⚠️ 바이블에 없는 이름\n" + "\n".join(f"- {m}" for m in missing))

    dst = root / "packs" / f"{label}.md"
    dst.parent.mkdir(exist_ok=True)
    text = "\n".join(out) + "\n"
    dst.write_text(text, encoding="utf-8")
    counts = ", ".join(f"{titles[d]} {len(picked[d])}" for d in STATEFUL_DIRS)
    print(f"맥락 팩 생성: {dst.relative_to(root)} ({len(text):,}자) — {counts}, 열린 복선 {len(open_rows)}")


if __name__ == "__main__":
    main()
