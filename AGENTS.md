# OfflineVoice — instructions for OpenAI Codex

This folder is a shared, fully offline narration resource. Claude Code and Codex use the **same**
command-line interface and the **same** engine; do not create a separate speech engine.

Location: environment variable `OFFLINE_VOICE_HOME` (set by `setup.bat`), currently
`D:\Development\Chykie Personal Projects\Ted-Voice`.

## Voices

- `voice_1` — **Ted**: young adult American man, casual and conversational. Default voice;
  long-form YouTube, documentary, educational, storytelling.
- `voice_2` — **Tessa**: young American woman, upbeat and youthful. Reels, TikTok, Shorts, promos.

Current names/settings: `voices/<id>/voice_config.json`. Routing rules: `config/voices.json`.

## Rules

1. Never call ElevenLabs or any online TTS for narration. No API keys are needed.
2. An explicit voice in the user's request ("Voice 2", "Tessa") always wins. Otherwise pass
   `--content-type` or `--request "<user request>"`; otherwise the default voice is used.
3. Wait for the command to finish and check the exit code before continuing.
4. If generation fails, surface stderr to the user; do not fall back to another TTS.

## Procedure

1. Locate the generator:
   - PowerShell: `& "$env:OFFLINE_VOICE_HOME\generate.bat"`
   - cmd: `"%OFFLINE_VOICE_HOME%\generate.bat"`
   - bash (Git Bash/MSYS): `"$OFFLINE_VOICE_HOME/generate.sh"` — do not launch the `.bat` from bash;
     cmd.exe mangles quoting when the install path and an argument both contain spaces.
   - Python directly: `"%OFFLINE_VOICE_HOME%\.venv\Scripts\python.exe" "%OFFLINE_VOICE_HOME%\scripts\generate_voice.py"`
2. Optional — confirm the voice: `generate.bat --which --request "<request>" --json`
3. Write the narration script to a UTF-8 text file (plain spoken text, blank line between paragraphs;
   write dates/times/symbols as they should be spoken).
4. Generate:
   ```
   "%OFFLINE_VOICE_HOME%\generate.bat" --voice voice_1 --input script.txt --output narration.mp3 --json
   ```
5. Validate: exit code `0`; JSON `output` exists; `stats.audible` is `true`; use `duration_s` for
   scene timing and subtitles.
6. Continue the video pipeline (FFmpeg mux: `ffmpeg -y -i video.mp4 -i narration.mp3 -c:v copy -c:a aac -shortest final.mp4`).

Exit codes: `0` ok, `1` generation failed, `2` bad input/config, `3` models missing (run `setup.bat`).
Output formats: `.mp3` or `.wav` (chosen by the `--output` extension).
Set `OFFLINE_VOICE_DEVICE=cpu` to keep the GPU free (CPU is still faster than real time).

## Working on this repository

- Code: `offline_voice/` package; CLIs in `scripts/`; tests in `tests/` (`test_voice.bat`).
- Interpreter: `.venv\Scripts\python.exe`.
- Do not commit `.env`, `models/`, `output/` or reference recordings.
