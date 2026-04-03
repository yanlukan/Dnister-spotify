# tests/test_language.py
from src.language.text_check import check_text_language


def test_detects_ukrainian_text():
    result = check_text_language("Привіт світе як справи сьогодні")
    assert result["language"] == "ukr"
    assert result["confidence"] > 0.5


def test_detects_russian_text():
    result = check_text_language("Привет мир как дела сегодня")
    assert result["language"] == "rus"
    assert result["confidence"] > 0.5


def test_handles_short_text():
    result = check_text_language("Ой")
    assert "language" in result
    assert "confidence" in result


def test_handles_latin_text():
    result = check_text_language("Hello world")
    assert result["language"] != "ukr"
    assert result["language"] != "rus"


from unittest.mock import patch, MagicMock
from src.language.audio_check import check_audio_language


def test_audio_check_returns_result_for_url():
    mock_result = {"ukr": 0.92, "rus": 0.05}
    with patch("src.language.audio_check._classify_audio", return_value=mock_result):
        result = check_audio_language("https://example.com/preview.mp3")
        assert result["language"] == "ukr"
        assert result["confidence"] > 0.5


def test_audio_check_returns_unknown_for_none():
    result = check_audio_language(None)
    assert result["language"] == "unknown"
    assert result["confidence"] == 0.0
