# Keepsay

Hear a written message in a familiar voice. Choose a recording, preview a short sample of the speaker, and play an AI-generated reading of your own words. Keepsay runs on your computer and uses Sarvam for synthesis.

## Run locally

You need Python 3.11 or newer and a Sarvam API key with Instant Voice Cloning access and available credits. The following commands use PowerShell from the repository root.

~~~powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env -ErrorAction Stop
~~~

On first setup, open the new .env and enter your key after SARVAM_API_KEY=. If you already have a configured .env, keep it. Launch the local server:

~~~powershell
.\.venv\Scripts\python -m uvicorn studio:app --host 127.0.0.1 --port 8765 --no-access-log
~~~

Open [Keepsay on localhost](http://127.0.0.1:8765). On macOS or Linux use the virtual environment’s bin/python executable. FFmpeg comes with the imageio-ffmpeg package on supported platforms. To use an existing FFmpeg executable, set FFMPEG_BINARY to its absolute path in .env.

## Make a keepsake

1. Choose a recording you have permission to use. Audio files, WhatsApp Opus notes and videos with an audio track are supported. The upload limit is 64 MiB.
2. Enter the second where the speaker begins. Select **Preview voice sample** and listen for clear solo speech. Aim for 10–15 seconds. Keepsay extracts up to 15 seconds and rejects clips shorter than 3 seconds.
3. Paste up to 1,000 characters and select **Create spoken message**. When it is ready, press play. You can write another message using the same sample, or select **Clear** to reset the form and release its audio players.

## How Keepsay uses Sarvam

Preview stays local. The browser sends the source recording to the local FastAPI route POST /clip. FFmpeg selects the first audio track, applies a high-pass filter, noise reduction and normalization, and returns a mono 16 kHz WAV. Temporary media files are removed when extraction finishes.

Generation calls POST /speak. The server validates the message, permission flag and WAV, then reads the API key from the environment or local .env. Only the reference clip and message go to Sarvam. The one-shot Instant Voice Cloning call in studio.py uses the asynchronous Python SDK:

~~~python
audio = await client.voice_cloning.convert(
    text=message.text,
    ref_audio=("reference.wav", clip, "audio/wav"),
    output_audio_codec="mp3",
    enable_cached_responses=False,
    request_options={"max_retries": 0},
)
~~~

The inline reference supplies the voice on each request. Keepsay creates no persistent voice profile. It leaves language detection to Sarvam and passes the typed words directly to synthesis. The server decodes the returned base64 audio and sends an MP3 to the browser. Generation is billed by Sarvam. [Official Instant Voice Cloning guide](https://docs.sarvam.ai/api/api-guides-tutorials/voice-cloning/overview)

## Privacy and operating limits

The key stays on the server. Responses disable browser caching. Keepsay has no database, account system or message history. **Clear** resets local browser state; Sarvam handles submitted samples under its own service terms. The local server accepts loopback hosts and allows two concurrent processing requests. Keep it bound to loopback for personal use.

If preview fails, check that the file has an audio track and move the start time earlier. If generation fails after a successful preview, check the key, cloning access and credits. If the voice sounds unclear, choose a passage with one speaker and less music or background speech.

## Source map

| File | Responsibility |
| --- | --- |
| keepsay.html | Accessible recording picker, preview, message editor and audio playback |
| studio.py | Local HTTP routes, FFmpeg extraction and Sarvam integration |
| models.py | Typed request validation |
| requirements.txt | Python runtime dependencies |

The app has been exercised with synthetic speech through a live Sarvam request and browser playback. Voice resemblance depends on the source recording and has not been independently scored.
