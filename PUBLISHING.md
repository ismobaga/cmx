# Releasing cmx-lid

Three outputs come from the same trained model:

| Output | Name | Built from |
|---|---|---|
| Python package | [`cmx-lid`](https://pypi.org/project/cmx-lid/) on PyPI | `cmx_lid/` (model in `cmx_lid/resources/`) |
| JS/TS package | [`@crommix/lid`](https://www.npmjs.com/package/@crommix/lid) on npm | `js/` (model in `js/model/`) |
| Demo site | ai.crommixmali.com | `site/` + `js/`, Docker on Dokploy |

Licensing: the code is Apache-2.0, and the model and lexicon files are
CC BY-SA 4.0 (see `NOTICE`).

## 0. Before every release

```powershell
python -m cmx_lid.build                               # retrain, benchmark, sync cmx_lid/resources + js/model
python -m unittest discover -s tests -t .             # includes the "packaged model is current" guard
cd js; npm test; cd ..                                # JS == Python on every fixture
```

Bump the version in **three** places, all to the same value: `pyproject.toml`,
`cmx_lid/__init__.py` (`__version__`) and `js/package.json`. Then update the
metrics in `site/lid/index.html` and `README.pypi.md` if they changed.

## 1. PyPI (`pip install cmx-lid`)

One-time setup: create an account on pypi.org (and test.pypi.org), then an
API token under *Account settings → API tokens*.

```powershell
pip install build twine
Remove-Item -Recurse -Force dist -ErrorAction SilentlyContinue
python -m build
python -m twine check dist/*
python -m twine upload --repository testpypi dist/*    # optional rehearsal
python -m twine upload dist/*                          # username: __token__, password: pypi-…
```

Check it: `pip install cmx-lid` in a fresh venv, then `cmx-lid "n taara l'hôpital kunun"`.

## 2. npm (`npm install @crommix/lid`)

One-time setup: create an npm account, then a **free organization named
`crommix`** at npmjs.com → *Add organization* (this reserves the `@crommix/`
scope for future models). Then run `npm login`.

```powershell
cd js
npm install
npm publish          # runs the tests first (prepublishOnly); publishConfig makes the scoped package public
cd ..
```

Check it: `npm view @crommix/lid`.

## 3. Demo site on Dokploy (ai.crommixmali.com)

1. Push the repo:
   `git remote add origin <your repo URL>; git push -u origin main`.
2. DNS: add an `A` record `ai` → your Dokploy server IP.
3. In Dokploy: *Project → Create Service → Application*.
   - **Source:** your Git provider (or "Git" + repo URL), branch `main`.
   - **Build Type:** `Dockerfile`, Docker File `Dockerfile`, Build Path `/`.
   - **Domains → Add domain:** host `ai.crommixmali.com`, path `/`,
     **container port 80**, HTTPS on, certificate *Let's Encrypt*.
   - Click **Deploy**, then watch *Deployments → logs*. The build takes about
     1 minute: `tsc`, then copying into nginx.
4. Check: `https://ai.crommixmali.com/healthz` → `ok`, then `/lid/`.
5. Optional: *Auto Deploy* on, so every push to `main` redeploys.

Troubleshooting:
- **404 or Bad Gateway:** the domain's container port must be **80**.
- **Old page after a deploy:** HTML is `no-cache`, so hard-refresh. JS and
  models are cached for 1 day.
- **Model not loading:** open `/vendor/cmx-lid/model/cmx-lid.json`; it
  should download (about 410 KB gzipped).

## Tag the release

```powershell
git tag v0.5.0; git push --tags
```
