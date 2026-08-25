# Valkyrie TTS

Generate spoken dialogue for **Mansions of Madness 2nd Edition** scenarios used with [Valkyrie](https://github.com/NPBruce/valkyrie).

The tool reads a scenario’s localization file, synthesizes speech for story text, mixes it with existing SFX when needed, and writes `audio=` entries into the scenario’s event/token definitions.

**By default it replaces the chosen `.valkyrie` in place** (same filename). The display name (`quest.name`) is left unchanged so win/loss and feedback stay on the **original scenario**. You do not end up with two copies in Download.

---

## Features

- Interactive picker for scenarios in **Valkyrie Download**
- Multiple TTS providers: **edge-tts** (free, default), **ElevenLabs** (paid API), **Kokoro** (local)
- Skips UI chrome, buttons, quest metadata, and very short strings
- Preserves existing scenario SFX: `SFX → short pause → TTS` when an event already has built-in audio
- Hash-based cache so unchanged lines are not regenerated
- **Overwrites the source `.valkyrie` in place** (no separate `*_TTS` twin)
- **Keeps original `quest.name`** (stats stay on the original scenario)
- Removes any leftover `*_TTS.valkyrie` twin and Editor `_TTS` folders
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

## Scenario name, files, and statistics

| | Default behavior |
|--|------------------|
| File | **Replaces** the chosen `Download\Scenario.valkyrie` in place |
| `quest.name` | Unchanged → stats report as the original scenario |
| Old `*_TTS.valkyrie` twin | Deleted if still present |
| Optional `-o path` | Write somewhere else instead of overwriting |

**Warning:** in-place replace is destructive for that file. Re-download the scenario from Valkyrie if you need a silent stock copy again.

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
python valkyrie_tts.py --provider elevenlabs --voice Adam --preview
```

### Optional: Kokoro (local)

```powershell
py -3.12 -m venv .venv-kokoro
.\.venv-kokoro\Scripts\python.exe -m pip install kokoro-tts soundfile
```

Download into the `tts` folder (next to `valkyrie_tts.py`):

- [kokoro-v1.0.onnx](https://github.com/nazdridoy/kokoro-tts/releases/download/v1.0.0/kokoro-v1.0.onnx)
- [voices-v1.0.bin](https://github.com/nazdridoy/kokoro-tts/releases/download/v1.0.0/voices-v1.0.bin)

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

---

## Run

### Interactive (recommended)

```powershell
python valkyrie_tts.py --provider kokoro --voice bm_daniel
```

Pick a numbered scenario from Download. When finished, **that same file** is the voiced version.

### Explicit path

```powershell
python valkyrie_tts.py -s "$env:APPDATA\Valkyrie\Download\SomeScenario.valkyrie" --provider kokoro --voice bm_daniel
```

### Options

| Option | Purpose |
|--------|---------|
| `-s` / `--scenario` | Path to `.valkyrie` (optional — interactive picker if omitted) |
| `-o` / `--output` | Write to another path instead of overwriting the source |
| `--provider` | `edge` (default), `elevenlabs`, or `kokoro` |
| `--voice` | Voice label (defaults depend on provider) |
| `--dry-run` | Parse and list work without writing audio |
| `--force` | Regenerate even when cache/output exists |
| `--preview` | Speak a sample line only |
| `--list-voices` | Print known voices |
| `--pause` | Seconds of silence between SFX and TTS when mixing (default `0.25`) |
| `--import-audio` | Override path to Valkyrie import audio folder |
| `--title-suffix` | Append to `quest.name` (default empty). Rarely needed now that the file is replaced in place. |

---

## Typical workflow

1. Download the scenario in Valkyrie.
2. Preview: `python valkyrie_tts.py --preview --provider kokoro --voice bm_daniel`
3. Run TTS on that scenario (interactive or `-s`).
4. The original Download file is replaced with the voiced package.
5. Play it in Valkyrie like the stock scenario (same name).
6. Story/search/clue lines speak; stock Mythos and stock combat lines do not.
7. Win/loss reports under the original scenario name.

---

## Troubleshooting

| Problem | Check |
|---------|--------|
| No scenarios listed | Files under `%APPDATA%\Valkyrie\Download\` |
| `edge-tts` errors | `pip install edge-tts`; network for Microsoft voices |
| ffmpeg errors | Install ffmpeg; `ffmpeg -version` in the same shell |
| Kokoro missing models | `kokoro-v1.0.onnx` + `voices-v1.0.bin` next to the script |
| Kokoro won’t install | Python **3.11–3.12** venv, not 3.14 |
| Mythos / combat still silent | Expected for stock pools — see caveats above |
| Need a silent copy again | Re-download the scenario in Valkyrie |

---

## Character cost (ElevenLabs)

Full scenarios can be **100k+** characters. Prefer edge-tts or Kokoro for whole campaigns.

---

## License / credits

- Scenario format and runtime: [Valkyrie](https://github.com/NPBruce/valkyrie)
- Game text and assets remain subject to Fantasy Flight / publisher terms; this tool only processes **local** Valkyrie data you already imported
- TTS engines: edge-tts, ElevenLabs, Kokoro (each under their own licenses and terms)
- Stock Mythos and stock combat dialogue live in official import localization and are not rewritten by this tool
