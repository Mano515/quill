"""Phase 5 — OCR: scanned PDFs, searchable PDF creation, deskew, denoising."""

from pathlib import Path


def pdf_to_images(
    input: Path,
    output_dir: Path,
    dpi: int = 300,
    fmt: str = "png",
    pages: list[int] | None = None,
) -> list[Path]:
    """Convert PDF pages to images."""
    from pdf2image import convert_from_path

    output_dir.mkdir(parents=True, exist_ok=True)
    first_page = pages[0] if pages else 1
    last_page = pages[-1] if pages else None

    images = convert_from_path(
        str(input),
        dpi=dpi,
        fmt=fmt,
        first_page=first_page,
        last_page=last_page,
    )

    saved: list[Path] = []
    page_nums = pages or list(range(first_page, first_page + len(images)))
    for page_num, img in zip(page_nums, images):
        out = output_dir / f"page_{page_num:04d}.{fmt}"
        img.save(out)
        saved.append(out)
    return saved


def ocr_pdf(
    input: Path,
    output: Path,
    lang: str = "fra+eng",
    dpi: int = 300,
    deskew: bool = False,
    denoise: bool = False,
    pages: list[int] | None = None,
) -> str:
    """
    Run OCR on a (scanned) PDF and produce a searchable PDF.
    Returns the full extracted text.
    lang: tesseract language code(s), e.g. 'fra', 'eng', 'fra+eng'
    """
    import tempfile
    from pathlib import Path as _Path

    import pytesseract
    from pdf2image import convert_from_path
    from PIL import Image
    from pypdf import PdfWriter

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = _Path(tmp)

        first_page = pages[0] if pages else 1
        last_page = pages[-1] if pages else None

        images = convert_from_path(
            str(input),
            dpi=dpi,
            first_page=first_page,
            last_page=last_page,
        )

        all_text: list[str] = []
        page_pdfs: list[_Path] = []

        for i, img in enumerate(images):
            processed = _preprocess(img, deskew=deskew, denoise=denoise)
            text = pytesseract.image_to_string(processed, lang=lang)
            all_text.append(text)

            # Create a single-page searchable PDF from this image
            page_pdf_path = tmp_dir / f"page_{i:04d}.pdf"
            searchable = pytesseract.image_to_pdf_or_hocr(processed, extension="pdf", lang=lang)
            page_pdf_path.write_bytes(searchable)
            page_pdfs.append(page_pdf_path)

        # Merge all page PDFs into one
        writer = PdfWriter()
        from pypdf import PdfReader
        for p in page_pdfs:
            reader = PdfReader(str(p))
            for page in reader.pages:
                writer.add_page(page)

        with open(output, "wb") as f:
            writer.write(f)

    return "\n\n".join(all_text)


def images_to_searchable_pdf(
    images: list[Path],
    output: Path,
    lang: str = "fra+eng",
    deskew: bool = False,
    denoise: bool = False,
) -> str:
    """Convert a list of images to a single searchable PDF via OCR."""
    import tempfile
    from pathlib import Path as _Path

    import pytesseract
    from PIL import Image
    from pypdf import PdfReader, PdfWriter

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = _Path(tmp)
        all_text: list[str] = []
        page_pdfs: list[_Path] = []

        for i, img_path in enumerate(images):
            img = Image.open(img_path)
            processed = _preprocess(img, deskew=deskew, denoise=denoise)
            text = pytesseract.image_to_string(processed, lang=lang)
            all_text.append(text)

            page_pdf_path = tmp_dir / f"page_{i:04d}.pdf"
            searchable = pytesseract.image_to_pdf_or_hocr(processed, extension="pdf", lang=lang)
            page_pdf_path.write_bytes(searchable)
            page_pdfs.append(page_pdf_path)

        writer = PdfWriter()
        for p in page_pdfs:
            reader = PdfReader(str(p))
            for page in reader.pages:
                writer.add_page(page)

        with open(output, "wb") as f:
            writer.write(f)

    return "\n\n".join(all_text)


def _preprocess(img, deskew: bool = False, denoise: bool = False):
    """Apply deskew and/or denoising to a PIL image."""
    if not deskew and not denoise:
        return img

    import numpy as np
    import cv2

    arr = np.array(img)

    if denoise:
        arr = cv2.fastNlMeansDenoisingColored(arr, None, 10, 10, 7, 21)

    if deskew:
        gray = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY)
        gray = cv2.bitwise_not(gray)
        coords = np.column_stack(np.where(gray > 0))
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        h, w = arr.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        arr = cv2.warpAffine(arr, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    from PIL import Image
    return Image.fromarray(arr)
