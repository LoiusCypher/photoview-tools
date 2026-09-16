import sqlalchemy
from fastapi import APIRouter, Query
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate

from app.model_files import Action, File, Folder, Host, Ignore, T_Actions, T_Files, T_Folders, T_Hosts, T_Ignores

from ..glue import file_db
from .common import SortActionField, SortFileField, SortFolderField, SortIgnoreField, SortOrder, Tags

router = APIRouter()

@router.get("/v1/hosts", tags=[Tags.hosts])
def get_hosts() -> Page[Host]:
    with file_db.Session() as session:
        return paginate( session, sqlalchemy.select( T_Hosts).order_by( T_Hosts.id))

@router.get("/v1/actions", tags=[Tags.actions])
def get_actions(sort_by: SortActionField | None = None, sort_order: SortOrder | None = None,) -> Page[Action]:
    if sort_by is None:
        sort_by = Query(SortActionField.started_at)
    if sort_order is None:
        sort_order = Query(SortOrder.asc)
    query = sqlalchemy.select( T_Actions)
    sort_column = getattr(T_Actions, sort_by.value)
    if sort_order == SortOrder.desc:
        query = query.order_by( sqlalchemy.desc(sort_column))
    else:
        query = query.order_by( sqlalchemy.asc(sort_column))
    with file_db.Session() as session:
        return paginate( session, query.order_by( T_Actions.host_id, T_Actions.updated_at))

@router.get("/v1/ignores", tags=[Tags.ignores])
def get_ignores(sort_by: SortIgnoreField | None = None, sort_order: SortOrder | None = None,) -> Page[Ignore]:
    if sort_by is None:
        sort_by = Query(SortIgnoreField.path_pattern)
    if sort_order is None:
        sort_order = Query(SortOrder.asc)
    query = sqlalchemy.select( T_Ignores)
    sort_column = getattr(T_Ignores, sort_by.value)
    if sort_order == SortOrder.desc:
        query = query.order_by( sqlalchemy.desc(sort_column))
    else:
        query = query.order_by( sqlalchemy.asc(sort_column))
    with file_db.Session() as session:
        return paginate( session, query.order_by( T_Ignores.path_pattern, T_Ignores.updated_at))

@router.get("/v1/folders", tags=[Tags.folders])
def get_folders( sort_by: SortFolderField | None = None, sort_order: SortOrder | None = None,) -> Page[Folder]:
    if sort_by is None:
        sort_by = Query(SortFolderField.path)
    if sort_order is None:
        sort_order = Query(SortOrder.asc)
    query = sqlalchemy.select( T_Folders)
    sort_column = getattr(T_Folders, sort_by.value)
    if sort_order == SortOrder.desc:
        query = query.order_by( sqlalchemy.desc(sort_column))
    else:
        query = query.order_by( sqlalchemy.asc(sort_column))
    with file_db.Session() as session:
        return paginate( session, query.order_by( T_Folders.host_id, T_Folders.path))

@router.get("/v1/files", tags=[Tags.files])
def get_files(sort_by: SortFileField | None = None, sort_order: SortOrder | None = None,) -> Page[File]:
    if sort_by is None:
        sort_by = Query(SortFileField.file_name)
    if sort_order is None:
        sort_order = Query(SortOrder.asc)
    with file_db.Session() as session:
        return paginate( session, sqlalchemy.select( T_Files).order_by( T_Files.length))

