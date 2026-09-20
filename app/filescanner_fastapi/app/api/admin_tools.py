import pathlib

from fastapi import APIRouter

from app.model_files import T_Files, T_Folders  # Base, File, T_Actions, , T_Hosts, T_Ignores

from ..glue import file_db
from .common import Tags

router = APIRouter()

@router.get("/dev/curr_host/ignores/cleanup", tags=[Tags.admin])
def dev_clean_up_ignored() -> None:
    with file_db.Session() as session:
        _clean_up_ignored( file_db, session, file_db.host_id, file_db.curr_ignores)

def _clean_up_ignored( file_db, session, host_id: int, ignores: list[str]) -> None:
    #ignore_starts = sorted( list( set( [file_db.ignored_to_startswith( ignore) for ignore in ignores])))
    ignore_starts = sorted( { file_db.ignored_to_startswith( ignore) for ignore in ignores})
    for ignore_start in ignore_starts:
        #print( f"_clean_up_ignored: {ignore_start = } ")
        for folder in file_db.s_get_undeleted_folders( session, host_id, ignore_start, reverse=True):
            #print( f"{folder = } ")
            #if self.debug: print( f"_clean_up_ignored: {host_id = } {folder.path = }")
            if file_db.path_is_ignored( folder.path, ignores):
                #print( f"_clean_up_ignored: {host_id = } deleting {folder.path = }")
                #print( f"{folder.files = }")
                #return
                #for file_id, file_name in self.all_files( conn, folder.id):
                    #print( f"_clean_up_ignored: {host_id = } deleting {folder.path = } {file_name = } {file_id = }")
                    #self.delete_file_id( conn, file_id)
                session.query( T_Folders).where( T_Folders.id==folder.id).delete()
            #print( f"{folder.files = } ")
            for file in folder.files:
                #print( f"{file = } ")
                container_file_path = pathlib.Path( folder.path, file.file_name)
                if file.deleted_at is None and file_db.path_is_ignored( container_file_path, ignores):
                    #print( f"{folder = } ")
                    #print( f"{file = } ")
                    #print( f"{file.folder = } ")
                    #print( f"_clean_up_ignored: deleting {container_file_path = } {file.file_name = }")
                    #file.delete()
                    session.query( T_Files).where( T_Files.id==file.id).delete()
        session.commit()
    #session.commit()
