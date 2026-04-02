"""
Utility helpers to extract plain text from various file types.
Supported: .txt, .pdf, .docx, .md
"""
from pathlib import Path


def extract_text(file_path: str) -> str:
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix in {".txt", ".md"}:
        return _read_text(path)
    elif suffix == ".pdf":
        return _read_pdf(path)
    elif suffix == ".docx":
        return _read_docx(path)
    else:
        # Attempt raw text fallback
        return _read_text(path)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _read_pdf(path: Path) -> str:
    try:
        import PyPDF2
        text_parts: list[str] = []
        with open(path, "rb") as fh:
            reader = PyPDF2.PdfReader(fh)
            for page in reader.pages:
                text_parts.append(page.extract_text() or "")
        return "\n".join(text_parts)
    except Exception as exc:
        raise ValueError(f"PDF extraction failed: {exc}") from exc


def _read_docx(path: Path) -> str:
    try:
        from docx import Document
        doc = Document(str(path))
        return "\n".join(para.text for para in doc.paragraphs)
    except Exception as exc:
        raise ValueError(f"DOCX extraction failed: {exc}") from exc
