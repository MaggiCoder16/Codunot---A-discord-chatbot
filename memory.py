memory = {}

def add_message_to_memory(channel_id, user, message):
    if channel_id not in memory:
        memory[channel_id] = {"messages": [], "topics": [], "user_moods": {}}
    entry = f"{user}: {message}"
    memory[channel_id]["messages"].append(entry)
    memory[channel_id]["messages"] = memory[channel_id]["messages"][-25:]

def add_topic(channel_id, topic):
    if channel_id not in memory:
        memory[channel_id] = {"messages": [], "topics": [], "user_moods": {}}
    memory[channel_id]["topics"].append(topic)
    memory[channel_id]["topics"] = memory[channel_id]["topics"][-10:]

def update_mood(channel_id, user, mood):
    if channel_id not in memory:
        memory[channel_id] = {"messages": [], "topics": [], "user_moods": {}}
    memory[channel_id]["user_moods"][user] = mood
