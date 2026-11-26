# Site de tutoriais do ForgedInAshes

App Vite + React + three.js. Todas as páginas de item, máquina e linha são montadas a partir de
`public/data/mod.json`, gerado dos arquivos do mod; só os guias de conceito (`src/guides.js`) são escritos à mão.

## Atualizar

```
fe.bat site
```

Exporta em GLB os modelos HD alterados (`tools/blender_export_glb.py` → `public/models`), regenera os dados e os
ícones (`tools/gen_site.py` → `public/data`, `public/icons`) e compila (`npm run build` → `dist`).

## Rodar local

```
cd site
npm install
npm run dev
```

## Deploy (Vercel)

Raiz do projeto: `site`. Build `npm run build`, saída `dist` (já em `vercel.json`, com o rewrite da SPA).

## Escrever um guia

Em `src/guides.js`, adicione `{ id, title, sub, icon, blocks }`. Cada bloco é `{ h }` (título), `{ p }`
(parágrafo) ou `{ note }` (destaque). No texto, `[[feSteamTurbine]]` vira um chip com ícone e link para a página do
item, e `[[id|n]]` um chip com quantidade.

## Regras

Só ícones e modelos do próprio mod. Nenhum arquivo do jogo vai para `public/`.
