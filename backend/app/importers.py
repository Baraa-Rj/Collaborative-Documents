"""Convert an uploaded file into (title, html). The result is sanitized by the caller like any other write."""
import html
import io
from pathlib import Path

import mammoth
import markdown

MAX_IMPORT_BYTES = 2 * 1024 * 1024  # 2 MB
SUPPORTED_EXTENSIONS = (".txt", ".md", ".docx")


class ImportFailed(ValueError):
    """Raised with a user-facing message when a file can't be imported."""


def _decode_text(data: bytes) -> str:
    # Content validation for text formats: must be UTF-8 and must not look binary.
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ImportFailed("File is not valid UTF-8 text.")
    if "\x00" in text:
        raise ImportFailed("File looks binary, not text.")
    return text


def _txt_to_html(text: str) -> str:
    # Blank lines separate paragraphs; single newlines become <br>.
    paragraphs = [p for p in text.replace("\r\n", "\n").split("\n\n") if p.strip()]
    return "".join(f"<p>{html.escape(p).replace(chr(10), '<br>')}</p>" for p in paragraphs)


def _docx_to_html(data: bytes) -> str:
    if not data.startswith(b"PK\x03\x04"):  # .docx is a zip archive
        raise ImportFailed("File is not a valid .docx document.")
    try:
        return mammoth.convert_to_html(io.BytesIO(data)).value
    except Exception:
        raise ImportFailed("Could not read the .docx document.")


def file_to_html(filename: str, data: bytes) -> tuple[str, str]:
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ImportFailed(f"Unsupported file type '{ext or 'none'}'. Supported: .txt, .md, .docx.")
    if len(data) > MAX_IMPORT_BYTES:
        raise ImportFailed("File is larger than the 2 MB limit.")
    if not data.strip():
        raise ImportFailed("File is empty.")

    if ext == ".txt":
        body = _txt_to_html(_decode_text(data))
    elif ext == ".md":
        body = markdown.markdown(_decode_text(data), extensions=["sane_lists"])
    else:
        body = _docx_to_html(data)

    title = Path(filename).stem.strip()[:200] or "Imported document"
    return title, body
