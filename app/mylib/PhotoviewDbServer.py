# Module Imports
import mariadb
import sys

class PhotoviewDbServer(object):
    port = 3306

    def __init__(self, root, root_pwd, user, user_pwd, host):
        self.root = root
        self.root_pwd = root_pwd
        self.user = user
        self.user_pwd = user_pwd
        self.host = host

    def new_conn(self, root=False):
        if root:
            user=self.root
            password=self.root_pwd
        else:
            user=self.user
            password=self.user_pwd
        # Connect to MariaDB Platform
        #print( PhotoviewDbServer.port)
        try:
            conn = mariadb.connect( user=user, password=password, host=self.host, port=PhotoviewDbServer.port,)
            return conn
        except mariadb.Error as e:
            print(f"Error connecting to MariaDB Connect Platform: {e}")
        return None


##if __name__ == '__main__':
    #sys.exit(main())

