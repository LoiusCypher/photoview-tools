import sqlalchemy
from fastapi import APIRouter
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate

from app.model_files import File, T_Files, T_Folders

from ..glue import file_db
from .common import Tags

router = APIRouter()

@router.get("/v1/hosts/{host_id}/folders/path_list", tags=[Tags.pathlist])
def get_host_folders_pathlist(host_id: int) -> Page[str]:
    with file_db.Session() as session:
        return paginate( session, sqlalchemy.select( T_Folders.path).where(T_Folders.host_id==host_id, T_Folders.deleted_at==None).order_by( T_Folders.path), unwrap_mode="unwrap",)

@router.get("/v1/hosts/{host_id}/files/path_list", tags=[Tags.pathlist])
def get_host_files_pathlist(host_id: int) -> Page[str]:
    with file_db.Session() as session:
        return paginate( session, sqlalchemy.select( T_Folders.path, T_Files.file_name).join( T_Folders.files).where(T_Folders.host_id==host_id, T_Folders.deleted_at==None).order_by( T_Folders.path, T_Files.file_name), unwrap_mode="unwrap",)

@router.get("/v1/folders/{folder_id}/files", tags=[Tags.pathlist])
def get_folder_files(folder_id: int) -> Page[File]:
    with file_db.Session() as session:
        return paginate( session, sqlalchemy.select( T_Files).where(T_Files.folder_id==folder_id).order_by( T_Files.length))

