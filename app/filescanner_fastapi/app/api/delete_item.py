from fastapi import APIRouter, Query
from fastapi_pagination import Page
from app.alchemyModelFiles import Action, File, Folder, Host, Ignore, T_Actions, T_Files, T_Folders, T_Hosts, T_Ignores
from fastapi_pagination.ext.sqlalchemy import paginate
import sqlalchemy
from .common import Tags, SortActionField, SortFileField, SortFolderField, SortIgnoreField, SortOrder
from ..glue import file_db

router = APIRouter()

@router.get("/v1/hosts/{host_id}", tags=[Tags.hosts])
def get_host_item(host_id: int) -> Host | None:
    with file_db.Session() as session:
        return session.get( T_Hosts, host_id)

@router.get("/v1/actions/{action_id}", tags=[Tags.actions])
def get_action(action_id: int) -> Action | None:
    with file_db.Session() as session:
        return session.get( T_Actions, action_id)

@router.get("/v1/ignores/{ignore_id}", tags=[Tags.ignores])
def get_ignore_item(ignore_id: int) -> Ignore | None:
    with file_db.Session() as session:
        return session.get( T_Ignores, ignore_id)

@router.get("/v1/folders/{folder_id}", tags=[Tags.folders])
def get_folder_item(folder_id: int) -> Folder | None:
    with file_db.Session() as session:
        return session.get( T_Folders, folder_id)

@router.get("/v1/files/{file_id}", tags=[Tags.files])
def get_files_item(file_id: int) -> File | None:
    with file_db.Session() as session:
        return session.get( T_Files, file_id)

