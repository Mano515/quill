"""Phase 4 — Advanced extraction: tables, images, links, form fields, language detection."""

from pathlib import Path


def extract_tables(
    input: Path,
    output: Path | None = None,
    pages: list[int] | None = None,
    fmt: str = "csv",
) -> list[dict]:
    """
    Extract tables from a PDF.
    Returns a list of {page, table_index, data} dicts.
    If output is given, exports to CSV or Excel.
    fmt: 'csv' | 'excel'
    """
    import pdfplumber

    results = []
    with pdfplumber.open(input) as pdf:
        target = set(pages) if pages else set(range(1, len(pdf.pages) + 1))
        for page_num in target:
            page = pdf.pages[page_num - 1]
            tables = page.extract_tables()
            for i, table in enumerate(tables):
                results.append({"page": page_num, "table_index": i, "data": table})

    if output and results:
        import pandas as pd

        if fmt == "excel":
            with pd.ExcelWriter(output) as writer:
                for r in results:
                    df = pd.DataFrame(r["data"])
                    sheet = f"p{r['page']}_t{r['table_index']}"
                    df.to_excel(writer, sheet_name=sheet, index=False, header=False)
        else:
            # CSV: one file per table, suffixed
            stem = output.stem
            for r in results:
                df = pd.DataFrame(r["data"])
                path = output.parent / f"{stem}_p{r['page']}_t{r['table_index']}.csv"
                df.to_csv(path, index=False, header=False)

    return results


def extract_images(input: Path, output_dir: Path) -> list[Path]:
    """Extract all embedded images from a PDF, saving them to output_dir."""
    import fitz

    output_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(input))
    saved: list[Path] = []

    for page_num, page in enumerate(doc, start=1):
        for img_index, img in enumerate(page.get_images(full=True)):
            xref = img[0]
            base_image = doc.extract_image(xref)
            ext = base_image["ext"]
            data = base_image["image"]
            out = output_dir / f"page{page_num}_img{img_index}.{ext}"
            out.write_bytes(data)
            saved.append(out)

    doc.close()
    return saved


def extract_links(input: Path, pages: list[int] | None = None) -> list[dict]:
    """
    Extract all hyperlinks from a PDF.
    Returns list of {page, uri, rect} dicts.
    """
    import fitz

    doc = fitz.open(str(input))
    target = set(pages) if pages else set(range(1, len(doc) + 1))
    results = []

    for page_num in target:
        page = doc[page_num - 1]
        for link in page.get_links():
            if link.get("uri"):
                results.append({
                    "page": page_num,
                    "uri": link["uri"],
                    "rect": list(link["from"]),
                })

    doc.close()
    return results


def extract_form_fields(input: Path) -> list[dict]:
    """Extract all form field names and their current values."""
    from pypdf import PdfReader

    reader = PdfReader(input)
    fields = reader.get_fields()
    if not fields:
        return []

    return [
        {
            "name": name,
            "value": field.get("/V"),
            "type": str(field.get("/FT", "")),
        }
        for name, field in fields.items()
    ]


def extract_layout(input: Path, pages: list[int] | None = None) -> list[dict]:
    """
    Extract text with preserved layout (position, font size, font name).
    Returns list of {page, text, x0, y0, x1, y1, size, font} dicts.
    """
    import pdfplumber

    results = []
    with pdfplumber.open(input) as pdf:
        target = set(pages) if pages else set(range(1, len(pdf.pages) + 1))
        for page_num in target:
            page = pdf.pages[page_num - 1]
            for word in page.extract_words(extra_attrs=["size", "fontname"]):
                results.append({
                    "page": page_num,
                    "text": word["text"],
                    "x0": word["x0"],
                    "y0": word["top"],
                    "x1": word["x1"],
                    "y1": word["bottom"],
                    "size": word.get("size"),
                    "font": word.get("fontname"),
                })
    return results


def detect_language(input: Path, pages: list[int] | None = None) -> dict:
    """
    Detect the language of the document.
    Returns {language, confidence, per_page: {page: lang}}.
    """
    from langdetect import detect, detect_langs
    from quill.features.basic import extract_text

    texts = extract_text(input, pages)
    full_text = " ".join(texts.values())

    per_page = {}
    for page_num, text in texts.items():
        try:
            per_page[page_num] = detect(text) if text.strip() else "unknown"
        except Exception:
            per_page[page_num] = "unknown"

    try:
        langs = detect_langs(full_text)
        return {
            "language": langs[0].lang if langs else "unknown",
            "confidence": round(langs[0].prob, 3) if langs else 0.0,
            "per_page": per_page,
        }
    except Exception:
        return {"language": "unknown", "confidence": 0.0, "per_page": per_page}
