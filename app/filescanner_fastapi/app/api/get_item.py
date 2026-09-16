import sqlalchemy
from fastapi import APIRouter

from app.model_files import T_Actions, T_Files, T_Folders, T_Hosts, T_Ignores

from ..glue import file_db
from .common import Tags

router = APIRouter()

@router.delete("/v1/hosts/{host_id}", tags=[Tags.hosts])
def delete_host_item(host_id: int) -> int:
    with file_db.Session() as session:
        results = session.execute( sqlalchemy.delete(T_Hosts).where(T_Hosts.id==host_id))
        assert results.rowcount <= 1
        session.commit()
        #print( f"delete_action_item: {results.rowcount = }")
        return results.rowcount

@router.delete("/v1/actions/{action_id}", tags=[Tags.actions])
def delete_action_item(action_id: int) -> int:
    with file_db.Session() as session:
        results = session.execute( sqlalchemy.delete(T_Actions).where(T_Actions.id==action_id))
        assert results.rowcount <= 1
        session.commit()
        #print( f"delete_action_item: {results.rowcount = }")
        return results.rowcount

@router.delete("/v1/ignores/{ignore_id}", tags=[Tags.ignores])
def delete_ignore_item(ignore_id: int) -> int:
    with file_db.Session() as session:
        results = session.execute( sqlalchemy.delete(T_Ignores).where(T_Ignores.id==ignore_id))
        assert results.rowcount <= 1
        session.commit()
        #print( f"delete_ignore_item: {results.rowcount = }")
        return results.rowcount

@router.delete("/v1/folders/{folder_id}", tags=[Tags.folders])
def delete_folder_item(folder_id: int) -> int:
    with file_db.Session() as session:
        results = session.execute( sqlalchemy.delete(T_Folders).where(T_Folders.id==folder_id))
        assert results.rowcount <= 1
        session.commit()
        #print( f"delete_folder_item: {results.rowcount = }")
        return results.rowcount

@router.delete("/v1/files/{file_id}", tags=[Tags.files])
def delete_file_item(file_id: int) -> int:
    with file_db.Session() as session:
        results = session.execute( sqlalchemy.delete(T_Files).where(T_Files.id==file_id))
        assert results.rowcount <= 1
        session.commit()
        #print( f"delete_file_item: {results.rowcount = }")
        return results.rowcount

