from fastapi import APIRouter, Query
from fastapi_pagination import Page

from app.alchemyModelFiles import PutAction, PutHost, PutIgnore, T_Actions, T_Hosts, T_Ignores
from app.alchemyFilesDB import _clean_up_ignored
import sqlalchemy
from .common import Tags
from ..glue import file_db

router = APIRouter()

@router.post("/v1/hosts", tags=[Tags.hosts])
def post_host(host: PutHost) -> int | None:
    stmt = sqlalchemy.insert(T_Hosts).values(name=host.name, domain=host.domain, ipv4=host.ipv4, ipv6=host.ipv6)
    with file_db.engine.connect() as conn:
        results = conn.execute( stmt)
        assert len(results.inserted_primary_key) == 1
        conn.commit()
        return results.inserted_primary_key[0]

@router.post("/v1/ignores", tags=[Tags.ignores])
def post_ignore(ignore: PutIgnore) -> int | None:
    host_id = ignore.host_id
    path_pattern = ignore.path_pattern
    with file_db.Session() as session:
        ignore = T_Ignores( host_id=ignore.host_id, path_pattern=ignore.path_pattern)
        session.add( ignore)
        session.commit()
        _clean_up_ignored( file_db, session, ignore.host_id, (ignore.path_pattern,))
    if file_db.host_id == host_id:
        file_db.curr_add_ignore( path_pattern)

@router.post("/v1/curr_host/scan", tags=[Tags.current])
def post_host_item_scan( scan_action: PutAction) -> int | None:
    stmt = sqlalchemy.insert(T_Actions).values(host_id=file_db.host_id, subtree=scan_action.subtree, started_at=None,
                   for_removed=scan_action.for_removed, for_new_or_updated=scan_action.for_new_or_updated, add_missing_sha=scan_action.add_missing_sha)
    with file_db.engine.connect() as conn:
        results = conn.execute( stmt)
        assert len(results.inserted_primary_key) == 1
        conn.commit()
        return results.inserted_primary_key[0]

