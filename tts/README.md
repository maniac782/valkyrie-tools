# Valkyrie TTS

Generate spoken dialogue for **Mansions of Madness 2nd Edition** scenarios used with [Valkyrie](https://github.com/NPBruce/valkyrie).

The tool reads a scenario’s localization file, synthesizes speech for story text, mixes it with existing SFX when needed, and writes `audio=` entries into the scenario’s event/token definitions. It packages the result as a new `.valkyrie` under **Download**.

By default the **display name (`quest.name`) is left unchanged**, so end-of-run win/loss and feedback should attach to the **original scenario** in Valkyrie’s stats. The file on disk is still named `*_TTS.valkyrie` so you can tell the voiced pack from the stock file.

---

## Features

- Interactive picker for scenarios in **Valkyrie Download**
- Multiple TTS providers: **edge-tts** (free, default), **ElevenLabs** (paid API), **Kokoro** (local)
- Skips UI chrome, buttons, quest metadata, and very short strings
- Preserves existing scenario SFX: `SFX → short pause → TTS` when an event already has built-in audio
- Hash-based cache so unchanged lines are not regenerated
- Packages to `%APPDATA%\Valkyrie\Download\<name>_TTS.valkyrie`
- **Keeps original `quest.name`** by default (stats stay on the original scenario)
- Cleans up any leftover Editor `_TTS` folders after packaging
- Preview a sample line before committing to a full scenario run

---

## What gets spoken (and what does not)

| Spoken | Not spoken |
|--------|------------|
| Scenario event `.text` lines (story, searches, clues, custom events) | UI labels, buttons, quest name/metadata |
| Token `.text` lines | Monster display names only |
| Custom monster events that have real `.text` in the scenario | Very short crumbs (&lt; ~8 characters after cleaning) |
| | **Built-in / stock Mythos phase text** |
| | **Stock monster attack / horror / evade lines** from the import pool |

### Mythos caveat (important)

Many scenarios only **enable** Valkyrie’s shared Mythos system by setting variables such as `$mythosMinor`, `$mythosMajor`, `$mythosDeadly`, or `$mythosFlavor`. The narrative lines you see in the Mythos phase then come from the **official game localization**:

```text
%APPDATA%\Valkyrie\MoM\import\text\Localization_en.txt
```

(keys like `MYTHOS_EVENT_…`), not from the scenario’s `Localization.English.txt`.

Those stock events have **no** scenario `[Event…]` section with an `audio=` field, so this tool cannot attach TTS to them. You will still hear scenario-authored story and any **custom** mythos events the author wrote with real `.text` entries.

Stock mythos may play a short sting such as `Mythos_01.ogg`; that is not full narration.

### Stock combat lines

Standard monster attack, horror, and evade text (`MONSTER_*_ATTACK_*`, etc.) also lives in the import localization and is selected by the engine at runtime. Same limitation: no scenario `audio=` slot to wire. Custom fight events that exist as scenario events with `.text` **are** voiced.

---

## Scenario name and statistics

| Setting | In-game / stats name | File on disk |
|---------|----------------------|--------------|
| **Default** (`--title-suffix` empty) | Original scenario name | `Download\<name>_TTS.valkyrie` |
| `--title-suffix " TTS"` | `Original TTS` | same |

- **Default:** win/loss and feedback should report under the **original** scenario identity.
- If both the stock and `_TTS` packs are installed, they can show the **same title** in the list — pick the `_TTS` file when you want voice.
- Use `--title-suffix " TTS"` only if you want a distinct menu label (stats then go to a separate “TTS” entry).

---

## Prerequisites

### Software

| Requirement | Notes |
|-------------|--------|
| **Python 3.10+** | 3.11 / 3.12 recommended. Kokoro often needs **3.11–3.12** in a dedicated venv (not 3.14). |
| **ffmpeg** | On `PATH` — used to convert audio to OGG and to mix SFX + TTS |
| **edge-tts** | Default free provider: `pip install edge-tts` |
| **ElevenLabs** (optional) | Paid API; needs `ELEVENLABS_API_KEY` in the environment |
| **Kokoro** (optional) | Local ONNX voices; separate venv + model files (see below) |
| **Valkyrie** | Installed and used at least once so AppData paths exist |

### Valkyrie data

1. Download / subscribe to scenarios in Valkyrie  
   (`%APPDATA%\Valkyrie\Download\*.valkyrie`).
2. Official content should already be imported (for built-in SFX under  
   `%APPDATA%\Valkyrie\MoM\import\audio\`).

The TTS tool does **not** download scenarios or game content.

---

## Install

```powershell
cd path\to\valkyrie-tools\tts
pip install edge-tts
# ffmpeg must be installed system-wide and available in PATH
```

### Optional: ElevenLabs

```powershell
$env:ELEVENLABS_API_KEY = "your_key_here"
```

```powershell
python valkyrie_tts.py --provider elevenlabs --voice Adam --preview
```

### Optional: Kokoro (local)

Kokoro is picky about Python version. Models must sit next to the script (or adjust paths in the script):

```powershell
py -3.12 -m venv .venv-kokoro
# If execution policy blocks Activate.ps1, call the venv python directly:
.\.venv-kokoro\Scripts\python.exe -m pip install kokoro-tts soundfile
```

Download into the `tts` folder (same directory as `valkyrie_tts.py`):

- [kokoro-v1.0.onnx](https://github.com/nazdridoy/kokoro-tts/releases/download/v1.0.0/kokoro-v1.0.onnx)
- [voices-v1.0.bin](https://github.com/nazdridoy/kokoro-tts/releases/download/v1.0.0/voices-v1.0.bin)

British male **Daniel** (`bm_daniel`, `en-gb`) is a good default. Generation is CPU-bound and slower than edge-tts; caching still applies.

```powershell
python valkyrie_tts.py --provider kokoro --voice bm_daniel --preview
```

---

## Voices

```powershell
python valkyrie_tts.py --list-voices
```

| Provider | Notes | Default voice |
|----------|--------|----------------|
| **edge** | Free neural voices (Thomas, Guy, Aria, Sonia, …) | `Thomas` |
| **elevenlabs** | Higher quality; metered by character count | `Adam` |
| **kokoro** | Free local; slower on CPU | `bm_daniel` |

Preview one line:

```powershell
python valkyrie_tts.py --preview --voice Thomas
python valkyrie_tts.py --preview --provider kokoro --voice bm_daniel
```

---

## Run

### Interactive (recommended)

```powershell
python valkyrie_tts.py
# or with an explicit voice / provider:
python valkyrie_tts.py --provider edge --voice Thomas
python valkyrie_tts.py --provider kokoro --voice bm_daniel
```

You get a numbered list of `%APPDATA%\Valkyrie\Download\*.valkyrie` files. Pick one; the tool generates audio and writes `Download\<name>_TTS.valkyrie`.

### Explicit scenario path

```powershell
python valkyrie_tts.py -s "$env:APPDATA\Valkyrie\Download\SomeScenario.valkyrie" --voice Thomas
```

### Options

| Option | Purpose |
|--------|---------|
| `-s` / `--scenario` | Path to `.valkyrie` (optional — interactive picker if omitted) |
| `-o` / `--output` | Output `.valkyrie` path (default: `Download\<name>_TTS.valkyrie`) |
| `--provider` | `edge` (default), `elevenlabs`, or `kokoro` |
| `--voice` | Voice label (defaults depend on provider) |
| `--dry-run` | Parse and list work without writing audio |
| `--force` | Regenerate even when cache/output exists |
| `--preview` | Speak a sample line only |
| `--list-voices` | Print known voices |
| `--pause` | Seconds of silence between SFX and TTS when mixing (default `0.25`) |
| `--import-audio` | Override path to Valkyrie import audio folder |
| `--title-suffix` | Append to `quest.name` (default **empty** so stats stay on original). Use `" TTS"` for a distinct menu name. |

---

## Typical workflow

1. Download the scenario in Valkyrie (`Download\*.valkyrie`).
2. Preview a voice: `python valkyrie_tts.py --preview --voice Thomas`.
3. Run TTS (interactive or `-s`); output lands as `Download\ScenarioName_TTS.valkyrie`.
4. In Valkyrie, play the `_TTS` package (refresh the list if needed).
5. Expect **story / search / clue** lines to be voiced.
6. Expect **stock Mythos** and **stock combat** lines to stay silent unless the author wrote custom events with `.text`.
7. At the end of the run, win/loss should report under the **original scenario name** (unless you used `--title-suffix`).

---

## Output layout (conceptual)

Inside the packaged scenario:

```text
tts_audio/
  EventSomeName.ogg
  TokenSomeName.ogg
  ...
events.ini               # audio=tts_audio/... added or updated
tokens.ini
Localization.English.txt # quest.name unchanged by default
...
```

Cache lives under the system temp folder (`valkyrie_tts_cache`) so re-runs are faster.

---

## Troubleshooting

| Problem | Check |
|---------|--------|
| No scenarios listed | Files under `%APPDATA%\Valkyrie\Download\` |
| `edge-tts` / import errors | `pip install edge-tts`; network allowed for Microsoft voices |
| ffmpeg errors | Install ffmpeg; confirm `ffmpeg -version` in the same shell |
| Kokoro missing models | Place `kokoro-v1.0.onnx` and `voices-v1.0.bin` next to the script |
| Kokoro won’t install | Use a Python **3.11–3.12** venv, not 3.14 |
| ElevenLabs failures | API key, quota, character budget for large scenarios |
| Mythos phase still silent | Expected for stock `$mythos*` pool — see Mythos caveat |
| Combat lines silent | Expected for stock `MONSTER_*` pool; custom events with `.text` should speak |
| Two scenarios with the same title | Default keeps `quest.name`; pick the `*_TTS.valkyrie` file for voice |
| Want a distinct menu name | `--title-suffix " TTS"` (stats then go to a separate entry) |

---

## Character cost (ElevenLabs)

Full scenarios can be **100k+** characters of dialogue after cleaning. At typical ElevenLabs rates that is often impractical compared to free edge-tts or local Kokoro. Prefer edge-tts or Kokoro for whole campaigns; use ElevenLabs for short tests if desired.

---

## License / credits

- Scenario format and runtime: [Valkyrie](https://github.com/NPBruce/valkyrie)
- Game text and assets remain subject to Fantasy Flight / publisher terms; this tool only processes **local** Valkyrie data you already imported
- TTS engines: edge-tts, ElevenLabs, Kokoro (each under their own licenses and terms)
- Stock Mythos and stock combat dialogue live in official import localization and are not rewritten by this tool
