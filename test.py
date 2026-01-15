import os, requests

DEAPI_API_KEY = os.getenv("DEAPI_API_KEY")

resp = requests.get(
    "https://api.deapi.ai/api/v1/client/models",
    headers={"Authorization": f"Bearer {DEAPI_API_KEY}"}
)

print(resp.status_code)
print(resp.json())
