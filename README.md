# Hadouken Zone

**Bot de Telegram que publica automáticamente ofertas de videojuegos de PS5 y Nintendo Switch en Amazon.es**, con un descuento mínimo del 20 %, precio comprobado, tarjeta visual de cada oferta y enlace de afiliado.

## Qué hace cada día

**Producción: GitHub Actions, gratis y sin ningún equipo encendido**

| Hora (Madrid) | Acción |
|---|---|
| 09:07 | Mensaje de **buenos días** con imagen de cabecera. |
| Cada 30 min (09:07 – 23:07) | Busca ofertas nuevas en las **fuentes** y publica todas las válidas, con **1 minuto** entre ofertas. |

**Fuentes de ofertas** (`hadouken_zone/sources/`, se eligen con `OFFER_SOURCES`):

| Fuente | Cómo funciona | Dónde funciona |
|---|---|---|
| `chollometro` *(activa)* | Ofertas **de Amazon** publicadas en Chollometro: precio, precio anterior y **ASIN** (por la redirección de la oferta). | GitHub Actions y en casa |
| `amazon` | Busca directamente en Amazon.es y verifica cada oferta en su ficha. | Solo desde una conexión doméstica (Amazon bloquea GitHub) |

Cada oferta se publica como **foto (tarjeta 1280x720)** con título, plataforma, precio actual, precio anterior tachado, % de descuento, ahorro y el **enlace limpio a Amazon** (`https://www.amazon.es/dp/ASIN`).

**Alternativa en casa:** `py main.py` deja el bot 24/7 en un PC (buenos días a las 09:00 y escaneo cada 30 min hasta las 23:30).

## Estructura

```
hadouken-zone/
├── main.py                  Punto de entrada (bot 24/7, pasada única para cron y comandos sueltos)
├── .github/workflows/       Automatización en GitHub Actions (publicación diaria y tests)
├── hadouken_zone/           Código del producto
│   ├── config.py            Rutas y ajustes (.env)
│   ├── models.py            Modelo Offer
│   ├── sources/             Fuentes de ofertas enchufables
│   │   ├── base.py          Contrato común (find_offers) y error de bloqueo
│   │   ├── chollometro.py   Fuente Chollometro (RSS + datos de la oferta + ASIN)
│   │   └── amazon/          Fuente Amazon: cliente HTTP, parser HTML y scraper
│   ├── rules.py             Reglas de negocio (plataforma, exclusiones, descuento coherente)
│   ├── affiliate.py         Enlaces de producto con ID de afiliado
│   ├── storage.py           Historial de publicadas y estado (JSON, escritura atómica)
│   ├── messages.py          Textos del canal (buenos días, ofertas)
│   ├── cards.py             Tarjeta visual de cada oferta
│   ├── telegram.py          Cliente de la API de Telegram
│   ├── pipeline.py          Ciclo: buscar → verificar → publicar
│   ├── scheduler.py         Calendario diario (buenos días + cada 30 min)
│   └── logging_setup.py     Registro en consola y logs/
├── tests/                   Tests (pytest) con HTML de ejemplo en tests/fixtures/
├── branding/                Identidad visual (ver branding/README.md)
├── tools/branding/          Scripts que generan los diseños
├── scripts/                 Arranque del bot y arranque automático en Windows
├── docs/                    Contexto del proyecto y registro de cambios
├── data/                    (se crea solo) historial, estado y tarjetas generadas
└── logs/                    (se crea solo) registro del bot y HTML de diagnóstico
```

## Instalación (Windows)

```powershell
cd C:\Users\Asus\Desktop\Proyectos\hadouken-zone
py -m pip install -r requirements.txt
Copy-Item .env.example .env        # solo la primera vez; después edita .env
```

Rellena en `.env` al menos `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` y `AMAZON_PARTNER_TAG`.

## Uso

```powershell
py main.py                 # bot 24/7 (deja la ventana abierta)
py main.py --ciclo         # una pasada del calendario y termina (lo que hace GitHub Actions)
py main.py --once          # un escaneo y publicación ahora
py main.py --buenos-dias   # envía ahora el buenos días
py main.py --test          # mensaje de presentación del canal
```

Con `DRY_RUN=true` todo se muestra en la consola y no se publica nada. Para publicar de verdad, pon `DRY_RUN=false`.

**Arranque automático:** `powershell -ExecutionPolicy Bypass -File .\scripts\programar_inicio_windows.ps1` crea una tarea de Windows que inicia el bot al encender el ordenador e iniciar sesión. El bot solo funciona mientras el ordenador está encendido y conectado.

## Automatización en GitHub Actions (producción)

Repositorio privado `Binteak/hadouken-zone-bot`. El workflow `.github/workflows/publicar_ofertas.yml` ejecuta `python main.py --ciclo` cada 30 minutos entre las 09:07 y las 23:07 (Europe/Madrid), con la fuente `chollometro`.

**Configuración (una sola vez):** en GitHub → *Settings → Secrets and variables → Actions → New repository secret*:

| Secret | Valor |
|---|---|
| `TELEGRAM_BOT_TOKEN` | El token del bot (el mismo que en tu `.env`) |
| `TELEGRAM_CHAT_ID` | `@hadoukenzone` (o el ID del canal) |

**Probar sin publicar:** pestaña *Actions → Publicar ofertas → Run workflow* con `dry_run = true`. El registro de la ejecución muestra lo que se habría publicado. Además, en *Artifacts* se guardan los registros y, si Amazon cambia su web, el HTML de diagnóstico.

**Estado entre ejecuciones:** el historial de publicadas (`offers.json`) y el estado (`state.json`) se guardan en la rama `estado`, que actualiza el propio bot. No la borres.

**Coste:** repo privado en GitHub Free (~2.000 minutos al mes). Unas 30 ejecuciones al día de ~1 minuto, más 1 minuto por oferta publicada, suman unos 1.000 minutos al mes. Los tests (`tests.yml`) se ejecutan en cada push de código.

**Importante:** no ejecutes a la vez el bot 24/7 en tu PC y el de GitHub, o se publicarán ofertas duplicadas.

## Tests

```powershell
py -m pip install -r requirements-dev.txt
py -m pytest
```

Los tests no acceden a internet: el HTML de Amazon y la API de Telegram están simulados.

## Configuración (.env)

| Variable | Por defecto | Descripción |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | — | Bot y canal de destino |
| `DRY_RUN` | `true` | `false` para publicar |
| `AMAZON_PARTNER_TAG` | vacío | ID de Amazon Afiliados (`xxxx-21`). Si está vacío, los enlaces van sin afiliado |
| `GOOD_MORNING_TIME` / `ACTIVE_UNTIL` | `09:00` / `23:30` | Inicio y fin de la jornada |
| `SCAN_INTERVAL_MINUTES` | `30` | Minutos entre escaneos |
| `OFFER_DELAY_SECONDS` | `60` | Segundos entre ofertas |
| `MAX_OFFERS_PER_CYCLE` | `25` | Límite por escaneo |
| `MIN_DISCOUNT_PERCENT` | `20` | Descuento mínimo |
| `REPUBLISH_AFTER_DAYS` | `7` | No repetir un producto antes de N días (salvo si baja otro 5 %) |
| `OFFER_SOURCES` | `chollometro` | Fuentes de ofertas, separadas por comas |
| `INCLUDE_SWITCH_2` | `false` | Incluir juegos de Switch 2 |
| `REQUEST_DELAY_SECONDS` / `SCRAPE_PAGES` | `4` / `2` | Prudencia al consultar Amazon |
| `VERIFY_PRODUCT_PAGE` | `true` | Confirmar precios en la ficha antes de publicar |

## Diagnóstico

- Registro: `logs/hadouken_zone.log`.
- Si Amazon cambia su web y el bot deja de encontrar productos, el HTML recibido se guarda en `logs/html_debug/` para ajustar el parser (`hadouken_zone/amazon/parser.py`).
- Si Amazon muestra un CAPTCHA, el bot no intenta saltarlo: espera al siguiente escaneo.

## Aviso legal

Leer datos de Amazon o de Chollometro de forma automática puede ir en contra de sus condiciones de uso. Antes de comercializar el producto, conviene pasar a la API oficial de Amazon para afiliados (ver `docs/contexto_hadouken.md`, hoja de ruta). Cuando hay ID de afiliado, cada publicación lo indica y el buenos días incluye la declaración de Amazon Afiliados.
