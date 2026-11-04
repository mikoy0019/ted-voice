# OfflineVoice — local narration resource

Two permanent, original narration voices that run **fully offline** (Kokoro-82M, Apache-2.0).
Installed at: `D:\Development\Chykie Personal Projects\Ted-Voice` — also exported as the
user environment variable `OFFLINE_VOICE_HOME` by `setup.bat`. Always locate the generator through
`OFFLINE_VOICE_HOME`; fall back to the path above only if the variable is missing.

| Voice | Name | Character | Default use |
|---|---|---|---|
| `voice_1` | Ted | young adult American man, casual, natural, conversational | YouTube long-form, documentary, educational, storytelling (default voice) |
| `voice_2` | Tessa | young American woman, upbeat, bright, youthful | Facebook Reels, TikTok, YouTube Shorts, promos |

Names, speed, sound and the default live in `voices/<id>/voice_config.json`; routing rules live in
`config/voices.json`. Read them rather than assuming the table above is current.

## Hard rules

- **Never call ElevenLabs (or any online TTS) to make narration.** ElevenLabs is only used by the
  one-time `scripts/elevenlabs_setup.py`, and only when the user asks.
- Use the single interface below. Do not import the engine directly or write another TTS wrapper.
- If the generator exits non-zero, report its stderr. Never silently switch to another TTS.
- Honour an explicit voice ("Voice 1", "voice_2", "Tessa") over any content-type rule.

## Using it from a video project (Claude Code)

Claude Code's shell is Git Bash, so call **`generate.sh`** (not `generate.bat`: cmd.exe breaks
quoting when the install path and an argument both contain spaces, as they do here).
In cmd/PowerShell use `generate.bat` instead — same arguments.

1. **Pick the voice** — pass the user's request; explicit voice > content type > default:
   ```
   "$OFFLINE_VOICE_HOME/generate.sh" --which --request "<the user's request>" --json
   ```
   or skip this and pass `--voice voice_1|voice_2` / `--content-type tiktok` directly.
2. **Write the narration script** as plain spoken UTF-8 text (no markdown, no stage directions,
   no emoji). Blank lines between paragraphs give longer pauses. Write dates, times and odd symbols
   the way they should be spoken ("March twelfth, twenty twenty-six", not "12/03/2026").
   Ted speaks ~175 words per minute; Tessa (speed 1.05) ~210.
3. **Generate offline** (one file per scene is best for syncing visuals):
   ```
   "$OFFLINE_VOICE_HOME/generate.sh" --voice voice_2 --input scene_01.txt --output audio/scene_01.mp3 --json
   ```
   Relative paths resolve against the current project folder. Without `--json`, stdout is just the
   absolute output path. First call in a process loads the model (~10–15 s); after that the GPU
   generates ~15–20× faster than real time (10 min of narration ≈ 50 s). If the GPU is busy
   (e.g. video rendering), prefix `OFFLINE_VOICE_DEVICE=cpu` (still faster than real time).
4. **Verify**: exit code `0`, the file exists, and in `--json` output `stats.audible` is `true`.
   `duration_s` is the narration length for timing.
5. **Sync visuals**: set each scene's length to its narration `duration_s` (plus any padding).
6. **Subtitles** (if requested): one cue per sentence of the scene script, timed proportionally to
   character count within the scene's `duration_s`; write an `.srt`.
7. **Mux and export** with FFmpeg, e.g.
   ```
   ffmpeg -y -i video_silent.mp4 -i narration.mp3 -c:v copy -c:a aac -shortest final.mp4
   ffmpeg -y -i final.mp4 -vf subtitles=subs.srt -c:a copy final_subtitled.mp4
   ```
   If `ffmpeg` is not on PATH, use the bundled one:
   `"$OFFLINE_VOICE_HOME/.venv/Scripts/python.exe" -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())"`.

Exit codes: `0` ok · `1` generation failed · `2` bad input/config (unknown voice, missing script) ·
`3` offline model files missing (run `setup.bat`).

Content types for `--content-type`: `youtube_long_form`, `documentary`, `educational`,
`storytelling`, `facebook_reels`, `tiktok`, `youtube_shorts`, `promotional`.

## Working on this repository

- Package code: `offline_voice/` (config, routing, text segmentation, audio, offline guard,
  `engines/kokoro_engine.py`, `generator.py`). CLIs in `scripts/` are thin wrappers.
- Python: always `.venv\Scripts\python.exe` (3.11, PyTorch CUDA build).
- Tests: `test_voice.bat` or `.venv\Scripts\python.exe -m pytest -q` (56+ tests; generation tests
  need the model installed).
- Never commit `.env`, `models/`, `output/`, or `voices/*/reference.wav`.
- The two voices are original blends of Kokoro base voicepacks. Do not clone a third-party voice
  (including ElevenLabs Voice Library voices) without the owner's documented permission.
- Ask before chargeable ElevenLabs calls; listing/looking up voices is free.
