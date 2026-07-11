# Module Imports
import mariadb
import os
# import skimage.io
import sys
import random
import math

from PIL import Image, ImageOps, ImageDraw
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
from mrcnn.config import Config

# Import COCO config
sys.path.append(os.path.join(OBJECT_DETECTOR_ROOT_DIR, "samples/coco/"))  # To find local version
import coco

class ShapesConfig(Config):
    """Configuration for training on the toy shapes dataset.
    Derives from the base Config class and overrides values specific
    to the toy shapes dataset.
    """
    # Give the configuration a recognizable name
    NAME = "shapes"

    # Train on 1 GPU and 8 images per GPU. We can put multiple images on each
    # GPU because the images are small. Batch size is 8 (GPUs * images/GPU).
    GPU_COUNT = 1
    IMAGES_PER_GPU = 8

    # Number of classes (including background)
    NUM_CLASSES = 1 + 3  # background + 3 shapes

    # Use small images for faster training. Set the limits of the small side
    # the large side, and that determines the image shape.
    IMAGE_MIN_DIM = 128
    IMAGE_MAX_DIM = 128

    # Use smaller anchors because our image and objects are small
    RPN_ANCHOR_SCALES = (8, 16, 32, 64, 128)  # anchor side in pixels

    # Reduce training ROIs per image because the images are small and have
    # few objects. Aim to allow ROI sampling to pick 33% positive ROIs.
    TRAIN_ROIS_PER_IMAGE = 32

    # Use a small epoch since the data is simple
    STEPS_PER_EPOCH = 100

    # use small validation steps since the epoch is small
    VALIDATION_STEPS = 5
    
def get_ax(rows=1, cols=1, size=8):
    """Return a Matplotlib Axes array to be used in
    all visualizations in the notebook. Provide a
    central point to control graph sizes.
    
    Change the default size attribute to control the size
    of rendered images
    """
    _, ax = plt.subplots(rows, cols, figsize=(size*cols, size*rows))
    return ax

class ShapesDataset(utils.Dataset):
    """Generates the shapes synthetic dataset. The dataset consists of simple
    shapes (triangles, squares, circles) placed randomly on a blank surface.
    The images are generated on the fly. No file access required.
    """

    def load_shapes(self, count, height, width):
        """Generate the requested number of synthetic images.
        count: number of images to generate.
        height, width: the size of the generated images.
        """
        # Add classes
        self.add_class("shapes", 1, "square")
        self.add_class("shapes", 2, "circle")
        self.add_class("shapes", 3, "triangle")

        # Add images
        # Generate random specifications of images (i.e. color and
        # list of shapes sizes and locations). This is more compact than
        # actual images. Images are generated on the fly in load_image().
        for i in range(count):
            bg_color, shapes = self.random_image(height, width)
            self.add_image("shapes", image_id=i, path=None,
                           width=width, height=height,
                           bg_color=bg_color, shapes=shapes)

    def load_image(self, image_id):
        """Generate an image from the specs of the given image ID.
        Typically this function loads the image from a file, but
        in this case it generates the image on the fly from the
        specs in image_info.
        """
        info = self.image_info[image_id]
        bg_color = np.array(info['bg_color']).reshape([1, 1, 3])
        image = np.ones([info['height'], info['width'], 3], dtype=np.uint8)
        #print(f"bg_color {bg_color} height {info['height']} width {info['width']}")
        image = image * bg_color.astype(np.uint8)
        for shape, color, dims in info['shapes']:
            image = self.draw_shape(image, shape, dims, color)
        return image

    def image_reference(self, image_id):
        """Return the shapes data of the image."""
        info = self.image_info[image_id]
        if info["source"] == "shapes":
            return info["shapes"]
        else:
            super(self.__class__).image_reference(self, image_id)

    def load_mask(self, image_id):
        """Generate instance masks for shapes of the given image ID.
        """
        info = self.image_info[image_id]
        shapes = info['shapes']
        count = len(shapes)
        mask = np.zeros([info['height'], info['width'], count], dtype=np.uint8)
        #print(f"mask count {count} height {info['height']} width {info['width']}")
        for i, (shape, _, dims) in enumerate(info['shapes']):
            #print(f"mask {i} mask {mask.shape} slice {mask[:, :, i].copy().shape}")
            mask[:, :, i] = self.draw_shape(mask[:, :, i].copy(),
                                                shape, dims, 1)
        # Handle occlusions
        occlusion = np.logical_not(mask[:, :, -1]).astype(np.uint8)
        for i in range(count-2, -1, -1):
            mask[:, :, i] = mask[:, :, i] * occlusion
            occlusion = np.logical_and(occlusion, np.logical_not(mask[:, :, i]))
        # Map class names to class IDs.
        class_ids = np.array([self.class_names.index(s[0]) for s in shapes])
        return mask.astype(bool), class_ids.astype(np.int32)

    def draw_shape(self, image, shape, dims, color):
        """Draws a shape from the given specs."""
        # Get the center x, y and the size s
        #+print(f"shape {shape} dims {dims}")
        x, y, s = dims
        im = Image.fromarray(image)
        d = ImageDraw.Draw(im)
        if shape == 'square':
            d.rectangle((x-s, y-s, x+s, y+s), fill=color)
            #cv2.rectangle(image, (x-s, y-s), (x+s, y+s), color, -1)
        #elif shape == "circle":
            d.ellipse([(x-s, y-s), (x+s, y+s)], fill=color)
            #cv2.circle(image, (x, y), s, color, -1)
        elif shape == "triangle":
            d.polygon([(x, y-s), (x-s/math.sin(math.radians(60)), y+s), (x+s/math.sin(math.radians(60)), y+s)], fill=color)
            #points = np.array([[[(x, y-s),
                                #(x-s/math.sin(math.radians(60)), y+s),
                                #(x+s/math.sin(math.radians(60)), y+s),
                                #](x, y-s),], dtype=np.int32)
            #cv2.fillPoly(image, points, color)
        imgae = np.array(im) # .astype(np.int16)
        return image

    def random_shape(self, height, width):
        """Generates specifications of a random shape that lies within
        the given height and width boundaries.
        Returns a tuple of three valus:
        * The shape name (square, circle, ...)
        * Shape color: a tuple of 3 values, RGB.
        * Shape dimensions: A tuple of values that define the shape size
                            and location. Differs per shape type.
        """
        # Shape
        shape = random.choice(["square", "circle", "triangle"])
        # Color
        color = tuple([random.randint(0, 255) for _ in range(3)])
        # Center x, y
        buffer = 20
        y = random.randint(buffer, height - buffer - 1)
        x = random.randint(buffer, width - buffer - 1)
        # Size
        s = random.randint(buffer, height//4)
        return shape, color, (x, y, s)

    def random_image(self, height, width):
        """Creates random specifications of an image with multiple shapes.
        Returns the background color of the image and a list of shape
        specifications that can be used to draw the image.
        """
        # Pick random background color
        bg_color = np.array([random.randint(0, 255) for _ in range(3)])
        # Generate a few random shapes and record their
        # bounding boxes
        shapes = []
        boxes = []
        N = random.randint(1, 4)
        for _ in range(N):
            shape, color, dims = self.random_shape(height, width)
            shapes.append((shape, color, dims))
            x, y, s = dims
            boxes.append([y-s, x-s, y+s, x+s])
        # Apply non-max suppression wit 0.3 threshold to avoid
        # shapes covering each other
        keep_ixs = utils.non_max_suppression(np.array(boxes), np.arange(N), 0.3)
        shapes = [s for i, s in enumerate(shapes) if i in keep_ixs]
        return bg_color, shapes

# ------------------------------

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

def load_model(object_detector_root_dir, trained, ibit_with, config):
    # Directory to save logs and trained model
    MODEL_DIR = os.path.join(object_detector_root_dir, "logs")

    if not trained:
        model = modellib.MaskRCNN(mode="training", config=config, model_dir=MODEL_DIR)

        if init_with == "imagenet":
            model.load_weights(model.get_imagenet_weights(), by_name=True)
        elif init_with == "coco":
            # Local path to trained weights file
            COCO_MODEL_PATH = os.path.join(OBJECT_DETECTOR_ROOT_DIR, "mask_rcnn_coco.h5")
            # Download COCO trained weights from Releases if needed
            if not os.path.exists(COCO_MODEL_PATH):
                utils.download_trained_weights(COCO_MODEL_PATH)
            # Load weights trained on MS COCO, but skip layers that
            # are different due to the different number of classes
            # See README for instructions to download the COCO weights
            model.load_weights(COCO_MODEL_PATH, by_name=True,
                               exclude=["mrcnn_class_logits", "mrcnn_bbox_fc", 
                                "mrcnn_bbox", "mrcnn_mask"])
        elif init_with == "last":
            # Load the last model you trained and continue training
            model.load_weights(model.find_last(), by_name=True)
        return model

    # Create model object in inference mode.
    model = modellib.MaskRCNN(mode="inference", config=config, model_dir=MODEL_DIR)

    # Local path to trained weights file
    coco_model_path = os.path.join(object_detector_root_dir, "mask_rcnn_coco.h5")
    # Download COCO trained weights from Releases if needed
    if not os.path.exists(coco_model_path):
        utils.download_trained_weights(coco_model_path)

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

# ------------------------------

shape_config = ShapesConfig()
shape_config.display()


# Training dataset
dataset_train = ShapesDataset()
dataset_train.load_shapes(500, shape_config.IMAGE_SHAPE[0], shape_config.IMAGE_SHAPE[1])
dataset_train.prepare()

# Validation dataset
dataset_val = ShapesDataset()
dataset_val.load_shapes(50, shape_config.IMAGE_SHAPE[0], shape_config.IMAGE_SHAPE[1])
dataset_val.prepare()


# Load and display random samples
image_ids = np.random.choice(dataset_train.image_ids, 4)
for image_id in image_ids:
    image = dataset_train.load_image(image_id)
    mask, class_ids = dataset_train.load_mask(image_id)
    #visualize.display_top_masks(image, mask, class_ids, dataset_train.class_names)

# Which weights to start with?
init_with = "coco"  # imagenet, coco, or last

# Create model in training mode
model = load_model(OBJECT_DETECTOR_ROOT_DIR, False, init_with, shape_config)

# Train the head branches
# Passing layers="heads" freezes all layers except the head
# layers. You can also pass a regular expression to select
# which layers to train by name pattern.
model.train(dataset_train, dataset_val, 
            learning_rate=shape_config.LEARNING_RATE, 
            epochs=1, 
            layers='heads')

# Fine tune all layers
# Passing layers="all" trains all layers. You can also 
# pass a regular expression to select which layers to
# train by name pattern.
model.train(dataset_train, dataset_val, 
            learning_rate=shape_config.LEARNING_RATE / 10,
            epochs=2, 
            layers="all")

# Save weights
# Typically not needed because callbacks save after every epoch
# Uncomment to save manually
# model_path = os.path.join(MODEL_DIR, "mask_rcnn_shapes.h5")
# model.keras_model.save_weights(model_path)


sys.exit(1)

# ------------------------------

create_object_db( "superphotosecret", "object_detector")

inference_config = InferenceConfig()
# inference_config.display()

model = load_model(OBJECT_DETECTOR_ROOT_DIR, True, "coco", inference_config)

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

