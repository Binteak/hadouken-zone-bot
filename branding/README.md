# Branding Hadouken Zone

Guía de marca y recursos gráficos del canal de Telegram.

## Contenido

| Carpeta | Qué hay | Uso |
|---|---|---|
| `originales/` | Avatar (400×400) y banner (600×200) originales | Fuente de todo lo demás. No editar. |
| `mascota/` | Mascota en alta resolución con fondo transparente (cabeza y pose hadouken) | Base para nuevos diseños. La usa también el generador de tarjetas. |
| `fuentes/` | Tipografía Inter (licencia OFL, ver `LICENCIA_OFL.txt`) | La usan el bot y las herramientas de diseño. |
| `telegram/avatar/` | Foto del canal 640×640 en morado y naranja | Subir tal cual; Telegram la recorta en círculo. |
| `telegram/publicaciones/` | Imagen de bienvenida 1280×720 | Mensaje fijado del canal. |
| `telegram/cabeceras/` | Buenos días, Chollo del día, Oferta flash, Top 5 semanal, Especial PS5, Especial Switch | La de buenos días la publica el bot cada mañana; el resto, para publicaciones especiales. |
| `telegram/stickers/` | 4 stickers 512×512 PNG transparentes | Crear el paquete con @Stickers en Telegram. |
| `telegram/tarjetas_ejemplo/` | Dos tarjetas de oferta de muestra | Referencia visual de lo que genera `hadouken_zone/cards.py`. Las carátulas son inventadas. |

## Paleta

| Nombre | HEX | Uso |
|---|---|---|
| Morado fondo | `#372F58` | Fondo principal (el de los originales) |
| Morado oscuro | `#1A1530` | Bordes del degradado, pie de las tarjetas |
| Tinta | `#161028` | Contornos gruesos de textos y piezas |
| Cian | `#52DEF5` | Contorno de la mascota, acentos, sombras de texto |
| Naranja | `#FF8024` | Energía del hadouken, sombras de texto |
| Amarillo | `#FFD640` | Precios, estrellas de descuento, rayos |
| Rojo | `#E8362E` | Avisos (Agotado) |
| Azul PS5 | `#0070E0` | Etiqueta de plataforma PS5 |
| Rojo Switch | `#E40014` | Etiqueta de plataforma Switch |
| Verde Xbox | `#107C10` | Etiqueta de plataforma Xbox |

## Tipografía

- **Titulares:** Inter Display Black Italic, con contorno oscuro grueso y sombra desplazada en cian o naranja (estilo pegatina, igual que la mascota).
- **Textos y etiquetas:** Inter Bold / ExtraBold.

## Reglas básicas

- La mascota siempre con su contorno cian, sobre fondo morado o transparente.
- No usar logotipos oficiales de PlayStation ni Nintendo: las plataformas se indican con etiquetas de texto (PS5 / SWITCH).
- Formatos: publicaciones 1280×720, avatar 640×640, stickers 512×512.

## Regenerar los diseños

Los diseños se generan con código, así que se pueden rehacer o modificar (ver `tools/branding/`):

```powershell
py -m pip install -r requirements-dev.txt
py tools\branding\mejorar_mascota.py     # solo si cambian los originales
py tools\branding\generar_disenos.py
```
