"""Phase 4 — Advanced extraction: tables, images, links, form fields, layout, language detection."""

from pathlib import Path


def extract_tables(
    input: Path,
    output: Path | None = None,
    pages: list[int] | None = None,
    fmt: str = "csv",
) -> list[dict]:
    """
    Extract tables from a PDF.

    Returns a list of dicts: {page, table_index, data}.
    If output is provided, also exports to CSV (one file per table) or a single Excel workbook.
    fmt: 'csv' | 'excel'
    """
    import pdfplumber

    results = []
    with pdfplumber.open(input) as pdf:
        target = set(pages) if pages else set(range(1, len(pdf.pages) + 1))
        for page_num in target:
            for i, table in enumerate(pdf.pages[page_num - 1].extract_tables()):
                results.append({"page": page_num, "table_index": i, "data": table})

    if output and results:
        import pandas as pd

        if fmt == "excel":
            with pd.ExcelWriter(output) as writer:
                for r in results:
                    sheet = f"p{r['page']}_t{r['table_index']}"
                    pd.DataFrame(r["data"]).to_excel(writer, sheet_name=sheet, index=False, header=False)
        else:
            # One CSV file per table, e.g. table_p1_t0.csv, table_p1_t1.csv, …
            stem = output.stem
            for r in results:
                path = output.parent / f"{stem}_p{r['page']}_t{r['table_index']}.csv"
                pd.DataFrame(r["data"]).to_csv(path, index=False, header=False)

    return results


def extract_images(input: Path, output_dir: Path) -> list[Path]:
    """Extract all embedded images from a PDF and save them to output_dir."""
    import fitz

    output_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(input))
    try:
        saved: list[Path] = []
        for page_num, page in enumerate(doc, start=1):
            for img_index, img in enumerate(page.get_images(full=True)):
                xref = img[0]  # cross-reference number, used to retrieve the image data
                base_image = doc.extract_image(xref)
                out = output_dir / f"page{page_num}_img{img_index}.{base_image['ext']}"
                out.write_bytes(base_image["image"])
                saved.append(out)
        return saved
    finally:
        doc.close()


def extract_links(input: Path, pages: list[int] | None = None) -> list[dict]:
    """
    Extract all hyperlinks from a PDF.
    Returns a list of {page, uri, rect} dicts.
    """
    import fitz

    doc = fitz.open(str(input))
    try:
        target = set(pages) if pages else set(range(1, len(doc) + 1))
        results = []
        for page_num in target:
            for link in doc[page_num - 1].get_links():
                if link.get("uri"):
                    results.append({
                        "page": page_num,
                        "uri": link["uri"],
                        "rect": list(link["from"]),
                    })
        return results
    finally:
        doc.close()


def extract_form_fields(input: Path) -> list[dict]:
    """Extract all form field names and their current values."""
    from pypdf import PdfReader

    fields = PdfReader(input).get_fields()
    if not fields:
        return []
    return [
        {"name": name, "value": field.get("/V"), "type": str(field.get("/FT", ""))}
        for name, field in fields.items()
    ]


def extract_layout(input: Path, pages: list[int] | None = None) -> list[dict]:
    """
    Extract text with its position and font information.
    Returns a list of {page, text, x0, y0, x1, y1, size, font} dicts.
    """
    import pdfplumber

    results = []
    with pdfplumber.open(input) as pdf:
        target = set(pages) if pages else set(range(1, len(pdf.pages) + 1))
        for page_num in target:
            for word in pdf.pages[page_num - 1].extract_words(extra_attrs=["size", "fontname"]):
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
    Returns {language, confidence, per_page: {page_num: lang_code}}.
    """
    from langdetect import detect, detect_langs
    from quill.features.basic import extract_text

    texts = extract_text(input, pages)
    full_text = " ".join(texts.values())

    # Detect per page first (best-effort — short text may fail)
    per_page = {}
    for page_num, text in texts.items():
        try:
            per_page[page_num] = detect(text) if text.strip() else "unknown"
        except Exception:
            per_page[page_num] = "unknown"

    # Detect on the full concatenated text for higher confidence
    try:
        langs = detect_langs(full_text)
        return {
            "language": langs[0].lang if langs else "unknown",
            "confidence": round(langs[0].prob, 3) if langs else 0.0,
            "per_page": per_page,
        }
    except Exception:
        return {"language": "unknown", "confidence": 0.0, "per_page": per_page}
