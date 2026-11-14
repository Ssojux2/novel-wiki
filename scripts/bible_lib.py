"""novel-wiki 공용 파서.

바이블 페이지(마크다운 + YAML frontmatter + 표)를 읽고,
장(chapter) 시점별 상태를 접어(fold) 계산한다.
표준 라이브러리만 사용한다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

CH_RE = re.compile(r"ch\s*0*(\d+)", re.IGNORECASE)
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
ENTITY_DIRS = ["characters", "places", "factions", "tech", "rules", "arcs", "chapters"]
STATEFUL_DIRS = ["characters", "places", "factions", "tech"]
DEAD_WORDS = ("사망", "죽음", "dead", "deceased")


def ch_num(value: str | int | None) -> int | None:
    """'ch07', 'ch7', '7', 7 -> 7. 실패하면 None."""
    if value is None:
        return None
    if isinstance(value, int):
        return value
    s = str(value).strip()
    m = CH_RE.search(s)
    if m:
        return int(m.group(1))
    if s.isdigit():
        return int(s)
    return None


def ch_label(n: int) -> str:
    return f"ch{n:02d}"


# ---------------------------------------------------------------- frontmatter
def split_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    raw = text[3:end].strip("\n")
    body = text[end + 4 :].lstrip("\n")
    meta: dict = {}
    for line in raw.splitlines():
        if ":" not in line or line.strip().startswith("#"):
            continue
        key, _, val = line.partition(":")
        val = val.strip()
        if val.startswith("[") and val.endswith("]"):
            items = [v.strip().strip("'\"") for v in val[1:-1].split(",")]
            meta[key.strip()] = [i for i in items if i]
        else:
            meta[key.strip()] = val.strip("'\"")
    return meta, body


# ---------------------------------------------------------------- tables
def parse_tables(body: str) -> dict[str, list[dict]]:
    """'## 제목' 아래의 첫 마크다운 표를 {제목: [행 dict]} 로 반환."""
    tables: dict[str, list[dict]] = {}
    heading = "_"
    lines = body.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("#"):
            heading = line.lstrip("#").strip()
            i += 1
            continue
        if line.strip().startswith("|") and i + 1 < len(lines) and re.match(
            r"^\s*\|?\s*:?-{2,}", lines[i + 1]
        ):
            header = [c.strip() for c in line.strip().strip("|").split("|")]
            rows = []
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                cells += [""] * (len(header) - len(cells))
                rows.append(dict(zip(header, cells)))
                i += 1
            tables.setdefault(heading, rows)
            continue
        i += 1
    return tables


def find_table(tables: dict[str, list[dict]], *keywords: str) -> list[dict]:
    for title, rows in tables.items():
        if any(k in title for k in keywords):
            return rows
    return []


# ---------------------------------------------------------------- pages
@dataclass
class Page:
    path: Path
    kind: str
    title: str
    meta: dict
    body: str
    aliases: list[str] = field(default_factory=list)

    @property
    def names(self) -> list[str]:
        out = [self.title] + list(self.aliases)
        return [n for n in out if n]

    @property
    def tables(self) -> dict[str, list[dict]]:
        return parse_tables(self.body)


def load_page(path: Path, kind: str) -> Page:
    text = path.read_text(encoding="utf-8")
    meta, body = split_frontmatter(text)
    title = meta.get("title") or path.stem
    aliases = meta.get("aliases") or []
    if isinstance(aliases, str):
        aliases = [a.strip() for a in aliases.split(",") if a.strip()]
    return Page(path, kind, title, meta, body, aliases)


def load_bible(root: Path) -> dict[str, list[Page]]:
    bible = root / "bible"
    out: dict[str, list[Page]] = {}
    for d in ENTITY_DIRS:
        folder = bible / d
        out[d] = (
            [load_page(p, d) for p in sorted(folder.glob("*.md")) if not p.name.startswith("_")]
            if folder.exists()
            else []
        )
    return out


def find_entity(bible: dict[str, list[Page]], name: str) -> Page | None:
    name = name.strip()
    for d in STATEFUL_DIRS + ["rules", "arcs"]:
        for p in bible.get(d, []):
            if name == p.path.stem or name in p.names:
                return p
    return None


# ---------------------------------------------------------------- state fold
STATE_KEYS_SET = ("앎", "소지품", "knows", "items")
STATE_KEYS_MAP = ("관계", "relations")


def _apply_set(current: list[str], cell: str) -> list[str]:
    items = [x.strip() for x in re.split(r"[,，;]", cell) if x.strip()]
    if not items:
        return current
    if all(x[0] in "+-" for x in items):
        cur = list(current)
        for x in items:
            v = x[1:].strip()
            if x[0] == "+" and v not in cur:
                cur.append(v)
            elif x[0] == "-" and v in cur:
                cur.remove(v)
        return cur
    return [x.lstrip("+") for x in items]


def _apply_map(current: dict, cell: str) -> dict:
    cur = dict(current)
    for part in re.split(r"[,，;]", cell):
        if ":" in part:
            k, _, v = part.partition(":")
            k, v = k.strip(), v.strip()
            if k:
                if v in ("-", "삭제"):
                    cur.pop(k, None)
                else:
                    cur[k] = v
    return cur


def state_rows(page: Page) -> list[dict]:
    rows = find_table(page.tables, "상태 변화", "상태변화", "State")
    good = []
    for r in rows:
        key = r.get("장") or r.get("ch") or r.get("chapter") or ""
        n = ch_num(key)
        if n is not None:
            good.append({**r, "_ch": n})
    return sorted(good, key=lambda r: r["_ch"])


def state_at(page: Page, chapter: int) -> dict:
    """chapter 장 '끝' 시점의 상태. 그 장 이전에 처음 등장하지 않았으면 present=False."""
    state: dict = {"present": False, "source_rows": []}
    for r in state_rows(page):
        if r["_ch"] > chapter:
            break
        state["present"] = True
        state["source_rows"].append(ch_label(r["_ch"]))
        for k, v in r.items():
            if k.startswith("_") or k in ("장", "ch", "chapter") or not v:
                continue
            if k in STATE_KEYS_SET:
                state[k] = _apply_set(state.get(k, []), v)
            elif k in STATE_KEYS_MAP:
                state[k] = _apply_map(state.get(k, {}), v)
            else:
                state[k] = v
    state["dead"] = any(w in str(state.get("상태", "")) for w in DEAD_WORDS)
    return state


def death_chapter(page: Page) -> int | None:
    for r in state_rows(page):
        if any(w in r.get("상태", "") for w in DEAD_WORDS):
            return r["_ch"]
    return None


def format_state(page: Page, chapter: int) -> str:
    s = state_at(page, chapter)
    if not s["present"]:
        return f"- **{page.title}**: {ch_label(chapter)} 시점까지 기록 없음"
    parts = []
    for k, v in s.items():
        if k in ("present", "source_rows", "dead"):
            continue
        if isinstance(v, list):
            v = ", ".join(v) if v else "(없음)"
        elif isinstance(v, dict):
            v = ", ".join(f"{a}: {b}" for a, b in v.items()) if v else "(없음)"
        parts.append(f"  - {k}: {v}")
    flag = " ⚠️사망" if s["dead"] else ""
    head = f"- **{page.title}**{flag} ({ch_label(chapter)} 끝 기준, 반영: {', '.join(s['source_rows'])})"
    return "\n".join([head] + parts)


# ---------------------------------------------------------------- manuscript
def manuscript_chapters(root: Path) -> dict[int, Path]:
    out: dict[int, Path] = {}
    folder = root / "manuscript"
    if not folder.exists():
        return out
    for p in sorted(folder.rglob("*.md")):
        n = ch_num(p.stem)
        if n is not None:
            out[n] = p
    return out


def read_tsv_table(path: Path, *keywords: str) -> list[dict]:
    if not path.exists():
        return []
    meta, body = split_frontmatter(path.read_text(encoding="utf-8"))
    tables = parse_tables(body)
    if keywords:
        rows = find_table(tables, *keywords)
        if rows:
            return rows
    for rows in tables.values():
        if rows:
            return rows
    return []


def mentions(text: str, names: list[str]) -> bool:
    for n in names:
        if len(n) >= 2 and n in text:
            return True
    return False


# ---------------------------------------------------------------- 호흡 프로필
BREATH_DEFAULT = {"mean": 45, "long_ratio": 25, "short_run": 2, "modes": [], "scene_modes": {}}


def load_breath_profile(root: Path) -> dict:
    """CLAUDE.md의 '## 호흡 프로필' 섹션을 읽는다. 없으면 기본값."""
    prof = dict(BREATH_DEFAULT)
    prof["scene_modes"] = {}
    cm = root / "CLAUDE.md"
    if not cm.exists():
        return prof
    text = cm.read_text(encoding="utf-8")
    m = re.search(r"^##\s*호흡 프로필\s*$(.*?)(?=^##\s|\Z)", text, flags=re.M | re.S)
    if not m:
        return prof
    for line in m.group(1).splitlines():
        line = line.strip().lstrip("-").strip()
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        v = v.split("←")[0].strip()
        num = re.search(r"\d+", v)
        if "평균 문장 길이" in k and num:
            prof["mean"] = int(num.group())
        elif "장문" in k and "비율" in k and num:
            prof["long_ratio"] = int(num.group())
        elif "연속 허용" in k and num:
            prof["short_run"] = int(num.group())
        elif "기본 모드" in k:
            prof["modes"] = [x.strip() for x in re.split(r"[,，]", v) if x.strip()]
        elif "장면별 모드" in k:
            for pair in re.split(r"[,，]", v):
                if "=" in pair:
                    a, _, b = pair.partition("=")
                    prof["scene_modes"][a.strip()] = b.strip()
    return prof
