# Crommix AI demo site: deploying on Dokploy

The site is static: a hub page (`/`) that lists the models, and one page per
model (`/lid/`, later `/asr/`, `/tts/` …). The models run in the visitor's
browser, so the server only serves files: an nginx container of about 10 MB.

```
site/                    source pages (edit these)
  index.html             hub; cards come from models.json
  models.json            model registry: add or flip "status" here
  assets/                shared styles (base.css), FR/EN switcher (i18n.js), hub.js
  lid/                   the language-ID demo (index.html, app.js, lid.css)
deploy/nginx.conf        gzip, caching, security headers (CSP)
Dockerfile               builds the JS runtimes, then serves site/ with nginx
```

In the container, each model's runtime lives at `/vendor/<module>/{dist,model}`.

## Preview locally

```powershell
cd js; npm install; cd ..                      # once: compiles the JS runtime
python deploy/build_site.py                     # assembles site-dist/
python -m http.server 8080 -d site-dist         # open http://localhost:8080/lid/
```

With Docker: `docker build -t crommix-ai . ; docker run -p 8080:80 crommix-ai`.

## First deployment on Dokploy

1. **DNS.** Add an `A` record `ai.crommixmali.com` pointing at your Dokploy
   server's IP (or a `CNAME` to its hostname).
2. **Git.** Push this repo to GitHub/GitLab/Gitea (a private repo is fine).
   `js/model/cmx-lid.json` (2 MB) must be committed. The Dockerfile doesn't
   need `data/` or `models/`.
3. **In Dokploy:** create a Project, then *Create Service → Application*.
   - *Provider*: your Git provider (or "Git" with the repo URL), branch `main`.
   - *Build type*: **Dockerfile**, path `Dockerfile`, context `.`.
   - *Domains*: add `ai.crommixmali.com`, **container port 80**, path `/`,
     HTTPS on with Let's Encrypt.
   - Deploy.
4. Check `https://ai.crommixmali.com/healthz` (it should return `ok`), then
   open `/lid/`.
5. Optional: turn on *Auto Deploy* (the Git webhook), so every push to `main`
   redeploys.

The page HTML is served with `no-cache`, so a redeploy shows up immediately.
JS, CSS and models are cached for a day.

## Updating the language-ID model

```powershell
python -m cmx_lid.build        # retrains, benchmarks, re-exports js/model/cmx-lid.json
cd js; npm test; cd ..         # confirms the JS port still matches Python
git commit -am "cmx-lid: retrain"; git push   # Dokploy redeploys
```

If the metrics changed, also update the numbers in `site/lid/index.html`
(the "Qualité mesurée" card, `data-pct` / `data-dec` attributes).

## Adding a new model (e.g. cmx-asr)

1. **Runtime:** build its browser runtime so it exposes a small JS API (like
   `load()` in `js/`) plus its model file(s).
2. **Ship it:** in the `Dockerfile`, add two `COPY` lines to
   `/usr/share/nginx/html/vendor/cmx-asr/dist` and `/vendor/cmx-asr/model`.
   Add the same module to `MODULES` in `deploy/build_site.py` for local
   previews.
3. **Page:** copy `site/lid/` to `site/asr/` and keep the header, footer and
   the `initI18n({ fr: {...}, en: {...} })` pattern. Shared styles come from
   `/assets/base.css`.
4. **Registry:** in `site/models.json`, set that entry to
   `"status": "live", "path": "/asr/"`. The hub card becomes a link
   automatically.
5. **Content Security Policy:** it allows only same-origin files, `blob:`
   workers and the microphone for this site. Models that use WebAssembly
   (ONNX Runtime Web, whisper.cpp) need `'wasm-unsafe-eval'` added to
   `script-src` in `deploy/nginx.conf`. Anything loaded from another domain
   must be added explicitly, but it's simpler to self-host it under
   `/vendor/`.
6. **Big models (> 50 MB):** keep them out of Git. Download them in a
   Dockerfile step or from object storage, and consider Git LFS. nginx
   already caches `.onnx`, `.bin` and `.wasm`.
