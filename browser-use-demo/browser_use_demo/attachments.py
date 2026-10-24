"""
Turn a user-uploaded file into content blocks for a user message.

Text-like files and PDFs become `document` blocks, images become `image`
blocks. The file travels with the user's next message, so Claude reads it
directly without needing a tool call.
"""

import base64
from pathlib import Path

MAX_FILE_BYTES = 10 * 1024 * 1024

TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".tsv", ".json", ".xml", ".html", ".log", ".yaml", ".yml"}
IMAGE_MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}
SUPPORTED_EXTENSIONS = sorted(TEXT_EXTENSIONS | set(IMAGE_MEDIA_TYPES) | {".pdf"})


class AttachmentError(ValueError):
    """Raised when an uploaded file can't be sent to Claude."""


def file_to_block(name: str, data: bytes) -> dict:
    """Build one content block for an uploaded file."""
    if len(data) > MAX_FILE_BYTES:
        raise AttachmentError(
            f"{name} is {len(data) / 1024 / 1024:.1f} MB. The limit is "
            f"{MAX_FILE_BYTES // 1024 // 1024} MB."
        )

    ext = Path(name).suffix.lower()
    if ext in TEXT_EXTENSIONS:
        return {
            "type": "document",
            "source": {
                "type": "text",
                "media_type": "text/plain",
                "data": data.decode("utf-8", errors="replace"),
            },
            "title": name,
        }
    if ext == ".pdf":
        return {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": base64.b64encode(data).decode(),
            },
            "title": name,
        }
    if ext in IMAGE_MEDIA_TYPES:
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": IMAGE_MEDIA_TYPES[ext],
                "data": base64.b64encode(data).decode(),
            },
        }
    raise AttachmentError(
        f"{name} has an unsupported type. Use one of: {', '.join(SUPPORTED_EXTENSIONS)}"
    )


def build_user_content(prompt: str, files: list[tuple[str, bytes]]) -> str | list[dict]:
    """Return message content: the plain prompt, or file blocks followed by the prompt.

    Files go before the text, which is the order Claude handles best for
    long documents.
    """
    if not files:
        return prompt

    blocks = [file_to_block(name, data) for name, data in files]
    names = ", ".join(name for name, _ in files)
    blocks.append({"type": "text", "text": f"{prompt}\n\n(Attached: {names})"})
    return blocks
