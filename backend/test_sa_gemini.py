import os
import requests
import google.auth
from google.oauth2 import service_account
from google.auth.transport.requests import Request

sa_path = "gcp-service-account.json"
scopes = ["https://www.googleapis.com/auth/generative-language"]

try:
    creds = service_account.Credentials.from_service_account_file(sa_path, scopes=scopes)
    creds.refresh(Request())
    print("Token generated successfully:", creds.token[:15] + "...")
    
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {creds.token}"
    }
    payload = {
        "contents": [{"parts": [{"text": "Hello, tell me a 1-sentence joke."}]}]
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=10)
    print("Response Status:", resp.status_code)
    print("Response Body:", resp.text)
except Exception as e:
    print("Error:", e)
