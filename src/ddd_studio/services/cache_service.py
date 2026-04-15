import json
import os

from models.event_storming_state import EventStormingState


def check_cache(state: EventStormingState) -> dict:
    print("🚦 [Cache Service: Check Cache] Starting...")
    try:
        audio_name = state.get("audio_name", "")
        audio_path = state.get("audio_path", "")
        context = state.get("context", "").strip()

        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file {audio_path} does not exist.")
        cache_path = os.path.splitext(audio_name)[0] + ".cache.json"
        cache_existe = os.path.exists(cache_path)
        print(
            f"{'✅' if cache_existe else '⚠️'} [Cache Service: Check Cache] {'Cache found' if cache_existe else 'No cache found'} at: {cache_path}"
        )
        return {"cache_path": cache_path, "cache_existe": cache_existe, "context": context}
    except Exception as e:
        print(f"❌ [Cache Service: Check Cache] Error: {str(e)}")
        return {"error": str(e)}


def load_cache(state: EventStormingState) -> dict:
    print("📄 [Cache Service: Load Cache] Loading from file...")
    try:
        cache_path = state.get("cache_path", "").strip()
        context = state.get("context", "").strip()
        with open(cache_path, encoding="utf-8") as f:
            data = json.load(f)
        print("✅ [Cache Service: Load Cache] Completed.")
        return {"transcription": data["transcription"], "context": context}
    except Exception as e:
        print(f"❌ [Cache Service: Load Cache] Error: {str(e)}")
        return {"error": f"Error reading cache: {str(e)}"}
