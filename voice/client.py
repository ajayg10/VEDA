import os
import sys
import time
import queue
import threading
import tempfile
import numpy as np
import sounddevice as sd
import whisper
import httpx
import pyttsx3
from openwakeword.model import Model

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dotenv import load_dotenv
load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────
VEDA_URL    = os.getenv("VEDA_URL", "http://13.207.134.161")
API_KEY     = os.getenv("VEDA_API_KEY", "")
SAMPLE_RATE = 16000
CHANNELS    = 1
CHUNK       = 4096   # openwakeword expects 80ms chunks at 16kHz

# ── Load models once at startup ───────────────────────────────────────────
print("Loading Whisper model...")
whisper_model = whisper.load_model("base")

import openwakeword, os
OWW_DIR = os.path.join(os.path.dirname(openwakeword.__file__), "resources", "models")
HEY_JARVIS = os.path.join(OWW_DIR, "hey_jarvis_v0.1.onnx")

print("Loading wake word model...")
oww_model = Model(wakeword_model_paths=[HEY_JARVIS])

# ── TTS engine ────────────────────────────────────────────────────────────
tts = pyttsx3.init()
tts.setProperty("rate", 165)    # speaking speed
tts.setProperty("volume", 1.0)

def speak(text: str) -> None:
    """Convert text to speech and play it."""
    print(f"VEDA: {text}")
    tts.say(text)
    tts.runAndWait()

# ── Send goal to VEDA API ─────────────────────────────────────────────────
def ask_veda(goal: str) -> str:
    """Send a goal to the Orchestrator and return a spoken summary."""
    try:
        resp = httpx.post(
            f"{VEDA_URL}/api/run",
            headers={"X-API-Key": API_KEY, "Content-Type": "application/json"},
            json={"goal": goal},
            timeout=120,
        )
        data = resp.json()
        plan = data.get("plan", {})
        steps = plan.get("steps", [])

        if not steps:
            return "I couldn't come up with a plan for that."

        # Summarize the plan in spoken form
        goal_text = plan.get("goal", goal)
        step_count = len(steps)
        first_step = steps[0].get("description", "")
        complexity = plan.get("estimated_complexity", "low")

        return (
            f"Got it. Here's my plan for: {goal_text}. "
            f"I've broken it into {step_count} step{'s' if step_count > 1 else ''}. "
            f"First: {first_step}. "
            f"Complexity is {complexity}."
        )
    except Exception as e:
        return f"Sorry, I couldn't reach the VEDA server. Error: {str(e)[:50]}"

# ── Record audio after wake word ──────────────────────────────────────────
def record_command(duration: float = 5.0) -> np.ndarray:
    """Record audio for `duration` seconds and return as numpy array."""
    print(f"  Recording for {duration}s...")
    audio = sd.rec(
        int(duration * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
    )
    sd.wait()
    return audio.flatten()

# ── Transcribe with Whisper ───────────────────────────────────────────────
def transcribe(audio: np.ndarray) -> str:
    """Run Whisper on raw float32 audio and return transcript."""
    result = whisper_model.transcribe(audio, fp16=False, language="en")
    return result["text"].strip()

# ── Main loop ─────────────────────────────────────────────────────────────
def run() -> None:
    speak("VEDA is online. Say Hey Jarvis to activate me.")
    print("\nListening for wake word... (Ctrl+C to quit)\n")

    audio_buffer = queue.Queue()

    def audio_callback(indata, frames, time_info, status):
        audio_buffer.put(indata.copy())

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
        blocksize=CHUNK,
        latency="high",
        callback=audio_callback,
    ):
        while True:
            chunk = audio_buffer.get()
            chunk_int16 = (chunk * 32767).astype(np.int16).flatten()
            oww_model.predict(chunk_int16)
            scores = oww_model.prediction_buffer.get("hey_jarvis_v0.1", [0])                                                  
            latest = scores[-1] if scores else 0

            if latest > 0.5:
                # Wake word detected
                print("\n🎙  Wake word detected!")
                speak("Yes?")

                # Clear buffer so stale audio doesn't bleed in
                while not audio_buffer.empty():
                    audio_buffer.get()

                # Record the command
                audio = record_command(duration=5.0)

                # Transcribe
                print("  Transcribing...")
                command = transcribe(audio)
                print(f"  You said: {command}")

                if not command or len(command.split()) < 2:
                    speak("I didn't catch that. Please try again.")
                    continue

                # Send to VEDA
                speak("On it.")
                response = ask_veda(command)
                speak(response)

                print("\nListening for wake word...\n")
                # Reset wake word model buffer
                oww_model.prediction_buffer["hey_jarvis_v0.1"] = []


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\nVEDA voice client stopped.")