#!/usr/bin/env python3
"""주간 연재 검토 팩. N화를 검토할 때 이전 회차들을 근거로 쓰도록 한 파일로 묶는다.

담는 것
  1. 연재 설정과 회차 추세표 (분량, 서술 호흡, 대사 비율, AI 티 점수) — 이번 화가 튀는지
  2. 지난 화 마지막 장면 ↔ 이번 화 첫 장면 (훅 연결 검토용)
  3. 직전 화 전문 + 그 이전 회차 요약 (lookback 만큼)
  4. 독자 기억 거리: 이번 화 등장 개체 중 오래 안 나온 것(회상 단서 필요), 처음 나온 것(소개 필요)
  5. 회차 간 반복 표현: 이번 화 문장이 이전 회차와 12자 이상 겹치는 구간
  6. 열린 복선과 기한

사용: python3 serial_review_pack.py --project . --chapter 12 [--lookback 3]
결과: packs/review-ch12.md
"""
import argparse
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bible_lib import (  # noqa: E402
    STATEFUL_DIRS, body_text, ch_label, ch_num, load_bible, load_breath_profile, load_serial_config,
    manuscript_chapters, read_tsv_table, split_frontmatter,
)

NGRAM = 12
RECALL_GAP = 4  # 이만큼 회차가 비면 독자가 잊었을 수 있다


def paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip() and not p.strip().startswith("#")]


def episode_metrics(path: Path, root: Path) -> dict:
    text = body_text(path)
    m = {"chars": len(re.sub(r"\s", "", text))}
    try:
        import breath_ko
        res, _ = breath_ko.analyze(path, load_breath_profile(root), 3)
        m["breath"] = res.get("mean")
        total = res["narration_sentences"] + res["dialogue_sentences"]
        m["dialogue"] = round(100 * res["dialogue_sentences"] / total) if total else 0
    except Exception:
        m["breath"], m["dialogue"] = None, None
    try:
        import deslop_ko
        fs, _ = deslop_ko.audit_file(path, root, [])
        w = sum(f["severity"] == "warning" for f in fs)
        s = sum(f["severity"] == "suggestion" for f in fs)
        n = sum(f["severity"] == "note" for f in fs)
        m["ai_score"] = max(0, 100 - w * 4 - s * 2 - n // 2)
    except Exception:
        m["ai_score"] = None
    return m


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s)


def repeated_spans(current: str, previous: dict[int, str], skip_words: set) -> list[tuple[str, int]]:
    cur = norm(current)
    index: dict[str, int] = {}
    for n, t in previous.items():
        t = norm(t)
        for i in range(len(t) - NGRAM + 1):
            index.setdefault(t[i:i + NGRAM], n)
    spans, i = [], 0
    while i <= len(cur) - NGRAM:
        g = cur[i:i + NGRAM]
        if g in index:
            j = i + NGRAM
            while j < len(cur) and cur[i:j + 1][-NGRAM:] in index:
                j += 1
            span = cur[i:j].strip()
            core = span
            for w in skip_words:
                core = core.replace(w, "")
            if len(re.sub(r"[\s\W]", "", core)) >= 8 and not span.startswith(("\"", "“")):
                spans.append((span, index[g]))
            i = j
        else:
            i += 1
    seen, out = set(), []
    for s, n in spans:
        if s not in seen:
            seen.add(s)
            out.append((s, n))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    ap.add_argument("--chapter", required=True)
    ap.add_argument("--lookback", type=int)
    a = ap.parse_args()

    root = Path(a.project).resolve()
    n = ch_num(a.chapter)
    chapters = manuscript_chapters(root)
    if n not in chapters:
        sys.exit(f"{ch_label(n)} 원고가 없습니다.")
    conf = load_serial_config(root)
    k = a.lookback or conf["lookback"]
    prev_ns = [x for x in sorted(chapters) if x < n]
    window = prev_ns[-k:]
    bible = load_bible(root)
    cur_text = body_text(chapters[n])
    out = [f"# 연재 검토 팩 — {ch_label(n)}", "",
           f"> 참조 범위: 직전 {len(window)}화 ({', '.join(ch_label(x) for x in window) or '없음'}). "
           "이 팩의 이전 회차 원문과 요약이 이번 화 검토의 근거다.", ""]

    # 1) 설정과 추세
    out.append("## 1. 연재 설정과 회차 추세")
    out.append(f"- 연재 요일: {conf['day'] or '(미설정)'} · 플랫폼: {conf['platform'] or '(미설정)'} · "
               f"회당 목표 분량: {conf['target_chars'] or '(미설정)'}자")
    rows = []
    for x in window + [n]:
        m = episode_metrics(chapters[x], root)
        rows.append((x, m))
    out += ["", "| 회차 | 분량(공백 제외) | 서술 평균 호흡 | 대사 비율 | AI 티 점수 |", "|---|---|---|---|---|"]
    for x, m in rows:
        mark = " ◀ 이번 화" if x == n else ""
        out.append(f"| {ch_label(x)}{mark} | {m['chars']:,} | {m['breath'] or '-'} | "
                   f"{m['dialogue'] if m['dialogue'] is not None else '-'}% | {m['ai_score'] if m['ai_score'] is not None else '-'} |")
    flags = []
    if len(rows) > 1:
        prev_m = [m for _, m in rows[:-1]]
        cur_m = rows[-1][1]
        avg_chars = statistics.mean(m["chars"] for m in prev_m)
        if avg_chars and abs(cur_m["chars"] - avg_chars) / avg_chars > 0.25:
            flags.append(f"분량이 이전 평균({avg_chars:,.0f}자)과 25% 이상 차이남")
        br = [m["breath"] for m in prev_m if m["breath"]]
        if br and cur_m["breath"] and abs(cur_m["breath"] - statistics.mean(br)) / statistics.mean(br) > 0.3:
            flags.append(f"서술 호흡이 이전 평균({statistics.mean(br):.0f}자)과 30% 이상 차이남 → 문체가 흔들렸는지 확인")
    if conf["target_chars"] and abs(rows[-1][1]["chars"] - conf["target_chars"]) / conf["target_chars"] > 0.15:
        flags.append(f"목표 분량({conf['target_chars']:,}자)과 15% 이상 차이남")
    out += [""] + [f"- ⚠️ {f}" for f in flags] if flags else ["", "- 추세 이상 없음"]

    # 2) 훅 연결
    out.append("\n## 2. 지난 화 마지막 ↔ 이번 화 시작")
    if window:
        last_paras = paragraphs(body_text(chapters[window[-1]]))[-3:]
        first_paras = paragraphs(cur_text)[:3]
        out.append(f"### {ch_label(window[-1])} 마지막 문단들 (독자가 일주일 동안 기억할 장면)")
        out += [f"> {p}" for p in last_paras]
        out.append(f"\n### {ch_label(n)} 첫 문단들")
        out += [f"> {p}" for p in first_paras]
        out.append("\n검토 질문: 지난 화의 훅을 이번 화가 받았나(바로 받기, 비틀어 받기, 의도적 지연)? 일주일 만에 돌아온 독자가 첫 문단에서 상황을 다시 잡을 수 있나?")
    else:
        out.append("(첫 회차)")

    # 3) 이전 회차
    out.append("\n## 3. 이전 회차")
    for x in window[:-1]:
        cs = root / "bible/chapters" / f"{ch_label(x)}.md"
        if cs.exists():
            _, cb = split_frontmatter(cs.read_text(encoding="utf-8"))
            m = re.search(r"##\s*요약\s*\n(.*?)(?=\n##|\Z)", cb, flags=re.S)
            summary = (m.group(1) if m else cb).strip()[:600]
            out.append(f"### {ch_label(x)} 요약\n{summary}")
        else:
            out.append(f"### {ch_label(x)} (바이블 미반영 — 마지막 부분)\n```text\n…{body_text(chapters[x])[-600:]}\n```")
    if window:
        out.append(f"### {ch_label(window[-1])} 전문 (직전 화)\n```text\n{body_text(chapters[window[-1]])}\n```")

    # 4) 독자 기억 거리
    out.append("\n## 4. 독자 기억 거리")
    texts = {x: body_text(p) for x, p in chapters.items() if x <= n}
    recall, new = [], []
    for d in STATEFUL_DIRS:
        for p in bible[d]:
            names = [nm for nm in p.names if len(nm) >= 2]
            if not any(nm in cur_text for nm in names):
                continue
            seen = [x for x in sorted(texts) if x < n and any(nm in texts[x] for nm in names)]
            if not seen:
                new.append(p.title)
            elif n - seen[-1] >= RECALL_GAP:
                recall.append(f"- **{p.title}**: 마지막 등장 {ch_label(seen[-1])} ({n - seen[-1]}주 전) → 짧은 회상 단서가 필요한지 확인")
    out += recall or ["- 오래 비었다가 돌아온 개체 없음"]
    if new:
        out.append("- 이번 화에 처음 등장(바이블 기준): " + ", ".join(new) + " → 첫 등장 소개가 충분한지 확인")

    # 5) 회차 간 반복
    out.append("\n## 5. 이전 회차와 겹치는 표현 (12자 이상)")
    skip = {nm for pages in bible.values() for p in pages for nm in p.names}
    prev_texts = {x: texts[x] for x in prev_ns[-max(k, 6):]}
    reps = repeated_spans(cur_text, prev_texts, skip)
    out += [f"- \"{s[:80]}\" ← {ch_label(src)}" for s, src in reps[:15]] or ["- 없음"]
    if reps:
        out.append("검토 질문: 의도한 반복(모티프, 후렴)인가, 무심코 재사용한 묘사인가?")

    # 6) 복선
    out.append("\n## 6. 열린 복선")
    rows = []
    for t in read_tsv_table(root / "bible/threads.md", "복선"):
        if t.get("상태", "").strip() != "open":
            continue
        due = ch_num(t.get("회수 예정"))
        mark = " ⏰기한 도래·경과" if due is not None and due <= n else ""
        rows.append(f"- {t.get('id')}: {t.get('복선·떡밥')} (심음 {t.get('심은 장')}, 예정 {t.get('회수 예정') or '-'}){mark}")
    out += rows or ["- 없음"]

    dst = root / "packs" / f"review-{ch_label(n)}.md"
    dst.parent.mkdir(exist_ok=True)
    dst.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"연재 검토 팩: {dst.relative_to(root)} — 참조 {len(window)}화, 추세 경고 {len(flags)}, "
          f"회상 필요 {len(recall)}, 신규 {len(new)}, 반복 표현 {len(reps)}")


if __name__ == "__main__":
    main()
