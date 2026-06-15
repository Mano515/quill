"""Phase 2 — Security: encryption, decryption, permissions."""

from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject


def encrypt(
    input: Path,
    output: Path,
    user_password: str,
    owner_password: str | None = None,
    allow_printing: bool = True,
    allow_copying: bool = True,
    allow_modifying: bool = True,
) -> None:
    """Encrypt a PDF with user and owner passwords."""
    reader = PdfReader(input)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)

    writer.encrypt(
        user_password=user_password,
        owner_password=owner_password or user_password,
        use_128bit=True,
        permissions_flag=_build_permissions(allow_printing, allow_copying, allow_modifying),
    )
    with open(output, "wb") as f:
        writer.write(f)


def decrypt(input: Path, output: Path, password: str) -> None:
    """Remove password protection from a PDF."""
    reader = PdfReader(input)
    if reader.is_encrypted:
        result = reader.decrypt(password)
        if result == 0:
            raise ValueError("Wrong password")

    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    with open(output, "wb") as f:
        writer.write(f)


def check_security(input: Path, password: str | None = None) -> dict:
    """Return security info about a PDF."""
    reader = PdfReader(input)
    info: dict = {"encrypted": reader.is_encrypted}

    if reader.is_encrypted and password:
        result = reader.decrypt(password)
        info["password_valid"] = result != 0
    elif reader.is_encrypted:
        info["password_valid"] = None

    return info


def _build_permissions(printing: bool, copying: bool, modifying: bool) -> int:
    """Build pypdf permissions flag."""
    from pypdf.constants import UserAccessPermissions as P

    flags = 0
    if printing:
        flags |= P.PRINT
    if copying:
        flags |= P.EXTRACT
    if modifying:
        flags |= P.MODIFY
    return flags
