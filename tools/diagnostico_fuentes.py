"""Diagnóstico TEMPORAL: ¿qué fuentes de ofertas responden desde GitHub Actions?"""
import re
import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept-Language": "es-ES,es;q=0.9"}
FEEDS = [
    "https://www.chollometro.com/rss/hot",
    "https://www.chollometro.com/rss/nuevos",
    "https://www.chollometro.com/rss/grupo/videojuegos",
    "https://www.chollometro.com/rss/grupo/playstation-5",
    "https://www.chollometro.com/rss/grupo/nintendo-switch",
    "https://www.ofertitas.es/etiqueta/amazon-espana/feed/",
]
s = requests.Session(); s.headers.update(UA)
deal_links = []
for url in FEEDS:
    try:
        r = s.get(url, timeout=25)
        items = re.findall(r"<item>(.*?)</item>", r.text, re.S)
        print(f"\n=== {url}\n  HTTP {r.status_code} | {len(r.text)} bytes | items: {len(items)}")
        for it in items[:40]:
            title = re.sub(r"<!\[CDATA\[|\]\]>", "", (re.search(r"<title>(.*?)</title>", it, re.S) or [None, ""])[1]).strip()
            link = (re.search(r"<link>(.*?)</link>", it, re.S) or [None, ""])[1].strip()
            low = it.lower()
            if any(k in low for k in ("ps5", "playstation 5", "switch")) :
                merchant = re.search(r"<pepper:merchant[^>]*name=\"([^\"]+)\"", it)
                price = re.search(r"<pepper:merchant[^>]*price=\"([^\"]+)\"", it)
                print(f"  - {title[:90]}")
                print(f"      tienda={merchant.group(1) if merchant else '?'} precio={price.group(1) if price else '?'} amazon_en_item={'amazon' in low}")
                if "chollometro" in link and len(deal_links) < 4:
                    deal_links.append(link)
        if items:
            tags = sorted(set(re.findall(r"<([a-zA-Z]+:[a-zA-Z]+)", items[0])))
            print("  etiquetas del item:", tags)
    except Exception as e:
        print(f"\n=== {url}\n  ERROR {e.__class__.__name__}: {e}")

print("\n=== Páginas de oferta (buscar enlace a Amazon / ASIN)")
for link in deal_links:
    try:
        r = s.get(link, timeout=25)
        visits = sorted(set(re.findall(r"https://www\.chollometro\.com/visit/[a-z]+/\d+", r.text)))
        asins = sorted(set(re.findall(r"amazon\.es/(?:[^\s\"']*/)?dp/([A-Z0-9]{10})", r.text)))
        prev = re.findall(r"(?:Precio anterior|precio original|PVPR)[^0-9]{0,40}([\d.,]+\s?€)", r.text, re.I)[:2]
        print(f"  {link}\n    HTTP {r.status_code} | visit={visits[:2]} | ASIN en página={asins[:3]} | precio anterior={prev}")
        for v in visits[:1]:
            rv = s.get(v, timeout=25, allow_redirects=False)
            loc = rv.headers.get("Location", "")
            m = re.search(r"/dp/([A-Z0-9]{10})", loc)
            print(f"    visit -> HTTP {rv.status_code} Location={loc[:120]} ASIN={m.group(1) if m else None}")
    except Exception as e:
        print(f"  {link} ERROR {e}")

print("\n=== Imágenes de Amazon (CDN)")
r = s.get("https://m.media-amazon.com/images/I/71J3kNEabQL._AC_SL1500_.jpg", timeout=25)
print(f"  m.media-amazon.com HTTP {r.status_code} {r.headers.get('content-type')}")
