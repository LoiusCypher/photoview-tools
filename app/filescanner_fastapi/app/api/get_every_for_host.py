from fastapi import APIRouter, Query
from fastapi_pagination import Page
from app.alchemyModelFiles import Action, File, Folder, Host, Ignore, T_Actions, T_Files, T_Folders, T_Hosts, T_Ignores
from fastapi_pagination.ext.sqlalchemy import paginate
import sqlalchemy
from .common import Tags, SortActionField, SortFileField, SortFolderField, SortIgnoreField, SortOrder
from ..glue import file_db

router = APIRouter()

@router.get("/v1/hosts/{host_id}/actions", tags=[Tags.actions])
def get_host_actions(host_id: int) -> Page[Action]:
    with file_db.Session() as session:
        return paginate( session, sqlalchemy.select( T_Actions).where(T_Actions.host_id==host_id).order_by( T_Actions.updated_at))

@router.get("/v1/hosts/{host_id}/ignores", tags=[Tags.ignores])
def get_host_ignores(host_id: int) -> Page[Ignore]:
    with file_db.Session() as session:
        return paginate( session, sqlalchemy.select( T_Ignores).where(T_Ignores.host_id==host_id).order_by( T_Ignores.path_pattern))

@router.get("/v1/hosts/{host_id}/folders", tags=[Tags.folders])
def get_host_folders( host_id: int, sort_by: SortFolderField = Query(SortFolderField.path), sort_order: SortOrder = Query(SortOrder.asc),) -> Page[Folder]:
    query = sqlalchemy.select( T_Folders).where(T_Folders.host_id==host_id)
    sort_column = getattr(T_Folders, sort_by.value)
    if sort_order == SortOrder.desc:
        query = query.order_by( sqlalchemy.desc(sort_column))
    else:
        query = query.order_by( sqlalchemy.asc(sort_column))
    with file_db.Session() as session:
        return paginate( session, query.order_by( T_Folders.path))

