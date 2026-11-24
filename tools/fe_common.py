"""Shared helpers for the Ferro & Engrenagem tools.

- Locates the game install (tools/game_path.txt).
- Loads vanilla Data/Config XML files.
- Applies the mod's XPath patch files in memory (simulation only; the game
  itself is never modified).

Patch operation names were confirmed in Assembly-CSharp.dll of game 3.4.0 (B10):
set, setattribute, append, prepend, insertAfter, insertBefore, remove,
removeattribute, csv, conditional. The exact semantics below follow common
7DTD modding usage; csv and conditional are only checked, not simulated.
"""
from __future__ import annotations

import copy
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    from lxml import etree
except ImportError:  # pragma: no cover
    sys.exit("lxml is missing: python -m pip install lxml")

REPO = Path(__file__).resolve().parent.parent
MOD_DIR = REPO / "Mods" / "FerroEngrenagem"
MOD_CONFIG = MOD_DIR / "Config"

PATCH_OPS = {
    "set", "setattribute", "append", "prepend", "insertAfter", "insertBefore",
    "remove", "removeattribute", "csv", "conditional",
}
# Ops whose xpath must match at least one node.
MUST_MATCH = PATCH_OPS - {"conditional"}

# Mod Config subfolder -> vanilla Data/Config subfolder.
# Checked in game (2026-11-24 log): the game patches "XUi_InGame/windows" etc., so mods must use
# Config/XUi_InGame/ (a Config/XUi/ folder is silently ignored).
SUBDIR_MAP = {"XUi": "XUi_InGame", "XUi_InGame": "XUi_InGame",
              "XUi_Menu": "XUi_Menu", "XUi_Common": "XUi_Common"}

_PARSER = etree.XMLParser(remove_blank_text=False)


def game_dir() -> Path:
    f = REPO / "tools" / "game_path.txt"
    if not f.exists():
        sys.exit(f"Missing {f}: put the game install path in it.")
    p = Path(f.read_text(encoding="utf-8").strip())
    if not (p / "Data" / "Config").is_dir():
        sys.exit(f"Data/Config not found under {p}")
    return p


def vanilla_config() -> Path:
    return game_dir() / "Data" / "Config"


def load_vanilla(rel: str) -> etree._ElementTree:
    return etree.parse(str(vanilla_config() / rel), _PARSER)


def mod_patch_files() -> list[tuple[Path, str]]:
    """(patch file, vanilla relative path) for every XML in the mod Config."""
    out = []
    if not MOD_CONFIG.is_dir():
        return out
    for f in sorted(MOD_CONFIG.rglob("*.xml")):
        rel = f.relative_to(MOD_CONFIG)
        parts = list(rel.parts)
        if len(parts) > 1:
            parts[0] = SUBDIR_MAP.get(parts[0], parts[0])
        out.append((f, "/".join(parts)))
    return out


@dataclass
class PatchResult:
    file: Path
    line: int
    op: str
    xpath: str
    matches: int
    problem: str = ""


@dataclass
class PatchRun:
    results: list[PatchResult] = field(default_factory=list)

    @property
    def problems(self) -> list[PatchResult]:
        return [r for r in self.results if r.problem]


def _select(tree, xpath):
    res = tree.xpath(xpath)
    if not isinstance(res, list):  # boolean/number/string xpath
        return [], f"xpath does not select nodes (returned {type(res).__name__})"
    return res, ""


def _children(cmd):
    return [copy.deepcopy(c) for c in cmd if isinstance(c.tag, str)]


def apply_patch_file(tree, patch_path: Path, run: PatchRun, apply: bool = True):
    ptree = etree.parse(str(patch_path), _PARSER)
    for cmd in ptree.getroot():
        if not isinstance(cmd.tag, str):
            continue  # comment / PI
        _apply_cmd(tree, cmd, patch_path, run, apply)


def _apply_cmd(tree, cmd, patch_path, run, apply):
    op = cmd.tag
    xpath = cmd.get("xpath")
    line = cmd.sourceline or 0
    if op not in PATCH_OPS:
        run.results.append(PatchResult(patch_path, line, op, xpath or "", 0,
                                       f"unknown patch op <{op}>"))
        return
    if op == "conditional":
        # Not simulated: just check the xpaths inside its branches.
        for branch in cmd.iter():
            if branch is not cmd and isinstance(branch.tag, str) and branch.get("xpath"):
                _apply_cmd(tree, branch, patch_path, run, apply=False)
        run.results.append(PatchResult(patch_path, line, op, "", 0, ""))
        return
    if not xpath:
        run.results.append(PatchResult(patch_path, line, op, "", 0, "missing xpath"))
        return
    try:
        nodes, err = _select(tree, xpath)
    except etree.XPathError as e:
        run.results.append(PatchResult(patch_path, line, op, xpath, 0, f"invalid xpath: {e}"))
        return
    res = PatchResult(patch_path, line, op, xpath, len(nodes), err)
    if not err and op in MUST_MATCH and not nodes:
        res.problem = "xpath matches 0 nodes"
    # Node-type rules enforced by the game (XmlPatchMethods, seen in the 3.4.0 log): a violating command throws and
    # the REST OF THE FILE is not applied.
    if not res.problem and nodes:
        attrs = [n for n in nodes if getattr(n, "is_attribute", False)]
        if op == "removeattribute" and len(attrs) != len(nodes):
            res.problem = "removeattribute must select attributes (.../@name); game: 'Can only remove Attributes'"
        elif op in ("setattribute", "append", "prepend", "insertAfter", "insertBefore") and attrs:
            res.problem = f"{op} must select elements, not attributes"
    run.results.append(res)
    if res.problem or not apply or op == "csv":
        return

    for n in nodes:
        is_attr = getattr(n, "is_attribute", False)
        if op == "set":
            if is_attr:
                n.getparent().set(n.attrname, cmd.text or "")
            else:
                n.text = cmd.text or ""
        elif op == "setattribute":
            n.set(cmd.get("name"), cmd.text or "")
        elif op == "removeattribute":  # the xpath selects the attribute itself (game semantics)
            n.getparent().attrib.pop(n.attrname, None)
        elif op == "remove":
            if is_attr:
                n.getparent().attrib.pop(n.attrname, None)
            elif n.getparent() is not None:
                n.getparent().remove(n)
        elif op == "append":
            for c in _children(cmd):
                n.append(c)
        elif op == "prepend":
            for i, c in enumerate(_children(cmd)):
                n.insert(i, c)
        elif op == "insertAfter":
            parent, idx = n.getparent(), n.getparent().index(n)
            for i, c in enumerate(_children(cmd)):
                parent.insert(idx + 1 + i, c)
        elif op == "insertBefore":
            parent, idx = n.getparent(), n.getparent().index(n)
            for i, c in enumerate(_children(cmd)):
                parent.insert(idx + i, c)


def patched(rel: str, run: PatchRun | None = None):
    """Vanilla tree for `rel` with all matching mod patch files applied."""
    run = run or PatchRun()
    tree = load_vanilla(rel)
    for f, target in mod_patch_files():
        if target == rel:
            apply_patch_file(tree, f, run)
    return tree, run
