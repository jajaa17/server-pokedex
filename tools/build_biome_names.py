"""
Resolves every Cobblemon spawn biome tag (and literal biome ref) used in
pokedex.json down to real, concrete biome IDs -- restricted to only the
mods actually installed on the server: vanilla Minecraft + Terralith.
(Tectonic doesn't add new biome IDs -- it's a terrain-shaping overlay on
top of vanilla/Terralith biomes, confirmed by inspecting its jar: no
data/tectonic/worldgen/biome or tags/worldgen/biome entries exist.)

Sources:
  - Cobblemon jar: data/cobblemon/tags/worldgen/biome/**  (the is_x tags
    used directly in spawn_pool_world condition.biomes)
  - Terralith jar: data/c/tags/worldgen/biome/**  (Terralith registers its
    own biomes into the "c:" common convention tags Cobblemon reads) and
    data/terralith/tags/worldgen/biome/**  (Terralith's own reference tags
    that the c: tags point to)
  - Vanilla: data/minecraft/tags/worldgen/biome/**, fetched on demand from
    the misode/mcmeta mirror (a GitHub repo that mirrors Mojang's own
    generated vanilla data per version) since we don't have the vanilla
    jar locally.

Any tag member from a namespace that isn't minecraft/terralith/cobblemon
(aether, biomesoplenty, the_bumblezone, wythers, clifftree, endercon,
blooming_biosphere, etc.) is silently dropped -- those mods aren't
installed so those biomes never actually generate.

Output: docs/biome_names.json -- maps each raw biome ref exactly as it
appears in pokedex.json's spawns[].biomes to a sorted list of real,
human-readable biome names.
"""
import json
import re
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
COBBLEMON_JAR = HERE / "mods" / "cobblemon.jar"
TERRALITH_JAR = HERE / "mods" / "terralith.jar"
POKEDEX_JSON = HERE / "pokedex.json"
OUT = HERE / "biome_names.json"

ALLOWED_NAMESPACES = {"minecraft", "terralith"}
VANILLA_MIRROR = "https://raw.githubusercontent.com/misode/mcmeta/{ver}-data/data/minecraft/tags/worldgen/biome/{path}.json"
MC_VERSION = "1.21.1"


def load_tags_from_jar(jar_path):
    tags = {}
    with zipfile.ZipFile(jar_path) as z:
        for n in z.namelist():
            m = re.match(r"data/([^/]+)/tags/worldgen/biome/(.+)\.json$", n)
            if not m:
                continue
            ns, path = m.group(1), m.group(2)
            try:
                data = json.loads(z.read(n))
            except ValueError:
                continue
            tags[f"{ns}:{path}"] = data.get("values", [])
    return tags


ALL_TAGS = {}
ALL_TAGS.update(load_tags_from_jar(COBBLEMON_JAR))
ALL_TAGS.update(load_tags_from_jar(TERRALITH_JAR))
print(f"loaded {len(ALL_TAGS)} tag definitions from jars")

_vanilla_cache = {}


def get_vanilla_tag(path):
    if path in _vanilla_cache:
        return _vanilla_cache[path]
    url = VANILLA_MIRROR.format(ver=MC_VERSION, path=path)
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(r.read())
            values = data.get("values", [])
    except Exception as e:
        print(f"  WARN: couldn't fetch vanilla tag minecraft:{path} ({e})")
        values = None
    _vanilla_cache[path] = values
    return values


def resolve_tag(tag_id, seen):
    if tag_id in seen:
        return set()
    seen.add(tag_id)
    ns, path = tag_id.split(":", 1)
    if ns == "minecraft":
        values = get_vanilla_tag(path)
    else:
        values = ALL_TAGS.get(tag_id)
    if values is None:
        return set()
    result = set()
    for v in values:
        if isinstance(v, dict):
            vid = v.get("id")
        else:
            vid = v
        if not vid:
            continue
        if vid.startswith("#"):
            inner = vid[1:]
            inner_ns = inner.split(":", 1)[0]
            if inner_ns not in ALLOWED_NAMESPACES and inner_ns != "cobblemon":
                continue  # tag from an uninstalled mod, contributes nothing
            result |= resolve_tag(inner, seen)
        else:
            vns = vid.split(":", 1)[0]
            if vns in ALLOWED_NAMESPACES:
                result.add(vid)
            # else: literal biome from an uninstalled mod, drop silently
    return result


def pretty_biome_name(biome_id):
    path = biome_id.split(":", 1)[1]
    words = path.replace("/", " ").replace("_", " ").split()
    return " ".join(w.capitalize() for w in words)


# ---- collect every raw biome ref actually used in pokedex.json ----
dex = json.loads(POKEDEX_JSON.read_text())
raw_refs = set()
for p in dex:
    for s in p.get("spawns", []):
        for b in s.get("biomes", []) or []:
            raw_refs.add(b)

print(f"found {len(raw_refs)} unique raw biome refs in pokedex.json")

result = {}
unresolved = []
for ref in sorted(raw_refs):
    if ref.startswith("#"):
        tag_id = ref[1:]
        ns = tag_id.split(":", 1)[0]
        if ns not in ALLOWED_NAMESPACES and ns != "cobblemon":
            result[ref] = []  # uninstalled mod's own category tag, nothing resolves
            continue
        biome_ids = resolve_tag(tag_id, set())
    else:
        # literal biome id
        ns = ref.split(":", 1)[0]
        biome_ids = {ref} if ns in ALLOWED_NAMESPACES else set()

    names = sorted({pretty_biome_name(b) for b in biome_ids})
    result[ref] = names
    if not names:
        unresolved.append(ref)

OUT.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
print(f"wrote {OUT}")
print(f"refs with zero resolved biomes (uninstalled-mod-only, or vanilla tag not found): {len(unresolved)}")
for r in unresolved:
    print("  ", r)
