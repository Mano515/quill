"""API routes — Phase 4: extraction."""

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from quill.api.deps import parse_pages, workdir

router = APIRouter(prefix="/extraction", tags=["Extraction"])


@router.post("/tables", summary="Extract tables to CSV or Excel")
async def extract_tables(
    file: UploadFile = File(...),
    pages: str | None = Form(None),
    fmt: str = Form("csv", description="csv | excel"),
):
    import zipfile
    from quill.features.extraction import extract_tables as _extract

    with workdir() as tmp:
        src = tmp / "input.pdf"
        src.write_bytes(await file.read())

        if fmt == "excel":
            out = tmp / "tables.xlsx"
            results = _extract(src, out, parse_pages(pages), "excel")
            return FileResponse(str(out), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename="tables.xlsx")
        else:
            results = _extract(src, tmp / "table.csv", parse_pages(pages), "csv")
            csv_files = list(tmp.glob("*.csv"))
            if len(csv_files) == 1:
                return FileResponse(str(csv_files[0]), media_type="text/csv", filename=csv_files[0].name)
            zip_path = tmp / "tables.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                for f in csv_files:
                    zf.write(f, f.name)
            return FileResponse(str(zip_path), media_type="application/zip", filename="tables.zip")


@router.post("/images", summary="Extract embedded images")
async def extract_images(file: UploadFile = File(...)):
    import zipfile
    from quill.features.extraction import extract_images as _extract

    with workdir() as tmp:
        src = tmp / "input.pdf"
        src.write_bytes(await file.read())
        out_dir = tmp / "images"
        saved = _extract(src, out_dir)

        if not saved:
            return JSONResponse({"message": "No images found"})

        zip_path = tmp / "images.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            for p in saved:
                zf.write(p, p.name)
        return FileResponse(str(zip_path), media_type="application/zip", filename="images.zip")


@router.post("/links", summary="Extract hyperlinks")
async def extract_links(
    file: UploadFile = File(...),
    pages: str | None = Form(None),
):
    from quill.features.extraction import extract_links as _extract

    with workdir() as tmp:
        src = tmp / "input.pdf"
        src.write_bytes(await file.read())
        return JSONResponse(_extract(src, parse_pages(pages)))


@router.post("/text", summary="Extract text with layout")
async def extract_layout(
    file: UploadFile = File(...),
    pages: str | None = Form(None),
):
    from quill.features.extraction import extract_layout

    with workdir() as tmp:
        src = tmp / "input.pdf"
        src.write_bytes(await file.read())
        return JSONResponse(extract_layout(src, parse_pages(pages)))


@router.post("/language", summary="Detect document language")
async def detect_language(file: UploadFile = File(...)):
    from quill.features.extraction import detect_language

    with workdir() as tmp:
        src = tmp / "input.pdf"
        src.write_bytes(await file.read())
        result = detect_language(src)
        return JSONResponse(result)
