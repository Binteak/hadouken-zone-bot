# Contexto del proyecto: Hadouken Zone

> Documento maestro del proyecto. Es la referencia para cualquier persona o asistente (Claude) que trabaje en él.
> Última actualización: 2026-11-02 · versión 1.1.0

## 1. Qué es

**Hadouken Zone** es un producto de software: un bot de Telegram que encuentra ofertas de videojuegos de **PlayStation 5** y **Nintendo Switch** en **Amazon.es** y las publica automáticamente en un canal de Telegram con enlace de afiliado.

- **Objetivo de negocio:** generar comisiones de Amazon Afiliados con un canal de ofertas fiable y atractivo.
- **Objetivo de producto:** que sea un proyecto profesional que se pueda **vender en el futuro**: código limpio y probado, documentación completa, branding propio y configuración por `.env`, sin valores fijos de un cliente concreto.

## 2. Funcionamiento diario (requisito del producto)

### ⚠️ Resultado de la prueba (2026-11-02): Amazon bloquea GitHub Actions

Dos ejecuciones de prueba (`dry_run`) desde GitHub Actions recibieron **HTTP 503 (bloqueo de Amazon)** en la primera petición. Las IP de GitHub son de centro de datos y Amazon las bloquea. **El workflow `publicar_ofertas.yml` está desactivado** (`disabled_manually`) para que no publique un buenos días sin ofertas. No se intenta esquivar el bloqueo (ni proxies ni rotación de IP).
GitHub se mantiene como repositorio del código y para los tests automáticos (`tests.yml`). El scraping de Amazon debe hacerse desde una **conexión doméstica** (PC, Android o Raspberry Pi en casa) o, en el futuro, mediante la API oficial de Amazon para afiliados.

### (Desactivado) GitHub Actions, una vez al día

- **Repositorio privado:** `Binteak/hadouken-zone-bot`. Workflow: `.github/workflows/publicar_ofertas.yml`.
- **Cron:** cada día a las **09:07, hora de Madrid** (`timezone: Europe/Madrid`). Se evita la hora en punto porque es cuando GitHub más retrasa.
- **Cada ejecución hace `python main.py --ciclo`:** buenos días con imagen y, a continuación, escaneo de Amazon y publicación de **todas** las ofertas nuevas, con **60 s** entre ofertas (máximo 25 por ejecución).
- **Estado entre ejecuciones:** `offers.json` y `state.json` se guardan en la rama **`estado`** (commit forzado por el propio workflow). Solo se guarda cuando se publica de verdad: las pruebas con `dry_run` no lo tocan.
- **Secrets de GitHub:** `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID`. `AMAZON_PARTNER_TAG` va vacío en el propio workflow (afiliación desactivada).
- **Ejecución manual:** *Actions → Publicar ofertas → Run workflow* (por defecto `dry_run=true`).
- **Coste:** repo privado en GitHub Free. Una ejecución diaria de 5 a 30 minutos cabe en los ~2.000 minutos mensuales. Si sobra cuota, se puede añadir una segunda ejecución por la tarde con otra línea `cron`.
- **Limitaciones:** GitHub no garantiza la puntualidad del cron (puede retrasarlo o, en incidencias, saltarse alguna ejecución). Amazon podría bloquear las IP de GitHub, que son de centro de datos. Si ocurre, el escaneo se para sin publicar y el HTML queda en los *Artifacts* de la ejecución.

### Modo alternativo: PC 24/7 (`py main.py`)

| Momento | Comportamiento |
|---|---|
| `GOOD_MORNING_TIME` (09:00, Europe/Madrid) | Mensaje de **buenos días** con la imagen `branding/telegram/cabeceras/cabecera_buenos_dias.png`. El texto cambia según el día de la semana y lleva la fecha. Se envía una sola vez al día, aunque el bot se reinicie. Si el bot arranca más de 2 horas tarde, ese día no se envía. |
| Justo después y cada `SCAN_INTERVAL_MINUTES` (30) | **Escaneo de Amazon** y publicación de **todas** las ofertas nuevas que cumplan las reglas. |
| Entre oferta y oferta | `OFFER_DELAY_SECONDS` (**60 s**). |
| Por escaneo | Máximo `MAX_OFFERS_PER_CYCLE` (25). |
| `ACTIVE_UNTIL` (23:30) | Fin de la jornada: no se escanea ni se publica hasta el día siguiente. |

**No deben funcionar los dos modos a la vez**, porque cada uno tiene su propio historial y se duplicarían las ofertas.

## 3. Reglas de negocio

Una oferta solo se publica si cumple **todas** estas condiciones (`hadouken_zone/rules.py`):

1. Es un **videojuego** de **PS5** o **Nintendo Switch**. La plataforma se detecta en el título o en la ficha. Se descartan Switch 2 (configurable con `INCLUDE_SWITCH_2`), los títulos que mencionan las dos plataformas, PS4, Xbox y PC.
2. **No es un accesorio ni hardware**: mandos, auriculares, consolas, cargadores, fundas, amiibo, tarjetas regalo, suscripciones (PS Plus, Switch Online)…
3. Está **disponible**.
4. Tiene **precio actual y precio anterior válidos**, y el actual es menor que el anterior.
5. **Descuento ≥ 20 %** (`MIN_DISCOUNT_PERCENT`).
6. **Coherencia del descuento:** se rechaza si supera el 90 % o si el precio de referencia es mayor de 300 €, porque indica un precio anterior falso o erróneo.
7. **Verificada en la ficha del producto:** antes de publicar se abre `/dp/ASIN` y se usan su precio y su precio de referencia ("Precio recomendado" o el precio más bajo reciente), que mandan sobre lo que mostraba la búsqueda.
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
                                         ├─ AmazonScraper (amazon/scraper.py)
                                         │    ├─ AmazonClient  (amazon/client.py)  HTTP, pausas, CAPTCHA
                                         │    └─ parser        (amazon/parser.py)  HTML → Offer
                                         ├─ rules.py           validación
                                         ├─ OfferStore         (storage.py)        data/offers.json
                                         ├─ cards.py           tarjeta JPG
                                         ├─ messages.py        textos HTML
                                         └─ TelegramClient     (telegram.py)       sendPhoto / sendMessage
```

**Flujo de un escaneo:**
1. Recorre las búsquedas de `config.SEARCHES` (juegos PS5 y juegos Switch), `SCRAPE_PAGES` páginas de cada una, con pausas de `REQUEST_DELAY_SECONDS` más un margen aleatorio.
2. Lee los resultados (ASIN, título, precio, precio tachado e imagen) y quita los duplicados.
3. Aplica las reglas y la deduplicación, y ordena por descuento.
4. Verifica cada candidata en su ficha y vuelve a aplicar las reglas.
5. Publica cada oferta con una pausa de 60 s y la marca como publicada (solo si `DRY_RUN=false`).

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

- **Scraping de Amazon:** puede ir en contra de las Condiciones de Uso de Amazon y del Acuerdo de Afiliados. Además, Amazon cambia su HTML y puede mostrar CAPTCHA. Para vender el producto con garantías, hay que migrar a la **API oficial de Amazon para afiliados**. El diseño ya lo permite: basta con sustituir `amazon/scraper.py` por otra fuente que devuelva objetos `Offer`.
- **Precios:** los precios de Amazon cambian. El precio publicado es el del momento de la verificación.
- **X/Twitter:** fuera de alcance (la API devolvió 403). Se retiró del producto en la versión 1.0.0.

## 11. Hoja de ruta

1. Primer día real de publicación (`DRY_RUN=false`). La afiliación (`binteak-21`) se activará solo cuando lo indique el titular.
2. Revisar el parser con el HTML real de Amazon tras el primer escaneo (`logs/html_debug/`).
3. Migrar a la API oficial de Amazon para afiliados.
4. Mostrar la hora de consulta del precio en el pie ("precio a las 10:30").
5. ~~Probar GitHub Actions~~ → bloqueado por Amazon (503). Producción desde una conexión doméstica: tarea diaria de Windows en el PC, o un Android o una Raspberry Pi en casa.
6. Resumen semanal automático ("Top 5 de la semana", la cabecera ya existe).
7. Panel de estadísticas (ofertas publicadas y clics).
8. Producto vendible: instalador, licencia y manual de cliente.
