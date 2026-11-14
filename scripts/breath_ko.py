#!/usr/bin/env python3
"""문장 호흡 측정기. 서술문의 길이 분포, 짧은 문장 연속 구간, 연결어미 밀도를 재고
CLAUDE.md '## 호흡 프로필'의 목표와 비교한다. 대사는 통계에서 뺀다.

사용:
  python3 breath_ko.py manuscript/ch03.md [다른 파일...] [--write] [--json] [--top 8]
"""
import argparse
import datetime as dt
import json
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bible_lib import load_breath_profile, split_frontmatter  # noqa: E402

SENT_END = re.compile(r"(?<=[.?!…])[\"'”’」』]?(?=\s|$)")
DIALOGUE = re.compile(r'^\s*["“「『\']')
# 문장을 끊지 않고 잇는 연결 어미·연결 부호 (근사치)
CONNECT = re.compile(r"(?:고|며|면서|다가|은 채|는 채|ㄴ 채|듯이?|자마자|는데|은데|지만|더니|도록|면|니),|"
                     r"(?:고|며|면서|다가|은 채|는 채|듯|는데|지만|더니)\s")
BUCKETS = [(0, 20, "~20자"), (21, 40, "21~40"), (41, 80, "41~80"), (81, 150, "81~150"), (151, 10**6, "151자~")]


def find_root(p: Path) -> Path:
    for parent in [p.parent, *p.parents]:
        if (parent / "CLAUDE.md").exists() or (parent / "bible").exists():
            return parent
    return p.parent


def sentences_with_lines(text: str):
    """(줄번호, 문장, 대사여부, 문단번호)"""
    out = []
    para = 0
    for ln, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if not s:
            para += 1
            continue
        if s.startswith("#") or re.match(r"^(\*\s*){3,}$|^-{3,}$", s):
            para += 1
            continue
        is_dlg = bool(DIALOGUE.match(s))
        start = 0
        for m in SENT_END.finditer(s):
            seg = s[start:m.end()].strip()
            if seg:
                out.append((ln, seg, is_dlg or bool(DIALOGUE.match(seg)), para))
            start = m.end()
        tail = s[start:].strip()
        if tail:
            out.append((ln, tail, is_dlg, para))
    return out


def analyze(path: Path, prof: dict, top: int):
    raw = path.read_text(encoding="utf-8")
    _, body = split_frontmatter(raw)
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    sents = sentences_with_lines(body)
    narr = [(ln, s, p) for ln, s, d, p in sents if not d]
    lens = [len(s) for _, s, _ in narr]
    res = {"file": str(path), "narration_sentences": len(narr), "dialogue_sentences": len(sents) - len(narr)}
    if not lens:
        res["note"] = "서술문이 없어 측정하지 않음"
        return res, []
    res["mean"] = round(statistics.mean(lens), 1)
    res["median"] = statistics.median(lens)
    res["long_ratio"] = round(100 * sum(1 for x in lens if x >= 80) / len(lens), 1)
    res["short_ratio"] = round(100 * sum(1 for x in lens if x <= 20) / len(lens), 1)
    res["cv"] = round(statistics.pstdev(lens) / res["mean"], 2) if len(lens) >= 3 else None
    res["connect_per_sentence"] = round(sum(len(CONNECT.findall(s)) for _, s, _ in narr) / len(narr), 2)
    res["buckets"] = {lab: sum(1 for x in lens if lo <= x <= hi) for lo, hi, lab in BUCKETS}
    res["target"] = {"mean": prof["mean"], "long_ratio": prof["long_ratio"], "short_run": prof["short_run"]}

    # 짧은 문장(20자 이하) 연속 구간
    runs, cur = [], []
    for item in narr:
        if len(item[1]) <= 20:
            if cur and item[2] != cur[-1][2]:
                if len(cur) > prof["short_run"]:
                    runs.append(cur)
                cur = []
            cur.append(item)
        else:
            if len(cur) > prof["short_run"]:
                runs.append(cur)
            cur = []
    if len(cur) > prof["short_run"]:
        runs.append(cur)

    # 호흡이 가장 짧은 문단
    paras = {}
    for ln, s, p in narr:
        paras.setdefault(p, []).append((ln, s))
    weak = sorted(
        [(statistics.mean(len(s) for _, s in v), v) for v in paras.values() if len(v) >= 3],
        key=lambda x: x[0],
    )[:top]

    targets = []
    for r in sorted(runs, key=len, reverse=True)[:top]:
        targets.append({"kind": "짧은 문장 연속", "line": r[0][0], "count": len(r),
                        "text": " ".join(s for _, s, _ in r)[:160]})
    seen = {t["line"] for t in targets}
    for avg, v in weak:
        if avg < prof["mean"] * 0.7 and v[0][0] not in seen:
            targets.append({"kind": "호흡 짧은 문단", "line": v[0][0], "count": len(v), "avg": round(avg, 1),
                            "text": " ".join(s for _, s in v)[:160]})
    res["verdict"] = verdict(res, prof)
    return res, targets


def verdict(r: dict, prof: dict) -> str:
    gaps = []
    if r["mean"] < prof["mean"] * 0.85:
        gaps.append(f"평균 문장 길이 {r['mean']}자 < 목표 {prof['mean']}자")
    if r["long_ratio"] < prof["long_ratio"] * 0.7:
        gaps.append(f"장문(80자+) 비율 {r['long_ratio']}% < 목표 {prof['long_ratio']}%")
    if r["short_ratio"] > 35:
        gaps.append(f"20자 이하 문장이 {r['short_ratio']}%")
    if r["mean"] > prof["mean"] * 1.6:
        gaps.append(f"평균 {r['mean']}자로 목표보다 훨씬 김. 가독성 확인")
    return "목표 범위" if not gaps else " / ".join(gaps)


def render(res: dict, targets: list) -> str:
    if "mean" not in res:
        return f"# 호흡 분석 — {Path(res['file']).name}\n\n{res.get('note')}\n"
    bar_max = max(res["buckets"].values()) or 1
    lines = [f"# 호흡 분석 — {Path(res['file']).name} ({dt.date.today().isoformat()})", "",
             f"**판정: {res['verdict']}**", "",
             "| 지표 | 현재 | 목표 |", "|---|---|---|",
             f"| 평균 문장 길이 (서술문, 공백 포함) | {res['mean']}자 (중앙값 {res['median']}) | {res['target']['mean']}자 |",
             f"| 장문(80자 이상) 비율 | {res['long_ratio']}% | {res['target']['long_ratio']}% |",
             f"| 20자 이하 문장 비율 | {res['short_ratio']}% | 낮을수록 |",
             f"| 문장당 연결어미 (추정) | {res['connect_per_sentence']} | 장문 모드면 1.5 이상 |",
             f"| 길이 변동계수 | {res['cv']} | 0.5 이상이면 리듬이 살아 있음 |",
             f"| 서술문 / 대사 | {res['narration_sentences']} / {res['dialogue_sentences']} | |",
             "", "## 길이 분포", "```"]
    for lab, n in res["buckets"].items():
        lines.append(f"{lab:>7} {'█' * int(30 * n / bar_max):<30} {n}")
    lines += ["```", "", "## 고칠 후보 (stylist가 이 구간부터 다룬다)"]
    if not targets:
        lines.append("- 없음")
    for t in targets:
        extra = f", 평균 {t['avg']}자" if "avg" in t else ""
        lines.append(f"- L{t['line']} [{t['kind']} {t['count']}문장{extra}]  \n  > {t['text']}")
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--top", type=int, default=8)
    a = ap.parse_args()
    all_res = []
    for f in a.files:
        path = Path(f).resolve()
        root = find_root(path)
        prof = load_breath_profile(root)
        res, targets = analyze(path, prof, a.top)
        all_res.append({**res, "targets": targets})
        if not a.json:
            report = render(res, targets)
            if a.write:
                out = root / "reviews" / f"breath-{path.stem}-{dt.date.today().isoformat()}.md"
                out.parent.mkdir(exist_ok=True)
                out.write_text(report, encoding="utf-8")
                print(f"리포트: {out}")
            print(report)
    if a.json:
        print(json.dumps(all_res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
