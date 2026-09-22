"""Upload content-type contract tests."""

import pytest

from sketricgen.config import ALLOWED_CONTENT_TYPES, EXTENSION_TO_CONTENT_TYPE
from sketricgen.upload import detect_content_type, validate_content_type


@pytest.mark.parametrize(
    ("file_name", "content_type"),
    [
        ("photo.PNG", "image/png"),
        ("report.pdf", "application/pdf"),
        (
            "data.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
        ("config.yaml", "text/yaml"),
        ("component.ts", "application/typescript"),
        ("component.tsx", "application/typescript"),
        ("script.py", "text/x-python"),
        ("query.sql", "application/sql"),
    ],
)
def test_explicit_extension_mapping(file_name: str, content_type: str) -> None:
    assert detect_content_type(file_name) == content_type


def test_every_extension_maps_to_an_allowed_content_type() -> None:
    assert set(EXTENSION_TO_CONTENT_TYPE.values()) <= ALLOWED_CONTENT_TYPES


def test_every_backend_content_type_is_accepted() -> None:
    for content_type in ALLOWED_CONTENT_TYPES:
        assert validate_content_type(content_type) == content_type
