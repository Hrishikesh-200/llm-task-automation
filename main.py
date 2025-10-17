import base64
import traceback
import json
import uuid
from fastapi import FastAPI, HTTPException, Request
from github import Github, GithubException
import os
import requests

# -------------------------------
# CONFIGURATION
# -------------------------------
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")  # Add your fine-grained PAT in env
GITHUB_USER = "Hrishikesh-200"
GITHUB_REPO = "llm-task-automation"
SECRET_KEY = "hris@tds_proj1_term3"

# LLM API (AIPipe/OpenRouter)
AIPIPE_TOKEN = os.environ.get("AIPIPE_API_KEY")  # put your token in env

app = FastAPI()

# -------------------------------
# GITHUB HELPER FUNCTIONS
# -------------------------------
def get_repo():
    gh = Github(GITHUB_TOKEN)
    try:
        repo = gh.get_repo(f"{GITHUB_USER}/{GITHUB_REPO}")
        return repo
    except GithubException as e:
        raise HTTPException(status_code=404, detail=f"GitHub repo error: {str(e)}")

def push_html_to_gh_pages(html_content):
    from github import Github, GithubException

    # ✅ Ensure html_content is a string
    if not isinstance(html_content, str):
        import json
        html_content = json.dumps(html_content, indent=2)

    repo_name = "Hrishikesh-200/llm-task-automation"
    branch = "main"
    file_name = "index.html"

    github_token = os.getenv("GITHUB_TOKEN")
    g = Github(github_token)
    repo = g.get_repo(repo_name)

    try:
        contents = repo.get_contents(file_name, ref=branch)
        repo.update_file(
            contents.path,
            f"Update {file_name}",
            html_content,
            contents.sha,
            branch=branch,
        )
    except GithubException as e:
        if e.status == 404:
            repo.create_file(file_name, f"Create {file_name}", html_content, branch=branch)
        else:
            raise

    # Construct public GitHub Pages URL
    pages_url = f"https://{repo_name.split('/')[0]}.github.io/{repo_name.split('/')[1]}/"
    return {"status": "success", "html_url": pages_url}


# -------------------------------
# LLM HELPER
# -------------------------------
def call_llm(brief: str, attachments: list = []):
    if not AIPIPE_TOKEN:
        raise HTTPException(status_code=500, detail="AIPipe token missing")
    headers = {
        "Authorization": f"Bearer {AIPIPE_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "openai/gpt-4.1-nano",
        "input": brief
    }
    try:
        response = requests.post("https://aipipe.org/openrouter/v1/responses", headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        # Assume the LLM returns the HTML in data["output"][0]["content"]
        html_content = data.get("output", [{}])[0].get("content", "<h1>LLM did not return content</h1>")
        return html_content
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"LLM call failed: {str(e)}")

# -------------------------------
# TASK HANDLERS
# -------------------------------
def handle_round1(task_data):
    html_content = call_llm(task_data["brief"], task_data.get("attachments", []))
    return push_html_to_gh_pages(html_content)

def handle_round2(task_data):
    html_content = call_llm(task_data["brief"], task_data.get("attachments", []))
    return push_html_to_gh_pages(html_content)

# -------------------------------
# API ENDPOINTS
# -------------------------------
@app.post("/run_task")
async def run_task(request: Request):
    try:
        data = await request.json()
        print("Received JSON:", data)
        # Secret check
        if data.get("secret", "").lower() != SECRET_KEY:
            raise HTTPException(status_code=401, detail="Unauthorized: Invalid secret")

        round_idx = data.get("round", 1)
        if round_idx == 1:
            result = handle_round1(data)
        else:
            result = handle_round2(data)

        # Return evaluator response
        return {
            "email": data.get("email"),
            "task": data.get("task"),
            "round": round_idx,
            "nonce": data.get("nonce"),
            **result
        }
    except Exception as e:
        print("Error processing task:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ping")
async def ping():
    return {"status": "ok"}
