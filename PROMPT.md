# PROJECT: DUAL OFFLINE AI VOICE RESOURCE

## ElevenLabs Voice Selection + Two Persistent Offline Voices + Claude Code and Codex Integration

You are a senior AI/ML engineer, Python developer, automation architect, and local AI infrastructure specialist.

Your task is to build a complete, lightweight, production-ready offline AI text-to-speech system that supports TWO permanent voice profiles.

The system must integrate with Claude Code, OpenAI Codex, and automated video-content production workflows.

Do not build a SaaS application or unnecessary dashboard.

I want a reusable local AI resource that other projects can access through simple commands.

***

# 1. PRIMARY OBJECTIVE

I have already selected TWO voices from ElevenLabs.

I want to configure these voices as Voice 1 and Voice 2 and use them consistently for my future video-content generation projects.

My desired workflow:

1. Connect to ElevenLabs during initial setup.
2. Retrieve information about my two selected voices.
3. Generate or import reference audio where authorized.
4. Prepare two permanent local voice profiles.
5. Install an open-source offline voice synthesis engine.
6. Configure both voices for local text-to-speech.
7. Allow Claude Code and Codex to select either voice.
8. Automatically generate narration during video production.
9. Produce MP3 or WAV audio files.
10. Operate entirely offline after installation.

The system must not require further ElevenLabs API calls for offline narration.

It must not consume ElevenLabs credits after the initial setup.

## Critical Technical Limitation

The ElevenLabs API does not provide a way to download or export proprietary voice-model weights.

A Voice ID is not a downloadable AI model.

Downloading audio does not automatically grant permission to clone the speaker.

Before creating a local clone, require confirmation that I own the voice or have explicit permission to reproduce it outside ElevenLabs.

***

# 2. HARDWARE AND ENVIRONMENT

Optimize the project for:

* Windows 10/11

* AMD Ryzen 7 4800H or equivalent

* NVIDIA GTX 1660 Ti or RTX 2060

* 6GB GPU VRAM

* 16GB RAM

* SSD storage

Before installing anything:

1. Detect the operating system.
2. Detect installed Python versions.
3. Check NVIDIA GPU availability.
4. Check CUDA support.
5. Measure available system memory.
6. Check available VRAM.
7. Check available storage.
8. Check FFmpeg installation.
9. Identify dependency conflicts.
10. Recommend a compatible local AI model.

Use GPU acceleration when available.

Implement CPU fallback when supported.

Avoid loading multiple large AI models simultaneously.

Both voice profiles should share the same synthesis engine whenever practical.

***

# 3. PROJECT DIRECTORY STRUCTURE

Create the following structure:

```
OfflineVoice/
│
├── models/
│   └── local-tts-engine/
│
├── voices/
│   │
│   ├── voice_1/
│   │   ├── reference.wav
│   │   ├── transcript.txt
│   │   ├── voice_config.json
│   │   └── metadata.json
│   │
│   └── voice_2/
│       ├── reference.wav
│       ├── transcript.txt
│       ├── voice_config.json
│       └── metadata.json
│
├── scripts/
│   ├── elevenlabs_setup.py
│   ├── import_voice.py
│   ├── generate_voice.py
│   ├── validate_voice.py
│   ├── test_offline.py
│   └── hardware_check.py
│
├── config/
│   ├── settings.json
│   └── voices.json
│
├── output/
│
├── tests/
│
├── setup.bat
├── generate.bat
├── test_voice.bat
│
├── requirements.txt
├── .env.example
├── .gitignore
├── CLAUDE.md
├── AGENTS.md
└── README.md

```

Use configurable installation directories.

Do not assume drive D: exists.

Support absolute and relative file paths.

Never commit API keys, private reference recordings, or sensitive credentials into Git.

***

# 4. ELEVENLABS INITIAL SETUP

Create a one-time ElevenLabs integration utility.

Use the official ElevenLabs API.

Store the API key in an environment variable:

```
ELEVENLABS_API_KEY=

```

## Required Capabilities

The setup utility should:

* Authenticate using my API key.

* Retrieve voices available to my account.

* Display voice names.

* Display Voice IDs.

* Display available descriptions.

* Allow me to select TWO voices.

* Save voice metadata locally.

* Support explicitly authorized reference-audio preparation.

* Download audio generated through an approved API request.

* Report API errors clearly.

### Important

Do not automatically generate reference recordings.

ElevenLabs API requests may consume credits.

Ask for explicit approval before making chargeable generation requests.

Do not treat public Voice Library access as permission to clone a voice.

Do not attempt to extract proprietary weights.

## Voice Selection

Support commands such as:

```
python scripts/elevenlabs_setup.py --list

```

```
python scripts/elevenlabs_setup.py --voice-1 VOICE_ID_1 --voice-2 VOICE_ID_2

```

Store:

```
{
  "voice_1": {
    "provider": "elevenlabs",
    "voice_id": "VOICE_ID_1",
    "name": "Selected Voice One",
    "offline_ready": false
  },
  "voice_2": {
    "provider": "elevenlabs",
    "voice_id": "VOICE_ID_2",
    "name": "Selected Voice Two",
    "offline_ready": false
  }
}

```

Both voices must be independently configured and validated.

***

# 5. LOCAL AI VOICE ENGINE

Research and evaluate open-source voice synthesis models.

Candidate engines:

* F5-TTS

* OpenVoice V2

* Kokoro TTS

* Other actively maintained local TTS engines

Evaluate:

1. Natural voice quality.
2. Voice consistency.
3. Offline availability.
4. Reference-based voice cloning.
5. NVIDIA CUDA support.
6. 6GB VRAM compatibility.
7. CPU inference.
8. Commercial licensing.
9. Model checkpoint licensing.
10. Windows compatibility.
11. Long-form speech quality.
12. Model download size.

Choose the best practical option.

If a model supports cloning but has restrictions on commercial output, explain those restrictions and select an appropriate alternative.

If local cloning of the selected ElevenLabs voice is not authorized, use an independently licensed voice preset instead.

Download all necessary checkpoints during installation.

After setup, inference must run entirely offline.

***

# 6. TWO PERMANENT VOICE PROFILES

Build a configuration system supporting exactly two voice profiles.

## VOICE 1

Identifier:

`voice_1`

Purpose:

Primary video narration.

Suggested use:

* Storytelling

* YouTube videos

* Educational content

* Documentary-style videos

* Long-form narration

## VOICE 2

Identifier:

`voice_2`

Purpose:

Alternative video narration.

Suggested use:

* Facebook Reels

* TikTok videos

* YouTube Shorts

* Promotional content

* Energetic narration

These are default roles only.

Allow me to change the voice descriptions, roles, and default selection.

Do not assume the gender, accent, or vocal characteristics of either voice.

## Voice Configuration

Each profile should contain:

```
{
  "id": "voice_1",
  "name": "My Primary Voice",
  "engine": "selected_local_engine",
  "reference_audio": "voices/voice_1/reference.wav",
  "reference_transcript": "voices/voice_1/transcript.txt",
  "language": "en",
  "speed": 1.0,
  "default": true,
  "offline_ready": false
}

```

Use only settings supported by the chosen model.

For models that require a transcript, validate the reference transcript before generation.

For models with built-in voice presets, store the preset identifier rather than pretending it uses reference-audio cloning.

## Voice Consistency

Maintain stable:

* Speaker identity

* Voice configuration

* Language

* Reference audio

* Inference settings

* Model version

Where supported, configure deterministic seeds.

Explain that exact consistency across all generated sentences cannot be guaranteed.

***

# 7. VOICE IMPORT AND PROCESSING

Build a utility to import authorized voice recordings.

Example:

```
python scripts/import_voice.py --voice voice_1 --input recording_1.mp3

```

```
python scripts/import_voice.py --voice voice_2 --input recording_2.mp3

```

Supported formats:

* WAV

* MP3

* FLAC

* M4A

Processing pipeline:

1. Validate the uploaded file.
2. Verify the file can be decoded.
3. Inspect audio duration.
4. Inspect sample rate.
5. Convert to the required format.
6. Normalize appropriately.
7. Remove unnecessary silence.
8. Store the processed reference.
9. Validate the transcript if required.
10. Update voice configuration.

Do not overprocess reference recordings.

Preserve their natural vocal characteristics.

Store voice authorization metadata without treating a checkbox alone as proof of legal permission.

***

# 8. OFFLINE VOICE GENERATION

Create a command-line text-to-speech utility.

## Generate Using Voice 1

```
python scripts/generate_voice.py --voice voice_1 --text "Welcome to today's video." --output output/video_1.mp3

```

## Generate Using Voice 2

```
python scripts/generate_voice.py --voice voice_2 --text "Here are five amazing facts." --output output/video_2.mp3

```

## Generate From a Script File

```
python scripts/generate_voice.py --voice voice_1 --input video_script.txt --output narration.mp3

```

## Default Voice

Support:

```
python scripts/generate_voice.py --input video_script.txt --output narration.mp3

```

When `--voice` is not provided, use the configured default voice.

## Core Requirements

The generator must:

1. Validate the input script.
2. Resolve the selected voice profile.
3. Verify that the voice is available offline.
4. Load the selected model.
5. Generate narration locally.
6. Save the audio.
7. Return the absolute output path.
8. Exit with a proper status code.

Support:

* MP3 output.

* WAV output.

* UTF-8 scripts.

* Long-form narration.

* Generation progress.

* Clear error handling.

* Optional generation seeds.

* Explicit output paths.

Never silently switch from offline inference to a paid API.

***

# 9. LONG-FORM NARRATION

Implement automatic script segmentation.

Requirements:

* Split at natural sentence boundaries.

* Preserve sentence order.

* Avoid cutting words.

* Maintain voice configuration.

* Generate segments sequentially.

* Combine generated segments.

* Insert natural pauses.

* Prevent audible clipping.

* Normalize the final audio.

Handle failed segments gracefully.

Avoid unnecessary regeneration of successfully completed segments.

Support narration for:

* 30-second Shorts.

* 60-second Reels.

* 5-minute videos.

* 10-minute videos.

* Longer content within practical hardware limits.

***

# 10. AUTOMATIC VOICE SELECTION

Create a lightweight voice-routing system.

If I specify a voice explicitly, always honor that selection.

Examples:

"Create a video using Voice 1."

Use `voice_1`.

"Create a Facebook Reel using Voice 2."

Use `voice_2`.

If I do not specify a voice, follow the configured content preferences.

Initial defaults:

| Content Type       | Voice    |
| :----------------- | :------- |
| YouTube long-form  | voice\_1 |
| Documentary        | voice\_1 |
| Educational        | voice\_1 |
| Storytelling       | voice\_1 |
| Facebook Reels     | voice\_2 |
| TikTok             | voice\_2 |
| YouTube Shorts     | voice\_2 |
| Promotional videos | voice\_2 |

Make these rules editable.

Do not use an external AI API to decide which voice to select.

Use straightforward local configuration.

***

# 11. CLAUDE CODE INTEGRATION

Create a reusable `CLAUDE.md` integration guide.

Whenever Claude Code generates video content:

1. Read the voice configuration.
2. Determine the requested voice.
3. Generate the narration script.
4. Invoke the local voice generator.
5. Verify the generated audio.
6. Add the narration to the video.
7. Synchronize visual scenes.
8. Add subtitles if requested.
9. Export the final video.

Claude Code must not invoke ElevenLabs during normal video generation.

Provide an example command:

```
python "D:\AI-Resources\OfflineVoice\scripts\generate_voice.py" --voice voice_1 --input script.txt --output narration.mp3

```

Use the actual installed path.

Do not hardcode example paths into production configuration.

***

# 12. CODEX INTEGRATION

Create an `AGENTS.md` file that explains how OpenAI Codex should use this voice resource.

Codex must:

* Locate the local voice generator.

* Read the voice configuration.

* Select Voice 1 or Voice 2.

* Generate narration locally.

* Wait for successful generation.

* Validate the audio file.

* Continue the video-production workflow.

Both Claude Code and Codex must use the same local voice-generation interface.

Do not create separate speech engines for each agent.

***

# 13. VIDEO GENERATION WORKFLOW

The final integration should follow:

```
CLAUDE CODE / CODEX
        |
        v
GENERATE CONTENT SCRIPT
        |
        v
SELECT VOICE
        |
        +----------+
        |          |
        v          v
     VOICE 1    VOICE 2
        |          |
        +-----+----+
              |
              v
     LOCAL TTS ENGINE
              |
              v
       NARRATION.MP3
              |
              v
       VIDEO PIPELINE
              |
              v
            FFMPEG
              |
              v
       FINAL VIDEO.MP4

```

The video-production system should be able to use either voice without changing its implementation.

***

# 14. GLOBAL REUSABILITY

The voice resource must work across different project directories.

For example:

```
D:\AI-Resources\OfflineVoice\
D:\Projects\Facebook-Reels\
D:\Projects\YouTube-Automation\
D:\Projects\TikTok-Content\

```

All three video projects should be able to call the same local voice engine.

Provide a stable CLI interface.

Avoid requiring the user to copy model files into every project.

Use an environment variable such as:

```
OFFLINE_VOICE_HOME=D:\AI-Resources\OfflineVoice

```

Support invoking the generator from anywhere.

***

# 15. STRICT OFFLINE OPERATION

After initial setup:

* No ElevenLabs API calls.

* No online TTS requests.

* No cloud inference.

* No subscription authentication.

* No model downloads during generation.

* No telemetry.

* No remote script processing.

* No external voice uploads.

Separate ElevenLabs setup from local inference.

If necessary model files are missing, fail with a clear error.

Never silently use online inference.

***

# 16. SIMPLE WINDOWS COMMANDS

Create:

`setup.bat`

Installs dependencies, models, and application files.

`generate.bat`

Generates narration with the selected voice.

`test_voice.bat`

Tests both voice profiles.

Example:

```
generate.bat --voice voice_1 --input script.txt --output narration.mp3

```

```
generate.bat --voice voice_2 --input script.txt --output narration.mp3

```

Ensure paths containing spaces work.

Use the project's virtual-environment Python interpreter.

***

# 17. TESTING AND VALIDATION

Create automated tests covering:

### Voice Configuration

* Two voice profiles exist.

* Both configurations are valid.

* Default voice selection works.

* Explicit voice selection works.

* Invalid voice identifiers are rejected.

### Audio Generation

* Voice 1 generates audio.

* Voice 2 generates audio.

* WAV export works.

* MP3 export works.

* Long scripts generate successfully.

* Output audio contains audible speech.

### Integration

* Claude Code can invoke the generator.

* Codex can invoke the generator.

* Different project directories can access the resource.

* Output paths are correct.

* FFmpeg can consume the output.

### Offline Verification

* Disable or block network access.

* Generate a sample using Voice 1.

* Generate a sample using Voice 2.

* Confirm neither generation attempts external connections.

### Resource Usage

* Monitor system memory.

* Monitor GPU memory.

* Record inference time.

* Report hardware limitations.

Do not claim tests have passed unless they actually ran.

***

# 18. IMPLEMENTATION ORDER

Follow this sequence:

**Step 1:** Inspect the hardware and development environment.

**Step 2:** Research compatible offline TTS engines and licensing.

**Step 3:** Create the project structure.

**Step 4:** Implement the ElevenLabs voice-selection utility.

**Step 5:** Implement the authorization and audio-import workflow.

**Step 6:** Install and configure the local TTS engine.

**Step 7:** Configure Voice 1 and Voice 2.

**Step 8:** Implement the offline narration generator.

**Step 9:** Implement automatic voice selection.

**Step 10:** Integrate Claude Code and Codex.

**Step 11:** Create Windows installation and generation scripts.

**Step 12:** Test both voice profiles.

**Step 13:** Test offline operation.

**Step 14:** Document all commands, dependencies, and limitations.

Do not stop after planning.

Implement and test the actual project using available tools.

If a required API credential, reference file, or authorization is unavailable, implement and test all independent components, then clearly identify the blocked setup step.

Do not invent credentials, sample files, or successful test results.

***

# 19. FINAL DELIVERABLES

The completed project must include:

1. A working offline TTS engine.
2. Two reusable voice profiles.
3. ElevenLabs voice-selection integration.
4. Authorized reference-audio import.
5. MP3 and WAV generation.
6. Automatic voice selection.
7. Long-form narration support.
8. Claude Code integration.
9. Codex integration.
10. Global voice-resource configuration.
11. Windows setup scripts.
12. Offline verification tests.
13. Installation documentation.

## FINAL SUCCESS CRITERIA

I should be able to open Claude Code or Codex and say:

**Example 1:**

"Create a 60-second Facebook Reel about artificial intelligence using Voice 2. Generate the narration offline, synchronize it with the visuals, add subtitles, and export the finished video."

**Example 2:**

"Create a 5-minute YouTube documentary about space exploration using Voice 1. Use my offline AI voice resource for narration."

**Example 3:**

"Create three short videos using my default voice. Generate all voiceovers locally without using ElevenLabs."

The coding agent must use the configured local voice resource without requiring additional API credits or subscriptions.

## CRITICAL FINAL INSTRUCTION

Build a real, functioning implementation.

Do not create a mockup.

Do not build a large application with unnecessary features.

Focus on TWO reliable, permanent offline voice resources that can be reused across unlimited video-content projects.

Prioritize stable narration generation, voice consistency, commercial-use compatibility, and straightforward Claude Code/Codex integration.
