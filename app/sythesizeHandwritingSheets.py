# Module Imports
import os
import sys
import random
import math
import pathlib

from PIL import Image, ImageOps, ImageDraw
import numpy as np

#import tensorflow as tf

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

def get_ax(rows=1, cols=1, size=8):
    """Return a Matplotlib Axes array to be used in
    all visualizations in the notebook. Provide a
    central point to control graph sizes.
    
    Change the default size attribute to control the size
    of rendered images
    """
    _, ax = plt.subplots(rows, cols, figsize=(size*cols, size*rows))
    return ax

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

import json

def crop_patterns( orig_dir, gen_dir, sub_dir, file, class_files ):
    print( orig_dir, gen_dir, sub_dir, file)
    with open( os.path.join( os.path.join( orig_dir, sub_dir), file)) as f:
        d = json.load(f)
        #print(d)
        #print(d.keys())
        print(f"version     {d['version']} ")
        print(f"imagePath   {d['imagePath']} ")
        print(f"imageHeight {d['imageHeight']} ")
        print(f"imageWidth  {d['imageWidth']} ")
        print(f"imageData   {d['imageData']} ")
        # Open the image
        print( orig_dir, sub_dir, file, d['imagePath'])
        img = ImageOps.exif_transpose( Image.open( os.path.join( os.path.join( orig_dir, sub_dir), d['imagePath'])))
        print(f"shapes {len(d['shapes'])} ")
        for idx, shapes in enumerate( d['shapes']):
            #print(shapes.keys())
            print(f"  label      {shapes['label']}")
            print(f"  group_id   {shapes['group_id']}")
            print(f"  shape_type {shapes['shape_type']}  {len(shapes['points'])} points")
            if shapes['shape_type'] == 'rectangle':
                xMin = round( min( shapes['points'][0][0], shapes['points'][1][0]))
                xMax = round( max( shapes['points'][0][0], shapes['points'][1][0]))
                yMin = round( min( shapes['points'][0][1], shapes['points'][1][1]))
                yMax = round( max( shapes['points'][0][1], shapes['points'][1][1]))
                print(f"    {xMin} {yMin} {xMax} {yMax}")
                img_area = img.crop((xMin, yMin, xMax, yMax))
                sample_file = os.path.join( os.path.join( os.path.join( gen_dir, shapes['label']), sub_dir), f"{idx:04d}-{d['imagePath']}")
                print(f'    {sample_file}')
                if not os.path.isdir( os.path.dirname( sample_file)):
                    os.makedirs( os.path.dirname( sample_file))
                img_area.save( sample_file)
                if shapes['label'] not in class_files:
                    class_files[shapes['label']] = ()
                class_files[shapes['label']] = class_files[shapes['label']] + (sample_file, )
                #print( 'class_files', class_files[shapes['label']])
                #print( 'class_files', class_files)
    return class_files

class HandwritingConfig(Config):
    """Configuration for training on the toy shapes dataset.
    Derives from the base Config class and overrides values specific
    to the toy shapes dataset.
    """
    # Give the configuration a recognizable name
    NAME = "handwritten"

    # Train on 1 GPU and 8 images per GPU. We can put multiple images on each
    # GPU because the images are small. Batch size is 8 (GPUs * images/GPU).
    GPU_COUNT = 1
    IMAGES_PER_GPU = 1

    # Number of classes (including background)
    NUM_CLASSES = 1 + 4  # background + 4 shapes

    # Use small images for faster training. Set the limits of the small side
    # the large side, and that determines the image shape.
    #IMAGE_MAX_DIM = 1280
    IMAGE_MAX_DIM = 1024
    IMAGE_MIN_DIM = 128

    # Use smaller anchors because our image and objects are small
    #RPN_ANCHOR_SCALES = (8, 16, 32, 64, 128, 256)  # anchor side in pixels
    RPN_ANCHOR_SCALES = (8, 16, 32, 64, 128)  # anchor side in pixels

    # Reduce training ROIs per image because the images are small and have
    # few objects. Aim to allow ROI sampling to pick 33% positive ROIs.
    TRAIN_ROIS_PER_IMAGE = 32

    # Use a small epoch since the data is simple
    STEPS_PER_EPOCH = 2

    # use small validation steps since the epoch is small
    VALIDATION_STEPS = 1
    
class HandwritingDataset(utils.Dataset):
    """Generates the shapes synthetic dataset. The dataset consists of simple
    shapes (triangles, squares, circles) placed randomly on a blank surface.
    The images are generated on the fly. No file access required.
    """

    def __init__(self, backgrounds, image_min, image_max, class_samples, class_map=None):
        self._image_min = image_min
        self._image_max = image_max
        print(f'image max {self._image_max} min {self._image_min}')
        self._backgrounds = backgrounds
        self.background_height = 0
        self.background_width = 0
        for bg_img in self._backgrounds:
            width, height = Image.open( bg_img).size
            self.background_height = max( height, self.background_height)
            self.background_width = max( width, self.background_width)
        print(f'background max:height {self.background_height} max:width {self.background_width}')
        self.pattern_height = max(max(c, key=lambda x:x['img_height'])['img_height'] for c in class_samples.values())
        self.pattern_width = max(max(c, key=lambda x:x['img_width'])['img_width'] for c in class_samples.values())
        print(f'pattern max_height {self.pattern_height} max_width {self.pattern_width}')
        #assert(self._image_min > self.pattern_height)
        #assert(self._image_max > self.pattern_width)
        print(f'classes {len(class_samples)}')
        super(HandwritingDataset, self).__init__(class_map=class_map)

    def load_shapes(self, count, class_samples, max_samples):
        """Generate the requested number of synthetic images.
        count: number of images to generate.
        height, width: the size of the generated images.
        """
        # Add classes
        for i, class_name in enumerate( class_samples.keys()):
            self.add_class("handwritten", i+1, class_name)
        #print(f'classes ')
        # Add images
        # Generate random specifications of images (i.e. color and
        # list of shapes sizes and locations). This is more compact than
        # actual images. Images are generated on the fly in load_image().
        for i in range(count):
            bg_path, bg_box, shapes = self.random_image( class_samples, max_samples)
            self.add_image("handwritten", image_id=i, path=None, bg_path=bg_path, bg_box=bg_box, shapes=shapes)

    def random_image(self, class_samples, max_samples):
        """Creates random specifications of an image with multiple shapes.
        Returns the background color of the image and a list of shape
        specifications that can be used to draw the image.
        """

        def random_shape(height, width, class_samples):
            """Generates specifications of a random shape that lies within
            the given height and width boundaries.
            Returns a tuple of three valus:
            * The shape name (square, circle, ...)
            * Shape dimensions: A tuple of values that define the shape size
                                and location. Differs per shape type.
            """
            # Class
            #print( class_samples.keys())
            class_sel = random.choice( list( class_samples.keys()))
            #print(class_sel)
            shape_sel = random.choice( class_samples[class_sel])
            # Region
            shape_width = shape_sel['img_width']
            shape_height = shape_sel['img_height']
            y = random.randint(0, max( 0, height - shape_height - 1))
            x = random.randint(0, max( 0, width - shape_width - 1))
            return class_sel, shape_sel['img_path'], (x, y, x + shape_width - 1, y + shape_height - 1)

        # Pick random background image
        bg_path = random.choice(self._backgrounds)
        width, height = Image.open( bg_path).size
        bg_width = min( width, self._image_max )
        bg_height = min( height, self._image_min )
        # Generate a few random shapes and record their
        bg_left = random.randint( 0, width - bg_width)
        bg_top = random.randint( 0, height - bg_height)
        # bounding boxes
        shapes = []
        boxes = []
        N = random.randint(1, max_samples)
        #print('shape count', N)
        for _ in range(N):
            class_sel, shape_path, dims = random_shape( bg_height, bg_width, class_samples,)
            #print( dims)
            shapes.append((class_sel, shape_path, dims))
            xs, ys, xe, ye = dims
            boxes.append([ys, xs, ye, xe])
        # Apply non-max suppression wit 0.3 threshold to avoid
        # shapes covering each other
        #print(f"boxes {np.array(boxes)} {boxes}")
        keep_ixs = utils.non_max_suppression(np.array(boxes), np.arange(N), 0.3)
        shapes = [s for i, s in enumerate(shapes) if i in keep_ixs]
        return bg_path, (bg_left, bg_top, bg_left+bg_width, bg_top+bg_height), shapes

    def load_image(self, image_id):
        """Generate an image from the specs of the given image ID.
        Typically this function loads the image from a file, but
        in this case it generates the image on the fly from the
        specs in image_info.
        """
        info = self.image_info[image_id]
        # print(f"Info {info.keys()} {info}")
        img = Image.open( info['bg_path']).crop( info['bg_box'])
        # print(f"image {info['bg_path']} {img.size} {info['bg_box']}")
        for cl_name, shape, dims in info['shapes']:
            img = self.draw_shape(img, shape, dims)
        image = np.array(img)
        img.save(f'/handwriting/generated/images/img-{image_id}.jpg')
        return image


    def load_mask(self, image_id):
        """Generate instance masks for shapes of the given image ID.
        """
        info = self.image_info[image_id]
        #print(f"Info {info.keys()} {info}")
        shapes = info['shapes']
        count = len(shapes)
        (bg_l, bg_t, bg_r, bg_b) = info['bg_box']
        mask = np.zeros( [bg_b-bg_t, bg_r-bg_l, count], dtype=np.uint8)
        for i, (cl_name, shape, dims) in enumerate(shapes):
            #print(f"mask {i} mask {mask.shape} slice {mask[:, :, i].copy().shape}")
            mask[:, :, i] = self.draw_mask(mask[:, :, i].copy(), shape, dims, 1)
            Image.fromarray(mask[:, :, i]*255).save(f'/handwriting/generated/images/mask-{i+1:04d}.jpg')
        # Handle occlusions
        occlusion = np.logical_not(mask[:, :, -1]).astype(np.uint8)
        #print(f"mask count {count} height {bg_b-bg_t} width {bg_r-bg_l} mask {mask.shape} occ {occlusion.shape}")
        #Image.fromarray((occlusion*255).astype(np.uint8)).save(f'/handwriting/generated/images/mask-o.jpg')
        for i in range(count-2, -1, -1):
            #print(f"mask {i} ")
            mask[:, :, i] = mask[:, :, i] * occlusion
            occlusion = np.logical_and(occlusion, np.logical_not(mask[:, :, i]))
            #print(f"mask count {count} occ {occlusion.shape}")
            #Image.fromarray((occlusion*255).astype(np.uint8)).save(f'mask-o.jpg')
        #Image.fromarray((occlusion*255).astype(np.uint8)).save(f'/handwriting/generated/images/mask-o.jpg')
        # Map class names to class IDs.
        class_ids = np.array([self.class_names.index(s[0]) for s in shapes])
        return mask.astype(bool), class_ids.astype(np.int32)


    def draw_mask(self, image, shape, dims, color):
        """Draws a shape from the given specs."""
        # Get the center x, y and the size s
        #print(f"shape {shape} dims {dims}")
        im = Image.fromarray(image)
        d = ImageDraw.Draw(im)
        xs, ys, xe, ye = dims
        d.rectangle((xs, ys, xe, ye), fill=color)
        image = np.array(im) # .astype(np.int16)
        return image

    def draw_shape(self, im, shape, dims):
        """Draws a shape from the given specs."""
        #print(f"shape {shape} dims {dims}")
        xs, ys, xe, ye = dims
        ix = Image.open(shape)
        im.paste(ix, (xs, ys))
        return im


# ------------------------------
def read_class_samples( gen_dir):
    class_samples = {}
    max_width = 0
    max_height = 0
    # Travers all the branch of a specified path
    for (cur_dir, dirs, _) in os.walk( gen_dir, topdown=True):
        if cur_dir == gen_dir:
            for class_dir in dirs:
                class_samples[class_dir] = ()
                for (cur_sample_dir, _, files) in os.walk( os.path.join( gen_dir, class_dir), topdown=True):
                    for file in files:
                        #print(cur_sample_dir, class_dir, file)
                        img_path = os.path.join( cur_sample_dir, file)
                        width, height = ImageOps.exif_transpose( Image.open( img_path)).size
                        class_samples[class_dir] = class_samples[class_dir] + ({"img_path" : img_path, "img_height" : height, "img_width" : width}, )
    return class_samples, max_width, max_height

backgrounds = ( '/handwriting/orig/LAV/LAV_NRW--Abt_Rheinland--PA_3103--29568/LAV_NRW_R_PA_3103_29568_0004.jpg',
                '/handwriting/orig/LAV/LAV_NRW--Abt_Rheinland--PA_3103--29568/LAV_NRW_R_PA_3103_29568_0005.jpg',
                )

class_samples, max_width, max_height = read_class_samples( '/handwriting/generated/classes')
#print(f'class_samples {class_samples}')

hand_config = HandwritingConfig()
#hand_config.display()

# Training dataset
dataset_train = HandwritingDataset( backgrounds, hand_config.IMAGE_MIN_DIM, hand_config.IMAGE_MAX_DIM, class_samples)
dataset_train.load_shapes(10, class_samples, 10)
dataset_train.prepare()

# Validation dataset
dataset_val = HandwritingDataset( backgrounds, hand_config.IMAGE_MIN_DIM, hand_config.IMAGE_MAX_DIM, class_samples)
dataset_val.load_shapes(5, class_samples, 10)
dataset_val.prepare()

# Load and display random samples
image_ids = np.random.choice(dataset_train.image_ids, 9)
for image_id in image_ids:
    image = dataset_train.load_image(image_id)
    mask, class_ids = dataset_train.load_mask(image_id)
    #visualize.display_top_masks(image, mask, class_ids, dataset_train.class_names)

# Which weights to start with?
init_with = "coco"  # imagenet, coco, or last

# Create model in training mode
model = load_model(OBJECT_DETECTOR_ROOT_DIR, False, init_with, hand_config)

print('begin training')
#tf.keras.backend.clear_session()

# Train the head branches
# Passing layers="heads" freezes all layers except the head
# layers. You can also pass a regular expression to select
# which layers to train by name pattern.
model.train(dataset_train, dataset_val, 
            learning_rate=hand_config.LEARNING_RATE, 
            epochs=1, 
            layers='heads')

print('head done')
#tf.keras.backend.clear_session()

# Fine tune all layers
# Passing layers="all" trains all layers. You can also 
# pass a regular expression to select which layers to
# train by name pattern.
model.train(dataset_train, dataset_val, 
            learning_rate=hand_config.LEARNING_RATE / 10,
            epochs=2, 
            layers="all")

print('training done')

# Save weights
# Typically not needed because callbacks save after every epoch
# Uncomment to save manually
model_path = os.path.join('/handwriting/generated/weights/', "mask_rcnn_shapes.h5")
model.keras_model.save_weights(model_path)


sys.exit(1)

