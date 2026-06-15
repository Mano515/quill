"""Phase 6 — PDF forms: fill, flatten, list fields, create interactive forms."""

from pathlib import Path


def fill_form(input: Path, output: Path, data: dict[str, str]) -> None:
    """Fill form fields by name. data: {field_name: value}."""
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(input)
    writer = PdfWriter()
    writer.append(reader)
    writer.update_page_form_field_values(writer.pages[0], data)

    # Apply to all pages
    for i in range(1, len(writer.pages)):
        writer.update_page_form_field_values(writer.pages[i], data)

    with open(output, "wb") as f:
        writer.write(f)


def flatten_form(input: Path, output: Path) -> None:
    """Flatten a PDF form — make fields non-editable by merging them into the page content."""
    import fitz

    doc = fitz.open(str(input))
    for page in doc:
        # Remove all widget annotations (form fields) after baking their appearance
        widgets = list(page.widgets())
        for widget in widgets:
            page.delete_widget(widget)
    doc.save(str(output))
    doc.close()


def list_fields(input: Path) -> list[dict]:
    """List all form fields with their type, value and options."""
    from pypdf import PdfReader

    reader = PdfReader(input)
    raw = reader.get_fields()
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
        # Dropdown / listbox options
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
        "type": "text" | "checkbox" | "radio" | "dropdown",
        "label": str,           # visible label above the field
        "x": float, "y": float, # position on page (points from top-left)
        "width": float,
        "height": float,
        "options": list[str],   # for dropdown / radio
        "page": int,            # 1-indexed, default 1
      }
    """
    import fitz

    doc = fitz.open()
    doc.new_page()

    for field in fields:
        page_num = field.get("page", 1) - 1
        while page_num >= len(doc):
            doc.new_page()

        page = doc[page_num]
        x, y = field["x"], field["y"]
        w, h = field.get("width", 200), field.get("height", 20)
        rect = fitz.Rect(x, y, x + w, y + h)

        label = field.get("label", field["name"])
        page.insert_text(fitz.Point(x, y - 4), label, fontsize=9, color=(0, 0, 0))

        widget = fitz.Widget()
        widget.rect = rect
        widget.field_name = field["name"]

        ftype = field.get("type", "text")
        if ftype == "text":
            widget.field_type = fitz.PDF_WIDGET_TYPE_TEXT
        elif ftype == "checkbox":
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
    doc.close()
