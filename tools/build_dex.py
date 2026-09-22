"""
Builds docs/pokedex.json from your Cobblemon jar and All The Mons x Mega
Showdown zip (or any other Cobblemon-format data pack/zip you add to SOURCES).

Run this once locally whenever your mods update, then commit the updated
docs/pokedex.json to your GitHub repo. The web app (docs/index.html) reads
that JSON file directly, no server or build step needed.

Usage:
    1. Copy your Cobblemon jar and All The Mons x Mega Showdown zip into this
       tools/ folder (or edit SOURCES below to point at their real paths).
    2. python build_dex.py
    3. Check the printed summary. It tells you how many species and spawn
       entries it found. If a number looks way too low, the format guesses
       below (see NOTES) probably don't match your version, and you should
       paste the script's printed sample entries back so the parsing can be
       fixed.
"""
import json
import re
import zipfile
from pathlib import Path

# ---- point these at your actual files ----
SOURCES = [
    "Cobblemon-neoforge-1.8.1+1.21.1.jar",
    "ATM x MSD [v4.0].zip",
]
OUT = Path(__file__).resolve().parent.parent / "docs" / "pokedex.json"

# Species you've said aren't actually catchable/findable on the server.
# These still get listed (so the dex stays complete) but flagged as
# "no_spawn" so the web app can show that instead of a fake location.
NOT_FINDABLE = {"castform", "oricorio", "celesteela", "ironjugulis", "tinglu", "ironboulder"}


def load_species(z, out):
    for n in z.namelist():
        m = re.match(r"data/([^/]+)/species/(?:.+/)?([^/]+)\.json$", n)
        if not m:
            continue
        try:
            sp = json.loads(z.read(n))
        except ValueError:
            continue
        name = m.group(2)
        dex = sp.get("nationalPokedexNumber") or sp.get("dex") or 0
        types = [t for t in (sp.get("primaryType"), sp.get("secondaryType")) if t]
        out[name] = {
            "id": name,
            "namespace": m.group(1),
            "dex": dex,
            "name": sp.get("name") or name.replace("_", " ").title(),
            "types": types,
            "labels": sp.get("labels", []),
            "spawns": [],
        }


def load_spawns(z, out):
    for n in z.namelist():
        if not re.match(r"data/[^/]+/spawn_pool_world/.+\.json$", n):
            continue
        try:
            entries = json.loads(z.read(n)).get("spawns", [])
        except ValueError:
            continue
        for e in entries:
            if not isinstance(e, dict) or "pokemon" not in e:
                continue
            name = e["pokemon"].split()[0].split(":")[-1].lower()
            if name not in out:
                continue
            cond = e.get("condition", {}) if isinstance(e.get("condition"), dict) else {}
            biomes = cond.get("biomes", [])
            level = e.get("level")
            if isinstance(level, dict):
                lvl = [level.get("min"), level.get("max")]
            elif isinstance(level, list):
                lvl = level
            else:
                lvl = None
            out[name]["spawns"].append({
                "bucket": e.get("bucket", "unknown"),
                "biomes": biomes,
                "level": lvl,
                "context": e.get("context"),
            })


def main():
    species = {}
    sample_species_file = None
    sample_spawn_file = None

    for src in SOURCES:
        path = Path(src)
        if not path.exists():
            print(f"SKIPPED (not found): {src}")
            continue
        with zipfile.ZipFile(path) as z:
            for n in z.namelist():
                if sample_species_file is None and "/species/" in n and n.endswith(".json"):
                    sample_species_file = n
                if sample_spawn_file is None and "/spawn_pool_world/" in n and n.endswith(".json"):
                    sample_spawn_file = n
            load_species(z, species)
            load_spawns(z, species)
        print(f"read: {src}")

    for name in NOT_FINDABLE:
        if name in species:
            species[name]["no_spawn"] = True

    result = sorted(species.values(), key=lambda s: (s["dex"] or 99999, s["id"]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, separators=(",", ":")), encoding="utf-8")

    with_spawns = sum(1 for s in result if s["spawns"])
    print()
    print(f"wrote {OUT} ({len(result)} species, {with_spawns} with at least one spawn entry)")
    print()
    print("If those numbers look far too low (a few dozen instead of ~1000+),")
    print("the species/spawn file format didn't match what this script expects.")
    print("Sample paths it found, open one and compare to what load_species()")
    print("and load_spawns() above are reading:")
    print("  species file:", sample_species_file)
    print("  spawn file:  ", sample_spawn_file)


if __name__ == "__main__":
    main()
