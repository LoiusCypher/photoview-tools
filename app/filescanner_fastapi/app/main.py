# Module Imports
import os
import sys
from contextlib import asynccontextmanager

import sqlalchemy
from fastapi import FastAPI
from fastapi_pagination import add_pagination

from app.glue import file_db
from app.model_files import T_Actions

from .api import admin_tools, create_new, delete_item, dev, events, get_every, get_every_for_host, get_item, invalidate_item, path_lists, tmp_copy


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
    await events.check_for_pending_actions()
    yield

app = FastAPI(lifespan=lifespan)
app.include_router( events.router)
app.include_router( get_every.router)
app.include_router( get_every_for_host.router)
app.include_router( get_item.router)
app.include_router( create_new.router)
app.include_router( delete_item.router)
app.include_router( invalidate_item.router)
app.include_router( admin_tools.router)
app.include_router( path_lists.router)
app.include_router( tmp_copy.router)
app.include_router( dev.router)
add_pagination(app)


def main() -> int:
    print(os.environ['CURR_HOSTNAME'])
    return 0

if __name__ == '__main__':
    sys.exit(main())

