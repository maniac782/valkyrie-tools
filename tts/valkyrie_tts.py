#!/usr/bin/env python3
"""
valkyrie_tts.py
---------------
Generate TTS dialogue for Valkyrie (Mansions of Madness) scenarios.

Providers:
  - edge      (free, default)
  - elevenlabs (paid)
  - kokoro    (free, local — uses the 3.12 venv + bm_daniel by default)

Interactive picker of Download scenarios.
Packages only to Download\\<name>_TTS.valkyrie
Cleans up Editor leftovers automatically.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
KOKORO_VENV = SCRIPT_DIR / ".venv-kokoro"
KOKORO_EXE = KOKORO_VENV / "Scripts" / "kokoro-tts.exe"
KOKORO_MODEL = SCRIPT_DIR / "kokoro-v1.0.onnx"
KOKORO_VOICES = SCRIPT_DIR / "voices-v1.0.bin"

EDGE_VOICES = {
    "Christopher": "en-US-ChristopherNeural",
    "Guy": "en-US-GuyNeural",
    "Davis": "en-US-DavisNeural",
    "Brian": "en-US-BrianNeural",
    "Roger": "en-US-RogerNeural",
    "Ryan": "en-GB-RyanNeural",
    "Thomas": "en-GB-ThomasNeural",
    "Jenny": "en-US-JennyNeural",
    "Aria": "en-US-AriaNeural",
    "Michelle": "en-US-MichelleNeural",
    "Sonia": "en-GB-SoniaNeural",
    "William": "en-AU-WilliamNeural",
}

ELEVEN_VOICES = {
    "Adam": "pNInz6obpgDQGcFmaJgB",
    "Antoni": "ErXwobaYiN019PkySvjV",
    "Arnold": "VR6AewLTigWG4xSOukaG",
    "Bella": "EXAVITQu4vr4xnSDxMaL",
    "Domi": "AZnzlk1XvdvUeBnXmlld",
    "Elli": "MF3mGyEYCl7XYWbV9V6O",
    "Josh": "TxGEqnHWrfWFTfGW9XjX",
    "Rachel": "21m00Tcm4TlvDq8ikWAM",
    "Sam": "yoZ06aMxZJJ28mfd3POQ",
}

# Kokoro voice short names (pass through as-is)
KOKORO_VOICES_LIST = {
    "daniel": "bm_daniel",
    "bm_daniel": "bm_daniel",
    "george": "bm_george",
    "bm_george": "bm_george",
    "emma": "bf_emma",
    "bf_emma": "bf_emma",
    "bella": "af_bella",
    "af_bella": "af_bella",
    "heart": "af_heart",
    "af_heart": "af_heart",
    "michael": "am_michael",
    "am_michael": "am_michael",
    "adam": "am_adam",
    "am_adam": "am_adam",
}

SKIP_KEY_PATTERNS = [
    re.compile(r"^quest\.", re.I),
    re.compile(r"^ui", re.I),
    re.compile(r"\.button\d*$", re.I),
    re.compile(r"\.monstername$", re.I),
    re.compile(r"opening|closing|prologue|epilogue|credits", re.I),
]

PLACEHOLDER_RE = re.compile(
    r"\{(?:c:|var:|rnd:|action|observation|strength|will|lore|influence|clue)[^}]*\}",
    re.I,
)
TAG_RE = re.compile(r"</?[bi]>")
WHITESPACE_RE = re.compile(r"\s+")


def log(msg: str) -> None:
    print(f"[valkyrie-tts] {msg}")


def die(msg: str, code: int = 1) -> None:
    log(f"ERROR: {msg}")
    sys.exit(code)


def appdata_path() -> Path:
    return Path(os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming"))


def download_dir() -> Path:
    return appdata_path() / "Valkyrie" / "Download"


def editor_dir() -> Path:
    return appdata_path() / "Valkyrie" / "MoM" / "Editor"


def clean_text_for_tts(text: str) -> str:
    text = text.replace("\\n", " ").replace("\n", " ")
    text = TAG_RE.sub("", text)
    text = PLACEHOLDER_RE.sub("", text)
    text = text.replace("{", "").replace("}", "")
    text = WHITESPACE_RE.sub(" ", text).strip()
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        text = text[1:-1].strip()
    return text


def should_skip_key(key: str) -> bool:
    return any(p.search(key) for p in SKIP_KEY_PATTERNS)


def event_name_from_key(key: str) -> Optional[str]:
    if not key.endswith(".text"):
        return None
    return key[: -len(".text")]


def parse_localization(path: Path) -> Dict[str, str]:
    result: Dict[str, str] = {}
    if not path.exists():
        return result
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith(";") or "," not in line:
            continue
        key, _, value = line.partition(",")
        key = key.strip()
        if should_skip_key(key):
            continue
        name = event_name_from_key(key)
        if not name:
            continue
        cleaned = clean_text_for_tts(value)
        if len(cleaned) < 8:
            continue
        result[name] = cleaned
    return result


def find_section_spans(content: str) -> List[Tuple[str, int, int]]:
    spans: List[Tuple[str, int, int]] = []
    matches = list(re.finditer(r"^\[([^\]]+)\]\s*$", content, re.M))
    for i, m in enumerate(matches):
        name = m.group(1)
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        spans.append((name, start, end))
    return spans


def section_has_audio(section_body: str) -> Optional[str]:
    m = re.search(r"^audio\s*=\s*(.+)\s*$", section_body, re.M | re.I)
    return m.group(1).strip() if m else None


def set_section_audio(content: str, section_name: str, audio_value: str) -> str:
    spans = find_section_spans(content)
    for name, start, end in spans:
        if name != section_name:
            continue
        body = content[start:end]
        header_end = body.find("\n")
        if header_end < 0:
            new_body = body.rstrip() + f"\naudio={audio_value}\n"
        else:
            if section_has_audio(body) is not None:
                new_body = re.sub(
                    r"^audio\s*=\s*.*$",
                    f"audio={audio_value}",
                    body,
                    count=1,
                    flags=re.M | re.I,
                )
            else:
                new_body = body[: header_end + 1] + f"audio={audio_value}\n" + body[header_end + 1 :]
        return content[:start] + new_body + content[end:]
    return content


def default_import_audio_dir() -> Path:
    return appdata_path() / "Valkyrie" / "MoM" / "import" / "audio"


def resolve_builtin_sfx(audio_name: str, import_dir: Path) -> Optional[Path]:
    if not import_dir.exists():
        return None
    name = audio_name.strip()
    if name.lower().endswith(".ogg"):
        candidate = import_dir / Path(name).name
        return candidate if candidate.exists() else None
    core = re.sub(r"^Audio", "", name, flags=re.I)
    m = re.match(r"^([A-Za-z_]+?)(\d*)$", core)
    if not m:
        return None
    base, num = m.group(1), m.group(2)
    candidates: List[str] = []
    if num:
        n = int(num)
        candidates += [
            f"{base}_{n:02d}.ogg",
            f"{base}_{n}.ogg",
            f"{base}{n}.ogg",
            f"{base}_{n:02d}_000002.ogg",
        ]
    candidates += [
        f"{base}_01.ogg",
        f"{base}_1.ogg",
        f"{base}.ogg",
        f"{base}_01_000002.ogg",
        f"{core}.ogg",
    ]
    lower_map = {p.name.lower(): p for p in import_dir.glob("*.ogg")}
    for c in candidates:
        hit = lower_map.get(c.lower())
        if hit:
            return hit
    for fname, path in lower_map.items():
        if fname.startswith(base.lower()):
            return path
    return None


def safe_filename(name: str) -> str:
    return re.sub(r"[^\w.\-]+", "_", name)[:120]


def cache_path(cache_dir: Path, text: str, voice: str) -> Path:
    h = hashlib.sha1(f"{voice}|{text}".encode("utf-8")).hexdigest()[:16]
    return cache_dir / f"{h}.ogg"


# ---------------------------------------------------------------------------
# TTS backends
# ---------------------------------------------------------------------------
async def generate_edge_tts(text: str, voice_id: str, out_mp3: Path) -> None:
    import edge_tts
    await edge_tts.Communicate(text, voice_id).save(str(out_mp3))


def generate_elevenlabs_tts(text: str, voice_id: str, out_mp3: Path) -> None:
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY environment variable not set")
    import urllib.request
    import json

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    payload = json.dumps({"text": text, "model_id": "eleven_multilingual_v2"}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        out_mp3.write_bytes(resp.read())


def generate_kokoro_tts(text: str, voice: str, out_wav: Path) -> None:
    """Call the 3.12 venv kokoro-tts CLI."""
    if not KOKORO_EXE.exists():
        raise RuntimeError(
            f"Kokoro not found at {KOKORO_EXE}\n"
            "Create the venv and install:  py -3.12 -m venv .venv-kokoro && "
            ".venv-kokoro\\Scripts\\python.exe -m pip install kokoro-tts soundfile"
        )
    if not KOKORO_MODEL.exists() or not KOKORO_VOICES.exists():
        raise RuntimeError(
            f"Missing model files.\n"
            f"Expected:\n  {KOKORO_MODEL}\n  {KOKORO_VOICES}\n"
            "Download from:\n"
            "  https://github.com/nazdridoy/kokoro-tts/releases/download/v1.0.0/kokoro-v1.0.onnx\n"
            "  https://github.com/nazdridoy/kokoro-tts/releases/download/v1.0.0/voices-v1.0.bin"
        )

    # lang from voice prefix
    lang = "en-gb" if voice.startswith("b") else "en-us"

    cmd = [
        str(KOKORO_EXE),
        "-",                      # stdin
        str(out_wav),
        "--voice", voice,
        "--lang", lang,
        "--model", str(KOKORO_MODEL),
        "--voices", str(KOKORO_VOICES),
    ]
    proc = subprocess.run(
        cmd,
        input=text.encode("utf-8"),
        capture_output=True,
    )
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", errors="replace")
        raise RuntimeError(f"kokoro-tts failed: {err}")


def ffmpeg_to_ogg(src: Path, dst: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(src), "-c:a", "libvorbis", "-q:a", "4", str(dst)],
        check=True,
        capture_output=True,
    )


def make_silence_wav(path: Path, seconds: float = 0.25) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
            "-t", str(seconds), str(path),
        ],
        check=True,
        capture_output=True,
    )


def mix_sfx_pause_tts(sfx: Path, tts_audio: Path, out_ogg: Path, pause: float = 0.25) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_p = Path(tmp)
        sfx_wav = tmp_p / "sfx.wav"
        tts_wav = tmp_p / "tts.wav"
        silence = tmp_p / "silence.wav"
        combined = tmp_p / "combined.wav"
        list_file = tmp_p / "list.txt"
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(sfx), "-ar", "44100", "-ac", "1", str(sfx_wav)],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(tts_audio), "-ar", "44100", "-ac", "1", str(tts_wav)],
            check=True, capture_output=True,
        )
        make_silence_wav(silence, pause)
        list_file.write_text(
            f"file '{sfx_wav.as_posix()}'\n"
            f"file '{silence.as_posix()}'\n"
            f"file '{tts_wav.as_posix()}'\n",
            encoding="utf-8",
        )
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
             "-c", "copy", str(combined)],
            check=True, capture_output=True,
        )
        ffmpeg_to_ogg(combined, out_ogg)


async def produce_audio(
    text: str,
    provider: str,
    voice_id: str,
    out_ogg: Path,
    sfx: Optional[Path] = None,
    pause: float = 0.25,
) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_p = Path(tmp)
        if provider == "kokoro":
            wav = tmp_p / "tts.wav"
            generate_kokoro_tts(text, voice_id, wav)
            tts_src = wav
        else:
            mp3 = tmp_p / "tts.mp3"
            if provider == "edge":
                await generate_edge_tts(text, voice_id, mp3)
            else:
                generate_elevenlabs_tts(text, voice_id, mp3)
            tts_src = mp3

        if sfx and sfx.exists():
            mix_sfx_pause_tts(sfx, tts_src, out_ogg, pause=pause)
        else:
            ffmpeg_to_ogg(tts_src, out_ogg)


# ---------------------------------------------------------------------------
# Scenario I/O
# ---------------------------------------------------------------------------
def unpack_scenario(src: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest)
        return
    with zipfile.ZipFile(src, "r") as zf:
        zf.extractall(dest)


def pack_scenario(folder: Path, out_valkyrie: Path) -> None:
    out_valkyrie.parent.mkdir(parents=True, exist_ok=True)
    if out_valkyrie.exists():
        out_valkyrie.unlink()
    with zipfile.ZipFile(out_valkyrie, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in folder.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(folder).as_posix())


def rename_scenario_title(work: Path, suffix: str = " TTS") -> str:
    new_name = ""
    for loc in work.glob("Localization*.txt"):
        text = loc.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        out_lines: List[str] = []
        for line in lines:
            if line.startswith("quest.name,"):
                _, _, val = line.partition(",")
                val = val.strip()
                if not val.endswith(suffix):
                    val_clean = re.sub(r"\s*\(V[\d.]+\)\s*$", "", val).rstrip()
                    val = f"{val_clean}{suffix}"
                out_lines.append(f"quest.name,{val}")
                if "English" in loc.name or not new_name:
                    new_name = val
            elif line.startswith("UISplashTitle.uitext,"):
                _, _, val = line.partition(",")
                val = val.strip()
                if not val.endswith(suffix):
                    val_clean = re.sub(r"\s*\(V[\d.]+\)\s*$", "", val).rstrip()
                    val = f"{val_clean}{suffix}"
                out_lines.append(f"UISplashTitle.uitext,{val}")
            else:
                out_lines.append(line)
        loc.write_text(
            "\n".join(out_lines) + ("\n" if text.endswith("\n") else ""),
            encoding="utf-8",
        )
    return new_name or f"Scenario{suffix}"


def discover_download_scenarios() -> List[Path]:
    d = download_dir()
    if not d.exists():
        return []
    return sorted(d.glob("*.valkyrie"))


def interactive_pick_scenario() -> Path:
    scenarios = discover_download_scenarios()
    if not scenarios:
        die(f"No .valkyrie files found in {download_dir()}")

    print("\nAvailable scenarios in Download:\n")
    for i, p in enumerate(scenarios, 1):
        size_mb = p.stat().st_size / (1024 * 1024)
        print(f"  {i:2d}. {p.stem}  ({size_mb:.1f} MB)")

    print()
    while True:
        try:
            choice = input("Enter number (or q to quit): ").strip()
            if choice.lower() in ("q", "quit", "exit"):
                print("Bye.")
                sys.exit(0)
            idx = int(choice)
            if 1 <= idx <= len(scenarios):
                return scenarios[idx - 1]
            print(f"Please enter a number between 1 and {len(scenarios)}")
        except ValueError:
            print("Please enter a number")


def process_scenario(
    scenario: Path,
    provider: str,
    voice_name: str,
    voice_id: str,
    dry_run: bool = False,
    force: bool = False,
    pause: float = 0.25,
    import_audio_dir: Optional[Path] = None,
    output: Optional[Path] = None,
    title_suffix: str = " TTS",
) -> None:
    import_audio_dir = import_audio_dir or default_import_audio_dir()
    tmp_root = Path(tempfile.mkdtemp(prefix="valkyrie_tts_"))
    work = tmp_root / "scenario"
    log(f"Working in: {tmp_root}")

    try:
        log(f"Unpacking: {scenario}")
        unpack_scenario(scenario, work)

        loc = work / "Localization.English.txt"
        if not loc.exists():
            locs = list(work.glob("Localization*.txt"))
            if not locs:
                die("No Localization.English.txt found in scenario")
            loc = locs[0]
            log(f"Using localization: {loc.name}")

        dialogue = parse_localization(loc)
        log(f"Parsed {len(dialogue)} dialogue entries from {loc.name}")

        events_path = work / "events.ini"
        tokens_path = work / "tokens.ini"
        events_content = events_path.read_text(encoding="utf-8", errors="replace") if events_path.exists() else ""
        tokens_content = tokens_path.read_text(encoding="utf-8", errors="replace") if tokens_path.exists() else ""

        event_spans = {n: (s, e) for n, s, e in find_section_spans(events_content)}
        token_spans = {n: (s, e) for n, s, e in find_section_spans(tokens_content)}
        log(f"Found {len(event_spans)} events, {len(token_spans)} tokens")

        audio_dir = work / "tts_audio"
        audio_dir.mkdir(exist_ok=True)
        cache_dir = Path(tempfile.gettempdir()) / "valkyrie_tts_cache"
        cache_dir.mkdir(exist_ok=True)

        jobs: List[Tuple[str, str, str, Optional[Path], str]] = []
        already = 0
        skipped = 0

        for name, text in sorted(dialogue.items()):
            in_events = name in event_spans
            in_tokens = name in token_spans
            if not in_events and not in_tokens:
                skipped += 1
                continue

            existing = None
            kind = "events" if in_events else "tokens"
            if in_events:
                s, e = event_spans[name]
                existing = section_has_audio(events_content[s:e])
            elif in_tokens:
                s, e = token_spans[name]
                existing = section_has_audio(tokens_content[s:e])

            rel = f"tts_audio/{safe_filename(name)}.ogg"
            abs_out = work / rel
            sfx_path: Optional[Path] = None

            if existing:
                if existing.replace("\\", "/").startswith("tts_audio/") and abs_out.exists() and not force:
                    already += 1
                    continue
                if existing.lower().endswith(".ogg") and not existing.replace("\\", "/").startswith("tts_audio/"):
                    local = work / existing.replace("\\", "/")
                    if local.exists():
                        sfx_path = local
                else:
                    sfx_path = resolve_builtin_sfx(existing, import_audio_dir)

            jobs.append((name, text, rel, sfx_path, kind))

        log(f"Will generate audio for {len(jobs)} lines")
        log(f"(already had tts audio: {already}, skipped unmatched: {skipped})")

        if dry_run:
            log("=== DRY RUN ===")
            for name, text, rel, sfx, kind in jobs[:20]:
                sfx_note = f" +SFX:{sfx.name}" if sfx else ""
                preview = text if len(text) < 90 else text[:87] + "..."
                log(f"  {name} [{kind}]{sfx_note}")
                log(f"    → {preview}")
            if len(jobs) > 20:
                log(f"  ... and {len(jobs) - 20} more")
            return

        async def run_all() -> None:
            nonlocal events_content, tokens_content
            for i, (name, text, rel, sfx, kind) in enumerate(jobs, 1):
                out_path = work / rel
                log(f"[{i}/{len(jobs)}] {name}" + (f" (mix {sfx.name})" if sfx else ""))
                try:
                    if sfx is None:
                        cpath = cache_path(cache_dir, text, voice_id)
                        if cpath.exists() and not force:
                            shutil.copy2(cpath, out_path)
                        else:
                            await produce_audio(text, provider, voice_id, out_path, sfx=None, pause=pause)
                            shutil.copy2(out_path, cpath)
                    else:
                        await produce_audio(text, provider, voice_id, out_path, sfx=sfx, pause=pause)
                except Exception as ex:
                    log(f"  FAILED: {ex}")
                    continue

                if kind == "events":
                    events_content = set_section_audio(events_content, name, rel.replace("\\", "/"))
                else:
                    tokens_content = set_section_audio(tokens_content, name, rel.replace("\\", "/"))

        asyncio.run(run_all())

        if events_path.exists():
            events_path.write_text(events_content, encoding="utf-8")
        if tokens_path.exists():
            tokens_path.write_text(tokens_content, encoding="utf-8")

        display_name = rename_scenario_title(work, suffix=title_suffix)
        log(f"Scenario display name set to: {display_name}")

        stem = scenario.stem if scenario.is_file() else scenario.name
        stem_clean = re.sub(r"_?TTS$", "", stem, flags=re.I)
        stem_clean = re.sub(r"[^\w\-]+", "", stem_clean) or "Scenario"
        out_name = f"{stem_clean}_TTS.valkyrie"

        if output is None:
            output = download_dir() / out_name

        log(f"Packaging → {output}")
        pack_scenario(work, output)
        log(f"Done. Playable file: {output}")

        leftover = editor_dir() / f"{stem_clean}_TTS"
        if leftover.exists():
            shutil.rmtree(leftover)
            log(f"Cleaned up Editor leftover: {leftover}")

    finally:
        if tmp_root.exists():
            shutil.rmtree(tmp_root, ignore_errors=True)
            log("Cleaned up temp work folder")


def resolve_voice(provider: str, voice: str) -> Tuple[str, str]:
    if provider == "edge":
        if voice in EDGE_VOICES:
            return voice, EDGE_VOICES[voice]
        if voice.endswith("Neural"):
            return voice, voice
        for k, v in EDGE_VOICES.items():
            if k.lower() == voice.lower():
                return k, v
        die(f"Unknown edge voice '{voice}'. Use --list-voices.")
    elif provider == "elevenlabs":
        if voice in ELEVEN_VOICES:
            return voice, ELEVEN_VOICES[voice]
        return voice, voice
    else:  # kokoro
        key = voice.lower().replace("-", "_")
        if key in KOKORO_VOICES_LIST:
            vid = KOKORO_VOICES_LIST[key]
            return vid, vid
        # pass through raw name
        return voice, voice


def run_preview(provider: str, voice_id: str, voice_label: str) -> None:
    sample = (
        "The ship thrashes in the turbulent waters and you narrowly avoid crashing into the jetty. "
        "Shaken, you tie the ship to the closest mooring post."
    )
    out = Path("valkyrie_tts_preview.mp3")
    log(f"Generating preview ({provider}) with voice: {voice_id}")
    try:
        if provider == "kokoro":
            wav = Path("valkyrie_tts_preview.wav")
            generate_kokoro_tts(sample, voice_id, wav)
            log(f"Wrote {wav.resolve()}")
            if sys.platform == "win32":
                os.startfile(str(wav))  # type: ignore
            return
        if provider == "edge":
            asyncio.run(generate_edge_tts(sample, voice_id, out))
        else:
            generate_elevenlabs_tts(sample, voice_id, out)
        log(f"Wrote {out.resolve()}")
        if sys.platform == "win32":
            os.startfile(str(out))  # type: ignore
        else:
            subprocess.run(["xdg-open", str(out)], check=False)
    except Exception as ex:
        log(f"Preview generation failed: {ex}")


def main() -> None:
    ap = argparse.ArgumentParser(description="TTS for Valkyrie / Mansions of Madness scenarios")
    ap.add_argument("-s", "--scenario", help="Path to .valkyrie (optional — interactive picker if omitted)")
    ap.add_argument("-o", "--output", help="Output .valkyrie path (default: Download\\<name>_TTS.valkyrie)")
    ap.add_argument("--provider", choices=["edge", "elevenlabs", "kokoro"], default="edge")
    ap.add_argument("--voice", default=None, help="Voice name (default depends on provider)")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--list-voices", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--pause", type=float, default=0.25)
    ap.add_argument("--import-audio", type=str, default=None)
    ap.add_argument("--title-suffix", default=" TTS")
    args = ap.parse_args()

    if args.list_voices:
        print("Edge voices:")
        for k, v in EDGE_VOICES.items():
            print(f"  {k:12} {v}")
        print("\nElevenLabs (defaults):")
        for k, v in ELEVEN_VOICES.items():
            print(f"  {k:12} {v}")
        print("\nKokoro (common):")
        for k, v in sorted(set(KOKORO_VOICES_LIST.items())):
            print(f"  {k:12} → {v}")
        return

    # Defaults per provider
    if args.voice is None:
        args.voice = {"edge": "Thomas", "elevenlabs": "Adam", "kokoro": "bm_daniel"}[args.provider]

    voice_label, voice_id = resolve_voice(args.provider, args.voice)
    log(f"Selected: {args.provider} / {voice_label} ({voice_id})")

    if args.preview:
        run_preview(args.provider, voice_id, voice_label)
        return

    if args.scenario:
        scenario = Path(args.scenario)
        if not scenario.exists():
            die(f"Scenario not found: {scenario}")
    else:
        scenario = interactive_pick_scenario()
        log(f"Chosen: {scenario.name}")

    import_dir = Path(args.import_audio) if args.import_audio else default_import_audio_dir()
    out = Path(args.output) if args.output else None

    process_scenario(
        scenario=scenario,
        provider=args.provider,
        voice_name=voice_label,
        voice_id=voice_id,
        dry_run=args.dry_run,
        force=args.force,
        pause=args.pause,
        import_audio_dir=import_dir,
        output=out,
        title_suffix=args.title_suffix,
    )


if __name__ == "__main__":
    main()