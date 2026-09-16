# Module Imports
import hashlib
import pathlib
import sys
from datetime import UTC, datetime

import sqlalchemy

from app.model_files import File, Folder, T_Actions
from app.progress import Progress

#from app.glue import file_db, file_db_prod

def check_files_for_removes( files: list[File], container_folder_path: pathlib.Path) -> int:
    #print( f"check_files_for_removes: {container_folder_path = } {files = }")
    dirty_cnt = 0
    for file in files:
        #print( f"{(container_folder_path / file.file_name) = }")
        if file.deleted_at is None and not (container_folder_path / file.file_name).is_file():
            print( f"NOT isfile {file.id} {(container_folder_path / file.file_name) = }")
            file.deleted_at=datetime.now( tz=UTC)
            dirty_cnt += 1
    return dirty_cnt

def check_folder_for_removes( db, folder: Folder, container_subtree_to_check_path: pathlib.Path) -> int:
    #print( f"check_for_removes: {folder = }")
    dirty_cnt = 0
    container_folder_path = db.host_to_container_path( folder.path)
    #print( f"check_folder_for_removes: {folder = } {container_folder_path = } {container_subtree_to_check_path = }")
    assert container_subtree_to_check_path in container_folder_path.parents or container_subtree_to_check_path == container_folder_path, f"SKIP {container_folder_path = } {folder.id = } not part of {container_subtree_to_check_path = }"
    #print( f"{db.root_in_container = } {container_folder_path = } {folder.id = }")
    if container_folder_path.is_dir():
        #print( folder.files)
        dirty_cnt += check_files_for_removes( folder.files, container_folder_path)
    else:
        print( f"check_folder_for_removes: delete_folder not isdir {folder.id} {container_folder_path}")
        folder.deleted_at=datetime.now( tz=UTC)
        dirty_cnt += 1
    return dirty_cnt

def check_for_removed_items( db, container_subtree_to_check_path: pathlib.Path, host_subtree_to_check_path: pathlib.Path, progress: Progress) -> None:
    print( f"check_for_removed_items: {container_subtree_to_check_path = }")
    with db.Session() as session:
        for folder in db.s_get_undeleted_folders( session, db.host_id, host_subtree_to_check_path):
            if 0 < check_folder_for_removes( db, folder, container_subtree_to_check_path):
                session.commit()
            if progress.tick( session):
                print( progress.status_msg())
                session.commit()
    print( "check_for_removed_items END")

def create_new_file( db, folder_id: int, file_name: str, file_stat, sha: bool, container_file_path: pathlib.Path) -> None:
    print( f"create_new_file: {file_name = }")
    file_hash = None
    if sha:
        file_hash = db.file_hash( container_file_path)
    file = db.create_file( folder_id, file_name, file_stat, file_hash)
    print( f"create_new_file: {file} NEW")
    return file

def check_for_new_or_updated_items( db, container_subtree_to_check: str, sha: bool, progress: Progress) -> None:
    print( f"check_for_new_or_updated_items: {container_subtree_to_check = }")
    for curr_container_path, dirs, files in pathlib.Path( container_subtree_to_check).walk(on_error=print):
        curr_host_path = db.container_to_host_path( curr_container_path)

        # if any subfolder is to be ignored, we can imediately remove him from visit list
        for idx in range( len( dirs)-1, -1, -1):
            if db.curr_path_is_ignored( curr_host_path / dirs[idx]):
                #print( f"check_for_new_or_updated_items: {idx} {(curr_host_path / dirs[idx])} is ignored DELETE from list")
                del dirs[idx]

        # current folder should have been eiminated from parent list, but maybe subtree was already to be avoided
        if db.curr_path_is_ignored( curr_host_path):
            print( f"check_for_new_or_updated_items: {curr_host_path = } is ignored")
            #assert False
            continue

        # folder is ok, check if we already know about it
        with db.Session() as session:
            host_hash = hashlib.md5( str(curr_host_path).encode()).hexdigest()
            folder = db.s_get_undeleted_folder_by_hash( session, db.host_id, host_hash)
            #print( f"check_for_new_or_updated_items: {folder = }")
            if folder is None:
                folder = db.s_create_folder( session, db.host_id, curr_host_path, host_hash)
                print( f"check_for_new_or_updated_items: NEW {folder = }")
            #folder_files = folder.files
            #print( f"check_for_new_or_updated_items: NEW {folder_files = }")
            for file_name in files:
                host_file_path = curr_host_path / file_name
                if db.curr_path_is_ignored( host_file_path):
                    #print( f"check_for_new_or_updated_items: {host_file_path = } FILE is ignored")
                    continue
                container_file_path = curr_container_path / file_name
                if container_file_path.is_file():
                    file_stat = container_file_path.lstat()
                    for file in folder.files:
                        if file.deleted_at is None and file.file_name == file_name:
                            if db.file_is_changed( file, file_stat):
                                print( f"check_for_new_or_updated_items: {curr_host_path / file_name} CHANGED")
                                file.deleted_at = datetime.now( tz=UTC)
                                file = create_new_file( db, folder.id, file_name, file_stat, sha, container_file_path)
                                session.add( file)
                                session.commit()
                            else:
                                if sha and file.file_hash is None:
                                    # file exists and is unchanged but hash should be computed, but is undefined
                                    file.file_hash = db.file_hash( container_file_path)
                                    session.commit()
                                    print( f"check_for_new_or_updated_items: {curr_host_path / file_name} {file.file_hash = } HASH added")
                            break # we found file existed in children of folder
                    else: # for loop not break: file is not in children of folder so it is new file
                        file = create_new_file( db, folder.id, file_name, file_stat, sha, container_file_path)
                        session.add( file)
                        session.commit()
                else:
                    if not container_file_path.is_symlink():
                        print( f"IS NOT file NOR link {container_file_path}")
        if progress.tick( session):
             print( progress.status_msg())
             if sha:
                 stmt = sqlalchemy.update(T_Actions).values( { 'add_missing_sha_progress': progress.percent}).where(T_Actions.id==progress.action_id)
                 session.execute( stmt)
                 session.commit()
    print( "check_for_new_or_updated_items END")

def main() -> int:
    return 0

if __name__ == '__main__':
    sys.exit(main())

