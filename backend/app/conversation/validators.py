"""
Upload validation.

Kept separate from service.py so validation rules can be unit tested
without spinning up storage or a database session, and so the rules
themselves are easy to find in one place when the accepted formats or
size limit change.
"""

from dataclasses import dataclass

ALLOWED_EXTENSIONS: tuple[str, ...] = ("mp3", "wav", "m4a", "aac")


class ValidationError(Exception):
    """Raised when an uploaded file fails validation. Message is user-facing."""


@dataclass
class UploadCandidate:
    filename: str
    content_type: str | None
    size_bytes: int


def validate_upload(
    candidate: UploadCandidate,
    *,
    allowed_mime_types: tuple[str, ...],
    max_size_bytes: int,
) -> None:
    """Raises ValidationError with a clear, user-facing message on failure."""
    extension = _extension_of(candidate.filename)
    if extension not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"Unsupported file type '.{extension}'. "
            f"Accepted formats: {', '.join(ALLOWED_EXTENSIONS)}."
        )

    if candidate.content_type is not None and candidate.content_type not in allowed_mime_types:
        raise ValidationError(
            f"Unsupported content type '{candidate.content_type}' for file "
            f"'{candidate.filename}'."
        )

    if candidate.size_bytes <= 0:
        raise ValidationError("Uploaded file is empty.")

    if candidate.size_bytes > max_size_bytes:
        max_mb = max_size_bytes / (1024 * 1024)
        actual_mb = candidate.size_bytes / (1024 * 1024)
        raise ValidationError(
            f"File is {actual_mb:.1f} MB, which exceeds the {max_mb:.0f} MB limit."
        )


def _extension_of(filename: str) -> str:
    if "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1].lower()
