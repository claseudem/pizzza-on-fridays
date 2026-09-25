from app.models.market_data import Quote
from app.models.watchlists import WATCHLISTS


def _fake_quote(ticker):
    return Quote(
        symbol=ticker,
        name=ticker,
        price=100.0,
        previous_close=95.0,
        change=5.0,
        change_percent=5.263,
        currency="USD",
    )


def test_index_renders_landing_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Market Dashboard" in response.data
    assert b'href="/graficas/"' in response.data
    assert b'href="/analisis-varianza/"' in response.data


def test_unknown_watchlist_is_404(client):
    assert client.get("/graficas/w/no-existe").status_code == 404


def test_show_watchlist_renders_first_symbol(client):
    watchlist = WATCHLISTS[0]
    response = client.get(f"/graficas/w/{watchlist.slug}")
    assert response.status_code == 200
    assert watchlist.symbols[0].ticker.encode() in response.data


def test_varianza_page_is_reachable(client):
    response = client.get("/analisis-varianza/")
    assert response.status_code == 200
    assert "Análisis de Varianza".encode() in response.data
    assert b'id="ticker-input"' in response.data
    assert b'id="download-csv-btn"' in response.data


def test_api_quote(client, monkeypatch):
    monkeypatch.setattr("app.controllers.api.market_data.get_quote", _fake_quote)
    response = client.get("/api/quote/AAPL")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["symbol"] == "AAPL"
    assert payload["is_up"] is True


def test_api_candles_rejects_bad_params(client):
    response = client.get("/api/candles/AAPL?range=bogus&interval=1d")
    assert response.status_code == 400


def test_api_volatility_chart_requires_tickers(client):
    response = client.get("/api/volatility-chart")
    assert response.status_code == 400


def test_api_volatility_chart_rejects_too_many_tickers(client):
    tickers = ",".join(f"T{i}" for i in range(10))
    response = client.get(f"/api/volatility-chart?tickers={tickers}")
    assert response.status_code == 400


def test_api_volatility_chart_returns_png(client, monkeypatch):
    monkeypatch.setattr(
        "app.controllers.api.analysis.render_volatility_histograms",
        lambda tickers, period: b"fake-png-bytes",
    )
    response = client.get("/api/volatility-chart?tickers=AAPL,MSFT")
    assert response.status_code == 200
    assert response.mimetype == "image/png"
    assert response.data == b"fake-png-bytes"


def test_api_email_send_requires_to(client):
    response = client.post("/api/email/send", json={})
    assert response.status_code == 400


def test_api_email_send_returns_id(client, monkeypatch):
    monkeypatch.setattr(
        "app.controllers.api.send_email",
        lambda to, subject, html: "email-123",
    )
    response = client.post("/api/email/send", json={"to": "test@example.com"})
    assert response.status_code == 200
    assert response.get_json() == {"id": "email-123"}


def test_api_email_send_reports_provider_errors(client, monkeypatch):
    from app.models.email import EmailError

    def _raise(to, subject, html):
        raise EmailError("Falta RESEND_API_KEY en el .env")

    monkeypatch.setattr("app.controllers.api.send_email", _raise)
    response = client.post("/api/email/send", json={"to": "test@example.com"})
    assert response.status_code == 502
    assert "error" in response.get_json()
