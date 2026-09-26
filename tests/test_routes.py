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


@pytest.fixture
def fake_uec(monkeypatch):
    from tests.test_quant import _fake_candles, _fake_earnings

    # El benchmark necesita datos distintos: quantstats cachea resampleos por contenido.
    monkeypatch.setattr(
        "app.models.quant.market_data.get_candles",
        lambda ticker, **k: _fake_candles(400 if ticker != "UEC" else 420),
    )
    monkeypatch.setattr("app.models.quant.market_data.get_earnings", lambda *a, **k: _fake_earnings())
    monkeypatch.setattr("app.models.quant.market_data.get_display_name", lambda ticker: f"Nombre {ticker}")


def test_quant_stats_index_redirects_to_fundamentales(client):
    response = client.get("/quant-stats/?ticker=AAPL&period=1y")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/quant-stats/fundamentales?ticker=AAPL&period=1y")


def test_quant_stats_sidebar_sections_keep_the_asset(client, fake_uec):
    html = client.get("/quant-stats/fundamentales?ticker=aapl").data.decode()
    assert "QUANT STATS" in html
    assert "Gráficas y fundamentales estadísticos" in html
    assert 'href="/quant-stats/revision?ticker=AAPL"' in html


def test_fundamentales_shows_the_three_quantstats_modules(client, fake_uec):
    from app.models.quant import ABSOLUTE_PLOTS

    response = client.get("/quant-stats/fundamentales?period=1y")
    assert response.status_code == 200
    html = response.data.decode()
    for module in ("quantstats.stats", "qs.stats.montecarlo", "quantstats.plots", "quantstats.reports"):
        assert module in html
    for label in ("Retorno acumulado", "Volatilidad anualizada", "Sharpe", "Sortino", "Máximo drawdown", "Calmar"):
        assert label in html
    for plot in ABSOLUTE_PLOTS:
        assert f"/api/quant/UEC/plot/{plot.slug}.png?period=1y" in html
    assert "/quant-stats/tearsheet" in html
    assert "Uranium Energy Corp" in html  # nombre de la watchlist


def test_fundamentales_has_nothing_comparative(client, fake_uec):
    """MECE: benchmark, períodos y earnings viven solo en Revisión analítica."""
    html = client.get("/quant-stats/fundamentales").data.decode()
    assert "rolling-beta" not in html
    assert "benchmark=" not in html
    assert 'name="benchmark"' not in html
    assert "/api/quant/UEC/earnings.png" not in html  # reportes de resultados


def test_summary_metrics_are_not_repeated_in_the_stat_tables(client, fake_uec):
    html = client.get("/quant-stats/fundamentales").data.decode()
    for label in ("Retorno acumulado", "Volatilidad anualizada", "Máximo drawdown"):
        assert html.count(f">{label}<") == 1


def test_fundamentales_runs_montecarlo_with_custom_thresholds(client, fake_uec):
    html = client.get("/quant-stats/fundamentales?sims=500&bust=-30&goal=100").data.decode()
    assert "DD ≤ -30%" in html
    assert "retorno ≥ +100%" in html
    assert "/api/quant/UEC/montecarlo.png?period=2y&amp;sims=500&amp;bust=-30&amp;goal=100" in html


def test_fundamentales_works_for_any_asset(client, fake_uec):
    html = client.get("/quant-stats/fundamentales?ticker=ccj").data.decode()
    assert "Gráficas y fundamentales estadísticos · CCJ" in html
    assert "Nombre CCJ" in html  # no está en las watchlists: nombre de Yahoo Finance
    assert "/api/quant/CCJ/plot/snapshot.png" in html


def test_invalid_ticker_falls_back_to_default(client, fake_uec):
    html = client.get("/quant-stats/fundamentales?ticker=<script>").data.decode()
    assert "· UEC" in html


def test_fundamentales_without_data(client, monkeypatch):
    monkeypatch.setattr("app.models.quant.market_data.get_candles", lambda *a, **k: [])
    monkeypatch.setattr("app.models.quant.market_data.get_display_name", lambda ticker: ticker)
    response = client.get("/quant-stats/fundamentales?ticker=NOEXISTE")
    assert response.status_code == 200
    assert "No se pudieron descargar precios de NOEXISTE".encode() in response.data


def test_revision_defaults_to_benchmark_mode(client, fake_uec):
    html = client.get("/quant-stats/revision?chart=bogus&period=bogus&mode=bogus").data.decode()
    assert "/api/quant/UEC/plot/returns.png?period=2y&amp;benchmark=SPY" in html
    assert "Métricas: UEC vs. SPY" in html
    assert "/quant-stats/tearsheet" in html


def test_revision_benchmark_mode_accepts_any_benchmark(client, fake_uec):
    html = client.get(
        "/quant-stats/revision?ticker=UEC&mode=benchmark&benchmark=ccj&chart=rolling-sharpe&window=63"
    ).data.decode()
    assert "/api/quant/UEC/plot/rolling-sharpe.png?period=2y&amp;benchmark=CCJ&amp;window=63" in html
    assert "Nombre CCJ" in html


def test_revision_benchmark_cannot_be_the_asset_itself(client, fake_uec):
    html = client.get("/quant-stats/revision?ticker=UEC&benchmark=UEC").data.decode()
    assert "Métricas: UEC vs. SPY" in html


def test_revision_periods_mode_compares_two_periods(client, fake_uec):
    html = client.get("/quant-stats/revision?mode=periodos&chart=drawdown&period=1y&compare=5y").data.decode()
    assert "/api/quant/UEC/plot/drawdown.png?period=1y\"" in html
    assert "/api/quant/UEC/plot/drawdown.png?period=5y\"" in html
    assert "rolling-beta" not in html  # sin benchmark no hay beta


def test_revision_periods_mode_never_compares_a_period_with_itself(client, fake_uec):
    html = client.get("/quant-stats/revision?mode=periodos&chart=drawdown&period=2y&compare=2y").data.decode()
    assert "/api/quant/UEC/plot/drawdown.png?period=1y\"" in html


def test_revision_earnings_mode(client, fake_uec):
    html = client.get("/quant-stats/revision?mode=earnings").data.decode()
    assert "/api/quant/UEC/earnings.png" in html
    earnings_section = html.split("Últimos 4 earnings", 1)[1]
    assert earnings_section.count("<tr>") == 1 + 4  # cabecera + 4 earnings


def test_tearsheet_is_served_and_downloadable(client, monkeypatch):
    calls = []
    monkeypatch.setattr(
        "app.controllers.quant_stats.quant.tearsheet_html",
        lambda *a: calls.append(a) or "<html>tearsheet</html>",
    )
    response = client.get("/quant-stats/tearsheet?ticker=aapl&period=1y&benchmark=spy")
    assert response.status_code == 200
    assert response.mimetype == "text/html"
    assert "Content-Disposition" not in response.headers
    assert calls == [("AAPL", "1y", "SPY")]
    download = client.get("/quant-stats/tearsheet?period=1y&download=1")
    assert download.headers["Content-Disposition"] == 'attachment; filename="UEC-tearsheet-1y.html"'


def test_tearsheet_rejects_invalid_benchmark(client):
    assert client.get("/quant-stats/tearsheet?benchmark=%3Cx%3E").status_code == 400


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


def test_api_quant_plot_validates_params(client):
    assert client.get("/api/quant/UEC/plot/bogus.png").status_code == 404
    assert client.get("/api/quant/UEC/plot/returns.png?period=bogus").status_code == 400
    assert client.get("/api/quant/UEC/plot/returns.png?benchmark=%3Cx%3E").status_code == 400
    assert client.get("/api/quant/%3Cx%3E/plot/returns.png").status_code == 400
    assert client.get("/api/quant/UEC/plot/rolling-sharpe.png?window=7").status_code == 400


def test_api_quant_plot_returns_png(client, monkeypatch):
    calls = []
    monkeypatch.setattr(
        "app.controllers.api.quant.render_qs_plot",
        lambda *a, **k: calls.append((a, k)) or b"fake-png-bytes",
    )
    response = client.get("/api/quant/uec/plot/rolling-sharpe.png?period=1y&benchmark=SPY&window=63")
    assert response.status_code == 200
    assert response.mimetype == "image/png"
    assert calls == [(("UEC", "1y", "rolling-sharpe"), {"benchmark": "SPY", "window": 63})]


def test_api_quant_montecarlo_validates_params(client):
    assert client.get("/api/quant/UEC/montecarlo.png?sims=7").status_code == 400
    assert client.get("/api/quant/UEC/montecarlo.png?bust=5").status_code == 400
    assert client.get("/api/quant/UEC/montecarlo.png?goal=-5").status_code == 400
    assert client.get("/api/quant/UEC/montecarlo.png?period=bogus").status_code == 400


def test_api_quant_montecarlo_returns_png(client, monkeypatch):
    calls = []
    monkeypatch.setattr(
        "app.controllers.api.quant.render_montecarlo_chart",
        lambda *a: calls.append(a) or b"fake-png-bytes",
    )
    response = client.get("/api/quant/aapl/montecarlo.png?period=1y&sims=500&bust=-30&goal=100")
    assert response.status_code == 200
    assert response.mimetype == "image/png"
    assert calls == [("AAPL", "1y", 500, -0.3, 1.0)]
