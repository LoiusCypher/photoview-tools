# Module Imports
import os
import sys
import sqlalchemy
from sqlalchemy.ext.automap import automap_base
from alchemyModelFiles import Base, T_Hosts, Host, PutHost, T_Actions, Action, PutAction, T_Ignores, Ignore, PutIgnore, T_Folders, Folder, T_Files, File
from alchemyModelFiles import FilesDB

from fastapi import FastAPI
from fastapi_utilities import repeat_every
from fastapi_pagination import Page, add_pagination #, paginate
from fastapi_pagination.ext.sqlalchemy import paginate # as pag
from typing import List, Optional, Union
from pydantic import BaseModel, StrictInt, Field
from datetime import datetime
from contextlib import asynccontextmanager


def curr_host_set_actions_inactive():
    with file_db.engine.connect() as conn:
        results = conn.execute( sqlalchemy.select(T_Actions)
                       .where( T_Actions.host_id==file_db.host_id, T_Actions.started_at!=None, T_Actions.deleted_at==None)).all()
        for result in results:
            print( 'curr_host_set_actions_inactive', result.id, result.started_at, result.deleted_at)
        results = conn.execute( sqlalchemy.update(T_Actions)
                       .where( T_Actions.host_id==file_db.host_id, T_Actions.started_at!=None, T_Actions.deleted_at==None)
                       .values( { 'started_at': None,} ))
        print( 'curr_host_set_actions_inactive', results.rowcount)
        conn.commit()

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
    if scan_action.for_removed:
        folder_cnt = check_for_removed_items( file_db, container_subtree_to_check, 0, 10)
        #print(" check_for_pending_actions: done", container_subtree_to_check)
    if scan_action.for_new_or_updated:
        check_for_new_or_updated_items( file_db, container_subtree_to_check, scan_action.add_missing_sha, 10, 100)
        #print(" check_for_new_or_updated_items: done", container_subtree_to_check, "with SHA" if scan_action.add_missing_sha else "")
    assert invalidate_action_item( scan_action.id) == 1
    b = datetime.now()
    print("CHECK DONE", b-start)

@asynccontextmanager
async def lifespan(app: FastAPI):
    curr_host_set_actions_inactive()
    await check_for_pending_actions()
    yield


files_db_name = "files_collector"
tools_db_name = "object_detector"
photo_db_name = "photoview"
host_fs='/host_fs'
app = FastAPI(lifespan=lifespan)
add_pagination(app)
file_db = FilesDB( "debian-1", host_fs)


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

@app.put("/v1/hosts")
def put_host(host: PutHost) -> Optional[int]:
    stmt = sqlalchemy.insert(T_Hosts).values(name=host.name, domain=host.domain, ipv4=host.ipv4, ipv6=host.ipv6)
    with file_db.engine.connect() as conn:
        results = conn.execute( stmt)
        assert len(results.inserted_primary_key) == 1
        conn.commit()
        return results.inserted_primary_key[0]

@app.put("/v1/ignores")
def put_ignore(ignore: PutIgnore) -> Optional[int]:
    stmt = sqlalchemy.insert(T_Ignores).values( host_id=ignore.host_id, path_pattern=ignore.path_pattern)
    with file_db.engine.connect() as conn:
        results = conn.execute( stmt)
        assert len(results.inserted_primary_key) == 1
        conn.commit()
        return results.inserted_primary_key[0]

@app.put("/v1/curr_host/scan")
def put_host_item_scan( scan_action: PutAction) -> Optional[int]:
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
def get_foldere_item(folder_id: int) -> Optional[Folder]:
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

@app.get("/v1/folders/{folder_id}/files")
def get_folder_files(folder_id: int) -> Page[File]:
    with file_db.Session() as session:
        return paginate( session, sqlalchemy.select( T_Files).where(T_Files.folder_id==folder_id).order_by( T_Files.length))

@app.delete("/v1/hosts/{host_id}")
def delete_host_item(host_id: int) -> int:
    with file_db.engine.connect() as conn:
        results = conn.execute( sqlalchemy.delete(T_Hosts).where(T_Hosts.id==host_id))
        assert results.rowcount <= 1
        conn.commit()
        return results.rowcount

@app.delete("/v1/actions/{action_id}")
def delete_action_item(action_id: int) -> int:
    with file_db.engine.connect() as conn:
        results = conn.execute( sqlalchemy.delete(T_Actions).where(T_Actions.id==action_id))
        assert results.rowcount <= 1
        conn.commit()
        return results.rowcount

@app.delete("/v1/ignores/{ignore_id}")
def delete_ignore_item(ignore_id: int) -> int:
    with file_db.engine.connect() as conn:
        results = conn.execute( sqlalchemy.delete(T_Ignores).where(T_Ignores.id==ignore_id))
        assert results.rowcount <= 1
        conn.commit()
        return results.rowcount

@app.delete("/v1/folders/{folder_id}")
def delete_folder_item(folder_id: int) -> int:
    with file_db.engine.connect() as conn:
        results = conn.execute( sqlalchemy.delete(T_Folders).where(T_Folders.id==folder_id))
        assert results.rowcount <= 1
        conn.commit()
        return results.rowcount

@app.delete("/v1/files/{file_id}")
def delete_file_item(file_id: int) -> int:
    with file_db.engine.connect() as conn:
        results = conn.execute( sqlalchemy.delete(T_Files).where(T_Files.id==file_id))
        assert results.rowcount <= 1
        conn.commit()
        return results.rowcount

def invalidate_action_item(action_id: int) -> int:
    print( f"invalidate_action_item: {action_id = }")
    with file_db.engine.connect() as conn:
        results = conn.execute( sqlalchemy.update(T_Actions).where(T_Actions.id==action_id).values({'deleted_at': datetime.now()}))
        assert results.rowcount <= 1
        conn.commit()
        return results.rowcount

def invalidate_folder_item(folder_id: int) -> int:
    print( f"invalidate_folder_item: {folder_id = }")
    with file_db.engine.connect() as conn:
        results = conn.execute( sqlalchemy.update(T_Folders).where(T_Folders.id==folder_id).values({'deleted_at': datetime.now()}))
        assert results.rowcount <= 1
        conn.commit()
        return results.rowcount

def invalidate_file_item(file_id: int) -> int:
    print( f"invalidate_file_item: {file_id = }")
    with file_db.engine.connect() as conn:
        results = conn.execute( sqlalchemy.update(T_Files).where(T_Files.id==file_id).values({'deleted_at': datetime.now()}))
        assert results.rowcount <= 1
        conn.commit()
        return results.rowcount

def check_for_removed_items( db, container_subtree_to_check: str, min_percent: Optional[int] =0, max_percent: int =100) -> int:
    print( f"check_for_removed_items: {container_subtree_to_check = }")
    with db.engine.connect() as conn:
        host_subtree = db.container_to_host_path( container_subtree_to_check)
        stmt = sqlalchemy.select( sqlalchemy.func.count()).select_from( T_Folders).where( T_Folders.host_id==db.host_id, T_Folders.path.startswith(host_subtree), T_Folders.deleted_at==None)
        with db.Session() as session:
            folder_cnt = session.scalar( stmt)
        idx = 0
        for folder_row in conn.execute( sqlalchemy.select( T_Folders.id, T_Folders.path).where( T_Folders.host_id==db.host_id, T_Folders.deleted_at==None)).all():
            container_folder_path = db.host_to_container_path( folder_row.path)
            #print( f"check_for_removed_items: {folder_row = } {container_folder_path = } {container_subtree_to_check = }")
            if container_folder_path.startswith( container_subtree_to_check):
                #print( f"{db.root_in_container = } {container_folder_path = } {folder_row.id = }")
                if os.path.isdir( container_folder_path):
                    #for file_id, file_name in db.all_files( conn, folder_id=folder_row.id):
                    stmt = sqlalchemy.select( T_Files.id, T_Files.file_name).where( T_Files.folder_id==folder_row.id, T_Files.deleted_at==None)
                    #print( stmt)
                    for file_row in conn.execute( stmt).all():
                        #print( f"{db.root_in_container = } {container_folder_path = } {file_row.file_name = }")
                        #print( f"{os.path.join( container_folder_path, file_row.file_name) = }")
                        if not os.path.isfile( os.path.join( container_folder_path, file_row.file_name)):
                            print( f"NOT isfile {file_row.id} {os.path.join( container_folder_path, file_row.file_name) = }")
                            #db.delete_file_id( conn, file_row.id)
                            invalidate_file_item(file_row.id)
                else:
                    print( f"delete_folder not isdir {folder_row.id} {container_folder_path}")
                    #db.delete_folder_id( conn, folder_row.id)
                    invalidate_folder_item(folder_row.id)
            #else:
                #print( f"Skip {container_folder_path = } {folder_row.id = } not part of {container_subtree_to_check = }")
            idx += 1
            if (idx % max( 1, int( folder_cnt / (max_percent-min_percent)))) == 0:
                percent = min_percent + ( (max_percent-min_percent) * idx / max( 1, folder_cnt) )
                print( f"{int(percent)} {folder_cnt}/{idx}")
    print( f"check_for_removed_items END")
    return folder_cnt

def check_for_new_or_updated_items( db, container_subtree_to_update: str, sha, min_percent: Optional[int] =0, max_percent: int =100) -> None:
    print( f"check_for_new_or_updated_items: {container_subtree_to_update = }")
    with db.engine.connect() as conn:
        for curr, dirs, files in os.walk( container_subtree_to_update):
            host_folder = db.container_to_host_path( curr)
            folder_id = db.get_folder_id( conn, db.host_id, host_folder)
            #print( f"check_for_new_or_updated_items: {curr = } {folder_id = } {files = }")
            for file_name in files:
                file_path = os.path.join( curr, file_name)
                if os.path.isfile( file_path):
                    file_stat = os.lstat( file_path)
                    #print( f"check_for_new_or_updated_items: {file_stat = }")
                    file_id = db.get_file_id( conn, folder_id, file_name, file_stat)
                else:
                    if not os.path.islink( file_path):
                        print( "IS NOT file NOR link", file_path)
            for sub_dir in dirs:
                folder_path = os.path.join( curr, sub_dir)
                host_path = db.container_to_host_path( folder_path)
                folder_id = db.get_folder_id( conn, db.host_id, host_path)
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
    return 0

if __name__ == '__main__':
    sys.exit(main())

