from fastapi import APIRouter, Query
from fastapi_pagination import Page
from app.alchemyModelFiles import Action, File, Folder, Host, Ignore, T_Actions, T_Files, T_Folders, T_Hosts, T_Ignores
from fastapi_pagination.ext.sqlalchemy import paginate
import sqlalchemy
from .common import Tags, SortActionField, SortFileField, SortFolderField, SortIgnoreField, SortOrder
from ..glue import file_db

router = APIRouter()

@router.get("/v1/hosts", tags=[Tags.hosts])
def get_hosts() -> Page[Host]:
    with file_db.Session() as session:
        return paginate( session, sqlalchemy.select( T_Hosts).order_by( T_Hosts.id))

@router.get("/v1/actions", tags=[Tags.actions])
def get_actions(sort_by: SortActionField = Query(SortActionField.started_at), sort_order: SortOrder = Query(SortOrder.asc),) -> Page[Action]:
    query = sqlalchemy.select( T_Actions)
    sort_column = getattr(T_Actions, sort_by.value)
    if sort_order == SortOrder.desc:
        query = query.order_by( sqlalchemy.desc(sort_column))
    else:
        query = query.order_by( sqlalchemy.asc(sort_column))
    with file_db.Session() as session:
        return paginate( session, query.order_by( T_Actions.host_id, T_Actions.updated_at))

@router.get("/v1/ignores", tags=[Tags.ignores])
def get_ignores(sort_by: SortIgnoreField = Query(SortIgnoreField.path_pattern), sort_order: SortOrder = Query(SortOrder.asc),) -> Page[Ignore]:
    query = sqlalchemy.select( T_Ignores)
    sort_column = getattr(T_Ignores, sort_by.value)
    if sort_order == SortOrder.desc:
        query = query.order_by( sqlalchemy.desc(sort_column))
    else:
        query = query.order_by( sqlalchemy.asc(sort_column))
    with file_db.Session() as session:
        return paginate( session, query.order_by( T_Ignores.path_pattern, T_Ignores.updated_at))

@router.get("/v1/folders", tags=[Tags.folders])
def get_folders( sort_by: SortFolderField = Query(SortFolderField.path), sort_order: SortOrder = Query(SortOrder.asc),) -> Page[Folder]:
    query = sqlalchemy.select( T_Folders)
    sort_column = getattr(T_Folders, sort_by.value)
    if sort_order == SortOrder.desc:
        query = query.order_by( sqlalchemy.desc(sort_column))
    else:
        query = query.order_by( sqlalchemy.asc(sort_column))
    with file_db.Session() as session:
        return paginate( session, query.order_by( T_Folders.host_id, T_Folders.path))

@router.get("/v1/files", tags=[Tags.files])
def get_files(sort_by: SortFileField = Query(SortFileField.file_name), sort_order: SortOrder = Query(SortOrder.asc),) -> Page[File]:
    with file_db.Session() as session:
        return paginate( session, sqlalchemy.select( T_Files).order_by( T_Files.length))

