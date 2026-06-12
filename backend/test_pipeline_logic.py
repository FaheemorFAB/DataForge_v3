import os
import logging
import requests
import json
from pathlib import Path

# Setup simple logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_pipeline")

# Mock the ROOT_DIR
ROOT_DIR = Path(__file__).resolve().parent / "dataforge"

def _get_sa_path() -> str | None:
    # Check both GOOGLE_SERVICE_ACCOUNT_JSON and GOOGLE_APPLICATION_CREDENTIALS
    for env_var in ["GOOGLE_SERVICE_ACCOUNT_JSON", "GOOGLE_APPLICATION_CREDENTIALS"]:
        val = os.getenv(env_var)
        if val:
            val = val.strip('"\'')
            # 1. Try absolute / direct path
            p = Path(val)
            if p.exists():
                return str(p.resolve())
            # 2. Try relative to PROJECT_ROOT (ROOT_DIR.parent)
            p_proj = ROOT_DIR.parent.parent / val
            if p_proj.exists():
                return str(p_proj.resolve())
            # 3. Try relative to ROOT_DIR
            p_root = ROOT_DIR.parent / val
            if p_root.exists():
                return str(p_root.resolve())
            # 4. Fallback search in project root if filename matches
            filename = p.name
            if filename:
                fb_root = ROOT_DIR.parent.parent / filename
                if fb_root.exists():
                    return str(fb_root.resolve())
    return None

def _gemini(prompt: str, temperature: float = 0.1, timeout: int = 10) -> str:
    sa_path = _get_sa_path()
    if sa_path:
        print(f"Using Service Account: {sa_path}")
        try:
            from google.oauth2 import service_account
            from google.auth.transport.requests import Request
            
            scopes = ["https://www.googleapis.com/auth/cloud-platform"]
            creds = service_account.Credentials.from_service_account_file(sa_path, scopes=scopes)
            creds.refresh(Request())
            
            with open(sa_path, "r") as f:
                sa_data = json.load(f)
            project_id = sa_data.get("project_id")
            location = "us-central1"
            
            url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{location}/publishers/google/models/gemini-2.5-flash:generateContent"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {creds.token}"
            }
            payload = {
                "contents": [{
                    "role": "user",
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": 2048
                }
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=timeout)
            if response.status_code != 200:
                raise RuntimeError(f"Vertex AI API error: {response.text}")
                
            data = response.json()
            candidates = data.get("candidates", [])
            if not candidates:
                return ""
            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                return ""
            return parts[0].get("text", "")
            
        except Exception as e:
            logger.error(f"Vertex AI API call failed: {e}")
            raise
    else:
        print("Using GEMINI_API_KEY (AI Studio fallback)")
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Neither GOOGLE_SERVICE_ACCOUNT_JSON nor GEMINI_API_KEY is configured.")
            
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": api_key
        }
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 2048
            }
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
        if resp.status_code != 200:
            raise RuntimeError(f"Gemini API error: {resp.text}")
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"]

if __name__ == "__main__":
    # Test 1: Set environment variables and test Vertex REST API
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "backend/gcp-service-account.json"
    print("--- Test 1 (with GOOGLE_APPLICATION_CREDENTIALS) ---")
    try:
        res = _gemini("Explain quantum computing in 1 sentence.")
        print("Result:", res)
    except Exception as e:
        print("Test 1 Failed:", e)
        
    # Test 2: Test fallback to GEMINI_API_KEY if SA path is cleared
    os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
    os.environ.pop("GOOGLE_SERVICE_ACCOUNT_JSON", None)
    print("\n--- Test 2 (with GEMINI_API_KEY fallback) ---")
    try:
        # Load env key from env file manually for test
        with open("backend/.env", "r") as f:
            for l in f:
                if l.startswith("GEMINI_API_KEY="):
                    key = l.split("=")[1].strip().strip('"\'')
                    os.environ["GEMINI_API_KEY"] = key
                    break
        res = _gemini("Explain quantum computing in 1 sentence.")
        print("Result:", res)
    except Exception as e:
        print("Test 2 Failed:", e)
