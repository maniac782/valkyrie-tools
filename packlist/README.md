# Valkyrie Packing List

Generate a visual packing list for any **Mansions of Madness 2nd Edition** scenario used with [Valkyrie](https://github.com/NPBruce/valkyrie).

The tool reads a scenario’s tile and monster definitions, converts the official art to PNGs, and builds an HTML checklist you can open in a browser while packing the box.

---

## Features

- Interactive picker for scenarios in **Valkyrie Editor** and **Download** folders
- Tile cards with art, printed name, expansion icon, and **v5.2 tile index** (e.g. `1 S`, `12 S`, `6 M`)
- 6-player-only tiles listed separately
- Monsters mapped to real base tokens (custom monsters resolve via `base=`)
- Auto-opens the HTML when finished
- Cleans up temporary extraction folders

Tile index numbers match the community **Mansions of Madness Tiles Index v5.2**:

**https://boardgamegeek.com/filepage/147448/mansions-of-madness-tiles-index**

If you organize your tiles by those numbers, the packing list tells you exactly which index to pull.

---

## Prerequisites

### Software

| Requirement | Notes |
|-------------|--------|
| **Python 3.10+** | 3.11 / 3.12 recommended |
| **Pillow** | `pip install pillow` |
| **Valkyrie** | Installed and used at least once so AppData paths exist |

### Valkyrie data

Scenarios must already be on disk:

1. Download / subscribe to scenarios in Valkyrie (they appear under  
   `%APPDATA%\Valkyrie\Download\` as `.valkyrie` files).
2. Optionally open a scenario in the Editor (copies under  
   `%APPDATA%\Valkyrie\MoM\Editor\`).

The packlist tool does **not** download scenarios. It only lists what Valkyrie already has.

### Official tile art

Valkyrie must have imported the game content so tile images exist under:

```text
%APPDATA%\Valkyrie\MoM\import\img\
```

(Those `Tile_*.dds` files are used for the card art.)

### Expansion icons

Place these PNGs next to the script in an `icons/` folder:

```text
icons/
  icon_core.png
  icon_rn.png
  icon_sm.png
  icon_btt.png
  icon_soa.png
  icon_sot.png
  icon_hj.png
  icon_pots.png
```

| File | Expansion |
|------|-----------|
| `icon_core.png` | Core |
| `icon_rn.png` | Recurring Nightmares |
| `icon_sm.png` | Suppressed Memories |
| `icon_btt.png` | Beyond the Threshold |
| `icon_soa.png` | Streets of Arkham |
| `icon_sot.png` | Sanctum of Twilight |
| `icon_hj.png` | Horrific Journeys |
| `icon_pots.png` | Path of the Serpent |

---

## Install

```powershell
cd path\to\valkyrie-tools\packlist   # or your clone folder
pip install pillow
```

No other Python packages are required.

---

## Run

```powershell
python valkyrie_packlist.py
```

1. The script lists available scenarios (Editor + Download).
2. Enter the number of the scenario you want.
3. If you pick a `.valkyrie` file, it is extracted temporarily, processed, then deleted.
4. Output is written to `packlist_<ScenarioName>/packing_list.html` and opened in your default browser.

Example output folder:

```text
packlist_Stress_and_Strain/
  packing_list.html
  tiles/          # converted tile PNGs
  monsters/       # converted monster PNGs
  icons/          # copied expansion icons
```

---

## How tiles are labeled

Each tile card shows:

- **Name** – printed side name (e.g. Hall Corner)
- **Expansion icon + name** – physical product the tile belongs to
- **Index** – community number from Tiles Index **v5.2** (e.g. `35 S`)

Indexes are hardcoded from v5.2 of the BGG file above. Expansion membership is also fixed in the catalog so icons stay correct even if multiple DDS variants exist in the import folder.

If a rare side is missing from the catalog, the badge shows `?` and expansion `Unknown`. Open an issue or send the `side=` line from `tiles.ini` and it can be added from the PDF.

---

## Typical workflow

1. Subscribe to / download the scenario in Valkyrie.
2. Run `python valkyrie_packlist.py` and pick that scenario.
3. Use the HTML page while packing tiles and monster tokens from the box.
4. Optional: sort physical tiles by v5.2 index so the numbers on the list match your storage.

---

## Troubleshooting

| Problem | Check |
|---------|--------|
| “No scenarios found” | Confirm files under `%APPDATA%\Valkyrie\Download\` and/or `...\MoM\Editor\` |
| Missing tile art | Confirm `%APPDATA%\Valkyrie\MoM\import\img\Tile_*.dds` exists (run Valkyrie content import) |
| Missing expansion icons | Ensure `icons/` sits next to `valkyrie_packlist.py` with the eight PNGs |
| `Pillow not found` | `pip install pillow` |
| Index shows `?` | That `TileSide*` is not in the v5.2 catalog yet — report the side id |

---

## License / credits

- Tile index numbers: [Mansions of Madness Tiles Index](https://boardgamegeek.com/filepage/147448/mansions-of-madness-tiles-index) (community file, v5.2)
- Scenario format and art: Valkyrie / Fantasy Flight Games content as installed locally
- This tool only reads local Valkyrie data; it does not redistribute game assets
```