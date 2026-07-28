import os
import requests
import google.auth
from google.oauth2 import service_account
from google.auth.transport.requests import Request

sa_path = "gcp-service-account.json"
scopes = ["https://www.googleapis.com/auth/cloud-platform"]
project_id = "gen-lang-client-0553507358"
location = "us-central1"

models_to_test = [
    "gemini-1.5-flash-001",
    "gemini-1.5-flash-002",
    "gemini-1.5-flash",
    "gemini-1.5-pro-001",
    "gemini-1.5-pro-002",
    "gemini-1.5-pro",
    "gemini-2.5-flash"
]

try:
    creds = service_account.Credentials.from_service_account_file(sa_path, scopes=scopes)
    creds.refresh(Request())
    
    for model in models_to_test:
        url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{location}/publishers/google/models/{model}:generateContent"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {creds.token}"
        }
        payload = {
            "contents": [{"parts": [{"text": "say hi"}]}],
            "generationConfig": {
                "temperature": 0.1
            }
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        print(f"Model: {model} -> Status: {resp.status_code}")
        if resp.status_code == 200:
            print("Response:", resp.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", ""))
        else:
            print("Error Message:", resp.json().get("error", {}).get("message", ""))
except Exception as e:
    print("Error:", e)
