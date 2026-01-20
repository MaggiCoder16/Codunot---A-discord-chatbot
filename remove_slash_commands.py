import os
import requests

TOKEN = os.getenv("DISCORD_TOKEN")
APP_ID = "1435987186502733878"

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing")

BASE_URL = f"https://discord.com/api/v10/applications/{APP_ID}/commands"

HEADERS = {
    "Authorization": f"Bot {TOKEN}",
    "Content-Type": "application/json"
}

# Fetch all global commands
resp = requests.get(BASE_URL, headers=HEADERS)
resp.raise_for_status()
commands = resp.json()

print(f"Found {len(commands)} global commands")

# Delete each command
for cmd in commands:
    cmd_id = cmd["id"]
    name = cmd["name"]

    r = requests.delete(f"{BASE_URL}/{cmd_id}", headers=HEADERS)
    if r.status_code == 204:
        print(f"Deleted: {name}")
    else:
        print(f"Failed to delete {name}: {r.status_code} {r.text}")

print("DONE. All global slash commands deleted.")
