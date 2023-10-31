from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.gzip import GZipMiddleware
import httpx
from dotenv import load_dotenv
import os
import gzip
import base64
from pydantic import BaseModel


app = FastAPI()

app.mount("/.well-known", StaticFiles(directory=".well-known"), name="well-known")
app.mount("/static", StaticFiles(directory="static"), name="static")

# app.add_middleware(CompressionMiddleware, minimum_size=1000)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://chat.openai.com",
        "http://localhost",
        "http://127.0.0.1",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

load_dotenv()

gitlab_api_url = os.environ.get("GITLAB_API_URL")
gitlab_personal_token = os.environ.get("GITLAB_PERSONAL_TOKEN")


class Change(BaseModel):
    old_path: str
    new_path: str
    diff_gzip_base64_encoded: str


class ChangesResponse(BaseModel):
    merge_request_iid: int
    project_id: int
    changes: list[Change]


@app.get("/ping")
async def get_ping_pong():
    return {"pong": "true"}


@app.get("/gitlab-projects")
async def get_gitlab_projects():
    headers = {"Authorization": f"Bearer {gitlab_personal_token}"}
    params = {
        "archived": "false",
        "per_page": 100,
        "membership": "true",
    }

    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(
            f"{gitlab_api_url}/projects", headers=headers, params=params
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail="Cannot fetch projects from GitLab.",
        )

    return [
        {
            'project_id': project['id'],
            'name': project['name_with_namespace'],
        }
        for project in response.json()
    ]


@app.get("/gitlab-projects/{project_id}/merge_requests")
async def get_gitlab_merge_requests(project_id: int):
    headers = {
        "Authorization": f"Bearer {gitlab_personal_token}",
    }
    params = {
        "state": "opened",
    }

    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(
            f"{gitlab_api_url}/projects/{project_id}/merge_requests",
            headers=headers,
            params=params,
        )

        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)

        return [
            {
                'merge_request_id': mr['id'],
                'merge_request_iid': mr['iid'],
                'source_branch': mr['source_branch'],
                'target_branch': mr['target_branch'],
                'title': mr['title'],
            }
            for mr in response.json()
        ]


@app.get("/gitlab-projects/{project_id}/merge_requests/{merge_request_iid}/changes", response_model=ChangesResponse)
async def get_gitlab_merge_request_changes(project_id: int, merge_request_iid: int):
    headers = {
        "Authorization": f"Bearer {gitlab_personal_token}",
    }

    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(
            f"{gitlab_api_url}/projects/{project_id}/merge_requests/{merge_request_iid}/changes",
            headers=headers,
        )

        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)

        def encode(diff: str) -> str:
            compressed_data = gzip.compress(diff.encode())
            return base64.b64encode(compressed_data).decode()

        changes_data = response.json()
        changes = [
            {
                'old_path': change['old_path'],
                'new_path': change['new_path'],
                'file': change['new_path'],
                'diff_gzip_base64_encoded': encode(change['diff']),
            }
            for change in changes_data["changes"]
        ]

        return {
            'merge_request_iid': merge_request_iid,
            'project_id': project_id,
            'changes': changes,
        }
