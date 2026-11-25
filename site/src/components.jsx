import { Link } from "react-router-dom";
import { useData, itemName, fluidName, fmtQty } from "./data";

export function Icon({ id, size = 36 }) {
  const db = useData();
  const it = db.items[id];
  if (db.fluids[id] && !it) {
    const cl = db.fluids[id].class;
    return <span className={"ico fluidico " + (cl === "molten" ? "molten" : cl === "gas" ? "gas" : "")} style={{ width: size, height: size }} title={fluidName(db, id)} />;
  }
  if (it && it.icon)
    return (
      <span className="ico" style={{ width: size, height: size }}>
        <img src={`/icons/${id}.png`} alt="" loading="lazy" />
      </span>
    );
  const name = itemName(db, id);
  const letters = name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join("").toUpperCase();
  return (
    <span className="ico letter" style={{ width: size, height: size, fontSize: Math.max(10, size / 3) }} title={name}>
      {letters}
    </span>
  );
}

export function Chip({ id, qty, fluid, size = 26 }) {
  const db = useData();
  const isFluid = fluid || (!!db.fluids[id] && !db.items[id]);
  const body = (
    <>
      <Icon id={id} size={size} />
      {qty != null && <span className="q">{fmtQty(qty)}{isFluid ? " L" : "×"}</span>}
      <span>{isFluid ? fluidName(db, id) : itemName(db, id)}</span>
    </>
  );
  if (isFluid) return <span className="chip fl">{body}</span>;
  return (
    <Link className="chip" to={`/item/${id}`}>
      {body}
    </Link>
  );
}

export function ItemCard({ id }) {
  const db = useData();
  const it = db.items[id];
  return (
    <Link className="icard fade-in" to={`/item/${id}`}>
      <div className="top-row">
        <Icon id={id} size={48} />
        <div>
          <div className="nm">{it.name}</div>
          <div className="cat">{it.cat}</div>
        </div>
      </div>
      {it.desc && <div className="d">{it.desc}</div>}
      <div className="badges">
        {it.model && <span className="pill brass">3D</span>}
        {it.energy.torqueOut ? <span className="pill">⚡ {it.energy.torqueOut} UT</span> : null}
        {it.energy.torqueCost ? <span className="pill">⚙ {it.energy.torqueCost} UT</span> : null}
        {it.energy.watts ? <span className="pill">{it.energy.watts} W</span> : null}
        {db.byMachine[id] ? <span className="pill">{db.byMachine[id].length} receitas</span> : null}
      </div>
    </Link>
  );
}

/** Single-series horizontal bars (one hue, no legend; values in text ink; hover tooltip). */
export function Bars({ rows, unit = "", tip }) {
  const max = Math.max(1, ...rows.map((r) => r[1]));
  return (
    <div className="bars" role="table">
      {rows.map(([label, v, link]) => (
        <div className="bar" key={label} role="row">
          <span className="lab" role="cell">{link ? <Link to={link}>{label}</Link> : label}</span>
          <span className="track"><span className="fill" style={{ width: `${(v / max) * 100}%`, display: "block" }} /></span>
          <span className="val" role="cell">{v}{unit}</span>
          <span className="tip">{tip ? tip(label, v) : `${label}: ${v}${unit}`}</span>
        </div>
      ))}
    </div>
  );
}

export function Stat({ v, l, s }) {
  return (
    <div className="stat fade-in">
      <div className="v">{v}</div>
      <div className="l">{l}</div>
      {s && <div className="s">{s}</div>}
    </div>
  );
}

export function Loading() {
  return (
    <div className="center">
      <div className="spinner" />
    </div>
  );
}
