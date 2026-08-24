#!/usr/bin/env python3
"""
valkyrie_packlist.py
Generic visual packing list for any Valkyrie MoM scenario.

- Lists Editor scenarios + every downloaded .valkyrie
- Lets you pick by number
- Builds tiles + real-monster packing list
- Opens the HTML automatically when finished
- Cleans up temp extraction folder
"""

import os
import re
import sys
import html
import zipfile
import shutil
import webbrowser
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Pillow not found – install with:  pip install pillow")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
APPDATA = Path(os.environ.get("APPDATA", ""))
MOM_ROOT = APPDATA / "Valkyrie" / "MoM"
EDITOR_DIR = MOM_ROOT / "Editor"
DOWNLOAD_DIR = APPDATA / "Valkyrie" / "Download"
IMPORT_IMG = MOM_ROOT / "import" / "img"
ICONS_DIR = Path(__file__).parent / "icons"

EXP_ICON_FILE = {
    "Core":                   "icon_core.png",
    "Recurring Nightmares":   "icon_rn.png",
    "Suppressed Memories":    "icon_sm.png",
    "Beyond the Threshold":   "icon_btt.png",
    "Streets of Arkham":      "icon_soa.png",
    "Sanctum of Twilight":    "icon_sot.png",
    "Horrific Journeys":      "icon_hj.png",
    "Path of the Serpent":    "icon_pots.png",
}

MAD_TO_EXP = {
    "MAD20": "Core",
    "MAD01": "Recurring Nightmares",
    "MAD06": "Suppressed Memories",
    "MAD23": "Beyond the Threshold",
    "MAD25": "Streets of Arkham",
    "MAD26": "Sanctum of Twilight",
    "MAD27": "Horrific Journeys",
    "MAD28": "Path of the Serpent",
}

NAME_OVERRIDES = {
    "TileSideHouseBoat": "Houseboat",
    "TileSideRentalDock": "Rental Dock",
    "TileSideTownSquare": "Town Square",
    "TileSideAlleyCorner1": "Alley Corner 1",
    "TileSideAlleyCorner2": "Alley Corner 2",
    "TileSideStreetCorner1": "Street Corner 1",
    "TileSideFurnaceRoom": "Furnace Room",
    "TileSideGuestBedroom": "Guest Bedroom",
    "TileSideHiddenLaboratory": "Hidden Laboratory",
    "TileSideBasementLanding": "Basement Landing",
    "TileSideAtticLoft": "Attic Loft",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def convert_any_image(src: Path, dst: Path, rotate: int = 0) -> bool:
    try:
        with Image.open(src) as im:
            im = im.convert("RGBA")
            if rotate:
                im = im.rotate(rotate, expand=True)
            im.save(dst, "PNG")
        return True
    except Exception as e:
        print(f"  ✗ {src.name}: {e}")
        return False

def side_to_candidates(side: str) -> list[str]:
    base = side.replace("TileSide", "")
    cands = [
        f"Tile_{base}_MAD20.dds", f"Tile_{base}_MAD01.dds", f"Tile_{base}_MAD06.dds",
        f"Tile_{base}_MAD23.dds", f"Tile_{base}_MAD25.dds", f"Tile_{base}_MAD27.dds",
        f"Tile_{base}_MAD28.dds", f"TILE_{base.upper()}_MAD20.dds",
        f"TILE_{base.upper()}_MAD27.dds", f"Tile_{base}.dds",
    ]
    underscored = re.sub(r"([a-z])([A-Z])", r"\1_\2", base)
    if underscored != base:
        cands = [f"Tile_{underscored}_MAD20.dds", f"Tile_{underscored}_MAD01.dds"] + cands
    return cands

def find_tile_image(side: str) -> Path | None:
    for name in side_to_candidates(side):
        p = IMPORT_IMG / name
        if p.exists():
            return p
    pattern = re.sub(r"[^a-z0-9]", "", side.replace("TileSide", "").lower())
    for p in IMPORT_IMG.glob("Tile_*.dds"):
        if pattern in re.sub(r"[^a-z0-9]", "", p.stem.lower()):
            return p
    return None

def find_monster_dds(name: str) -> Path | None:
    clean = re.sub(r"^(Monster|CustomMonster)", "", name)
    candidates = [
        f"Monster_{clean}.dds",
        f"Monster_{clean}_000002.dds",
        f"Monster_{name}.dds",
        f"{name}.dds",
    ]
    for suffix in ("_Tile21", "_BASE", "_REvent1", "_Tile15", "_Tile3", "_Tile14"):
        if clean.endswith(suffix):
            candidates.insert(0, f"Monster_{clean[:-len(suffix)]}.dds")
    for c in candidates:
        p = IMPORT_IMG / c
        if p.exists():
            return p
    pattern = re.sub(r"[^a-z0-9]", "", clean.lower())
    for p in IMPORT_IMG.glob("Monster_*.dds"):
        if pattern and pattern in re.sub(r"[^a-z0-9]", "", p.stem.lower()):
            return p
    return None

def parse_tiles_ini(tiles_ini: Path) -> dict[str, str]:
    text = tiles_ini.read_text(encoding="utf-8", errors="ignore")
    mapping, current = {}, None
    for line in text.splitlines():
        m = re.match(r"^\[([^\]]+)\]", line)
        if m:
            current = m.group(1).strip()
            continue
        if current and line.strip().lower().startswith("side="):
            mapping[current] = line.split("=", 1)[1].strip()
    return mapping

def parse_custom_monsters(scenario_dir: Path) -> dict[str, dict]:
    result = {}
    monsters_ini = scenario_dir / "monsters.ini"
    if not monsters_ini.exists():
        return result
    text = monsters_ini.read_text(encoding="utf-8", errors="ignore")
    current = None
    for line in text.splitlines():
        m = re.match(r"^\[(CustomMonster[^\]]+)\]", line)
        if m:
            current = m.group(1).strip()
            result[current] = {}
            continue
        if current is None:
            continue
        low = line.strip().lower()
        if low.startswith("base="):
            result[current]["base"] = line.split("=", 1)[1].strip()
        elif low.startswith("image="):
            val = line.split("=", 1)[1].strip()
            if val:
                result[current]["image"] = val
    return result

def collect_added_tiles(scenario_dir: Path) -> tuple[list[str], list[str]]:
    normal, six = [], []
    seen = set()
    for ini in scenario_dir.glob("*.ini"):
        text = ini.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"^add\s*=\s*(.+)$", text, re.MULTILINE | re.IGNORECASE):
            for name in m.group(1).split():
                name = name.strip()
                if not name.startswith("Tile") or name in seen:
                    continue
                seen.add(name)
                if "6Player" in name:
                    six.append(name)
                else:
                    normal.append(name)
    return normal, six

def collect_real_monsters(scenario_dir: Path) -> list[tuple[str, list[str]]]:
    custom_info = parse_custom_monsters(scenario_dir)
    order = []
    used_by: dict[str, list[str]] = {}
    for ini in scenario_dir.glob("*.ini"):
        text = ini.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"^monster\s*=\s*(\S+)", text, re.MULTILINE | re.IGNORECASE):
            mon = m.group(1).strip()
            if not mon:
                continue
            if mon in custom_info and "base" in custom_info[mon]:
                real = custom_info[mon]["base"]
                custom_name = mon
            else:
                real = mon
                custom_name = None
            if real not in used_by:
                used_by[real] = []
                order.append(real)
            if custom_name and custom_name not in used_by[real]:
                used_by[real].append(custom_name)
    return [(real, used_by[real]) for real in order]

def nice_monster_name(monster: str) -> str:
    name = re.sub(r"^CustomMonster", "", monster)
    name = re.sub(r"^Monster", "", name)
    name = re.sub(r"_(Tile\d+|BASE|REvent\d+)$", "", name)
    name = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)
    return name.strip() or monster

def nice_name(side: str) -> str:
    if side in NAME_OVERRIDES:
        return NAME_OVERRIDES[side]
    base = side.replace("TileSide", "")
    return re.sub(r"([a-z])([A-Z])", r"\1 \2", base)

def guess_expansion(img_path: Path | None) -> str:
    if not img_path:
        return "Unknown"
    m = re.search(r"(MAD\d+)", img_path.name, re.IGNORECASE)
    if m:
        return MAD_TO_EXP.get(m.group(1).upper(), "Unknown")
    return "Unknown"

def guess_size(img_path: Path | None) -> str:
    if not img_path:
        return "?"
    size = img_path.stat().st_size
    if size > 1_800_000:
        return "L"
    if size > 1_000_000:
        return "M"
    return "S"

def find_scenario_name(folder: Path) -> str:
    # Localization files (both "key = value" and "key,value" formats)
    for loc_name in ("Localization.English.txt", "Localization.txt"):
        loc = folder / loc_name
        if not loc.exists():
            continue
        text = loc.read_text(encoding="utf-8", errors="ignore")
        for key in ("quest.name", "UISplashTitle", "name"):
            # INI style: key = value
            m = re.search(rf"^{re.escape(key)}\s*=\s*(.+)$", text, re.MULTILINE | re.IGNORECASE)
            if m:
                return m.group(1).strip().strip('"')
            # CSV style: key,value
            m = re.search(rf"^{re.escape(key)}\s*,\s*(.+)$", text, re.MULTILINE | re.IGNORECASE)
            if m:
                return m.group(1).strip().strip('"')

    # quest.ini
    quest = folder / "quest.ini"
    if quest.exists():
        text = quest.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r"^name\s*=\s*(.+)$", text, re.MULTILINE | re.IGNORECASE)
        if m:
            return m.group(1).strip().strip('"')

    return folder.name

def discover_scenarios() -> list[Path]:
    found = []
    if EDITOR_DIR.exists():
        for p in sorted(EDITOR_DIR.iterdir()):
            if p.is_dir() and (p / "tiles.ini").exists():
                found.append(p)
    if DOWNLOAD_DIR.exists():
        for p in sorted(DOWNLOAD_DIR.glob("*.valkyrie")):
            found.append(p)
    for p in sorted(Path(".").glob("*.valkyrie")):
        if p.resolve() not in [x.resolve() for x in found]:
            found.append(p)
    return found

# ---------------------------------------------------------------------------
# Build packing list
# ---------------------------------------------------------------------------
def build_packlist(scenario_dir: Path):
    tiles_ini = scenario_dir / "tiles.ini"
    if not tiles_ini.exists():
        print("No tiles.ini found in this scenario")
        return

    scenario_name = find_scenario_name(scenario_dir)
    print(f"\nBuilding packing list for: {scenario_name}")

    component_to_side = parse_tiles_ini(tiles_ini)
    normal_comps, six_comps = collect_added_tiles(scenario_dir)
    real_monsters = collect_real_monsters(scenario_dir)

    print(f"  Normal tiles  : {len(normal_comps)}")
    print(f"  6-player tiles: {len(six_comps)}")
    print(f"  Real monsters : {len(real_monsters)}")

    sides = []
    seen = set()
    for comp in normal_comps:
        side = component_to_side.get(comp)
        if side and side not in seen:
            seen.add(side)
            sides.append((side, False))
    for comp in six_comps:
        side = component_to_side.get(comp)
        if side and side not in seen:
            seen.add(side)
            sides.append((side, True))

    out_dir = Path(f"packlist_{re.sub(r'[^A-Za-z0-9]+', '_', scenario_name)}")
    tiles_dir = out_dir / "tiles"
    monsters_dir = out_dir / "monsters"
    icons_out = out_dir / "icons"
    for d in (tiles_dir, monsters_dir, icons_out):
        d.mkdir(parents=True, exist_ok=True)

    icon_map = {}
    for exp, fname in EXP_ICON_FILE.items():
        src_icon = ICONS_DIR / fname
        if src_icon.exists():
            shutil.copy2(src_icon, icons_out / fname)
            icon_map[exp] = f"icons/{fname}"
            print(f"  ✓ icon {fname}")
        else:
            print(f"  ! missing {src_icon.name}")

    tile_cards = []
    for i, (side, is_six) in enumerate(sides, 1):
        img_src = find_tile_image(side)
        printed = nice_name(side)
        exp = guess_expansion(img_src)
        size = guess_size(img_src)
        img_rel = None
        if img_src:
            dst = tiles_dir / f"{side}.png"
            if convert_any_image(img_src, dst):
                img_rel = f"tiles/{side}.png"
                print(f"  ✓ tile {side} → {printed}")
        tile_cards.append({
            "num": i, "printed": printed, "exp": exp, "size": size,
            "img": img_rel, "icon": icon_map.get(exp), "six": is_six,
        })

    monster_cards = []
    for i, (real, customs) in enumerate(real_monsters, 1):
        printed = nice_monster_name(real)
        img_src = find_monster_dds(real)
        img_rel = None
        if img_src:
            dst = monsters_dir / f"{real}.png"
            if convert_any_image(img_src, dst, rotate=180):
                img_rel = f"monsters/{real}.png"
                print(f"  ✓ monster {real} → {printed}")
            else:
                print(f"  ✗ convert failed {real}")
        else:
            print(f"  ? no image for {real}")
        note = ""
        if customs:
            short = [nice_monster_name(c) for c in customs]
            note = " (as " + ", ".join(short) + ")"
        monster_cards.append({
            "num": i, "printed": printed, "note": note,
            "raw": real, "img": img_rel, "has_custom": bool(customs),
        })

    legend = []
    for exp in ["Core", "Recurring Nightmares", "Suppressed Memories",
                "Beyond the Threshold", "Streets of Arkham",
                "Sanctum of Twilight", "Horrific Journeys", "Path of the Serpent"]:
        if exp in icon_map:
            legend.append(f'<span><img src="{icon_map[exp]}" height="18" alt=""> {exp}</span>')

    html_parts = [f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>Packing List – {html.escape(scenario_name)}</title>
<style>
  body{{font-family:system-ui,sans-serif;background:#1a1a1a;color:#eee;margin:0;padding:1.5rem}}
  h1{{margin-top:0}}
  .legend{{margin-bottom:1.2rem;font-size:.9rem;color:#bbb;display:flex;gap:1.5rem;flex-wrap:wrap;align-items:center}}
  .legend span{{display:flex;align-items:center;gap:.4rem}}
  .legend img{{height:18px}}
  .section{{margin:2.5rem 0 0.8rem;font-size:1.25rem;color:#ddd;border-bottom:1px solid #444;padding-bottom:0.35rem}}
  .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:1rem}}
  .card{{background:#2a2a2a;border-radius:10px;overflow:hidden;box-shadow:0 4px 12px #0008}}
  .card.six{{border:2px solid #c9a227}}
  .card.custom{{border:2px solid #6a5acd}}
  .card img.tile, .card img.monster{{width:100%;display:block;background:#111;aspect-ratio:1;object-fit:contain}}
  .card .missing{{height:160px;display:flex;align-items:center;justify-content:center;color:#666;font-size:.85rem}}
  .meta{{padding:.7rem .9rem}}
  .num{{font-size:.75rem;color:#888}}
  .name{{font-weight:600;font-size:1.0rem;margin:.15rem 0}}
  .note{{font-size:.75rem;color:#aaa;margin-top:.15rem}}
  .badges{{display:flex;align-items:center;gap:.4rem;margin-top:.3rem;flex-wrap:wrap}}
  .badges img.icon{{height:16px;width:auto}}
  .size{{background:#444;padding:.12rem .4rem;border-radius:4px;font-size:.72rem}}
  .exp{{font-size:.78rem;color:#bbb}}
  .six-badge{{background:#c9a227;color:#111;padding:.12rem .4rem;border-radius:4px;font-size:.72rem;font-weight:600}}
  .custom-badge{{background:#6a5acd;color:#fff;padding:.12rem .4rem;border-radius:4px;font-size:.72rem;font-weight:600}}
</style></head><body>
<h1>{html.escape(scenario_name)} – Packing List</h1>
<p>Tiles and real monster tokens needed for this scenario.<br>
Custom monsters are mapped to the physical base token you must pull from the box.</p>
<div class="legend">{''.join(legend)}</div>
"""]

    normal_cards = [c for c in tile_cards if not c["six"]]
    six_cards = [c for c in tile_cards if c["six"]]

    if normal_cards:
        html_parts.append('<div class="section">Tiles</div><div class="grid">')
        for c in normal_cards:
            img_html = (f'<img class="tile" src="{c["img"]}" alt="{html.escape(c["printed"])}">'
                        if c["img"] else '<div class="missing">no image</div>')
            icon_html = f'<img class="icon" src="{c["icon"]}" alt="">' if c["icon"] else ""
            html_parts.append(f"""
  <div class="card">{img_html}
    <div class="meta">
      <div class="num">#{c["num"]:02d}</div>
      <div class="name">{html.escape(c["printed"])}</div>
      <div class="badges">{icon_html}<span class="exp">{html.escape(c["exp"])}</span><span class="size">{html.escape(c["size"])}</span></div>
    </div>
  </div>""")
        html_parts.append("</div>")

    if six_cards:
        html_parts.append('<div class="section">Tiles – 6-player only</div><div class="grid">')
        for c in six_cards:
            img_html = (f'<img class="tile" src="{c["img"]}" alt="{html.escape(c["printed"])}">'
                        if c["img"] else '<div class="missing">no image</div>')
            icon_html = f'<img class="icon" src="{c["icon"]}" alt="">' if c["icon"] else ""
            html_parts.append(f"""
  <div class="card six">{img_html}
    <div class="meta">
      <div class="num">#{c["num"]:02d}</div>
      <div class="name">{html.escape(c["printed"])}</div>
      <div class="badges">{icon_html}<span class="exp">{html.escape(c["exp"])}</span><span class="size">{html.escape(c["size"])}</span><span class="six-badge">6-player only</span></div>
    </div>
  </div>""")
        html_parts.append("</div>")

    if monster_cards:
        html_parts.append('<div class="section">Monsters (real tokens)</div><div class="grid">')
        for c in monster_cards:
            img_html = (f'<img class="monster" src="{c["img"]}" alt="{html.escape(c["printed"])}">'
                        if c["img"] else '<div class="missing">no image</div>')
            custom_badge = '<span class="custom-badge">used as custom</span>' if c["has_custom"] else ""
            cls = "card custom" if c["has_custom"] else "card"
            note_html = f'<div class="note">{html.escape(c["note"])}</div>' if c["note"] else ""
            html_parts.append(f"""
  <div class="{cls}">{img_html}
    <div class="meta">
      <div class="num">#{c["num"]:02d}</div>
      <div class="name">{html.escape(c["printed"])}</div>
      {note_html}
      <div class="badges">{custom_badge}</div>
    </div>
  </div>""")
        html_parts.append("</div>")

    html_parts.append("</body></html>")
    out = out_dir / "packing_list.html"
    out.write_text("".join(html_parts), encoding="utf-8")
    print(f"\nDone → {out}")

    # Automatically open in the default browser
    webbrowser.open(out.resolve().as_uri())
    print("Opened in browser.")

# ---------------------------------------------------------------------------
# Main – interactive picker
# ---------------------------------------------------------------------------
def main():
    scenarios = discover_scenarios()
    if not scenarios:
        print("No scenarios found.")
        print(f"Looked in: {EDITOR_DIR}")
        print(f"       and: {DOWNLOAD_DIR}")
        sys.exit(1)

    print("Available scenarios:\n")
    for i, p in enumerate(scenarios, 1):
        if p.is_dir():
            name = find_scenario_name(p)
            print(f"  {i:2d}. [Editor] {name}  ({p.name})")
        else:
            print(f"  {i:2d}. [Download] {p.stem}")

    print()
    while True:
        try:
            choice = input("Enter number (or q to quit): ").strip()
            if choice.lower() in ("q", "quit", "exit"):
                print("Bye.")
                return
            idx = int(choice)
            if 1 <= idx <= len(scenarios):
                break
            print(f"Please enter a number between 1 and {len(scenarios)}")
        except ValueError:
            print("Please enter a number")

    selected = scenarios[idx - 1]
    work = None

    if selected.suffix.lower() == ".valkyrie":
        work = Path("temp_scenario")
        if work.exists():
            shutil.rmtree(work)
        work.mkdir()
        print(f"Extracting {selected.name} ...")
        with zipfile.ZipFile(selected) as z:
            z.extractall(work)
        scenario_dir = work
    else:
        scenario_dir = selected

    try:
        build_packlist(scenario_dir)
    finally:
        # Always clean up the temp extraction folder
        if work is not None and work.exists():
            shutil.rmtree(work)
            print("Cleaned up temp_scenario/")

if __name__ == "__main__":
    main()