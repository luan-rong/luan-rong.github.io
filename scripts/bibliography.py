"""Dependency-free BibTeX / RIS import for the static academic homepage.

Designed for typical exports from arXiv, publishers, Zotero and Google Scholar.
It supports nested BibTeX braces, quoted values, # concatenation, common
month macros, and RIS continuation lines. Unknown fields are preserved.
"""
from __future__ import annotations

import hashlib
import re
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2,
    "mar": 3, "march": 3, "apr": 4, "april": 4,
    "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}
MONTH_LABELS = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _read_braced(text: str, pos: int) -> tuple[str, int]:
    """Return the contents of {...} and position just after the closing brace."""
    assert text[pos] == "{"
    level, start, i = 1, pos + 1, pos + 1
    while i < len(text):
        if text[i] == "\\" and i + 1 < len(text):
            i += 2
            continue
        if text[i] == "{":
            level += 1
        elif text[i] == "}":
            level -= 1
            if level == 0:
                return text[start:i], i + 1
        i += 1
    raise ValueError("Unclosed BibTeX brace")


def _read_quoted(text: str, pos: int) -> tuple[str, int]:
    assert text[pos] == '"'
    i, out = pos + 1, []
    while i < len(text):
        if text[i] == "\\" and i + 1 < len(text):
            out.append(text[i:i+2]); i += 2
        elif text[i] == '"':
            return "".join(out), i + 1
        else:
            out.append(text[i]); i += 1
    raise ValueError("Unclosed BibTeX quoted value")


def _read_field_value(body: str, pos: int, strings: dict[str, str]) -> tuple[str, int]:
    pieces = []
    while pos < len(body):
        while pos < len(body) and body[pos].isspace():
            pos += 1
        if pos >= len(body):
            break
        if body[pos] == "{":
            val, pos = _read_braced(body, pos)
        elif body[pos] == '"':
            val, pos = _read_quoted(body, pos)
        else:
            start = pos
            while pos < len(body) and body[pos] not in ",#\n\r":
                pos += 1
            raw = body[start:pos].strip()
            val = strings.get(raw.lower(), raw)
        pieces.append(val)
        while pos < len(body) and body[pos].isspace():
            pos += 1
        if pos < len(body) and body[pos] == "#":
            pos += 1
            continue
        break
    return "".join(pieces).strip(), pos


def _parse_fields(body: str, strings: dict[str, str]) -> dict[str, str]:
    fields = {}
    pos = 0
    while pos < len(body):
        while pos < len(body) and body[pos] in ", \t\r\n":
            pos += 1
        if pos >= len(body):
            break
        match = re.match(r"([\w:-]+)\s*=\s*", body[pos:])
        if not match:
            raise ValueError(f"Cannot parse BibTeX field near: {body[pos:pos+50]!r}")
        key = match.group(1).lower()
        pos += match.end()
        val, pos = _read_field_value(body, pos, strings)
        fields[key] = val
        if pos < len(body) and body[pos] not in ", \t\r\n":
            raise ValueError(f"Unexpected character in BibTeX entry: {body[pos]!r}")
    return fields


def parse_bibtex(text: str, filename: str = "input.bib") -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    strings = {month: month for month in MONTHS}
    cursor = 0
    while True:
        match = re.search(r"@\s*([a-zA-Z]+)\s*([({])", text[cursor:])
        if not match:
            break
        kind = match.group(1).lower()
        opening = cursor + match.end() - 1
        if text[opening] == "{":
            content, cursor = _read_braced(text, opening)
        else:
            # Rare BibTeX @(...) form. A matching ) is required.
            close = text.find(")", opening + 1)
            if close == -1:
                raise ValueError(f"Unclosed BibTeX entry in {filename}")
            content, cursor = text[opening + 1:close], close + 1
        if kind in {"comment", "preamble"}:
            continue
        if kind == "string":
            strings.update(_parse_fields(content, strings))
            continue
        if "," not in content:
            raise ValueError(f"BibTeX entry in {filename} lacks a citation key / comma")
        key, body = content.split(",", 1)
        if not key.strip():
            raise ValueError(f"Empty citation key in {filename}")
        result.append({"entry_type": kind, "id": key.strip(), "fields": _parse_fields(body, strings), "source": filename})
    return result


RIS_PATTERN = re.compile(r"^([A-Z][A-Z0-9])\s+-\s?(.*)$")


def parse_ris(text: str, filename: str = "input.ris") -> list[dict[str, Any]]:
    items = []
    record: dict[str, list[str]] = {}
    previous = ""
    for line in text.splitlines():
        match = RIS_PATTERN.match(line)
        if match:
            field, value = match.group(1), match.group(2).strip()
            if field == "TY":
                if record:
                    items.append(record)
                record = {"TY": [value]}
            elif field == "ER":
                if record:
                    items.append(record)
                record = {}
                previous = ""
                continue
            else:
                record.setdefault(field, []).append(value)
            previous = field
        elif line.strip() and previous and previous in record:
            record[previous][-1] += " " + line.strip()
    if record:
        items.append(record)
    output = []
    for i, rec in enumerate(items, 1):
        key = (rec.get("ID") or [f"{Path(filename).stem}-{i}"])[0]
        output.append({"entry_type": "ris", "id": key, "fields": rec, "source": filename})
    return output


def clean_tex(value: Any) -> str:
    if value is None:
        return ""
    val = str(value)
    # Preserve the Unicode used in most modern BibTeX exports.
    tex_replacements = {
        r"\&": "&", r"\%": "%", r"\_": "_", r"\-": "-",
        r"\textendash": "–", r"\textemdash": "—", r"\LaTeX": "LaTeX",
        r"\{": "{", r"\}": "}", r"~": " ",
    }
    for src, dest in tex_replacements.items():
        val = val.replace(src, dest)
    # Simple brace grouping ({AI}, {NASA}) should not show in a title.
    val = val.replace("{", "").replace("}", "")
    return re.sub(r"\s+", " ", val).strip()


def format_author(name: str) -> str:
    name = clean_tex(name)
    # BibTeX and RIS commonly export "Surname, Given".
    if "," in name:
        pieces = [part.strip() for part in name.split(",")]
        if len(pieces) >= 2 and pieces[1]:
            return f"{pieces[1]} {pieces[0]}".strip()
    return name


def normalize_authors(raw: Any, ris: bool = False) -> str:
    names = raw if isinstance(raw, list) else re.split(r"\s+and\s+", str(raw or ""), flags=re.I)
    return ", ".join(format_author(n) for n in names if n.strip())


def safe_url(url: Any) -> str:
    value = clean_tex(url).strip()
    if not value:
        return ""
    try:
        parsed = urlsplit(value)
        if parsed.scheme.lower() in {"https", "http"} and parsed.netloc:
            return value
        if parsed.scheme.lower() == "mailto" and parsed.path:
            return value
    except ValueError:
        pass
    return ""


def _ris_get(fields: dict[str, list[str]], *keys: str) -> str:
    for key in keys:
        if fields.get(key):
            return fields[key][0]
    return ""


def _date_parts(raw_date: Any, raw_year: Any, raw_month: Any) -> tuple[int, int, int]:
    for raw in (raw_date, raw_year):
        s = clean_tex(raw)
        match = re.search(r"(?<!\d)(19\d\d|20\d\d|21\d\d)(?:[-/.](\d{1,2}))?(?:[-/.](\d{1,2}))?", s)
        if match:
            year = int(match.group(1))
            month = int(match.group(2) or 0)
            day = int(match.group(3) or 0)
            if not month:
                m = clean_tex(raw_month).lower().strip().rstrip(".")
                month = MONTHS.get(m, int(m) if m.isdigit() else 0)
            if not 1 <= month <= 12:
                month = 0
            if not 1 <= day <= 31:
                day = 0
            if month and day:
                try:
                    date(year, month, day)
                except ValueError:
                    day = 0
            return year, month, day
    return 0, 0, 0


def _category(entry_type: str, venue: str, fields: dict, arxiv_id: str = "") -> str:
    v = venue.lower()
    typ = entry_type.lower()
    if typ in {"inproceedings", "conference", "proceedings", "conf"}:
        return "Conference"
    if typ in {"jour", "jfull", "journal"}:
        return "Preprint" if "arxiv" in v else "Journal"
    if typ == "article" and v and "arxiv" not in v and "preprint" not in v:
        return "Journal"
    if typ in {"unpublished", "unpb"} or "arxiv" in v or "preprint" in v or arxiv_id:
        return "Preprint"
    if typ == "article":
        return "Journal"
    if fields.get("booktitle"):
        return "Conference"
    if fields.get("journal"):
        return "Journal"
    return "Other"


def _arxiv_id(fields: dict[str, Any], url: str) -> str:
    hint = clean_tex(fields.get("eprint", "") or fields.get("arxiv", ""))
    if hint:
        hint = re.sub(r"^arxiv:\s*", "", hint, flags=re.I)
        if re.fullmatch(r"\d{4}\.\d{4,5}(v\d+)?|[a-zA-Z.-]+/\d{7}(v\d+)?", hint):
            return hint
    match = re.search(r"arxiv\.org/(?:abs|pdf)/([^?#/]+)", url, re.I)
    return match.group(1).removesuffix(".pdf") if match else ""


def normalize_entry(entry: dict[str, Any]) -> dict[str, Any]:
    fields = entry["fields"]
    ris = entry["entry_type"] == "ris"
    if ris:
        title = _ris_get(fields, "TI", "T1", "CT", "BT")
        authors = normalize_authors(fields.get("AU") or fields.get("A1") or fields.get("A2") or [], True)
        venue = _ris_get(fields, "T2", "JO", "JF", "JA", "J2", "BT", "PB")
        year, month, day = _date_parts(_ris_get(fields, "DA", "Y1"), _ris_get(fields, "PY"), "")
        raw_url = _ris_get(fields, "UR", "L3")
        doi = _ris_get(fields, "DO")
        kind = _ris_get(fields, "TY")
        pdf = safe_url(_ris_get(fields, "L1", "L2"))
        code, project = "", ""
        abstract = _ris_get(fields, "AB", "N2")
        featured = False
        highlight = ""
        note = _ris_get(fields, "N1")
        extra_fields = {}
    else:
        title = fields.get("title", "")
        authors = normalize_authors(fields.get("author", ""))
        venue = fields.get("journal", "") or fields.get("booktitle", "") or fields.get("publisher", "")
        year, month, day = _date_parts(fields.get("date", ""), fields.get("year", ""), fields.get("month", ""))
        raw_url = fields.get("url", "")
        doi = fields.get("doi", "")
        kind = entry["entry_type"]
        pdf = safe_url(fields.get("pdf", ""))
        code = safe_url(fields.get("code", ""))
        project = safe_url(fields.get("project", ""))
        abstract = fields.get("abstract", "")
        featured = str(fields.get("featured", "")).lower() in ("true", "yes", "1")
        highlight = fields.get("highlight", "")
        note = fields.get("note", "")
        extra_fields = fields

    title = clean_tex(title)
    if not title:
        raise ValueError(f"Missing publication title in {entry['source']} ({entry['id']})")
    venue = clean_tex(venue)
    doi = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", clean_tex(doi), flags=re.I)
    url = safe_url(raw_url)
    if not url and doi:
        url = safe_url(f"https://doi.org/{doi}")
    arxiv_id = _arxiv_id(extra_fields, url)
    category = _category(kind, venue, extra_fields, arxiv_id)
    if category == "Preprint" and not venue:
        venue = "arXiv preprint" if arxiv_id else "Preprint"
    if not venue:
        venue = "Publication"
    if category == "Preprint" and arxiv_id and not url:
        url = f"https://arxiv.org/abs/{arxiv_id}"

    links = []
    if url:
        links.append({"label": "arXiv" if "arxiv.org" in urlsplit(url).netloc else "Paper", "url": url})
    for label, href in (("PDF", pdf), ("Code", code), ("Project", project)):
        if href and all(link["url"] != href for link in links):
            links.append({"label": label, "url": href})
    if doi and not any("doi.org/" in link["url"] for link in links):
        doi_href = safe_url(f"https://doi.org/{doi}")
        if doi_href:
            links.append({"label": "DOI", "url": doi_href})
    if not url and arxiv_id:
        url = f"https://arxiv.org/abs/{arxiv_id}"

    display_date = (f"{MONTH_LABELS[month]} {year}" if month else str(year)) if year else "Date unavailable"
    return {
        "id": entry["id"],
        "title": title,
        "authors": authors,
        "venue": venue,
        "year": year,
        "month": month,
        "day": day,
        "date_label": display_date,
        "sort_key": f"{year:04d}-{month:02d}-{day:02d}",
        "category": category,
        "url": url,
        "doi": doi,
        "arxiv_id": arxiv_id,
        "links": links,
        "featured": featured,
        "highlight": clean_tex(highlight),
        "abstract": clean_tex(abstract),
        "note": clean_tex(note),
        "source": entry["source"],
    }


def _dedupe_key(pub: dict) -> str:
    # Title-based grouping catches imports of the same paper as .bib and .ris.
    # Publication versions take precedence over a preprint in that case.
    title = re.sub(r"[^a-z0-9]+", "", pub["title"].lower())
    if title:
        return f"title:{title}"
    if pub["doi"]:
        return f"doi:{pub['doi'].lower()}"
    return pub["id"].lower()


def load_publications(folder: Path) -> list[dict]:
    if not folder.exists():
        raise FileNotFoundError(f"No publication folder: {folder}")
    entries: list[dict] = []
    for path in sorted(folder.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".bib", ".ris"}:
            continue
        text = path.read_text(encoding="utf-8-sig")
        relative = str(path.relative_to(folder))
        try:
            entries.extend(parse_bibtex(text, relative) if path.suffix.lower() == ".bib" else parse_ris(text, relative))
        except Exception as err:
            raise ValueError(f"Could not parse {relative}: {err}") from err

    candidates = [normalize_entry(entry) for entry in entries]
    priority = {"Journal": 4, "Conference": 3, "Preprint": 2, "Other": 1}
    unique = {}
    for p in candidates:
        key = _dedupe_key(p)
        old = unique.get(key)
        if not old or (priority[p["category"]], p["sort_key"]) > (priority[old["category"]], old["sort_key"]):
            unique[key] = p
    return sorted(unique.values(), key=lambda p: (p["sort_key"], p["title"].lower()), reverse=True)
