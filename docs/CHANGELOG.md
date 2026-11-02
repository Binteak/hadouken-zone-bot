# Registro de cambios

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
