"""
Splits regional forms (Alolan/Galarian/Hisuian/Paldean) out of their base
species into their own Pokedex entries with their own types and their own
spawn data, instead of being silently merged into the base species entry
(which is what the original build_dex.py did -- it only ever read the
first word of a spawn's "pokemon" field, so "raichu" and "raichu alolan"
both landed in the same "raichu" bucket, hiding the fact they spawn in
completely different biomes).

Only touches species that actually have a real regional form (labeled
"..._form" on a non-battle-only form in the Cobblemon species JSON) --
everything else in pokedex.json (including every ATM x MSD addition,
which this script never reads) is left completely untouched.

Source: Cobblemon-neoforge jar only. Regional forms are a base-Cobblemon
feature, not something ATM x MSD adds, so the jar is a complete source
for this -- confirmed by checking that every "*_form"-labeled form and
its spawn_pool_world entries live in data/cobblemon/**, never elsewhere.
"""
import csv
import json
import re
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
COBBLEMON_JAR = HERE / "mods" / "cobblemon.jar"
POKEDEX_JSON = HERE / "pokedex.json"
POKEAPI_CSV = HERE / "mods" / "pokeapi_pokemon.csv"

# Cobblemon aspect name -> PokeAPI slug suffix, for sprite lookups.
ASPECT_TO_POKEAPI_SLUG = {
    "alolan": "alola",
    "galarian": "galar",
    "hisuian": "hisui",
    "paldean": "paldea",
}


def load_pokeapi_ids():
    """slug ("raichu-alola") -> PokeAPI numeric id, for sprite URLs."""
    ids = {}
    with open(POKEAPI_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            ids[row["identifier"]] = int(row["id"])
    return ids


def species_files(z):
    for n in z.namelist():
        m = re.match(r"data/cobblemon/species/(?:.+/)?([^/]+)\.json$", n)
        if m:
            yield n, m.group(1)


def main():
    pokeapi_ids = load_pokeapi_ids()

    with zipfile.ZipFile(COBBLEMON_JAR) as z:
        # ---- pass 1: find every species with a real regional form ----
        regional_species = {}  # base_name -> {"species": dict, "forms": [...]}
        for path, base_name in species_files(z):
            try:
                sp = json.loads(z.read(path))
            except ValueError:
                continue
            real_forms = []
            for form in sp.get("forms", []):
                if form.get("battleOnly"):
                    continue
                labels = form.get("labels", [])
                aspects = form.get("aspects", [])
                region_labels = [l for l in labels if l.endswith("_form")]
                if not region_labels or not aspects:
                    continue
                region_key = region_labels[0][: -len("_form")]  # alolan/galarian/hisuian/paldean
                real_forms.append({"form": form, "region_key": region_key, "aspects": aspects})
            if real_forms:
                regional_species[base_name] = {"species": sp, "forms": real_forms}

        print(f"found {len(regional_species)} base species with a real regional form")

        # ---- build the id lookup: (base_name, aspect) -> new entry id ----
        aspect_to_id = {}
        new_entries = {}
        REGION_DISPLAY = {"alolan": "Alolan", "galarian": "Galarian", "hisuian": "Hisuian", "paldean": "Paldean"}

        for base_name, info in regional_species.items():
            sp = info["species"]
            dex = sp.get("nationalPokedexNumber") or sp.get("dex") or 0
            base_types = [t for t in (sp.get("primaryType"), sp.get("secondaryType")) if t]
            base_display = sp.get("name") or base_name.replace("_", " ").title()

            new_entries[base_name] = {
                "id": base_name,
                "namespace": "cobblemon",
                "dex": dex,
                "name": base_display,
                "types": base_types,
                "labels": sp.get("labels", []),
                "spawns": [],
            }

            for fdef in info["forms"]:
                form = fdef["form"]
                region_key = fdef["region_key"]
                region_display = REGION_DISPLAY.get(region_key, region_key.capitalize())
                form_id = f"{base_name}-{region_key}"
                form_types = [t for t in (form.get("primaryType"), form.get("secondaryType")) if t] or base_types

                pokeapi_slug = f"{base_name.replace('_', '-')}-{ASPECT_TO_POKEAPI_SLUG.get(region_key, region_key)}"
                sprite_id = pokeapi_ids.get(pokeapi_slug)

                entry = {
                    "id": form_id,
                    "namespace": "cobblemon",
                    "dex": dex,
                    "name": f"{region_display} {base_display}",
                    "types": form_types,
                    "labels": form.get("labels", []),
                    "spawns": [],
                    "regionalForm": region_display,
                }
                if sprite_id:
                    entry["spriteId"] = sprite_id
                new_entries[form_id] = entry

                for asp in fdef["aspects"]:
                    aspect_to_id[(base_name, asp.lower())] = form_id

        missing_sprites = [e["id"] for e in new_entries.values() if e.get("regionalForm") and "spriteId" not in e]
        print(f"regional-form entries missing a PokeAPI sprite id: {missing_sprites}")

        # ---- pass 2: route every spawn_pool_world entry for these species ----
        spawn_count = 0
        for n in z.namelist():
            if not re.match(r"data/cobblemon/spawn_pool_world/.+\.json$", n):
                continue
            try:
                entries = json.loads(z.read(n)).get("spawns", [])
            except ValueError:
                continue
            for e in entries:
                if not isinstance(e, dict) or "pokemon" not in e:
                    continue
                tokens = e["pokemon"].split()
                base_name = tokens[0].split(":")[-1].lower()
                if base_name not in regional_species:
                    continue
                target_id = base_name
                for t in tokens[1:]:
                    asp = t.split("=")[0].lower()
                    key = (base_name, asp)
                    if key in aspect_to_id:
                        target_id = aspect_to_id[key]
                        break
                cond = e.get("condition", {}) if isinstance(e.get("condition"), dict) else {}
                biomes = cond.get("biomes", [])
                level = e.get("level")
                if isinstance(level, dict):
                    lvl = [level.get("min"), level.get("max")]
                elif isinstance(level, list):
                    lvl = level
                else:
                    lvl = None
                new_entries[target_id]["spawns"].append({
                    "bucket": e.get("bucket", "unknown"),
                    "biomes": biomes,
                    "level": lvl,
                    "context": e.get("context"),
                })
                spawn_count += 1

        print(f"routed {spawn_count} spawn entries across base + regional forms")

    # ---- merge into the existing pokedex.json, replacing only the touched species ----
    dex = json.loads(POKEDEX_JSON.read_text())
    dex_by_id = {p["id"]: p for p in dex}
    replaced = 0
    added = 0
    for entry_id, entry in new_entries.items():
        if entry_id in dex_by_id:
            replaced += 1
        else:
            added += 1
        dex_by_id[entry_id] = entry

    result = sorted(dex_by_id.values(), key=lambda p: (p["dex"] or 99999, p["id"]))
    POKEDEX_JSON.write_text(json.dumps(result, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {POKEDEX_JSON}: replaced {replaced} existing entries, added {added} new regional-form entries")
    print(f"total entries now: {len(result)}")


if __name__ == "__main__":
    main()
