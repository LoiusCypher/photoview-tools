# Module Imports
import mariadb
import sys

from mylib.PhotoviewDbServer import PhotoviewDbServer

class PhotoviewObjectServer( PhotoviewDbServer):

    def __init__(self, root, root_pwd, user, user_pwd, host, tools_db_name, photo_db_name):
        super().__init__( root, root_pwd, user, user_pwd, host)
        self.tools_db_name = tools_db_name
        self.photo_db_name = photo_db_name
        self.create_object_db()
        print( f"Object Database ready")

    def create_object_db( self):

        def create_table_scan_media( conn):
            # Get new Cursor
            cur = conn.cursor()
            try:
                cur.execute(f"CREATE TABLE IF NOT EXISTS `{self.tools_db_name}`.`scan_media` ("
                            " `id` bigint(20) NOT NULL AUTO_INCREMENT,"
                            " `created_at` datetime(3) DEFAULT NULL,"
                            " `updated_at` datetime(3) DEFAULT NULL,"
                            " `detection` bigint(20) NOT NULL UNIQUE,"
                            " `media_id` bigint(20) NOT NULL,"
                            " PRIMARY KEY (`id`)"
                            " )")
            except mariadb.Error as e:
                print(f"Error connecting to MariaDB Platform Table: {e}")
                sys.exit(1)
            #print("create_table_scan_media done")

        def create_table_skipped_media( conn):
            # Get new Cursor
            cur = conn.cursor()
            try:
                cur.execute(f"CREATE TABLE IF NOT EXISTS `{self.tools_db_name}`.`skipped_media` ("
                            " `id` bigint(20) NOT NULL AUTO_INCREMENT,"
                            " `created_at` datetime(3) DEFAULT NULL,"
                            " `updated_at` datetime(3) DEFAULT NULL,"
                            " `detection` bigint(20) NOT NULL,"
                            " `media_id` bigint(20) NOT NULL,"
                            " PRIMARY KEY (`id`)"
                            " )")
            except mariadb.Error as e:
                print(f"Error connecting to MariaDB Platform Table: {e}")
                sys.exit(1)
            #print("create_table_skipped_media done")

        def create_table_results( conn):
            # Get new Cursor
            cur = conn.cursor()
            try:
                cur.execute(f"CREATE TABLE IF NOT EXISTS `{self.tools_db_name}`.`results` ("
                            " `id` bigint(20) NOT NULL AUTO_INCREMENT,"
                            " `created_at` datetime(3) DEFAULT NULL,"
                            " `updated_at` datetime(3) DEFAULT NULL,"
                            " `detection` bigint(20) NOT NULL,"
                            " `file_path` bigint(20) NOT NULL,"
                            " `class_name` bigint(20) NOT NULL,"
                            " `region` bigint(20) NOT NULL,"
                            " `score` bigint(20) NOT NULL,"
                            " PRIMARY KEY (`id`)"
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
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{self.tools_db_name}` ;")
        except mariadb.Error as e:
            print(f"Error connecting to MariaDB Platform CREATE DB: {e}")
            sys.exit(1)
        try:
            cur.execute(f"GRANT ALL PRIVILEGES ON {self.tools_db_name}.* TO 'photoview'@'%' ;")
        except mariadb.Error as e:
            print(f"Error connecting to MariaDB Privileges: {e}")
            sys.exit(1)
        #print("create_object_database done")
        create_table_scan_media( conn)
        create_table_skipped_media( conn)
        conn.close()

    def get_last_media_id( self, detection, conn):
        last_id = -1
        cur = conn.cursor()
        try:
            cur.execute(f"SELECT media_id"
                        f" FROM `{self.tools_db_name}`.`scan_media`"
                        f" WHERE detection = ? "
                        f" ;", (detection, ))
            row = cur.fetchone()
            if row is not None:
                print(f"get_last_media_id: {detection = } last_id {row[0]} ")
                last_id = row[0]
            else:
                print(f"get_last_media_id: no row, fall back to default ")
        except mariadb.Error as e:
            print(f"Error getting last media_id for detection {detection}: {e}")
            sys.exit(1)
        return last_id

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
        print(f"No more media file in database")
        # return None

    def store_skipped_media_id( self, detection, media_id, cur):
        #print(f"store_skipped_media_id: {detection = } {media_id = }")
        try:
            cur.execute(f"INSERT INTO `{self.tools_db_name}`.`skipped_media`"
                        f" ( detection, media_id, created_at, updated_at )"
                        f" VALUES ( ?, ?, CURRENT_TIMESTAMP(3), CURRENT_TIMESTAMP(3) ) "
                        f" ;", (detection, media_id, ))
        except mariadb.Error as e:
            print(f"Error connecting to MariaDB Privileges store_skipped_media_id: {e}")
            sys.exit(1)
        try:
            cur.execute(f"SELECT *"
                        f" FROM `{self.tools_db_name}`.`skipped_media`"
                        f" WHERE detection = ? "
                        f" ;", (detection, ))
        except mariadb.Error as e:
            print(f"Error connecting to MariaDB Privileges store_skipped_media_id: {e}")
            sys.exit(1)
        for row in cur:
            # print(f"skipped_media: {row[0]} {row[1]} {row[2]} {row[3]} {row[4]} ")
            print(f"skipped_media: {row} ")

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
            print(f"Error connecting to MariaDB Privileges: {e}")
            sys.exit(1)
        for row in cur.fetchall():
            print(f"scan_media count: {row[0]} for detection {row[1]} ")
        cur.close()
        conn.close()
        return row[0]

    def store_scanned_media_id( self, detection, media_id, cur):
        #print(f"store_scanned_media_id: {detection = } {media_id = }")
        try:
            cur.execute(f"INSERT INTO `{self.tools_db_name}`.`scan_media`"
                        f" ( detection, media_id, created_at, updated_at )"
                        f" VALUES ( ?, ?, CURRENT_TIMESTAMP(3), CURRENT_TIMESTAMP(3) ) "
                        f" ON DUPLICATE KEY UPDATE media_id=?, updated_at=CURRENT_TIMESTAMP(3) "
                        f" ;", (detection, media_id, media_id, ))
        except mariadb.Error as e:
            print(f"Error connecting to MariaDB Privileges: {e}")
            sys.exit(1)
        try:
            cur.execute(f"SELECT *"
                        f" FROM `{self.tools_db_name}`.`scan_media`"
                        f" WHERE detection = ? "
                        f" ;", (detection, ))
        except mariadb.Error as e:
            print(f"Error connecting to MariaDB Privileges: {e}")
            sys.exit(1)
        row = cur.fetchone()
        if row is not None:
            print(f"store_scanned_media_id: {row[0]} {row[1]} {row[2]} {row[3]} {row[4]} ")

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
                print(f"Missing Face Group created: {class_name} {row[0]} {row[1]} {row[2]} {row[3]} ")
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
            print(f"Error connecting to MariaDB Privileges: {e}")
            sys.exit(1)
        print(f"deleted row count: {cur.rowcount} for {media_id = } {detection = } ")
        cur.close()
        conn.commit()
        conn.close()


##if __name__ == '__main__':
    #sys.exit(main())

