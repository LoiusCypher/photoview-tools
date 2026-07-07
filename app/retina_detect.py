import os
import sys
import random
import math
import numpy as np
import skimage.io
import matplotlib
import matplotlib.pyplot as plt

# Root directory of the model
OBJECT_DETECTOR_ROOT_DIR = os.path.abspath("/Mask-RCNN_model")
# print(OBJECT_DETECTOR_ROOT_DIR)

# Directory of images to run detection on
IMAGE_DIR = os.path.abspath( "/photos/album1")

# Import Mask RCNN
sys.path.append(OBJECT_DETECTOR_ROOT_DIR)  # To find local version of the library
from mrcnn import utils
import mrcnn.model as modellib
from mrcnn import visualize

# Import COCO config
sys.path.append(os.path.join(OBJECT_DETECTOR_ROOT_DIR, "samples/coco/"))  # To find local version
import coco

# %matplotlib inline 

# Directory to save logs and trained model
MODEL_DIR = os.path.join(OBJECT_DETECTOR_ROOT_DIR, "logs")

# Local path to trained weights file
COCO_MODEL_PATH = os.path.join(OBJECT_DETECTOR_ROOT_DIR, "mask_rcnn_coco.h5")
# Download COCO trained weights from Releases if needed
if not os.path.exists(COCO_MODEL_PATH):
    utils.download_trained_weights(COCO_MODEL_PATH)

class InferenceConfig(coco.CocoConfig):
    # Set batch size to 1 since we'll be running inference on
    GPU_COUNT = 1
    IMAGES_PER_GPU = 1

config = InferenceConfig()
# config.display()

# Visualize results
def print_results( file_names, results):
    print( 'File(s):', file_names, 'results: ', len(results))
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

# Create model object in inference mode.
model = modellib.MaskRCNN(mode="inference", model_dir=MODEL_DIR, config=config)

# Load weights trained on MS-COCO
model.load_weights(COCO_MODEL_PATH, by_name=True)

# # Load COCO dataset
# dataset = coco.CocoDataset()
# dataset.load_coco(COCO_DIR, "train")
# dataset.prepare()
# 
# # Print class names
# print(dataset.class_names)

# COCO Class names
# Index of the class in the list is its ID. For example, to get ID of
# the teddy bear class, use: class_names.index('teddy bear')
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

# Print class names
# print(class_names)

# Load a random image from the images folder
file_names = next(os.walk(IMAGE_DIR))[2]
print(len(file_names), file_names)
selected_file_name = os.path.join(IMAGE_DIR, random.choice(file_names))
image = skimage.io.imread(selected_file_name)
# print(image.shape)

# Run detection
#results = model.detect([image], verbose=1)
results = model.detect([image], verbose=0)

print_results( [selected_file_name], results)

# visualize.display_instances(image, r['rois'], r['masks'], r['class_ids'], 
#                             class_names, r['scores'])

