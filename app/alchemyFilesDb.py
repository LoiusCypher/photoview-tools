import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base

# Define the MariaDB engine using MariaDB Connector/Python
engine = sqlalchemy.create_engine("mariadb+mariadbconnector://photoview:photosecret@192.168.2.227:3306/objectdetector")

Base = declarative_base()


class T_Hosts(Base):
    __tablename__ = 'hosts'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, nullable=False)
    name = sqlalchemy.Column(sqlalchemy.String(length=64), nullable=False)
    domain = sqlalchemy.Column(sqlalchemy.String(length=255))
    ipv4 = sqlalchemy.Column(sqlalchemy.String(length=15))
    ipv6 = sqlalchemy.Column(sqlalchemy.String(length=15))
    created_at = sqlalchemy.Column(sqlalchemy.DateTime(), nullable=False)
    updated_at = sqlalchemy.Column(sqlalchemy.DateTime(), nullable=False)

class T_Ignores(Base):
    __tablename__ = 'ignored_paths'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    host_id = sqlalchemy.Column(sqlalchemy.Integer, ForeignKey("hosts.id"), nullable=False),
    path_pattern = sqlalchemy.Column(sqlalchemy.String(length=750), nullable=False)
    created_at = sqlalchemy.Column(sqlalchemy.DateTime(), nullable=False)
    updated_at = sqlalchemy.Column(sqlalchemy.DateTime(), nullable=False)


class T_Folders(Base):
    __tablename__ = 'folders'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    parent_id = sqlalchemy.Column(sqlalchemy.Integer, ForeignKey("folders.id"))
    host_id = sqlalchemy.Column(sqlalchemy.Integer, ForeignKey("hosts.id"), nullable=False)
    path = sqlalchemy.Column(sqlalchemy.String(length=750), nullable=False)
    path_hash = sqlalchemy.Column(sqlalchemy.String(length=64), nullable=False)
    created_at = sqlalchemy.Column(sqlalchemy.DateTime(), nullable=False)
    updated_at = sqlalchemy.Column(sqlalchemy.DateTime(), nullable=False)
    deleted_at = sqlalchemy.Column(sqlalchemy.DateTime())

class T_Files(Base):
    __tablename__ = 'files'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    folder_id = sqlalchemy.Column(sqlalchemy.Integer, ForeignKey("folders.id"), nullable=False)
    file_name = sqlalchemy.Column(sqlalchemy.String(length=256), nullable=False)
    file_hash = sqlalchemy.Column(sqlalchemy.String(length=128))
    length = sqlalchemy.Column(sqlalchemy.Integer(), nullable=False)
    ctime_ns = sqlalchemy.Column(sqlalchemy.Integer(), nullable=False)
    mtime_ns = sqlalchemy.Column(sqlalchemy.Integer(), nullable=False)
    ctime = sqlalchemy.Column(sqlalchemy.DateTime(), nullable=False)
    mtime = sqlalchemy.Column(sqlalchemy.DateTime(), nullable=False)
    created_at = sqlalchemy.Column(sqlalchemy.DateTime(), nullable=False)
    updated_at = sqlalchemy.Column(sqlalchemy.DateTime(), nullable=False)
    deleted_at = sqlalchemy.Column(sqlalchemy.DateTime())

Base.metadata.create_all(engine)

# Create a session
Session = sqlalchemy.orm.sessionmaker()
Session.configure(bind=engine)
session = Session()

def selectAll():
   hosts = session.query(T_Hosts).all()
   for host in hosts:
       print(" - " + host.id + ' ' + host.name)

