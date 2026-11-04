# OfflineVoice (Ted-Voice)

Two permanent narration voices that run **entirely offline** on your own PC, for use by any video
project, Claude Code or Codex. No ElevenLabs credits, subscriptions or internet are needed after setup.

| ID | Name | Character | Default roles |
|---|---|---|---|
| `voice_1` | **Ted** | young adult American man — casual, natural, conversational | YouTube long-form, documentary, educational, storytelling (**default**) |
| `voice_2` | **Tessa** | young American woman — upbeat, bright, youthful | Facebook Reels, TikTok, YouTube Shorts, promos |

### Where these voices come from

You picked two ElevenLabs voices: **Mark – Natural Conversations** and **Brittney – Social Media
Voice**. Both are public Voice Library voices owned by other creators (not voices in your account),
and the ElevenLabs API cannot export voice models. Copying those speakers' voices would need their
permission, so this project does **not** clone them.

Instead, Ted and Tessa are **original voices with the same character**: each is a weighted blend of
Kokoro-82M's built-in voicepacks (Apache-2.0), chosen to match the age, accent, gender and delivery
described for Mark and Brittney. The ElevenLabs voices are recorded only as character references
(`config/voices.json` → `elevenlabs`). You own and can rename, re-tune or replace both voices.

## Quick start

```bat
setup.bat                                   :: one time, needs internet (~3 GB download)
generate.bat --voice voice_1 --text "Welcome to today's video." --output output\video_1.mp3
generate.bat --voice voice_2 --input script.txt --output narration.mp3
generate.bat --input script.txt --output narration.mp3          :: default voice
test_voice.bat                                                  :: test both voices offline
```

Listen first: `output\DEMO_Ted_voice_1.mp3` and `output\DEMO_Tessa_voice_2.mp3`.

From **Git Bash** (Claude Code's shell) use `generate.sh` with the same arguments. Launching a
`.bat` from bash breaks when the install path *and* an argument both contain spaces (a cmd.exe
quoting rule), which is the case for this folder. PowerShell and cmd can use `generate.bat`.

`setup.bat` creates `.venv`, installs PyTorch (CUDA build if an NVIDIA GPU is present, otherwise
CPU), installs Kokoro, downloads the model to `models/`, builds both voices, validates them offline
and sets the `OFFLINE_VOICE_HOME` user environment variable so other projects can find the generator.

## Generating narration

```
python scripts/generate_voice.py [--voice voice_1|voice_2|<name>] [--content-type TYPE] [--request "TEXT"]
                                 (--text "..." | --input script.txt) [--output file.mp3|file.wav]
                                 [--seed N] [--no-cache] [--json] [--which]
```

- **Output**: `.mp3` or `.wav`, chosen by the extension. Relative paths resolve against the current
  folder. On success stdout is only the absolute output path (or a JSON result with `--json`);
  progress goes to stderr.
- **Exit codes**: `0` ok · `1` generation failed · `2` bad input/config · `3` model files missing.
- **Long-form**: scripts are split at sentence boundaries (abbreviation-aware, never mid-word),
  generated in order, joined with natural pauses (250 ms between sentences, 650 ms between
  paragraphs), then loudness-normalised with a peak ceiling so nothing clips.
- **Resume**: every finished segment is cached in `output/.segments/`. If a run fails part-way,
  re-running only generates the missing segments. `--no-cache` forces a full regeneration.
- **Consistency**: each voice has a fixed voicepack, speed, model version and seed (`seed` in its
  `voice_config.json`), so the same text gives the same delivery. Bit-identical output across
  CPU vs GPU, or across PyTorch versions, is not guaranteed, and each sentence's intonation is
  decided by the model from context.
- **Device**: `config/settings.json` → `device` (`auto` uses the GPU when ≥700 MB VRAM is free, else
  CPU; GPU out-of-memory falls back to CPU). Override per call with `OFFLINE_VOICE_DEVICE=cpu`.
- **Script tips**: plain spoken text; blank line = paragraph pause; write dates, times and symbols
  as they should be spoken ("March twelfth", not "12/03"). Unknown words and names are still
  pronounced (espeak-ng fallback is bundled).

### Measured on this laptop (RTX 4050 Laptop 6 GB, Ryzen 7 7445HS, 16 GB RAM)

| Job | Result |
|---|---|
| Model load (first call per process) | ~10–15 s |
| Short clip, GPU, warm | ~0.05–0.1× real time (5 s of audio in ~0.3 s) |
| 5.2-minute narration (voice_1, GPU) | 18 s |
| 10.4-minute narration (voice_1, GPU, 54 segments) | 51 s |
| 15 s clip on CPU only, incl. model load | 22 s (synthesis alone faster than real time) |
| Peak VRAM | ~830 MB |
| Peak RAM (generator process) | ~2.1 GB |
| Outbound network attempts during generation | 0 |

Note: at test time only ~2 GB of the 6 GB VRAM and ~0.3–3.8 GB of RAM were free because of other
running apps. Kokoro fits comfortably, but close heavy apps if generation slows down.

### Automatic voice selection

Priority: explicit `--voice` (or "Voice 1/2"/a voice name inside `--request`) → `--content-type` →
keywords in `--request` → the default voice. Rules are plain JSON in `config/voices.json` (top to
bottom, first match wins); no AI or network is involved.

```
generate.bat --which --request "Create a 60-second Facebook Reel about AI"      -> voice_2 (Tessa)
generate.bat --which --content-type documentary                                -> voice_1 (Ted)
```

## Customising the voices

```
python scripts/configure_voice.py --show
python scripts/configure_voice.py --audition voice_1        :: renders 4 candidate blends to voices\voice_1\samples\
python scripts/configure_voice.py --voice voice_1 --blend am_michael:0.6,am_puck:0.4
python scripts/configure_voice.py --voice voice_2 --name "Tessa" --speed 1.05
python scripts/configure_voice.py --voice voice_2 --set-default
python scripts/validate_voice.py                            :: re-validate after changes
```

Available base voices (American English, with Kokoro's own quality grades): female `af_heart` (A),
`af_bella` (A-), `af_nicole` (B-), `af_aoede`, `af_kore`, `af_sarah` (C+), `af_alloy`, `af_nova` (C),
`af_sky` (C-); male `am_michael`, `am_puck`, `am_fenrir` (C+), `am_eric`, `am_echo`, `am_liam`,
`am_onyx` (D). British `bf_*`/`bm_*` voicepacks are downloaded too (`lang_code` `b`).

## ElevenLabs utility (one-time, optional)

```
python scripts/elevenlabs_setup.py --list                      :: voices in your account (free)
python scripts/elevenlabs_setup.py --search "Mark"             :: public Voice Library (free)
python scripts/elevenlabs_setup.py --voice-1 UgBBYS2sOqTuMpoF3BR0 --voice-2 kPzsL2i3teMYv0FxEYQ6
python scripts/elevenlabs_setup.py --show
```

Needs `ELEVENLABS_API_KEY` in `.env` (see `.env.example`). Generating reference audio
(`--generate-reference`) costs credits and is refused unless you pass `--approve-credits` **and**
the voice is owned by your account. Public Voice Library access is not treated as permission to clone.
Note that audio made on the ElevenLabs free tier is not licensed for commercial use.

## Importing your own (authorised) recording

```
python scripts/import_voice.py --voice voice_1 --input my_voice.m4a --transcript my_voice.txt ^
    --authorization "My own voice, recorded 2026-10-08"
```

Validates and decodes WAV/MP3/FLAC/M4A, checks duration and sample rate, converts to 24 kHz mono,
gently normalises, trims only leading/trailing silence, saves `voices/<id>/reference.wav` +
`transcript.txt`, and logs your authorisation statement (a record, not proof of permission).
**Limitation:** Kokoro cannot clone from reference audio, so imported references are stored for a
future cloning-capable engine (e.g. Chatterbox, MIT) and the voice keeps using its voicepack.

## Offline guarantees

After setup, generation:
- loads the model, voicepacks and the spaCy English model from local files only;
- sets `HF_HUB_OFFLINE`, `TRANSFORMERS_OFFLINE`, telemetry opt-outs;
- installs a socket guard that **refuses every non-loopback connection and DNS lookup** in the
  generator process (`config/settings.json` → `offline.block_network`), so it cannot silently
  reach ElevenLabs, Hugging Face or anything else;
- fails with a clear error (exit code 3) if model files are missing; never falls back to a paid API.

## Testing

`test_voice.bat` runs: profile validation (generates a test clip per voice and marks it
`offline_ready`), `scripts/test_offline.py` (both voices, MP3 + WAV, network blocked, memory/VRAM/
timing report → `output/offline_test_report.json`; add `--long` for a ~5-minute narration), and the
pytest suite in `tests/` (config, routing, segmentation, audio export, generation, CLI integration
from another folder with spaces in its path, FFmpeg muxing into an MP4).

## Engine choice and licensing

Kokoro-82M was chosen after comparing current open-source engines for this laptop (RTX 4050 6 GB,
16 GB RAM) and commercial use:

| Engine | Weights licence | Why not primary |
|---|---|---|
| **Kokoro-82M** ✅ | Apache-2.0 | — small (330 MB), <1 GB VRAM, fast on CPU, deterministic voicepacks |
| Chatterbox / Turbo | MIT | good cloning + expressiveness, but ~3–4 GB VRAM and hard pins (torch 2.6, numpy<2); a candidate second engine for authorised cloning |
| Qwen3-TTS 0.6B | Apache-2.0 | larger; separate dependency pins |
| F5-TTS | **CC-BY-NC** | non-commercial weights |
| Spark-TTS, Fish S2, Higgs v3 | non-commercial | not usable for monetised videos |

Kokoro: code Apache-2.0 (hexgrad/kokoro), weights Apache-2.0 (hexgrad/Kokoro-82M). Output audio is
yours to use commercially.

## Project layout

```
config/settings.json        engine, device (auto|cuda|cpu), paths, pauses, loudness, offline guard
config/voices.json          routing rules + ElevenLabs character references
voices/voice_N/             voice_config.json, metadata.json (provenance), voice.pt (the voice)
offline_voice/              package: config, routing, text, audio, offline_guard, engines/, generator
scripts/                    hardware_check, elevenlabs_setup, download_models, configure_voice,
                            import_voice, generate_voice, validate_voice, test_offline
models/                     downloaded checkpoints (git-ignored)
output/                     generated audio + segment cache (git-ignored)
setup.bat / generate.bat / test_voice.bat
generate.sh                 Git Bash launcher (same arguments as generate.bat)
CLAUDE.md / AGENTS.md       how Claude Code and Codex use this resource
```

All paths in `config/settings.json` may be absolute or relative to this folder.

## Limitations

- Kokoro voices are good but less expressive than ElevenLabs; the male base voices are rated C+ by
  Kokoro's author, which is why Ted is a blend. Audition alternatives with `configure_voice.py`.
- No voice cloning in the installed engine (see "Importing" above).
- English only as configured (Kokoro also supports other languages via `lang_code`).
- No emotion/paralinguistic tags (laughs, whispers).
