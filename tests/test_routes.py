import pytest

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


def test_index_shows_landing_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Ver gr\xc3\xa1ficas en vivo" in response.data


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


def test_api_report_preview_returns_html(client, monkeypatch):
    monkeypatch.setattr("app.models.report.market_data.get_quote", _fake_quote)
    response = client.get("/api/report/preview?watchlists=overview")
    assert response.status_code == 200
    assert response.mimetype == "text/html"
    assert b"Informe de mercado" in response.data


def test_api_report_preview_unknown_watchlist_is_404(client):
    assert client.get("/api/report/preview?watchlists=no-existe").status_code == 404


def test_api_report_send_requires_to(client):
    assert client.post("/api/report/send", json={}).status_code == 400


def test_api_report_send_returns_id(client, monkeypatch):
    calls = []

    def _send(to, slugs):
        calls.append((to, slugs))
        return "email-456"

    monkeypatch.setattr("app.controllers.api.report.send_market_report", _send)
    response = client.post("/api/report/send", json={"to": "test@example.com", "watchlists": ["overview"]})
    assert response.status_code == 200
    assert response.get_json() == {"id": "email-456"}
    assert calls == [("test@example.com", ["overview"])]


def test_api_send_assets_report_requires_to(client):
    assert client.post("/api/email/send-assets-report", json={}).status_code == 400


def test_api_send_assets_report_unknown_watchlist_is_404(client):
    response = client.post(
        "/api/email/send-assets-report", json={"to": "test@example.com", "watchlists": ["no-existe"]}
    )
    assert response.status_code == 404


def test_api_send_assets_report_sends_report_html(client, monkeypatch):
    sent = {}

    def _send(to, subject, html):
        sent.update(to=to, subject=subject, html=html)
        return "email-789"

    monkeypatch.setattr("app.models.report.market_data.get_quote", _fake_quote)
    monkeypatch.setattr("app.controllers.api.send_email", _send)
    response = client.post(
        "/api/email/send-assets-report", json={"to": "test@example.com", "watchlists": ["overview"]}
    )
    assert response.status_code == 200
    assert response.get_json()["id"] == "email-789"
    assert sent["to"] == "test@example.com"
    assert sent["subject"].startswith("Informe de mercado")
    assert "Resumen" in sent["html"]


def test_api_send_assets_report_reports_provider_errors(client, monkeypatch):
    from app.models.email import EmailError

    def _raise(to, subject, html):
        raise EmailError("Falta RESEND_API_KEY en el .env")

    monkeypatch.setattr("app.models.report.market_data.get_quote", _fake_quote)
    monkeypatch.setattr("app.controllers.api.send_email", _raise)
    response = client.post("/api/email/send-assets-report", json={"to": "test@example.com"})
    assert response.status_code == 502
    assert "error" in response.get_json()

def test_uec_page_shows_metrics_and_earnings(client, monkeypatch):
    from tests.test_quant import _fake_candles, _fake_earnings

    monkeypatch.setattr("app.models.quant.market_data.get_candles", lambda *a, **k: _fake_candles())
    monkeypatch.setattr("app.models.quant.market_data.get_earnings", lambda *a, **k: _fake_earnings())
    response = client.get("/analisis-uec/?period=1y")
    assert response.status_code == 200
    html = response.data.decode()
    for label in ("Retorno acumulado", "Volatilidad anualizada", "Sharpe", "Sortino", "Máximo drawdown"):
        assert label in html
    assert "/api/quant/UEC/drawdown.png?period=1y" in html
    assert "/api/quant/UEC/monthly-heatmap.png?period=1y" in html
    assert "/api/quant/UEC/earnings.png" in html
    assert html.count("<tr>") == 1 + 4  # cabecera + 4 earnings


def test_uec_page_without_data(client, monkeypatch):
    monkeypatch.setattr("app.models.quant.market_data.get_candles", lambda *a, **k: [])
    monkeypatch.setattr("app.models.quant.market_data.get_earnings", lambda *a, **k: [])
    response = client.get("/analisis-uec/")
    assert response.status_code == 200
    assert "No se pudieron descargar precios".encode() in response.data


@pytest.mark.parametrize("chart", ["drawdown", "monthly-heatmap"])
def test_api_quant_charts_reject_bad_period(client, chart):
    assert client.get(f"/api/quant/UEC/{chart}.png?period=bogus").status_code == 400


def test_api_quant_earnings_rejects_bad_count(client):
    assert client.get("/api/quant/UEC/earnings.png?count=50").status_code == 400


def test_api_quant_drawdown_returns_png(client, monkeypatch):
    monkeypatch.setattr(
        "app.controllers.api.quant.render_drawdown_chart", lambda ticker, period: b"fake-png-bytes"
    )
    response = client.get("/api/quant/uec/drawdown.png")
    assert response.status_code == 200
    assert response.mimetype == "image/png"


def test_informes_page_has_preview_and_send_buttons(client):
    response = client.get("/informes/")
    assert response.status_code == 200
    assert b'id="preview-btn"' in response.data
    assert b'id="send-btn"' in response.data
    for watchlist in WATCHLISTS:
        assert f'value="{watchlist.slug}"'.encode() in response.data


def test_informes_page_has_background_fx_layers(client):
    response = client.get("/informes/")
    for scene in ("charts", "stats", "sports"):
        # Video en bucle si existe static/video/informes-<escena>.mp4; si no, canvas.
        assert f"fx-layer--{scene}".encode() in response.data
        assert (
            f"video/informes-{scene}.mp4".encode() in response.data
            or f'data-fx-scene="{scene}"'.encode() in response.data
        )
    assert b'aria-hidden="true"' in response.data
