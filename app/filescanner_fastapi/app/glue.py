import os
from app.alchemyFilesDB import FilesDB


files_db_name = "files_collector"
tools_db_name = "object_detector"
photo_db_name = "photoview"
host_fs='/host_fs'

curr_hostname = os.environ['CURR_HOSTNAME']
#print(f"{curr_hostname}")
assert curr_hostname is not None
mariadb_conn = os.environ['MARIADB_CONN']
#print(f"{mariadb_conn}")

file_db_prod = FilesDB( curr_hostname, host_fs, mariadb_conn, 'db_files_prod')
file_db = FilesDB( curr_hostname, host_fs, mariadb_conn, 'db_files_dev')
