"""Diagnóstico TEMPORAL (4): datos de la oferta principal en Chollometro."""
import re
import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept-Language": "es-ES,es;q=0.9"}
s = requests.Session(); s.headers.update(UA)
txt = s.get("https://www.chollometro.com/rss/nuevos", timeout=25).text
items = [it for it in re.findall(r"<item>(.*?)</item>", txt, re.S) if 'name="Amazon"' in it]
print("ITEM RSS COMPLETO:\n", items[0][:1800])
link = re.search(r"<link>(.*?)</link>", items[0], re.S).group(1).strip()
tid = re.search(r"-(\d+)$", link).group(1)
html = s.get(link, timeout=25).text
print("\nthreadId", tid, "apariciones:", len(re.findall(tid, html)))
for m in list(re.finditer(r'threadId\\?"\s*:\s*\\?"?' + tid, html))[:2]:
    print("\n--- contexto threadId ---\n", html[max(0, m.start()-300):m.start()+1500])
for tag in ["data-vue3", "__INITIAL_STATE__", "application/ld+json", "og:title", "og:image", "og:price", "product:price"]:
    i = html.find(tag)
    print(f"\n[{tag}] pos={i}:", html[i:i+400].replace("\n", " ") if i >= 0 else "-")
