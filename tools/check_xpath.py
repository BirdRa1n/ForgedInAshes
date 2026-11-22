"""Check every XPath in the mod's patch files against vanilla Data/Config.

Patches are applied in order (in memory), so a later xpath can target nodes
added by an earlier <append>. Exit code 1 if any problem is found.

Usage: python tools/check_xpath.py [-v]
"""
import sys

from lxml import etree

import fe_common as fe


def main() -> int:
    verbose = "-v" in sys.argv
    files = fe.mod_patch_files()
    if not files:
        print("No patch files in", fe.MOD_CONFIG)
        return 0
    trees = {}
    run = fe.PatchRun()
    for f, rel in files:
        rel_name = f.relative_to(fe.MOD_CONFIG)
        if not (fe.vanilla_config() / rel).exists():
            print(f"[SKIP] {rel_name}: no vanilla file '{rel}' (not a patch target?)")
            continue
        try:
            if rel not in trees:
                trees[rel] = fe.load_vanilla(rel)
            fe.apply_patch_file(trees[rel], f, run)
        except etree.XMLSyntaxError as e:
            print(f"[ERR ] {rel_name}: XML syntax error: {e}")
            run.results.append(fe.PatchResult(f, 0, "-", "-", 0, "syntax error"))

    for r in run.results:
        name = r.file.relative_to(fe.MOD_CONFIG)
        if r.problem:
            print(f"[FAIL] {name}:{r.line} <{r.op}> {r.xpath} -> {r.problem}")
        elif verbose:
            print(f"[ OK ] {name}:{r.line} <{r.op}> {r.xpath} -> {r.matches} node(s)")
    n_bad = len(run.problems)
    print(f"\n{len(run.results)} command(s) checked, {n_bad} problem(s).")
    return 1 if n_bad else 0


if __name__ == "__main__":
    sys.exit(main())
