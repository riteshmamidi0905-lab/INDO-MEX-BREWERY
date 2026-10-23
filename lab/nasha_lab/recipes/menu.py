"""Versioned menu definitions (D-90). A definition says which dishes are on the concept menu, which simulator slot sells each, and the synthetic popularity weights.
`historical` (menu-def-v1-d84-historical) reproduces every simulation made before D-90 byte for byte; `current` (menu-def-v2-2026-10-23) is used for future scenarios and contains no Goat Birria.
Both files are read-only records: a new menu state is a new file, never an edit."""
import json

from . import model

MENU_DIR = model.ROOT / "food/menu"
FILES = {"historical": "menu-definition.v1-d84-historical.json", "current": "menu-definition.v2-2026-10-23.json"}
DEFAULT = "historical"          # byte-stable default for the frozen simulation; new scenarios ask for "current" explicitly
RETIRED = ("goat-birria",)


def load(name=DEFAULT):
    d = json.loads((MENU_DIR / FILES[name]).read_text())
    for it in d["items"]:
        assert it["menu_item_id"] not in RETIRED, f"retired dish {it['menu_item_id']} in {d['menu_id']}"
    return d


def slot_to_recipe(name=DEFAULT):
    return {i["sim_item_id"]: i["menu_item_id"] for i in load(name)["items"]}


def sim_slots(name=DEFAULT):
    return tuple(slot_to_recipe(name))


def detect(item_ids):
    """Which definition a generated warehouse was built for, from the item ids it actually contains."""
    ids = set(item_ids)
    for name in ("current",):
        if set(sim_slots(name)) <= ids:
            return name
    return "historical"
