import base64
import gzip
import os
from urllib.parse import quote

import httpx
from dotenv import load_dotenv
from fastapi import HTTPException

from gptlab.models import Project, MergeRequest, Change, Changes

load_dotenv()

gitlab_api_url = os.environ.get("GITLAB_API_URL")
gitlab_personal_token = os.environ.get("GITLAB_PERSONAL_TOKEN")


class Client:
    async def projects(self) -> list[Project]:
        params = {
            "archived": "false",
            "per_page": 100,
            "membership": "true",
        }

        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(
                f"{gitlab_api_url}/projects", headers=self._headers, params=params
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail="Cannot fetch projects from GitLab.",
            )

        return [
            Project(project_id=project["id"], name=project["name_with_namespace"])
            for project in response.json()
        ]

    async def merge_requests(self, project_id: int) -> list[MergeRequest]:
        params = {
            "state": "opened",
        }

        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(
                f"{gitlab_api_url}/projects/{project_id}/merge_requests",
                headers=self._headers,
                params=params,
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code, detail=response.text
                )

            return [
                MergeRequest(
                    merge_request_id=mr["id"],
                    merge_request_iid=mr["iid"],
                    source_branch=mr["source_branch"],
                    target_branch=mr["target_branch"],
                    title=mr["title"],
                )
                for mr in response.json()
            ]

    async def merge_request_details(self, project_id: int, merge_request_iid: int) -> Changes:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(
                f"{gitlab_api_url}/projects/{project_id}/merge_requests/{merge_request_iid}/changes",
                headers=self._headers,
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code, detail=response.text
                )

            def encode(diff: str) -> str:
                compressed_data = gzip.compress(diff.encode())
                return base64.b64encode(compressed_data).decode()

            changes_data = response.json()
            changes = [
                Change(
                    old_path=change["old_path"],
                    new_path=change["new_path"],
                    file=change["new_path"],
                    diff_gzip_base64_encoded=encode(change["diff"]),
                )
                for change in changes_data["changes"]
            ]

            return Changes(
                merge_request_iid=merge_request_iid,
                project_id=project_id,
                changes=changes,
            )

    async def get_file_content(self, project_id: int, file_path: str, branch: str) -> str:
        encoded_file_path = quote(file_path, safe="")

        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(
                f"{gitlab_api_url}/projects/{project_id}/repository/files/{encoded_file_path}/raw",
                headers=self._headers,
                params={"ref": branch},
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail="Cannot fetch file content from GitLab.",
            )

        return response.text

    @property
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {gitlab_personal_token}"}
