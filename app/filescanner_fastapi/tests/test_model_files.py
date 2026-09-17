import time
from datetime import UTC, datetime

import pytest
import sqlalchemy

from app.files_db import Base, T_Hosts


@pytest.fixture(scope="module")
def db_session():
    engine = sqlalchemy.create_engine('mariadb+mariadbconnector://photoview:photosecret@192.168.2.227:3306/filesdb')
    #engine = sqlalchemy.create_engine('sqlite:///:memory:')
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session = sqlalchemy.orm.sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()

@pytest.fixture(scope="module")
def valid_host():
    valid_host = T_Hosts(
            name="TestHost",
            domain="test.domain",
            ipv4="192.168.3.99",
    )
    return valid_host

#@pytest.fixture(scope="module")
#def valid_ignore():
    #valid_ignore = T_Ignores(
            #path_pattern="/test/**",
            #host_id=6,
    #)
    #return valid_ignore


class TestFilesDB_host:
    # ...

    def test_create_valid(self, db_session, valid_host):
        h = valid_host
        db_session.add(h)
        db_session.commit()
        host = db_session.query(T_Hosts).filter_by(name="TestHost").first()
        print( host)
        assert host
        assert host.name == "TestHost"
        assert host.domain == "test.domain"
        assert host.ipv4 == "192.168.3.99"
        assert host.ipv6 == None
        t_now = datetime.now(UTC).astimezone()
        print( t_now)
        t_diff = (datetime.now(UTC).astimezone().replace(tzinfo=None) - host.created_at).total_seconds()
        assert 0 <= t_diff < 1
        t_diff = (datetime.now(UTC).astimezone().replace(tzinfo=None) - host.updated_at).total_seconds()
        assert 0 <= t_diff < 1
        t_diff = (host.updated_at - host.created_at).total_seconds()
        print( f"updated_at-created_at {t_diff}")
        assert 0 <= t_diff < 1

    def test_update_valid(self, db_session, valid_host):
        h = valid_host
        db_session.add(h)
        db_session.commit()
        host = db_session.query(T_Hosts).filter_by(name="TestHost").first()
        created = host.created_at
        updated = host.updated_at
        time.sleep(1)
        host.ipv6 = '2001:db8::ff00:42:8329'
        db_session.commit()
        print( host)
        assert host
        assert host.ipv6 == '2001:db8::ff00:42:8329'
        t_diff = (host.created_at - created).total_seconds()
        assert 0 <= t_diff < 1
        t_diff = (host.updated_at - updated).total_seconds()
        print( f"updated_at-created_at {t_diff}")
        assert 1 <= t_diff < 2

    #def test_ignorehost_valid(self, db_session, valid_ignore):
        #db_session.add(valid_ignore)
        #db_session.commit()
        #ignore = db_session.query(T_Ignores).filter_by(host_id=6).first()
        #assert ignore.path_pattern == "/est/**"

    #def teardown_class(self):
        #self.session.rollback()
        #self.session.close()

    #@pytest.mark.xfail(raises=IntegrityError)
    #def test_author_no_email(self):
        #author = Author(
            #firstname="James",
            #lastname="Clear"
        #)
        #self.session.add(author)
        #try:
            #self.session.commit()
        #except IntegrityError:
            #self.session.rollback()

#def test_files_db_init()
#    f_db = FilesDBBase( mariadb_conn="photoview:photosecret@192.168.2.227", db_name="filesdb")

