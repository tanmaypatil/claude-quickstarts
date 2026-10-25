"""Tests for turning uploaded files into message content blocks."""

import base64

import pytest

from browser_use_demo.attachments import (
    MAX_FILE_BYTES,
    AttachmentError,
    build_user_content,
    file_to_block,
)


def test_no_files_keeps_plain_prompt():
    assert build_user_content("hello", []) == "hello"


def test_csv_becomes_text_document():
    block = file_to_block("names.csv", b"name\nAsha Rao\n")
    assert block == {
        "type": "document",
        "source": {"type": "text", "media_type": "text/plain", "data": "name\nAsha Rao\n"},
        "title": "names.csv",
    }


def test_pdf_becomes_base64_document():
    block = file_to_block("Plan.PDF", b"%PDF-1.4")
    assert block["source"]["media_type"] == "application/pdf"
    assert base64.b64decode(block["source"]["data"]) == b"%PDF-1.4"


def test_image_becomes_image_block():
    block = file_to_block("shot.jpg", b"\xff\xd8")
    assert block["type"] == "image"
    assert block["source"]["media_type"] == "image/jpeg"


def test_files_come_before_prompt_text():
    content = build_user_content("Test these", [("a.txt", b"one"), ("b.png", b"x")])
    assert [b["type"] for b in content] == ["document", "image", "text"]
    assert content[-1]["text"] == "Test these\n\n(Attached: a.txt, b.png)"


def test_invalid_utf8_is_replaced_not_rejected():
    block = file_to_block("bad.txt", b"ok\xff")
    assert block["source"]["data"] == "ok�"


def test_unsupported_type_is_rejected():
    with pytest.raises(AttachmentError, match="unsupported type"):
        file_to_block("app.exe", b"MZ")


def test_oversized_file_is_rejected():
    with pytest.raises(AttachmentError, match="limit is 10 MB"):
        file_to_block("big.txt", b"x" * (MAX_FILE_BYTES + 1))
