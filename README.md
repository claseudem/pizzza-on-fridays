# Market Dashboard

Panel de precios en vivo, estilo TradingView, construido con **Flask**
(arquitectura **MVC**) y **UV** para la gestión del proyecto/dependencias.
Descarga los precios de **Yahoo Finance** (vía `yfinance`) y los dibuja con
[lightweight-charts](https://github.com/tradingview/lightweight-charts), la
propia librería open-source de gráficos de TradingView.

![sidebar](https://img.shields.io/badge/UI-sidebar%20izquierdo-2962ff)

## Arquitectura

```
config.py               # Configuración (variables de entorno)
run.py                   # Punto de entrada: `uv run run.py`
app/
  __init__.py            # Application factory: create_app()
  models/                # MODEL: acceso a datos, sin Flask
    apps.py                 # Registro de "apps" de primer nivel del sidebar
    watchlists.py            # Registro de watchlists de la app "Gráficas"
    market_data.py            # Descarga + caché de precios/velas (yfinance)
    analysis.py                # Volatilidad mensual + histogramas (seaborn)
    report.py                   # Informe HTML de cotizaciones para enviar por email
  controllers/            # CONTROLLER: blueprints de Flask
    home.py                   # "/" -> redirige a la app por defecto
    graficas.py                # App "Gráficas": sidebar de watchlists + gráfico
    varianza.py                 # App "Análisis de Varianza" (placeholder)
    api.py                       # API JSON que consume el JavaScript
  views/                   # VIEW: plantillas Jinja2
    base.html                 # Layout con el sidebar
    dashboard.html             # Cabecera + toolbar + contenedor del gráfico
    varianza.html               # Página en blanco de Análisis de Varianza
    partials/sidebar.html
  static/
    css/style.css
    js/app.js                 # Fetch a la API + render con lightweight-charts
    js/vendor/lightweight-charts.standalone.production.js
tests/                   # pytest (modelos + rutas, con datos simulados)
```

- **Model**: `app/models/market_data.py` es el único lugar que habla con
  `yfinance`; expone `Quote` (precio actual) y velas OHLC ya cacheadas.
  `app/models/apps.py` registra las secciones de primer nivel del sidebar
  y `app/models/watchlists.py` las watchlists dentro de la app "Gráficas".
- **View**: plantillas Jinja2 en `app/views` (sí, la carpeta se llama
  `views` y no `templates`, configurado explícitamente en la app factory).
- **Controller**: un blueprint por app (`home`, `graficas`, `varianza`) más
  `api`, que sirve JSON al frontend (para refrescar precios sin recargar
  la página).

## Cómo extenderla

El sidebar tiene dos niveles:

1. **Apps** (`app/models/apps.py`): las secciones de primer nivel, cada
   una con su propio blueprint. Para añadir una nueva (por ejemplo
   "Backtesting"):

   ```python
   App(slug="backtesting", name="Backtesting", icon="🧪", endpoint="backtesting.index", kind="blank"),
   ```

   y crear `app/controllers/backtesting.py` con un blueprint que renderice
   su propia plantilla, registrado en `app/__init__.py`. Con `kind="blank"`
   no hace falta tocar el sidebar: solo aparece el enlace.

2. **Watchlists** (`app/models/watchlists.py`), anidadas dentro de la app
   "Gráficas" (`kind="watchlists"`). Para añadir una nueva sección de
   tickers (por ejemplo "Bancos"):

   ```python
   Watchlist(
       slug="bancos",
       name="Bancos",
       icon="🏦",
       symbols=(
           Symbol("JPM", "JPMorgan"),
           Symbol("BAC", "Bank of America"),
       ),
   ),
   ```

   No hace falta tocar plantillas, controladores ni JavaScript: la nueva
   sección aparece automáticamente en el sidebar, con su propia ruta
   `/graficas/w/bancos` y su propio endpoint `/api/watchlist/bancos/quotes`.

### Análisis de Varianza

Además de la tabla de precios, esta app calcula la **volatilidad mensual
anualizada** (desviación estándar de los retornos diarios dentro de cada
mes calendario, multiplicada por `sqrt(252)`) de uno o varios tickers y
muestra, por cada uno, un histograma con la distribución de esas
volatilidades a lo largo del período elegido. El histograma se genera en
el servidor con **seaborn/matplotlib** (`app/models/analysis.py`) y se
sirve como PNG desde `GET /api/volatility-chart?tickers=AAPL,MSFT&period=5y`.

### Informe de mercado por email

`app/models/report.py` obtiene las cotizaciones de las watchlists, construye
un informe HTML (resumen de subidas/bajadas, mayores movimientos y una tabla
por watchlist) con la plantilla `app/views/emails/market_report.html` y lo
envía vía Resend:

```python
from app.models.report import build_market_report, send_market_report

report = build_market_report(["overview"])   # .subject y .html listos para enviar
send_market_report("destino@ejemplo.com")      # todas las watchlists
```

También por HTTP: `GET /api/report/preview?watchlists=overview` para verlo
en el navegador y `POST /api/email/send-assets-report` con
`{"to": "destino@ejemplo.com", "watchlists": ["overview"]}` para enviarlo
(`watchlists` es opcional).

## Puesta en marcha

Requiere [uv](https://docs.astral.sh/uv/) y Python 3.12+.

```bash
uv sync                 # instala dependencias (y crea el .venv)
cp .env.example .env    # opcional: ajustar TTLs de caché, etc.
uv run run.py           # http://localhost:5000
```

## Tests

```bash
uv run pytest
```

## Notas

- Los precios se cachean en memoria (`QUOTE_CACHE_TTL` / `CANDLE_CACHE_TTL`
  en `.env`) para no saturar Yahoo Finance; ajusta los valores según lo
  necesites.
- El servidor de desarrollo de Flask no es apto para producción; para
  desplegar, sirve `app` (la factory `create_app()`) con Gunicorn/uWSGI
  detrás de un proxy.
