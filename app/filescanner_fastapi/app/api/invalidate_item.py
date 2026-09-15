from fastapi import APIRouter, Query
from fastapi_pagination import Page

from app.alchemyModelFiles import PutAction, PutHost, PutIgnore, T_Actions, T_Hosts, T_Ignores
from app.alchemyFilesDB import _clean_up_ignored
import sqlalchemy
from .common import Tags
from ..glue import file_db

router = APIRouter()

@router.post("/v1/invalidate/files/{file_id}", tags=[Tags.files])
def invalidate_file_item(file_id: int) -> int:
    #print( f"invalidate_file_item: {file_id = }")
    with file_db.Session() as session:
        results = session.execute( sqlalchemy.update(T_Files).where(T_Files.id==file_id).values({'deleted_at': datetime.now( tz=UTC)}))
        assert results.rowcount <= 1
        session.commit()
        #print( f"invalidate_file_item: {results.rowcount = }")
        return results.rowcount

def invalidate_action_item(action_id: int, tags=[Tags.actions]) -> int: # noqa: B006
    print( f"invalidate_action_item: {action_id = }")
    with file_db.Session() as session:
        results = session.execute( sqlalchemy.update(T_Actions).where(T_Actions.id==action_id).values({'deleted_at': datetime.now( tz=UTC)}))
        assert results.rowcount <= 1
        session.commit()
        #print( f"invalidate_action_item: {results.rowcount = }")
        return results.rowcount

def invalidate_folder_item(folder_id: int, tags=[Tags.folders]) -> int: # noqa: B006
    print( f"invalidate_folder_item: {folder_id = }")
    with file_db.Session() as session:
        results = session.execute( sqlalchemy.update(T_Folders).where(T_Folders.id==folder_id).values({'deleted_at': datetime.now( tz=UTC), 'updated_at': datetime.now( tz=UTC), 'created_at': datetime.now( tz=UTC), }))
        assert results.rowcount <= 1
        session.commit()
        #print( f"invalidate_folder_item: {results.rowcount = }")
        return results.rowcount

