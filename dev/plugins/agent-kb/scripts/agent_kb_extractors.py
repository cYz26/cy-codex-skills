from __future__ import annotations

import importlib.util
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree

from agent_kb_crawl4ai import capability as crawl4ai_capability
from agent_kb_markitdown import capability as markitdown_capability
from agent_kb_markitdown import convert as try_markitdown


TEXT_EXTENSIONS = {".md", ".markdown", ".txt", ".csv", ".json", ".xml"}


class TextHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str):
        self.parts.extend(filter(None, [data.strip()]))


def extractor_capabilities():
    return {"markitdown": markitdown_capability(), "crawl4ai": crawl4ai_capability()}


def extract_markdown(path: Path):
    markitdown = try_markitdown(path)
    if markitdown["ok"]:
        return markitdown
    fallback = fallback_extract(path)
    if fallback["ok"]:
        return fallback
    return {True: markitdown, False: fallback}[markitdown["available"]]


def fallback_extract(path: Path):
    suffix = path.suffix.lower()
    extractors = dict.fromkeys(TEXT_EXTENSIONS, extract_text)
    extractors.update({
        ".html": extract_html,
        ".htm": extract_html,
        ".pdf": extract_pdf,
        ".docx": extract_docx,
        ".xlsx": extract_xlsx,
    })
    extractor = extractors.get(suffix)
    return extractor(path) if extractor else unsupported(suffix)


def extract_text(path: Path):
    return {"ok": True, "extractor": "text", "text": path.read_text(encoding="utf-8", errors="replace")}


def extract_html(path: Path):
    parser = TextHTMLParser()
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    return {"ok": True, "extractor": "html", "text": "\n\n".join(parser.parts)}


def extract_pdf(path: Path):
    if importlib.util.find_spec("pypdf") is None:
        return unsupported(".pdf")
    from pypdf import PdfReader

    text = "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
    return {"ok": True, "extractor": "pypdf", "text": text}


def extract_docx(path: Path):
    with zipfile.ZipFile(path) as archive:
        xml = archive.read("word/document.xml")
    root = ElementTree.fromstring(xml)
    texts = [node.text or "" for node in root.iter() if node.tag.endswith("}t")]
    return {"ok": True, "extractor": "docx-zip", "text": "\n".join(texts)}


def extract_xlsx(path: Path):
    if importlib.util.find_spec("openpyxl") is None:
        return unsupported(".xlsx")
    from openpyxl import load_workbook

    workbook = load_workbook(path, data_only=True, read_only=True)
    rows = []
    for sheet in workbook.worksheets:
        rows.append(f"# {sheet.title}")
        rows.extend("\t".join("" if cell is None else str(cell) for cell in row) for row in sheet.values)
    return {"ok": True, "extractor": "openpyxl", "text": "\n".join(rows)}


def unsupported(suffix: str):
    return {"ok": False, "extractor": "unsupported", "error": f"unsupported extension {suffix}", "text": ""}
