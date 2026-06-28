"""Phase 6 — PDF forms: fill, flatten, list fields, create interactive forms."""

from pathlib import Path


def fill_form(input: Path, output: Path, data: dict[str, str]) -> None:
    """Fill form fields by name. data: {field_name: value}."""
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(input)
    writer = PdfWriter()
    writer.append(reader)

    # Apply the values to every page (fields can span multiple pages)
    for page in writer.pages:
        writer.update_page_form_field_values(page, data)

    with open(output, "wb") as f:
        writer.write(f)


def flatten_form(input: Path, output: Path) -> None:
    """
    Flatten a PDF form — delete all widget annotations so fields become non-editable.
    The current field values stay visible because they are already drawn into the page
    content stream; deleting the widget just removes the interactive overlay.
    """
    import fitz

    # Open as an in-memory stream so PyMuPDF holds no file handle on Windows,
    # allowing the caller's temp directory to be deleted immediately after.
    doc = fitz.open(stream=input.read_bytes(), filetype="pdf")
    try:
        for page in doc:
            for widget in list(page.widgets()):
                page.delete_widget(widget)
        doc.save(str(output))
    finally:
        doc.close()


def list_fields(input: Path) -> list[dict]:
    """List all form fields with their type, value and options."""
    from pypdf import PdfReader

    raw = PdfReader(input).get_fields()
    if not raw:
        return []

    results = []
    for name, field in raw.items():
        entry: dict = {
            "name": name,
            "type": str(field.get("/FT", "")).lstrip("/"),
            "value": field.get("/V"),
            "options": None,
        }
        # Dropdown / listbox: /Opt is a list of strings or [export_val, display_val] pairs
        opt = field.get("/Opt")
        if opt:
            entry["options"] = [o if isinstance(o, str) else o[1] for o in opt]
        results.append(entry)
    return results


def create_form(output: Path, fields: list[dict]) -> None:
    """
    Create a PDF with interactive form fields from scratch.

    Each field dict:
      {
        "name": str,
        "type": "text" | "checkbox" | "dropdown",
        "label": str,           # visible label above the field
        "x": float, "y": float, # position in points from top-left
        "width": float,
        "height": float,
        "options": list[str],   # for dropdown only
        "page": int,            # 1-indexed, default 1
      }
    """
    import fitz

    doc = fitz.open()
    doc.new_page()

    try:
        for field in fields:
            page_num = field.get("page", 1) - 1
            while page_num >= len(doc):
                doc.new_page()

            page = doc[page_num]
            x, y = field["x"], field["y"]
            w, h = field.get("width", 200), field.get("height", 20)
            rect = fitz.Rect(x, y, x + w, y + h)

            # Draw the label just above the field
            label = field.get("label", field["name"])
            page.insert_text(fitz.Point(x, y - 4), label, fontsize=9, color=(0, 0, 0))

            widget = fitz.Widget()
            widget.rect = rect
            widget.field_name = field["name"]

            ftype = field.get("type", "text")
            if ftype == "checkbox":
                widget.field_type = fitz.PDF_WIDGET_TYPE_CHECKBOX
            elif ftype == "dropdown":
                widget.field_type = fitz.PDF_WIDGET_TYPE_LISTBOX
                widget.choice_values = field.get("options", [])
            else:
                widget.field_type = fitz.PDF_WIDGET_TYPE_TEXT

            widget.text_color = (0, 0, 0)
            widget.fill_color = (0.95, 0.95, 0.95)
            page.add_widget(widget)

        doc.save(str(output))
    finally:
        doc.close()
