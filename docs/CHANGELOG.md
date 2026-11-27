# Registro de cambios

## 1.5.0 — 2026-11-27 · Hilo de buenas noches
- **Buenas noches a las 23:00** (`GOOD_NIGHT_TIME`, `GOOD_NIGHT_TOP`): cabecera con el resumen del día (número de ofertas, reparto por plataforma y la mejor) y, como **respuestas sin sonido**, las 3 mejores ofertas publicadas ese día con su tarjeta. Después no se publican más ofertas hasta el día siguiente. Nuevo `py main.py --buenas-noches`.
- Nueva cabecera `cabecera_buenas_noches.png`: mascota dormida (ojos cerrados, cejas relajadas, coloretes), luna creciente, «Z z z» que no pisan la cabeza ni la luna y etiquetas de plataforma en dos filas. Se genera con `tools/branding/generar_buenas_noches.py`. `cards._fondo()` admite `trama=False` (sin puntos en la esquina).
- Telegram: `send_photo` devuelve el `message_id` y admite `reply_to` y `silent`.
- `OfferStore.published_on()`: ofertas publicadas en un día local. 128 tests.

## 1.4.0 — 2026-11-27 · PS4, Switch 2 y nuevos colores de plataforma
- **PS4** como plataforma nueva (`INCLUDE_PS4`, activa por defecto), con etiqueta **azul** y hashtag `#PS4`. «PS4/PS5» se publica como PS5.
- **Switch 2** activada por defecto (`INCLUDE_SWITCH_2=true`) como plataforma propia: etiqueta roja con el **«2» en un círculo blanco** para distinguirla de la Switch, y hashtag `#NintendoSwitch2`.
- **PS5** pasa a etiqueta **blanca** con texto oscuro.
- Xbox sigue como una sola plataforma (Series X|S y Xbox One).
- Textos del canal, guía de marca y búsquedas de la fuente `amazon` actualizados. 120 tests.

## 1.3.0 — 2026-11-27 · Xbox y disparador cada 5 minutos
- **Xbox**: se publican juegos de Xbox Series X|S y Xbox One (`INCLUDE_XBOX`, activo por defecto). Etiqueta verde `XBOX` en la tarjeta (`#107C10`), hashtag `#Xbox` y textos del canal actualizados. Game Pass y Xbox Live se excluyen como suscripciones. Un título con más de una plataforma sigue descartándose.
- **Producción cada 5 minutos con cron-job.org** (`workflow_dispatch` por la API de GitHub). Diagnóstico: el `schedule` de GitHub solo lanzaba 3-4 pasadas al día y el RSS de "nuevos" de Chollometro solo cubre las 30 últimas ofertas (minutos en horas punta), así que no salía casi nada. El `schedule` queda como respaldo.
- El repositorio es público: GitHub Actions no consume minutos (coste 0 €). Historial revisado: sin secretos.
- 113 tests (10 nuevos).

## 1.2.1 — 2026-11-02 · Descuento mínimo 15 %
- `MIN_DISCOUNT_PERCENT` pasa de 20 % a **15 %** (más volumen de ofertas). Se actualizan los mensajes, la imagen de bienvenida y la documentación.
- Cron del workflow en UTC (sin `timezone:`), porque las pasadas programadas no arrancaban. El horario de Madrid lo sigue controlando el bot.
- Nuevo `py main.py --verificar`: comprueba el token y el canal de Telegram sin publicar nada. El workflow lo ejecuta antes de cada pasada real.

## 1.2.0 — 2026-11-02 · Fuentes enchufables y Chollometro (producción en GitHub Actions)
- Nueva arquitectura de **fuentes de ofertas** (`hadouken_zone/sources/`): contrato común `find_offers`, registro de fuentes y `OFFER_SOURCES` en `.env`. El scraper de Amazon pasa a `sources/amazon/`.
- **Fuente `chollometro`**: lee los RSS (nuevos y populares), se queda con las ofertas de Amazon y lee de cada una el precio, el precio anterior (`nextBestPrice`), si ha caducado y el **ASIN** (por la redirección `/visit/threadmain/<id>`). Limpia el título y publica el enlace limpio de Amazon.
- Validado en GitHub Actions con datos reales: 8 de 8 ofertas de Amazon leídas con ASIN y precios.
- Pipeline multi-fuente: deduplicación por ASIN entre fuentes; una fuente bloqueada no detiene a las demás.
- Modo cron: cada ejecución programada escanea, sin intervalo mínimo.
- Workflow de publicación **reactivado**: cada 30 min de 09:07 a 23:07 (Europe/Madrid).
- 103 tests (21 nuevos). Acciones de GitHub actualizadas (checkout v5, setup-python v6).

## 1.1.0 — 2026-11-02 · Automatización en GitHub Actions
- Nuevo modo `py main.py --ciclo`: una pasada del calendario (buenos días + escaneo) y termina. Pensado para cron.
- `.github/workflows/publicar_ofertas.yml`: ejecución diaria a las 09:07 (Europe/Madrid), estado persistente en la rama `estado`, ejecución manual en `dry_run` y registros como *artifact*.
- `.github/workflows/tests.yml`: tests en cada push.
- Repositorio privado `Binteak/hadouken-zone-bot`.
- Prueba en GitHub Actions: Amazon responde 503 (bloqueo de IP de centro de datos). Workflow de publicación desactivado; los tests siguen activos.

## 1.0.0 — 2026-11-02 · Producto Hadouken Zone

**Proyecto**
- La carpeta pasa de `amazon-deals-bot` a `hadouken-zone`, con una estructura de producto: código, tests, branding, herramientas, scripts y documentación.
- Documentación nueva: `README.md`, `docs/contexto_hadouken.md` (documento maestro, que incluye la arquitectura) y la guía de marca en `branding/README.md`.

**Funcionalidad nueva**
- Fuente de ofertas: **Amazon.es** (`hadouken_zone/amazon/`). Busca juegos de PS5 y Switch, verifica cada oferta en su ficha, detecta CAPTCHA sin intentar saltarlo y guarda el HTML de diagnóstico.
- Reglas: descuento mínimo del 20 %, coherencia del descuento (máximo 90 % y referencia de hasta 300 €), exclusión de accesorios y hardware, detección de plataforma y descarte de Switch 2 (configurable).
- Enlaces de afiliado con `AMAZON_PARTNER_TAG` y avisos legales de Amazon Afiliados.
- Planificador diario: **buenos días a las 09:00** con imagen, **escaneo cada 30 min**, **60 s entre ofertas** y jornada hasta las 23:30.
- Cada oferta se publica como **foto** con su tarjeta visual y el texto en HTML.
- Historial anti-duplicados por ASIN (republica a los 7 días o si el precio baja otro 5 %).
- Registro rotativo en `logs/`.
- **81 tests** con pytest (parser, reglas, afiliados, mensajes, almacenamiento, planificador, ciclo completo, tarjetas y Telegram).
- Branding: nueva `cabecera_buenos_dias.png`.

**Afiliación**
- ID `binteak-21` registrado pero desactivado hasta nuevo aviso: las URL se publican sin `tag`.

**Retirado**
- Fuentes RSS (Chollometro, Ofertitas): sus candidatos nunca se podían verificar, así que no se publicaban. Las sustituye Amazon.
- Publicador de X/Twitter: fuera de alcance (error 403).
- Vistas previas circulares del avatar (duplicadas) y `data/candidates.json` / `data/products.json` (formatos antiguos).
- Todo lo retirado está en la copia de seguridad `Proyectos\hadouken-zone_respaldo_<fecha>\`, fuera del proyecto.

## 0.2.0 — 2026-11-02 · Reorganización
- Código agrupado en el paquete `hadouken_zone/`, branding en `branding/` y herramientas de diseño en `tools/branding/`.

## 0.1.0 — 2026-10-30
- Primera versión: RSS, publicación en Telegram y prueba en X/Twitter.
