"""
Title: Object detection with Vision Transformers
Author: [Karan V. Dave](https://www.linkedin.com/in/karan-dave-811413164/)
Date created: 2022/03/27
Last modified: 2023/11/20
Description: A simple Keras implementation of object detection using Vision Transformers.
Accelerator: GPU
"""

"""
## Introduction

The article
[Vision Transformer (ViT)](https://arxiv.org/abs/2010.11929)
architecture by Alexey Dosovitskiy et al.
demonstrates that a pure transformer applied directly to sequences of image
patches can perform well on object detection tasks.

In this Keras example, we implement an object detection ViT
and we train it on the
[Caltech 101 dataset](http://www.vision.caltech.edu/datasets/)
to detect an airplane in the given image.
"""

"""
## Imports and setup
"""

import os

#os.environ["KERAS_BACKEND"] = "jax"  # @param ["tensorflow", "jax", "torch"]
os.environ["KERAS_BACKEND"] = "torch"  # @param ["tensorflow", "jax", "torch"]


#import numpy as np
#import tensorflow as tf
#import tensorflow.keras as keras
#from tensorflow.keras import layers
import keras
from keras import layers
from keras import ops
#from tensorflow.keras import ops
#from keras import ops
#from tensorflow.keras.backend.python import ops
import tensorflow.keras.ops
import matplotlib.pyplot as plt
import numpy as np
import cv2
import os
import scipy.io
import shutil

"""
## Prepare dataset

We use the [Caltech 101 Dataset](https://data.caltech.edu/records/mzrjq-6wc02).
"""


"""
## Implement the patch creation layer
"""

import numpy as np


"""
## Implement the patch encoding layer

The `PatchEncoder` layer linearly transforms a patch by projecting it into a
vector of size `projection_dim`. It also adds a learnable position
embedding to the projected vector.
"""

class PatchEncoder(layers.Layer):
    def __init__(self, num_patches, projection_dim):
        super().__init__()
        self.num_patches = num_patches
        self.projection = layers.Dense(units=projection_dim)
        self.position_embedding = layers.Embedding(
            input_dim=num_patches, output_dim=projection_dim
        )

    def call(self, patch):
        positions = ops.expand_dims(
            ops.arange(start=0, stop=self.num_patches, step=1), axis=0
        )
        projected_patches = self.projection(patch)
        encoded = projected_patches + self.position_embedding(positions)
        return encoded

    # Override function to avoid error while saving model
    def get_config(self):
        config = super().get_config().copy()
        config.update(
            {
                "input_shape": input_shape,
                "patch_size": patch_size,
                "num_patches": num_patches,
                "projection_dim": projection_dim,
                "num_heads": num_heads,
                "transformer_units": transformer_units,
                "transformer_layers": transformer_layers,
                "mlp_head_units": mlp_head_units,
            }
        )
        return config

class Patches(layers.Layer):
    def __init__(self, patch_size):
        super().__init__()
        self.patch_size = patch_size

    def call(self, images):
        #input_shape = ops.shape(images)
        input_shape = np.shape(images)
        batch_size = input_shape[0]
        height = input_shape[1]
        width = input_shape[2]
        channels = input_shape[3]
        num_patches_h = height // self.patch_size
        num_patches_w = width // self.patch_size
        patches = keras.ops.image.extract_patches(images, size=self.patch_size)
        #patches = ops.reshape(
        patches = np.reshape(
            patches,
            (
                batch_size,
                num_patches_h * num_patches_w,
                self.patch_size * self.patch_size * channels,
            ),
        )
        return patches

    def get_config(self):
        config = super().get_config()
        config.update({"patch_size": self.patch_size})
        return config

"""
## Implement multilayer-perceptron (MLP)

We use the code from the Keras example
[Image classification with Vision Transformer](https://keras.io/examples/vision/image_classification_with_vision_transformer/)
as a reference.
"""

def mlp(x, hidden_units, dropout_rate):
    for units in hidden_units:
        x = layers.Dense(units, activation=keras.activations.gelu)(x)
        x = layers.Dropout(dropout_rate)(x)
    return x

"""
## Build the ViT model

The ViT model has multiple Transformer blocks.
The `MultiHeadAttention` layer is used for self-attention,
applied to the sequence of image patches. The encoded patches (skip connection)
and self-attention layer outputs are normalized and fed into a
multilayer perceptron (MLP).
The model outputs four dimensions representing
the bounding box coordinates of an object.
"""

def create_vit_object_detector(
    input_shape,
    patch_size,
    num_patches,
    projection_dim,
    num_heads,
    transformer_units,
    transformer_layers,
    mlp_head_units,
):
    inputs = keras.Input(shape=input_shape)
    # Create patches
    patches = Patches(patch_size)(inputs)
    # Encode patches
    encoded_patches = PatchEncoder(num_patches, projection_dim)(patches)

    # Create multiple layers of the Transformer block.
    for _ in range(transformer_layers):
        # Layer normalization 1.
        x1 = layers.LayerNormalization(epsilon=1e-6)(encoded_patches)
        # Create a multi-head attention layer.
        attention_output = layers.MultiHeadAttention(
            num_heads=num_heads, key_dim=projection_dim, dropout=0.1
        )(x1, x1)
        # Skip connection 1.
        x2 = layers.Add()([attention_output, encoded_patches])
        # Layer normalization 2.
        x3 = layers.LayerNormalization(epsilon=1e-6)(x2)
        # MLP
        x3 = mlp(x3, hidden_units=transformer_units, dropout_rate=0.1)
        # Skip connection 2.
        #print(f'x3 {x3.shape} {x3} x2 {x2.shape} {x2}')
        encoded_patches = layers.Add()([x3, x2])

    # Create a [batch_size, projection_dim] tensor.
    representation = layers.LayerNormalization(epsilon=1e-6)(encoded_patches)
    representation = layers.Flatten()(representation)
    representation = layers.Dropout(0.3)(representation)
    # Add MLP.
    features = mlp(representation, hidden_units=mlp_head_units, dropout_rate=0.3)

    bounding_box = layers.Dense(4)(
        features
    )  # Final four neurons that output bounding box

    # return Keras model.
    return keras.Model(inputs=inputs, outputs=bounding_box)

"""
## Run the experiment
"""
import sys
# Root directory of the model
OBJECT_DETECTOR_ROOT_DIR = os.path.abspath("/Mask-RCNN_model")
# Import Mask RCNN
sys.path.append(OBJECT_DETECTOR_ROOT_DIR)  # To find local version of the library
from mrcnn import utils
#from mrcnn.utils import Dataset

def run_experiment(model, learning_rate, weight_decay, batch_size, num_epochs):
    optimizer = keras.optimizers.AdamW(
        learning_rate=learning_rate, weight_decay=weight_decay
    )

    # Compile model.
    model.compile(optimizer=optimizer, loss=keras.losses.MeanSquaredError())
    print(f"Model compiled")

    checkpoint_filepath = "vit_object_detector.weights.h5"
    checkpoint_callback = keras.callbacks.ModelCheckpoint(
        checkpoint_filepath,
        monitor="val_loss",
        save_best_only=True,
        save_weights_only=True,
    )
    print(f"Callbacks set")

    #print(f"batch {batch_size} {len(x_train)} ")
    #################################################################
    # Decomposed model fit

    epochs = num_epochs  # In practice you need at least 20 epochs to generate nice digits.
    save_dir = "vit_object_detector.weights.h5"

    run_own_loop = False
    if run_own_loop:
        for epoch in range(epochs):
            print("\nStart epoch", epoch)

            #for step, real_images in enumerate(dataset):
            for step, real_images, classed_masks in airplane_set.get_batches(batch_size):
                # Train the discriminator & generator on one batch of real images.
                d_loss, g_loss, boxes = model.train_step(real_images)
                print(f'training output')

                # Logging.
                #if step % 200 == 0:
                if step % 5 == 0:
                    # Print metrics
                    print("discriminator loss at step %d: %.2f" % (step, d_loss))
                    print("adversarial loss at step %d: %.2f" % (step, g_loss))

                    # Save one generated image
                    img = keras.utils.array_to_img(generated_images[0] * 255.0, scale=False)
                    img.save(os.path.join(save_dir, "generated_img" + str(step) + ".png"))

                # To limit execution time we stop after 10 steps.
                # Remove the lines below to actually train the model!
                if step > 10:
                    break

    else:
        # Regular model fit
        print(f"-model fit starting")
        step, x_train, y_train = next(airplane_set.get_batches(batch_size))
        print(f"Next {step} {x_train.shape} {y_train}")
        history = model.fit(
            x=x_train,
            y=y_train,
            batch_size=batch_size,
            epochs=num_epochs,
            validation_split=0.1,
            callbacks=[
                checkpoint_callback,
                keras.callbacks.EarlyStopping(monitor="val_loss", patience=10),
            ],
            verbose=2,
        )
        print(f"-model fit done")

        return history


patch_size = 32  # Size of the patches to be extracted from the input images

image_size = 112  # resize input images to this size


# Path to images and annotations
path_images = "./101_ObjectCategories/airplanes/"
path_annot = "./Annotations/Airplanes_Side_2/"

import pathlib

if False:
    path_to_downloaded_file = keras.utils.get_file(
        fname="101_ObjectCategories_archive",
        #fname="101_ObjectCategories",
        origin="https://data.caltech.edu/records/mzrjq-6wc02/files/caltech-101.zip",
        #origin="http://www.vision.caltech.edu/Image_Datasets/Caltech101/101_ObjectCategories.tar.gz",
        #untar=True,
        extract=True,
        archive_format="zip",  # downloaded file format
        cache_dir="./cache-2",  # cache and extract in current directory
    )
    print(path_to_downloaded_file)
    download_base_dir = os.path.dirname(path_to_downloaded_file)
    print(download_base_dir)

    print(path_to_downloaded_file)
    data_dir = pathlib.Path(path_to_downloaded_file)
    print(data_dir)
    batch_size = 32
    img_height = image_size
    img_width = image_size

    path_to_downloaded_file = keras.utils.get_file(
        fname="caltech_101_zipped",
        origin="https://data.caltech.edu/records/mzrjq-6wc02/files/caltech-101.zip",
        extract=True,
        archive_format="zip",  # downloaded file format
        cache_dir=".",  # cache and extract in current directory
    )
    download_base_dir = os.path.dirname(path_to_downloaded_file)

    # Extracting tar files found inside main zip file
    shutil.unpack_archive(
        os.path.join(download_base_dir, "caltech_101_zipped/caltech-101", "101_ObjectCategories.tar.gz"), "."
    )

    data_dir = pathlib.Path("./101_ObjectCategories/").with_suffix('')
    print('data_dir', data_dir)

    import glob
    jpgs = glob.glob(f'data_dir/*/*.jpg')
    shutil.unpack_archive(
        os.path.join(download_base_dir, "caltech_101_zipped/caltech-101", "Annotations.tar"), "."
    )
    pngs = [f.split('.jpg')[0] + "_segmentation" + ".png" for f in jpgs]

    #airplane_set = keras.utils.image_dataset_from_tensor_slices((,))
    airplane_set = keras.utils.image_dataset_from_directory(
        data_dir,
        validation_split=0.2,
        subset="training",
        seed=123,
        image_size=(img_height, img_width),
        batch_size=batch_size
    )
    #airplane_set.prepare()
    #for elem in airplane_set:
    #    print( elem)
    #    break
elif False:
    path_to_downloaded_file = keras.utils.get_file(
        fname="caltech_101_zipped",
        origin="https://data.caltech.edu/records/mzrjq-6wc02/files/caltech-101.zip",
        extract=True,
        archive_format="zip",  # downloaded file format
        cache_dir=".",  # cache and extract in current directory
    )
    download_base_dir = os.path.dirname(path_to_downloaded_file)

    # Extracting tar files found inside main zip file
    shutil.unpack_archive(
        os.path.join(download_base_dir, "caltech_101_zipped/caltech-101", "101_ObjectCategories.tar.gz"), "."
    )
    shutil.unpack_archive(
        os.path.join(download_base_dir, "caltech_101_zipped/caltech-101", "Annotations.tar"), "."
    )

    airplane_set = AirplaneDataset()
    airplane_set.load_dataset( path_images, path_annot, image_size, 5)
    airplane_set.prepare()

    # train set
#print('Train: %d' % len(airplane_set.image_ids))

## Convert the list to numpy array, split to train and test dataset
#(x_train), (y_train) = (
    #np.asarray(images[: int(len(images) * 0.8)]),
    #np.asarray(targets[: int(len(targets) * 0.8)]),
#)
#(x_test), (y_test) = (
    #np.asarray(images[int(len(images) * 0.8) :]),
    #np.asarray(targets[int(len(targets) * 0.8) :]),
#)
#print(f"Train / Test split done")


"""
## Display patches for an input image
"""
def display_image_patch(image):
    plt.figure(figsize=(4, 4))
    #plt.imshow(x_train[0].astype("uint8"))
    plt.imshow(image.astype("uint8"))
    plt.axis("off")
    #print(f"Plot 1 done")

    patches = Patches(patch_size)(np.expand_dims( image, axis=0))
    print(f"Image size: {image_size} X {image_size}")
    print(f"Patch size: {patch_size} X {patch_size}")
    print(f"{patches.shape[1]} patches per image \n{patches.shape[-1]} elements per patch")


    n = int(np.sqrt(patches.shape[1]))
    plt.figure(figsize=(4, 4))
    for i, patch in enumerate(patches[0]):
        ax = plt.subplot(n, n, i + 1)
        patch_img = ops.reshape(patch, (patch_size, patch_size, 3))
        plt.imshow(ops.convert_to_numpy(patch_img).astype("uint8"))
        plt.axis("off")
    #print(f"Plot 2 done")

#display_image_patch( airplane_set.load_image( airplane_set.image_ids[0]))

input_shape = (image_size, image_size, 3)  # input image shape
learning_rate = 0.001
weight_decay = 0.0001
#batch_size = 32
batch_size = 3
num_epochs = 100
num_patches = (image_size // patch_size) ** 2
projection_dim = 64
num_heads = 4
# Size of the transformer layers
transformer_units = [
    projection_dim * 2,
    projection_dim,
]
transformer_layers = 4
mlp_head_units = [2048, 1024, 512, 64, 32]  # Size of the dense layers
##print(f"Config done")

################

history = []

vit_object_detector = create_vit_object_detector(
    input_shape,
    patch_size,
    num_patches,
    projection_dim,
    num_heads,
    transformer_units,
    transformer_layers,
    mlp_head_units,
)
print(f"Detector creation done")

# Import Mask RCNN
from mrcnn.config import Config

# define a configuration for the model
class KangarooConfig(Config):
	# define the name of the configuration
	NAME = "kangaroo_cfg"
	# number of classes (background + kangaroo)
	NUM_CLASSES = 1 + 1
	# number of training steps per epoch
	STEPS_PER_EPOCH = 131
 
from KangarooDataset  import KangarooDataset 

# Import Mask RCNN
sys.path.append(OBJECT_DETECTOR_ROOT_DIR)  # To find local version of the library
import mrcnn.model as modellib

import math
import logging

def data_generator(dataset, config, shuffle=True, augment=False, augmentation=None,
                   random_rois=0, batch_size=1, detection_targets=False,
                   no_augmentation_sources=None):
    """A generator that returns images and corresponding target class ids,
    bounding box deltas, and masks.

    dataset: The Dataset object to pick data from
    config: The model config object
    shuffle: If True, shuffles the samples before every epoch
    augment: (deprecated. Use augmentation instead). If true, apply random
        image augmentation. Currently, only horizontal flipping is offered.
    augmentation: Optional. An imgaug (https://github.com/aleju/imgaug) augmentation.
        For example, passing imgaug.augmenters.Fliplr(0.5) flips images
        right/left 50% of the time.
    random_rois: If > 0 then generate proposals to be used to train the
                 network classifier and mask heads. Useful if training
                 the Mask RCNN part without the RPN.
    batch_size: How many images to return in each call
    detection_targets: If True, generate detection targets (class IDs, bbox
        deltas, and masks). Typically for debugging or visualizations because
        in trainig detection targets are generated by DetectionTargetLayer.
    no_augmentation_sources: Optional. List of sources to exclude for
        augmentation. A source is string that identifies a dataset and is
        defined in the Dataset class.

    Returns a Python generator. Upon calling next() on it, the
    generator returns two lists, inputs and outputs. The contents
    of the lists differs depending on the received arguments:
    inputs list:
    - images: [batch, H, W, C]
    - image_meta: [batch, (meta data)] Image details. See compose_image_meta()
    - rpn_match: [batch, N] Integer (1=positive anchor, -1=negative, 0=neutral)
    - rpn_bbox: [batch, N, (dy, dx, log(dh), log(dw))] Anchor bbox deltas.
    - gt_class_ids: [batch, MAX_GT_INSTANCES] Integer class IDs
    - gt_boxes: [batch, MAX_GT_INSTANCES, (y1, x1, y2, x2)]
    - gt_masks: [batch, height, width, MAX_GT_INSTANCES]. The height and width
                are those of the image unless use_mini_mask is True, in which
                case they are defined in MINI_MASK_SHAPE.

    outputs list: Usually empty in regular training. But if detection_targets
        is True then the outputs list contains target class_ids, bbox deltas,
        and masks.
    """

    def compute_backbone_shapes(config, image_shape):
        """Computes the width and height of each stage of the backbone network.

        Returns:
            [N, (height, width)]. Where N is the number of stages
        """
        if callable(config.BACKBONE):
            return config.COMPUTE_BACKBONE_SHAPE(image_shape)

        # Currently supports ResNet only
        assert config.BACKBONE in ["resnet50", "resnet101"]
        return np.array(
            [[int(math.ceil(image_shape[0] / stride)),
                int(math.ceil(image_shape[1] / stride))]
                for stride in config.BACKBONE_STRIDES])
    #### ####

    def compose_image_meta(image_id, original_image_shape, image_shape,
                           window, scale, active_class_ids):
        """Takes attributes of an image and puts them in one 1D array.

        image_id: An int ID of the image. Useful for debugging.
        original_image_shape: [H, W, C] before resizing or padding.
        image_shape: [H, W, C] after resizing and padding
        window: (y1, x1, y2, x2) in pixels. The area of the image where the real
                image is (excluding the padding)
        scale: The scaling factor applied to the original image (float32)
        active_class_ids: List of class_ids available in the dataset from which
            the image came. Useful if training on images from multiple datasets
            where not all classes are present in all datasets.
        """
        meta = np.array(
            [image_id] +                  # size=1
            list(original_image_shape) +  # size=3
            list(image_shape) +           # size=3
            list(window) +                # size=4 (y1, x1, y2, x2) in image cooredinates
            [scale] +                     # size=1
            list(active_class_ids)        # size=num_classes
        )
        return meta

    #### ####

    def load_image_gt(dataset, config, image_id, augment=False, augmentation=None,
                      use_mini_mask=False):
        """Load and return ground truth data for an image (image, mask, bounding boxes).

        augment: (deprecated. Use augmentation instead). If true, apply random
            image augmentation. Currently, only horizontal flipping is offered.
        augmentation: Optional. An imgaug (https://github.com/aleju/imgaug) augmentation.
            For example, passing imgaug.augmenters.Fliplr(0.5) flips images
            right/left 50% of the time.
        use_mini_mask: If False, returns full-size masks that are the same height
            and width as the original image. These can be big, for example
            1024x1024x100 (for 100 instances). Mini masks are smaller, typically,
            224x224 and are generated by extracting the bounding box of the
            object and resizing it to MINI_MASK_SHAPE.

        Returns:
        image: [height, width, 3]
        shape: the original shape of the image before resizing and cropping.
        class_ids: [instance_count] Integer class IDs
        bbox: [instance_count, (y1, x1, y2, x2)]
        mask: [height, width, instance_count]. The height and width are those
            of the image unless use_mini_mask is True, in which case they are
            defined in MINI_MASK_SHAPE.
        """
        # Load image and mask
        image = dataset.load_image(image_id)
        mask, class_ids = dataset.load_mask(image_id)
        original_shape = image.shape
        image, window, scale, padding, crop = utils.resize_image(
            image,
            min_dim=config.IMAGE_MIN_DIM,
            min_scale=config.IMAGE_MIN_SCALE,
            max_dim=config.IMAGE_MAX_DIM,
            mode=config.IMAGE_RESIZE_MODE)
        mask = utils.resize_mask(mask, scale, padding, crop)

        # Random horizontal flips.
        # TODO: will be removed in a future update in favor of augmentation
        if augment:
            logging.warning("'augment' is deprecated. Use 'augmentation' instead.")
            if random.randint(0, 1):
                image = np.fliplr(image)
                mask = np.fliplr(mask)

        # Augmentation
        # This requires the imgaug lib (https://github.com/aleju/imgaug)
        if augmentation:
            import imgaug

            # Augmenters that are safe to apply to masks
            # Some, such as Affine, have settings that make them unsafe, so always
            # test your augmentation on masks
            MASK_AUGMENTERS = ["Sequential", "SomeOf", "OneOf", "Sometimes",
                               "Fliplr", "Flipud", "CropAndPad",
                               "Affine", "PiecewiseAffine"]

            def hook(images, augmenter, parents, default):
                """Determines which augmenters to apply to masks."""
                return augmenter.__class__.__name__ in MASK_AUGMENTERS

            # Store shapes before augmentation to compare
            image_shape = image.shape
            mask_shape = mask.shape
            # Make augmenters deterministic to apply similarly to images and masks
            det = augmentation.to_deterministic()
            image = det.augment_image(image)
            # Change mask to np.uint8 because imgaug doesn't support np.bool
            mask = det.augment_image(mask.astype(np.uint8),
                                     hooks=imgaug.HooksImages(activator=hook))
            # Verify that shapes didn't change
            assert image.shape == image_shape, "Augmentation shouldn't change image size"
            assert mask.shape == mask_shape, "Augmentation shouldn't change mask size"
            # Change mask back to bool
            mask = mask.astype(np.bool)

        # Note that some boxes might be all zeros if the corresponding mask got cropped out.
        # and here is to filter them out
        _idx = np.sum(mask, axis=(0, 1)) > 0
        mask = mask[:, :, _idx]
        class_ids = class_ids[_idx]
        # Bounding boxes. Note that some boxes might be all zeros
        # if the corresponding mask got cropped out.
        # bbox: [num_instances, (y1, x1, y2, x2)]
        bbox = utils.extract_bboxes(mask)

        # Active classes
        # Different datasets have different classes, so track the
        # classes supported in the dataset of this image.
        active_class_ids = np.zeros([dataset.num_classes], dtype=np.int32)
        source_class_ids = dataset.source_class_ids[dataset.image_info[image_id]["source"]]
        active_class_ids[source_class_ids] = 1

        # Resize masks to smaller size to reduce memory usage
        if use_mini_mask:
            mask = utils.minimize_mask(bbox, mask, config.MINI_MASK_SHAPE)

        # Image meta data
        image_meta = compose_image_meta(image_id, original_shape, image.shape,
                                        window, scale, active_class_ids)

        return image, image_meta, class_ids, bbox, mask


    #### ####

    def build_rpn_targets(image_shape, anchors, gt_class_ids, gt_boxes, config):
        """Given the anchors and GT boxes, compute overlaps and identify positive
        anchors and deltas to refine them to match their corresponding GT boxes.

        anchors: [num_anchors, (y1, x1, y2, x2)]
        gt_class_ids: [num_gt_boxes] Integer class IDs.
        gt_boxes: [num_gt_boxes, (y1, x1, y2, x2)]

        Returns:
        rpn_match: [N] (int32) matches between anchors and GT boxes.
                   1 = positive anchor, -1 = negative anchor, 0 = neutral
        rpn_bbox: [N, (dy, dx, log(dh), log(dw))] Anchor bbox deltas.
        """
        # RPN Match: 1 = positive anchor, -1 = negative anchor, 0 = neutral
        rpn_match = np.zeros([anchors.shape[0]], dtype=np.int32)
        # RPN bounding boxes: [max anchors per image, (dy, dx, log(dh), log(dw))]
        rpn_bbox = np.zeros((config.RPN_TRAIN_ANCHORS_PER_IMAGE, 4))

        # Handle COCO crowds
        # A crowd box in COCO is a bounding box around several instances. Exclude
        # them from training. A crowd box is given a negative class ID.
        crowd_ix = np.where(gt_class_ids < 0)[0]
        if crowd_ix.shape[0] > 0:
            # Filter out crowds from ground truth class IDs and boxes
            non_crowd_ix = np.where(gt_class_ids > 0)[0]
            crowd_boxes = gt_boxes[crowd_ix]
            gt_class_ids = gt_class_ids[non_crowd_ix]
            gt_boxes = gt_boxes[non_crowd_ix]
            # Compute overlaps with crowd boxes [anchors, crowds]
            crowd_overlaps = utils.compute_overlaps(anchors, crowd_boxes)
            crowd_iou_max = np.amax(crowd_overlaps, axis=1)
            no_crowd_bool = (crowd_iou_max < 0.001)
        else:
            # All anchors don't intersect a crowd
            no_crowd_bool = np.ones([anchors.shape[0]], dtype=bool)

        # Compute overlaps [num_anchors, num_gt_boxes]
        overlaps = utils.compute_overlaps(anchors, gt_boxes)

        # Match anchors to GT Boxes
        # If an anchor overlaps a GT box with IoU >= 0.7 then it's positive.
        # If an anchor overlaps a GT box with IoU < 0.3 then it's negative.
        # Neutral anchors are those that don't match the conditions above,
        # and they don't influence the loss function.
        # However, don't keep any GT box unmatched (rare, but happens). Instead,
        # match it to the closest anchor (even if its max IoU is < 0.3).
        #
        # 1. Set negative anchors first. They get overwritten below if a GT box is
        # matched to them. Skip boxes in crowd areas.
        anchor_iou_argmax = np.argmax(overlaps, axis=1)
        anchor_iou_max = overlaps[np.arange(overlaps.shape[0]), anchor_iou_argmax]
        rpn_match[(anchor_iou_max < 0.3) & (no_crowd_bool)] = -1
        # 2. Set an anchor for each GT box (regardless of IoU value).
        # If multiple anchors have the same IoU match all of them
        gt_iou_argmax = np.argwhere(overlaps == np.max(overlaps, axis=0))[:,0]
        rpn_match[gt_iou_argmax] = 1
        # 3. Set anchors with high overlap as positive.
        rpn_match[anchor_iou_max >= 0.7] = 1

        # Subsample to balance positive and negative anchors
        # Don't let positives be more than half the anchors
        ids = np.where(rpn_match == 1)[0]
        extra = len(ids) - (config.RPN_TRAIN_ANCHORS_PER_IMAGE // 2)
        if extra > 0:
            # Reset the extra ones to neutral
            ids = np.random.choice(ids, extra, replace=False)
            rpn_match[ids] = 0
        # Same for negative proposals
        ids = np.where(rpn_match == -1)[0]
        extra = len(ids) - (config.RPN_TRAIN_ANCHORS_PER_IMAGE -
                            np.sum(rpn_match == 1))
        if extra > 0:
            # Rest the extra ones to neutral
            ids = np.random.choice(ids, extra, replace=False)
            rpn_match[ids] = 0

        # For positive anchors, compute shift and scale needed to transform them
        # to match the corresponding GT boxes.
        ids = np.where(rpn_match == 1)[0]
        ix = 0  # index into rpn_bbox
        # TODO: use box_refinement() rather than duplicating the code here
        for i, a in zip(ids, anchors[ids]):
            # Closest gt box (it might have IoU < 0.7)
            gt = gt_boxes[anchor_iou_argmax[i]]

            # Convert coordinates to center plus width/height.
            # GT Box
            gt_h = gt[2] - gt[0]
            gt_w = gt[3] - gt[1]
            gt_center_y = gt[0] + 0.5 * gt_h
            gt_center_x = gt[1] + 0.5 * gt_w
            # Anchor
            a_h = a[2] - a[0]
            a_w = a[3] - a[1]
            a_center_y = a[0] + 0.5 * a_h
            a_center_x = a[1] + 0.5 * a_w

            # Compute the bbox refinement that the RPN should predict.
            rpn_bbox[ix] = [
                (gt_center_y - a_center_y) / a_h,
                (gt_center_x - a_center_x) / a_w,
                np.log(gt_h / a_h),
                np.log(gt_w / a_w),
            ]
            # Normalize
            rpn_bbox[ix] /= config.RPN_BBOX_STD_DEV
            ix += 1

        return rpn_match, rpn_bbox

    #### ####

    def mold_image(images, config):
        """Expects an RGB image (or array of images) and subtracts
        the mean pixel and converts it to float. Expects image
        colors in RGB order.
        """
        return images.astype(np.float32) - config.MEAN_PIXEL

    #### ####

    b = 0  # batch item index
    image_index = -1
    image_ids = np.copy(dataset.image_ids)
    error_count = 0
    no_augmentation_sources = no_augmentation_sources or []

    # Anchors
    # [anchor_count, (y1, x1, y2, x2)]
    backbone_shapes = compute_backbone_shapes(config, config.IMAGE_SHAPE)
    anchors = utils.generate_pyramid_anchors(config.RPN_ANCHOR_SCALES,
                                             config.RPN_ANCHOR_RATIOS,
                                             backbone_shapes,
                                             config.BACKBONE_STRIDES,
                                             config.RPN_ANCHOR_STRIDE)

    # Keras requires a generator to run indefinitely.
    while True:
        try:
            # Increment index to pick next image. Shuffle if at the start of an epoch.
            image_index = (image_index + 1) % len(image_ids)
            if shuffle and image_index == 0:
                np.random.shuffle(image_ids)

            # Get GT bounding boxes and masks for image.
            image_id = image_ids[image_index]

            # If the image source is not to be augmented pass None as augmentation
            if dataset.image_info[image_id]['source'] in no_augmentation_sources:
                image, image_meta, gt_class_ids, gt_boxes, gt_masks = \
                load_image_gt(dataset, config, image_id, augment=augment,
                              augmentation=None,
                              use_mini_mask=config.USE_MINI_MASK)
            else:
                image, image_meta, gt_class_ids, gt_boxes, gt_masks = \
                    load_image_gt(dataset, config, image_id, augment=augment,
                                augmentation=augmentation,
                                use_mini_mask=config.USE_MINI_MASK)

            # Skip images that have no instances. This can happen in cases
            # where we train on a subset of classes and the image doesn't
            # have any of the classes we care about.
            if not np.any(gt_class_ids > 0):
                continue

            # RPN Targets
            rpn_match, rpn_bbox = build_rpn_targets(image.shape, anchors,
                                                    gt_class_ids, gt_boxes, config)

            # Mask R-CNN Targets
            if random_rois:
                rpn_rois = generate_random_rois(
                    image.shape, random_rois, gt_class_ids, gt_boxes)
                if detection_targets:
                    rois, mrcnn_class_ids, mrcnn_bbox, mrcnn_mask =\
                        build_detection_targets(
                            rpn_rois, gt_class_ids, gt_boxes, gt_masks, config)

            # Init batch arrays
            if b == 0:
                batch_image_meta = np.zeros(
                    (batch_size,) + image_meta.shape, dtype=image_meta.dtype)
                batch_rpn_match = np.zeros(
                    [batch_size, anchors.shape[0], 1], dtype=rpn_match.dtype)
                batch_rpn_bbox = np.zeros(
                    [batch_size, config.RPN_TRAIN_ANCHORS_PER_IMAGE, 4], dtype=rpn_bbox.dtype)
                batch_images = np.zeros(
                    (batch_size,) + image.shape, dtype=np.float32)
                batch_gt_class_ids = np.zeros(
                    (batch_size, config.MAX_GT_INSTANCES), dtype=np.int32)
                batch_gt_boxes = np.zeros(
                    (batch_size, config.MAX_GT_INSTANCES, 4), dtype=np.int32)
                batch_gt_masks = np.zeros(
                    (batch_size, gt_masks.shape[0], gt_masks.shape[1],
                     config.MAX_GT_INSTANCES), dtype=gt_masks.dtype)
                if random_rois:
                    batch_rpn_rois = np.zeros(
                        (batch_size, rpn_rois.shape[0], 4), dtype=rpn_rois.dtype)
                    if detection_targets:
                        batch_rois = np.zeros(
                            (batch_size,) + rois.shape, dtype=rois.dtype)
                        batch_mrcnn_class_ids = np.zeros(
                            (batch_size,) + mrcnn_class_ids.shape, dtype=mrcnn_class_ids.dtype)
                        batch_mrcnn_bbox = np.zeros(
                            (batch_size,) + mrcnn_bbox.shape, dtype=mrcnn_bbox.dtype)
                        batch_mrcnn_mask = np.zeros(
                            (batch_size,) + mrcnn_mask.shape, dtype=mrcnn_mask.dtype)

            # If more instances than fits in the array, sub-sample from them.
            if gt_boxes.shape[0] > config.MAX_GT_INSTANCES:
                ids = np.random.choice(
                    np.arange(gt_boxes.shape[0]), config.MAX_GT_INSTANCES, replace=False)
                gt_class_ids = gt_class_ids[ids]
                gt_boxes = gt_boxes[ids]
                gt_masks = gt_masks[:, :, ids]

            # Add to batch
            batch_image_meta[b] = image_meta
            batch_rpn_match[b] = rpn_match[:, np.newaxis]
            batch_rpn_bbox[b] = rpn_bbox
            batch_images[b] = mold_image(image.astype(np.float32), config)
            batch_gt_class_ids[b, :gt_class_ids.shape[0]] = gt_class_ids
            batch_gt_boxes[b, :gt_boxes.shape[0]] = gt_boxes
            batch_gt_masks[b, :, :, :gt_masks.shape[-1]] = gt_masks
            if random_rois:
                batch_rpn_rois[b] = rpn_rois
                if detection_targets:
                    batch_rois[b] = rois
                    batch_mrcnn_class_ids[b] = mrcnn_class_ids
                    batch_mrcnn_bbox[b] = mrcnn_bbox
                    batch_mrcnn_mask[b] = mrcnn_mask
            b += 1

            # Batch full?
            if b >= batch_size:
                inputs = [batch_images, batch_image_meta, batch_rpn_match, batch_rpn_bbox, batch_gt_class_ids, batch_gt_boxes, batch_gt_masks]
                outputs = []

                if random_rois:
                    inputs.extend([batch_rpn_rois])
                    if detection_targets:
                        inputs.extend([batch_rois])
                        # Keras requires that output and targets have the same number of dimensions
                        batch_mrcnn_class_ids = np.expand_dims(
                            batch_mrcnn_class_ids, -1)
                        outputs.extend(
                            [batch_mrcnn_class_ids, batch_mrcnn_bbox, batch_mrcnn_mask])

                for i in range(len(inputs)):
                    print( 'inputs', i, np.array(inputs[i]).shape)
                print( 'outputs1', np.array(outputs).shape)
                print( 'outputs2', len(outputs))
                print( 'outputs3', outputs)
                yield inputs, outputs

                # start a new batch
                b = 0
        except (GeneratorExit, KeyboardInterrupt):
            raise
        except:
            # Log it and skip the image
            logging.exception("Error processing image {}".format(
                dataset.image_info[image_id]))
            error_count += 1
            if error_count > 5:
                raise

class MaskRCNN(keras.Model):
    def train(self, train_dataset, val_dataset, learning_rate, epochs, layers,
              augmentation=None, custom_callbacks=None, no_augmentation_sources=None):
        """Train the model.
        train_dataset, val_dataset: Training and validation Dataset objects.
        learning_rate: The learning rate to train with
        epochs: Number of training epochs. Note that previous training epochs
                are considered to be done alreay, so this actually determines
                the epochs to train in total rather than in this particaular
                call.
        layers: Allows selecting wich layers to train. It can be:
            - A regular expression to match layer names to train
            - One of these predefined values:
              heads: The RPN, classifier and mask heads of the network
              all: All the layers
              3+: Train Resnet stage 3 and up
              4+: Train Resnet stage 4 and up
              5+: Train Resnet stage 5 and up
        augmentation: Optional. An imgaug (https://github.com/aleju/imgaug)
            augmentation. For example, passing imgaug.augmenters.Fliplr(0.5)
            flips images right/left 50% of the time. You can pass complex
            augmentations as well. This augmentation applies 50% of the
            time, and when it does it flips images right/left half the time
            and adds a Gaussian blur with a random sigma in range 0 to 5.

                augmentation = imgaug.augmenters.Sometimes(0.5, [
                    imgaug.augmenters.Fliplr(0.5),
                    imgaug.augmenters.GaussianBlur(sigma=(0.0, 5.0))
                ])
	    custom_callbacks: Optional. Add custom callbacks to be called
	        with the keras fit_generator method. Must be list of type keras.callbacks.
        no_augmentation_sources: Optional. List of sources to exclude for
            augmentation. A source is string that identifies a dataset and is
            defined in the Dataset class.
        """
        assert self.mode == "training", "Create model in training mode."

        # Pre-defined layer regular expressions
        layer_regex = {
            # all layers but the backbone
            "heads": r"(mrcnn\_.*)|(rpn\_.*)|(fpn\_.*)",
            # From a specific Resnet stage and up
            "3+": r"(res3.*)|(bn3.*)|(res4.*)|(bn4.*)|(res5.*)|(bn5.*)|(mrcnn\_.*)|(rpn\_.*)|(fpn\_.*)",
            "4+": r"(res4.*)|(bn4.*)|(res5.*)|(bn5.*)|(mrcnn\_.*)|(rpn\_.*)|(fpn\_.*)",
            "5+": r"(res5.*)|(bn5.*)|(mrcnn\_.*)|(rpn\_.*)|(fpn\_.*)",
            # All layers
            "all": ".*",
        }
        if layers in layer_regex.keys():
            layers = layer_regex[layers]

        # Data generators
        train_generator = data_generator(train_dataset, self.config, shuffle=True,
                                         augmentation=augmentation,
                                         batch_size=self.config.BATCH_SIZE,
                                         no_augmentation_sources=no_augmentation_sources)
        val_generator = data_generator(val_dataset, self.config, shuffle=True,
                                       batch_size=self.config.BATCH_SIZE)

        # Create log_dir if it does not exist
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

        # Callbacks
        callbacks = [
            keras.callbacks.TensorBoard(log_dir=self.log_dir,
                                        histogram_freq=0, write_graph=True, write_images=False),
            keras.callbacks.ModelCheckpoint(self.checkpoint_path,
                                            verbose=0, save_weights_only=True),
        ]

        # Add custom callbacks to the list
        if custom_callbacks:
            callbacks += custom_callbacks

        # Train
        log("\nStarting at epoch {}. LR={}\n".format(self.epoch, learning_rate))
        log("Checkpoint Path: {}".format(self.checkpoint_path))
        self.set_trainable(layers)
        self.compile(learning_rate, self.config.LEARNING_MOMENTUM)

        # Work-around for Windows: Keras fails on Windows when using
        # multiprocessing workers. See discussion here:
        # https://github.com/matterport/Mask_RCNN/issues/13#issuecomment-353124009
        workers = multiprocessing.cpu_count()

        self.keras_model.fit_generator(
            train_generator,
            initial_epoch=self.epoch,
            epochs=epochs,
            steps_per_epoch=self.config.STEPS_PER_EPOCH,
            callbacks=callbacks,
            validation_data=val_generator,
            validation_steps=self.config.VALIDATION_STEPS,
            max_queue_size=100,
            workers=workers,
            use_multiprocessing=True,
        )
        self.epoch = max(self.epoch, epochs)

# Train model
if True:
    # prepare train set
    train_set = KangarooDataset()
    train_set.load_dataset('kangaroo', is_train=True)
    train_set.prepare()
    print('Train: %d' % len(train_set.image_ids))
    # prepare test set
    test_set = KangarooDataset()
    test_set.load_dataset('kangaroo', is_train=True)
    test_set.prepare()
    print('Test: %d' % len(test_set.image_ids))
    # prepare config
    config = KangarooConfig()
    config.display()
    # define the model
    #model = MaskRCNN(mode='training', model_dir='./', config=config)
    print(input_shape)
    model = create_vit_object_detector(
        input_shape,
        patch_size,
        num_patches,
        projection_dim,
        num_heads,
        transformer_units,
        transformer_layers,
        mlp_head_units,
    )
    # load weights (mscoco) and exclude the output layers
    #model.load_weights('mask_rcnn_coco.h5', by_name=True, exclude=["mrcnn_class_logits", "mrcnn_bbox_fc",  "mrcnn_bbox", "mrcnn_mask"])
    # train weights (output layers or 'heads')
    #model.train(train_set, training=True)
    #model.train(train_set, test_set, learning_rate=config.LEARNING_RATE, epochs=5, layers='heads')

    optimizer = keras.optimizers.AdamW( learning_rate=learning_rate, weight_decay=weight_decay)
    # Compile model.
    model.compile(optimizer=optimizer, loss=keras.losses.MeanSquaredError())
    print(f"Model compiled")

    # Data generators
    train_generator = data_generator(train_set, config, shuffle=True,
                                         augmentation=None,
                                         batch_size=config.BATCH_SIZE,
                                         no_augmentation_sources=None)
    model.fit(train_generator, epochs=5)

else:
    history = run_experiment( vit_object_detector, learning_rate, weight_decay, batch_size, num_epochs)
    print(f"Experiment done")

##############################################################################


def plot_history(item):
    plt.plot(history.history[item], label=item)
    plt.plot(history.history["val_" + item], label="val_" + item)
    plt.xlabel("Epochs")
    plt.ylabel(item)
    plt.title("Train and Validation {} Over Epochs".format(item), fontsize=14)
    plt.legend()
    plt.grid()
    plt.show()


plot_history("loss")
print(f"Plot 3 done")


"""
## Evaluate the model
"""

import matplotlib.patches as patches

# Saves the model in current path
vit_object_detector.save("vit_object_detector.keras")


# To calculate IoU (intersection over union, given two bounding boxes)
def bounding_box_intersection_over_union(box_predicted, box_truth):
    # get (x, y) coordinates of intersection of bounding boxes
    top_x_intersect = max(box_predicted[0], box_truth[0])
    top_y_intersect = max(box_predicted[1], box_truth[1])
    bottom_x_intersect = min(box_predicted[2], box_truth[2])
    bottom_y_intersect = min(box_predicted[3], box_truth[3])

    # calculate area of the intersection bb (bounding box)
    intersection_area = max(0, bottom_x_intersect - top_x_intersect + 1) * max(
        0, bottom_y_intersect - top_y_intersect + 1
    )

    # calculate area of the prediction bb and ground-truth bb
    box_predicted_area = (box_predicted[2] - box_predicted[0] + 1) * (
        box_predicted[3] - box_predicted[1] + 1
    )
    box_truth_area = (box_truth[2] - box_truth[0] + 1) * (
        box_truth[3] - box_truth[1] + 1
    )

    # calculate intersection over union by taking intersection
    # area and dividing it by the sum of predicted bb and ground truth
    # bb areas subtracted by  the interesection area

    # return ioU
    return intersection_area / float(
        box_predicted_area + box_truth_area - intersection_area
    )


i, mean_iou = 0, 0

# Compare results for 10 images in the test set
for input_image in x_test[:10]:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 15))
    im = input_image

    # Display the image
    ax1.imshow(im.astype("uint8"))
    ax2.imshow(im.astype("uint8"))

    input_image = cv2.resize(
        input_image, (image_size, image_size), interpolation=cv2.INTER_AREA
    )
    input_image = np.expand_dims(input_image, axis=0)
    preds = vit_object_detector.predict(input_image)[0]

    h, w = (im).shape[0:2]

    top_left_x, top_left_y = int(preds[0] * w), int(preds[1] * h)

    bottom_right_x, bottom_right_y = int(preds[2] * w), int(preds[3] * h)

    box_predicted = [top_left_x, top_left_y, bottom_right_x, bottom_right_y]
    # Create the bounding box
    rect = patches.Rectangle(
        (top_left_x, top_left_y),
        bottom_right_x - top_left_x,
        bottom_right_y - top_left_y,
        facecolor="none",
        edgecolor="red",
        linewidth=1,
    )
    # Add the bounding box to the image
    ax1.add_patch(rect)
    ax1.set_xlabel(
        "Predicted: "
        + str(top_left_x)
        + ", "
        + str(top_left_y)
        + ", "
        + str(bottom_right_x)
        + ", "
        + str(bottom_right_y)
    )

    top_left_x, top_left_y = int(y_test[i][0] * w), int(y_test[i][1] * h)

    bottom_right_x, bottom_right_y = int(y_test[i][2] * w), int(y_test[i][3] * h)

    box_truth = top_left_x, top_left_y, bottom_right_x, bottom_right_y

    mean_iou += bounding_box_intersection_over_union(box_predicted, box_truth)
    # Create the bounding box
    rect = patches.Rectangle(
        (top_left_x, top_left_y),
        bottom_right_x - top_left_x,
        bottom_right_y - top_left_y,
        facecolor="none",
        edgecolor="red",
        linewidth=1,
    )
    # Add the bounding box to the image
    ax2.add_patch(rect)
    ax2.set_xlabel(
        "Target: "
        + str(top_left_x)
        + ", "
        + str(top_left_y)
        + ", "
        + str(bottom_right_x)
        + ", "
        + str(bottom_right_y)
        + "\n"
        + "IoU"
        + str(bounding_box_intersection_over_union(box_predicted, box_truth))
    )
    i = i + 1

print("mean_iou: " + str(mean_iou / len(x_test[:10])))
plt.show()

"""
This example demonstrates that a pure Transformer can be trained
to predict the bounding boxes of an object in a given image,
thus extending the use of Transformers to object detection tasks.
The model can be improved further by tuning hyper-parameters and pre-training.
"""

"""
## Relevant Chapters from Deep Learning with Python
- [Chapter 12: Object detection](https://deeplearningwithpython.io/chapters/chapter12_object-detection)
"""

#########  END  ##############################################
#########  END  ##############################################
#########  END  ##############################################

# Module Imports
import os
import sys
import random
import math
import pathlib

from PIL import Image, ImageOps, ImageDraw

#import tensorflow as tf

# Root directory of the model
OBJECT_DETECTOR_ROOT_DIR = os.path.abspath("/Mask-RCNN_model")
# print(OBJECT_DETECTOR_ROOT_DIR)

tools_db_name = "object_detector"

from mrcnn import utils
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

##############################################################################

class AirplaneDataset(utils.Dataset):

    # load the dataset definitions
    def load_dataset(self, path_images, path_annot, image_size, min_mask_size, is_train=True):
        self.add_class("dataset", 1, "Airplane")
        image_paths = [ f for f in os.listdir(path_images) if os.path.isfile(os.path.join(path_images, f)) ]
        image_paths.sort()
        annot_paths = [ f for f in os.listdir(path_annot) if os.path.isfile(os.path.join(path_annot, f)) ]
        annot_paths.sort()
        # loop over the annotations and images, preprocess them and store in lists
        for i in range(0, len(annot_paths)):
            image = keras.utils.load_img( path_images + image_paths[i],)
            w, h = image.size[:2]
            #print(f"Loop {i} {path_annot + annot_paths[i]}")
            targets = []
            # Access bounding box coordinates
            #print( f"Annot {scipy.io.loadmat(path_annot + annot_paths[i])}")
            for annot in scipy.io.loadmat(path_annot + annot_paths[i])["box_coord"]:
                #print(f"annot {annot}")
                box = [ round(image_size*(float(coord) / w)) for coord in annot ]
                if (box[1] - box[0] > min_mask_size) and (box[3] - box[2] > min_mask_size):
                    # apply relative scaling to bounding boxes as per given image and append to list
                    targets.append( box )
                    #print(f"box {box[0]}:{box[2]} {box[1]}:{box[3]}")

            if len( targets) > 0:
                #print(f"Loop {i} {path_annot + annot_paths[i]} {path_images + image_paths[i]}")
                # resize images # convert image to array and append to list
                img = keras.utils.img_to_array(image.resize((image_size, image_size)))

                self.add_image( 'dataset', image_id=id, image=img, annotation=targets, path=path_images + image_paths[i])
                #print(f"Annot {i} done")


    # load the masks for an image
    def load_mask(self, image_id):
        info = self.image_info[image_id]
        boxes = info['annotation']
        w, h, c = info['image'].shape
        #print(f"shape {info['image'].shape}")
        masks = np.zeros([h, w, len(boxes)], dtype='uint8')
        #print(f"annotation {info['annotation']}")
        #class_ids = list()
        class_ids = np.zeros( len(boxes), dtype=np.int32)
        for i, box in enumerate( boxes):
            masks[box[1]:box[3], box[0]:box[2], i] = 1
            #class_ids.append(self.class_names.index('Airplane'))
            class_ids[i] = self.class_names.index('Airplane')
            #print(f"box {masks.shape} {i} {box[0]}:{box[2]} {box[1]}:{box[3]}")
        #return masks, np.asarray(class_ids, dtype='int32')
        return masks, class_ids
 
    # load an image reference
    def load_image(self, image_id):
        info = self.image_info[image_id]
        return info['image']

    # load an image reference
    def get_batches(self, batch_size):
        images = list ()
        masks = list ()
        print(f"batch start {len(self.image_ids)}")
        for batch_idx in range(0, len(self.image_ids), batch_size):
            images = np.array([self.load_image( id) for id in self.image_ids[ batch_idx:batch_idx+batch_size]])
            #masks = np.array([(self.load_mask( id)) for id in self.image_ids[ batch_idx:batch_idx+batch_size]])
            masks = [(self.load_mask( id)) for id in self.image_ids[ batch_idx:batch_idx+batch_size]]
            #for i, id in enumerate(self.image_ids[ batch_idx:batch_idx+batch_size]):
                #masks.append( self.load_mask( id))
            print(f"batch {batch_idx} {len(images)} {images.shape} {len(masks)} {masks}")
            yield batch_idx, images, masks
