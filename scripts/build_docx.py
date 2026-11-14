#!/usr/bin/env python3
"""manuscript/ 장 파일을 한 권의 .docx로 합본한다. 표준 라이브러리만 사용한다 (Word, pandoc 불필요).

사용:
  python3 build_docx.py --project . [--preset contest|reading|review] [--title 제목] [--author 이름]
                        [--from 1 --to 10] [--font 바탕] [--size 11] [--spacing 160]
                        [--chapter-label "제{n}장"] [--no-check] [--strict] [--out 경로.docx]

프리셋
  contest : 공모전·투고용. A4, 11pt, 줄간격 160%, 표지에 원고지 매수(200자 기준 추정)
  reading : 읽기용. 신국판(152×225mm), 10.5pt, 줄간격 170%
  review  : 검토·인쇄용. A4, 11pt, 줄간격 200%, 넓은 여백, 장 번호·파일명 표시

본문 변환 규칙
  - frontmatter, HTML 주석 <!-- -->, Obsidian 주석 %% %% 는 제거
  - [[링크|표시]] → 표시, [[링크]] → 링크
  - 첫 줄 '# 제목' → 장 제목. 없으면 --chapter-label 형식
  - '* * *' / '***' / '---' 단독 줄 → 가운데 장면 구분
  - 빈 줄로 문단 구분. **굵게**, *기울임* 지원
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bible_lib import ch_label, manuscript_chapters, split_frontmatter  # noqa: E402

MM = 56.7  # twips per mm

PRESETS = {
    "contest": dict(page=(210, 297), margin=(25, 20, 25, 20), size=11, spacing=160, header_info=False),
    "reading": dict(page=(152, 225), margin=(20, 18, 20, 18), size=10.5, spacing=170, header_info=False),
    "review": dict(page=(210, 297), margin=(25, 30, 25, 30), size=11, spacing=200, header_info=True),
}
SCENE_BREAK = re.compile(r"^\s*(\*\s*\*\s*\*|\*{3,}|-{3,}|＊\s*＊\s*＊)\s*$")


# ------------------------------------------------------------------ 텍스트 정리
def clean(text: str) -> str:
    _, body = split_frontmatter(text)
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    body = re.sub(r"%%.*?%%", "", body, flags=re.S)
    body = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", body)
    body = re.sub(r"\[\[([^\]]+)\]\]", r"\1", body)
    return body.strip()


def blocks(body: str):
    """('title', str) | ('break', None) | ('para', str) 를 순서대로 낸다."""
    lines = body.splitlines()
    title = None
    if lines and lines[0].startswith("# "):
        title = lines[0][2:].strip()
        lines = lines[1:]
    if title:
        yield ("title", title)
    buf: list[str] = []

    def flush():
        if buf:
            yield ("para", " ".join(s.strip() for s in buf))
            buf.clear()

    for line in lines:
        if SCENE_BREAK.match(line):
            yield from flush()
            yield ("break", None)
        elif not line.strip():
            yield from flush()
        elif line.startswith("#"):
            yield from flush()
            yield ("subtitle", line.lstrip("#").strip())
        else:
            buf.append(line)
    yield from flush()


def plain_len(body: str) -> int:
    text = re.sub(r"^#.*$", "", body, flags=re.M)
    text = re.sub(r"[*_]", "", text)
    text = re.sub(r"\n+", "\n", text)
    return len(text.strip())


# ------------------------------------------------------------------ XML 조각
def runs(text: str) -> str:
    out = []
    for part in re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*)", text):
        if not part:
            continue
        rpr = ""
        if part.startswith("**") and part.endswith("**"):
            part, rpr = part[2:-2], "<w:rPr><w:b/></w:rPr>"
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            part, rpr = part[1:-1], "<w:rPr><w:i/></w:rPr>"
        out.append(f'<w:r>{rpr}<w:t xml:space="preserve">{escape(part)}</w:t></w:r>')
    return "".join(out)


def p(style: str, inner: str, page_break_before: bool = False) -> str:
    ppr = f'<w:pPr><w:pStyle w:val="{style}"/>{"<w:pageBreakBefore/>" if page_break_before else ""}</w:pPr>'
    return f"<w:p>{ppr}{inner}</w:p>"


def styles_xml(font: str, size: float, spacing: int) -> str:
    sz = int(round(size * 2))
    line = int(240 * spacing / 100)
    rfonts = f'<w:rFonts w:ascii="{font}" w:hAnsi="{font}" w:eastAsia="{font}" w:cs="{font}"/>'
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
 <w:docDefaults>
  <w:rPrDefault><w:rPr>{rfonts}<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/><w:lang w:val="ko-KR" w:eastAsia="ko-KR"/></w:rPr></w:rPrDefault>
  <w:pPrDefault><w:pPr><w:spacing w:after="0" w:line="{line}" w:lineRule="auto"/><w:jc w:val="both"/></w:pPr></w:pPrDefault>
 </w:docDefaults>
 <w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/></w:style>
 <w:style w:type="paragraph" w:styleId="Body"><w:name w:val="본문"/><w:basedOn w:val="Normal"/><w:qFormat/>
  <w:pPr><w:ind w:firstLineChars="100" w:firstLine="{sz * 10}"/></w:pPr></w:style>
 <w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:qFormat/>
  <w:pPr><w:spacing w:before="4800" w:after="600"/><w:jc w:val="center"/></w:pPr><w:rPr><w:b/><w:sz w:val="{sz * 2 + 8}"/></w:rPr></w:style>
 <w:style w:type="paragraph" w:styleId="Meta"><w:name w:val="표지 정보"/><w:basedOn w:val="Normal"/>
  <w:pPr><w:spacing w:after="120"/><w:jc w:val="center"/></w:pPr></w:style>
 <w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Body"/><w:qFormat/>
  <w:pPr><w:keepNext/><w:spacing w:before="1200" w:after="720"/><w:jc w:val="center"/><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/><w:sz w:val="{sz + 8}"/></w:rPr></w:style>
 <w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:next w:val="Body"/><w:qFormat/>
  <w:pPr><w:keepNext/><w:spacing w:before="360" w:after="240"/><w:jc w:val="center"/><w:outlineLvl w:val="1"/></w:pPr><w:rPr><w:b/></w:rPr></w:style>
 <w:style w:type="paragraph" w:styleId="SceneBreak"><w:name w:val="장면 구분"/><w:basedOn w:val="Normal"/>
  <w:pPr><w:spacing w:before="240" w:after="240"/><w:jc w:val="center"/></w:pPr></w:style>
 <w:style w:type="paragraph" w:styleId="Footer"><w:name w:val="footer"/><w:basedOn w:val="Normal"/><w:pPr><w:jc w:val="center"/></w:pPr><w:rPr><w:sz w:val="{max(sz - 4, 16)}"/></w:rPr></w:style>
 <w:style w:type="paragraph" w:styleId="Header"><w:name w:val="header"/><w:basedOn w:val="Normal"/><w:pPr><w:jc w:val="right"/></w:pPr><w:rPr><w:sz w:val="{max(sz - 4, 16)}"/><w:color w:val="808080"/></w:rPr></w:style>
</w:styles>'''


FOOTER = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:pPr><w:pStyle w:val="Footer"/></w:pPr>
<w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText xml:space="preserve"> PAGE </w:instrText></w:r><w:r><w:fldChar w:fldCharType="separate"/></w:r><w:r><w:t>1</w:t></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r></w:p></w:ftr>'''


def header_xml(text: str) -> str:
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:hdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            f'<w:p><w:pPr><w:pStyle w:val="Header"/></w:pPr><w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p></w:hdr>')


def write_docx(dst: Path, body_xml: str, title: str, author: str, cfg: dict, font: str, header_text: str | None):
    pw, ph = (int(v * MM) for v in cfg["page"])
    t, r, b, l = (int(v * MM) for v in cfg["margin"])
    hdr_ref = '<w:headerReference w:type="default" r:id="rIdHeader"/>' if header_text else ""
    sect = (f'<w:sectPr>{hdr_ref}<w:footerReference w:type="default" r:id="rIdFooter"/>'
            f'<w:pgSz w:w="{pw}" w:h="{ph}"/><w:pgMar w:top="{t}" w:right="{r}" w:bottom="{b}" w:left="{l}" '
            f'w:header="567" w:footer="567" w:gutter="0"/><w:titlePg/></w:sectPr>')
    document = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                f"<w:body>{body_xml}{sect}</w:body></w:document>")
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rels = ['<Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>',
            '<Relationship Id="rIdSettings" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/>',
            '<Relationship Id="rIdFooter" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>']
    overrides = ['<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>',
                 '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>',
                 '<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>',
                 '<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>',
                 '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>',
                 '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>']
    if header_text:
        rels.append('<Relationship Id="rIdHeader" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="header1.xml"/>')
        overrides.append('<Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>')
    files = {
        "[Content_Types].xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>' + "".join(overrides) + "</Types>",
        "_rels/.rels": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
            '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
            "</Relationships>",
        "word/_rels/document.xml.rels": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + "".join(rels) + "</Relationships>",
        "word/document.xml": document,
        "word/styles.xml": styles_xml(font, cfg["size"], cfg["spacing"]),
        "word/settings.xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:defaultTabStop w:val="800"/><w:themeFontLang w:val="ko-KR" w:eastAsia="ko-KR"/></w:settings>',
        "word/footer1.xml": FOOTER,
        "docProps/core.xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            f"<dc:title>{escape(title)}</dc:title><dc:creator>{escape(author)}</dc:creator><dc:language>ko-KR</dc:language>"
            f'<dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>'
            f'<dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified></cp:coreProperties>',
        "docProps/app.xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
            "<Application>novel-wiki</Application></Properties>",
    }
    if header_text:
        files["word/header1.xml"] = header_xml(header_text)
    dst.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)


# ------------------------------------------------------------------ 사전 점검
def preflight(root: Path, chapters: dict[int, Path]) -> list[str]:
    notes = []
    here = Path(__file__).resolve().parent
    try:
        res = subprocess.run([sys.executable, str(here / "lint_bible.py"), "--project", str(root), "--json"],
                             capture_output=True, text=True, timeout=120)
        findings = json.loads(res.stdout or "[]")
        warn = [f for f in findings if f["severity"] == "warning"]
        if warn:
            notes.append(f"연속성 경고 {len(warn)}개 (예: {warn[0]['issue']}) → /novel-wiki:lint")
    except Exception as e:
        notes.append(f"린트 실행 실패: {e}")
    try:
        import deslop_ko
        low = []
        for n, path in chapters.items():
            fs, _ = deslop_ko.audit_file(path, root, [])
            w = sum(1 for f in fs if f["severity"] == "warning")
            s = sum(1 for f in fs if f["severity"] == "suggestion")
            no = sum(1 for f in fs if f["severity"] == "note")
            score = max(0, 100 - w * 4 - s * 2 - no // 2)
            if score < 70:
                low.append(f"{ch_label(n)}({score})")
        if low:
            notes.append(f"AI 티 점수 70 미만: {', '.join(low)} → /novel-wiki:deslop")
    except Exception as e:
        notes.append(f"AI 티 검사 실패: {e}")
    for n, path in chapters.items():
        raw = path.read_text(encoding="utf-8")
        if re.search(r"\bTODO\b|\bTK\b|\?\?\?|【.*?】", raw):
            notes.append(f"{ch_label(n)}: TODO·TK·??? 같은 작업 표시가 남아 있음")
    return notes


# ------------------------------------------------------------------ 메인
def guess_title(root: Path) -> str:
    cm = root / "CLAUDE.md"
    if cm.exists():
        m = re.match(r"#\s*(.+?)\s*—", cm.read_text(encoding="utf-8"))
        if m:
            return m.group(1)
    return root.name


def guess_author() -> str:
    try:
        return subprocess.run(["git", "config", "user.name"], capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        return ""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    ap.add_argument("--preset", default="contest", choices=PRESETS)
    ap.add_argument("--title")
    ap.add_argument("--author")
    ap.add_argument("--from", dest="start", type=int)
    ap.add_argument("--to", dest="end", type=int)
    ap.add_argument("--font", default="바탕")
    ap.add_argument("--size", type=float)
    ap.add_argument("--spacing", type=int, help="줄간격 %%")
    ap.add_argument("--chapter-label", default="{n}장")
    ap.add_argument("--no-title-page", action="store_true")
    ap.add_argument("--no-check", action="store_true")
    ap.add_argument("--strict", action="store_true", help="점검에서 문제가 나오면 빌드 중단")
    ap.add_argument("--out")
    a = ap.parse_args()

    root = Path(a.project).resolve()
    chapters = manuscript_chapters(root)
    chapters = {n: p for n, p in sorted(chapters.items())
                if (a.start is None or n >= a.start) and (a.end is None or n <= a.end)}
    if not chapters:
        sys.exit("합칠 원고가 없습니다 (manuscript/chNN.md).")

    cfg = dict(PRESETS[a.preset])
    if a.size:
        cfg["size"] = a.size
    if a.spacing:
        cfg["spacing"] = a.spacing
    title = a.title or guess_title(root)
    author = a.author or guess_author()

    notes = [] if a.no_check else preflight(root, chapters)
    if notes:
        print("사전 점검:")
        for n in notes:
            print(f"  ⚠️ {n}")
        if a.strict:
            sys.exit("--strict: 점검 항목을 해결한 뒤 다시 빌드하세요.")

    total_chars = 0
    parts = []
    if not a.no_title_page:
        parts.append(p("Title", runs(title)))
        if author:
            parts.append(p("Meta", runs(author)))
    first = True
    for n, path in chapters.items():
        body = clean(path.read_text(encoding="utf-8"))
        total_chars += plain_len(body)
        has_title = False
        for kind, val in blocks(body):
            if kind == "title":
                parts.append(p("Heading1", runs(val), page_break_before=not (first and a.no_title_page)))
                has_title = True
            elif kind == "subtitle":
                parts.append(p("Heading2", runs(val)))
            elif kind == "break":
                parts.append(p("SceneBreak", '<w:r><w:t xml:space="preserve">*   *   *</w:t></w:r>'))
            else:
                if not has_title:
                    parts.append(p("Heading1", runs(a.chapter_label.format(n=n)), page_break_before=not (first and a.no_title_page)))
                    has_title = True
                parts.append(p("Body", runs(val)))
        first = False

    manuscript_pages = round(total_chars / 200)
    if not a.no_title_page:
        meta = [f"{len(chapters)}장 · 약 {total_chars:,}자 · 원고지 약 {manuscript_pages:,}매 (200자 기준 추정)"]
        if a.start or a.end:
            meta.append(f"수록: {ch_label(min(chapters))} ~ {ch_label(max(chapters))}")
        parts[2 if author else 1:2 if author else 1] = [p("Meta", runs(m)) for m in meta]

    today = dt.date.today().isoformat()
    safe = re.sub(r'[\\/:*?"<>|]', "_", title)
    dst = Path(a.out).resolve() if a.out else root / "builds" / today / f"{safe}-{a.preset}.docx"
    header = f"{title} — {a.preset} 빌드 {today}" if cfg["header_info"] else None
    write_docx(dst, "".join(parts), title, author, cfg, a.font, header)

    report = dst.with_suffix(".build.md")
    report.write_text("\n".join([
        f"# 빌드 기록 — {title} ({today})", "",
        f"- 프리셋: {a.preset} · 글꼴 {a.font} {cfg['size']}pt · 줄간격 {cfg['spacing']}%",
        f"- 수록: {', '.join(ch_label(n) for n in chapters)}",
        f"- 분량: 약 {total_chars:,}자 · 원고지 약 {manuscript_pages:,}매 (공백 포함 글자 수 ÷ 200, 추정치)",
        "", "## 사전 점검", *([f"- {x}" for x in notes] or ["- 문제 없음" if not a.no_check else "- 생략"]),
    ]) + "\n", encoding="utf-8")
    print(f"빌드 완료: {dst}")
    print(f"  {len(chapters)}장 · 약 {total_chars:,}자 · 원고지 약 {manuscript_pages:,}매 · 기록 {report.name}")


if __name__ == "__main__":
    main()
