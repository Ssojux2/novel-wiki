#!/usr/bin/env python3
"""바이블·원고 기계적 연속성 검사 (LLM Wiki의 Lint 1단계).

판단이 필요한 검사(인물이 모르는 걸 아는지, 규칙 위반 등)는 continuity-checker 에이전트가
이 리포트를 받아 2단계로 수행한다.

사용: python3 lint_bible.py --project . [--json] [--no-write]
결과: reviews/lint-YYYY-MM-DD.md
"""
import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bible_lib import (  # noqa: E402
    ENTITY_DIRS, STATEFUL_DIRS, WIKILINK_RE, ch_label, ch_num, death_chapter, load_bible,
    manuscript_chapters, read_tsv_table, state_rows,
)

LEDGERS = {"timeline", "threads", "terms", "serial", "_overview", "_index", "_log", "overview", "index", "log"}
TIME_RE = re.compile(r"D\s*([+-]?\d+)(?:\s+(\d{1,2}):(\d{2}))?")


def finding(audit, severity, file, line, quote, issue):
    return {"audit": audit, "severity": severity,
            "location": {"file": file, "line": line, "quote": quote[:120]}, "issue": issue}


def line_in(path: Path, needle: str) -> int:
    if not needle or not path.exists():
        return 1
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if needle in line:
            return i
    return 1


def story_minutes(s: str):
    m = TIME_RE.search(s or "")
    if not m:
        return None
    d = int(m.group(1))
    h = int(m.group(2) or 0)
    mi = int(m.group(3) or 0)
    return d * 1440 + h * 60 + mi


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args()

    root = Path(a.project).resolve()
    bdir = root / "bible"
    if not bdir.exists():
        sys.exit("bible/ 폴더가 없습니다. 먼저 /novel-wiki:init")
    bible = load_bible(root)
    chapters = manuscript_chapters(root)
    latest = max(chapters) if chapters else 0
    F = []

    # ---- 이름 해석 테이블
    resolve = {}
    for d in ENTITY_DIRS:
        for p in bible[d]:
            for key in [p.path.stem, f"{d}/{p.path.stem}", *p.names]:
                resolve[key] = p
    all_md = [p for p in bdir.rglob("*.md") if "_templates" not in p.parts]

    # 1) 깨진 링크 + 인바운드 집계
    inbound = {id(p): 0 for d in ENTITY_DIRS for p in bible[d]}
    for f in all_md:
        rel = str(f.relative_to(root))
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            line = re.sub(r"`[^`]*`", "", line)  # 인라인 코드(예시 표기)는 무시
            for m in WIKILINK_RE.finditer(line):
                target = m.group(1).strip()
                if target.endswith("/") or "..." in target or target in LEDGERS:
                    continue
                stem = target.split("/")[-1]
                p = resolve.get(target) or resolve.get(stem)
                if p is None:
                    F.append(finding("links", "warning", rel, i, m.group(0), f"깨진 링크: '{target}' 페이지가 없음"))
                elif p.path != f:
                    inbound[id(p)] += 1

    # 2) 고아 페이지 + 색인 누락
    index_text = (bdir / "_index.md").read_text(encoding="utf-8") if (bdir / "_index.md").exists() else ""
    for d in ENTITY_DIRS:
        for p in bible[d]:
            rel = str(p.path.relative_to(root))
            if p.path.stem not in index_text and p.title not in index_text:
                F.append(finding("index", "suggestion", rel, 1, p.title, "_index.md에 등록되지 않은 페이지"))
            if d != "chapters" and inbound[id(p)] == 0:
                F.append(finding("orphan", "note", rel, 1, p.title, "다른 바이블 페이지에서 링크되지 않음"))

    # 3) 미반영(ingest 안 된) 장
    for n, mp in sorted(chapters.items()):
        cs = bdir / "chapters" / f"{ch_label(n)}.md"
        rel = str(mp.relative_to(root))
        if not cs.exists():
            F.append(finding("ingest", "warning", rel, 1, ch_label(n), "바이블에 반영되지 않은 장 → /novel-wiki:ingest"))
        elif mp.stat().st_mtime > cs.stat().st_mtime + 1:
            F.append(finding("ingest", "suggestion", rel, 1, ch_label(n), "원고가 바이블 요약보다 나중에 수정됨 → 재-ingest 권장"))

    # 4) 사망 인물 재등장
    for p in bible["characters"]:
        dch = death_chapter(p)
        if dch is None:
            continue
        names = [x for x in p.names if len(x) >= 2]
        for n, mp in chapters.items():
            if n <= dch:
                continue
            for i, line in enumerate(mp.read_text(encoding="utf-8").splitlines(), 1):
                hit = next((x for x in names if x in line), None)
                if hit:
                    F.append(finding("dead-character", "warning", str(mp.relative_to(root)), i, line.strip(),
                                     f"'{p.title}'은(는) {ch_label(dch)}에서 사망. 회상·기록·언급인지 확인"))
                    break

    # 5) 상태표 기록이 원고보다 앞서감 / first_appears 불일치
    for d in STATEFUL_DIRS:
        for p in bible[d]:
            rows = state_rows(p)
            rel = str(p.path.relative_to(root))
            if rows and latest and rows[-1]["_ch"] > latest:
                F.append(finding("state", "note", rel, 1, ch_label(rows[-1]["_ch"]),
                                 f"상태표에 아직 쓰지 않은 장({ch_label(rows[-1]['_ch'])})이 있음 — 계획이면 outline으로 옮길 것"))
            fa = ch_num(p.meta.get("first_appears"))
            if rows and fa is not None and rows[0]["_ch"] != fa:
                F.append(finding("state", "note", rel, 1, str(p.meta.get("first_appears")),
                                 f"first_appears({ch_label(fa)})와 첫 상태 기록({ch_label(rows[0]['_ch'])})이 다름"))

    # 6) 타임라인 순서
    tl = read_tsv_table(bdir / "timeline.md", "사건")
    last = None
    for r in tl:
        if "회상" in r.get("구분", ""):
            continue
        t = story_minutes(r.get("이야기 내 시각", ""))
        if t is None:
            continue
        if last and t < last[0] and (ch_num(r.get("장")) or 0) >= (ch_num(last[1].get("장")) or 0):
            F.append(finding("timeline", "warning", "bible/timeline.md", line_in(bdir / "timeline.md", r.get("이야기 내 시각", "")), f"{r.get('장')} {r.get('이야기 내 시각')}",
                             f"시간 역행: '{r.get('사건')}'이 앞 사건({last[1].get('이야기 내 시각')})보다 이른데 회상 표시가 없음"))
        last = (t, r)

    # 7) 복선
    for t in read_tsv_table(bdir / "threads.md", "복선"):
        if t.get("상태", "").strip() != "open":
            continue
        due = ch_num(t.get("회수 예정"))
        planted = ch_num(t.get("심은 장"))
        q = f"{t.get('id')} {t.get('복선·떡밥')}"
        if due is not None and latest and due < latest:
            F.append(finding("threads", "warning", "bible/threads.md", line_in(bdir / "threads.md", f"| {t.get('id')} |"), q,
                             f"회수 예정({ch_label(due)})이 지났는데 open. 회수하거나 일정 조정·dropped 처리"))
        elif due is None and planted is not None and latest - planted >= 8:
            F.append(finding("threads", "suggestion", "bible/threads.md", line_in(bdir / "threads.md", f"| {t.get('id')} |"), q,
                             f"{latest - planted}장째 회수 계획 없음"))

    # 8) 고유명사 금지 변형
    for term in read_tsv_table(bdir / "terms.md", "용어"):
        canon = term.get("정본", "").strip()
        bad = [b.strip() for b in re.split(r"[,，]", term.get("금지 변형", "")) if b.strip()]
        for n, mp in chapters.items():
            for i, line in enumerate(mp.read_text(encoding="utf-8").splitlines(), 1):
                for b in bad:
                    if b in line:
                        F.append(finding("terms", "suggestion", str(mp.relative_to(root)), i, line.strip(),
                                         f"'{b}' → 정본 '{canon}'"))

    # ---- 출력
    sev_order = {"warning": 0, "suggestion": 1, "note": 2}
    F.sort(key=lambda x: (sev_order[x["severity"]], x["audit"], x["location"]["file"], x["location"]["line"]))
    if a.json:
        print(json.dumps(F, ensure_ascii=False, indent=2))
        return

    counts = {s: sum(1 for f in F if f["severity"] == s) for s in sev_order}
    today = dt.date.today().isoformat()
    lines = [f"# 연속성 린트 — {today}", "",
             f"원고 {len(chapters)}장 (최신 {ch_label(latest) if latest else '-'}) · "
             f"경고 {counts['warning']} · 제안 {counts['suggestion']} · 참고 {counts['note']}", ""]
    labels = {"warning": "경고", "suggestion": "제안", "note": "참고"}
    for s in sev_order:
        group = [f for f in F if f["severity"] == s]
        if not group:
            continue
        lines.append(f"## {labels[s]} ({len(group)})")
        for f in group:
            loc = f["location"]
            lines.append(f"- [{f['audit']}] `{loc['file']}:{loc['line']}` — {f['issue']}  \n  > {loc['quote']}")
        lines.append("")
    if not F:
        lines.append("문제 없음.")
    report = "\n".join(lines)
    if not a.no_write:
        out = root / "reviews" / f"lint-{today}.md"
        out.parent.mkdir(exist_ok=True)
        out.write_text(report + "\n", encoding="utf-8")
        print(f"리포트: {out.relative_to(root)}")
    print(report)


if __name__ == "__main__":
    main()
