from datetime import datetime

import sqlalchemy
from fastapi import APIRouter
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from pydantic import BaseModel, Field, StrictInt

from app.model_files import T_Files, T_Folders

from ..glue import file_db
from .common import Tags

router = APIRouter()

class HashCnt(BaseModel):
    file_hash: str | None
    length: StrictInt = Field( json_schema_extra={ "format": 'int64',})
    count: StrictInt = Field( json_schema_extra={ "format": 'int64',})

class HashCntHost(HashCnt):
    host_id: StrictInt = Field( json_schema_extra={ "format": 'int64',})

@router.get("/v1/file_hash_counts", tags=[Tags.develop])
def get_file_hash_counts(min_size: int =1, host_id: int | None =None) -> Page[HashCnt | HashCntHost]:
    if host_id:
        stmt = sqlalchemy.select( T_Files.file_hash, T_Files.length, sqlalchemy.func.count( T_Files.file_hash).label("count"))
    else:
        stmt = sqlalchemy.select( T_Files.file_hash, T_Files.length, T_Folders.host_id, sqlalchemy.func.count( T_Files.file_hash).label("count"))
    stmt = stmt.join( T_Folders)
    if host_id:
        stmt = stmt.where( T_Folders.host_id == host_id)
    stmt = stmt.where( T_Files.deleted_at == None, T_Files.file_hash != None, T_Files.length >= min_size )
    stmt = stmt.group_by( T_Files.file_hash, T_Files.length)
    stmt = stmt.having( sqlalchemy.text( "count > 1")) \
               .order_by( sqlalchemy.desc( T_Files.length), sqlalchemy.asc( "count"))
    with file_db.Session() as session:
        return paginate( session, stmt)

class FileFolder(BaseModel):
    folder_id: int
    path: str
    file_name: str

class FileFolderHost(FileFolder):
    host_id: int 

@router.get("/v1/file_hash/{file_hash}", tags=[Tags.develop])
def get_files_with_hash( file_hash: str, host_id: int | None =None) -> Page[FileFolder | FileFolderHost]:
    if host_id:
        stmt = sqlalchemy.select( T_Files.folder_id, T_Files.file_name, T_Folders.path)
    else:
        stmt = sqlalchemy.select( T_Folders.host_id, T_Files.folder_id, T_Files.file_name, T_Folders.path)
    stmt = stmt.join( T_Folders) \
               .where( T_Files.deleted_at == None, T_Files.file_hash == file_hash)
    if host_id:
        stmt = stmt.where( T_Folders.host_id == host_id)
    if host_id:
        stmt = stmt.order_by( T_Files.folder_id)
    else:
        stmt = stmt.order_by( T_Folders.host_id, T_Files.folder_id)
    with file_db.Session() as session:
        return paginate( session, stmt)

class CompareFolders(BaseModel):
    id: int | None
    id_1: int | None
    file_name: str | None
    file_name_1: str | None
    length: int | None
    length_1: int | None
    file_hash: str | None
    file_hash_1: str | None
    ctime: datetime | None
    ctime_1: datetime | None
    ctime_ns: int | None
    ctime_ns_1: int | None
    mtime: datetime | None
    mtime_1: datetime | None
    mtime_ns: int | None
    mtime_ns_1: int | None

@router.get("/v1/file_hash/compare_folders/{folder_id_1}/{folder_id_2}", tags=[Tags.develop])
def cmp_folder_files( folder_id_1: int, folder_id_2: int, diff_only: bool =True, cmp_ctime: bool =False, cmp_mtime: bool =False) -> Page[CompareFolders]:
    stmt0 = sqlalchemy.select( T_Files.id,
                               T_Files.file_hash,
                               T_Files.file_name,
                               T_Files.length,
                               T_Files.ctime,
                               T_Files.ctime_ns,
                               T_Files.mtime,
                               T_Files.mtime_ns,
            )
    stmt1 = stmt0.where( T_Files.folder_id == folder_id_1).order_by( T_Files.length).alias("file1") # .subquery()
    stmt2 = stmt0.where( T_Files.folder_id == folder_id_2).order_by( T_Files.length).alias("file2") # .subquery()
    with file_db.Session() as session:
        cntstmt1 = sqlalchemy.select( sqlalchemy.func.count()).select_from( stmt1)
        cntstmt2 = sqlalchemy.select( sqlalchemy.func.count()).select_from( stmt2)
        #print( "STMT1", cntstmt1))
        #print( "STMT2", cntstmt2))
        tst1 = session.scalar( cntstmt1)
        tst2 = session.scalar( cntstmt2)
        print( "LEN_01", tst1, tst2)
    match_cond = "file1.file_hash = file2.file_hash"
    match_cond += " AND file1.length = file2.length"
    if cmp_ctime:
        match_cond += " AND file1.ctime_ns = file2.ctime_ns"
    if cmp_mtime:
        match_cond += " AND file1.mtime_ns = file2.mtime_ns"
    stmtL = sqlalchemy.select( stmt1, stmt2).outerjoin_from( stmt1, stmt2, sqlalchemy.text( match_cond))
    #print( "STMT_L", stmtL)
    stmtR = sqlalchemy.select( stmt1, stmt2).outerjoin_from( stmt2, stmt1, sqlalchemy.text( match_cond))
    #print( "STMT_R", stmtR)
    if diff_only:
        stmtL = stmtL.where( sqlalchemy.text( "file2.id IS NULL"))
        #print( "STMT_L", stmtL)
        stmtR = stmtR.where( sqlalchemy.text( "file1.id IS NULL"))
        #print( "STMT_R", stmtR)
    with file_db.Session() as session:
        stmtU = sqlalchemy.union( stmtL, stmtR)
        #print( "STMT_U", stmtU)
        return paginate( session, stmtU, unwrap_mode="auto",)

