"""Diagnóstico TEMPORAL (2): ASIN en ofertas de Amazon de Chollometro y RSS de videojuegos."""
import re
import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept-Language": "es-ES,es;q=0.9"}
s = requests.Session(); s.headers.update(UA)

print("=== Enlaces RSS en páginas de grupo / búsqueda")
for page in ["https://www.chollometro.com/grupo/videojuegos", "https://www.chollometro.com/grupo/ps5",
             "https://www.chollometro.com/grupo/nintendo-switch", "https://www.chollometro.com/search?q=ps5"]:
    try:
        r = s.get(page, timeout=25)
        rss = sorted(set(re.findall(r"""(https?://www\.chollometro\.com/rss/[^"'\s<>]+|/rss/[^"'\s<>]+)""", r.text)))
        print(f"  {page} -> HTTP {r.status_code} | rss={rss[:8]}")
    except Exception as e:
        print(f"  {page} ERROR {e}")

print("\n=== Candidatas de RSS")
cands = ["https://www.chollometro.com/rss/grupo/videojuegos-gaming", "https://www.chollometro.com/rss/grupo/ps5",
         "https://www.chollometro.com/rss/grupo/juegos-ps5", "https://www.chollometro.com/rss/grupo/switch",
         "https://www.chollometro.com/rss/grupo/juegos-nintendo-switch", "https://www.chollometro.com/rss/search?q=ps5",
         "https://www.chollometro.com/rss/buscar?q=ps5", "https://www.chollometro.com/rss/keyword/ps5"]
for u in cands:
    try:
        r = s.get(u, timeout=25)
        print(f"  {u} -> HTTP {r.status_code} items={len(re.findall('<item>', r.text))}")
    except Exception as e:
        print(f"  {u} ERROR {e}")

print("\n=== Ofertas de Amazon en el RSS 'nuevos' y 'hot': cómo aparece el enlace a Amazon")
seen = 0
for feed in ["https://www.chollometro.com/rss/nuevos", "https://www.chollometro.com/rss/hot"]:
    txt = s.get(feed, timeout=25).text
    for it in re.findall(r"<item>(.*?)</item>", txt, re.S):
        if 'name="Amazon"' not in it or seen >= 3:
            continue
        seen += 1
        link = re.search(r"<link>(.*?)</link>", it, re.S).group(1).strip()
        print(f"\n  RSS item ({link}):")
        for m in re.finditer(r"(visit|amazon|dp/)", it, re.I):
            print("    item…", it[max(0, m.start()-60):m.start()+90].replace("\n", " "))
            break
        r = s.get(link, timeout=25)
        html = r.text
        print(f"    página HTTP {r.status_code}, {len(html)} bytes")
        for pat in [r"visit\\?/[a-z]+\\?/\d+", r"amazon\.es", r"/dp/[A-Z0-9]{10}", r'"merchantUrl"', r"linkCloaked|cloakedUrl|dealUrl|\"link\""]:
            ms = list(re.finditer(pat, html))
            if ms:
                m = ms[0]
                print(f"    [{pat}] x{len(ms)}: …{html[max(0,m.start()-80):m.start()+140]!r}")
            else:
                print(f"    [{pat}] sin coincidencias")
        v = re.search(r"https?:\\?/\\?/www\.chollometro\.com\\?/visit\\?/[a-z]+\\?/\d+", html)
        if v:
            vurl = v.group(0).replace("\\/", "/")
            rv = s.get(vurl, timeout=25, allow_redirects=False)
            print(f"    visit {vurl} -> HTTP {rv.status_code} Location={rv.headers.get('Location','')[:160]}")
if not seen:
    print("  (ahora mismo no hay ofertas de Amazon en esos RSS)")
