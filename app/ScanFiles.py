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

def check_for_removed_items( db, host_id, subtree_to_check=None):
    #print( f"{host_id = } {root_in_container = }")
    conn = db.new_conn()
    assert conn is not None
    if subtree_to_check is None:
        subtree_to_check = db.root_in_container
    for folder_id, folder_host_path in db.folders( conn, host_id):
        if not folder_host_path.startswith( subtree_to_check):
            print( f"Skip {folder_host_path = } {folder_id = } not part of {subtree_to_check = }")
        else:
            #print( f"{db.root_in_container = } {folder_host_path = } {folder_id = }")
            #print( f"{os.path.join( db.root_in_container, folder_host_path) = }")
            if not os.path.isdir( os.path.join( db.root_in_container, folder_host_path)):
                print( f"delete_folder {folder_id} {folder_host_path}")
                db.delete_folder_id( conn, folder_id)
            else:
                for file_id, file_name in db.files( conn, folder_id=folder_id):
                    #print( f"{root_in_container = } {folder_path = } {file_name = }")
                    #print( f"{os.path.join( folder_path, file_name) = }")
                    if not os.path.isfile( os.path.join( folder_host_path, file_name)):
                        print( f"delete_file {file_id} {folder_host_path} {file_name}")
                        db.delete_file_id( conn, file_id)
    conn.close()

def check_for_new_or_updated_items( db, host_id, subtree_to_update=None, sha=False):
    #print( f"{host_id = } {subtree_to_update = }")
    conn = db.new_conn()
    assert conn is not None
    if subtree_to_update is None:
        subtree_to_update = db.root_in_container
    for curr, dirs, files in os.walk( subtree_to_update):
        folder_id, host_folder = db.get_folder_id( conn, curr)
        #print( f"{curr = } {folder_id = } {files = }")
        if folder_id is not None:
            for file_name in files:
                file_path = os.path.join( curr, file_name)
                file_stat = os.lstat( file_path)
                file_id = db.get_file_id( conn, folder_id, file_name, file_stat, host_folder, sha)
                #print( curr, file_name, file_id)
            #print( f"{curr = } {dirs = }")
            for sub_dir in dirs:
                folder_path = os.path.join( curr, sub_dir)
                folder_id, _ = db.get_folder_id( conn, folder_path)
                #print( curr, sub_dir, folder_id)
    conn.close()

host_fs='/host_fs'

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument( "--version", "-V", action="store_true", help="show version")
    parser.add_argument( "--host-name", required=True, help="Host name")
    parser.add_argument( "--host-ipv4", required=True, help="Host IPV4 address")
    subparsers = parser.add_subparsers(dest='subcommand')
    subparsers.required = True 
    parser_ignore = subparsers.add_parser('ignore')
    parser_ignore.add_argument( "pattern", help="Path pattern to ignore",)
    #group = parser_ignore.add_mutually_exclusive_group()
    #group.add_argument( "--remove", action="store_true", help="Remove pattern from ignore list in db",)
    parser_ignore.add_argument( "--remove", action="store_true", help="Remove pattern from ignore list in db",)
    parser_ignore.add_argument( "--list", action="store_true", help="List ignore pattern",)
    parser_list = subparsers.add_parser('list')
    group = parser_list.add_mutually_exclusive_group()
    group.add_argument( "--folders", action="store_true", help="Only list folders in db",)
    group.add_argument( "--files", action="store_true", help="Only list files in db",)
    group.add_argument( "--ignores", action="store_true", help="Only ignore patterns in db",)
    parser_list.add_argument( "--deleted", action="store_false", help="List deleted items",)
    parser_count = subparsers.add_parser('count')
    parser_count.add_argument( "--folders", action="store_true", help="Only count folders in db",)
    parser_count.add_argument( "--files", action="store_true", help="Only count files in db",)
    parser_count.add_argument( "--deleted", action="store_false", help="Count deleted items",)
    parser_check = subparsers.add_parser('check')
    parser_check.add_argument( "--removed", action="store_true", help="Check for removed items",)
    parser_check.add_argument( "--new-or-changed", action="store_true", help="Check for new or changed items",)
    parser_check.add_argument( "--subtree", "-S", help="Scan partial subtree",)
    parser_check.add_argument( "--sha", action="store_true", help="Compute SHA3 checksums",)
    parser.add_argument( "--debug", "-D", action="store_true", help="enable debug output")
    parser.add_argument( "--recreate-database", "-R", action="store_true", help="Recreate database",)
    args = parser.parse_args()

    try:
        subtree = os.path.abspath( os.path.join( host_fs, args.subtree.strip('/')))
        assert os.path.isdir( subtree)
    except:
        subtree = None
    print(f"{subtree = }")

    db_server = PhotoviewFilesServer( root="root", root_pwd="superphotosecret",
                                      user="photoview", user_pwd="photosecret",
                                      db_host_ip_or_dns="192.168.2.227",
                                      files_db_name=files_db_name,
                                      recreate=args.recreate_database)

    host_id = db_server.set_host( host_fs, host_name=args.host_name, ipv4=args.host_ipv4)

    print( f"{args = }")

    if args.subcommand == "ignore":
        if args.list:
            db_server.list_ignore_patterns()
        if args.remove:
            db_server.remove_ignore_pattern( args.pattern)
        else:
            db_server.add_ignore_pattern( args.pattern)

    if args.subcommand == "count":
        conn = db_server.new_conn()
        if args.folders or not args.files:
            db_server.count_folders( conn, args.deleted)
        if not args.folders or args.files:
            db_server.count_files( conn, args.deleted)

    if args.subcommand == "list":
        conn = db_server.new_conn()
        if args.folders or not (args.files or args.ignores):
            db_server.list_folders( conn, args.deleted)
        if args.files or not (args.folders or args.ignores):
            db_server.list_files( conn, args.deleted)
        if not (args.folders or args.files) or args.ignores:
            db_server.list_ignore_patterns( args.deleted)

    if args.subcommand == "check":
        if args.removed or not args.new_or_changed:
            print( "check_recorded_tree")
            check_for_removed_items( db_server, host_fs, subtree)
        if not args.removed or args.new_or_changed:
            print( "update_recorded_tree")
            check_for_new_or_updated_items( db_server, host_fs, subtree_to_update=subtree, sha=args.sha)

    return 0

    print( f"Only Deleted")
    db_server.list_folders( conn, host_id, all_or_deleted=False)
    db_server.list_files( conn, host_id=host_id, all_or_deleted=False)

    return -2

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

