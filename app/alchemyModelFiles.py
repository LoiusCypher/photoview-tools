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
                                    nullable=False, default=datetime.utcnow)
    updated_at = sqlalchemy.Column( sqlalchemy.DateTime().with_variant( sqlalchemy.dialects.mysql.DATETIME(fsp=3), 'mariadb'),
                                    nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
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
                                    nullable=False, default=datetime.utcnow)
    updated_at = sqlalchemy.Column( sqlalchemy.DateTime().with_variant( sqlalchemy.dialects.mysql.DATETIME(fsp=3), 'mariadb'),
                                    nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

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
    for_removed_progress: float=0.0
    for_new_or_updated_progress: float =0.0
    add_missing_sha_progress: float =0.0
    created_at: datetime
    started_at: Optional[datetime]
    updated_at: datetime
    expected_at: Optional[datetime]
    deleted_at: Optional[datetime]

class T_Actions(Base):
    __tablename__ = 'actions'
    #id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(primary_key=True)
    id = sqlalchemy.Column( sqlalchemy.BigInteger(), primary_key=True)
    host_id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.ForeignKey("hosts.id", ondelete="CASCADE"))
    subtree = sqlalchemy.Column( sqlalchemy.String(length=750))
    for_removed = sqlalchemy.Column( sqlalchemy.Boolean(), default=False, nullable=True)
    for_removed_progress = sqlalchemy.Column( sqlalchemy.Float(), default=0.0, nullable=False)
    for_new_or_updated = sqlalchemy.Column( sqlalchemy.Boolean(), default=False, nullable=True)
    for_new_or_updated_progress = sqlalchemy.Column( sqlalchemy.Float(), default=0.0, nullable=False)
    add_missing_sha = sqlalchemy.Column( sqlalchemy.Boolean(), default=False, nullable=True)
    add_missing_sha_progress = sqlalchemy.Column( sqlalchemy.Float(), default=0.0, nullable=False)
    # = sqlalchemy.Column( sqlalchemy.Float(), default=0.0, nullable=False)
    started_at = sqlalchemy.Column( sqlalchemy.DateTime().with_variant( sqlalchemy.dialects.mysql.DATETIME(fsp=3), 'mariadb'))
    expected_at = sqlalchemy.Column( sqlalchemy.DateTime().with_variant( sqlalchemy.dialects.mysql.DATETIME(fsp=3), 'mariadb'))
    created_at = sqlalchemy.Column( sqlalchemy.DateTime().with_variant( sqlalchemy.dialects.mysql.DATETIME(fsp=3), 'mariadb'),
                                    nullable=False, default=datetime.utcnow)
    updated_at = sqlalchemy.Column( sqlalchemy.DateTime().with_variant( sqlalchemy.dialects.mysql.DATETIME(fsp=3), 'mariadb'),
                                    nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow) # datetime.now)
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
    depth: Optional[int]
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
    depth = sqlalchemy.Column(sqlalchemy.Integer(), nullable=True)
    created_at = sqlalchemy.Column( sqlalchemy.DateTime().with_variant( sqlalchemy.dialects.mysql.DATETIME(fsp=3), 'mariadb'),
                                    nullable=False, default=datetime.utcnow)
    updated_at = sqlalchemy.Column( sqlalchemy.DateTime().with_variant( sqlalchemy.dialects.mysql.DATETIME(fsp=3), 'mariadb'),
                                    nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = sqlalchemy.Column( sqlalchemy.DateTime().with_variant( sqlalchemy.dialects.mysql.DATETIME(fsp=3), 'mariadb'))

    host: sqlalchemy.orm.Mapped["T_Hosts"] = sqlalchemy.orm.relationship(back_populates="folders", single_parent=True,
                                                                          cascade="all, delete", passive_deletes=True)
    ##parent = sqlalchemy.orm.relationship( "T_Folders", remote_side=[id])
    #parent: sqlalchemy.orm.Mapped[Optional["T_Folders"]] = sqlalchemy.orm.relationship( "T_Folders", single_parent=True, back_populates="childs", cascade="all, delete-orphan", remote_side=[id])
    parent: sqlalchemy.orm.Mapped[Optional["T_Folders"]] = sqlalchemy.orm.relationship( "T_Folders", single_parent=True, cascade="all, delete-orphan", remote_side=[id])
    childs: sqlalchemy.orm.Mapped[List["T_Folders"]] = sqlalchemy.orm.relationship( back_populates="parent")
    files: sqlalchemy.orm.Mapped[List["T_Files"]] = sqlalchemy.orm.relationship(back_populates="folder")

    def __repr__(self):
        return f"<Folder(id='{self.id}', host_id='{self.host_id}', parent_id='{self.parent_id}', depth='{self.depth}', path='{self.path}', path_hash='{self.path_hash}'" \
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
    updated_at: datetime
    deleted_at: Optional[datetime]

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
                                    nullable=False, default=datetime.utcnow)
    updated_at = sqlalchemy.Column( sqlalchemy.DateTime().with_variant( sqlalchemy.dialects.mysql.DATETIME(fsp=3), 'mariadb'),
                                    nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = sqlalchemy.Column( sqlalchemy.DateTime().with_variant( sqlalchemy.dialects.mysql.DATETIME(fsp=3), 'mariadb'))

    folder: sqlalchemy.orm.Mapped["T_Folders"] = sqlalchemy.orm.relationship(back_populates="files", single_parent=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<File(id='{self.id}', folder_id='{self.folder_id}', file_name='{self.file_name}', length='{self.length}'," \
               f" ctime_ns='{self.ctime_ns}' mtime_ns='{self.mtime_ns}' ctime='{self.ctime}' ctime='{self.mtime}'" \
               f" created_at='{self.created_at}', updated_at='{self.updated_at}', deleted_at='{self.deleted_at}'>"

print(sqlalchemy.__version__)

