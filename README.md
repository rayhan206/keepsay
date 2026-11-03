# Keepsay

Keepsay lets you hear a written message in a familiar voice. Choose an audio or video recording of someone whose voice you have permission to use, then type or paste the words you want to hear. Keepsay makes an AI-generated reading and labels it as such in the player.

## Why use it?

When you live far from home, a parent’s “Did you eat yet?” can sound different from the same four words on a screen. Keepsay lets you pair a family voice note with a text like that, or hear a goodnight message in a long-distance partner’s voice. For remembrance, you might pair an old family video with a line from a letter that person wrote.

You choose the words and the reference voice independently. A message can come from a chat, a handwritten card you transcribe, or something you write yourself.

## What you can do

1. **Find the voice in a recording.** Open a voice note, audio file, or video up to 64 MiB. Enter the second where the person starts speaking. This lets you use a short passage from a longer recording.
2. **Listen before generating.** Preview up to 15 seconds locally and adjust the start time until you hear one clear speaker. A 10–15 second passage with little music or background noise works best.
3. **Give the voice your words.** Paste up to 1,000 characters and select **Create spoken message**. A character counter shows how much room you have. Keepsay reads the text you supply.
4. **Play it back.** Listen, pause, or replay using the audio controls. Try another message with the same voice sample, or select **Clear** to remove the sample, text, and result from the page.

## How it works

| Feature | Implementation |
| --- | --- |
| Recording picker and playback | HTML, CSS, and JavaScript provide labeled controls, a clip preview, and a browser audio player. |
| Voice extraction | FFmpeg runs on your computer. It extracts the chosen passage, reduces background noise, adjusts volume, and prepares a mono 16 kHz WAV sample. |
| Message validation | A Python FastAPI server and Pydantic validate the submitted message and permission flag. The server also checks the WAV format and duration before synthesis. |
| Familiar-voice reading | The server calls Sarvam Instant Voice Cloning through the asynchronous Python SDK. It sends the short reference clip and your text together, requests an MP3, and returns it to the browser for playback. |

The original recording stays on your computer. Selecting **Create spoken message** sends the prepared sample and text to Sarvam using your server-side API key. Keepsay uses an inline reference for each generation and keeps no voice-profile database or message history. [Sarvam Instant Voice Cloning documentation](https://docs.sarvam.ai/api/api-guides-tutorials/voice-cloning/overview)

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
