import os
import sys

import requests

base = os.getenv("WIKI_HAMI_API_BASE", "http://localhost:8000/api/v1")
response = requests.get(f"{base}/health", timeout=10)
print(response.status_code, response.json())
sys.exit(0 if response.ok else 1)
