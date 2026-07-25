import torchvision
##from torchvision.models import resnet50, ResNet50_Weights
#from torchvision.models import maskrcnn_resnet50_fpn_v2

# Using pretrained weights:
##resnet50(weights=ResNet50_Weights.IMAGENET1K_V1)
##resnet50(weights="IMAGENET1K_V1")

# Using no weights:
##resnet50(weights=None)
##resnet50()

import libDloadCoco
import libDsetCoco

######## COCO 1 ----------------

from pycocotools.coco import COCO
from pycocotools import mask as coco_mask
from torch.utils.data import Dataset

from torchvision.datasets import CocoDetection, wrap_dataset_for_transforms_v2
#import torchvision.datasets.CocoDetection(root: Union[str, Path], annFile: str, transform: Optional[Callable] = None, target_transform: Optional[Callable] = None, transforms: Optional[Callable] = None)

def plot_sample( sample):
    img, target = sample
    if isinstance( img, Image.Image):
        #print( 'img', type(img))
        #print( 'image', img.size, img.mode, img)
        img=functional.pil_to_tensor(img)
        #print( 'img', type(img))
        #print( 'image', img.shape)
    #print( 'img', img.type)
    #print( 'target.keys()', target.keys())
    #print( 'boxes', target['boxes'])
    fig = plt.figure(figsize=(10, 8))
    plt.title( f"Image Target ({img.shape}) ")
    #print( 'img', img)
    #pil_mask = create_polygon_boxes( pil_img.size, target['boxes'])
    #print( 'pil_mask', pil_mask)
    #plt.imshow(pil_mask)

    draw_bboxes = partial(draw_bounding_boxes, fill=False, width=2, font_size=25)

    pil_labels = target['labels'].tolist()
    print( 'pil_labels', pil_labels)
    set_labels = list(set(pil_labels))
    #print( 'set_labels', set_labels)
    len_labels = len(set_labels)
    #print( 'len(set_labels)', len_labels)
    idx_labels = [set_labels.index(id) for id in pil_labels]
    #print( 'idx_labels', idx_labels)
    colors = distinctipy.get_colors(len_labels)
    #print( 'colors', colors)
    int_colors = [tuple(int(c*255) for c in colors[idx]) for idx in idx_labels]
    #print( 'int_colors', int_colors)
    #txt_labels = [self.coco.loadCats(id)[0]['name'] for id in pil_labels]
    #print( 'text labels', txt_labels)
    #txt_labels = [cat['name'] for cat in self.coco.loadCats( pil_labels)]
    txt_labels = [str(cat) for cat in pil_labels]
    #print( 'text labels', txt_labels)
    # Annotate the sample image with labels and bounding boxes
    annotated_tensor = draw_bboxes(
        image=img,
        boxes=target['boxes'], 
        labels=txt_labels, 
        colors=int_colors
    )
    pil_image = functional.to_pil_image( annotated_tensor, mode='RGB')
    plt.imshow(pil_image)
    plt.axis('off')
    plt.show()

def plot_prediction( image, pred, cat_names=None):
        for name, pred_val in pred.items():
                print(f"{name:<20}{len(pred_val)}")
        print( 'boxes', pred['boxes'])
        #print( 'image', image.shape, image)
        fig = plt.figure(figsize=(10, 8))
        plt.title( f"Image Target ({image.shape}) ")
        draw_bboxes = partial(draw_bounding_boxes, fill=False, width=2, font_size=25)
        pil_labels = pred['labels'].tolist()
        #print( 'pil_labels', pil_labels)
        pil_scores = pred['scores'].tolist()
        #print( 'pil_scores', pil_scores)
        set_labels = list(set(pil_labels))
        #print( 'set_labels', set_labels)
        len_labels = len(set_labels)
        #print( 'len(set_labels)', len_labels)
        idx_labels = [set_labels.index(id) for id in pil_labels]
        #print( 'idx_labels', idx_labels)
        colors = distinctipy.get_colors(len_labels)
        #print( 'colors', colors)
        int_colors = [tuple(int(c*255) for c in colors[idx]) for idx in idx_labels]
        #print( 'int_colors', int_colors)
        if cat_names is None:
            txt_labels = [str(cat) for cat in pil_labels]
        else:
            txt_labels = [f"{cat_names[cat]} {score:.3f}" for cat, score in zip( pil_labels, pil_scores)]
        print( 'text labels', txt_labels)
        # Annotate the sample image with labels and bounding boxes
        annotated_tensor = draw_bboxes(
            image=image, 
            boxes=pred['boxes'], 
            labels=txt_labels, 
            colors=int_colors
        )
        pil_image = functional.to_pil_image( annotated_tensor, mode='RGB')
        plt.imshow(pil_image)
        plt.axis('off')
        plt.show()

import keras

#print('cap_val2017_data:', cap_val2017_data)
#dataset_iter = cap_val2017_data
#print(next(dataset_iter))

import os
import torch
import torchvision.transforms.v2 as T
from torchvision.io import decode_image
from torchvision.utils import draw_bounding_boxes
from torchvision.transforms import functional

import os
import sys

os.environ["QT_API"] = "PyQt6"

from PyQt6 import QtCore, QtWidgets
from matplotlib.backends.backend_qtagg import FigureCanvas
from matplotlib.figure import Figure

class MplCanvas(FigureCanvas):

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super().__init__(fig)


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Create the maptlotlib FigureCanvas object,
        # which defines a single set of axes as self.axes.
        sc = MplCanvas(self, width=5, height=4, dpi=100)
        sc.axes.plot([0,1,2,3,4], [10,1,20,3,40])
        self.setCentralWidget(sc)

        self.show()


app = QtWidgets.QApplication(sys.argv)
w = MainWindow()
app.exec()

transforms = T.Compose(
    [
        T.ToImage(),
#        T.RandomPhotometricDistort(p=1),
#        T.RandomZoomOut(fill={tv_tensors.Image: (123, 117, 104), "others": 0}),
#        T.RandomIoUCrop(),
#        T.RandomHorizontalFlip(p=1),
        T.SanitizeBoundingBoxes(),
        T.ToDtype(torch.float32, scale=True),
    ]
)

from PIL import Image, ImageDraw
import matplotlib
import matplotlib.pyplot as plt
from functools import partial
from distinctipy import distinctipy
from torchvision.models.detection.mask_rcnn import maskrcnn_resnet50_fpn, MaskRCNN_ResNet50_FPN_Weights

image_size = 256 # 513

debug_set=False
train=False
coco_torch=True
model_torch=False
if True:
    ann_file, ids_file, imagedir = libDloadCoco.download_coco_files( 'val', '2017')
    if coco_torch:
        coco_set = CocoDetection( root=imagedir, annFile=ann_file, transforms=transforms) # target_transform )
        #sample = torch_coco_set[0]
        #img, target = sample
        #print(f"{type(img) = }\n{type(target) = }\n{type(target[0]) = }\n{target[0].keys() = }")
        coco_set = wrap_dataset_for_transforms_v2(coco_set, target_keys=("boxes", "labels", "masks"))
    else:
        coco_set = libDsetCoco.COCOSegmentation( ann_file, ids_file, imagedir, split='val', image_size=image_size)
    if debug_set:
        print(f"{type(coco_set) = }  {len(coco_set) = }")
        sample = coco_set[0]
        print(f"{type(sample) = }  {len(sample) = }")
        img, target = sample
        #print(f"target {target}")
        print(f"{type(img) = }\n{type(target) = }\n{target.keys() = }")
        print(f"{target['boxes'].shape = }\n{target['labels'].shape = }\n{target['masks'].shape = }")
        #print(f"{type(target['boxes']) = }\n{type(target['labels']) = }\n{type(target['masks']) = }")
        plot_sample( sample)

    data_loader = torch.utils.data.DataLoader(
        coco_set,
        batch_size=2,
        # We need a custom collation function here, since the object detection
        # models expect a sequence of images and target dictionaries. The default
        # collation function tries to torch.stack() the individual elements,
        # which fails in general for object detection, because the number of bounding
        # boxes varies between the images of the same batch.
        collate_fn=lambda batch: tuple(zip(*batch)),
    )

    if model_torch:
        category_names = None
        model = torchvision.models.get_model("maskrcnn_resnet50_fpn_v2", weights=None, weights_backbone=None).train()
    else:
               #maskrcnn_resnet50_fpn(                  weights=MaskRCNN_ResNet50_FPN_Weights.DEFAULT)
        weights = MaskRCNN_ResNet50_FPN_Weights.COCO_V1
        category_names = weights.meta["categories"]
        model = maskrcnn_resnet50_fpn( pretrained=True, weights=weights)

    if train: # train
        model.train()
        for imgs, targets in data_loader:
            loss_dict = model(imgs, targets)
            # Put your training logic here

            print(f"{[img.shape for img in imgs] = }")
            print(f"{[type(target) for target in targets] = }")
            for name, loss_val in loss_dict.items():
                print(f"{name:<20}{loss_val:.3f}")
            break
    else: # inference
        model.eval()
        for imgs, targets in data_loader:
            pred_batch_dict = model(imgs, targets)
            print( type(pred_batch_dict[0]))
            for img, pred in zip( imgs, pred_batch_dict):
            	plot_prediction( img, pred, category_names)
            for name, pred_val in pred_batch_dict[0].items():
                #print(f"{name:<20}{pred_val:.3f}")
                print(f"{name:<20}{len(pred_val)}")
            break

    assert False

import random


def coco_collate_fn(batch):
    images = []
    targets = []
    
    #print('batch', len(batch),len(batch[0]), batch)
    #print(len(batch),len(batch[0]),len(batch[0][0]),len(batch[0][1]))
    #print('len(batch),len(batch[0])', len(batch),len(batch[0]))
    for elem in batch:
        image = elem['image']
        #target = elem['label']
        target = elem['target']
        #print("image", image)
        #print("target", target)
        #print("image.shape", image.shape)
        #print('len(target)',len(target))
        #if len(target) > 0:
            #print('target[0].keys()',target[0].keys())
        images.append(image)
        # target is typically a list of dicts for CocoDetection
        targets.append(target)
        #print(len(images),len(targets))
        
    # Stack images into a single tensor of shape [B, C, H, W]
    #images = torch.stack(images, dim=0)
    #print('coco collate images',images)
    #print('coco collate images[0]',images[0])
    #print('images[0].shape',images[0].shape)
    #print('coco collate len(images)',len(images), 'images[0].shape',images[0].shape)

    return images, targets

collate_fn=lambda x: tuple(zip(*x))

from torch.utils.data import DataLoader

ann_file, ids_file, imagedir = libDloadCoco.download_coco_files( split='val', year='2017')
coco_set = libDsetCoco.COCOSegmentation( ann_file, ids_file, imagedir, split='val', image_size=image_size)

print( 'Dataset size', len(coco_set))
#print( coco_set.NUM_CLASSES, len(coco_set.CAT_LIST))
#print( coco_set[0])
#print( coco_set[0]['image'])
#coco_set.display_image_target( random.randrange(len(coco_set)))

def print_batch(dataset_iter):
        images, targets = next( iter( dataset_iter))
        print('iter batch_len len(images)',len(images),'len(targets)',len(targets))
        print('iter images[0].shape',images[0].shape)
        #print('iter images[0].shape[-2:]',images[0].shape[-2:])
        #print('iter targets[0]',targets[0])
        print("iter len(targets[0]['labels'])", len(targets[0]['labels']))
        #print("iter targets[0]['labels']", targets[0]['labels'])
        print("iter targets[0]['boxes'].shape", targets[0]['boxes'].shape)
        print("iter targets[0]['boxes']", targets[0]['boxes'])
        print("iter targets[0]['masks'].shape", targets[0]['masks'].shape)
        #print()
        #print(targets[1][0].keys())
        print()

batch_size=5 # 4

# Create the DataLoader with your collate_fn
dataset_iter = DataLoader(
    coco_set,
    batch_size=batch_size,
    shuffle=False,
    collate_fn=coco_collate_fn
)

print_batch(dataset_iter)

######## COCO 1 ================

def run_inference_batch( batch_idx, model, images):
    #print('shape', images[0].shape), targets[0].shape)
    for elem_idx, image in enumerate( images):
        coco_set.display_image_target( elem_idx + batch_idx * len(images))
    results = model( images)
    return results

def print_batch_results( batch_idx, batches_cnt, images, results):
    print('batch loop', batch_idx + 1, '/', batches_cnt, ':', len(results), results[0].keys())
    print('      labels', len(results[0]['labels']), results[0]['labels'])
    print('      scores', len(results[0]['scores']), results[0]['scores'])
    if len(results[0]['boxes']) > 0:
        print('      boxes ', len(results[0]['boxes']), results[0]['boxes'][0])
    else:
        print('      boxes ', len(results[0]['boxes']))
    #print('      boxes ', len(results[0]['boxes']), results[0]['boxes'][0])
    print('      masks ', len(results[0]['masks']), results[0]['masks'].shape)
    for i, (image, result) in enumerate( zip( images, results)):
        display_image_result( i, batch_idx, batches_cnt, image, result)

from torchvision.utils import save_image

def print_batch_target_masks( batch_idx, images, targets, save_mask=False):
    for j in range(len(targets)):
        print('shape', batch_idx, j, targets[j]['masks'].shape)
        if save_mask:
            save_image( images[j], f'./debug/b{batch_idx:04d}_i{j:04d}_b.jpg')
            non_black_mask = (targets[j] > 1e-5).any(dim=0)
            targets[j][:, non_black_mask] = 255 # 1.0
            save_image( targets[j], f'./debug/b{batch_idx:04d}_i{j:04d}_m.png')

def display_image_result( i, batch_idx, batches_cnt, image, result):
    print('batch loop', batch_idx + 1, '/', batches_cnt, 'image', i + 1)

    if len(result['boxes']) > 0:
        print('      boxes ', len(result['boxes']), result['boxes'][0])
    else:
        print('      boxes ', len(result['boxes']))

    fig = plt.figure(figsize=(10, 8))
    plt.title( f"Image Result ({image.shape}) batch {batch_idx+1}/{batches_cnt} elem {i+1}")
    pil_image = functional.to_pil_image( image, mode='RGB')
    pil_labels = result['labels'].tolist()
    draw_bboxes = partial(draw_bounding_boxes, fill=False, width=2, font_size=25)
    print( 'pil_labels', pil_labels)
    set_labels = list(set(pil_labels))
    #print( 'set_labels', set_labels)
    len_labels = len(set_labels)
    #print( 'len(set_labels)', len_labels)
    idx_labels = [set_labels.index(id) for id in pil_labels]
    #print( 'idx_labels', idx_labels)
    txt_labels = [coco_set.cat_name(id) if id not in [12, 29, 30, 45, 68, 69, 71, 83] else 'UNKNOWN' for id in pil_labels]
    print( 'text labels', txt_labels)
    #txt_labels = [coco_set.coco.loadCats(id)[0]['name'] for id in pil_labels]
    #try:
        #txt_labels = [coco_set.cat_name(id) if id not in [29, 68, 69, 71] else 'UNKNOWN' for id in pil_labels]
    #except:
        #print('exception', [id for id in pil_labels])
    #txt_labels2 = [cat['name'] for cat in coco_set.loadCats( pil_labels)]
    #print( 'text labels', txt_labels, txt_labels2)
    colors = distinctipy.get_colors(len_labels)
    #print( 'colors', colors)
    int_colors = [tuple(int(c*255) for c in colors[idx]) for idx in idx_labels]
    #print( 'int_colors', int_colors)
    annotated_tensor = draw_bboxes(
        image=image, 
        boxes=result['boxes'], 
        labels=txt_labels, 
        colors=int_colors
    )
    pil_image = functional.to_pil_image( annotated_tensor, mode='RGB')
    plt.imshow(pil_image)
    #fig.figimage(pil_image)
    plt.axis('off')
    plt.show()
    print('      labels', len(result['labels']), [(id, txt) for id, txt in zip( pil_labels, txt_labels)])
    print('      scores', len(result['scores']), result['scores'])
    print('      masks ', len(result['masks']), result['masks'].shape)
    print()

def run_inference_epoch(model, dataloader, batches_cnt):
    for i, (images, targets) in enumerate( dataloader):
        print('Batch Loop', i + 1, 'Images:', len(images), 'Targets:', len(targets))
        print('Batch Loop', i + 1, images, targets)
        print_batch_target_masks( i, images, targets, save_mask=False)
        #coco_set.display_image_target( i)
        results = run_inference_batch( i, model, images)
        print_batch_results( i, batches_cnt, images, results)

import math
from tqdm.auto import tqdm

debug_loss=False

def run_epoch(model, dataloader, optimizer, lr_scheduler, scaler, epoch_id, is_training):
    """
    Function to run a single training or evaluation epoch.
    
    Args:
        model: A PyTorch model to train or evaluate.
        dataloader: A PyTorch DataLoader providing the data.
        optimizer: The optimizer to use for training the model.
        loss_func: The loss function used for training.
        device: The device (CPU or GPU) to run the model on.
        scaler: Gradient scaler for mixed-precision training.
        is_training: Boolean flag indicating whether the model is in training or evaluation mode.
    
    Returns:
        The average loss for the epoch.
    """
    if is_training:
        # Set the model to training mode
        model.train()
    else:
        model.eval()
    
    epoch_loss = 0  # Initialize the total loss for this epoch
    progress_bar = tqdm(total=len(dataloader), desc="Train" if is_training else "Eval")  # Initialize a progress bar
    
    # Loop over the data
    for batch_id, (inputs, targets) in enumerate(dataloader):
        # Move inputs and targets to the specified device
        #inputs = torch.stack(inputs).to(device)
        
        # Forward pass with Automatic Mixed Precision (AMP) context manager
        #with autocast(torch.device(device).type):
        if is_training:
                #losses = model(inputs.to(device), move_data_to_device(targets, device))
                losses = model(inputs, targets)
        else:
                with torch.no_grad():
                    #losses = model(inputs.to(device), move_data_to_device(targets, device))
                    losses = model(inputs, targets)
        
        if debug_loss:
            for key, val in losses.items():
                print( ' ', key, val)

        # Compute the loss
        loss = sum([loss for loss in losses.values()])  # Sum up the losses
        if debug_loss:
            print( 'loss', loss)

        # If in training mode, backpropagate the error and update the weights
        if is_training:
            #print( 'training')
            if scaler:
                #print( 'scaler')
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                old_scaler = scaler.get_scale()
                scaler.update()
                new_scaler = scaler.get_scale()
                if new_scaler >= old_scaler:
                    lr_scheduler.step()
                    #print( 'lr_scheduler.step()')
            else:
                loss.backward()
                optimizer.step()
                lr_scheduler.step()
                
            optimizer.zero_grad()

        # Update the total loss
        loss_item = loss.item()
        if debug_loss:
            print( 'loss_item', loss_item, 'math.isnan(loss_item)', math.isnan(loss_item), 'math.isfinite(loss_item)', math.isfinite(loss_item))
        epoch_loss += loss_item
        
        # Update the progress bar
        progress_bar_dict = dict(loss=loss_item, avg_loss=epoch_loss/(batch_id+1))
        if is_training:
            progress_bar_dict.update(lr=lr_scheduler.get_last_lr()[0])
        progress_bar.set_postfix(progress_bar_dict)
        progress_bar.update()
        #print('batch', batch_id, 'done')

        # If loss is NaN or infinity, stop training
        if is_training:
            stop_training_message = f"Loss is NaN and infinite at epoch {epoch_id}, batch {batch_id}. Stopping training."
            assert not math.isnan(loss_item) or math.isfinite(loss_item), stop_training_message
            assert not math.isnan(loss_item), f"Loss is NaN epoch {epoch_id}, batch {batch_id}. Stopping training."
            assert math.isfinite(loss_item), f"Loss is infinite at epoch {epoch_id}, batch {batch_id}. Stopping training."

    # Cleanup and close the progress bar 
    progress_bar.close()
    
    # Return the average loss for this epoch
    return epoch_loss / (batch_id + 1)

if False:
    print( 'detection', torchvision.models.list_models(module=torchvision.models.detection))
    print( 'detection.mask_rcnn', torchvision.models.list_models(module=torchvision.models.detection.mask_rcnn))

from torchvision.models.detection.mask_rcnn import maskrcnn_resnet50_fpn, MaskRCNN_ResNet50_FPN_Weights
#maskrcnn_resnet50_fpn(weights=MaskRCNN_ResNet50_FPN_Weights.DEFAULT)
model = maskrcnn_resnet50_fpn( pretrained=True, weights=MaskRCNN_ResNet50_FPN_Weights.COCO_V1)

in_features_box = model.roi_heads.box_predictor.cls_score.in_features
in_features_mask = model.roi_heads.mask_predictor.conv5_mask.in_channels
out_chanels_mask = model.roi_heads.mask_predictor.conv5_mask.out_channels

from torchvision.models.detection.mask_rcnn import MaskRCNNPredictor
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
if True:
    #coco_set.NUM_CLASSES = 4
    print( 'NUM_CLASSES', coco_set.NUM_CLASSES)
    model.roi_heads.box_predictor = FastRCNNPredictor(in_channels=in_features_box, num_classes=coco_set.NUM_CLASSES)
    model.roi_heads.mask_predictor = MaskRCNNPredictor(in_channels=in_features_mask, dim_reduced=min(256,out_chanels_mask), num_classes=coco_set.NUM_CLASSES)
    new_in_features_box = model.roi_heads.box_predictor.cls_score.in_features
    new_in_features_mask = model.roi_heads.mask_predictor.conv5_mask.in_channels
    new_out_chanels_mask = model.roi_heads.mask_predictor.conv5_mask.out_channels
    print( 'in_features_box', in_features_box, '->', new_in_features_box,
           'in_features_mask', in_features_mask, '->', new_in_features_mask,
           'out_chanels_mask', out_chanels_mask, '->', new_out_chanels_mask)
else:
    print( 'in_features_box', in_features_box, 'in_features_mask', in_features_mask, 'out_chanels_mask', out_chanels_mask)

#from torchtnt.utils import get_module_summary
#print( get_module_summary(model.eval(), [torch.randn(1, 3, 256, 256)]))

model.eval()
print('before evaluate')
if False:
    images, first = next( dataset_iter)
    results = model( images)
    print('test', len(results), results[0])

batches_cnt = 1 + (len(coco_set) - 1) // batch_size

run_inference_epoch(model, dataset_iter, batches_cnt)

# Learning rate for the model
lr = 5e-6
# Number of training epochs
epochs = 50
# AdamW optimizer; includes weight decay for regularization
optimizer = torch.optim.AdamW(model.parameters(), lr=lr)
# Learning rate scheduler; adjusts the learning rate during training
print('trainiing steps', epochs*len(dataset_iter), 'epochs', epochs, 'batches', len(dataset_iter))
lr_scheduler = torch.optim.lr_scheduler.OneCycleLR(optimizer, max_lr=lr, total_steps=epochs*len(dataset_iter))

run_epoch(model, dataset_iter, optimizer, lr_scheduler, scaler=None, epoch_id=1, is_training=True)

from torchvision.models.detection.mask_rcnn import maskrcnn_resnet50_fpn_v2, MaskRCNN_ResNet50_FPN_V2_Weights
maskrcnn_resnet50_fpn_v2(weights=MaskRCNN_ResNet50_FPN_V2_Weights.DEFAULT)
maskrcnn_resnet50_fpn_v2(weights=MaskRCNN_ResNet50_FPN_V2_Weights.COCO_V1)

