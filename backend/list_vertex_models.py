import os
import requests
import google.auth
from google.oauth2 import service_account
from google.auth.transport.requests import Request

sa_path = "gcp-service-account.json"
scopes = ["https://www.googleapis.com/auth/cloud-platform"]
project_id = "gen-lang-client-0553507358"
location = "us-central1"

try:
    creds = service_account.Credentials.from_service_account_file(sa_path, scopes=scopes)
    creds.refresh(Request())
    
    # Try listing models
    url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{location}/models"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {creds.token}"
    }
    resp = requests.get(url, headers=headers, timeout=10)
    print("Response Status (Models):", resp.status_code)
    print("Response Body (Models):", resp.text[:1000])
except Exception as e:
    print("Error:", e)
