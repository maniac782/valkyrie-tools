#!/usr/bin/env python3
"""
valkyrie_packlist.py
Generic visual packing list for any Valkyrie MoM scenario.
- Lists Editor scenarios + every downloaded .valkyrie
- Lets you pick by number
- Builds tiles + real-monster packing list
- Size/index/expansion from MansionsOfMadnessTilesIndex_v5.2.pdf (every tile side Valkyrie defines, matched by
  name and set symbol; built with momcasebook's scripts/tiles-index-from-pdf.py)
- Expansion icon comes from the catalog (not whichever DDS is found first)
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
    print("Pillow not found – install with: pip install pillow")
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
    "Core": "icon_core.png",
    "Recurring Nightmares": "icon_rn.png",
    "Suppressed Memories": "icon_sm.png",
    "Beyond the Threshold": "icon_btt.png",
    "Streets of Arkham": "icon_soa.png",
    "Sanctum of Twilight": "icon_sot.png",
    "Horrific Journeys": "icon_hj.png",
    "Path of the Serpent": "icon_pots.png",
}

EXP_TO_MAD = {
    "Core": "MAD20",
    "Recurring Nightmares": "MAD01",
    "Suppressed Memories": "MAD06",
    "Beyond the Threshold": "MAD23",
    "Streets of Arkham": "MAD25",
    "Sanctum of Twilight": "MAD26",
    "Horrific Journeys": "MAD27",
    "Path of the Serpent": "MAD28",
}

MAD_TO_EXP = {v: k for k, v in EXP_TO_MAD.items()}

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

# TileSide -> (size, index, expansion)
# Index from MansionsOfMadnessTilesIndex_v5.2.pdf (every side Valkyrie defines, matched by name and set symbol)
# Expansion = physical product that tile belongs to (first-edition sides: Recurring Nightmares / Suppressed Memories)
TILE_INFO: dict[str, tuple[str, str, str]] = {
    # ===== Core (MoMBase) =====
    'TileSideAlley1': ('S', '1S', 'Core'),
    'TileSideBedroom1': ('S', '1S', 'Core'),
    'TileSideAlley2': ('S', '2S', 'Core'),
    'TileSideBedroom2': ('S', '2S', 'Core'),
    'TileSideBellTower': ('S', '3S', 'Core'),
    'TileSideStreetCorner1': ('S', '3S', 'Core'),
    'TileSideAlleyEnd': ('S', '4S', 'Core'),
    'TileSideBilliardsRoom': ('S', '4S', 'Core'),
    'TileSideEntryHall': ('S', '11S', 'Core'),
    'TileSideStreetCorner2': ('S', '11S', 'Core'),
    'TileSideDock2': ('S', '14S', 'Core'),
    'TileSideHall1': ('S', '14S', 'Core'),
    'TileSideDock1': ('S', '15S', 'Core'),
    'TileSideHall2': ('S', '15S', 'Core'),
    'TileSideAlleyCorner1': ('S', '16S', 'Core'),
    'TileSideHallCorner1': ('S', '16S', 'Core'),
    'TileSideAlleyCorner2': ('S', '17S', 'Core'),
    'TileSideHallCorner2': ('S', '17S', 'Core'),
    'TileSideBathroom': ('S', '18S', 'Core'),
    'TileSideStreet1': ('S', '18S', 'Core'),
    'TileSideHallEnd': ('S', '19S', 'Core'),
    'TileSideStreetCorner3': ('S', '19S', 'Core'),
    'TileSideHallStairs': ('S', '20S', 'Core'),
    'TileSideStreet2': ('S', '20S', 'Core'),
    'TileSideLibrary': ('S', '21S', 'Core'),
    'TileSideYard1': ('S', '21S', 'Core'),
    'TileSideHouseBoat': ('S', '23S', 'Core'),
    'TileSideOffice': ('S', '23S', 'Core'),
    'TileSideRentalDock': ('S', '31S', 'Core'),
    'TileSideStudy': ('S', '31S', 'Core'),
    'TileSideBeach': ('S', '32S', 'Core'),
    'TileSideYard2': ('S', '32S', 'Core'),
    'TileSideAttic': ('M', '1M', 'Core'),
    'TileSideParkPond': ('M', '1M', 'Core'),
    'TileSideBallroom': ('M', '5M', 'Core'),
    'TileSideWarehouse': ('M', '5M', 'Core'),
    'TileSideBasement': ('M', '7M', 'Core'),
    'TileSideFleaMarket': ('M', '7M', 'Core'),
    'TileSideConservatory': ('M', '8M', 'Core'),
    'TileSideStorefront': ('M', '8M', 'Core'),
    'TileSideDiningRoom': ('M', '9M', 'Core'),
    'TileSideTownSquare': ('M', '9M', 'Core'),
    'TileSideInteriorHall': ('M', '15M', 'Core'),
    'TileSideRootCellar': ('M', '15M', 'Core'),
    'TileSideLobby': ('M', '16M', 'Core'),
    'TileSideToolShed': ('M', '16M', 'Core'),
    'TileSideLounge': ('M', '17M', 'Core'),
    'TileSidePier': ('M', '17M', 'Core'),
    # ===== Recurring Nightmares (MoM1ET) =====
    'TileSideCave1': ('S', '5S', 'Recurring Nightmares'),
    'TileSideHallway4': ('S', '5S', 'Recurring Nightmares'),
    'TileSideCave2': ('S', '6S', 'Recurring Nightmares'),
    'TileSideHallway3': ('S', '6S', 'Recurring Nightmares'),
    'TileSideCeremonyRoom': ('S', '8S', 'Recurring Nightmares'),
    'TileSideNursery': ('S', '8S', 'Recurring Nightmares'),
    'TileSideChasm': ('S', '9S', 'Recurring Nightmares'),
    'TileSideHallway2': ('S', '9S', 'Recurring Nightmares'),
    'TileSideCrypt': ('S', '10S', 'Recurring Nightmares'),
    'TileSideHallway1': ('S', '10S', 'Recurring Nightmares'),
    'TileSideFurnaceRoom': ('S', '12S', 'Recurring Nightmares'),
    'TileSideMasterBedroom': ('S', '12S', 'Recurring Nightmares'),
    'TileSideGuestBedroom': ('S', '29S', 'Recurring Nightmares'),
    'TileSideSecretPassage': ('S', '29S', 'Recurring Nightmares'),
    'TileSideAtticLoft': ('M', '2M', 'Recurring Nightmares'),
    'TileSideChapel': ('M', '2M', 'Recurring Nightmares'),
    'TileSideGallery': ('M', '4M', 'Recurring Nightmares'),
    'TileSideStorageShed': ('M', '4M', 'Recurring Nightmares'),
    'TileSideBasementLanding': ('M', '6M', 'Recurring Nightmares'),
    'TileSideTowerRoom': ('M', '6M', 'Recurring Nightmares'),
    'TileSideGarden': ('M', '10M', 'Recurring Nightmares'),
    'TileSideLibrary1E': ('M', '10M', 'Recurring Nightmares'),
    'TileSideFrontPorch': ('M', '11M', 'Recurring Nightmares'),
    'TileSideLaboratory': ('M', '11M', 'Recurring Nightmares'),
    'TileSideDiningRoom1E': ('M', '13M', 'Recurring Nightmares'),
    'TileSideGraveyard': ('M', '13M', 'Recurring Nightmares'),
    'TileSideCornerHallway': ('M', '21M', 'Recurring Nightmares'),
    'TileSideRootCellar1E': ('M', '21M', 'Recurring Nightmares'),
    'TileSideFoyer': ('L', '2L', 'Recurring Nightmares'),
    'TileSideFrontYard': ('L', '2L', 'Recurring Nightmares'),
    # ===== Suppressed Memories (FAT) =====
    'TileSideCave3': ('S', '7S', 'Suppressed Memories'),
    'TileSideOfficeFA': ('S', '7S', 'Suppressed Memories'),
    'TileSideGraveyard2': ('S', '13S', 'Suppressed Memories'),
    'TileSideHallway5': ('S', '13S', 'Suppressed Memories'),
    'TileSideMedicalStorage': ('S', '22S', 'Suppressed Memories'),
    'TileSideObservationRoom': ('S', '22S', 'Suppressed Memories'),
    'TileSideGreenhouse': ('M', '3M', 'Suppressed Memories'),
    'TileSideHiddenLaboratory': ('M', '3M', 'Suppressed Memories'),
    'TileSideGeneratorRoom': ('M', '12M', 'Suppressed Memories'),
    'TileSideOperatingTheater': ('M', '12M', 'Suppressed Memories'),
    'TileSideMorgue': ('M', '20M', 'Suppressed Memories'),
    'TileSideRooftop': ('M', '20M', 'Suppressed Memories'),
    # ===== Suppressed Memories (CotWT) =====
    'TileSideCaveBend': ('S', '24S', 'Suppressed Memories'),
    'TileSideOldOak': ('S', '24S', 'Suppressed Memories'),
    'TileSideCaveEntrance': ('S', '25S', 'Suppressed Memories'),
    'TileSidePigPen': ('S', '25S', 'Suppressed Memories'),
    'TileSideOldWell': ('S', '26S', 'Suppressed Memories'),
    'TileSideRiverBend': ('S', '26S', 'Suppressed Memories'),
    'TileSideOuthouse': ('S', '27S', 'Suppressed Memories'),
    'TileSideRiverRapids': ('S', '27S', 'Suppressed Memories'),
    'TileSideCampsite': ('S', '28S', 'Suppressed Memories'),
    'TileSideScarecrow': ('S', '28S', 'Suppressed Memories'),
    'TileSideRottedPorch': ('S', '30S', 'Suppressed Memories'),
    'TileSideSpruceGrove': ('S', '30S', 'Suppressed Memories'),
    'TileSideAbandonedShack': ('M', '14M', 'Suppressed Memories'),
    'TileSideHillTop': ('M', '14M', 'Suppressed Memories'),
    'TileSideMarshland': ('M', '18M', 'Suppressed Memories'),
    'TileSideRitualSite': ('M', '18M', 'Suppressed Memories'),
    'TileSidePond': ('M', '19M', 'Suppressed Memories'),
    'TileSideTortureChamber': ('M', '19M', 'Suppressed Memories'),
    'TileSideOldForest': ('L', '1L', 'Suppressed Memories'),
    'TileSideWaterwheel': ('L', '1L', 'Suppressed Memories'),
    'TileSideBarn': ('L', '3L', 'Suppressed Memories'),
    'TileSideCoveredBridge': ('L', '3L', 'Suppressed Memories'),
    # ===== Beyond the Threshold (BtT) =====
    'TileSideBalcony': ('S', '33S', 'Beyond the Threshold'),
    'TileSideBasementStorage': ('S', '33S', 'Beyond the Threshold'),
    'TileSideEntryHallMAD23': ('S', '34S', 'Beyond the Threshold'),
    'TileSidePorch': ('S', '34S', 'Beyond the Threshold'),
    'TileSideDiningRoomMAD23': ('S', '35S', 'Beyond the Threshold'),
    'TileSideHallCorner': ('S', '35S', 'Beyond the Threshold'),
    'TileSideBedroom': ('S', '36S', 'Beyond the Threshold'),
    'TileSideKitchen': ('S', '36S', 'Beyond the Threshold'),
    'TileSideAtticStorage': ('S', '37S', 'Beyond the Threshold'),
    'TileSideLibraryMAD23': ('S', '37S', 'Beyond the Threshold'),
    'TileSideHallStairsMAD23': ('S', '38S', 'Beyond the Threshold'),
    'TileSideYard1MAD23': ('S', '38S', 'Beyond the Threshold'),
    # ===== Streets of Arkham (SoA) =====
    'TileSideCuriosityShop': ('S', '39S', 'Streets of Arkham'),
    'TileSideHallStairsMAD25': ('S', '39S', 'Streets of Arkham'),  # "Stairs" in the index; back of Curiosity Shop
    'TileSideMagicShop': ('S', '40S', 'Streets of Arkham'),
    'TileSideOfficeMAD25': ('S', '40S', 'Streets of Arkham'),
    'TileSideClassroom3': ('S', '41S', 'Streets of Arkham'),
    'TileSideLoungeMAD25': ('S', '41S', 'Streets of Arkham'),
    'TileSideClassroom2': ('S', '42S', 'Streets of Arkham'),
    'TileSideWarehouseMAD25': ('S', '42S', 'Streets of Arkham'),
    'TileSideAlley': ('S', '43S', 'Streets of Arkham'),
    'TileSideExhibit1': ('S', '43S', 'Streets of Arkham'),
    'TileSideBedroomMAD25': ('S', '44S', 'Streets of Arkham'),
    'TileSideYard2MAD25': ('S', '44S', 'Streets of Arkham'),
    'TileSideExhibit2': ('S', '45S', 'Streets of Arkham'),
    'TileSidePrintingPress': ('S', '45S', 'Streets of Arkham'),
    'TileSidePortraitHall': ('S', '46S', 'Streets of Arkham'),
    'TileSideSpeakeasy': ('S', '46S', 'Streets of Arkham'),
    'TileSideChapelMAD25': ('S', '47S', 'Streets of Arkham'),
    'TileSideSewer2': ('S', '47S', 'Streets of Arkham'),
    'TileSideResearchLibrary': ('S', '48S', 'Streets of Arkham'),
    'TileSideStreetCorner': ('S', '48S', 'Streets of Arkham'),
    'TileSideLibraryArchives': ('S', '49S', 'Streets of Arkham'),
    'TileSideSewer1': ('S', '49S', 'Streets of Arkham'),
    'TileSideExhibit3': ('M', '22M', 'Streets of Arkham'),
    'TileSideLobbyMAD25': ('M', '22M', 'Streets of Arkham'),
    'TileSideMainExhibit': ('M', '23M', 'Streets of Arkham'),
    'TileSideYard1MAD25': ('M', '23M', 'Streets of Arkham'),
    'TileSideBandstand': ('M', '24M', 'Streets of Arkham'),
    'TileSideLab': ('M', '24M', 'Streets of Arkham'),
    'TileSideGeneralShop': ('M', '25M', 'Streets of Arkham'),
    'TileSideStudio': ('M', '25M', 'Streets of Arkham'),
    'TileSideClassroom1': ('M', '26M', 'Streets of Arkham'),
    'TileSideLibraryMAD25': ('M', '26M', 'Streets of Arkham'),
    'TileSideDiner': ('L', '4L', 'Streets of Arkham'),
    'TileSideExhibitEntrance': ('L', '4L', 'Streets of Arkham'),
    # ===== Sanctum of Twilight (SoT) =====
    'TileSideCeremonyRoomMAD26': ('S', '50S', 'Sanctum of Twilight'),
    'TileSidePharmacy': ('S', '50S', 'Sanctum of Twilight'),
    'TileSideLoungeMAD26': ('S', '51S', 'Sanctum of Twilight'),
    'TileSideParadeFloat1': ('S', '51S', 'Sanctum of Twilight'),
    'TileSideInnerSanctum': ('S', '52S', 'Sanctum of Twilight'),
    'TileSideParadeFloat2': ('S', '52S', 'Sanctum of Twilight'),
    'TileSideStorageRoom': ('S', '53S', 'Sanctum of Twilight'),
    'TileSideVault': ('S', '53S', 'Sanctum of Twilight'),
    'TileSideCafe': ('M', '27M', 'Sanctum of Twilight'),
    'TileSideDungeonHall': ('M', '27M', 'Sanctum of Twilight'),
    # ===== Horrific Journeys (HJ) =====
    'TileSideFreightCar2': ('S', '54S', 'Horrific Journeys'),
    'TileSideStorageHold': ('S', '54S', 'Horrific Journeys'),
    'TileSideMedicalOffice': ('S', '55S', 'Horrific Journeys'),
    'TileSideObservationCar': ('S', '55S', 'Horrific Journeys'),
    'TileSideBaggageCar': ('S', '56S', 'Horrific Journeys'),
    'TileSideLifeBoat': ('S', '56S', 'Horrific Journeys'),
    'TileSideCrewBedroom': ('S', '57S', 'Horrific Journeys'),
    'TileSideTracks': ('S', '57S', 'Horrific Journeys'),
    'TileSideChartRoom': ('S', '58S', 'Horrific Journeys'),
    'TileSideDiningCar1': ('S', '58S', 'Horrific Journeys'),
    'TileSideCabin1': ('S', '59S', 'Horrific Journeys'),
    'TileSideLoungeCar': ('S', '59S', 'Horrific Journeys'),
    'TileSideCabin3': ('S', '60S', 'Horrific Journeys'),
    'TileSidePassengerCar2': ('S', '60S', 'Horrific Journeys'),
    'TileSidePassengerCar1': ('S', '61S', 'Horrific Journeys'),
    'TileSideSpa': ('S', '61S', 'Horrific Journeys'),
    'TileSideBridge': ('S', '62S', 'Horrific Journeys'),
    'TileSideSleeperCar': ('S', '62S', 'Horrific Journeys'),
    'TileSideEngine': ('S', '63S', 'Horrific Journeys'),
    'TileSideShipDeck3': ('S', '63S', 'Horrific Journeys'),
    'TileSideCarboose': ('S', '64S', 'Horrific Journeys'),
    'TileSideShipDeck4': ('S', '64S', 'Horrific Journeys'),
    'TileSideDiningCar2': ('S', '65S', 'Horrific Journeys'),
    'TileSideShipDeck6': ('S', '65S', 'Horrific Journeys'),
    'TileSideFreightCar1': ('S', '66S', 'Horrific Journeys'),
    'TileSideShipDeck5': ('S', '66S', 'Horrific Journeys'),
    'TileSideShipDeck2': ('S', '67S', 'Horrific Journeys'),
    'TileSideViewingRoom3': ('S', '67S', 'Horrific Journeys'),
    'TileSideShipDeck1': ('S', '68S', 'Horrific Journeys'),
    'TileSideViewingRoom1': ('S', '68S', 'Horrific Journeys'),
    'TileSideDiningRoomMAD27': ('M', '28M', 'Horrific Journeys'),
    'TileSidePool': ('M', '28M', 'Horrific Journeys'),
    'TileSideProw': ('M', '29M', 'Horrific Journeys'),
    'TileSideViewingRoom2': ('M', '29M', 'Horrific Journeys'),
    'TileSideEngineRoom': ('M', '30M', 'Horrific Journeys'),
    'TileSideStation': ('M', '30M', 'Horrific Journeys'),
    # ===== Path of the Serpent (PotS) =====
    'TileSideAltarChamber': ('S', '69S', 'Path of the Serpent'),
    'TileSideRiver1': ('S', '69S', 'Path of the Serpent'),
    'TileSideJungleRuins2': ('S', '70S', 'Path of the Serpent'),
    'TileSideStorageChamber': ('S', '70S', 'Path of the Serpent'),
    'TileSideClearing1': ('S', '71S', 'Path of the Serpent'),
    'TileSideVerdantChamber': ('S', '71S', 'Path of the Serpent'),
    'TileSideHallChamber1': ('S', '72S', 'Path of the Serpent'),
    'TileSideShrine': ('S', '72S', 'Path of the Serpent'),
    # 'TileSideCampsite' is also Path of the Serpent 73S, but a TileSide can only have one entry
    'TileSideHallChamber2': ('S', '73S', 'Path of the Serpent'),
    'TileSideAntechamber': ('S', '74S', 'Path of the Serpent'),
    'TileSideRiver2': ('S', '74S', 'Path of the Serpent'),
    'TileSideRavine': ('S', '75S', 'Path of the Serpent'),
    'TileSideTunnel': ('S', '75S', 'Path of the Serpent'),
    'TileSideBurialChamber': ('S', '76S', 'Path of the Serpent'),
    'TileSideOvergrownPath': ('S', '76S', 'Path of the Serpent'),
    'TileSideRiverCrossing': ('S', '77S', 'Path of the Serpent'),
    'TileSideRuinedChamber': ('S', '77S', 'Path of the Serpent'),
    'TileSideHollowGrove': ('S', '78S', 'Path of the Serpent'),
    'TileSideSunlitChamber': ('S', '78S', 'Path of the Serpent'),
    'TileSideBedChamber': ('S', '79S', 'Path of the Serpent'),
    'TileSideJungleRuins1': ('S', '79S', 'Path of the Serpent'),
    'TileSideRiverEdge': ('M', '31M', 'Path of the Serpent'),
    'TileSideThroneChamber': ('M', '31M', 'Path of the Serpent'),
    'TileSideRuinedHut': ('M', '32M', 'Path of the Serpent'),
    'TileSideStatueChamber': ('M', '32M', 'Path of the Serpent'),
    'TileSideCrackedChamber': ('M', '33M', 'Path of the Serpent'),
    'TileSideTempleStairs': ('M', '33M', 'Path of the Serpent'),
    'TileSideCrumblingPlaza': ('M', '34M', 'Path of the Serpent'),
    'TileSidePoolChamber': ('M', '34M', 'Path of the Serpent'),
    'TileSideMosaicChamber': ('M', '35M', 'Path of the Serpent'),
    'TileSideRopeBridge': ('M', '35M', 'Path of the Serpent'),
    'TileSideClearing2': ('M', '36M', 'Path of the Serpent'),
    'TileSidePit': ('M', '36M', 'Path of the Serpent'),
}

# Valkyrie uses one name for two different tiles: Campsite is 28 S in Call of the Wild (Suppressed Memories) and
# 73 S in Path of the Serpent. Which one a scenario means is decided from the expansions it lists (quest.ini packs=).
TILE_ALTERNATIVES: dict[str, dict[str, tuple[str, str, str]]] = {
    "TileSideCampsite": {"SM": ("S", "28S", "Suppressed Memories"), "PotS": ("S", "73S", "Path of the Serpent")},
}


def lookup_tile(side: str, packs: set[str] | None = None) -> tuple[str, str, str]:
    """Return (size, index, expansion). Exact TileSide match; for a side shared by two tiles, the one from an
    expansion the scenario uses (packs from quest.ini)."""
    alts = TILE_ALTERNATIVES.get(side)
    if alts and packs:
        for pack, info in alts.items():
            if pack in packs or (pack == "SM" and packs & {"CotWT", "CotWM", "CotWI", "FAT", "FAM", "FAI"}):
                return info
    if side in TILE_INFO:
        return TILE_INFO[side]
    return ("?", "", "Unknown")


def scenario_packs(scenario_dir: Path) -> set[str]:
    """Expansion ids the scenario lists in quest.ini (packs=SoA HJ ...)."""
    quest = scenario_dir / "quest.ini"
    if not quest.exists():
        return set()
    m = re.search(r"^packs\s*=\s*(.+)$", quest.read_text(encoding="utf-8", errors="ignore"), re.MULTILINE | re.IGNORECASE)
    return set(m.group(1).split()) if m else set()


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
        print(f" ✗ {src.name}: {e}")
        return False


def side_to_candidates(side: str, preferred_mad: str | None = None) -> list[str]:
    base = side.replace("TileSide", "")
    underscored = re.sub(r"([a-z])([A-Z])", r"\1_\2", base)
    # MAD01/MAD06/MAD09 are the first-edition, Forbidden Alchemy and Call of the Wild images
    mads = ["MAD20", "MAD01", "MAD06", "MAD09", "MAD21", "MAD22", "MAD23", "MAD25", "MAD26", "MAD27", "MAD28"]
    if preferred_mad and preferred_mad in mads:
        mads = [preferred_mad] + [m for m in mads if m != preferred_mad]

    cands: list[str] = []
    for mad in mads:
        cands.append(f"Tile_{base}_{mad}.dds")
        if underscored != base:
            cands.append(f"Tile_{underscored}_{mad}.dds")
        cands.append(f"TILE_{base.upper()}_{mad}.dds")
    cands.append(f"Tile_{base}.dds")
    return cands


def find_tile_image(side: str, expansion: str = "Unknown") -> Path | None:
    preferred_mad = EXP_TO_MAD.get(expansion)
    for name in side_to_candidates(side, preferred_mad):
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


def parse_tiles_ini(scenario_dir: Path) -> dict[str, str]:
    """Tile component -> TileSide, from every .ini in the scenario (most keep tiles in tiles.ini, some don't)."""
    mapping = {}
    for ini in ini_files(scenario_dir):
        current = None
        for line in ini.read_text(encoding="utf-8", errors="ignore").splitlines():
            m = re.match(r"^\[([^\]]+)\]", line)
            if m:
                current = m.group(1).strip()
                continue
            if current and line.strip().lower().startswith("side="):
                mapping[current] = line.split("=", 1)[1].strip()
    return mapping


def ini_files(scenario_dir: Path) -> list[Path]:
    """Every .ini in the scenario, including subfolders: some scenarios keep versions for different expansions in
    folders (all/, recurring/, ...), so the list covers anything any version might use."""
    return sorted(scenario_dir.rglob("*.ini"))


def parse_custom_monsters(scenario_dir: Path) -> dict[str, dict]:
    result = {}
    text = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in ini_files(scenario_dir))
    current = None
    for line in text.splitlines():
        m = re.match(r"^\[(CustomMonster[^\]]+)\]", line)
        if m:
            current = m.group(1).strip()
            result.setdefault(current, {})
            continue
        if line.startswith("["):
            current = None
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
    for ini in ini_files(scenario_dir):
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
    for ini in ini_files(scenario_dir):
        text = ini.read_text(encoding="utf-8", errors="ignore")
        # a spawn can list several monster types (the game picks one), so take them all
        for m in re.finditer(r"^monster\s*=\s*(.+)$", text, re.MULTILINE | re.IGNORECASE):
            for mon in m.group(1).split():
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
    base = re.sub(r"(MAD\d+|1E|FA)$", "", base)          # Valkyrie's expansion suffixes (ChapelMAD25, DiningRoom1E)
    return re.sub(r"([a-z])([A-Z0-9])", r"\1 \2", base)  # GuestBedroom -> Guest Bedroom, Yard2 -> Yard 2


def find_scenario_name(folder: Path) -> str:
    for loc_name in ("Localization.English.txt", "Localization.txt"):
        loc = folder / loc_name
        if not loc.exists():
            continue
        text = loc.read_text(encoding="utf-8", errors="ignore")
        for key in ("quest.name", "UISplashTitle", "name"):
            m = re.search(rf"^{re.escape(key)}\s*=\s*(.+)$", text, re.MULTILINE | re.IGNORECASE)
            if m:
                return m.group(1).strip().strip('"')
            m = re.search(rf"^{re.escape(key)}\s*,\s*(.+)$", text, re.MULTILINE | re.IGNORECASE)
            if m:
                return m.group(1).strip().strip('"')
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
    scenario_name = find_scenario_name(scenario_dir)
    print(f"\nBuilding packing list for: {scenario_name}")

    component_to_side = parse_tiles_ini(scenario_dir)
    if not component_to_side:
        print("No tiles found in this scenario")
        return
    packs = scenario_packs(scenario_dir)
    normal_comps, six_comps = collect_added_tiles(scenario_dir)
    real_monsters = collect_real_monsters(scenario_dir)

    print(f" Normal tiles : {len(normal_comps)}")
    print(f" 6-player tiles: {len(six_comps)}")
    print(f" Real monsters : {len(real_monsters)}")

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
            print(f" ✓ icon {fname}")
        else:
            print(f" ! missing {src_icon.name}")

    tile_cards = []
    for i, (side, is_six) in enumerate(sides, 1):
        size, index, exp = lookup_tile(side, packs)
        printed = nice_name(side)
        if index and len(index) >= 2 and index[-1] in "SML":
            size_label = f"{index[:-1]} {index[-1]}"  # e.g. "35 S"
        else:
            size_label = index if index else size

        # Image: prefer the MAD file for this expansion
        img_src = find_tile_image(side, exp)
        img_rel = None
        if img_src:
            dst = tiles_dir / f"{side}.png"
            if convert_any_image(img_src, dst):
                img_rel = f"tiles/{side}.png"
                print(f" ✓ tile {side} → {printed} [{size_label}] [{exp}]")
        else:
            print(f" ? no image for {side} ({printed}) [{size_label}] [{exp}]")

        tile_cards.append({
            "num": i,
            "printed": printed,
            "exp": exp,
            "size": size_label,
            "img": img_rel,
            "icon": icon_map.get(exp),
            "six": is_six,
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
                print(f" ✓ monster {real} → {printed}")
            else:
                print(f" ✗ convert failed {real}")
        else:
            print(f" ? no image for {real}")
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
Custom monsters are mapped to the physical base token you must pull from the box.<br>
Size labels match <em>Mansions of Madness Tiles Index v5.2</em>. Expansion icons match the physical product.</p>
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
    webbrowser.open(out.resolve().as_uri())
    print("Opened in browser.")


def main():
    scenarios = discover_scenarios()
    if not scenarios:
        print("No scenarios found.")
        print(f"Looked in: {EDITOR_DIR}")
        print(f" and: {DOWNLOAD_DIR}")
        sys.exit(1)

    print("Available scenarios:\n")
    for i, p in enumerate(scenarios, 1):
        if p.is_dir():
            name = find_scenario_name(p)
            print(f" {i:2d}. [Editor] {name} ({p.name})")
        else:
            print(f" {i:2d}. [Download] {p.stem}")
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
        if work is not None and work.exists():
            shutil.rmtree(work)
            print("Cleaned up temp_scenario/")


if __name__ == "__main__":
    main()