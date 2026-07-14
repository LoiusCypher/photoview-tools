# fit a mask rcnn on the kangaroo dataset
from os import listdir
from xml.etree import ElementTree
from numpy import zeros
from numpy import asarray
# -----
import os
import sys
# Root directory of the model
OBJECT_DETECTOR_ROOT_DIR = os.path.abspath("/Mask-RCNN_model")
# Import Mask RCNN
sys.path.append(OBJECT_DETECTOR_ROOT_DIR)  # To find local version of the library
#from mrcnn import utils
#from mrcnn.utils import Dataset
# =====
from mrcnn.utils import Dataset
from mrcnn.config import Config
from mrcnn.model import MaskRCNN

from KangorooDataset import KangarooDataset

# define a configuration for the model
class KangarooConfig(Config):
	# define the name of the configuration
	NAME = "kangaroo_cfg"
	# number of classes (background + kangaroo)
	NUM_CLASSES = 1 + 1
	# number of training steps per epoch
	STEPS_PER_EPOCH = 131

# prepare train set
train_set = KangarooDataset()
train_set.load_dataset('kangaroo', is_train=True)
train_set.prepare()
print('Train: %d' % len(train_set.image_ids))
# prepare test/val set
test_set = KangarooDataset()
test_set.load_dataset('kangaroo', is_train=False)
test_set.prepare()
print('Test: %d' % len(test_set.image_ids))
# prepare config
config = KangarooConfig()
config.display()
# define the model
model = MaskRCNN(mode='training', model_dir='./', config=config)

import tensorflow.keras as keras
path_to_downloaded_file = keras.utils.get_file(
        fname="mask_rcnn_coco.h5",
        origin="https://github.com/matterport/Mask_RCNN/releases/download/v2.0/mask_rcnn_coco.h5",
        cache_dir=".",  # cache and extract in current directory
)
print(path_to_downloaded_file)
download_base_dir = os.path.dirname(path_to_downloaded_file)

# load weights (mscoco) and exclude the output layers
model.load_weights(path_to_downloaded_file, by_name=True, exclude=["mrcnn_class_logits", "mrcnn_bbox_fc",  "mrcnn_bbox", "mrcnn_mask"])
#model.load_weights('mask_rcnn_coco.h5', by_name=True, exclude=["mrcnn_class_logits", "mrcnn_bbox_fc",  "mrcnn_bbox", "mrcnn_mask"])
# train weights (output layers or 'heads')
model.train(train_set, test_set, learning_rate=config.LEARNING_RATE, epochs=5, layers='heads')

