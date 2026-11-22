"""Rend les visuels Sportscast avec l'atelier, sans intervention.

Usage : python render.py plans/2026-11-23.json
Lit le plan de la semaine, télécharge les covers (liens RSS), remplit l'atelier
(atelier.html) dans Chromium et écrit, pour chaque post :
  images/<semaine>/<slug>-post.png (4:5) et -story.png (9:16)
  images/<semaine>/<slug>-carrousel-NN.png pour un carrousel
plus images/<semaine>/manifest.json (chemins + légende générée par l'atelier).
"""
import asyncio, base64, json, mimetypes, pathlib, sys, urllib.request

from playwright.async_api import async_playwright

ROOT = pathlib.Path(__file__).resolve().parent


def data_url(src):
    if not src:
        return None
    if src.startswith("data:"):
        return src
    p = pathlib.Path(src)
    if p.exists():
        raw, mime = p.read_bytes(), mimetypes.guess_type(p.name)[0] or "image/jpeg"
    else:
        req = urllib.request.Request(src, headers={"User-Agent": "Mozilla/5.0 Sportscast"})
        with urllib.request.urlopen(req, timeout=30) as r:
            raw, mime = r.read(), (r.headers.get_content_type() or "image/jpeg")
    return f"data:{mime};base64," + base64.b64encode(raw).decode()


JS_FILL = """
async (p) => {
  localStorage.clear();
  loadSeries(p.series, {rotate: true});
  const set = (id, v) => { if (v !== undefined && v !== null) document.querySelector('#' + id).value = String(v); };
  set('sport', p.sport);
  if (p.headline !== undefined) {
    if (typeof p.headline === 'number') set('headline', p.headline);
    else { set('headline', 'custom'); set('headlineCustom', p.headline); }
  }
  set('tagline', p.tagline);
  if (SERIES[p.series].carousel) {
    lastMulti = isMulti(); headOptions();
    if (p.headline !== undefined) {
      if (typeof p.headline === 'number') set('headline', p.headline);
      else { set('headline', 'custom'); set('headlineCustom', p.headline); }
    }
    state.items = p.items.map(it => ({name: it.name, line2: it.line2, handle: it.handle || '', sport: it.sport, url: it.url || '', cover: it.cover}));
  } else {
    ['name', 'line2', 'duree', 'date', 'handle', 'url'].forEach(f => set(f, p[f]));
    state.cover = p.cover;
  }
  render();
  await document.fonts.ready;
  const b64 = async (blob) => { const a = new Uint8Array(await blob.arrayBuffer()); let s = ''; for (let i = 0; i < a.length; i += 32768) s += String.fromCharCode.apply(null, a.subarray(i, i + 32768)); return btoa(s); };
  const out = {caption: caption(), files: []};
  if (SERIES[p.series].carousel) {
    for (let i = 0; i < slideCount(); i++)
      out.files.push({kind: 'carrousel', n: i + 1, data: await b64(await svgToPNG(buildSlide(i, true, 'post'), 1080, 1350))});
  } else {
    for (const f of ['post', 'story'])
      out.files.push({kind: f, data: await b64(await svgToPNG(buildPost(f, true), 1080, f === 'story' ? 1920 : 1350))});
  }
  return out;
}
"""


async def main(plan_path):
    plan = json.loads(pathlib.Path(plan_path).read_text(encoding="utf-8"))
    week = plan["week"]
    out_dir = ROOT / "images" / week
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest, errors = [], []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page()
        await page.goto((ROOT / "atelier.html").as_uri())
        await page.wait_for_function("typeof loadSeries === 'function'")
        for post in plan["posts"]:
            slug = post["slug"]
            try:
                p = dict(post)
                if p.get("items"):
                    p["items"] = [{**it, "cover": data_url(it.get("cover"))} for it in p["items"]]
                else:
                    p["cover"] = data_url(p.get("cover"))
                res = await page.evaluate(JS_FILL, p)
                files = []
                for f in res["files"]:
                    name = f"{slug}-{f['kind']}" + (f"-{f['n']:02d}" if f["kind"] == "carrousel" else "") + ".png"
                    (out_dir / name).write_bytes(base64.b64decode(f["data"]))
                    files.append(f"images/{week}/{name}")
                manifest.append({"slug": slug, "series": post["series"], "caption": res["caption"], "files": files})
            except Exception as e:  # un post raté ne bloque pas les autres
                errors.append({"slug": slug, "error": str(e)[:300]})
        await browser.close()
    (out_dir / "manifest.json").write_text(json.dumps({"week": week, "posts": manifest, "errors": errors}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": len(manifest), "errors": errors}, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))
