from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.gzip import GZipMiddleware
import httpx
from dotenv import load_dotenv
import os
from gptlab.gitlab import Client
from gptlab.models import Project, MergeRequest, Changes

app = FastAPI()

app.mount("/.well-known", StaticFiles(directory=".well-known"), name="well-known")
app.mount("/static", StaticFiles(directory="static"), name="static")

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


gitlab_client = Client()

@app.get("/gitlab-projects", response_model=list[Project])
async def get_gitlab_projects():
    return await gitlab_client.projects()


@app.get("/gitlab-projects/{project_id}/merge_requests", response_model=list[MergeRequest])
async def get_gitlab_merge_requests(project_id: int):
    return await gitlab_client.merge_requests(project_id)


@app.get("/gitlab-projects/{project_id}/merge_requests/{merge_request_iid}/changed_files")
async def get_gitlab_merge_request_changed_files(project_id: int, merge_request_iid: int):
    changes = await gitlab_client.merge_request_details(project_id, merge_request_iid)

    return [change.file for change in changes.changes]


@app.get("/gitlab-projects/{project_id}/merge_requests/{merge_request_iid}/changes", response_model=Changes)
async def get_gitlab_merge_request_changes(project_id: int, merge_request_iid: int):
    return await gitlab_client.merge_request_details(project_id, merge_request_iid)

@app.get("/gitlab-projects/{project_id}/branch/{source_branch}/files/{file_path:path}")
async def get_file_content(project_id: int, source_branch: str, file_path: str):
    return await gitlab_client.get_file_content(project_id, file_path, source_branch)
