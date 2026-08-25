# Module Imports
import os
import sys
import argparse

from mylib.PhotoviewFilesServer import PhotoviewFilesServer

files_db_name = "files_collector"
tools_db_name = "object_detector"
photo_db_name = "photoview"

#import os
#from os.path import join, getsize

def check_for_removed_items( db, container_subtree_to_check):
    #print( f"{root_in_container = }")
    if container_subtree_to_check is None:
        container_subtree_to_check = db.root_in_container
    with db.new_conn() as conn:
        for folder_id, folder_container_path in db.all_folders( conn):
            if folder_container_path.startswith( container_subtree_to_check):
                #print( f"{db.root_in_container = } {folder_container_path = } {folder_id = }")
                if os.path.isdir( folder_container_path):
                    for file_id, file_name in db.all_files( conn, folder_id=folder_id):
                        #print( f"{root_in_container = } {folder_path = } {file_name = }")
                        #print( f"{os.path.join( folder_container_path, file_name) = }")
                        if not os.path.isfile( os.path.join( folder_container_path, file_name)):
                            print( f"NOT isfile {file_id} {os.path.join( folder_container_path, file_name) = }")
                            db.delete_file_id( conn, file_id)
                else:
                    print( f"delete_folder not isdir {folder_id} {folder_container_path}")
                    db.delete_folder_id( conn, folder_id)
            else:
                print( f"Skip {folder_container_path = } {folder_id = } not part of {container_subtree_to_check = }")

def check_for_new_or_updated_items( db, container_subtree_to_update, sha):
    #print( f"{container_subtree_to_update = }")
    if container_subtree_to_update is None:
        container_subtree_to_update = db.root_in_container
    with db.new_conn() as conn:
        for curr, dirs, files in os.walk( container_subtree_to_update):
            folder_id, host_folder = db.get_folder_id( conn, curr)
            #print( f"{curr = } {folder_id = } {files = }")
            if folder_id is not None:
                for file_name in files:
                    file_path = os.path.join( curr, file_name)
                    if os.path.isfile( file_path):
                        file_stat = os.lstat( file_path)
                        file_id = db.get_file_id( conn, folder_id, file_name, file_stat, host_folder, sha)
                        #print( curr, file_name, file_id)
                    else:
                        if os.path.islink( file_path):
                            print( "IS NOT file NOR link", file_paath)
                #print( f"{curr = } {dirs = }")
                for sub_dir in dirs:
                    folder_path = os.path.join( curr, sub_dir)
                    folder_id, _ = db.get_folder_id( conn, folder_path)
                    #print( curr, sub_dir, folder_id)

host_fs='/host_fs'

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument( "--version", "-V", action="store_true", help="show version")
    parser.add_argument( "--recreate-database", "-R", action="store_true", help="Recreate database",)
    parser.add_argument( "--debug", "-D", action="store_true", help="enable debug output")
    parser.add_argument( "host_name", help="Host name")
    # sub commands
    subparsers = parser.add_subparsers(dest='subcommand')
    subparsers.required = True 
    parser_ignore = subparsers.add_parser('ignore')
    parser_list = subparsers.add_parser('list')
    parser_count = subparsers.add_parser('count')
    parser_check = subparsers.add_parser('check')
    parser_hosts = subparsers.add_parser('hosts')
    parser_init = subparsers.add_parser('clear')
    # ignore
    parser_ignore.add_argument( "pattern", nargs='?', help="Path pattern to ignore",)
    parser_ignore.add_argument( "--remove", action="store_true", help="Remove pattern from ignore list in db",)
    parser_ignore.add_argument( "--update-defaults", action="store_true", help="Update patterns from defaults",)
    # list
    group = parser_list.add_mutually_exclusive_group()
    group.add_argument( "--hosts", action="store_true", help="Only list hosts in db",)
    group.add_argument( "--ignores", action="store_true", help="Only list ignore patterns in db",)
    group.add_argument( "--folders", action="store_true", help="Only list folders in db",)
    group.add_argument( "--files", action="store_true", help="Only list files in db",)
    parser_list.add_argument( "--deleted", action="store_true", help="List deleted items",)
    # count
    group = parser_count.add_mutually_exclusive_group()
    group.add_argument( "--hosts", action="store_true", help="Only list hosts in db",)
    group.add_argument( "--ignores", action="store_true", help="Only list ignore patterns in db",)
    group.add_argument( "--folders", action="store_true", help="Only list folders in db",)
    group.add_argument( "--files", action="store_true", help="Only list files in db",)
    parser_count.add_argument( "--deleted", action="store_true", help="Count deleted items",)
    parser_count.add_argument( "--every-host", action="store_true", help="Count items for every hosts",)
    # check
    parser_check.add_argument( "--removed", action="store_true", help="Check for removed items",)
    parser_check.add_argument( "--new-or-changed", action="store_true", help="Check for new or changed items",)
    parser_check.add_argument( "--subtree", "-S", help="Scan partial subtree",)
    parser_check.add_argument( "--sha", action="store_true", help="Compute SHA3 checksums",)
    # hosts
    #parser_hosts.add_argument( "--list-all", action="store_true", help="List all hosts",)
    #parser_hosts.add_argument( "--update-ignores", action="store_true", help="List all hosts",)
    #parser_hosts.add_argument( "--host-ipv4", help="Host IPV4 address")

    args = parser.parse_args()

    print( f"{args = }")

    try:
        container_subtree = os.path.abspath( os.path.join( host_fs, args.subtree.strip('/')))
        assert os.path.isdir( container_subtree)
    except:
        container_subtree = None
    print(f"{container_subtree = }")

    db_server = PhotoviewFilesServer( root="root", root_pwd="superphotosecret",
                                      user="photoview", user_pwd="photosecret",
                                      db_host_ip_or_dns="192.168.2.227",
                                      files_db_name=files_db_name,
                                      recreate=args.recreate_database)

    #db_server.set_host( host_fs, host_name=args.host_name, ipv4=args.host_ipv4)
    db_server.set_host( host_fs, args.host_name)

    #db_server.test_path_is_ignored( "/var/lib/docker/volumes/6eee01d3d25aa65deed671e75bd2b42bf3ffd68eb3c6f8c32439852c24d1a5bc/_data/temp")

    if args.subcommand == "clear":
        print( f"Deleted:", db_server.clear_folders_and_files())

    if args.subcommand == "ignore":
        if args.update_defaults:
            with db_server.new_conn() as conn:
                added_cnt = db_server.update_default_ignored_paths( conn, None)
                print( f"{added_cnt} entries added")
        else:
            if args.remove:
                ids = db_server.remove_ignore_pattern( args.pattern)
                if ids is None:
                    print( f"No entries removed")
                else:
                    print( f"{ids} entry removed")
            else:
                added_cnt = db_server.add_ignore_pattern( args.pattern)
                print( f"{added_cnt} entries added")

    if args.subcommand == "list":
        _del = None
        if args.deleted:
            _del = False
        if args.hosts or not (args.ignores or args.folders or args.files):
            db_server.list_hosts( all_or_deleted=_del)
        if args.ignores or not (args.hosts or args.folders or args.files):
            db_server.list_ignore_patterns( all_or_deleted=_del)
        if args.folders or not (args.hosts or args.ignores or args.files):
            db_server.list_folders( all_or_deleted=_del)
        if args.files or not (args.hosts or args.ignores or args.folders):
            db_server.list_files( all_or_deleted=_del)

    if args.subcommand == "hosts":
        #if args.list_all:
            db_server.list_hosts( host_id='*')

    if args.subcommand == "count":
        _hosts = None
        if args.every_host:
            _hosts = "*"
        _del = None
        if args.deleted:
            _del = False
        if args.hosts or not (args.ignores or args.folders or args.files):
            host_cnt = db_server.count_hosts( all_or_deleted=_del)
            print( f"Hosts: {host_cnt}")
        if args.ignores or not (args.hosts or args.folders or args.files):
            for host_id, ignore_cnt in db_server.count_ignores( host_id=_hosts, all_or_deleted=_del):
                print( f"Ignores {host_id}: {ignore_cnt}")
        if args.folders or not (args.hosts or args.ignores or args.files):
            for host_id, folder_cnt in db_server.count_folders( host_id=_hosts, all_or_deleted=_del):
                print( f"Folders {host_id}:: {folder_cnt}")
        if args.files or not (args.hosts or args.ignores or args.folders):
            for host_id, file_cnt in db_server.count_files( host_id=_hosts, all_or_deleted=_del):
                print( f"Files {host_id}:: {file_cnt}")

    if args.subcommand == "check":
        if args.removed or not args.new_or_changed:
            print( "check_recorded_tree")
            check_for_removed_items( db_server, container_subtree)
        if not args.removed or args.new_or_changed:
            print( "update_recorded_tree")
            check_for_new_or_updated_items( db_server, container_subtree, args.sha)

    return 0

    detection = 2
    last_id = -1
    #last_id = 1
    #last_id = 2
    if not args.restart:
        print(f"Continue to process files")
        last_id = db_server.get_last_media_id( detection, conn)
        if (last_id != -1):
            last_id, path = next(db_server.get_next_filename( last_id, conn))
            cur = conn.cursor()
            db_server.store_skipped_media_id( detection, last_id, cur)
            db_server.store_scanned_media_id( detection, last_id, cur)
            cur.close()
            conn.commit()
            print(f"Skip: {last_id}, Path: {path}")

    # If not starting from scratch, skip current, because we probably crashed on current
    for media_id, path in db_server.get_next_filename( last_id, conn):
        print(f"ID: {media_id}, Path: {path}")
        if not os.path.isfile(path):
            print(f"Error {path} does not exist")
            return 1

        if args.detection_remove:
            db_server.remove_media_detections( media_id, detection)
            db_server.remove_media_detections( media_id, 1)

        #try:
            #with skimage.io.imread(path) as image:
                #print( type(image), np.dtype(image), image.shape)

        if path.endswith(".mp4") or path.endswith(".svg"):
            db_server.store_skipped_media_id( media_id, conn)
            conn.commit()
            print(f"Skipping: {media_id}, Path: {path}")
            continue

        # Open the image
        pil_img = Image.open(path)
        #print( f"pil_img        {type(pil_img) = } {pil_img.mode = } {pil_img.size = }")

        # Automatically read EXIF tags and transpose the image correctly
        #pil_img_trans = ImageOps.exif_transpose(pil_img)
        #print( f"pil_img_trans {type(pil_img_trans) = } {pil_img_trans.mode = } {pil_img_trans.size = }")
        #match pil_img_trans.mode:
            #case "1" | "P" | "I" | "L" | "RGBA":
                #pil_img_trans = pil_img_trans.convert("RGB")
                #print( "pil_img_trans convert to RGB", type(pil_img_trans), pil_img_trans.mode)

        tensor_img_oriented = transformations( ImageOps.exif_transpose( pil_img))
        #print( "tensor_img_oriented:", type(tensor_img_oriented), type(tensor_img_oriented[0]), tensor_img_oriented.dtype, tensor_img_oriented.shape)
        result = model([tensor_img_oriented])[0]

        cur = conn.cursor()
        # print( f"media_id: {media_id}  Width: {width} Height: {height}")
        for box, label, score in zip( result['boxes'], result['labels'], result['scores']):
            if score > 0.9:
                width = tensor_img_oriented.shape[2]
                height = tensor_img_oriented.shape[1]
                print(f"  {detection = } {classnames[label]:20s} {width = } {height = } {score = }")
                #print(f"  {box = }")
                min0 = min(box[0],box[2])
                min1 = min(box[1],box[3])
                max0 = max(box[0],box[2])
                max1 = max(box[1],box[3])
                rect = f"{min0/width:8.6f}:{max0/width:8.6f}:{min1/height:8.6f}:{max1/height:8.6f}"

                face_group_id = db_server.get_face_group_id( classnames[label], cur)
                db_server.store_result( detection, media_id, rect, face_group_id, score, cur)
                #break
            else:
                if score > 0.75:
                    print( f"skipped: {media_id}  {classnames[label]:20s} {score:03f}")
        db_server.store_scanned_media_id( detection, media_id, cur)
        conn.commit()
        #conn.rollback()

        if args.single:
            break

    conn.close()
    return 0

if __name__ == '__main__':
    sys.exit(main())

