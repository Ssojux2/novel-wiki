#!/usr/bin/env python3
"""한국어 소설 AI 티·문장 기계 감사 (결정론적 1차 패스).

author-toolkit의 avoid-ai-writing(탐지 모드)과 prose-mechanics의 결정론적 감사
(필터어, 반복어, 문장 길이 분산, 문장 시작 반복, 대사 태그)를 한국어용으로 다시 구현했다.
판단이 필요한 2차 패스(실제로 고칠지, 어떻게 고칠지)는 deslop-editor 에이전트가 한다.

사용:
  python3 deslop_ko.py manuscript/ch03.md [다른 파일...] [--json] [--write]
  --write: reviews/deslop-<파일명>-YYYY-MM-DD.md 로 저장 (프로젝트 루트 = 파일의 상위에서 CLAUDE.md 탐색)
"""
import argparse
import datetime as dt
import json
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ko_patterns as K  # noqa: E402

SENT_SPLIT = re.compile(r"(?<=[.?!…])[\"'”’」』]?\s+")


def find_root(p: Path) -> Path:
    for parent in [p.parent, *p.parents]:
        if (parent / "CLAUDE.md").exists() or (parent / "bible").exists():
            return parent
    return p.parent


def strip_markup(text: str) -> str:
    text = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.S)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    return text


def line_of(text: str, idx: int) -> int:
    return text.count("\n", 0, idx) + 1


def F(audit, severity, file, line, quote, issue, confidence="deterministic"):
    return {"audit": audit, "technique": audit, "severity": severity,
            "location": {"file": file, "line": line, "quote": quote.strip()[:100] or "-"},
            "issue": issue, "confidence": confidence}


def norm_word(w: str) -> str:
    w = re.sub(r"[^가-힣A-Za-z0-9]", "", w)
    for p in K.PARTICLES:
        if w.endswith(p) and len(w) - len(p) >= 2:
            return w[: -len(p)]
    return w


def bible_names(root: Path) -> set:
    names = set()
    try:
        from bible_lib import load_bible
        for pages in load_bible(root).values():
            for p in pages:
                names.update(p.names)
    except Exception:
        pass
    return names


def audit_file(path: Path, root: Path, extra_tier1: list) -> tuple[list, dict]:
    raw = path.read_text(encoding="utf-8")
    text = strip_markup(raw)
    rel = str(path.relative_to(root)) if path.is_relative_to(root) else str(path)
    chars = max(len(re.sub(r"\s", "", text)), 1)
    per_k = 1000 / chars
    out = []

    def lines_hit(pattern, audit, sev, issue_fn, conf="deterministic"):
        n = 0
        for m in re.finditer(pattern, text, flags=re.M):
            ln = line_of(text, m.start())
            ctx = text.splitlines()[ln - 1] if text.splitlines() else m.group(0)
            out.append(F(audit, sev, rel, ln, ctx, issue_fn(m), conf))
            n += 1
        return n

    stats = {}
    # Tier 1
    t1 = 0
    for pat, why in K.TIER1 + extra_tier1:
        t1 += lines_hit(pat, "ai-ism-t1", "warning", lambda m, w=why: f"'{m.group(0)}' — {w}")
    stats["tier1"] = t1

    # Tier 2 (문단 단위 군집)
    t2 = 0
    offset = 0
    for para in re.split(r"\n\s*\n", text):
        hits = [(pat, why, m) for pat, why in K.TIER2 for m in re.finditer(pat, para)]
        if len({h[0] for h in hits}) >= 2:
            ln = line_of(text, text.find(para, offset))
            words = ", ".join(sorted({h[2].group(0) for h in hits}))
            out.append(F("ai-ism-t2", "suggestion", rel, ln, para[:100], f"상투어 군집: {words}"))
            t2 += 1
        offset += len(para)
    stats["tier2_paragraphs"] = t2

    # 호흡 프로필: 장문 지향이면 접속·연결 표현 기준을 완화하고, 호흡이 짧으면 breath를 권한다
    try:
        from bible_lib import load_breath_profile
        prof = load_breath_profile(root)
    except Exception:
        prof = {"mean": 45}
    long_mode = prof.get("mean", 45) >= 50

    # Tier 3 밀도
    for pat, limit, why in K.TIER3_DENSITY:
        if long_mode and pat in ("그리고", r"(?:을|를) 통해"):
            limit *= 1.5
        c = len(re.findall(pat, text))
        d = c * per_k
        if d > limit:
            out.append(F("ai-ism-t3", "suggestion", rel, 1, f"{c}회", f"{why}: 1,000자당 {d:.1f}회 (기준 {limit})"))

    # 구조 패턴
    stats["em_dash"] = len(re.findall(K.EM_DASH, text))
    if stats["em_dash"] * per_k > 1.0:
        out.append(F("em-dash", "suggestion", rel, 1, f"{stats['em_dash']}회",
                     f"줄표(—) 1,000자당 {stats['em_dash']*per_k:.1f}회. 한국어 소설에선 드묾. 쉼표·마침표로"))
    lines_hit(K.NOT_X_BUT_Y, "not-x-but-y", "note", lambda m: "'A가 아니라 B' 대조 구문 — 한 작품에 몇 번만", "judgment")
    lines_hit(K.TRIAD, "triad", "note", lambda m: f"3항 나열 '{m.group(0)}' — 리듬이 기계적이면 2개나 4개로", "judgment")
    lines_hit(K.TAG_ADVERB, "dialogue-tag", "suggestion", lambda m: f"부사로 꾸민 대사 태그 '{m.group(0)}' — 대사 자체로 보여주기")

    # 필터어 / 감정 이름
    fw = lines_hit(K.FILTER_WORDS, "filter-words", "note", lambda m: f"필터어 '{m.group(0)}' — 지각을 직접 제시할 수 있나")
    stats["filter_per_k"] = round(fw * per_k, 2)
    en = lines_hit(K.EMOTION_NAMES, "show-vs-tell", "suggestion", lambda m: f"감정 이름 '{m.group(0)}' — 몸·행동으로", "judgment")
    stats["emotion_names"] = en

    # 문장 단위
    sentences = [s.strip() for s in SENT_SPLIT.split(re.sub(r"\n+", " ", text)) if len(s.strip()) > 1]
    narr = [s for s in sentences if not s.startswith(("\"", "“", "「", "'"))]
    lens = [len(s) for s in narr]
    if len(lens) >= 8:
        mean = statistics.mean(lens)
        sd = statistics.pstdev(lens)
        cv = sd / mean if mean else 0
        stats["sentence_len_mean"] = round(mean, 1)
        stats["sentence_len_cv"] = round(cv, 2)
        if cv < 0.35:
            out.append(F("sentence-variance", "suggestion", rel, 1, f"평균 {mean:.0f}자, 변동계수 {cv:.2f}",
                         "문장 길이가 단조로움 (변동계수 < 0.35). 짧은 문장과 긴 문장을 섞어라"))
        run = 1
        for i in range(1, len(lens)):
            if lens[i - 1] and abs(lens[i] - lens[i - 1]) / lens[i - 1] <= 0.15:
                run += 1
                if run == 5:
                    out.append(F("sentence-variance", "note", rel, 1, narr[i][:60], "비슷한 길이의 문장 5개 연속"))
            else:
                run = 1
        if mean < prof.get("mean", 45) * 0.85:
            out.append(F("short-breath", "suggestion", rel, 1, f"서술문 평균 {mean:.0f}자 (목표 {prof.get('mean', 45)}자)",
                         "호흡이 프로필 목표보다 짧음 → /novel-wiki:breath 로 장문화"))
        pro = sum(1 for s in narr if re.match(K.PRONOUN_START, s))
        stats["pronoun_start_ratio"] = round(pro / len(narr), 2)
        if pro / len(narr) > 0.2:
            out.append(F("pronoun-subject", "suggestion", rel, 1, f"{pro}/{len(narr)}문장",
                         f"서술문 {pro/len(narr):.0%}가 '그는/그녀는'으로 시작. 한국어는 주어 생략이 자연스럽다"))
        firsts = [s.split()[0] if s.split() else "" for s in narr]
        for i in range(2, len(firsts)):
            if firsts[i] and firsts[i] == firsts[i - 1] == firsts[i - 2]:
                out.append(F("sentence-starters", "note", rel, 1, narr[i][:60], f"'{firsts[i]}'로 시작하는 문장 3연속"))

    # 반복어(echo): 150자 창 안에서 같은 내용어
    words = [(m.start(), norm_word(m.group(0))) for m in re.finditer(r"\S+", text)]
    skip = bible_names(root)  # 인물·장소 이름 반복은 정상
    echoes = Counter()
    first_pos = {}
    for i, (pos, w) in enumerate(words):
        if len(w) < 2 or w in K.STOP_ECHO or w in skip:
            continue
        for j in range(i + 1, len(words)):
            p2, w2 = words[j]
            if p2 - pos > 150:
                break
            if w2 == w:
                echoes[w] += 1
                first_pos.setdefault(w, p2)
                break
    for w, c in echoes.most_common(12):
        out.append(F("echoes", "note", rel, line_of(text, first_pos[w]), w, f"'{w}' 150자 안 반복 {c}곳"))
    stats["chars"] = chars
    out.sort(key=lambda f: f["location"]["line"])
    return out, stats


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()

    all_out = []
    for fname in a.files:
        path = Path(fname).resolve()
        root = find_root(path)
        extra = []
        crutch = root / "reviews" / "crutch-words.txt"
        if crutch.exists():
            extra = [(re.escape(w.strip()), "작가 지정 금지어") for w in crutch.read_text(encoding="utf-8").splitlines() if w.strip()]
        findings, stats = audit_file(path, root, extra)
        all_out.append((path, root, findings, stats))

    if a.json:
        print(json.dumps([f for _, _, fs, _ in all_out for f in fs], ensure_ascii=False, indent=2))
        return

    labels = {"warning": "꼭 고칠 것", "suggestion": "고려할 것", "note": "참고"}
    for path, root, findings, stats in all_out:
        today = dt.date.today().isoformat()
        c = Counter(f["severity"] for f in findings)
        score = max(0, 100 - c["warning"] * 4 - c["suggestion"] * 2 - c["note"] // 2)
        head = [f"# AI 티·문장 감사 — {path.name} ({today})", "",
                f"인간다움 점수(참고용) **{score}/100** · 꼭 고칠 것 {c['warning']} · 고려할 것 {c['suggestion']} · 참고 {c['note']}",
                f"통계: {json.dumps(stats, ensure_ascii=False)}", ""]
        body = []
        for sev in ("warning", "suggestion", "note"):
            group = [f for f in findings if f["severity"] == sev]
            if not group:
                continue
            body.append(f"## {labels[sev]} ({len(group)})")
            for f in group:
                L = f["location"]
                body.append(f"- L{L['line']} [{f['audit']}] {f['issue']}  \n  > {L['quote']}")
            body.append("")
        report = "\n".join(head + body)
        if a.write:
            out = root / "reviews" / f"deslop-{path.stem}-{today}.md"
            out.parent.mkdir(exist_ok=True)
            out.write_text(report + "\n", encoding="utf-8")
            print(f"리포트: {out}")
        print(report)


if __name__ == "__main__":
    main()
