"""Diagnóstico TEMPORAL (3): estructura de ofertas de Amazon en Chollometro (guarda ejemplos)."""
import json, os, re
import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept-Language": "es-ES,es;q=0.9"}
s = requests.Session(); s.headers.update(UA)
os.makedirs("muestras", exist_ok=True)
feeds = {"nuevos": "https://www.chollometro.com/rss/nuevos", "hot": "https://www.chollometro.com/rss/hot"}
amazon_links = []
for name, url in feeds.items():
    txt = s.get(url, timeout=25).text
    open(f"muestras/rss_{name}.xml", "w", encoding="utf-8").write(txt)
    for it in re.findall(r"<item>(.*?)</item>", txt, re.S):
        if 'name="Amazon"' in it:
            amazon_links.append(re.search(r"<link>(.*?)</link>", it, re.S).group(1).strip())
print("ofertas de Amazon en RSS:", len(amazon_links))
games = [l for l in amazon_links if re.search(r"ps5|playstation|switch|juego", l)]
pick = (games + [l for l in amazon_links if l not in games])[:3]
for i, link in enumerate(pick):
    html = s.get(link, timeout=25).text
    open(f"muestras/oferta_{i}.html", "w", encoding="utf-8").write(html)
    print("\n==", link)
    for key in ["price", "nextBestPrice", "percentage", "discount", "isExpired", "temperature", "title", "mainImage", "merchant", "status", "expired"]:
        ms = re.findall(r'\\?"' + key + r'\\?":\s*([^,}]{0,80})', html)
        print(f"  {key}: {ms[:4]}")
