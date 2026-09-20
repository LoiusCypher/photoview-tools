import sqlalchemy
from fastapi import APIRouter
from sqlalchemy.ext.automap import automap_base

from app.model_files import T_Actions, T_Files, T_Folders, T_Hosts, T_Ignores

from ..glue import file_db
from .common import Tags

router = APIRouter()

@router.get("/tmpcopy/hosts", tags=[Tags.develop])
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

