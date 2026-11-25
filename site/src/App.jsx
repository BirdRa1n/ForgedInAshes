import { useEffect, useMemo, useRef, useState } from "react";
import { BrowserRouter, Routes, Route, NavLink, Link, useNavigate, useLocation } from "react-router-dom";
import { DataCtx, useLoadData, useData } from "./data";
import { Icon, Loading } from "./components";
import { Home, Catalog, ItemPage, Lines, LinePage, Guides, GuidePage, Stats } from "./pages";
import { GUIDES } from "./guides";

function Palette({ onClose }) {
  const db = useData();
  const nav = useNavigate();
  const [q, setQ] = useState("");
  const [sel, setSel] = useState(0);
  const ref = useRef(null);
  useEffect(() => ref.current && ref.current.focus(), []);
  const res = useMemo(() => {
    const qq = q.trim().toLowerCase();
    const items = db.list
      .filter((it) => it.mod || (db.routes[it.id] || []).length)
      .filter((it) => !qq || it.name.toLowerCase().includes(qq) || it.id.toLowerCase().includes(qq))
      .sort((a, b) => {
        const sa = a.name.toLowerCase().startsWith(qq) ? 0 : 1, sb = b.name.toLowerCase().startsWith(qq) ? 0 : 1;
        return sa - sb || (b.mod ? 1 : 0) - (a.mod ? 1 : 0) || a.name.localeCompare(b.name, "pt");
      })
      .slice(0, 40)
      .map((it) => ({ to: `/item/${it.id}`, id: it.id, label: it.name, c: it.mod ? it.cat : "item do jogo" }));
    const guides = GUIDES.filter((g) => !qq || g.title.toLowerCase().includes(qq)).map((g) => ({ to: `/guias/${g.id}`, id: g.icon, label: g.title, c: "guia" }));
    return [...guides.slice(0, qq ? 3 : 2), ...items];
  }, [db, q]);
  const go = (r) => { nav(r.to); onClose(); };
  return (
    <div className="palette-bg" onMouseDown={onClose}>
      <div className="palette" onMouseDown={(e) => e.stopPropagation()}>
        <input ref={ref} className="input" placeholder="Buscar máquinas, peças, guias…" value={q}
               onChange={(e) => { setQ(e.target.value); setSel(0); }}
               onKeyDown={(e) => {
                 if (e.key === "ArrowDown") { e.preventDefault(); setSel((s) => Math.min(res.length - 1, s + 1)); }
                 if (e.key === "ArrowUp") { e.preventDefault(); setSel((s) => Math.max(0, s - 1)); }
                 if (e.key === "Enter" && res[sel]) go(res[sel]);
                 if (e.key === "Escape") onClose();
               }} />
        <div className="res">
          {res.map((r, k) => (
            <div key={r.to} className={"row" + (k === sel ? " sel" : "")} onMouseEnter={() => setSel(k)} onClick={() => go(r)}>
              <Icon id={r.id} size={30} /> <span>{r.label}</span> <span className="c">{r.c}</span>
            </div>
          ))}
          {!res.length && <div className="row muted">Nada encontrado.</div>}
        </div>
      </div>
    </div>
  );
}

function Shell({ children }) {
  const [open, setOpen] = useState(false);
  const loc = useLocation();
  useEffect(() => {
    const h = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setOpen(true); }
      if (e.key === "/" && document.activeElement.tagName !== "INPUT") { e.preventDefault(); setOpen(true); }
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, []);
  useEffect(() => setOpen(false), [loc.pathname]);
  return (
    <div className="app">
      <header className="top">
        <Link className="brand" to="/"><img src="/icons/feGearbox.png" alt="" /> Ferro <b>&amp;</b> Engrenagem</Link>
        <nav className="nav">
          <NavLink to="/linhas">Linhas</NavLink>
          <NavLink to="/maquinas">Máquinas</NavLink>
          <NavLink to="/catalogo">Catálogo</NavLink>
          <NavLink to="/guias">Guias</NavLink>
          <NavLink to="/indicadores">Indicadores</NavLink>
        </nav>
        <button className="searchbtn" onClick={() => setOpen(true)}>🔍 Buscar <span className="kbd">Ctrl K</span></button>
      </header>
      <main>{children}</main>
      <footer>Ferro &amp; Engrenagem · mod para 7 Days to Die · páginas geradas dos arquivos do mod · valores sujeitos a balanceamento</footer>
      {open && <Palette onClose={() => setOpen(false)} />}
    </div>
  );
}

export default function App() {
  const { db, err } = useLoadData();
  if (err) return <div className="center">Não deu para carregar os dados: {err}</div>;
  if (!db) return <Loading />;
  return (
    <DataCtx.Provider value={db}>
      <BrowserRouter>
        <Shell>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/catalogo" element={<Catalog />} />
            <Route path="/maquinas" element={<Catalog machinesOnly />} />
            <Route path="/item/:id" element={<ItemPage />} />
            <Route path="/linhas" element={<Lines />} />
            <Route path="/linha/:id" element={<LinePage />} />
            <Route path="/guias" element={<Guides />} />
            <Route path="/guias/:id" element={<GuidePage />} />
            <Route path="/indicadores" element={<Stats />} />
            <Route path="*" element={<p>Página não encontrada. <Link to="/">Início</Link></p>} />
          </Routes>
        </Shell>
      </BrowserRouter>
    </DataCtx.Provider>
  );
}
