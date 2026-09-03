import os
import sys
import hashlib
import mariadb
from datetime import datetime, timezone
import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.mysql import INET4, INET6
from typing import List, Optional, Union
from pydantic import BaseModel, StrictInt, Field


Base = sqlalchemy.orm.declarative_base()

#class DBinit( object):

class PutHost( BaseModel):
    name: str
    domain: str | None = None
    ipv4: Optional[str]
    ipv6: Optional[str]

class Host( PutHost):
    id: StrictInt = Field( format='int64')
    created_at: datetime
    updated_at: datetime

class T_Hosts(Base):
    __tablename__ = 'hosts'
    #id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(primary_key=True)
    id = sqlalchemy.Column( sqlalchemy.BigInteger(), primary_key=True)
    name = sqlalchemy.Column( sqlalchemy.String(length=64), nullable=False, unique=True)
    domain = sqlalchemy.Column( sqlalchemy.String(length=255))
    ipv4 = sqlalchemy.Column( sqlalchemy.dialects.mysql.INET4())
    ipv6 = sqlalchemy.Column( sqlalchemy.dialects.mysql.INET6())
    created_at = sqlalchemy.Column( sqlalchemy.DateTime().with_variant( sqlalchemy.dialects.mysql.DATETIME(fsp=3), 'mariadb'),
                                    nullable=False, default=datetime.now)
    updated_at = sqlalchemy.Column( sqlalchemy.DateTime().with_variant( sqlalchemy.dialects.mysql.DATETIME(fsp=3), 'mariadb'),
                                    nullable=False, default=datetime.now, onupdate=datetime.now)
    ''' CONFIRMED upto here ''' 
    ignores: sqlalchemy.orm.Mapped[List["T_Ignores"]] = sqlalchemy.orm.relationship(back_populates="host", single_parent=True,
                                                                          cascade="all, delete", passive_deletes=True)
    actions: sqlalchemy.orm.Mapped[List["T_Actions"]] = sqlalchemy.orm.relationship(back_populates="host", single_parent=True,
                                                                          cascade="all, delete", passive_deletes=True)
    folders: sqlalchemy.orm.Mapped[List["T_Folders"]] = sqlalchemy.orm.relationship(back_populates="host", single_parent=True,
                                                                          cascade="all, delete", passive_deletes=True)

    def __repr__(self):
        return f"<Host(id='{self.id}', name='{self.name}', domain='{self.domain}', ipv4='{self.ipv4}', ipv6='{self.ipv6}'," \
               f" created_at='{self.created_at}', modified_at='{self.updated_at}'>"

class PutIgnore(BaseModel):
    host_id: StrictInt = Field( format='int64')
    path_pattern: str

class Ignore( PutIgnore):
    id: StrictInt = Field( format='int64')
    created_at: datetime
    updated_at: datetime

class T_Ignores(Base):
    __tablename__ = 'ignores'
    #id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(primary_key=True)
    id = sqlalchemy.Column( sqlalchemy.BigInteger(), primary_key=True)
    host_id = sqlalchemy.orm.mapped_column( sqlalchemy.ForeignKey("hosts.id", ondelete="CASCADE"))
    path_pattern = sqlalchemy.Column( sqlalchemy.String(length=750), nullable=False)
    created_at = sqlalchemy.Column( sqlalchemy.DateTime().with_variant( sqlalchemy.dialects.mysql.DATETIME(fsp=3), 'mariadb'),
                                    nullable=False, default=datetime.now)
    updated_at = sqlalchemy.Column( sqlalchemy.DateTime().with_variant( sqlalchemy.dialects.mysql.DATETIME(fsp=3), 'mariadb'),
                                    nullable=False, default=datetime.now, onupdate=datetime.now)

    host: sqlalchemy.orm.Mapped["T_Hosts"] = sqlalchemy.orm.relationship(back_populates="ignores", cascade="all, delete-orphan",  single_parent=True,passive_deletes=True)

    def __repr__(self):
        return f"<Ignore(id='{self.id}', host_id='{self.host_id}', path_pattern='{self.path_pattern}'," \
               f" created_at='{self.created_at}', modified_at='{self.updated_at}'>"

class PutAction(BaseModel):
    subtree: Optional[str]
    for_removed: Optional[bool]
    for_new_or_updated: Optional[bool]
    add_missing_sha: Optional[bool]

class Action(PutAction):
    id: StrictInt = Field( format='int64')
    host_id: StrictInt = Field( format='int64')
    started_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]

class T_Actions(Base):
    __tablename__ = 'actions'
    #id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(primary_key=True)
    id = sqlalchemy.Column( sqlalchemy.BigInteger(), primary_key=True)
    host_id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.ForeignKey("hosts.id", ondelete="CASCADE"))
    subtree = sqlalchemy.Column( sqlalchemy.String(length=750))
    for_removed = sqlalchemy.Column( sqlalchemy.Boolean(), default=False, nullable=True)
    for_new_or_updated = sqlalchemy.Column( sqlalchemy.Boolean(), default=False, nullable=True)
    add_missing_sha = sqlalchemy.Column( sqlalchemy.Boolean(), default=False, nullable=True)
    started_at = sqlalchemy.Column( sqlalchemy.DateTime().with_variant( sqlalchemy.dialects.mysql.DATETIME(fsp=3), 'mariadb'))
    created_at = sqlalchemy.Column( sqlalchemy.DateTime().with_variant( sqlalchemy.dialects.mysql.DATETIME(fsp=3), 'mariadb'),
                                    nullable=False, default=datetime.now)
    updated_at = sqlalchemy.Column( sqlalchemy.DateTime().with_variant( sqlalchemy.dialects.mysql.DATETIME(fsp=3), 'mariadb'),
                                    nullable=False, default=datetime.now, onupdate=datetime.now)
    deleted_at = sqlalchemy.Column( sqlalchemy.DateTime().with_variant( sqlalchemy.dialects.mysql.DATETIME(fsp=3), 'mariadb'))

    host: sqlalchemy.orm.Mapped["T_Hosts"] = sqlalchemy.orm.relationship( back_populates="actions", single_parent=True,
                                                                          cascade="all, delete", passive_deletes=True)

    def __repr__(self):
        return f"<Action(id='{self.id}', host_id='{self.host_id}', subtree='{self.subtree}'," \
               f" for_removed='{self.for_removed}', for_new_or_updated='{self.for_new_or_updated}', for_new_or_updated='{self.for_new_or_updated}'," \
               f" created_at='{self.created_at}', updated_at='{self.updated_at}', deleted_at='{self.deleted_at}'>"

class Folder(BaseModel):
    id: StrictInt = Field( format='int64')
    host_id: StrictInt = Field( format='int64')
    parent_id: Union[ None, int]
    path: str
    path_hash: str
    depth: int
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]

class T_Folders(Base):
    __tablename__ = 'folders'
    #id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(primary_key=True)
    id = sqlalchemy.Column( sqlalchemy.BigInteger(), primary_key=True)
    host_id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.ForeignKey("hosts.id", ondelete="CASCADE"))
    parent_id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.ForeignKey("folders.id", ondelete="CASCADE"), nullable=True, default=None)
    path = sqlalchemy.Column( sqlalchemy.String(length=750), nullable=False)
    path_hash = sqlalchemy.Column( sqlalchemy.String(length=64).with_variant( sqlalchemy.dialects.mysql.CHAR(64), "mariadb"), nullable=False)
    depth = sqlalchemy.Column(sqlalchemy.Integer())
    created_at = sqlalchemy.Column( sqlalchemy.DateTime().with_variant( sqlalchemy.dialects.mysql.DATETIME(fsp=3), 'mariadb'),
                                    nullable=False, default=datetime.now)
    updated_at = sqlalchemy.Column( sqlalchemy.DateTime().with_variant( sqlalchemy.dialects.mysql.DATETIME(fsp=3), 'mariadb'),
                                    nullable=False, default=datetime.now, onupdate=datetime.now)
    deleted_at = sqlalchemy.Column( sqlalchemy.DateTime().with_variant( sqlalchemy.dialects.mysql.DATETIME(fsp=3), 'mariadb'))

    host: sqlalchemy.orm.Mapped["T_Hosts"] = sqlalchemy.orm.relationship(back_populates="folders", single_parent=True,
                                                                          cascade="all, delete", passive_deletes=True)
    ##parent = sqlalchemy.orm.relationship( "T_Folders", remote_side=[id])
    #parent: sqlalchemy.orm.Mapped[Optional["T_Folders"]] = sqlalchemy.orm.relationship( "T_Folders", single_parent=True, back_populates="childs", cascade="all, delete-orphan", remote_side=[id])
    parent: sqlalchemy.orm.Mapped[Optional["T_Folders"]] = sqlalchemy.orm.relationship( "T_Folders", single_parent=True, cascade="all, delete-orphan", remote_side=[id])
    #childs = sqlalchemy.orm.relationship( "T_Folders", back_populates="parent")
    files: sqlalchemy.orm.Mapped[List["T_Files"]] = sqlalchemy.orm.relationship(back_populates="folder")

    def __repr__(self):
        return f"<Folder(id='{self.id}', host_id='{self.host_id}', parent_id='{self.parent_id}', path='{self.path}', path_hash='{self.path_hash}'" \
               f" created_at='{self.created_at}', updated_at='{self.updated_at}', deleted_at='{self.deleted_at}'>"

class File(BaseModel):
    id: StrictInt = Field( format='int64')
    folder_id: StrictInt = Field( format='int64')
    file_name: str
    length: StrictInt = Field( format='int64')
    ctime_ns: StrictInt = Field( format='int64')
    mtime_ns: StrictInt = Field( format='int64')
    ctime: datetime
    mtime: datetime
    file_hash: Optional[str]
    created_at: datetime

class T_Files(Base):
    __tablename__ = 'files'
    #id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(primary_key=True)
    id = sqlalchemy.Column( sqlalchemy.BigInteger(), primary_key=True)
    folder_id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.ForeignKey("folders.id", ondelete="CASCADE"))
    file_name = sqlalchemy.Column(sqlalchemy.String(length=256), nullable=False)
    length = sqlalchemy.Column(sqlalchemy.BigInteger(), nullable=False)
    ctime_ns = sqlalchemy.Column(sqlalchemy.BigInteger(), nullable=False)
    mtime_ns = sqlalchemy.Column(sqlalchemy.BigInteger(), nullable=False)
    ctime = sqlalchemy.Column(sqlalchemy.DateTime().with_variant( sqlalchemy.dialects.mysql.DATETIME(fsp=3), 'mariadb'), nullable=False)
    mtime = sqlalchemy.Column(sqlalchemy.DateTime().with_variant( sqlalchemy.dialects.mysql.DATETIME(fsp=3), 'mariadb'), nullable=False)
    file_hash = sqlalchemy.Column(sqlalchemy.String(length=128).with_variant( sqlalchemy.dialects.mysql.CHAR(128), "mariadb"))
    created_at = sqlalchemy.Column( sqlalchemy.DateTime().with_variant( sqlalchemy.dialects.mysql.DATETIME(fsp=3), 'mariadb'),
                                    nullable=False, default=datetime.now)
    updated_at = sqlalchemy.Column( sqlalchemy.DateTime().with_variant( sqlalchemy.dialects.mysql.DATETIME(fsp=3), 'mariadb'),
                                    nullable=False, default=datetime.now, onupdate=datetime.now)
    deleted_at = sqlalchemy.Column( sqlalchemy.DateTime().with_variant( sqlalchemy.dialects.mysql.DATETIME(fsp=3), 'mariadb'))

    folder: sqlalchemy.orm.Mapped["T_Folders"] = sqlalchemy.orm.relationship(back_populates="files", single_parent=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<File(id='{self.id}', folder_id='{self.folder_id}', file_name='{self.file_name}', length='{self.length}'," \
               f" ctime_ns='{self.ctime_ns}' mtime_ns='{self.mtime_ns}' ctime='{self.ctime}' ctime='{self.mtime}'" \
               f" created_at='{self.created_at}', updated_at='{self.updated_at}', deleted_at='{self.deleted_at}'>"

print(sqlalchemy.__version__)

class FilesDB( object):
    """ A class to create and drop filesDB tables and provide a session for it """
    # Define the MariaDB engine using MariaDB Connector/Python
    #engine = sqlalchemy.create_engine("mariadb+mariadbconnector://photoview:photosecret@192.168.2.227:3306/objectdetector")
    engine = sqlalchemy.create_engine("mariadb+mariadbconnector://photoview:photosecret@192.168.2.227:3306/filesdb")

    def __init__( self, host_name: str, root_in_container: str):
        def set_curr_host( host_name):
            with self.engine.connect() as conn:
                rows = conn.execute( sqlalchemy.select(T_Hosts.id).where(T_Hosts.name==host_name)).all()
                #print( len( rows), host_name, rows )
                assert len( rows) <= 1
                if len( rows) == 1:
                    self.host_id = rows[0][0]
                else:
                    stmt = sqlalchemy.insert(T_Hosts).values(name=host_name, domain=None, ipv4=None, ipv6=None)
                    rows = conn.execute( stmt)
                    conn.commit()
                    print( "inserted key", rows.inserted_primary_key)
                    self.host_id = rows.inserted_primary_key
            self.host_name = host_name

        self.root_in_container = root_in_container
        Base.metadata.create_all( self.engine)
        set_curr_host( host_name)
        #set_curr_host( "test3")
        # Create a session
        self.Session = sqlalchemy.orm.sessionmaker()
        self.Session.configure(bind=self.engine)
        with self.Session() as session:
            self.ignores = session.scalar( sqlalchemy.select( T_Ignores.path_pattern).where(T_Ignores.host_id==self.host_id).order_by( T_Ignores.path_pattern))

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

    def get_folder_id( self, conn, host_id: int, folder_path: str) -> int:
        path_hash = hashlib.md5( folder_path.encode()).hexdigest()
        stmt = sqlalchemy.select( T_Folders.id).where( T_Folders.host_id==host_id, T_Folders.path_hash==path_hash, T_Folders.deleted_at==None)
        results = conn.execute( stmt).all()
        #print( f"get_file_id: {len(results)} {results}")
        assert len(results) <= 1
        if len(results) == 0:
            #print( f"get_folder_id new folder {folder_path = }")
            stmt = sqlalchemy.insert( T_Folders).values( {'host_id': host_id, 'path': folder_path, 'path_hash': path_hash})
            results = conn.execute( stmt)
            assert len(results.inserted_primary_key) == 1
            conn.commit()
            #print( f"get_folder_id returns new id: {results.inserted_primary_key[0]}")
            return results.inserted_primary_key[0]
        #print( f"get_folder_id returns: {results[0][0]}")
        return results[0][0]

    def get_file_id( self, conn, folder_id: int, file_name: str, file_stat, file_hash=None) -> int:
        stmt = sqlalchemy.select( T_Files.id).where( T_Files.folder_id==folder_id, T_Files.file_name==file_name, T_Files.deleted_at==None)
        results = conn.execute( stmt).all()
        #print( f"get_file_id: {len(results)} {results}")
        assert len(results) <= 1
        if len(results) == 0:
            #print( f"get_file_id new file {file_name}")
            stmt = sqlalchemy.insert( T_Files).values( {'folder_id': folder_id, 'file_name': file_name, 'length': file_stat.st_size,
                                                        'ctime_ns': file_stat.st_ctime_ns, 'mtime_ns': file_stat.st_mtime_ns,
                                                        'ctime': datetime.fromtimestamp( file_stat.st_ctime_ns / 1e9, tz=timezone.utc),
                                                        'mtime': datetime.fromtimestamp( file_stat.st_mtime_ns / 1e9, tz=timezone.utc),
                                                        'file_hash': file_hash})
            results = conn.execute( stmt)
            assert len(results.inserted_primary_key) == 1
            conn.commit()
            #print( f"get_file_id returns new id: {results.inserted_primary_key[0]}")
            return results.inserted_primary_key[0]
        #print( f"get_file_id returns: {results[0][0]}")
        return results[0][0]

    def drop_tables( self) -> None:
        T_Files.__table__.drop( self.engine)
        T_Folders.__table__.drop( self.engine)
        T_Actions.__table__.drop( self.engine)
        T_Ignores.__table__.drop( self.engine)
        T_Hosts.__table__.drop( self.engine)
