"""API routes — Phase 3: annotations."""

from fastapi import APIRouter, File, Form, UploadFile

from quill.api.deps import parse_pages, pdf_response, workdir

router = APIRouter(prefix="/annotations", tags=["Annotations"])


@router.post("/watermark", summary="Add text watermark")
async def watermark(
    file: UploadFile = File(...),
    text: str = Form(...),
    opacity: float = Form(0.15),
    font_size: int = Form(60),
    angle: float = Form(45.0),
):
    from quill.features.annotations import add_watermark_text

    with workdir() as tmp:
        src = tmp / "input.pdf"
        src.write_bytes(await file.read())
        out = tmp / "watermarked.pdf"
        add_watermark_text(src, out, text, opacity, font_size, angle=angle)
        return pdf_response(out, "watermarked.pdf")


@router.post("/stamp", summary="Add stamp (CONFIDENTIEL, APPROUVÉ…)")
async def stamp(
    file: UploadFile = File(...),
    label: str = Form("CONFIDENTIEL"),
    pages: str | None = Form(None),
    font_size: int = Form(48),
):
    from quill.features.annotations import add_stamp

    with workdir() as tmp:
        src = tmp / "input.pdf"
        src.write_bytes(await file.read())
        out = tmp / "stamped.pdf"
        add_stamp(src, out, label, parse_pages(pages), font_size=font_size)
        return pdf_response(out, "stamped.pdf")


@router.post("/add-text", summary="Overlay free text on pages")
async def add_text(
    file: UploadFile = File(...),
    text: str = Form(...),
    x: float = Form(...),
    y: float = Form(...),
    pages: str | None = Form(None),
    font_size: int = Form(12),
):
    from quill.features.annotations import add_text as _add

    with workdir() as tmp:
        src = tmp / "input.pdf"
        src.write_bytes(await file.read())
        out = tmp / "annotated.pdf"
        _add(src, out, text, x, y, parse_pages(pages), font_size)
        return pdf_response(out, "annotated.pdf")


@router.post("/page-numbers", summary="Add page numbers")
async def page_numbers(
    file: UploadFile = File(...),
    position: str = Form("bottom-center"),
    prefix: str = Form(""),
    suffix: str = Form(""),
    start: int = Form(1),
    font_size: int = Form(10),
):
    from quill.features.annotations import add_page_numbers

    with workdir() as tmp:
        src = tmp / "input.pdf"
        src.write_bytes(await file.read())
        out = tmp / "numbered.pdf"
        add_page_numbers(src, out, position, font_size, prefix, suffix, start)
        return pdf_response(out, "numbered.pdf")


@router.post("/comment", summary="Add sticky-note comment")
async def comment(
    file: UploadFile = File(...),
    text: str = Form(...),
    x: float = Form(50),
    y: float = Form(50),
    page: int = Form(1),
    author: str = Form("Quill"),
):
    from quill.features.annotations import add_comment

    with workdir() as tmp:
        src = tmp / "input.pdf"
        src.write_bytes(await file.read())
        out = tmp / "commented.pdf"
        add_comment(src, out, text, x, y, page, author)
        return pdf_response(out, "commented.pdf")


@router.post("/add-image", summary="Embed an image onto PDF pages")
async def add_image(
    file: UploadFile = File(...),
    image: UploadFile = File(...),
    x: float = Form(50),
    y: float = Form(50),
    width: float = Form(100),
    height: float = Form(100),
    pages: str | None = Form(None),
):
    from quill.features.annotations import add_image as _add_img

    with workdir() as tmp:
        src = tmp / "input.pdf"
        src.write_bytes(await file.read())
        img_path = tmp / image.filename
        img_path.write_bytes(await image.read())
        out = tmp / "with_image.pdf"
        _add_img(src, out, img_path, x, y, width, height, parse_pages(pages))
        return pdf_response(out, "with_image.pdf")
