import pytest

from app.conversation.validators import UploadCandidate, ValidationError, validate_upload

ALLOWED_MIME = ("audio/mpeg", "audio/wav")
MAX_SIZE = 10 * 1024 * 1024  # 10 MB


def test_accepts_valid_mp3() -> None:
    candidate = UploadCandidate("buyer_consultation.mp3", "audio/mpeg", 1024)
    validate_upload(candidate, allowed_mime_types=ALLOWED_MIME, max_size_bytes=MAX_SIZE)


def test_rejects_unsupported_extension() -> None:
    candidate = UploadCandidate("notes.txt", "text/plain", 1024)
    with pytest.raises(ValidationError, match="Unsupported file type"):
        validate_upload(candidate, allowed_mime_types=ALLOWED_MIME, max_size_bytes=MAX_SIZE)


def test_rejects_oversized_file() -> None:
    candidate = UploadCandidate("big.mp3", "audio/mpeg", MAX_SIZE + 1)
    with pytest.raises(ValidationError, match="exceeds"):
        validate_upload(candidate, allowed_mime_types=ALLOWED_MIME, max_size_bytes=MAX_SIZE)


def test_rejects_empty_file() -> None:
    candidate = UploadCandidate("empty.mp3", "audio/mpeg", 0)
    with pytest.raises(ValidationError, match="empty"):
        validate_upload(candidate, allowed_mime_types=ALLOWED_MIME, max_size_bytes=MAX_SIZE)


def test_rejects_mismatched_mime_type() -> None:
    candidate = UploadCandidate("track.mp3", "video/mp4", 1024)
    with pytest.raises(ValidationError, match="Unsupported content type"):
        validate_upload(candidate, allowed_mime_types=ALLOWED_MIME, max_size_bytes=MAX_SIZE)
