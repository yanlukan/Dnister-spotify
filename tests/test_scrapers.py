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


from src.scrapers.lastfm import scrape_lastfm


def test_lastfm_parses_tracks():
    api_response = {
        "tracks": {
            "track": [
                {"name": "ПЛАКАЛА", "artist": {"name": "KAZKA"}},
                {"name": "Stefania", "artist": {"name": "Kalush Orchestra"}},
            ]
        }
    }
    with patch("src.scrapers.lastfm.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = api_response
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp
        songs = scrape_lastfm(api_key="fake_key", tags=["ukrainian"])
        assert len(songs) == 2
        assert songs[0]["name"] == "ПЛАКАЛА"
        assert songs[0]["source"] == "lastfm"


def test_lastfm_returns_empty_without_key():
    songs = scrape_lastfm(api_key="", tags=["ukrainian"])
    assert songs == []


from src.scrapers.kworb import scrape_kworb


def test_kworb_parses_chart():
    html = """
    <html><body><table>
    <tr><td>1</td><td></td><td><a>KAZKA</a> - ПЛАКАЛА</td></tr>
    <tr><td>2</td><td></td><td><a>Океан Ельзи</a> - Обійми</td></tr>
    </table></body></html>
    """
    with patch("src.scrapers.kworb.requests.get") as mock_get:
        mock_get.return_value = MagicMock(text=html, status_code=200)
        songs = scrape_kworb()
        assert len(songs) == 2
        assert songs[0]["artist"] == "KAZKA"
        assert songs[0]["name"] == "ПЛАКАЛА"
        assert songs[0]["source"] == "kworb"


def test_kworb_returns_empty_on_failure():
    with patch("src.scrapers.kworb.requests.get") as mock_get:
        mock_get.side_effect = Exception("Timeout")
        songs = scrape_kworb()
        assert songs == []
