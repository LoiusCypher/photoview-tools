# Module Imports
import os
import sys
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import sqlalchemy
from fastapi import FastAPI
from fastapi_pagination import Page, add_pagination  #, paginate
from fastapi_pagination.ext.sqlalchemy import paginate  # as pag
from fastapi_utilities import repeat_every
from sqlalchemy.ext.automap import automap_base

from app.files_db import _clean_up_ignored
from app.glue import file_db
from app.model_files import Action, File, T_Actions, T_Files, T_Folders, T_Hosts, T_Ignores
from app.progress import Progress
from app.scan_hostfiles import check_for_new_or_updated_items, check_for_removed_items

from .api import create_new, delete_item, get_every, get_every_for_host, get_item, invalidate_item
from .api.common import Tags


#@app.on_event("startup")
@repeat_every(seconds=30, wait_first=True, raise_exceptions=True)
def check_for_pending_actions() -> None:
    #print("CHECK START")
    scan_action = get_next_pending_action()
    if scan_action is None:
        #print("NO CHECK")
        return
    #print( f"{scan_action = }")
    start = datetime.now( tz=UTC)
    file_db.fix_folder_depth()
    print( f"check_for_pending_actions: {scan_action.subtree = }")
    container_subtree_to_check_path = file_db.action_subtree_to_container_path( scan_action.subtree)
    host_subtree_path = file_db.container_to_host_path( container_subtree_to_check_path)
    folder_cnt = max( 1, file_db.folder_cnt( host_subtree_path))
    progress = Progress( T_Actions, 'for_removed_progress', scan_action.id, steps=folder_cnt, resolution=1)
    if scan_action.for_removed and scan_action.for_new_or_updated:
        progress.add_task( 'for_new_or_updated_progress', ranges=98, resolution=10)
    if scan_action.for_removed:
        progress.start_next()
        check_for_removed_items( file_db, container_subtree_to_check_path, host_subtree_path, progress)
        #print(" check_for_pending_actions: done", container_subtree_to_check_path)
    if scan_action.for_new_or_updated:
        progress.start_next()
        check_for_new_or_updated_items( file_db, container_subtree_to_check_path, scan_action.add_missing_sha, progress)
        #print(" check_for_new_or_updated_items: done", container_subtree_to_check_path, "with SHA" if scan_action.add_missing_sha else "")
    assert invalidate_item.invalidate_action_item( scan_action.id) == 1
    b = datetime.now( tz=UTC)
    print("CHECK DONE", b-start)

def curr_host_set_actions_inactive() -> None:
    with file_db.Session() as session:
        stmt = sqlalchemy.select(T_Actions).where( T_Actions.host_id==file_db.host_id, T_Actions.started_at!=None, T_Actions.deleted_at==None)
        for action in session.scalars( stmt):
            #print( f"curr_host_set_actions_inactive: {action}")
            action.started_at = None
        session.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    curr_host_set_actions_inactive()
    await check_for_pending_actions()
    yield

app = FastAPI(lifespan=lifespan)
app.include_router( get_every.router)
app.include_router( get_every_for_host.router)
app.include_router( get_item.router)
app.include_router( create_new.router)
app.include_router( delete_item.router)
app.include_router( invalidate_item.router)
add_pagination(app)

@app.get("/dev/curr_host/ignores/cleanup", tags=[Tags.current])
def dev_clean_up_ignored() -> None:
    with file_db.Session() as session:
        _clean_up_ignored( file_db, session, file_db.host_id, file_db.curr_ignores)

@app.get("/tmpcopy/hosts", tags=[Tags.develop])
def tmp_copy() -> None:
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
        print( "Old Hosts:", len( rows))
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
        print( "Old Actions:", len( rows))
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
        print( "Old Ignores:", len( rows))
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
        print( "Old Folders:", len( rows))
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
        print( "Old Files:", len( rows))
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

@app.get("/v1/hosts/{host_id}/folders/path_list", tags=[Tags.folders])
def get_host_folders_pathlist(host_id: int) -> Page[str]:
    with file_db.Session() as session:
        return paginate( session, sqlalchemy.select( T_Folders.path).where(T_Folders.host_id==host_id, T_Folders.deleted_at==None).order_by( T_Folders.path), unwrap_mode="unwrap",)

@app.get("/v1/hosts/{host_id}/files/path_list", tags=[Tags.files])
def get_host_files_pathlist(host_id: int) -> Page[str]:
    with file_db.Session() as session:
        return paginate( session, sqlalchemy.select( T_Folders.path, T_Files.file_name).join( T_Folders.files).where(T_Folders.host_id==host_id, T_Folders.deleted_at==None).order_by( T_Folders.path, T_Files.file_name), unwrap_mode="unwrap",)

@app.get("/v1/folders/{folder_id}/files", tags=[Tags.folders])
def get_folder_files(folder_id: int) -> Page[File]:
    with file_db.Session() as session:
        return paginate( session, sqlalchemy.select( T_Files).where(T_Files.folder_id==folder_id).order_by( T_Files.length))


@app.get('/v1/curr_host/activate_next_pending_scan', tags=[Tags.current])
def get_next_pending_action() -> Action | None:
    with file_db.engine.connect() as conn:
        while True:
            results = conn.execute( sqlalchemy.select(T_Actions)
                           .where( T_Actions.host_id==file_db.host_id, T_Actions.started_at==None, T_Actions.deleted_at==None).limit(1)).all()
            assert len(results) <= 1
            if len(results) == 0:
                #print( f"get_next_pending_action() None")
                return None
            action_row = results[0]
            print( 'started_at', datetime.now( tz=UTC))
            results = conn.execute( sqlalchemy.update(T_Actions).values( { 'started_at': datetime.now( tz=UTC)})
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

