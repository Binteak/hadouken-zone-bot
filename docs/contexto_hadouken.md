# Contexto del proyecto: Hadouken Zone

> Documento maestro del proyecto. Es la referencia para cualquier persona o asistente (Claude) que trabaje en él.
> Última actualización: 2026-11-02 · versión 1.2.1

## 1. Qué es

**Hadouken Zone** es un producto de software: un bot de Telegram que encuentra ofertas de videojuegos de **PlayStation 5** y **Nintendo Switch** en **Amazon.es** y las publica automáticamente en un canal de Telegram con enlace de afiliado.

- **Objetivo de negocio:** generar comisiones de Amazon Afiliados con un canal de ofertas fiable y atractivo.
- **Objetivo de producto:** que sea un proyecto profesional que se pueda **vender en el futuro**: código limpio y probado, documentación completa, branding propio y configuración por `.env`, sin valores fijos de un cliente concreto.

## 2. Funcionamiento diario (requisito del producto)

### Producción: GitHub Actions + fuente Chollometro (gratis, sin equipos encendidos)

- **Repositorio privado:** `Binteak/hadouken-zone-bot`. Workflow: `.github/workflows/publicar_ofertas.yml`.
- **Cron:** cada 30 minutos, de **09:07 a 23:07, hora de Madrid** (`7,37 9-22 * * *` y `7 23 * * *`, con `timezone: Europe/Madrid`). Se evita la hora en punto, que es cuando GitHub más se retrasa.
- **Cada ejecución hace `python main.py --ciclo`:**
  - A las 09:07, **buenos días** con imagen.
  - En cada ejecución, **escaneo de las fuentes** y publicación de **todas** las ofertas nuevas válidas, con **60 s** entre ofertas (máximo 25 por ejecución).
- **Estado entre ejecuciones:** `offers.json` y `state.json` se guardan en la rama **`estado`** (commit forzado del propio workflow). Solo se guarda cuando se publica de verdad.
- **Secrets de GitHub:** `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID`. `AMAZON_PARTNER_TAG` va vacío en el workflow (afiliación desactivada).
- **Ejecución manual:** *Actions → Publicar ofertas → Run workflow* (por defecto `dry_run=true`).
- **Coste:** repo privado en GitHub Free (~2.000 min/mes). Unas 30 ejecuciones al día de ~1 minuto, más 1 minuto por oferta publicada, suman unos 1.000 minutos al mes.
- **Por qué no se lee Amazon desde GitHub:** la prueba del 2026-11-02 dio **HTTP 503**, porque Amazon bloquea las IP de centros de datos. No se intenta esquivar (ni proxies ni rotación de IP).

### Alternativa en casa: PC 24/7 (`py main.py`)

Buenos días a las 09:00 (`GOOD_MORNING_TIME`), escaneo cada 30 minutos (`SCAN_INTERVAL_MINUTES`), 60 s entre ofertas y fin de la jornada a las 23:30 (`ACTIVE_UNTIL`). Desde casa puede usar también la fuente `amazon` (`OFFER_SOURCES=chollometro,amazon`).
**No deben funcionar el modo GitHub y el modo PC a la vez:** cada uno tiene su propio historial y se duplicarían las ofertas.

## 2 bis. Fuentes de ofertas (`hadouken_zone/sources/`)

El bot no depende de una sola web. Cada fuente implementa `find_offers(limit, is_new)` y devuelve objetos `Offer` validados con `rules.py`. Se activan con `OFFER_SOURCES` (en orden de prioridad), y el pipeline las combina sin repetir ASIN. Si una fuente falla o está bloqueada, las demás siguen funcionando.

| Fuente | Estado | Cómo obtiene la oferta |
|---|---|---|
| `chollometro` | **Activa en producción** | Recorre los RSS `nuevos` y `hot` y se queda con las ofertas cuya tienda es **Amazon**. Descarta antes las que no son juegos de PS5 o Switch, según el título. De la página de cada oferta lee el objeto JSON de la oferta principal (`threadId`): `price`, `nextBestPrice` (precio anterior), `linkHost`, `status` y si ha caducado. El **ASIN** sale de la redirección `/visit/threadmain/<id>` (`Location` con `amazon.es/dp/ASIN`), sin entrar en Amazon. El título se limpia de precios y cupones. |
| `amazon` | Disponible (solo en casa) | Búsqueda en Amazon.es y verificación del precio en la ficha del producto. |

**Futuras fuentes** (añadir un módulo en `sources/` y registrarlo en `REGISTRY`): otras webs de chollos, la API oficial de Amazon para afiliados (cuando se active la afiliación) o la fuente `amazon` desde un equipo en casa.

## 3. Reglas de negocio

Una oferta solo se publica si cumple **todas** estas condiciones (`hadouken_zone/rules.py`):

1. Es un **videojuego** de **PS5** o **Nintendo Switch**. La plataforma se detecta en el título o en la ficha. Se descartan Switch 2 (configurable con `INCLUDE_SWITCH_2`), los títulos que mencionan las dos plataformas, PS4, Xbox y PC.
2. **No es un accesorio ni hardware**: mandos, auriculares, consolas, cargadores, fundas, amiibo, tarjetas regalo, suscripciones (PS Plus, Switch Online)…
3. Está **disponible**.
4. Tiene **precio actual y precio anterior válidos**, y el actual es menor que el anterior.
5. **Descuento ≥ 15 %** (`MIN_DISCOUNT_PERCENT`; era 20 % hasta la versión 1.2.0, rebajado por decisión del titular para tener más volumen).
6. **Coherencia del descuento:** se rechaza si supera el 90 % o si el precio de referencia es mayor de 300 €, porque indica un precio anterior falso o erróneo.
7. **Precio comprobado según la fuente:** con la fuente `amazon` se abre la ficha `/dp/ASIN` y su precio manda. Con `chollometro` se usan el precio y el precio anterior publicados en la oferta (moderada por la comunidad) y se descartan las caducadas. Si una oferta no tiene precio anterior, no se publica, porque el descuento no se puede comprobar.
8. **Sin duplicados:** no se vuelve a publicar un ASIN durante `REPUBLISH_AFTER_DAYS` (7) días, salvo que su precio baje al menos otro 5 %. El historial está en `data/offers.json`.

Las ofertas de cada escaneo se publican de **mayor a menor descuento**.

## 4. Enlaces de afiliado

- Formato: `https://www.amazon.es/dp/<ASIN>?tag=<AMAZON_PARTNER_TAG>` (`hadouken_zone/affiliate.py`).
- **No se inventan identificadores.** Si `AMAZON_PARTNER_TAG` está vacío, el enlace es el normal del producto y no se muestra ningún aviso de afiliado.
- Con ID de afiliado: cada publicación indica *"Enlace de afiliado"* y el buenos días incluye la declaración obligatoria de Amazon Afiliados.
- **Estado actual (decisión del titular, 2026-11-02): afiliación DESACTIVADA hasta nuevo aviso.** El ID de Amazon Afiliados del proyecto es `binteak-21`, pero **no debe añadirse a las URL** ni activarse en `.env` hasta que el titular lo indique expresamente. Mientras tanto, `AMAZON_PARTNER_TAG` queda vacío y el ID se guarda solo como comentario (`# AMAZON_PARTNER_TAG=binteak-21`).
- Para activarlo (solo con permiso expreso): `AMAZON_PARTNER_TAG=binteak-21` en `.env` y reiniciar el bot.

## 5. Formato de las publicaciones

- **Oferta:** foto con la tarjeta 1280x720 (`cards.py`: carátula, etiqueta de plataforma, estrella con el %, precio anterior tachado, precio actual y ahorro) y un pie en HTML: título, plataforma, precios, ahorro, enlace "Ver oferta en Amazon" y hashtags. Si falla la imagen, se envía solo el texto.
- **Buenos días:** imagen de cabecera más un texto con siete variantes, una por día de la semana.
- **Presentación del canal:** `py main.py --test`.
- Pensado para leerse en el móvil: frases cortas, emojis como iconos y precios en formato español (`1.299,99 €`).

## 6. Arquitectura

```
main.py ─► Scheduler (scheduler.py) ─► Pipeline (pipeline.py)
                                         ├─ Fuentes (sources/, OFFER_SOURCES)
                                         │    ├─ ChollometroSource (sources/chollometro.py)  RSS + oferta + ASIN
                                         │    └─ AmazonScraper     (sources/amazon/)          HTTP, parser, CAPTCHA
                                         ├─ rules.py           validación
                                         ├─ OfferStore         (storage.py)        data/offers.json
                                         ├─ cards.py           tarjeta JPG
                                         ├─ messages.py        textos HTML
                                         └─ TelegramClient     (telegram.py)       sendPhoto / sendMessage
```

**Flujo de un escaneo:**
1. Cada fuente activa devuelve sus ofertas válidas y nuevas: aplica `rules.py` y comprueba con el historial que no se hayan publicado ya.
2. El pipeline las combina sin repetir ASIN y las ordena de mayor a menor descuento.
3. Publica cada oferta con una pausa de 60 s y la marca como publicada (solo si `DRY_RUN=false`).

**Robustez:**
- Si aparece un CAPTCHA o un bloqueo, el escaneo se detiene sin intentar saltarlo y se reintenta en el siguiente.
- Un error de red solo genera un aviso en el registro.
- Si una búsqueda devuelve 0 resultados, se guarda el HTML en `logs/html_debug/` para ajustar el parser.
- Las escrituras JSON son atómicas.

## 7. Estructura de carpetas

| Carpeta | Contenido |
|---|---|
| `hadouken_zone/` | Código del producto (ver arquitectura). |
| `tests/` | Tests con pytest. `tests/fixtures/` contiene HTML de Amazon de ejemplo que documenta la estructura esperada. |
| `branding/` | Originales, mascota HD, fuentes Inter (OFL), avatar, bienvenida, cabeceras (incluida la de buenos días), stickers, tarjetas de ejemplo y guía de marca. |
| `tools/branding/` | `mejorar_mascota.py` (alta resolución) y `generar_disenos.py` (todos los diseños). |
| `scripts/` | `iniciar_bot.ps1` y `programar_inicio_windows.ps1` (modo PC 24/7). |
| `.github/workflows/` | `publicar_ofertas.yml` (producción diaria) y `tests.yml` (tests en cada push). |
| `docs/` | Este documento y `CHANGELOG.md`. |
| `data/`, `logs/` | Se generan al ejecutar el bot. Están fuera de control de versiones. |

## 8. Tecnología y entorno

- Python 3.10+ (en el PC de desarrollo, 3.13). Dependencias: requests, python-dotenv, beautifulsoup4, pillow, tzdata. Para desarrollo, además: pytest, numpy, scipy y opencv-python.
- Ruta local: `C:\Users\Asus\Desktop\Proyectos\hadouken-zone`. Repositorio: `github.com/Binteak/hadouken-zone-bot` (privado, rama `main`, más la rama `estado` que gestiona el bot).
- Producción en GitHub Actions (gratis, una vez al día). Alternativa: el PC con Windows encendido.
- Canal: `TELEGRAM_CHAT_ID` (por defecto `@hadoukenzone`).

## 9. Cómo trabajar en el proyecto

1. Antes de modificar el código, lee este documento y los módulos afectados.
2. Trabaja de forma incremental y modular. No reescribas lo que funciona, y si eliminas una funcionalidad, justifícalo.
3. Toda regla de negocio nueva debe ir en `rules.py`, con su test.
4. Ejecuta `py -m pytest` antes de dar un cambio por bueno.
5. La configuración va en `.env` y `config.py`, nunca fija en el código. Los secretos solo van en `.env`.
6. Documenta los cambios en `docs/CHANGELOG.md` y, si cambia el comportamiento, en este documento.
7. Explica los cambios en español, indicando los archivos afectados y los comandos exactos de Windows (PowerShell).
8. La carpeta del proyecto debe mantenerse limpia: nada de proyectos dentro del proyecto, ni duplicados ni archivos sueltos.

## 10. Riesgos y limitaciones

- **Dependencia de Chollometro:** si cambia su web o limita el acceso, la fuente deja de encontrar ofertas. Lo detectan los avisos del registro de GitHub Actions. Reutilizar sus ofertas de forma automática es una zona gris respecto a sus condiciones de uso. Además, solo se publican ofertas que la comunidad ya ha encontrado, y algunos días habrá pocas o ninguna de juegos en Amazon.
- **Scraping de Amazon:** puede ir en contra de sus Condiciones de Uso y del Acuerdo de Afiliados; además, Amazon bloquea los centros de datos y muestra CAPTCHA. Para vender el producto con garantías, hay que migrar a la **API oficial de Amazon para afiliados**, que sería una fuente más en `sources/`.
- **Precios:** los precios de Amazon cambian. El precio publicado es el del momento de la verificación.
- **X/Twitter:** fuera de alcance (la API devolvió 403). Se retiró del producto en la versión 1.0.0.

## 11. Hoja de ruta

1. Primer día real de publicación (`DRY_RUN=false`). La afiliación (`binteak-21`) se activará solo cuando lo indique el titular.
2. Revisar el parser con el HTML real de Amazon tras el primer escaneo (`logs/html_debug/`).
3. Migrar a la API oficial de Amazon para afiliados.
4. Mostrar la hora de consulta del precio en el pie ("precio a las 10:30").
5. ~~Leer Amazon desde GitHub Actions~~: bloqueado (503). Producción con la fuente `chollometro` desde GitHub. Para leer Amazon directamente hace falta un equipo en casa o la API oficial.
6. Añadir más fuentes de chollos para tener más volumen de ofertas.
7. Resumen semanal automático ("Top 5 de la semana", la cabecera ya existe).
8. Panel de estadísticas (ofertas publicadas y clics).
9. Producto vendible: instalador, licencia y manual de cliente.
