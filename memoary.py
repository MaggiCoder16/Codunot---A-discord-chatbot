import json
import os

MEMORY_FILE = "chat_memory.json"

if not os.path.exists(MEMORY_FILE):
    with open(MEMORY_FILE, "w") as f:
        json.dump({}, f)

def load_memory():
    with open(MEMORY_FILE, "r") as f:
        return json.load(f)

def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)

memory = load_memory()

def add_message_to_memory(channel_id, user, msg):
    if channel_id not in memory:
        memory[channel_id] = {"messages": [], "topics": [], "user_moods": {}}
    memory[channel_id]["messages"].append(f"{user}: {msg}")
    if len(memory[channel_id]["messages"]) > 30:
        memory[channel_id]["messages"] = memory[channel_id]["messages"][-30:]
    save_memory(memory)

def add_topic(channel_id, topic):
    if channel_id not in memory:
        memory[channel_id] = {"messages": [], "topics": [], "user_moods": {}}
    memory[channel_id]["topics"].append(topic)
    if len(memory[channel_id]["topics"]) > 10:
        memory[channel_id]["topics"] = memory[channel_id]["topics"][-10:]
    save_memory(memory)

def update_mood(channel_id, user, mood):
    if channel_id not in memory:
        memory[channel_id] = {"messages": [], "topics": [], "user_moods": {}}
    memory[channel_id]["user_moods"][user] = mood
    save_memory(memory)
