"""Report vanilla recipes by craft_area, before and after the mod's patches.

Writes tools/out/recipes.csv and prints a summary per craft_area.
An empty craft_area means the recipe is crafted in the player's inventory.

Usage: python tools/recipe_report.py [--changed]
  --changed   print every recipe whose craft_area the mod changes
"""
import collections
import csv
import sys

import fe_common as fe

INV = "(inventory)"


def recipe_rows(tree):
    rows = []
    for i, r in enumerate(tree.getroot().iter("recipe")):
        ingr = ";".join(f"{g.get('name')}x{g.get('count', '1')}" for g in r.iter("ingredient"))
        rows.append({
            "idx": i,
            "name": r.get("name", ""),
            "count": r.get("count", "1"),
            "craft_area": r.get("craft_area", "") or INV,
            "craft_tool": r.get("craft_tool", ""),
            "craft_time": r.get("craft_time", ""),
            "tags": r.get("tags", ""),
            "ingredients": ingr,
        })
    return rows


def main() -> int:
    vanilla = recipe_rows(fe.load_vanilla("recipes.xml"))
    tree, run = fe.patched("recipes.xml")
    modded = recipe_rows(tree)
    for p in run.problems:
        print(f"[WARN] patch problem {p.file.name}:{p.line} {p.xpath} -> {p.problem}")

    # Match vanilla to modded by (name, occurrence #), since names can repeat.
    def keyed(rows):
        seen, out = collections.Counter(), {}
        for r in rows:
            k = (r["name"], seen[r["name"]])
            seen[r["name"]] += 1
            out[k] = r
        return out

    v, m = keyed(vanilla), keyed(modded)
    out_dir = fe.REPO / "tools" / "out"
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / "recipes.csv"
    with out_file.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["name", "count", "craft_area_vanilla", "craft_area_mod", "status",
                    "craft_tool", "craft_time", "tags", "ingredients"])
        for k in sorted(set(v) | set(m), key=lambda k: (k[0].lower(), k[1])):
            a, b = v.get(k), m.get(k)
            r = b or a
            status = ("new" if not a else "removed" if not b
                      else "moved" if a["craft_area"] != b["craft_area"] else "")
            w.writerow([r["name"], r["count"], a["craft_area"] if a else "",
                        b["craft_area"] if b else "", status, r["craft_tool"],
                        r["craft_time"], r["tags"], r["ingredients"]])

    cv = collections.Counter(r["craft_area"] for r in vanilla)
    cm = collections.Counter(r["craft_area"] for r in modded)
    print(f"{'craft_area':<24}{'vanilla':>9}{'mod':>9}")
    for area in sorted(set(cv) | set(cm), key=lambda a: -cv.get(a, 0)):
        print(f"{area:<24}{cv.get(area, 0):>9}{cm.get(area, 0):>9}")
    print(f"{'TOTAL':<24}{len(vanilla):>9}{len(modded):>9}")
    print(f"\nCSV: {out_file}")

    if "--changed" in sys.argv:
        for k in sorted(set(v) & set(m)):
            if v[k]["craft_area"] != m[k]["craft_area"]:
                print(f"  {k[0]}: {v[k]['craft_area']} -> {m[k]['craft_area']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
