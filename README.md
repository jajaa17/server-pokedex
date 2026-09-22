# Server Pokedex

A static web app for players to search, filter by type, and sort every
Pokemon available on the server (Cobblemon + All The Mons x Mega Showdown),
plus see where each one spawns. No server or database needed, it's plain
HTML/JS reading a JSON file.

## How it's structured

- `tools/build_dex.py` reads your Cobblemon jar and ATM x MSD zip and writes
  `docs/pokedex.json`, the data file the web app uses. You run this locally,
  not on GitHub.
- `docs/index.html` is the whole app: search box, type filter, sort dropdown,
  and a detail view with spawn biomes and level ranges.
- `docs/pokedex.json` is the data. It starts as an empty list (`[]`) until
  you run the extractor.

## 1. Generate the data

1. Install Python 3 if you don't have it.
2. Copy your Cobblemon jar and your `ATM x MSD [v4.0].zip` into the `tools/`
   folder (or edit the `SOURCES` list at the top of `build_dex.py` to point
   at wherever they actually are).
3. From the `tools/` folder, run:
   ```
   python build_dex.py
   ```
4. It prints how many species and spawn entries it found, and writes
   `docs/pokedex.json`. If the numbers look far too low (a few dozen instead
   of a thousand-plus), the mod's internal file format doesn't match what
   the script expects. It also prints one example species file path and one
   example spawn file path, so you can open those inside the jar/zip
   yourself and compare their structure to what `load_species()` and
   `load_spawns()` in the script are reading, and adjust the field names.

Rerun this any time Cobblemon or ATM x MSD updates, and commit the new
`docs/pokedex.json`.

## 2. Put it on GitHub

1. Create a new repository on GitHub (public, so Pages can serve it for
   free).
2. Push this whole folder to it:
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
5. GitHub gives you a URL like `https://<you>.github.io/<repo-name>/`.
   That's the page to share with players.

Every time you update `docs/pokedex.json` and push, the live page updates
within a minute or two, no rebuild step required.

## Notes and things to double check

- **Missing Pokemon:** Castform, Oricorio, Celesteela, Iron Jugulis, Ting-Lu,
  and Iron Boulder are flagged as not currently findable, matching what you
  said earlier. If that list changes, edit `NOT_FINDABLE` at the top of
  `build_dex.py` and rerun it.
- **Dex numbers:** the script reads `nationalPokedexNumber` from each
  species file. If ATM species don't use that exact field name, their dex
  numbers may come through as 0 and sort to the end. Check the printed
  sample file if numbers look off.
- **Spawn data trust:** the extractor is only as accurate as what's in the
  jar/zip. If ATM x MSD stores spawns differently from base Cobblemon (a
  different folder name, a different field for biomes), those species will
  show up in the dex with no spawn info listed rather than wrong info. The
  app is written to show "no spawn data found" rather than guess.
- **File size:** a full dex with spawn data is usually a few hundred KB to
  low single-digit MB as JSON, well within what a browser loads instantly.
- **Offline testing:** to check the site locally before pushing, run
  `python -m http.server` from inside the `docs/` folder and open
  `http://localhost:8000` in a browser.
