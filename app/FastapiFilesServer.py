# Module Imports
import hashlib
import os
import pathlib
import sys
import sqlalchemy
from sqlalchemy.ext.automap import automap_base
from alchemyModelFiles import Base, T_Hosts, Host, PutHost, T_Actions, Action, PutAction, T_Ignores, Ignore, PutIgnore, T_Folders, Folder, T_Files, File
from alchemyFilesDB import FilesDB

from fastapi import FastAPI
from fastapi_utilities import repeat_every
from fastapi_pagination import Page, add_pagination #, paginate
from fastapi_pagination.ext.sqlalchemy import paginate # as pag
from typing import List, Optional, Union
from pydantic import BaseModel, StrictInt, Field
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from progress import Progress

def curr_host_set_actions_inactive():
    with file_db.Session() as session:
        stmt = sqlalchemy.select(T_Actions).where( T_Actions.host_id==file_db.host_id, T_Actions.started_at!=None, T_Actions.deleted_at==None)
        for action in session.scalars( stmt): #.all():
            #print( f"curr_host_set_actions_inactive: {action}")
            action.started_at = None
        session.commit()


#@app.on_event("startup")
@repeat_every(seconds=30, wait_first=True, raise_exceptions=True)
def check_for_pending_actions() -> None:
    #print("CHECK START")
    scan_action = get_next_pending_action()
    if scan_action is None:
        #print("NO CHECK")
        return None
    #print( f"{scan_action = }")
    start = datetime.now()
    file_db.fix_folder_depth()
    print( f"check_for_pending_actions: {scan_action.subtree = }")
    if scan_action.subtree is None:
        container_subtree_to_check = file_db.root_in_container
        #print( f"1 {container_subtree_to_check = }")
    else:
        if file_db.is_container_path( scan_action.subtree):
            container_subtree_to_check = scan_action.subtree
            print( f"2 {container_subtree_to_check = }")
        else:
            container_subtree_to_check = file_db.host_to_container_path( scan_action.subtree)
    with file_db.Session() as session:
        host_subtree = file_db.container_to_host_path( container_subtree_to_check)
        stmt = sqlalchemy.select( sqlalchemy.func.count()).select_from( T_Folders).where( T_Folders.host_id==file_db.host_id, T_Folders.path.startswith(host_subtree), T_Folders.deleted_at==None)
        folder_cnt = max( 1, session.scalar( stmt))
    progress = Progress( resolution=10, ranges=[ 0, 100],  counts=[ folder_cnt,])
    if scan_action.for_removed and scan_action.for_new_or_updated:
        progress = Progress( resolution=10, ranges=[ 0, 5, 100], counts=[ folder_cnt, folder_cnt,])
    if scan_action.for_removed:
        progress.start_next()
        folder_cnt = check_for_removed_items( file_db, container_subtree_to_check, progress)
        #print(" check_for_pending_actions: done", container_subtree_to_check)
    if scan_action.for_new_or_updated:
        progress.start_next()
        check_for_new_or_updated_items( file_db, container_subtree_to_check, scan_action.add_missing_sha, progress)
        #print(" check_for_new_or_updated_items: done", container_subtree_to_check, "with SHA" if scan_action.add_missing_sha else "")
    assert invalidate_action_item( scan_action.id) == 1
    b = datetime.now()
    print("CHECK DONE", b-start)

@asynccontextmanager
async def lifespan(app: FastAPI):
    curr_host_set_actions_inactive()
    await check_for_pending_actions()
    yield


curr_hostname = os.environ['CURR_HOSTNAME']
#print(f"{curr_hostname}")
assert curr_hostname is not None
mariadb_conn = os.environ['MARIADB_CONN']
#print(f"{mariadb_conn}")
assert mariadb_conn is not None

files_db_name = "files_collector"
tools_db_name = "object_detector"
photo_db_name = "photoview"
host_fs='/host_fs'
app = FastAPI(lifespan=lifespan)
add_pagination(app)
file_db_prod = FilesDB( curr_hostname, host_fs, mariadb_conn, 'db_files_prod')
file_db = FilesDB( curr_hostname, host_fs, mariadb_conn, 'db_files_dev')


@app.get("/dev/ignores/cleanup")
def dev_clean_up_ignored() -> None:
    with file_db.Session() as session:
        _clean_up_ignored( session, file_db.host_id, file_db.curr_ignores)

def _clean_up_ignored( session, host_id: int, ignores: List[str]) -> None:
    ignore_starts = sorted( list( set( [file_db.ignored_to_startswith( ignore) for ignore in ignores])))
    for ignore_start in ignore_starts:
        #print( f"_clean_up_ignored: {ignore_start = } ")
        for folder in file_db.s_get_undeleted_folders( session, host_id=host_id, reverse=True, startswith=ignore_start):
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
                file_path_ = pathlib.Path( folder.path, file.file_name)
                if file.deleted_at is None and file_db.path_is_ignored( file_path_, ignores):
                    #print( f"{folder = } ")
                    #print( f"{file = } ")
                    #print( f"{file.folder = } ")
                    #print( f"_clean_up_ignored: deleting {file_path_ = } {file.file_name = }")
                    #file.delete()
                    session.query( T_Files).where( T_Files.id==file.id).delete()
        session.commit()
    #session.commit()

@app.get("/tmpcopy/hosts")
def get_hosts() -> None:
    old_base = automap_base()
    old_engine = sqlalchemy.create_engine("mariadb+mariadbconnector://photoview:photosecret@192.168.2.227:3306/files_collector")
    old_base.prepare(old_engine, reflect=False)

    #new_engine=file_db.engine
    #Session = sqlalchemy.orm.sessionmaker()
    ##Session.configure(bind=file_db.engine)
    #new_session = Session( bind=new_engine)
    with file_db.Session() as new_session:
        with file_db.engine.connect() as conn:
                stmt = sqlalchemy.delete(T_Files)
                result = conn.execute( stmt)
                conn.commit()
                for depth in [ 75, 60, 45, 30, 15, 0 ]:
                    print( depth)
                    stmt = sqlalchemy.delete(T_Folders).where( sqlalchemy.text(f"depth>{depth}"))
                    result = conn.execute( stmt)
                    conn.commit()
                stmt = sqlalchemy.delete(T_Actions)
                result = conn.execute( stmt)
                conn.commit()
                stmt = sqlalchemy.delete(T_Ignores)
                result = conn.execute( stmt)
                conn.commit()
                stmt = sqlalchemy.delete(T_Hosts)
                result = conn.execute( stmt)
                conn.commit()

        with old_engine.connect() as conn:
            rows = conn.execute( sqlalchemy.select(T_Hosts)).all()
        print( f"Old Hosts:", len( rows))
        new_data = []
        for result in rows:
                new = T_Hosts()
                new.id = result.id
                new.name = result.name
                new.domain = result.domain
                new.ipv4 = result.ipv4
                new.ipv6 = result.ipv6
                new_data.append(new)
        new_session.bulk_save_objects(new_data)
        new_session.commit()

    

        with old_engine.connect() as conn:
            #rows = conn.execute( sqlalchemy.select(T_Actions)).all()
            rows = conn.execute( sqlalchemy.text("SELECT id, host_id, subtree, for_removed, for_new_or_updated, add_missing_sha, created_at, updated_at, deleted_at FROM actions")).all()
        print( f"Old Actions:", len( rows))
        new_data = []
        for result in rows:
                new = T_Actions()
                #print( new)
                new.id = result.id
                new.host_id = result.host_id
                new.parent_id = result.parent_id
                new.path = result.path
                new.path_hash = result.path_hash
                new.started_at = None
                new.created_at = result.created_at
                new.updated_at = result.updated_at
                new.deleted_at = result.deleted_at
                new_data.append(new)
        new_session.bulk_save_objects(new_data)
        new_session.commit()

        print( sqlalchemy.select(T_Ignores))
        with old_engine.connect() as conn:
            #rows = conn.execute( sqlalchemy.select(Table("ignored_paths"))).all()
            rows = conn.execute( sqlalchemy.text("SELECT ignored_paths.id, ignored_paths.host_id, ignored_paths.path_pattern, ignored_paths.created_at, ignored_paths.updated_at FROM ignored_paths")).all()
        print( f"Old Ignores:", len( rows))
        new_data = []
        for result in rows:
                new = T_Ignores()
                #print( new)
                new.id = result.id
                new.host_id = result.host_id
                new.path_pattern = result.path_pattern
                new.created_at = result.created_at
                new.updated_at = result.updated_at
                new_data.append(new)
        new_session.bulk_save_objects(new_data)
        new_session.commit()

        print( sqlalchemy.select(T_Folders))
        with old_engine.connect() as conn:
            #rows = conn.execute( sqlalchemy.select(T_Folders)).all()
            rows = conn.execute( sqlalchemy.text("SELECT folders.id, folders.host_id, folders.parent_id, folders.path, folders.path_hash, folders.created_at, folders.updated_at, folders.deleted_at FROM folders")).all()
        print( f"Old Folders:", len( rows))
        new_data = []
        saved_data = []
        for result in rows:
                new = T_Folders()
                new.id = result.id
                new.host_id = result.host_id
                new.parent_id = result.parent_id
                new.path = result.path
                new.path_hash = result.path_hash
                new.created_at = result.created_at
                new.updated_at = result.updated_at
                new.deleted_at = result.deleted_at
                if result.parent_id is None:
                    #print( new)
                    new.parent_id = result.host_id
                    new.parent_id = None
                    new.depth = 1
                    stmt = sqlalchemy.insert(T_Folders).values( id=result.id, host_id=result.host_id, parent_id=None,
                                                                path=result.path, path_hash=result.path_hash,
                                                                depth=1,
                                                                deleted_at=result.deleted_at, created_at=result.created_at, updated_at=result.updated_at)
                    #print( stmt)
                    with file_db.engine.connect() as conn:
                        results = conn.execute( stmt)
                        assert len(results.inserted_primary_key) == 1
                        conn.commit()
                    print( f"root inserted {result.id} {result.host_id} {result.parent_id} {result.path_hash}")
                else:
                    new_data.append(new)
                    for saved in saved_data:
                        if saved.id == new.parent_id:
                            new.depth = saved.depth + 1
                            break
                saved_data.insert( 0, new)
                if len( new_data) >= 5000:
                    new_session.bulk_save_objects(new_data)
                    new_session.commit()
                    new_data = []
        new_session.bulk_save_objects(new_data)
        new_session.commit()

        with old_engine.connect() as conn:
            rows = conn.execute( sqlalchemy.select(T_Files)).all()
        print( f"Old Files:", len( rows))
        new_data = []
        for result in rows:
                new = T_Files()
                new.id = result.id
                new.folder_id = result.folder_id
                new.file_name = result.file_name
                new.length = result.length
                new.ctime_ns = result.ctime_ns
                new.mtime_ns = result.mtime_ns
                new.ctime = result.ctime
                new.mtime = result.mtime
                new.file_hash = result.file_hash
                new.created_at = result.created_at
                new.updated_at = result.updated_at
                new.deleted_at = result.deleted_at
                #print( new)
                new_data.append(new)
                if len( new_data) >= 50000:
                    print( "commiting", new_data[0].id)
                    new_session.bulk_save_objects(new_data)
                    new_session.commit()
                    new_data = []
        new_session.bulk_save_objects(new_data)
        new_session.commit()

@app.post("/v1/hosts")
def post_host(host: PutHost) -> Optional[int]:
    stmt = sqlalchemy.insert(T_Hosts).values(name=host.name, domain=host.domain, ipv4=host.ipv4, ipv6=host.ipv6)
    with file_db.engine.connect() as conn:
        results = conn.execute( stmt)
        assert len(results.inserted_primary_key) == 1
        conn.commit()
        return results.inserted_primary_key[0]

@app.post("/v1/ignores")
def post_ignore(ignore: PutIgnore) -> Optional[int]:
    host_id = ignore.host_id
    path_pattern = ignore.path_pattern
    with file_db.Session() as session:
        ignore = T_Ignores( host_id=ignore.host_id, path_pattern=ignore.path_pattern)
        session.add( ignore)
        session.commit()
        _clean_up_ignored( session, ignore.host_id, (ignore.path_pattern,))
    if file_db.host_id == host_id:
        file_db.curr_add_ignore( path_pattern)
    #stmt = sqlalchemy.insert(T_Ignores).values( host_id=host_id, path_pattern=path_pattern)
    #with file_db.engine.connect() as conn:
        #results = conn.execute( stmt)
        #assert len(results.inserted_primary_key) == 1
        #conn.commit()
        #cnt = results.inserted_primary_key[0]
    #ret cnt

@app.post("/v1/curr_host/scan")
def post_host_item_scan( scan_action: PutAction) -> Optional[int]:
    stmt = sqlalchemy.insert(T_Actions).values(host_id=file_db.host_id, subtree=scan_action.subtree, started_at=None,
                   for_removed=scan_action.for_removed, for_new_or_updated=scan_action.for_new_or_updated, add_missing_sha=scan_action.add_missing_sha)
    with file_db.engine.connect() as conn:
        results = conn.execute( stmt)
        assert len(results.inserted_primary_key) == 1
        conn.commit()
        return results.inserted_primary_key[0]

@app.get("/v1/hosts")
def get_hosts() -> Page[Host]:
    with file_db.Session() as session:
        return paginate( session, sqlalchemy.select( T_Hosts).order_by( T_Hosts.id))

@app.get("/v1/actions")
def get_actions() -> Page[Action]:
    with file_db.Session() as session:
        return paginate( session, sqlalchemy.select( T_Actions).order_by( T_Actions.host_id, T_Actions.updated_at))

@app.get("/v1/ignores")
def get_ignores() -> Page[Ignore]:
    with file_db.Session() as session:
        return paginate( session, sqlalchemy.select( T_Ignores).order_by( T_Ignores.host_id, T_Ignores.path_pattern))

@app.get("/v1/folders")
def get_folders() -> Page[Folder]:
    with file_db.Session() as session:
        return paginate( session, sqlalchemy.select( T_Folders).order_by( T_Folders.host_id, T_Folders.path))

@app.get("/v1/files")
def get_files() -> Page[File]:
    with file_db.Session() as session:
        return paginate( session, sqlalchemy.select( T_Files).order_by( T_Files.length))

@app.get("/v1/hosts/{host_id}")
def get_host_item(host_id: int) -> Optional[Host]:
    with file_db.Session() as session:
        return session.get( T_Hosts, host_id)

@app.get("/v1/actions/{action_id}")
def get_actions(action_id: int) -> Optional[Action]:
    with file_db.Session() as session:
        return session.get( T_Actions, action_id)

@app.get("/v1/ignores/{ignore_id}")
def get_ignore_item(ignore_id: int) -> Optional[Ignore]:
    with file_db.Session() as session:
        return session.get( T_Ignores, ignore_id)

@app.get("/v1/folders/{folder_id}")
def get_folder_item(folder_id: int) -> Optional[Folder]:
    with file_db.Session() as session:
        return session.get( T_Folders, folder_id)

@app.get("/v1/files/{file_id}")
def get_files_item(file_id: int) -> Optional[File]:
    with file_db.Session() as session:
        return session.get( T_Files, file_id)

@app.get("/v1/hosts/{host_id}/actions")
def get_host_actions(host_id: int) -> Page[Action]:
    with file_db.Session() as session:
        return paginate( session, sqlalchemy.select( T_Actions).where(T_Actions.host_id==host_id).order_by( T_Actions.updated_at))

@app.get("/v1/hosts/{host_id}/ignores")
def get_host_ignores(host_id: int) -> Page[Ignore]:
    with file_db.Session() as session:
        return paginate( session, sqlalchemy.select( T_Ignores).where(T_Ignores.host_id==host_id).order_by( T_Ignores.path_pattern))

@app.get("/v1/hosts/{host_id}/folders")
def get_host_folders(host_id: int) -> Page[Folder]:
    with file_db.Session() as session:
        return paginate( session, sqlalchemy.select( T_Folders).where(T_Folders.host_id==host_id).order_by( T_Folders.path))

@app.get("/v1/hosts/{host_id}/folders/path_list")
def get_host_folders(host_id: int) -> Page[str]:
    with file_db.Session() as session:
        return paginate( session, sqlalchemy.select( T_Folders.path).where(T_Folders.host_id==host_id, T_Folders.deleted_at==None).order_by( T_Folders.path), unwrap_mode="unwrap",)

@app.get("/v1/hosts/{host_id}/files/path_list")
def get_host_folders(host_id: int) -> Page[str]:
    with file_db.Session() as session:
        return paginate( session, sqlalchemy.select( T_Folders.path, T_Files.file_name).join( T_Folders.files).where(T_Folders.host_id==host_id, T_Folders.deleted_at==None).order_by( T_Folders.path, T_Files.file_name), unwrap_mode="unwrap",)

@app.get("/v1/folders/{folder_id}/files")
def get_folder_files(folder_id: int) -> Page[File]:
    with file_db.Session() as session:
        return paginate( session, sqlalchemy.select( T_Files).where(T_Files.folder_id==folder_id).order_by( T_Files.length))

@app.delete("/v1/hosts/{host_id}")
def delete_host_item(host_id: int) -> int:
    with file_db.Session() as session:
        results = session.execute( sqlalchemy.delete(T_Hosts).where(T_Hosts.id==host_id))
        assert results.rowcount <= 1
        session.commit()
        #print( f"delete_action_item: {results.rowcount = }")
        return results.rowcount

@app.delete("/v1/actions/{action_id}")
def delete_action_item(action_id: int) -> int:
    with file_db.Session() as session:
        results = session.execute( sqlalchemy.delete(T_Actions).where(T_Actions.id==action_id))
        assert results.rowcount <= 1
        session.commit()
        #print( f"delete_action_item: {results.rowcount = }")
        return results.rowcount

@app.delete("/v1/ignores/{ignore_id}")
def delete_ignore_item(ignore_id: int) -> int:
    with file_db.Session() as session:
        results = session.execute( sqlalchemy.delete(T_Ignores).where(T_Ignores.id==ignore_id))
        assert results.rowcount <= 1
        session.commit()
        #print( f"delete_ignore_item: {results.rowcount = }")
        return results.rowcount

@app.delete("/v1/folders/{folder_id}")
def delete_folder_item(folder_id: int) -> int:
    with file_db.Session() as session:
        results = session.execute( sqlalchemy.delete(T_Folders).where(T_Folders.id==folder_id))
        assert results.rowcount <= 1
        session.commit()
        #print( f"delete_folder_item: {results.rowcount = }")
        return results.rowcount

@app.delete("/v1/files/{file_id}")
def delete_file_item(file_id: int) -> int:
    with file_db.Session() as session:
        results = session.execute( sqlalchemy.delete(T_Files).where(T_Files.id==file_id))
        assert results.rowcount <= 1
        session.commit()
        #print( f"delete_file_item: {results.rowcount = }")
        return results.rowcount

def invalidate_action_item(action_id: int) -> int:
    print( f"invalidate_action_item: {action_id = }")
    with file_db.Session() as session:
        results = session.execute( sqlalchemy.update(T_Actions).where(T_Actions.id==action_id).values({'deleted_at': datetime.now()}))
        assert results.rowcount <= 1
        session.commit()
        #print( f"invalidate_action_item: {results.rowcount = }")
        return results.rowcount

def invalidate_folder_item(folder_id: int) -> int:
    print( f"invalidate_folder_item: {folder_id = }")
    with file_db.Session() as session:
        results = session.execute( sqlalchemy.update(T_Folders).where(T_Folders.id==folder_id).values({'deleted_at': datetime.now(), 'updated_at': datetime.now(), 'created_at': datetime.now(), }))
        assert results.rowcount <= 1
        session.commit()
        #print( f"invalidate_folder_item: {results.rowcount = }")
        return results.rowcount

@app.post("/v1/invalidate/files/{file_id}")
def invalidate_file_item(file_id: int) -> int:
    #print( f"invalidate_file_item: {file_id = }")
    with file_db.Session() as session:
        results = session.execute( sqlalchemy.update(T_Files).where(T_Files.id==file_id).values({'deleted_at': datetime.now()}))
        assert results.rowcount <= 1
        session.commit()
        #print( f"invalidate_file_item: {results.rowcount = }")
        return results.rowcount

def check_for_removed_items( db, container_subtree_to_check: str, progress: Progress) -> None:
    print( f"check_for_removed_items: {container_subtree_to_check = }")
    with db.Session() as session:
        #stmt = sqlalchemy.select( T_Folders).where( T_Folders.host_id==db.host_id, T_Folders.deleted_at==None).order_by( T_Folders.path)
        #for folder in session.scalars( stmt).all():
        for folder in db.s_get_undeleted_folders( session, host_id=db.host_id, startswith=db.container_to_host_path( container_subtree_to_check)):
            container_folder_path = db.host_to_container_path( folder.path)
            #print( f"check_for_removed_items: {folder = } {container_folder_path = } {container_subtree_to_check = }")
            if container_folder_path.startswith( container_subtree_to_check):
                #print( f"{db.root_in_container = } {container_folder_path = } {folder.id = }")
                if pathlib.Path( container_folder_path).is_dir():
                    #print( folder.files)
                    for file in folder.files:
                        #print( f"{db.root_in_container = } {container_folder_path = } {file.file_name = }")
                        #print( f"{pathlib.Path( container_folder_path, file.file_name) = }")
                        if file.deleted_at is None and not pathlib.Path( container_folder_path, file.file_name).is_file():
                            print( f"NOT isfile {file.id} {pathlib.Path( container_folder_path, file.file_name) = }")
                            file.deleted_at=datetime.now( tz=timezone.utc)
                            session.commit()
                else:
                    print( f"check_for_removed_items: delete_folder not isdir {folder.id} {container_folder_path}")
                    folder.deleted_at=datetime.now( tz=timezone.utc)
                    session.commit()
                if progress.tick():
                    print( progress.status_msg())
            #else:
                #print( f"Skip {container_folder_path = } {folder.id = } not part of {container_subtree_to_check = }")
        session.commit()
    print( f"check_for_removed_items END")
    return

def check_for_new_or_updated_items( db, container_subtree_to_check: str, sha: bool, progress: Progress) -> None:
    print( f"check_for_new_or_updated_items: {container_subtree_to_check = }")
    for curr_, dirs, files in pathlib.Path( container_subtree_to_check).walk(on_error=print):
        host_folder_ = db.container_to_host_path_( curr_)

        # if any subfolder is to be ignored, we can imediately remove him from visit list
        for idx in range( len( dirs)-1, -1, -1):
            if db.curr_path_is_ignored( host_folder_ / dirs[idx]):
                #print( f"check_for_new_or_updated_items: {idx} {(host_folder_ / dirs[idx])} is ignored DELETE from list")
                del dirs[idx]

        # current folder should have been eiminated from parent list, but maybe subtree was already to be avoided
        if db.curr_path_is_ignored( host_folder_):
            print( f"check_for_new_or_updated_items: {host_folder_ = } is ignored")
            #assert False
            continue

        # folder is ok, do vheck if we already know about it
        with db.Session() as session:
            host_hash = hashlib.md5( str(host_folder_).encode()).hexdigest()
            folder = db.s_get_undeleted_folder_by_hash( session, db.host_id, host_hash)
            #print( f"check_for_new_or_updated_items: {folder = }")
            if folder is None:
                folder = db.s_create_folder( session, db.host_id, host_folder_, host_hash)
                print( f"check_for_new_or_updated_items: NEW {folder = }")
            folder_files = folder.files
            #print( f"check_for_new_or_updated_items: NEW {folder_files = }")

           #for file in folder_files:
               #if db.curr_path_is_ignored( host_folder_ / file.file_name):
                   ##print( f"check_for_new_or_updated_items: {(host_folder_ / file.file_name) = } FILE is ignored")
                   #continue
               #file_path_ = curr_ / file.file_name
               #if file_path_.is_file():
                   #file_stat = file_path_.lstat()
                   #if file_stat.st_mtime_ns != file.mtime_ns or file_stat.st_ctime_ns != file.ctime_ns or file_stat.st_size != file.length:
                       #file.deleted_at = datetime.now( timezone.utc)
                       #session.commit
                   #else:
               #else:
                   #file.deleted_at = datetime.now( timezone.utc)
                   #session.commit

            for file_name in files:
                if db.curr_path_is_ignored( host_folder_ / file_name):
                    #print( f"check_for_new_or_updated_items: {(host_folder_ / file_name) = } FILE is ignored")
                    continue
                file_path = os.path.join( str( curr_), file_name)
                file_path_ = curr_ / file_name
                assert file_path_.is_file() == os.path.isfile( file_path)
                if file_path_.is_file():
                    file_stat = file_path_.lstat()
                    for file in folder.files:
                        if file.deleted_at is None and file.file_name == file_name:
                            if db.file_is_changed( file, file_stat):
                                print( f"check_for_new_or_updated_items: {host_folder_ / file_name} CHANGED")
                                file.deleted_at = datetime.now( timezone.utc)
                                session.commit()
                                if sha:
                                    file_hash = db.file_hash( file_path_)
                                file = db.s_create_file( session, folder.id, file_name, file_stat, file_hash)
                                print( f"check_for_new_or_updated_items: {file} NEW")
                            else:
                                if sha and file.file_hash is None:
                                    # file exists and is unchanged but hash should be computed, but is undefined
                                    file.file_hash = db.file_hash( file_path_)
                                    session.commit()
                                    print( f"check_for_new_or_updated_items: {host_folder_ / file_name} {file.file_hash = } HASH added")
                            break
                    else:
                        #print( f"xx:", any(files for file in folder.files if file.deleted_at is None and file.file_name == file_name))
                        file_hash = None
                        if sha:
                            file_hash = db.file_hash( file_path_)
                        #print( f"check_for_new_or_updated_items: {file_stat = } {file_hash = }")
                        file = db.s_create_file( session, folder.id, file_name, file_stat, file_hash)
                else:
                    if not file_path_.is_symlink():
                        print( f"IS NOT file NOR link {file_path_}")
        if progress.tick():
             print( progress.status_msg())
        #temp = progr['res'] * progr['rng'] * folder_progr
        #cond = temp % progr['cnt'] < (progr['res'] * progr['rng'])
        #if cond:
            #perc = progr['min'] + int( temp / progr['cnt']) / progr['res']
            #print( f"{perc} {progr['cnt']}/{folder_progr} {datetime.now()-start}")
    print( f"check_for_new_or_updated_items END")


@app.get('/v1/curr_host/activate_next_pending_scan')
def get_next_pending_action() -> Optional[Action]:
    with file_db.engine.connect() as conn:
        while True:
            results = conn.execute( sqlalchemy.select(T_Actions)
                           .where( T_Actions.host_id==file_db.host_id, T_Actions.started_at==None, T_Actions.deleted_at==None).limit(1)).all()
            assert len(results) <= 1
            if len(results) == 0:
                #print( f"get_next_pending_action() None")
                return None
            action_row = results[0]
            results = conn.execute( sqlalchemy.update(T_Actions).values( { 'started_at': datetime.now()})
                           .where( T_Actions.id==action_row.id, T_Actions.host_id==file_db.host_id, T_Actions.started_at==None, T_Actions.deleted_at==None))
            if results.rowcount == 1:
                conn.commit()
                break
            conn.rollback()
        #print( f"get_next_pending_action() {action_row}")
        return action_row


def main() -> int:
    print(os.environ['CURR_HOSTNAME'])
    return 0

if __name__ == '__main__':
    sys.exit(main())

