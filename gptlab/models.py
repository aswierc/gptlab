from pydantic import BaseModel


class Project(BaseModel):
    project_id: int
    name: str


class MergeRequest(BaseModel):
    merge_request_id: int
    merge_request_iid: int
    source_branch: str
    target_branch: str
    title: str


class Change(BaseModel):
    old_path: str
    new_path: str
    diff_gzip_base64_encoded: str
    file: str


class Changes(BaseModel):
    merge_request_iid: int
    project_id: int
    changes: list[Change]

