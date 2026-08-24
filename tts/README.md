# Valkyrie TTS

Generate spoken dialogue for **Mansions of Madness 2nd Edition** scenarios used with [Valkyrie](https://github.com/NPBruce/valkyrie).

The tool reads a scenario’s localization file, synthesizes speech for story text, mixes it with existing SFX when needed, and writes `audio=` entries into the scenario’s event/token definitions. You can package the result as a new `.valkyrie` for play.

---

## Features

- Interactive picker for scenarios in **Valkyrie Download** (and optional paths)
- Multiple TTS providers: **edge-tts** (free), **ElevenLabs** (paid API), **Kokoro** (local)
- Skips UI chrome, buttons, quest metadata, and very short strings
- Preserves existing scenario SFX: `SFX → short pause → TTS` when an event already has built-in audio
- Hash-based cache so unchanged lines are not regenerated
- Optional package to `.valkyrie` in Download
- Optional install into Editor as `<name>_TTS` (can be disabled / cleaned up after packaging)
- Preview a sample line before committing to a full scenario run

---

## What gets spoken (and what does not)

| Spoken | Not spoken |
|--------|------------|
| Scenario event `.text` lines (story, searches, clues, custom events) | UI labels, buttons, quest name/metadata |
| Token `.text` lines | Monster display names only |
| Lines long enough to be real dialogue | Very short crumbs (&lt; ~8 characters after cleaning) |
| | **Built-in / stock Mythos phase text** |

### Mythos caveat (important)

Many scenarios only **enable** Valkyrie’s shared Mythos system by setting variables such as `$mythosMinor`, `$mythosMajor`, `$mythosDeadly`, or `$mythosFlavor`. The narrative lines you see in the Mythos phase then come from the **official game localization**:

```text
%APPDATA%\Valkyrie\MoM\import\text\Localization_en.txt
```

(keys like `MYTHOS_EVENT_…`), not from the scenario’s `Localization.English.txt`.

Those stock events have **no** scenario `[Event…]` section with an `audio=` field, so this tool cannot attach TTS to them. You will still hear scenario-authored story and any **custom** mythos events the author wrote with real `.text` entries.

Stock mythos may play a short sting such as `Mythos_01.ogg`; that is not full narration.

---

## Prerequisites

### Software

| Requirement | Notes |
|-------------|--------|
| **Python 3.10+** | 3.11 / 3.12 recommended. Kokoro often needs **3.11–3.12** in a dedicated venv (not 3.14). |
| **ffmpeg** | On `PATH` — used to convert MP3 → OGG and to mix SFX + TTS |
| **edge-tts** | Default free provider: `pip install edge-tts` |
| **ElevenLabs** (optional) | Paid API; needs `ELEVENLABS_API_KEY` (or equivalent) in the environment |
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
cd C:\valkyrievoices\valkyrie-tools\tts   # or your clone path
pip install edge-tts
# ffmpeg must be installed system-wide and available in PATH
```

### Optional: ElevenLabs

```powershell
pip install requests   # if not already available
$env:ELEVENLABS_API_KEY = "your_key_here"
```

Use a provider flag such as `--provider elevenlabs` and a voice name the script knows (see `--list-voices`).

### Optional: Kokoro (local)

Kokoro is picky about Python version. A typical setup:

```powershell
py -3.12 -m venv C:\valkyrievoices\.venv-kokoro
# Activate (if execution policy blocks scripts, use the venv python path directly)
C:\valkyrievoices\.venv-kokoro\Scripts\python.exe -m pip install kokoro-tts soundfile

# Download models into the folder you run from (or pass --model / --voices):
#   kokoro-v1.0.onnx
#   voices-v1.0.bin
# from the kokoro-tts project releases
```

British male **Daniel** is often selected as `bm_daniel` with `en-gb`. Generation is CPU-bound and slower than edge-tts; caching still applies.

---

## Voices

List built-in voice labels:

```powershell
python valkyrie_tts.py --list-voices
```

Typical groups:

- **edge-tts** — free neural voices (e.g. Thomas, Guy, Aria, Sonia)
- **ElevenLabs** — higher quality, metered by character count (full scenarios can be expensive)
- **Kokoro** — free local; quality depends on voice; slower on CPU

Preview one line:

```powershell
python valkyrie_tts.py --preview --voice Thomas
# or another provider/voice your script supports
```

---

## Run

### Interactive (recommended)

```powershell
python valkyrie_tts.py --voice Thomas
```

(Exact flags depend on your script version: scenario picker from Download, then process.)

### Explicit scenario path

```powershell
python valkyrie_tts.py -s "$env:APPDATA\Valkyrie\Download\SomeScenario.valkyrie" --voice Thomas
```

### Useful options (as implemented in the script)

| Option | Purpose |
|--------|---------|
| `-s` / `--scenario` | Path to `.valkyrie` or extracted folder |
| `-o` / `--output` | Output `.valkyrie` path (e.g. under Download) |
| `--voice` | Voice label |
| `--provider` | `edge` / `elevenlabs` / `kokoro` (names as in your script) |
| `--dry-run` | Parse and list work without writing audio |
| `--force` | Regenerate even when cache/output exists |
| `--no-editor` | Do not install a copy under `MoM\Editor` |
| `--preview` | Speak a sample line only |
| `--list-voices` | Print known voices |
| `--pause` | Pause seconds between SFX and TTS when mixing |

After a successful run with packaging, prefer **one** final package under Download and avoid leaving a permanent `_TTS` Editor folder unless you are editing.

---

## Typical workflow

1. Download the scenario in Valkyrie (appears under `Download\*.valkyrie`).
2. Preview a voice: `python valkyrie_tts.py --preview --voice Thomas`.
3. Run TTS on that scenario; package to e.g. `ScenarioName_TTS.valkyrie` in Download.
4. In Valkyrie, play the `_TTS` package (or refresh the scenario list).
5. Expect **story/search/clue** lines to be voiced; expect **stock Mythos phase** lines to stay silent unless the author wrote custom mythos events.

---

## Output layout (conceptual)

Inside the working/packaged scenario:

```text
tts_audio/
  EventSomeName.ogg
  TokenSomeName.ogg
  ...
events.ini      # audio=tts_audio/... added or updated
tokens.ini
Localization.English.txt
...
```

Cached intermediates may live under a temp/cache directory so re-runs are faster.

---

## Troubleshooting

| Problem | Check |
|---------|--------|
| No scenarios listed | Files under `%APPDATA%\Valkyrie\Download\` |
| `edge-tts` / import errors | `pip install edge-tts`; network allowed for Microsoft voices |
| ffmpeg errors | Install ffmpeg; confirm `ffmpeg -version` in the same shell |
| Kokoro missing models | Place `kokoro-v1.0.onnx` and `voices-v1.0.bin` where the CLI expects them |
| Kokoro won’t install | Use Python 3.11–3.12 venv, not 3.14 |
| ElevenLabs failures | API key, quota, character budget for large scenarios |
| Mythos phase still silent | Expected for stock `$mythos*` pool — see Mythos caveat above |
| Duplicate Editor + Download copies | Use `--no-editor` or clean Editor `_TTS` folders after packaging |

---

## Character cost (ElevenLabs)

Full scenarios can be **100k+** characters of dialogue after cleaning. At typical ElevenLabs rates that is often impractical compared to free edge-tts or local Kokoro. Prefer edge-tts or Kokoro for whole campaigns; use ElevenLabs for short tests if desired.

---

## License / credits

- Scenario format and runtime: [Valkyrie](https://github.com/NPBruce/valkyrie)
- Game text and assets remain subject to Fantasy Flight / publisher terms; this tool only processes **local** Valkyrie data you already imported
- TTS engines: edge-tts, ElevenLabs, Kokoro (each under their own licenses and terms)
- Stock Mythos dialogue lives in official import localization and is not rewritten by this tool
```
