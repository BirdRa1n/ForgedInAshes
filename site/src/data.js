// Everything the site shows comes from /data/mod.json (tools/gen_site.py). This module indexes it and builds the
// production plans: any item becomes a full tutorial (tree, step list, machines, raw materials) with no page written
// by hand.
import { createContext, useContext, useEffect, useState } from "react";

export const DataCtx = createContext(null);
export const useData = () => useContext(DataCtx);

// stations the mod hides (their recipes moved to the mod's machines)
const HIDDEN = new Set(["forge", "workbench", "chemistryStation", "cementMixer"]);

export function useLoadData() {
  const [db, setDb] = useState(null);
  const [err, setErr] = useState(null);
  useEffect(() => {
    fetch("/data/mod.json")
      .then((r) => r.json())
      .then((d) => setDb(index(d)))
      .catch((e) => setErr(String(e)));
  }, []);
  return { db, err };
}

function index(d) {
  const routes = {}; // item -> [route]
  const fluidRoutes = {}; // fluid -> [route]
  const usedIn = {}; // item -> Set(product)
  const byMachine = {}; // machine -> [route]
  const add = (m, k, v) => (m[k] = m[k] || []).push(v);
  for (const r of d.recipes) {
    const route = { type: "recipe", machine: r.area || "", out: [r.out, r.n], ing: r.ing, fin: [], fout: [], t: r.t, data: r };
    if (HIDDEN.has(r.area)) route.hidden = true;
    add(routes, r.out, route);
    if (r.area) add(byMachine, r.area, route);
    for (const [i] of r.ing) (usedIn[i] = usedIn[i] || new Set()).add(r.out);
  }
  for (const p of d.processes) {
    const route = { type: "process", machine: p.machine, out: p.out, ing: p.in, fin: p.fin, fout: p.fout, t: p.t, data: p };
    if (p.out) add(routes, p.out[0], route);
    if (p.extra) add(routes, p.extra[0], { ...route, out: [p.extra[0], p.extra[1]], byproduct: true });
    for (const [f] of p.fout) add(fluidRoutes, f, route);
    add(byMachine, p.machine, route);
    const product = p.out ? p.out[0] : p.fout[0] ? p.fout[0][0] : null;
    for (const [i] of p.in) if (product) (usedIn[i] = usedIn[i] || new Set()).add(product);
    if (p.mold && product) (usedIn[p.mold] = usedIn[p.mold] || new Set()).add(product);
  }
  // bottled fluids (Bottler) and the Item Drain: items <-> fluids
  const list = Object.entries(d.items).map(([id, it]) => ({ id, ...it }));
  return { ...d, routes, fluidRoutes, usedIn, byMachine, list };
}

export const itemName = (db, id) => (db.items[id] ? db.items[id].name : db.fluids[id] ? db.fluids[id].name : id);
export const machineName = (db, m) => (m === "" ? "Inventário" : db.items[m] ? db.items[m].name : db.areas[m] || m);
export const fluidName = (db, f) => (db.fluids[f] ? db.fluids[f].name : f);

/** Routes that make id, best first: the mod's chain processes, the mod's machines, then the inventory / campfire. */
export function bestRoutes(db, id) {
  const rs = (db.routes[id] || []).filter((r) => !r.hidden);
  const score = (r) =>
    (r.byproduct ? 3 : 0) + (r.type === "process" ? 0 : r.machine.startsWith("fe") ? 1 : 2) + (r.data.planned ? 5 : 0);
  return [...rs].sort((a, b) => score(a) - score(b));
}

/** A full production plan for qty of id: tree + ordered steps + machines + raw materials. */
export function plan(db, id, qty = 1, choice = {}) {
  const steps = new Map(); // key -> {route, crafts}
  const raw = new Map(); // id -> qty
  const rawFluids = new Map();
  const machines = new Set();
  const order = [];

  function walkFluid(f, litres, stack, depth) {
    const rs = (db.fluidRoutes[f] || []).filter((r) => !stack.has(r.data.id));
    if (!rs.length || depth > 9 || f === "water") {
      rawFluids.set(f, (rawFluids.get(f) || 0) + litres);
      return { id: f, fluid: true, qty: litres, raw: true, children: [] };
    }
    const r = rs[0];
    const per = r.fout.find((x) => x[0] === f)[1] || 1;
    const crafts = Math.ceil(litres / per);
    return node(f, litres, r, crafts, stack, depth, true);
  }

  function node(id0, qty0, r, crafts, stack, depth, fluid) {
    const key = r.type + ":" + (r.data.id || r.out[0] + "@" + r.machine);
    const s2 = new Set(stack);
    s2.add(r.data.id || key);
    s2.add(id0);
    const children = [];
    for (const [i, n] of r.ing) children.push(walk(i, n * crafts, s2, depth + 1));
    for (const [f, l] of r.fin) children.push(walkFluid(f, l * crafts, s2, depth + 1));
    if (r.data.mold) children.push({ id: r.data.mold, qty: 1, tool: true, children: [], raw: false });
    const prev = steps.get(key);
    if (prev) prev.crafts += crafts;
    else {
      steps.set(key, { route: r, crafts });
      order.push(key);
    }
    machines.add(r.machine);
    return { id: id0, fluid, qty: qty0, route: r, crafts, children };
  }

  function walk(i, n, stack, depth) {
    const rs = bestRoutes(db, i).filter((r) => !stack.has(r.data.id || r.out[0] + "@" + r.machine) && !r.ing.some(([x]) => stack.has(x)));
    if (!rs.length || depth > 9) {
      raw.set(i, (raw.get(i) || 0) + n);
      return { id: i, qty: n, raw: true, children: [] };
    }
    const r = rs[Math.min(choice[i] || 0, rs.length - 1)];
    const per = r.out ? r.out[1] : 1;
    return node(i, n, r, Math.ceil(n / per), stack, depth, false);
  }

  const tree = walk(id, qty, new Set(), 0);
  // steps in the order they must happen: deepest first (post-order of the tree)
  const post = [];
  const seen = new Set();
  (function po(t) {
    for (const c of t.children) po(c);
    if (t.route) {
      const key = t.route.type + ":" + (t.route.data.id || t.route.out[0] + "@" + t.route.machine);
      if (!seen.has(key)) {
        seen.add(key);
        post.push({ key, ...steps.get(key) });
      }
    }
  })(tree);
  return { tree, steps: post, machines: [...machines], raw: [...raw.entries()], rawFluids: [...rawFluids.entries()] };
}

export const KIND_VERB = {
  melt: "Derreta", cast: "Molde", press: "Prense", turn: "Torneie", crush: "Triture", wash: "Lave", mix: "Misture",
  dry: "Seque / aqueça", distill: "Destile", spin: "Fie / centrifugue", assemble: "Encaixe", sequence: "Feche",
  boil: "Cozinhe / ferva", grow: "Cultive",
};

export function fmtQty(n) {
  if (n >= 1000) return (n / 1000).toFixed(n % 1000 ? 1 : 0).replace(".", ",") + " mil";
  return String(Math.round(n * 10) / 10).replace(".", ",");
}
