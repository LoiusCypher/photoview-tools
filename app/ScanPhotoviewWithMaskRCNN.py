# Module Imports
import mariadb
import os
# import skimage.io
import sys

from PIL import Image, ImageOps
import numpy as np

# Root directory of the model
OBJECT_DETECTOR_ROOT_DIR = os.path.abspath("/Mask-RCNN_model")
# print(OBJECT_DETECTOR_ROOT_DIR)

tools_db_name = "object_detector"

# Import Mask RCNN
sys.path.append(OBJECT_DETECTOR_ROOT_DIR)  # To find local version of the library
from mrcnn import utils
import mrcnn.model as modellib
#from mrcnn import visualize

# Import COCO config
sys.path.append(os.path.join(OBJECT_DETECTOR_ROOT_DIR, "samples/coco/"))  # To find local version
import coco

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

class InferenceConfig(coco.CocoConfig):
    # Set batch size to 1 since we'll be running inference on
    GPU_COUNT = 1
    IMAGES_PER_GPU = 1

def load_trrained_model(object_detector_root_dir):
    # Directory to save logs and trained model
    MODEL_DIR = os.path.join(object_detector_root_dir, "logs")

    # Local path to trained weights file
    coco_model_path = os.path.join(object_detector_root_dir, "mask_rcnn_coco.h5")
    # Download COCO trained weights from Releases if needed
    if not os.path.exists(coco_model_path):
        utils.download_trained_weights(coco_model_path)

    config = InferenceConfig()
    # config.display()

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

def create_table_scan_media( conn, db_name):
    # Get new Cursor
    cur = conn.cursor()
    try:
        cur.execute(f"CREATE TABLE IF NOT EXISTS `{db_name}`.`scan_media` ("
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
    print("create_table_scan_media done")

def create_table_skipped_media( conn, db_name):
    # Get new Cursor
    cur = conn.cursor()
    try:
        cur.execute(f"CREATE TABLE IF NOT EXISTS `{db_name}`.`skipped_media` ("
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
    print("create_table_skipped_media done")

def create_object_db( pwd, db_name):
    # Connect to MariaDB Platform
    try:
        conn = mariadb.connect(
            user="root",
            password=pwd,
            host="192.168.2.227",
            port=3306,
        )
    except mariadb.Error as e:
        print(f"Error connecting to MariaDB Connect Platform: {e}")
        sys.exit(1)

    # Get Cursor
    cur = conn.cursor()
    try:
        cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` ;")
    except mariadb.Error as e:
        print(f"Error connecting to MariaDB Platform CREATE DB: {e}")
        sys.exit(1)
    try:
        cur.execute(f"GRANT ALL PRIVILEGES ON {db_name}.* TO 'photoview'@'%' ;")
    except mariadb.Error as e:
        print(f"Error connecting to MariaDB Privileges: {e}")
        sys.exit(1)
    print("create_object_database done")
    create_table_scan_media( conn, db_name)
    create_table_skipped_media( conn, db_name)
    conn.close()

def get_next_filename(start_id, conn):
    cur = conn.cursor()
    cur.execute("SELECT id, path" # ", image_faces.id, face_groups.id, face_groups.label"
                " FROM `photoview`.`media`"
                " WHERE id > ? "
                " ORDER BY id ASC "
                " ;", (start_id,))
    row = cur.fetchone()
    while row is not None:
        # print(f"ID: {row[0]}, Path: {row[1]}, Label: {row[4]}")
        yield row[0], row[1]
        row = cur.fetchone()
    print(f"No more media file in database")
    # return None

def store_scanned_media_id( media_id, conn, db_name):
    cur = conn.cursor()
    try:
        cur.execute(f"INSERT INTO `{db_name}`.`scan_media`"
                    f" ( detection, media_id, created_at, updated_at )"
                    f" VALUES ( 1, ?, CURRENT_TIMESTAMP(3), CURRENT_TIMESTAMP(3) ) "
                    f" ON DUPLICATE KEY UPDATE media_id=?, updated_at=CURRENT_TIMESTAMP(3) "
                    f" ;", (media_id, media_id, ))
    except mariadb.Error as e:
        print(f"Error connecting to MariaDB Privileges: {e}")
        sys.exit(1)
    try:
        cur.execute(f"SELECT *"
                    f" FROM `{db_name}`.`scan_media`"
                    f" WHERE detection = 1 "
                    f" ;")
    except mariadb.Error as e:
        print(f"Error connecting to MariaDB Privileges: {e}")
        sys.exit(1)
    row = cur.fetchone()
    if row is not None:
        print(f"scan_media: {row[0]} {row[1]} {row[2]} {row[3]} {row[4]} ")
    cur.close()

def store_skipped_media_id( media_id, conn, db_name):
    cur = conn.cursor()
    try:
        cur.execute(f"INSERT INTO `{db_name}`.`skipped_media`"
                    f" ( detection, media_id, created_at, updated_at )"
                    f" VALUES ( 1, ?, CURRENT_TIMESTAMP(3), CURRENT_TIMESTAMP(3) ) "
                    f" ;", (media_id, ))
    except mariadb.Error as e:
        print(f"Error connecting to MariaDB Privileges store_skipped_media_id: {e}")
        sys.exit(1)
    try:
        cur.execute(f"SELECT *"
                    f" FROM `{db_name}`.`skipped_media`"
                    f" WHERE detection = 1 "
                    f" ;")
    except mariadb.Error as e:
        print(f"Error connecting to MariaDB Privileges store_skipped_media_id: {e}")
        sys.exit(1)
    for row in cur:
        # print(f"skipped_media: {row[0]} {row[1]} {row[2]} {row[3]} {row[4]} ")
        print(f"skipped_media: {row} ")

def store_results( media_id, height, width, result, conn, db_name):
    cur = conn.cursor()
    # print( f"id: {media_id}  Width: {width} Height: {height}")
    for roi, class_id, score in zip( result['rois'], result['class_ids'], result['scores']):
        cur.execute("SELECT id"
                    " FROM `photoview`.`face_groups`"
                    " WHERE label = ? "
                    " ;", (class_names[class_id],))
        row = cur.fetchone()
        if row is None:
            # print(f"Class: {class_names[class_id]} does not exist")
            cur.execute("INSERT INTO `photoview`.`face_groups`"
                    " ( face_groups.label, created_at, updated_at )"
                    " VALUES ( ?, CURRENT_TIMESTAMP(3), CURRENT_TIMESTAMP(3) ) "
                    " ;", (class_names[class_id],))
            cur.execute("SELECT *"
                    " FROM `photoview`.`face_groups`"
                    " WHERE label = ? "
                    " ;", (class_names[class_id],))
            row = cur.fetchone()
            if row is not None:
                print(f"Missing Face Group created: {class_names[class_id]} {row[0]} {row[1]} {row[2]} {row[3]} ")
                face_group_id = row[0]
        else:
            face_group_id = row[0]
            # print(f"Apropriate Face Group found: {face_group_id} {class_names[class_id]}")
        rect = f"{min(roi[1],roi[3])/width:8.6f}:{max(roi[1],roi[3])/width:8.6f}:{min(roi[0],roi[2])/height:8.6f}:{max(roi[0],roi[2])/height:8.6f}"
        # print(f"Rect: {rect}  {score}% {roi[0]} {roi[1]} {roi[2]} {roi[3]} w: {width} h: {height}")
        cur.execute("INSERT INTO `photoview`.`image_faces`"
                    " ( face_group_id, media_id, rectangle, confirmed, subgroup, detection, created_at, updated_at, descriptor )"
                    " VALUES ( ?, ?, ?, 0, 0, 1, CURRENT_TIMESTAMP(3), CURRENT_TIMESTAMP(3), ? ) "
                    " ;", (face_group_id, media_id, rect, [class_id for element in range(128)]))
        cur.execute("SELECT *"
                    " FROM `photoview`.`image_faces`"
                    " WHERE face_group_id = ? "
                    " ;", (face_group_id,))
        row = cur.fetchone()
        if row is not None:
            print(f"Stored: {class_names[class_id]} {row[0]} {row[1]} {row[2]} {row[3]} {row[4]} row[5] {row[6]} {row[7]} {row[8]} {row[9]} ")
    store_scanned_media_id( media_id, conn, db_name)
    conn.commit()

def get_last_media_id( skip, db_name, conn):
    last_id = -1
    detection = 1
    cur = conn.cursor()
    try:
        cur.execute(f"SELECT media_id"
                    f" FROM `{db_name}`.`scan_media`"
                    f" WHERE detection = ? "
                    f" ;", (detection,))
        row = cur.fetchone()
        if row is not None:
            print(f"get_last_media_id: {row[0]} ")
            last_id = row[0]
        else:
            print(f"get_last_media_id: now row, fall back to default ")
    except mariadb.Error as e:
        print(f"Error getting last media_id for detection {detection}: {e}")
        sys.exit(1)
    return last_id

create_object_db( "superphotosecret", "object_detector")

model = load_trrained_model(OBJECT_DETECTOR_ROOT_DIR)

try:
    conn = mariadb.connect(
        user="photoview",
        password="photosecret",
        host="192.168.2.227",
        port=3306
        # database="photoview"
    )
except mariadb.Error as e:
    print(f"Error connecting to MariaDB Platform Connection: {e}")
    sys.exit(1)

last_id = get_last_media_id(True, tools_db_name, conn)
# If not starting from scratch, skip current, because we probably crashed on current
if False and (last_id != -1):
    store_skipped_media_id( last_id, conn, tools_db_name)
    last_id, path = next(get_next_filename( last_id, conn))
    store_scanned_media_id( last_id, conn, tools_db_name)
    conn.commit()
    print(f"Skip: {last_id}, Path: {path}")
for id, path in get_next_filename( last_id, conn):
    print(f"ID: {id}, Path: {path}")
    if not os.path.isfile(path):
        print(f"Error {path} does not exist")
        sys.exit(1)
    
    #try:
        #with skimage.io.imread(path) as image:
            #print( type(image), np.dtype(image), image.shape)

    if path.endswith(".mp4"):
        print(f"Skippimg {path}")
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

    #results = model.detect([image], verbose=0)
    results = model.detect([img_oriented], verbose=0)
    # print_results( [path], results)

    store_results( id, img_oriented.shape[0], img_oriented.shape[1], results[0], conn, tools_db_name)

conn.close()

