# Module Imports
from datetime import datetime, timezone
import hashlib
import mariadb
import os
import pathlib
import sys

from mylib.PhotoviewDbServer import PhotoviewDbServer

class PhotoviewFilesServer( PhotoviewDbServer):

    def __init__(self, root, root_pwd, user, user_pwd, db_host_ip_or_dns, files_db_name, recreate=False, debug=True, debug_entry=False, debug_ignore=False):
        super().__init__( root, root_pwd, user, user_pwd, db_host_ip_or_dns)
        self.files_db_name = files_db_name
        self.create_files_db( recreate)
        #print( f"Files Database ready")
        self.curr_host_id = None
        self.debug = debug
        self.debug_entry = debug_entry
        self.debug_ignore = debug_ignore

    def create_files_db( self, recreate):

        def create_table_hosts( conn):
            # Get new Cursor
            cur = conn.cursor()
            try:
                cur.execute(f"CREATE TABLE IF NOT EXISTS `{self.files_db_name}`.`hosts` ("
                            " `id` bigint(20) NOT NULL AUTO_INCREMENT,"
                            " `created_at` datetime(3) DEFAULT NULL,"
                            " `updated_at` datetime(3) DEFAULT NULL,"
                            " `name` CHAR(64) DEFAULT NULL,"
                            " `domain` CHAR(255) DEFAULT NULL,"
                            " `ipv4` INET4 DEFAULT NULL,"
                            " `ipv6` INET6 DEFAULT NULL,"
                            " PRIMARY KEY (`id`)"
                            " )")
            except mariadb.Error as e:
                print(f"Error connecting to MariaDB Platform Table: {e}")
                sys.exit(1)
            #print("create_table_skipped_media done")

        def create_table_ignored_paths( conn):
            # Get new Cursor
            cur = conn.cursor()
            try:
                cur.execute(f"CREATE TABLE IF NOT EXISTS `{self.files_db_name}`.`ignored_paths` ("
                            " `id` bigint(20) NOT NULL AUTO_INCREMENT,"
                            " `created_at` datetime(3) DEFAULT NULL,"
                            " `updated_at` datetime(3) DEFAULT NULL,"
                            " `host_id` bigint(20) NOT NULL,"
                            " `path_pattern` varchar(500) NOT NULL,"
                            " PRIMARY KEY (`id`),"
                            " CONSTRAINT `fk_ignored_host` FOREIGN KEY (host_id) REFERENCES hosts (id) ON DELETE CASCADE ON UPDATE RESTRICT"
                            " )")
            except mariadb.Error as e:
                print(f"Error connecting to MariaDB Platform Table: {e}")
                sys.exit(1)
            #print("create_table_ignored_paths done")

        def create_table_folders( conn):
            # Get new Cursor
            cur = conn.cursor()
            try:
                cur.execute(f"CREATE TABLE IF NOT EXISTS `{self.files_db_name}`.`folders` ("
                            " `id` bigint(20) NOT NULL AUTO_INCREMENT,"
                            " `created_at` datetime(3) DEFAULT NULL,"
                            " `updated_at` datetime(3) DEFAULT NULL,"
                            " `deleted_at` datetime(3) DEFAULT NULL,"
                            " `path` varchar(500) NOT NULL,"
                            " `path_hash` char(64) NOT NULL,"
                            " `parent_id` bigint(20) NULL,"
                            " `host_id` bigint(20) NOT NULL,"
                            " PRIMARY KEY (`id`),"
                            " CONSTRAINT `fk_folder_parent_folders` FOREIGN KEY (parent_id) REFERENCES folders (id) ON DELETE CASCADE ON UPDATE RESTRICT,"
                            " CONSTRAINT `fk_folders_host` FOREIGN KEY (host_id) REFERENCES hosts (id) ON DELETE CASCADE ON UPDATE RESTRICT"
                            " )")
            except mariadb.Error as e:
                print(f"Error connecting to MariaDB Platform Table: {e}")
                sys.exit(1)
            #print("create_table_skipped_media done")

        def create_table_files( conn):
            # Get new Cursor
            cur = conn.cursor()
            try:
                cur.execute(f"CREATE TABLE IF NOT EXISTS `{self.files_db_name}`.`files` ("
                            " `id` bigint(20) NOT NULL AUTO_INCREMENT,"
                            " `created_at` datetime(3) DEFAULT NULL,"
                            " `updated_at` datetime(3) DEFAULT NULL,"
                            " `deleted_at` datetime(3) DEFAULT NULL,"
                            " `file_name` varchar(256) NOT NULL,"
                            " `folder_id` bigint(20) NOT NULL,"
                            " `length` bigint(20) NOT NULL,"
                            " `file_hash` char(128) NOT NULL,"
                            " `ctime_ns` bigint NOT NULL,"
                            " `mtime_ns` bigint NOT NULL,"
                            " `ctime` datetime(3) NOT NULL,"
                            " `mtime` datetime(3) NOT NULL,"
                            " PRIMARY KEY (`id`),"
                            " CONSTRAINT `fk_file_parent_folders` FOREIGN KEY (folder_id) REFERENCES folders (id) ON DELETE CASCADE ON UPDATE RESTRICT"
                            " )")
            except mariadb.Error as e:
                print(f"Error connecting to MariaDB Platform Table: {e}")
                sys.exit(1)
            #print("create_table_skipped_media done")

        conn = self.new_conn(root=True)
        if conn is None: return

        # Get Cursor
        cur = conn.cursor()
        try:
            if recreate:
                cur.execute(f"DROP DATABASE IF EXISTS `{self.files_db_name}` ;")
                cur.execute(f"CREATE OR REPLACE DATABASE `{self.files_db_name}` ;")
            else:
                cur.execute(f"CREATE DATABASE IF NOT EXISTS `{self.files_db_name}` ;")
        except mariadb.Error as e:
            print(f"Error connecting to MariaDB Platform CREATE DB: {e}")
            sys.exit(1)
        try:
            cur.execute(f"GRANT ALL PRIVILEGES ON {self.files_db_name}.* TO 'photoview'@'%' ;")
        except mariadb.Error as e:
            print(f"Error connecting to MariaDB Privileges: {e}")
            sys.exit(1)
        cur.close()
        create_table_hosts( conn)
        create_table_ignored_paths( conn)
        create_table_folders( conn)
        create_table_files( conn)
        conn.commit()
        conn.close()

    """ User routines start here
    """

    def set_host( self, conn, root_in_container, host_name = None, domain = None, ipv4 = None, ipv6 = None) -> int:
        #print( f"set_host {root_in_container = } {host_name = }")
        self.root_in_container = os.path.abspath( root_in_container)
        self.curr_host_id = self.get_host_id( conn, host_name, domain, ipv4, ipv6)
        #print( f"set_host {self.curr_host_id = }")
        self.curr_host_ignored_patterns = [row[1] for row in self.ignores( conn, self.curr_host_id)]
        #print( self.curr_host_ignored_patterns)

    def get_host_id( self, conn, host_name = None, domain = None, ipv4 = None, ipv6 = None) -> int:
        self.curr_host_id = None
        cur = conn.cursor()
        try:
            if host_name is None:
                if ipv4 is None:
                    if ipv6 is None:
                        print( 'At least one host attribute must be specified')
                        return None
                    else:
                        cur.execute(f"SELECT id" f" FROM `{self.files_db_name}`.`hosts`" f" WHERE ipv6 = ? " f" ;", ( ipv6, ))
                else:
                    cur.execute(f"SELECT id" f" FROM `{self.files_db_name}`.`hosts`" f" WHERE ipv4 = ? " f" ;", ( ipv4, ))
            else:
                if domain is None:
                    cur.execute(f"SELECT id" f" FROM `{self.files_db_name}`.`hosts`" f" WHERE name = ? " f" ;", ( host_name, ))
                else:
                    cur.execute(f"SELECT id" f" FROM `{self.files_db_name}`.`hosts`" f" WHERE name = ? AND domain = ?" f" ;", ( host_name, domain, ))
            row = cur.fetchone()
            if not row is None:
                #print(f"get_host_id: host_id {row[0]} ")
                return row[0]
        except mariadb.Error as e:
            print(f"Error getting last media_id for detection {detection}: {e}")
            sys.exit(1)
        return self.create_host_id( conn, host_name, domain, ipv4, ipv6)

    def fetch_ignored_id( self, conn, path_pattern, host_id):
        #print( f"ignored_id {path_pattern = } {host_id = }")
        with conn.cursor() as cur:
            try:
                cur.execute( f"SELECT id FROM `{self.files_db_name}`.`ignored_paths` WHERE host_id = ? AND path_pattern = ? ;", ( host_id, path_pattern, ))
                rows = cur.fetchall()
                print( f"ignored_id {len(rows) = } {path_pattern = } {host_id = }")
                assert len( rows) <= 1
                if len( rows) == 1:
                    #print( f"fetch_ignored_id: folder_id {rows[0][0]} ")
                    return rows[0][0]
            except mariadb.Error as e:
                print( f"Error fetch_ignored_id: {e}")
        return None

    def create_ignored_pattern( self, conn, host_id, path_pattern):
        if self.debug_entry or self.debug_ignore: print( f"create_ignored_pattern {host_id = } {path_pattern = }")
        with conn.cursor() as cur:
            try:
                cur.execute( f"INSERT INTO `{self.files_db_name}`.`ignored_paths`" \
                             f" ( host_id, path_pattern, created_at, updated_at )" \
                             f" VALUES ( ?, ?, CURRENT_TIMESTAMP(3), CURRENT_TIMESTAMP(3) ) " \
                             f" RETURNING id ;", ( host_id, path_pattern, ))
                rows = cur.fetchall()
                assert len( rows) == 1
                conn.commit()
                id = rows[0][0]
            except mariadb.Error as e:
                print(f"Error connecting to MariaDB: (create_ignored_folder) {e}")
                sys.exit(1)
        for folder_id, folder_path in self.folders( conn, host_id, host_path=False):
            #if self.debug: print( f"create_ignored_pattern: {host_id = } {path_pattern = } {folder_path = }")
            if self._path_is_ignored( folder_path):
                print( f"create_ignored_pattern: {host_id = } {path_pattern = } deleting {folder_path = }")
                for file_id, file_name in self.files( conn, folder_id):
                    print( f"create_ignored_pattern: {host_id = } {path_pattern = } deleting {folder_path = } {file_name = } {file_id = }")
                    self.delete_file_id( conn, file_id)
                self.delete_folder_id( conn, folder_id)
            for file_id, file_name in self.files( conn, folder_id):
                if self._path_is_ignored( os.path.join( folder_path, file_name)):
                    print( f"create_ignored_pattern: {host_id = } {path_pattern = } deleting {folder_path = }/{file_name = }")
                    self.delete_file_id( conn, file_id)
        return id 

    def ignores( self, conn, host_id, all_or_deleted=None):
        cur = conn.cursor()
        cur.execute( f"SELECT id, path_pattern FROM `{self.files_db_name}`.`ignored_paths`"
                     f" WHERE host_id = ? ;", ( host_id, ))
        row = cur.fetchone()
        while not row is None:
            #print(f"ID: {row[0]}, Path: {row[1]}")
            yield row[0], row[1]
            row = cur.fetchone()
        #print( f"No more ignores in database")

    """ public ignore patterns
    """

    def add_ignore_pattern( self, path_pattern, host_id=None):
        if self.debug_entry or self.debug_ignore: print( f"add_ignore_pattern {path_pattern = } {host_id = }")
        if host_id is None:
            host_id = self.curr_host_id
        with self.new_conn() as conn:
            id = self.fetch_ignored_id( conn, path_pattern, host_id)
            if id is None:
                id = self.create_ignored_pattern( conn, host_id, path_pattern)
        return id

    def remove_ignore_pattern( self, path_pattern, host_id=None):
        if self.debug_entry or self.debug_ignore: print( f"remove_ignore_pattern {path_pattern = } {host_id = }")
        if host_id is None:
            host_id = self.curr_host_id
        with self.new_conn() as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute( f"DELETE FROM `{self.files_db_name}`.`ignored_paths` WHERE host_id = ? AND path_pattern = ? RETURNING id ;",
                                  ( host_id, path_pattern, ))
                    rows = cur.fetchall()
                    if self.debug_ignore: print( f"remove_ignore_pattern {len(rows) = } {path_pattern = } {host_id = }")
                    assert len( rows) <= 1
                    if len( rows) == 0:
                        print( f"remove_ignore_pattern: no match {len(rows) = } {path_pattern = } {host_id = }")
                        return None
                    if self.debug_ignore: print( f"remove_ignore_pattern: id {rows[0][0]} ")
                    conn.commit()
                except mariadb.Error as e:
                    print( f"Error connecting to MariaDB Privileges: {e}")
                    sys.exit(1)
        return rows[0][0]

    def list_ignore_patterns( self, host_id=None, all_or_deleted=None):
        if self.debug_entry or self.debug_ignore: print( f"list_ignore_patterns {host_id = } {all_or_deleted = }")
        if host_id == "*":
            print( f"No host_id")
            conn = self.new_conn()
            for host in self.hosts( conn):
                print( f"{host = }")
                for ignore in self.ignores( conn, host[0], all_or_deleted=all_or_deleted):
                    print( f"{ignore = }")
            conn.close()
        else:
            if host_id is None:
                host_id = self.curr_host_id
            #print( f"list_ignore_patterns {host_id = }")
            conn = self.new_conn()
            for ignore in self.ignores( conn, host_id, all_or_deleted=all_or_deleted):
                print( f"{ignore = }")
            conn.close()

    """ host
    """

    def create_host_id( self, conn, host_name = None, domain = None, ipv4 = None, ipv6 = None) -> int:

        def init_ignored_paths( conn, host_id):
            print( f"init_ignored_paths {host_id = }")
            self.get_ignored_id( conn, '/dev/**', host_id)
            self.get_ignored_id( conn, '/home/*/.cache/**', host_id)
            self.get_ignored_id( conn, '/home/*/.mozilla/**', host_id)
            self.get_ignored_id( conn, '/proc/**', host_id)
            self.get_ignored_id( conn, '/run/**', host_id)
            self.get_ignored_id( conn, '/swap', host_id)
            self.get_ignored_id( conn, '/sys/**', host_id)
            self.get_ignored_id( conn, '/tmp/**', host_id)

        print( f"create_host_id {host_name = } {domain = } {ipv4 = } {ipv6 = }")
        param_str = ""
        place_str = ""
        sel_list = []
        if not host_name is None:
            param_str = param_str+"name, "
            place_str = place_str+"?, "
            sel_list.append( host_name)
        if not domain is None:
            param_str = param_str+"domain, "
            place_str = place_str+"?, "
            sel_list.append( domain)
        if not ipv4 is None:
            param_str = param_str+"ipv4, "
            place_str = place_str+"?, "
            sel_list.append( ipv4)
        if not ipv6 is None:
            param_str = param_str+"ipv6, "
            place_str = place_str+"?, "
            sel_list.append( ipv6)
        exec_str = f"INSERT INTO `{self.files_db_name}`.`hosts`" \
                   f" ( {param_str} created_at, updated_at )" \
                   f" VALUES ( {place_str} CURRENT_TIMESTAMP(3), CURRENT_TIMESTAMP(3) ) " \
                   f" RETURNING id ;"
        #print( f"{exec_str = } {sel_list = } ")
        cur = conn.cursor()
        try:
            cur.execute(exec_str, sel_list)
            rows = cur.fetchall()
            cur.close()
            conn.commit()
            init_ignored_paths( conn, rows[0][0])
            return rows[0][0]
        except mariadb.Error as e:
            print(f"Error connecting to MariaDB: (create_host_id) {e}")
            sys.exit(1)

    def hosts( self, conn):
        cur = conn.cursor()
        cur.execute( f"SELECT id, name, domain, ipv4, ipv6 FROM `{self.files_db_name}`.`hosts` ;")
        row = cur.fetchone()
        while not row is  None:
            #print(f"ID: {row[0]}, Name: {row[1]}, Subdir: {row[2]}, IPv4: {row[3]}, IPv6: {row[4]}")
            yield row[0], row[1], row[2], row[3], row[4]
            row = cur.fetchone()
        print(f"No more folders in database")
        # return None

    """ folders
    """

    def list_folders( self, conn, host_id=None, all_or_deleted=None):
        if host_id == "*":
            print( f"No host_id")
            for host in self.hosts( conn):
                print( f"{host = }")
                for folder in self.folders( conn, host[0], host_path=False, all_or_deleted=all_or_deleted):
                    print( f"{folder = }")
        else:
            if host_id is None:
                host_id = self.curr_host_id
            #print( f"list_folders {host_id = }")
            for folder in self.folders( conn, host_id, host_path=False, all_or_deleted=all_or_deleted):
                print( f"{folder = }")

    def count_folders( self, conn, host_id=None, all_or_deleted=None):
        if host_id == "*":
            print( f"No host_id")
            for host in self.hosts( conn):
                folders = self.folders( conn, host[0], all_or_deleted=all_or_deleted)
                print( f"{host = } {len(list(folders)) = }")
        else:
            if host_id is None:
                host_id = self.curr_host_id
            #print( f"count_folders {host_id = }")
            folder = self.folders( conn, host_id, all_or_deleted=all_or_deleted)
            print( f"{len(list(folders)) = }")

    def _path_is_ignored( self, path):
        #print( f"path_is_ignored: {path = }")
        for patt in self.curr_host_ignored_patterns:
            try:
                if pathlib.PurePath( path).full_match( patt):
                    #print( f"path_is_ignored: {pathlib.PurePath( path) = } {patt = }")
                    return True
            except:
                if pathlib.PurePath( path).match( patt):
                    return True
                for parent in pathlib.PurePath( path).parents:
                    if parent.match( patt):
                        #print( f"path_is_ignored: {pathlib.PurePath( path) = } {patt = } {parent = }")
                        return True
        return False

    def get_folder_id( self, conn, folder_path, host_id=None) -> int:
        #print( f"get_folder_id {host_id = }")
        abs_path = os.path.abspath( folder_path)
        host_path = os.path.abspath( os.path.join( '/', os.path.relpath( abs_path, self.root_in_container)))
        host_hash = hashlib.md5( host_path.encode()).hexdigest()
        #print( f"get_folder_id {abs_path = } {host_path = } {host_hash = }")
        if host_id is None:
            host_id = self.curr_host_id
            if self._path_is_ignored( host_path):
                print( f"get_folder_id: folder IGNORED {abs_path = } {host_path = } {host_hash = }")
                return None, host_path
        #print( f"{abs_path = } {host_path = } {host_hash = }")
        with conn.cursor() as cur:
            try:
                cur.execute( f"SELECT id FROM `{self.files_db_name}`.`folders` WHERE host_id = ? AND path_hash = ? ;", ( host_id, host_hash, ))
                rows = cur.fetchall()
            except mariadb.Error as e:
                print( f"Error getting last media_id for detection {detection}: {e}")
        assert len( rows) <= 1
        if len( rows) == 1:
            #print( f"get_folder_id: folder_id {rows[0][0]} exists")
            return rows[0][0], host_path
        if abs_path == self.root_in_container:
            parent_id = None
        else:
            parent_id, _ = self.get_folder_id( conn, os.path.dirname( abs_path), host_id)
        #print( f"{parent_id = }")
        return self.create_folder_id( conn, host_id, host_path, host_hash, parent_id), host_path

    def create_folder_id( self, conn, host_id, folder_path, folder_hash, parent_id) -> int:
        print( f"create_folder_id {host_id = } {folder_path = } {folder_hash = } {parent_id = }")
        assert folder_path == os.path.abspath( folder_path)
        try:
            cur = conn.cursor()
            cur.execute( f"INSERT INTO `{self.files_db_name}`.`folders`" \
                         f" ( host_id, parent_id, path, path_hash, created_at, updated_at )" \
                         f" VALUES ( ?, ?, ?, ?, CURRENT_TIMESTAMP(3), CURRENT_TIMESTAMP(3) ) " \
                         f" RETURNING id ;", ( host_id, parent_id, folder_path, folder_hash, ))
            row = cur.fetchone()
            assert not row is None
            cur.close()
            conn.commit()
            return row[0]
        except mariadb.Error as e:
            print( f"Error connecting to MariaDB: (create_folder_id) {e}")
            sys.exit(1)

    def folders( self, conn, host_id, host_path=True, all_or_deleted=None):
        cur = conn.cursor()
        filter_str = ""
        if all_or_deleted is None:
            filter_str = "AND deleted_at IS NULL"
        else:
            if not all_or_deleted:
                filter_str = "AND deleted_at IS NOT NULL"
        cur.execute( f"SELECT id, path FROM `{self.files_db_name}`.`folders`"
                     f" WHERE host_id = ? {filter_str} ;", ( host_id, ))
        row = cur.fetchone()
        while not row is None:
            #print(f"ID: {row[0]}, Path: {row[1]}")
            if host_path:
                yield row[0], os.path.abspath( os.path.join( self.root_in_container, os.path.relpath( row[1], '/')))
            else:
                yield row[0], row[1]
            row = cur.fetchone()
        #print( f"No more folders in database")

    def delete_folder_id( self, conn, folder_id):
        print( f"delete_folder_id: {folder_id = }")
        with conn.cursor() as cur:
            try:
                cur = conn.cursor()
                cur.execute( f"UPDATE `{self.files_db_name}`.`folders`" \
                             f" SET deleted_at = CURRENT_TIMESTAMP(3) " \
                             f" WHERE id = ? AND deleted_at IS NULL" \
                             f" ;", ( folder_id, ))
                             #f" RETURNING id ;", ( folder_id, ))
                rows = cur.rowcount
                #print( f"{rows = }")
                assert rows == 1
            except mariadb.Error as e:
                print( f"Error connecting to MariaDB: (delete_folder_id) {e}")
                sys.exit(1)
        conn.commit()

    def count_files( self, conn, host_id=None, all_or_deleted=None):
        if host_id == "*":
            print( f"No host_id")
            for host in self.hosts( conn):
                file_rows = self.files( conn, all_columns=True, all_or_deleted=all_or_deleted)
                print( f"{host = } {len(list(file_rows))}")
        else:
            if host_id is None:
                host_id = self.curr_host_id
            #print( f"count_files {host_id = }")
            for folder_id, folder_path in self.folders( conn, host_id, host_path=False, all_or_deleted=True):
                file_rows = self.files( conn, folder_id, all_columns=True, all_or_deleted=all_or_deleted)
                print( f"{len(list(file_rows))}")

    def list_files( self, conn, host_id=None, all_or_deleted=None):
        if host_id == "*":
            print( f"No host_id")
            for host in self.hosts( conn):
                print( f"{host = }")
                for file_row in self.files( conn, all_columns=True, all_or_deleted=all_or_deleted):
                    print( f"ID: {file_row[0]:7d} Length: {file_row[2]:9d}  CTime {file_row[5]}  MTime {file_row[6]}"
                           f"#{file_row[7]} Del {file_row[10] if file_row[10] is not None else False}  {file_row[1]}")
        else:
            if host_id is None:
                host_id = self.curr_host_id
            #print( f"list_files {host_id = }")
            for folder_id, folder_path in self.folders( conn, host_id, host_path=False, all_or_deleted=True):
                for file_row in self.files( conn, folder_id, all_columns=True, all_or_deleted=all_or_deleted):
                    print( f"ID: {file_row[0]:7d} Length: {file_row[2]:9d}  CTime {file_row[5]}  MTime {file_row[6]}"
                           f"#{file_row[7]} Del {file_row[10] if file_row[10] is not None else False}  {file_row[1]}")

    """ public files
    """

    def get_file_id( self, conn, folder_id, file_name, file_stat, host_path) -> int:
        #print( f"get_file_id {folder_id = } {file_name = } {host_path = }")
        if self._path_is_ignored( os.path.join( host_path, file_name)):
            print( f"get_file_id: file IGNORED {host_path = } {file_name = }")
            return None
        with conn.cursor() as cur:
            try:
                cur.execute( f"SELECT id, length, mtime_ns FROM `{self.files_db_name}`.`files`"
                             f" WHERE folder_id = ? AND file_name = ? AND deleted_at IS NULL"
                             f" ;", ( folder_id, file_name, ))
                rows = cur.fetchall()
            except mariadb.Error as e:
                print( f"Error getting file_id {e}")
            assert len( rows) <= 1
            if len( rows) == 1:
                #print( f"get_file_id: exists {rows[0] = }")
                if file_stat.st_size == rows[0][1] and file_stat.st_mtime_ns == rows[0][2]:
                    #print( f"get_file_id: UNCHANGED file_id {rows[0][0]} {file_name} ")
                    return rows[0][0]
                # file was changed
                print( f"get_file_id: CHANGED file_id {rows[0][0]} {file_name} ")
                self.delete_file_id( conn, rows[0][0])
        return self.create_file_id( conn, folder_id, file_name, file_stat)

    def create_file_id( self, conn, folder_id, file_name, file_stat) -> int:
        print( f"create_file_id {folder_id = } {file_name = } {file_stat = }")
        try:
            cur = conn.cursor()
            #print( f"{datetime.fromtimestamp( file_stat.st_ctime_ns / 1e9, tz=timezone.utc) = }")
            #print( f"{file_stat.st_ctime_ns / 1e9 = }")
            cur.execute( f"INSERT INTO `{self.files_db_name}`.`files`" \
                         f" ( folder_id, file_name, length, ctime_ns, mtime_ns, ctime, mtime, file_hash, created_at, updated_at )" \
                         f" VALUES ( ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP(3), CURRENT_TIMESTAMP(3) ) " \
                         f" RETURNING id ;", ( folder_id, file_name, file_stat.st_size,
                                               file_stat.st_ctime_ns, file_stat.st_mtime_ns,
                                               datetime.fromtimestamp( file_stat.st_ctime_ns / 1e9, tz=timezone.utc), 
                                               datetime.fromtimestamp( file_stat.st_mtime_ns / 1e9, tz=timezone.utc), 
                                               -1, ))
            row = cur.fetchone()
            assert not row is None
            cur.close()
            conn.commit()
            return row[0]
        except mariadb.Error as e:
            print( f"Error connecting to MariaDB: (create_file_id) {e}")
            sys.exit(1)

    def files( self, conn, folder_id=None, all_columns=False, all_or_deleted=None):
        #print( f"files {folder_id = } {all_columns = } {all_or_deleted = }")
        if folder_id is None:
            where_str = ""
            param_lst = ( )
            if all_or_deleted is None:
                where_str = "WHERE deleted_at IS NULL"
            else:
                if not all_or_deleted:
                    where_str = "WHERE deleted_at IS NOT NULL"
        else:
            where_str = "WHERE folder_id = ? "
            param_lst = ( folder_id, )
            if all_or_deleted is None:
                where_str += "AND deleted_at IS NULL"
            else:
                if not all_or_deleted:
                    where_str += "AND deleted_at IS NOT NULL"
        columns = "id, file_name"
        if all_columns:
            columns += ", length, ctime_ns, mtime_ns, ctime, mtime, file_hash, created_at, updated_at, deleted_at"
        stmt = f"SELECT {columns}" \
               f" FROM `{self.files_db_name}`.`files`" \
               f" {where_str} ;"
        #print( stmt, param_lst)
        with conn.cursor() as cur:
            cur.execute( stmt, param_lst)
            row = cur.fetchone()
            while row is not None:
                #print(f"ID: {row[0]}, File: {row[1]}")
                yield row
                row = cur.fetchone()
        #print( f"No more files in database")

    def delete_file_id( self, conn, file_id):
        print( f"delete_file_id: {file_id = }")
        with conn.cursor() as cur:
            try:
                cur.execute( f"UPDATE `{self.files_db_name}`.`files`" \
                             f" SET deleted_at = CURRENT_TIMESTAMP(3)" \
                             f" WHERE id = ? AND deleted_at IS NULL" \
                             f" ;", ( file_id, ))
                             #f" RETURNING id AS b_id, deleted_at ;", ( file_id, ))
                rows = cur.rowcount
                #print( f"{rows = }")
                assert rows == 1
            except mariadb.Error as e:
                print( f"Error connecting to MariaDB: (delete_file_id) {e}")
                sys.exit(1)
        conn.commit()

    def get_next_filename( self, start_id, conn):
        cur = conn.cursor()
        cur.execute(f"SELECT id, path"
                    f" FROM `{self.photo_db_name}`.`media`"
                    " WHERE id > ? "
                    " ORDER BY id ASC "
                    " ;", (start_id,))
        row = cur.fetchone()
        while row is not None:
            #print(f"ID: {row[0]}, Path: {row[1]}")
            yield row[0], row[1]
            row = cur.fetchone()
        #print( f"No more media file in database")
        # return None

    def store_skipped_media_id( self, detection, media_id, cur):
        #print(f"store_skipped_media_id: {detection = } {media_id = }")
        try:
            cur.execute(f"INSERT INTO `{self.files_db_name}`.`skipped_media`"
                        f" ( detection, media_id, created_at, updated_at )"
                        f" VALUES ( ?, ?, CURRENT_TIMESTAMP(3), CURRENT_TIMESTAMP(3) ) "
                        f" ;", (detection, media_id, ))
        except mariadb.Error as e:
            print( f"Error connecting to MariaDB: (store_skipped_media_id) {e}")
            sys.exit(1)
        try:
            cur.execute(f"SELECT *"
                        f" FROM `{self.files_db_name}`.`skipped_media`"
                        f" WHERE detection = ? "
                        f" ;", (detection, ))
        except mariadb.Error as e:
            print( f"Error connecting to MariaDB Privileges store_skipped_media_id: {e}")
            sys.exit(1)
        for row in cur:
            # print(f"skipped_media: {row[0]} {row[1]} {row[2]} {row[3]} {row[4]} ")
            print( f"skipped_media: {row} ")

    def count_scanned_media_id( self, detection) -> int:
        conn = self.new_conn()
        cur = conn.cursor()
        try:
            cur.execute(f"SELECT COUNT(media_id), detection FROM `{self.photo_db_name}`.`image_faces`"
                        f" GROUP BY detection"
                        f" ;")
                        #f" WHERE detection = ?"
                        #f" ;", (detection, ))
        except mariadb.Error as e:
            print( f"Error connecting to MariaDB: (count_scanned_media_id) {e}")
            sys.exit(1)
        for row in cur.fetchall():
            print( f"scan_media count: {row[0]} for detection {row[1]} ")
        cur.close()
        conn.close()
        return row[0]

    def store_scanned_media_id( self, detection, media_id, cur):
        #print(f"store_scanned_media_id: {detection = } {media_id = }")
        try:
            cur.execute(f"INSERT INTO `{self.files_db_name}`.`scan_media`"
                        f" ( detection, media_id, created_at, updated_at )"
                        f" VALUES ( ?, ?, CURRENT_TIMESTAMP(3), CURRENT_TIMESTAMP(3) ) "
                        f" ON DUPLICATE KEY UPDATE media_id=?, updated_at=CURRENT_TIMESTAMP(3) "
                        f" ;", (detection, media_id, media_id, ))
        except mariadb.Error as e:
            print( f"Error connecting to MariaDB: (store_scanned_media_id I) {e}")
            sys.exit(1)
        try:
            cur.execute(f"SELECT *"
                        f" FROM `{self.files_db_name}`.`scan_media`"
                        f" WHERE detection = ? "
                        f" ;", (detection, ))
        except mariadb.Error as e:
            print( f"Error connecting to MariaDB: (store_scanned_media_id II) {e}")
            sys.exit(1)
        row = cur.fetchone()
        if row is not None:
            print( f"store_scanned_media_id: {row[0]} {row[1]} {row[2]} {row[3]} {row[4]} ")

    def get_face_group_id( self, class_name, cur):
        cur.execute(f"SELECT id"
                    f" FROM `{self.photo_db_name}`.`face_groups`"
                    f" WHERE label = ? "
                    f" ;", (class_name,))
        row = cur.fetchone()
        if row is None:
            # print(f"Class: {class_name} does not exist")
            cur.execute(f"INSERT INTO `{self.photo_db_name}`.`face_groups`"
                        f" ( face_groups.label, created_at, updated_at )"
                        f" VALUES ( ?, CURRENT_TIMESTAMP(3), CURRENT_TIMESTAMP(3) ) "
                        f" ;", (class_name,))
            cur.execute(f"SELECT *"
                        f" FROM `{self.photo_db_name}`.`face_groups`"
                        f" WHERE label = ? "
                        f" ;", (class_name,))
            row = cur.fetchone()
            if row is not None:
                print( f"Missing Face Group created: {class_name} {row[0]} {row[1]} {row[2]} {row[3]} ")
                face_group_id = row[0]
        else:
            face_group_id = row[0]
            # print(f"Apropriate Face Group found: {face_group_id} {class_name}")
        return face_group_id

    def store_result( self, detection, media_id, rect, face_group_id, score, cur):
        cur.execute(f"INSERT INTO `{self.photo_db_name}`.`image_faces`"
                    f" ( face_group_id, media_id, rectangle, confirmed, subgroup, detection, created_at, updated_at, descriptor )"
                    f" VALUES ( ?, ?, ?, 0, 0, ?, CURRENT_TIMESTAMP(3), CURRENT_TIMESTAMP(3), ? ) "
                    f" ;", (face_group_id, media_id, rect, detection, [face_group_id for element in range(128)]))
        cur.execute(f"SELECT *"
                    f" FROM `{self.photo_db_name}`.`image_faces`"
                    f" WHERE face_group_id = ? "
                    f" ;", (face_group_id,))
        row = cur.fetchone()
        #if row is not None:
            #print(f"Stored: {face_group_id} {row[0]} {row[1]} {row[2]} {row[3]} {row[4]} row[5] {row[6]} {row[7]} {row[8]} {row[9]} ")

    def remove_media_detections( self, media_id, detection):
        conn = self.new_conn()
        cur = conn.cursor()
        try:
            cur.execute(f"DELETE FROM `{self.photo_db_name}`.`image_faces`"
                        f" WHERE media_id = ? and detection = ?"
                        f" ;", ( media_id, detection, ))
        except mariadb.Error as e:
            print( f"Error connecting to MariaDB Privileges: {e}")
            sys.exit(1)
        print( f"deleted row count: {cur.rowcount} for {media_id = } {detection = } ")
        cur.close()
        conn.commit()
        conn.close()


##if __name__ == '__main__':
    #sys.exit(main())

