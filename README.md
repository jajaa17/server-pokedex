# Server Pokedex

This is the Pokedex for **my own private Minecraft server** — I built it so
players on my server always have an up-to-date, searchable reference for
every Pokemon we've actually got set up, instead of relying on the vanilla
games' Pokedex (which doesn't match a heavily modded server at all). It's
free, needs no login, and works on phone or desktop.

That said, the site and the data pipeline behind it aren't tied to my
server specifically — if you run a Minecraft server on the same mod set,
you're welcome to fork this repo, point the build scripts at your own mod
files, and stand up the exact same site for your own players. See
"Regenerating the data" below.

**Mods this is built for:**
- [Cobblemon](https://modrinth.com/mod/cobblemon)
- [Mega Showdown](https://modrinth.com/mod/mega-showdown) (including the
  separate Legends Z-A mega-evolution addon jar)
- [Create Aeronautics](https://modrinth.com/mod/create-aeronautics)
- ATM x Mega Showdown (ATM x MSD) datapack/resourcepack

The shipped `docs/pokedex.json` reflects *my* server's specific
configuration (spawn tables, datapack tweaks, disabled species, etc.) — if
your server changes any of that from the defaults, regenerate the data
rather than using it as-is. No server or database needed to host the site
itself either; it's a plain static page reading a JSON file, so GitHub
Pages (free) is all it takes.

## What the site shows

- **Search, type filter, biome filter, and sort** across the whole dex.
- **Where to find it** — spawn buckets, biomes, level ranges, and the finer
  conditions Cobblemon actually checks (time of day, weather, moon phase, Y
  level, nearby blocks/structures, slime chunks), plus any "spawns more
  often when X" bonuses.
- **Evolution family tree** — the full chain for a species, not just the
  next step, with plain-English requirements (level, trade, held item,
  friendship, biome, move known, etc.), pulled straight from Cobblemon's own
  species data.
- **Mega Evolution** — which Pokemon can Mega Evolve on this server, the
  Mega Stone each one needs, what it's crafted from, and (for the newer
  Legends Z-A megas) which ones come from the separate zamega addon jar.
- **Special mechanics** — legendary/mythical obtain methods and form
  changes (Terastallization quirks, Primal Reversion, fusions, Reveal
  Glass, plate/memory swapping, etc.).
- **Real Pokedex flavor text**, with a read-aloud button.
- **Poke Snack tips** — which seasoning helps for a given Pokemon's type or
  rarity tier.
- Light and dark theme.

## How it's structured

- `docs/index.html` is the whole app — a single static page, no build step.
- `docs/pokedex.json` is the data file it reads. It's generated, not
  hand-written.
- `tools/` has the Python scripts that generate/enrich `docs/pokedex.json`
  by reading straight from the mod jars/zips (species data, spawn
  conditions, evolutions, mega evolutions, mechanics, flavor text). You run
  these locally whenever a mod updates, then commit the refreshed
  `docs/pokedex.json`.

## Regenerating the data

1. Install Python 3 if you don't have it.
2. Copy the relevant mod jars/zips (Cobblemon, Mega Showdown, the zamega
   addon, ATM x MSD) into `tools/`, or point each script at wherever they
   actually live.
3. Run the build scripts in `tools/` — each one reads from the jars/zips
   and only ever *adds* fields to `docs/pokedex.json`, so they're safe to
   rerun in any order after a mod update. Each script prints a summary of
   what it changed.
4. Commit the refreshed `docs/pokedex.json`.

## Put it on GitHub Pages

1. Create a repository on GitHub (public, so Pages can serve it for free).
2. Push this folder to it:
   ```
   git init
   git add .
   git commit -m "Server pokedex"
   git branch -M main
   git remote add origin https://github.com/<you>/<repo-name>.git
   git push -u origin main
   ```
3. In the repo, go to **Settings -> Pages**.
4. Under "Build and deployment", set **Source** to "Deploy from a branch",
   branch `main`, folder `/docs`. Save.
5. GitHub gives you a URL like `https://<you>.github.io/<repo-name>/` —
   that's the page to share with players.

Every time you update `docs/pokedex.json` (or `docs/index.html`) and push,
the live page updates within a minute or two, no rebuild step required.

## Notes and things to double check

- **Missing Pokemon:** a handful of species are flagged as not currently
  findable on this server (no wild spawn source in the pack). That list
  lives in `build_dex.py`.
- **Spawn data trust:** the extractor is only as accurate as what's in the
  jar/zip. Where a species' spawn data can't be confidently read, the app
  shows "no spawn data found" rather than guessing.
- **Offline testing:** to check the site locally before pushing, run
  `python -m http.server` from inside the `docs/` folder and open
  `http://localhost:8000` in a browser.
