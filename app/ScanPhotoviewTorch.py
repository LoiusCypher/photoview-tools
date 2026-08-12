# Module Imports
import mariadb
import os
import sys
import argparse

from torchvision.models.detection import MaskRCNN_ResNet50_FPN_Weights, maskrcnn_resnet50_fpn
import torch
#print("After import torch")

from PIL import Image, ImageOps
import numpy as np

# Root directory of the model
OBJECT_DETECTOR_ROOT_DIR = os.path.abspath("/Mask-RCNN_model")
#print(OBJECT_DETECTOR_ROOT_DIR)

tools_db_name = "object_detector"
photo_db_name = "photoview"

# Import Mask RCNN
sys.path.append(OBJECT_DETECTOR_ROOT_DIR)  # To find local version of the library
from mrcnn import utils
import mrcnn.model as modellib
#from mrcnn import visualize
#print("After import mrcnn")

# Import COCO config
sys.path.append(os.path.join(OBJECT_DETECTOR_ROOT_DIR, "samples/coco/"))  # To find local version
import coco
#print("After import coco")

class_names = ['BG', 'person', 'bicycle', 'car', 'motorcycle', 'airplane',
               'bus', 'train', 'truck', 'boat', 'traffic light',
               'fire hydrant', 'stop sign', 'parking meter', 'bench', 'bird',
               'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear',
               'zebra', 'giraffe', 'backpack', 'umbrella', 'handbag', 'tie',
               'suitcase', 'frisbee', 'skis', 'snowboard', 'sports ball',
               'kite', 'baseball bat', 'baseball glove', 'skateboard',
               'surfboard', 'tennis racket', 'bottle', 'wine glass', 'cup',
               'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple',
               'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza',
               'donut', 'cake', 'chair', 'couch', 'potted plant', 'bed',
               'dining table', 'toilet', 'tv', 'laptop', 'mouse', 'remote',
               'keyboard', 'cell phone', 'microwave', 'oven', 'toaster',
               'sink', 'refrigerator', 'book', 'clock', 'vase', 'scissors',
               'teddy bear', 'hair drier', 'toothbrush']

def load_trained_model_torch():
    # model = maskrcnn_resnet50_fpn(weights=MaskRCNN_ResNet50_FPN_Weights.DEFAULT)
    model = maskrcnn_resnet50_fpn(weights=MaskRCNN_ResNet50_FPN_Weights.COCO_V1)
    model.eval()
    return model

class InferenceConfig(coco.CocoConfig):
    # Set batch size to 1 since we'll be running inference on
    GPU_COUNT = 1
    IMAGES_PER_GPU = 1

def load_trained_model(object_detector_root_dir):
    # Directory to save logs and trained model
    MODEL_DIR = os.path.join(object_detector_root_dir, "logs")

    # Local path to trained weights file
    #coco_model_path = os.path.join(object_detector_root_dir, "mask_rcnn_coco.h5")
    coco_model_path = os.path.join(MODEL_DIR, "mask_rcnn_coco.h5")
    # Download COCO trained weights from Releases if needed
    if not os.path.exists(coco_model_path):
        utils.download_trained_weights(coco_model_path)

    config = InferenceConfig()
    config.display()

    # Create model object in inference mode.
    model = modellib.MaskRCNN(mode="inference", model_dir=MODEL_DIR, config=config)

    # Load weights trained on MS-COCO
    model.load_weights(coco_model_path, by_name=True)

    return model

def print_results( file_names, results):
    print( 'File(s):', file_names, 'results: ', len(results))

    # Print class names
    for file_name, r in zip( file_names, results):
        print( 'File:', file_name, 'results: ', len(results))

        print( 'keys:', len(r.items()), end=" ")
        for key, value in r.items() :
            print (key, end=" ")
        print(' ')

        print( 'rois: ', len(r['rois']), r['rois'])
        print( 'masks:', len(r['masks']), len(r['masks'][0]), len(r['masks'][0][0]), r['masks'][0])

        print( 'class_ids:', len(r['class_ids']), end=" ")
        for idx in r['class_ids'] :
            print( idx, class_names[idx], end=" ")
        print(' ')

        print( 'scores:', len(r['scores']), r['scores'])

class PhotoviewServer(object):
    port = 3306

    def __init__(self, root, root_pwd, user, user_pwd, host, tools_db_name, photo_db_name):
        self.root = root
        self.root_pwd = root_pwd
        self.user = user
        self.user_pwd = user_pwd
        self.host = host
        self.tools_db_name = tools_db_name
        self.photo_db_name = photo_db_name
        self.create_object_db()
        print( f"Object Database ready")

    def new_conn(self, root=False):
        if root:
            user=self.root
            password=self.root_pwd
        else:
            user=self.user
            password=self.user_pwd
        # Connect to MariaDB Platform
        #print( PhotoviewServer.port)
        try:
            # database="photoview"
            conn = mariadb.connect(
                user=user,
                password=password,
                host=self.host,
                port=PhotoviewServer.port,
            )
            return conn
        except mariadb.Error as e:
            print(f"Error connecting to MariaDB Connect Platform: {e}")
        return None

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

    def get_last_media_id( self, detection, skip, conn):
        last_id = -1
        detection = 1
        cur = conn.cursor()
        try:
            cur.execute(f"SELECT media_id"
                        f" FROM `{self.tools_db_name}`.`scan_media`"
                        f" WHERE detection = ? "
                        f" ;", (detection, ))
            row = cur.fetchone()
            if row is not None:
                print(f"get_last_media_id: {row[0]} ")
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
            print(f"ID: {row[0]}, Path: {row[1]}")
            yield row[0], row[1]
            row = cur.fetchone()
        print(f"No more media file in database")
        # return None

    def store_skipped_media_id( self, detection, media_id, conn):
        cur = conn.cursor()
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

    def store_scanned_media_id( self, detection, media_id, conn):
        cur = conn.cursor()
        try:
            cur.execute(f"INSERT INTO `{self.tools_db_name}`.`scan_media`"
                        f" ( detection, media_id, created_at, updated_at )"
                        f" VALUES ( 1, ?, CURRENT_TIMESTAMP(3), CURRENT_TIMESTAMP(3) ) "
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
            print(f"scan_media: {row[0]} {row[1]} {row[2]} {row[3]} {row[4]} ")
        cur.close()

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

    def store_result( self, detection, media_id, height, width, roi, face_group_id, score, cur):
        rect = f"{min(roi[1],roi[3])/width:8.6f}:{max(roi[1],roi[3])/width:8.6f}:{min(roi[0],roi[2])/height:8.6f}:{max(roi[0],roi[2])/height:8.6f}"
        # print(f"Rect: {rect}  {score}% {roi[0]} {roi[1]} {roi[2]} {roi[3]} w: {width} h: {height}")
        cur.execute(f"INSERT INTO `{self.photo_db_name}`.`image_faces`"
                    f" ( face_group_id, media_id, rectangle, confirmed, subgroup, detection, created_at, updated_at, descriptor )"
                    f" VALUES ( ?, ?, ?, 0, 0, ?, CURRENT_TIMESTAMP(3), CURRENT_TIMESTAMP(3), ? ) "
                    f" ;", (face_group_id, media_id, rect, detection, [class_id for element in range(128)]))
        cur.execute(f"SELECT *"
                    f" FROM `{self.photo_db_name}`.`image_faces`"
                    f" WHERE face_group_id = ? "
                    f" ;", (face_group_id,))
        row = cur.fetchone()
        if row is not None:
            print(f"Stored: {class_names[class_id]} {row[0]} {row[1]} {row[2]} {row[3]} {row[4]} row[5] {row[6]} {row[7]} {row[8]} {row[9]} ")

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument( "--version", "-V", action="store_true", help="show version")
    parser.add_argument( "--debug", "-D", action="store_true", help="enable debug output")
    parser.add_argument( "--restart", "-R", action="store_true", help="Restart scanning from first file",)
    args = parser.parse_args()

    db_server = PhotoviewServer( root="root", root_pwd="superphotosecret",
                                 user="photoview", user_pwd="photosecret",
                                 host="192.168.2.227",
                                 tools_db_name=tools_db_name, photo_db_name=photo_db_name)

    #model = load_trained_model(OBJECT_DETECTOR_ROOT_DIR)
    model = load_trained_model_torch()
    #print(f"Got model")

    conn = db_server.new_conn()
    if conn is None: return

    detection = 1
    last_id = -1
    if not args.restart:
        print(f"Continue to process files")
        last_id = db_server.get_last_media_id( detection, True, conn)

    # If not starting from scratch, skip current, because we probably crashed on current
    if False and (last_id != -1):
        db_server.store_skipped_media_id( last_id, conn)
        last_id, path = next(db_server.get_next_filename( last_id, conn))
        db_server.store_scanned_media_id( last_id, conn)
        conn.commit()
        print(f"Skip: {last_id}, Path: {path}")
    for media_id, path in db_server.get_next_filename( last_id, conn):
        print(f"ID: {media_id}, Path: {path}")
        if not os.path.isfile(path):
            print(f"Error {path} does not exist")
            return 1
    
        #try:
            #with skimage.io.imread(path) as image:
                #print( type(image), np.dtype(image), image.shape)

        if path.endswith(".mp4") or path.endswith(".svg"):
            db_server.store_skipped_media_id( media_id, conn)
            conn.commit()
            print(f"Skipping: {media_id}, Path: {path}")
            continue

        # Open the image
        img = Image.open(path)

        # Automatically read EXIF tags and transpose the image correctly
        img_trans = ImageOps.exif_transpose(img)
        print( "img_trans", type(img_trans), img_trans.mode)
        match img_trans.mode:
            case "1" | "P" | "I" | "L" | "RGBA":
                img_trans = img_trans.convert("RGB")
                print( "img_trans convert to RGB", type(img_trans), img_trans.mode)
        img_oriented = np.array(img_trans) # .astype(np.int16)
        print( "img_oriented:", type(img_oriented), type(img_oriented[0]), img_oriented.dtype, img_oriented.shape)
        # print(image.shape, img_oriented.shape)

        if img_oriented.shape[2] == 2:
            db_server.store_skipped_media_id( media_id, conn)
            conn.commit()
            print(f"Skiped: {media_id}, Path: {path}")
            continue

        #results = model.detect([image], verbose=0)
        results = model.detect([img_oriented], verbose=0)
        print_results( [path], results)

        cur = conn.cursor()
        # print( f"media_id: {media_id}  Width: {width} Height: {height}")
        for roi, class_id, score in zip( result['rois'], result['class_ids'], result['scores']):
            face_group_id = db_server.get_face_group_id( class_names[class_id], cur)
            db_server.store_result( detection, media_id, img_oriented.shape[0], img_oriented.shape[1], roi, face_group_id, score, conn)
        db_server.store_scanned_media_id( detection, media_id, conn)
        #conn.commit()
        conn.rollback()

    conn.close()
    return 0

if __name__ == '__main__':
    sys.exit(main())

