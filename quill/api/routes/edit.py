"""API routes — text editing."""  # v2

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse

from quill.api.deps import pdf_response, workdir

router = APIRouter(prefix="/edit", tags=["Édition"])


@router.post("/replace-text", summary="Replace text inside a bounding box on a PDF page")
async def replace_text(
    file: UploadFile = File(...),
    page: int = Form(1),
    x0: float = Form(...),
    y0: float = Form(...),
    x1: float = Form(...),
    y1: float = Form(...),
    new_text: str = Form(...),
    tracking: float = Form(0.0),
    weight_extra: float = Form(0.0),
):
    from quill.features.edit import replace_text as _replace

    with workdir() as tmp:
        src = tmp / "input.pdf"
        src.write_bytes(await file.read())
        out = tmp / "edited.pdf"
        _replace(src, out, page=page, x0=x0, y0=y0, x1=x1, y1=y1, new_text=new_text,
                 tracking_extra=tracking, weight_extra=weight_extra)
        return pdf_response(out, "edited.pdf")


@router.post("/text-spans", summary="Extract text spans with positions via PyMuPDF (fallback for PDFs where PDF.js fails)")
async def text_spans(
    file: UploadFile = File(...),
    page: int = Form(1),
):
    """
    Retourne tous les spans de texte de la page avec leurs coordonnées PDF
    (top-down, en points). Utilisé comme fallback quand PDF.js ne peut pas
    extraire le texte (ex. polices Figma avec noms invalides).
    """
    import fitz

    data = await file.read()
    doc = fitz.open(stream=data, filetype="pdf")
    try:
        if page < 1 or page > len(doc):
            return JSONResponse({"spans": []})
        pg = doc[page - 1]
        spans = []
        for block in pg.get_text("dict")["blocks"]:
            if block.get("type") != 0:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    text = span.get("text", "").strip()
                    if not text:
                        continue
                    bb = span["bbox"]   # (x0, y0, x1, y1) top-down PDF points
                    spans.append({
                        "text": text,
                        "x0": bb[0], "y0": bb[1],
                        "x1": bb[2], "y1": bb[3],
                    })
        return JSONResponse({"spans": spans})
    finally:
        doc.close()
