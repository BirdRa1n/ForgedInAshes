# AGENTS.md — `site/` (tutorial website)

Read the [root AGENTS.md](../AGENTS.md) first.

Vite 6 + React 19 + react-router 7 + three / @react-three/fiber / drei. Deployed on Vercel with the project root
set to `site` (`vercel.json`: build `npm run build`, output `dist`, SPA rewrite).

## Data-driven by design

- **Do not write one page per item.** Every item, machine and production line page is rendered from
  `public/data/mod.json`, produced by `python tools/gen_site.py` from the mod's XML and data.
- `src/data.js` → `plan(db, id, qty)` builds the production tree, ordered steps, machines and raw materials for any
  item. Fix tutorial logic there, once, for every page.
- Only the concept guides in `src/guides.js` are hand-written (Portuguese UI). `[[id]]` renders an item chip,
  `[[id|n]]` a chip with a quantity. Every referenced id must exist in the data.
- 3D models are GLB files in `public/models` (from `tools/blender_export_glb.py`), loaded lazily by
  `src/Model3D.jsx`. Avoid drei `<Html>` inside the canvas (it broke route changes with `removeChild` errors).

## Commands

```powershell
npm install
npm run dev     # http://localhost:5173
npm run build   # must pass before committing
```

`fe.bat site` does GLB export + data + build in one step. `node_modules/` and `dist/` are git-ignored.

## Rules

- Only the mod's own icons and models in `public/` — never game assets.
- Keep the dark industrial theme (`src/styles.css`: brass `#e8a33d`, fluid `#4cc3d9`, surface `#15181d`).
- Check pages in a browser (home, an item page, a line page, guides, indicators, Ctrl+K palette) after UI changes.
