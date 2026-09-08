import os
import sys
import hashlib
import mariadb
import pathlib
from datetime import datetime, timezone
import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.mysql import INET4, INET6
from typing import List, Optional, Union
from pydantic import BaseModel, StrictInt, Field
from alchemyModelFiles import Base, T_Hosts, Host, PutHost, T_Ignores, Ignore, PutIgnore, T_Actions, Action, PutAction, T_Folders, Folder, T_Files, File
#from alchemyModelFiles import T_Hosts, Host, PutHost, T_Ignores, Ignore, PutIgnore, T_Actions, Action, PutAction, T_Folders, Folder, PutFolder, T_Files, File, PutFile


#Base = sqlalchemy.orm.declarative_base()

class FilesDBBase( object):
    """ A class to create and drop filesDB tables and provide a session for it """
    # Define the MariaDB engine using MariaDB Connector/Python
    #engine = sqlalchemy.create_engine("mariadb+mariadbconnector://photoview:photosecret@192.168.2.227:3306/objectdetector")
    #engine = sqlalchemy.create_engine("mariadb+mariadbconnector://photoview:photosecret@192.168.2.227:3306/filesdb")

    def __init__( self, mariadb_conn: str, db_name: str) -> None:
        assert db_name is not None
        self.engine = sqlalchemy.create_engine( f"mariadb+mariadbconnector://{mariadb_conn}/{db_name}")
        self.Session = sqlalchemy.orm.sessionmaker()
        self.Session.configure(bind=self.engine)

    def ignored_to_startswith( self, ignore: str) -> str:
        #print( f"ignored_to_startswith: {ignore = }")
        while True:
            #print( f"ignored_to_startswith:  {not any([char in ignore for char in '*.['])}  {[char in ignore for char in '*.['] = }")
            if not any([char in ignore for char in '*.[']):
                #print( f"ignored_to_startswith: exit loop")
                break
            ignore = str( pathlib.Path( ignore).parent)
            #print( f"ignored_to_startswith: loop {ignore = }")
        #print( f"ignored_to_startswith: exit {ignore = }")
        return ignore

    def path_is_ignored( self, path: str, ignores: List[str]) -> bool:
        #print( f"path_is_ignored: {path = } {ignores = }")
        for patt in ignores:
            try:
                if pathlib.PurePath( path).full_match( patt):
                    print( f"path_is_ignored: 1 {pathlib.PurePath( path) = } {patt = }")
                    return True
            except:
                if pathlib.PurePath( path).match( patt):
                    #print( f"path_is_ignored: 2 {pathlib.PurePath( path) = } {patt = }")
                    return True
                for parent in pathlib.PurePath( path).parents:
                    if parent.match( patt):
                        #print( f"path_is_ignored: 3 {pathlib.PurePath( path) = } {patt = } {parent = }")
                        return True
        return False


class FilesDB( FilesDBBase):

    def __init__( self, host_name: str, root_in_container: str, mariadb_conn: str, db_name: str ='filesdb') -> None:

        def set_curr_host( host_name: str) -> None:
            with self.Session() as session:
                stmt = sqlalchemy.select(T_Hosts.id).where(T_Hosts.name==host_name)
                self.host_id = session.scalar( stmt)
                if self.host_id is None:
                    host = T_Hosts( name=host_name)
                    session.add( host)
                    session.commit()
                    print( "inserted host id:", host.id)
                    self.host_id = host.id
            self.curr_host_name = host_name

        super().__init__( mariadb_conn, db_name)
        Base.metadata.create_all( self.engine)
        self.root_in_container = root_in_container
        #set_curr_host( "test3")
        set_curr_host( host_name)
        with self.Session() as session:
            stmt = sqlalchemy.select( T_Ignores.path_pattern).where(T_Ignores.host_id==self.host_id).order_by( T_Ignores.path_pattern)
            self.curr_ignores = session.scalars( stmt).all()
        #print( f" __init__ self.curr_ignores = ")
        #for ignore in self.curr_ignores:
            #print( f" __init__ {ignore}")
        #print( f" __init__ {len(self.curr_ignores) = }")

    def curr_add_ignore( self, pattern: str) -> None:
        self.curr_ignores.append( pattern)

    def is_container_path( self, path: str) -> bool:
        return os.path.abspath( path).startswith( self.root_in_container)

    def host_to_container_path( self, host_path: str) -> str:
        host_abs_path = os.path.abspath( host_path)
        #print( f"host_to_container_path: {host_path = } {host_abs_path = }")
        #print( f"host_to_container_path: {os.path.relpath( host_abs_path, '/') = }")
        container_path = os.path.abspath( os.path.join( self.root_in_container, os.path.relpath( host_abs_path, '/')))
        return container_path

    def container_to_host_path( self, container_path: str) -> str:
        container_abs_path = os.path.abspath( container_path)
        host_path = os.path.abspath( os.path.join( '/', os.path.relpath( container_abs_path, self.root_in_container)))
        return host_path

    def container_to_host_path_( self, container_path: pathlib.Path) -> pathlib.Path:
        return ( container_path.root / container_path.absolute().relative_to( self.root_in_container)).absolute()

    def fix_folder_depth( self) -> None:
        #print( f"db_fix_folder_depth: START")
        while True:
            with self.Session() as session:
                stmt = sqlalchemy.select( T_Folders).where( T_Folders.depth==None)
                for folder in session.scalars( stmt):
                    #print( f"db_fix_folder_depth: 1 {folder}")
                    if pathlib.PurePath( folder.path) == pathlib.PurePath( folder.path).root:
                        print( f"db_fix_folder_depth: 8 got root {folder.path}")
                        continue
                    #print( f"db_fix_folder_depth: 2 {folder.parent}")
                    if folder.parent is None and folder.parent_id is None:
                        parent_path = str( pathlib.Path( folder.path).parent.absolute())
                        parent_hash = hashlib.md5( parent_path.encode()).hexdigest()
                        stmt = sqlalchemy.select( T_Folders).where( T_Folders.host_id==folder.host_id, T_Folders.path_hash==parent_hash, T_Folders.deleted_at==None)
                        parent = session.scalar( stmt)
                        #print( f"db_fix_folder_depth: 3 got {parent}")
                        folder.parent_id = parent.id
                        #print( f"db_fix_folder_depth: 7 got {folder.id = } {parent.id = } {folder.parent_id = }")
                        if parent.depth is not None:
                            folder.depth = parent.depth + 1
                        #session.commit
                        #print( f"db_fix_folder_depth: 6 got {folder}")
                        break
                    if folder.parent is None and folder.parent_id is not None:
                        parent = session.get( T_Folders, folder.parent_id)
                        print( f"db_fix_folder_depth: 4 got {parent}")
                    if folder.parent is not None and folder.parent.depth is not None:
                        folder.depth = folder.parent.depth + 1
                        session.commit()
                        print( f"db_fix_folder_depth: 5 fixed {folder.path}")
                        break
                else:
                    print( f"db_fix_folder_depth: fixed everything")
                    break
                session.commit()
            #print( f"db_fix_folder_depth: LOOP")
        #print( f"db_fix_folder_depth: END")

    def s_get_undeleted_folder_by_hash( self, session, host_id: int, folder_hash: str) -> T_Folders:
        #print( f"s_get_undeleted_folder_by_hash: {host_id} {folder_hash}")
        stmt = sqlalchemy.select( T_Folders).where( T_Folders.host_id==host_id, T_Folders.path_hash==folder_hash, T_Folders.deleted_at==None)
        return session.scalar( stmt)

    def s_get_undeleted_folders( self, session, host_id: int, startswith: Optional[str] =None, reverse: bool =False) -> List[T_Folders]:
        print( f"s_get_undeleted_folders: {host_id}")
        stmt = sqlalchemy.select( T_Folders).where( T_Folders.host_id==host_id, T_Folders.deleted_at==None)
        if startswith is not None:
            stmt = stmt.where( T_Folders.path.startswith( startswith))
        if reverse:
            stmt = stmt.order_by( sqlalchemy.desc( T_Folders.path))
        else:
            stmt = stmt.order_by( T_Folders.path)
        return session.scalars( stmt).all()

    def s_create_folder( self, session, host_id: int, folder_path: pathlib.Path, folder_hash: str) -> T_Folders:
        #print( f"s_create_folder: {host_id} {folder_path} {folder_hash}")
        if folder_path == folder_path.root:
            folder = T_Folders( host_id = self.host_id, parent_id = None, path = str( folder_path), path_hash = host_hash, depth = 1)
            print( f"s_create_folder: root {folder_path}")
        else:
            parent_path = folder_path.parent.absolute()
            parent_hash = hashlib.md5( str( parent_path).encode()).hexdigest()
            parent = self.s_get_undeleted_folder_by_hash( session, host_id, parent_hash)
            #print( f"get_parent_folder: {folder}")
            if parent is None:
                print( f"s_create_folder: root {parent_path}")
                parent = self.s_create_folder( session, host_id, str( parent_path), parent_hash)
            folder = T_Folders( host_id = self.host_id, parent_id = parent.id, path = str( folder_path), path_hash = folder_hash, depth = parent.depth + 1)
        session.add( folder)
        session.commit()
        return folder

    def s_create_file( self, session, folder_id: int, file_name: str, file_stat, file_hash: str) -> T_Files:
        #print( f"s_create_file: {folder_id} {file_name} {file_stat} {file_hash}")
        file = T_Files( folder_id = folder_id, file_name = file_name, length = file_stat.st_size,
                        ctime_ns = file_stat.st_ctime_ns, mtime_ns = file_stat.st_mtime_ns,
                        ctime = datetime.fromtimestamp( file_stat.st_ctime_ns / 1e9, tz=timezone.utc),
                        mtime = datetime.fromtimestamp( file_stat.st_mtime_ns / 1e9, tz=timezone.utc),
                        file_hash = file_hash)
        session.add( file)
        session.commit()
        return file

    def curr_path_is_ignored( self, path: str) -> bool:
        #print( f"curr_path_is_ignored: {path = }")
        #print( f"curr_path_is_ignored: {self.curr_ignores = }")
        return self.path_is_ignored( path, self.curr_ignores)

    def file_is_changed( self, file: File, file_stat) -> bool:
        #print( f"file_is_changed: {file = } {file_stat = }")
        #print( f"file_is_changed: {file_stat.st_mtime_ns != file.mtime_ns or file_stat.st_ctime_ns != file.ctime_ns or file_stat.st_size != file.length} { file = } {file_stat = }")
        return file_stat.st_mtime_ns != file.mtime_ns or file_stat.st_ctime_ns != file.ctime_ns or file_stat.st_size != file.length

    def file_hash( self, file_path: pathlib.Path) -> str:
        print( f"file_hash: {file_path = }")
        BUF_SIZE = 65536  # lets read stuff in 64kb chunks!
        hash = hashlib.sha3_512()
        with open( str( file_path), 'rb') as f:
            while True:
                data = f.read(BUF_SIZE)
                if not data:
                    break
                hash.update(data)
        return hash.hexdigest()

    def drop_tables( self) -> None:
        T_Files.__table__.drop( self.engine)
        T_Folders.__table__.drop( self.engine)
        T_Actions.__table__.drop( self.engine)
        T_Ignores.__table__.drop( self.engine)
        T_Hosts.__table__.drop( self.engine)
