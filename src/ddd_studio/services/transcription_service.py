import functools
import json
from collections.abc import Iterator

from config.settings import WHISPER_MODEL
from faster_whisper import WhisperModel
from langgraph.config import get_stream_writer
from models.event_storming_state import EventStormingState


@functools.cache
def load_whisper_model():
    print(f"🚀 [Whisper] Loading model '{WHISPER_MODEL}' (automatic download if missing)...")
    model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
    return model


@functools.cache
def load_writer():
    return get_stream_writer()


def transcribe_audio(state: EventStormingState) -> Iterator[dict]:
    print("🎤 [Transcription Service: Transcribe] Starting Whisper...")
    try:
        writer = load_writer()
        audio_path = state.get("audio_path", "").strip()
        cache_path = state.get("cache_path", "").strip()
        context = state.get("context", "").strip()
        has_refine = state.get("has_refine", False)

        print(f"... Loading Whisper model '{WHISPER_MODEL}'...")
        writer({"status": f"Cargando modelo {WHISPER_MODEL}..."})

        model = load_whisper_model()
        print(f"... Transcribing {audio_path} (this may take a while)...")
        writer({"status": "Transcribiendo audio (esto puede tardar)..."})

        segments, info = model.transcribe(audio_path, beam_size=5)
        total_duration = info.duration

        full_transcription = []
        for segment in segments:
            segment_text = segment.text.strip()
            percent_complete = (segment.end / total_duration) * 100
            writer({"status": f"[Transcribiendo] ...{percent_complete:.2f}% completado"})

            full_transcription.append(segment_text)

        transcription = " ".join(full_transcription)

        print("... Transcripción completa, saving to cache...")
        cache_data = {"transcription": transcription, "context": context}
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)

        print(f"... Cache .json saved at '{cache_path}'.")
        writer({"status": "Se guarda una copia en caché del texto transcrito."})
        print("✅ [Transcription Service: Transcribe] Completed.")

        yield {"transcription": transcription, "context": context, "has_refine": has_refine}

    except Exception as e:
        print(f"❌ [Transcription Service: Transcribe] Error: {str(e)}")
        yield {"error": f"Whisper error: {str(e)}"}
