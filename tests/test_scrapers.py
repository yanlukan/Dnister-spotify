# tests/test_scrapers.py
from unittest.mock import patch, MagicMock
from src.scrapers.hitfm import scrape_hitfm


def test_hitfm_parses_songs():
    html = """
    <html><script>
    var songsFound = [
        {"singer": "KAZKA", "song": "ПЛАКАЛА", "time": "12:00"},
        {"singer": "Океан Ельзи", "song": "Обійми", "time": "12:05"}
    ];
    </script></html>
    """
    with patch("src.scrapers.hitfm.requests.get") as mock_get:
        mock_get.return_value = MagicMock(text=html, status_code=200)
        songs = scrape_hitfm()
        assert len(songs) == 2
        assert songs[0] == {"name": "ПЛАКАЛА", "artist": "KAZKA", "source": "hitfm"}
        assert songs[1] == {"name": "Обійми", "artist": "Океан Ельзи", "source": "hitfm"}


def test_hitfm_returns_empty_on_failure():
    with patch("src.scrapers.hitfm.requests.get") as mock_get:
        mock_get.side_effect = Exception("Connection failed")
        songs = scrape_hitfm()
        assert songs == []
