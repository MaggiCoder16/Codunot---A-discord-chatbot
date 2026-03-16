import os
import json
from datetime import datetime
from encryption import save_encrypted, load_encrypted


class MemoryManager:
    def __init__(self, limit=15, file_path=None):
        self.limit = limit
        self.file_path = file_path
        self.memory = {}
        self.flags = {}

        if self.file_path:
            self._load()

    # ---------------- LOAD / SAVE ----------------

    def _load(self):
        if not self.file_path or not os.path.exists(self.file_path):
            return
        try:
            raw = load_encrypted(self.file_path)
            data = json.loads(raw)
            self.memory = data.get("memory", {})
            self.flags = data.get("flags", {})
        except Exception as e:
            print(f"[MEMORY] Load error: {e}")
            self.memory = {}
            self.flags = {}

    def persist(self):
        if not self.file_path:
            return
        try:
            # timestamps are datetime objects in memory — convert to strings for JSON
            serializable = {}
            for chan_id, data in self.memory.items():
                serializable[chan_id] = {
                    "messages":     data.get("messages", []),
                    "timestamps":   [
                        t.isoformat() if isinstance(t, datetime) else t
                        for t in data.get("timestamps", [])
                    ],
                    "roast_target": data.get("roast_target"),
                    "mode":         data.get("mode", "funny"),
                    "model":        data.get("model", "openai/gpt-oss-120b"),
                }
            save_encrypted(self.file_path, json.dumps({"memory": serializable, "flags": self.flags}))
        except Exception as e:
            print(f"[MEMORY] Save error: {e}")

    # ---------------- MESSAGE LOGGING ----------------

    def add_message(self, channel_id, user, message):
        self._ensure_channel(channel_id)
        entry = f"{user}: {message}"
        self.memory[channel_id]["messages"].append(entry)
        self.memory[channel_id]["messages"] = self.memory[channel_id]["messages"][-self.limit:]
        self.memory[channel_id]["timestamps"].append(datetime.utcnow())
        self.memory[channel_id]["timestamps"] = self.memory[channel_id]["timestamps"][-self.limit:]

    def get_recent_flat(self, channel_id, n):
        if channel_id in self.memory:
            return self.memory[channel_id]["messages"][-n:]
        return []

    def get_last_timestamp(self, channel_id):
        if channel_id in self.memory and self.memory[channel_id]["timestamps"]:
            return self.memory[channel_id]["timestamps"][-1]
        return None

    # ---------------- ROAST TARGET ----------------

    def set_roast_target(self, channel_id, target_name):
        self._ensure_channel(channel_id)
        self.memory[channel_id]["roast_target"] = target_name

    def get_roast_target(self, channel_id):
        if channel_id in self.memory:
            return self.memory[channel_id]["roast_target"]
        return None

    def remove_roast_target(self, channel_id):
        if channel_id in self.memory:
            self.memory[channel_id]["roast_target"] = None

    # ---------------- CHANNEL MODE ----------------

    def save_channel_mode(self, channel_id, mode):
        self._ensure_channel(channel_id)
        self.memory[channel_id]["mode"] = mode

    def get_channel_mode(self, channel_id):
        if channel_id in self.memory:
            return self.memory[channel_id].get("mode")
        return None

    # ---------------- CHANNEL MODEL ----------------

    def save_channel_model(self, channel_id, model):
        self._ensure_channel(channel_id)
        self.memory[channel_id]["model"] = model

    def get_channel_model(self, channel_id):
        if channel_id in self.memory:
            return self.memory[channel_id].get("model", "openai/gpt-oss-120b")
        return "openai/gpt-oss-120b"

    def clear_channel_messages(self, channel_id):
        self._ensure_channel(channel_id)
        self.memory[channel_id]["messages"] = []
        self.memory[channel_id]["timestamps"] = []

    # ---------------- FLAGS ----------------

    def set_flag(self, key):
        self.flags[key] = True

    def get_flag(self, key):
        return self.flags.get(key, False)

    # ---------------- INTERNAL ----------------

    def _ensure_channel(self, channel_id):
        if channel_id not in self.memory:
            self.memory[channel_id] = {
                "messages":     [],
                "timestamps":   [],
                "roast_target": None,
                "mode":         "funny",
                "model":        "openai/gpt-oss-120b",
            }

    async def close(self):
        self.persist()
