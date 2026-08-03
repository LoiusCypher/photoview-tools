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
import json

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

def gen_labelme_json( image, pred, cat_names, epoch, file_name, min_score=0.9):
    json_file = os.path.join( "Test-Images", f"{file_name.replace('.jpg','.json')}")
    #print( f"{json_file = }")
    labelme_dict = {}
    labelme_dict['version'] = "1.0.0"
    labelme_dict['flags'] = {}
    labelme_dict['shapes'] = []
    labelme_dict['imagePath'] = file_name
    labelme_dict['imageData'] = None
    #print( f"{image.shape = }")
    labelme_dict['imageHeight'] = image.shape[1]
    labelme_dict['imageWidth'] = image.shape[2]
    #print( f"{pred = }")
    for i in range( len( pred['boxes'])):
        #print( f"{pred['labels'][i] = }") 
        #print( f"{cat_names[pred['labels'][i]] = }") 
        #print( f"{i = } {pred['scores'][i].item() = } ", pred['scores'][i].float()) 
        bbox = {
            #'label': f"{cat_names[pred['labels'][i]-1]}",
            'label': f"{cat_names[pred['labels'][i]-1]}_{pred['scores'][i].item():.2f}",
            'points': [
                [ pred['boxes'][i][0].item(), pred['boxes'][i][1].item() ],
                [ pred['boxes'][i][2].item(), pred['boxes'][i][3].item() ]
            ],
            'group_id': None,
            'description': "",
            'shape_type': "rectangle",
            'flags': {},
            'mask': None,
        }
        #print( f"{bbox = } ") 
        if pred['scores'][i].item() >= min_score:
            labelme_dict['shapes'].append( bbox)
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump( labelme_dict, f, ensure_ascii=False, indent=4)

def plot_prediction( image, pred, cat_names=None, epoch=None, file_name=None):
        for name, pred_val in pred.items():
            print(f"{name:<20}{len(pred_val)}")
        print( 'boxes', pred['boxes'])
        print( f'image {image.shape = }')
        fig = plt.figure(figsize=(10, 8))
        plt.title( f"Image Target ({image.shape}) ")
        draw_bboxes = partial(draw_bounding_boxes, fill=False, width=2, font_size=max(image.shape[1]//30,25))
        pil_labels = pred['labels'].tolist()
        print( f'{pil_labels = }')
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
            txt_labels = [f"CAT {cat:02d}  {score:.2f}" for cat in pil_labels]
        else:
            txt_labels = [f"{cat_names[cat-1]}  {score:.2f}" for cat, score in zip( pil_labels, pil_scores)]
        #print( 'text labels', txt_labels)
        # Annotate the sample image with labels and bounding boxes
        annotated_tensor = draw_bboxes(
            image=image, 
            boxes=pred['boxes'], 
            labels=txt_labels, 
            colors=int_colors,
        )
        pil_image = functional.to_pil_image( annotated_tensor, mode='RGB')
        plt.imshow(pil_image)
        plt.axis('off')
        if epoch != None:
            pil_image.save( f"Test-Images/Epoch-{epoch:04d}-{file_name}.png")
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
import argparse

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


#app = QtWidgets.QApplication(sys.argv)
#w = MainWindow()
#app.exec()

from PIL import Image, ImageDraw
import matplotlib
import matplotlib.pyplot as plt
from functools import partial
from distinctipy import distinctipy
from torchvision.models.detection import fasterrcnn_resnet50_fpn, FasterRCNN_ResNet50_FPN_Weights
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision.models.detection.mask_rcnn import maskrcnn_resnet50_fpn, MaskRCNN_ResNet50_FPN_Weights
from torchvision.models.detection.mask_rcnn import MaskRCNNPredictor
from engine import train_one_epoch, evaluate
import utils
 
def config_mask_model( model, class_cnt):
    in_features_box = model.roi_heads.box_predictor.cls_score.in_features
    in_features_mask = model.roi_heads.mask_predictor.conv5_mask.in_channels
    out_chanels_mask = model.roi_heads.mask_predictor.conv5_mask.out_channels
    model.roi_heads.box_predictor = MaskRCNNPredictor(in_channels=in_features_box, num_classes=class_cnt)
    new_in_features_box = model.roi_heads.box_predictor.cls_score.in_features
    new_in_features_mask = model.roi_heads.mask_predictor.conv5_mask.in_channels
    new_out_chanels_mask = model.roi_heads.mask_predictor.conv5_mask.out_channels
    print( 'in_features_box', in_features_box, '->', new_in_features_box,
           'in_features_mask', in_features_mask, '->', new_in_features_mask,
           'out_chanels_mask', out_chanels_mask, '->', new_out_chanels_mask)
    return model

def config_fast_model( model, class_cnt):
    in_features_box = model.roi_heads.box_predictor.cls_score.in_features
    model.roi_heads.box_predictor = FastRCNNPredictor(in_channels=in_features_box, num_classes=class_cnt)
    new_in_features_box = model.roi_heads.box_predictor.cls_score.in_features
    print( f"{in_features_box = } -> {new_in_features_box = } / {class_cnt = }")
    return model

def load_lav_coco(split):
    assert split == 'train' or split == 'val'
    ann_file=f'LAV/{split}.json'
    coco = COCO(ann_file)
    cats_ids = coco.getCatIds()
    print( 'Categories count', len(cats_ids), 'max', max(cats_ids))
    #print(f"{coco.loadCats(cats_ids) = }")
    category_names = [coco.loadCats([cat])[0]['name'] for cat in cats_ids]
    coco_set = CocoDetection( root='.', annFile=ann_file, transforms=transforms ) #, target_transform )
    coco_set = wrap_dataset_for_transforms_v2(coco_set, target_keys=("boxes", "labels", "iscrowd", "image_id"))
    #print( f"lav_coco {coco_set = } {len(coco_set) = }")
    #sample = coco_set[0]
    #img, target = sample
    #print(f"coco_torch {type(img) = }\n{type(target) = }\n{target.keys() = }\n{target.values() = }")
    #print()
    return coco_set, cats_ids, category_names

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

def load_categories(dset):
    match dset:
        case 'coco_torch':
            ann_file, ids_file, imagedir = libDloadCoco.download_coco_files( 'train', '2014')
            coco_set = CocoDetection( root=imagedir, annFile=ann_file, transforms=transforms) # target_transform )
            #sample = coco_set[0]
            #img, target = sample
            #print(f"{type(img) = }\n{type(target) = }\n{type(target[0]) = }\n{target[0].keys() = }")
            coco_set_train = wrap_dataset_for_transforms_v2(coco_set, target_keys=("boxes", "labels", "masks"))
            ann_file, ids_file, imagedir = libDloadCoco.download_coco_files( 'val', '2014')
            coco_set = CocoDetection( root=imagedir, annFile=ann_file, transforms=transforms) # target_transform )
            #sample = coco_set[0]
            #img, target = sample
            #print(f"{type(img) = }\n{type(target) = }\n{type(target[0]) = }\n{target[0].keys() = }")
            coco_set_val = wrap_dataset_for_transforms_v2(coco_set, target_keys=("boxes", "labels", "masks"))

        case 'own_coco':
            image_size = 256 # 513
            ann_file, ids_file, imagedir = libDloadCoco.download_coco_files( 'train', '2014')
            coco_set_train = libDsetCoco.COCOSegmentation( ann_file, ids_file, imagedir, split='train', image_size=image_size)
            ann_file, ids_file, imagedir = libDloadCoco.download_coco_files( 'val', '2014')
            coco_set_val = libDsetCoco.COCOSegmentation( ann_file, ids_file, imagedir, split='val', image_size=image_size)

        case 'lav_coco':
            coco_set_train, cats_ids_train, category_names_train = load_lav_coco('train')
            coco_set_val, cats_ids_val, category_names_val = load_lav_coco('val')
            assert cats_ids_train == cats_ids_val
            assert category_names_train == category_names_val
            category_names = category_names_train 
            cats_ids = cats_ids_train
            num_classes = 1 + max(cats_ids)
    return category_names, cats_ids, num_classes, coco_set_train, coco_set_val

def load_dloader(dset):
    category_names, cats_ids, num_classes, coco_set_train, coco_set_val = load_categories(dset)
    if False:
        print(f"{type(coco_set) = }  {len(coco_set) = }")
        sample = coco_set[0]
        print(f"{type(sample) = }  {len(sample) = }")
        img, target = sample
        #print(f"target {target}")
        print(f"{type(img) = }\n{type(target) = }\n{target.keys() = }")
        print(f"{target['boxes'].shape = }\n{target['labels'].shape = }\n{target['image_id'] = }")
        #print(f"{type(target['boxes']) = }\n{type(target['labels']) = }\n{type(target['image_id']) = }")
        plot_sample( sample)

    train_loader = torch.utils.data.DataLoader(
        coco_set_train,
        batch_size=4,
        # We need a custom collation function here, since the object detection
        # models expect a sequence of images and target dictionaries. The default
        # collation function tries to torch.stack() the individual elements,
        # which fails in general for object detection, because the number of bounding
        # boxes varies between the images of the same batch.
        collate_fn=lambda batch: tuple(zip(*batch)),
    )
    val_loader = torch.utils.data.DataLoader(
        coco_set_val,
        batch_size=2,
        # We need a custom collation function here, since the object detection
        # models expect a sequence of images and target dictionaries. The default
        # collation function tries to torch.stack() the individual elements,
        # which fails in general for object detection, because the number of bounding
        # boxes varies between the images of the same batch.
        collate_fn=lambda batch: tuple(zip(*batch)),
    )
    return category_names, cats_ids, num_classes, train_loader, val_loader

def get_test_files(root_dir):
    test_files = []
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.lower().endswith(('.jpeg', '.jpg')):
                test_files.append( os.path.join( root, file))
    #print( f"{test_files = }")
    return test_files

def load_model( mask_model, checkpath):
             #maskrcnn_resnet50_fpn(                  weights=MaskRCNN_ResNet50_FPN_Weights.DEFAULT)
    #weights = MaskRCNN_ResNet50_FPN_Weights.COCO_V1
    #weights = FasterRCNN_ResNet50_FPN_Weights.DEFAULT
    #fasterrcnn_resnet50_fpnmodel = maskrcnn_resnet50_fpn( pretrained=True, weights=weights)
    #model = config_fast_model( model, 1+len(category_names))
    #model = config_fast_model( model, 1+len(category_names))

    last_epoch = 0
    category_names = None
    optimizer_state = None
    if mask_model:
        model = torchvision.models.get_model("maskrcnn_resnet50_fpn_v2", weights=None, weights_backbone=None)
    else:
        if checkpath is None:
            weights = FasterRCNN_ResNet50_FPN_Weights.COCO_V1
            print( f"F{weights.meta.keys() = }")
            category_names = weights.meta["categories"]
            model = fasterrcnn_resnet50_fpn( weights=weights)
        else:
            checkpoint_dict = torch.load( checkpath, weights_only=True)
            last_epoch = checkpoint_dict['epoch']
            category_names = checkpoint_dict['classes']
            model = fasterrcnn_resnet50_fpn( num_classes=1+len(category_names))
            model.load_state_dict( checkpoint_dict['model_state_dict'])
            optimizer_state = checkpoint_dict['optimizer_state_dict']
        print( f"FastRCNN Model loaded categories {len(category_names) = }")
    return model, last_epoch, category_names, optimizer_state

def merge_cats( dset_category_names, model_category_names):
    print( f" {dset_category_names = }")
    print( f"{model_category_names = }")
    merged_categories = []
    new_cats = []
    for cat in dset_category_names:
        if cat not in model_category_names:
            new_cats.append( cat)
    print( f"   {new_cats = }")
    for cat in model_category_names:
        if cat in dset_category_names: # and cat != '__none__':
            merged_categories.append( cat)
        else:
            if len( new_cats) > 0:
                n_cat = new_cats.pop()
                print( f" DEL {cat} -> NEW {n_cat}")
                merged_categories.append( n_cat)
            else:
                print( f" DEL {cat} -> __none__")
                merged_categories.append( '__none__')
    for cat in new_cats:
        print( f" NEW {cat}")
        merged_categories.append( cat)
    return merged_categories

def train_main( dset, checkpoint_file, mask_model, num_epochs):
    model, last_epoch, loaded_category_names, optimizer_state = load_model( mask_model, checkpoint_file)
    category_names, _, num_classes, train_loader, val_loader = load_dloader(dset)
    category_names = merge_cats( category_names, loaded_category_names)
    #print( f"train_main {category_names = }")
    model.train()

    # construct an optimizer
    params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.SGD(
        params,
        lr=0.005,
        momentum=0.9,
        weight_decay=0.0005
    )
    if  optimizer_state is not None:
        optimizer.load_state_dict(optimizer_state)

    next_epoch = last_epoch + 1
    loaded_class_cnt = 1+len(loaded_category_names)
    print( f"{next_epoch = } {loaded_class_cnt = }")
    if loaded_class_cnt != num_classes:
        print( f"Change model to {num_classes = }")
        model = config_fast_model( model, num_classes)
    model = config_fast_model( model, num_classes)

    # Loop through each epoch
    for epoch in range(next_epoch, next_epoch+num_epochs):
        print(f"\nEpoch {epoch + 1}/{next_epoch+num_epochs}")

        # Train the model for one epoch, printing status every 25 iterations
        #my_train_one_epoch(model, optimizer, train_loader, epoch, print_freq=5)  # Using train_loader for training
        train_one_epoch(model, optimizer, train_loader, torch.device("cpu"), epoch, print_freq=5)  # Using train_loader for training

        # Evaluate the model on the validation dataset
        coco_evaluator = evaluate(model, val_loader, device=torch.device("cpu"))  # Using val_loader for evaluation
        #print(coco_evaluator.summarize())
        for iou_type, coco_eval in coco_evaluator.coco_eval.items():
            print(f"IoU metric: {iou_type}")
            print(coco_eval.stats)
        print( type( coco_evaluator.coco_eval['bbox']))


        # Optionally, save the model checkpoint after each epoch
        #torch.save(model.state_dict(), f"datasets/fast/model_epoch_{epoch + 1}.pth")
        if os.path.isfile( checkpoint_file):
            os.rename( checkpoint_file, os.path.join( os.path.dirname(checkpoint_file), f"model_checkpoint_epoch_{epoch:03d}.pth"))
            print( f"renamed model_checkpoint_epoch_{epoch = }")
        torch.save({
                    'epoch': epoch,
                    'classes': category_names,
                    'model_state_dict': model.state_dict(),
                    'optimizer_state_dict': optimizer.state_dict(),
                    }, checkpoint_file)
        print( f"saved {epoch+1 = }")

import random

def test_main( checkpoint_file, mask_model):
    model, last_epoch, category_names, _ = load_model( mask_model, checkpoint_file)
    print( f"{last_epoch = }")
    model.eval()
    test_files = get_test_files( 'LAV/LAV_NRW--Abt_Rheinland--PA_3103--29569')
    image_path = random.choice( test_files)
    print( f"{image_path = }")
    image = torchvision.io.read_image(image_path) # .float()
    transform = T.ToDtype(torch.float32, scale=True)
    image = transform( image)
    print( f"{image.shape = }")
    pred_batch_dict = model([image])
    #print( f"{type(pred_batch_dict[0]) = }")
    print( f"{pred_batch_dict[0].keys() = }")
    #plot_prediction( image, pred_batch_dict[0], category_names, epoch=last_epoch, file_name=os.path.basename(image_path))
    gen_labelme_json( image, pred_batch_dict[0], category_names, epoch=last_epoch, file_name=os.path.basename(image_path), min_score=0.8)
    return

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", "-V", action="store_true", help="show version")
    parser.add_argument("--debug", "-D", action="store_true", help="enable debug output")
    parser.add_argument(
        "--test", "-T",
        action="store_true",
        help="select an arbitrary image and run inference on it",
    )
    parser.add_argument(
        "--restart", "-R",
        action="store_true",
        help="Restart training from scratch",
    )
    args = parser.parse_args()

    debug_set=args.debug
    dset='lav_coco' # 'coco_torch' 'own_coco' 'lav_coco'
    model_torch=False
    image_size = 256 # 513
    checkpoint_file = None
    if not args.restart:
        checkpoint_file = "datasets/fast/model_checkpoint.pth"

    if False:
        app = QtWidgets.QApplication(sys.argv)
        w = MainWindow()
        app.exec()

    if args.version:
        print(f"{__appname__} {__version__}")
        return 0

    if args.test:
        test_main( checkpoint_file, model_torch)
        return 0

    # Set the number of epochs for training
    num_epochs = 300
    train_main( dset, checkpoint_file, model_torch, num_epochs)
    return 0


if __name__ == '__main__':
    sys.exit(main())

assert False


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

def display_image_result( i, batch_idx, batches_cnt, image, result, epoch=None, file_name=None):
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
    if epoch != None:
        plt.savefig( f"Test-Images/Epoch-{epoch:04d}-{file_name}.png")
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

