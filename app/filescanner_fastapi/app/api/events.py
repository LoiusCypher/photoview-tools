from datetime import UTC, datetime

import sqlalchemy
from fastapi import APIRouter
from fastapi_utilities import repeat_every

from app.model_files import Action, T_Actions
from app.progress import Progress
from app.scan_hostfiles import check_for_new_or_updated_items, check_for_removed_items

from ..glue import file_db
from . import invalidate_item
from .common import Tags

router = APIRouter()

@router.get('/v1/curr_host/activate_next_pending_scan', tags=[Tags.current])
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

