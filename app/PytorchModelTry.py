import torchvision
##from torchvision.models import resnet50, ResNet50_Weights
#from torchvision.models import maskrcnn_resnet50_fpn_v2

# Using pretrained weights:
##resnet50(weights=ResNet50_Weights.IMAGENET1K_V1)
##resnet50(weights="IMAGENET1K_V1")

# Using no weights:
##resnet50(weights=None)
##resnet50()

######## COCO 1 ----------------

from pycocotools.coco import COCO
from pycocotools import mask as coco_mask
from torch.utils.data import Dataset

from torchvision.datasets import CocoDetection
#import torchvision.datasets.CocoDetection(root: Union[str, Path], annFile: str, transform: Optional[Callable] = None, target_transform: Optional[Callable] = None, transforms: Optional[Callable] = None)

import keras
from torchvision.datasets import CocoDetection

#cap_val2017_data = CocoDetection(
    #root="datasets/val2017_extracted/val2017",
    #annFile="datasets/annotations_trainval2017_extracted/annotations/captions_val2017.json"
#)
#print('cap_val2017_data:', cap_val2017_data)
#dataset_iter = iter(cap_val2017_data)
#print(next(dataset_iter))

import os
import torch
import torchvision.transforms.v2 as T
from torchvision.io import decode_image
from torchvision.utils import draw_bounding_boxes

image_size = 256 # 513

class COCOSegmentation(Dataset):
    #CAT_LIST = [0, 5, 2, 16, 9, 44, 6, 3, 17, 62, 21, 67, 18, 19, 4, 1, 64, 20, 63, 7, 72]
    #NUM_CLASSES = len(CAT_LIST)
    #NUM_CLASSES = 130
    #CAT_LIST = [c_idx for c_idx in range(NUM_CLASSES)]

    def __init__(self,
                 image_size=513,
                 base_dir='coco', # Path.db_root_dir('coco'),
                 split='train',
                 year='2017'):
        super().__init__()
        assert year == '2017'
        assert split == 'val' or split == 'train' or split == 'test'
        self.split = split
        if split == 'val' or split == 'train':
            zip_name = f"annotations_trainval{year}.zip"
        annotdir = keras.utils.get_file(
            fname=zip_name,
            origin=f"http://images.cocodataset.org/annotations/{zip_name}",
            extract=True,
            archive_format="zip",  # downloaded file format
            cache_dir=".",  # cache and extract in current directory
        )
        ann_file = os.path.join( annotdir, 'annotations/instances_{}{}.json'.format(split, year))
        #print(ann_file)
        ids_file = os.path.join( annotdir, 'annotations/{}_ids_{}.pth'.format(split, year))
        #print(ids_file)

        zip_name=f'{split}{year}.zip'
        imagedir = keras.utils.get_file(
            fname=zip_name,
            origin=f"http://images.cocodataset.org/zips/{zip_name}",
            extract=True,
            archive_format="zip",  # downloaded file format
            cache_dir=".",  # cache and extract in current directory
        )
        self.imagedir = os.path.join( imagedir, '{}{}'.format(split, year))
        #print(self.imagedir)
        self.coco = COCO(ann_file)
        cats_ids = self.coco.getCatIds()
        print( 'Categories count', len(cats_ids)+1, 'max', max(cats_ids))
        self.NUM_CLASSES = max(cats_ids) + 1
        self.CAT_LIST = [c_idx for c_idx in range(self.NUM_CLASSES)]
        #self.coco_mask = mask
        if os.path.exists(ids_file):
            self.ids = torch.load(ids_file)
        else:
            ids = list(self.coco.imgs.keys())
            self.ids = self._preprocess(ids, ids_file)
        self.image_size = image_size

    def __getitem__(self, index):
        _img, _target = self._make_img_gt_point_pair(index)
        #sample = {'image': _img, 'label': _target}
        sample = {'image': _img, 'target': _target}

        if self.split == "train":
            return self.transform_tr(sample)
        elif self.split == 'val':
            return self.transform_val(sample)

    from PIL import Image

    def _make_img_gt_point_pair(self, index):
        coco = self.coco
        img_id = self.ids[index]
        img_metadata = coco.loadImgs(img_id)[0]
        path = img_metadata['file_name']
        #_img = Image.open(os.path.join(self.imagedir, path)).convert('RGB')
        _img = decode_image(os.path.join(self.imagedir, path), mode="RGB")
        #print( '_img', _img, _img.shape)
        cocotarget = coco.loadAnns(coco.getAnnIds(imgIds=img_id))
        #_target = Image.fromarray(self._gen_seg_mask(
        if True:
            _target = { #
                'labels': torch.tensor( [ instance['category_id'] for instance in cocotarget ], dtype=torch.long),
                'masks': self._gen_seg_mask( cocotarget, img_metadata['height'], img_metadata['width']),
                'boxes': torch.Tensor(
                         [ [ instance['bbox'][1],
                             instance['bbox'][0],
                             instance['bbox'][1]+instance['bbox'][3],
                             instance['bbox'][0]+instance['bbox'][2]
                           ] for instance in cocotarget ]
                ),
            }
        if True:
            # Extract segmentation masks, bounding boxes and labels from annotations
            boxes = []  # List to store bounding boxes
            labels = []  # List to store category labels
            masks = []  # List to store segmentation masks
            for ann in cocotarget:
                xmin, ymin, w, h = ann['bbox']  # Get bounding box in COCO format (x, y, width, height)
                boxes.append([xmin, ymin, xmin + w, ymin + h])  # Append box in (xmin, ymin, xmax, ymax) format
                labels.append(ann['category_id'])  # Append category ID
                mask = self.coco.annToMask(ann)  # Convert segmentation to binary mask
                masks.append(mask)  # Append mask
            # Convert annotations to PyTorch tensors
            boxes = torch.as_tensor(boxes, dtype=torch.float32)  # Bounding boxes as float tensors
            labels = torch.as_tensor(labels, dtype=torch.int64)  # Labels as int64 tensors
            masks = torch.as_tensor(masks, dtype=torch.uint8)  # Masks as uint8 tensors
            area = torch.as_tensor([ann['area'] for ann in cocotarget], dtype=torch.float32)  # Area of each object
            iscrowd = torch.as_tensor([ann.get('iscrowd', 0) for ann in cocotarget], dtype=torch.int64)  # Crowd annotations
            # store everything in a dictionary
            _target = {
                "boxes": boxes,  # Bounding boxes
                "labels": labels,  # Object labels
                "masks": masks,  # Segmentation masks
                "image_id": img_id,  # Image ID
                "area": area,  # Area of each object
                "iscrowd": iscrowd  # Crowd flags
            }
        #print( '_target', _target, _target.shape)
        return _img, _target

    def _preprocess(self, ids, ids_file):
        print("Preprocessing mask, this will take a while. " + \
              "But don't worry, it only run once for each split.")
        #tbar = trange(len(ids))
        tbar = range(len(ids))
        new_ids = []
        for i in tbar:
            img_id = ids[i]
            cocotarget = self.coco.loadAnns(self.coco.getAnnIds(imgIds=img_id))
            img_metadata = self.coco.loadImgs(img_id)[0]
            mask = self._gen_seg_mask(cocotarget, img_metadata['height'], img_metadata['width'])
            # more than 1k pixels
            if (mask > 0).sum() > 1000:
                new_ids.append(img_id)
            #tbar.set_description('Doing: {}/{}, got {} qualified images'. \
                                 #format(i, len(ids), len(new_ids)))
        print('Found number of qualified images: ', len(new_ids))
        torch.save(new_ids, ids_file)
        return new_ids


    def _gen_seg_mask(self, target, h, w, item='segmentation'):
    #def _gen_seg_mask(self, target, h, w, item='bbox'):
        #print('new mask', h, w)
        #mask = np.zeros((h, w), dtype=np.uint8)
        mask = torch.zeros((h, w))
        #coco_mask = self.coco_mask
        for instance in target:
            # 'segmentation', 'area', 'iscrowd', 'image_id', 'bbox', 'category_id', 'id'
            #print(instance.keys())
            #print( 'image_id', instance['image_id'])
            #print( f"category_id {instance['category_id']:02d}", end=' ')
            category_info = self.coco.loadCats(instance['category_id'])
            category_name = category_info[0]['name']
            #print( f"cat info {category_info}", end=' ')
            #print( f"{category_name:10s}", end=' ')
            #print( f"bbox {instance['bbox']}")
            #print( 'segmentation', instance['segmentation'])
            #print( 'area', instance['area'])
            #print( 'iscrowd', instance['iscrowd'])
            rle = coco_mask.frPyObjects(instance['segmentation'], h, w)
            #print("segm rle", rle, 'cat', instance['category_id'], category_name)
            m = torch.from_numpy(coco_mask.decode(rle))
            #print("segm mask shspe", m.shape)
            #print("segm mask", m)
            cat = instance['category_id']
            if cat in self.CAT_LIST:
                c = self.CAT_LIST.index(cat)
            else:
                continue
            if len(m.shape) < 3:
                mask[:, :] += (mask == 0) * (m * c)
            else:
                #mask[:, :] += (mask == 0) * (((np.sum(m, axis=2)) > 0) * c).astype(np.uint8)
                mask[:, :] += (mask == 0) * (((torch.sum(m, dim=2)) > 0) * c).type(torch.uint8)
            #print("final mask shape", mask.shape)
            #print("final mask", mask)
        return T.ToImage()(mask).type(torch.uint8)

    def transform_val(self, sample):
        #composed_transforms = transforms.Compose([
            #tr.FixScaleCrop(crop_size=self.args.crop_size),
            #tr.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
            #tr.ToTensor()])
        composed_transforms = T.Compose([
            T.Resize((self.image_size,self.image_size)),
            T.ToImage(),
            T.ToDtype(torch.float32, scale=True), 
        ])
        #print('transform Image before', sample['image'], sample['image'].shape)
        #print('transform label before', sample['label'], sample['label'].shape)
        if False:
            #trans_lab = composed_transforms(sample['label'])
            trans_lab = composed_transforms(sample['mask'])
            print('transform lab', trans_lab, trans_lab.shape)
        try:
            keys = sample.keys()
        except (AttributeError, TypeError):
            sample = composed_transforms(sample)
        else: # no exception raised
            sample['image'] = composed_transforms(sample['image'])
            #for key in sample['target'].keys():
                ##print('key', key)
                #if key == 'masks':
                    #sample['target'][key] = composed_transforms(sample['target'][key])
        #print('transform Image after', sample['image'], sample['image'].shape)
        #print('transform label after', sample['label'], sample['label'].shape)
        return sample

    def transform_tr(self, sample):
        composed_transforms = transforms.Compose([
            tr.RandomHorizontalFlip(),
            tr.RandomScaleCrop(base_size=self.args.base_size, crop_size=self.args.crop_size),
            tr.RandomGaussianBlur(),
            tr.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
            tr.ToTensor()])

        return composed_transforms(sample)

    def __len__(self):
        return len(self.ids)


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

coco_set = COCOSegmentation( year='2017', split='val', image_size=image_size)

print( 'Dataset size', len(coco_set))
#print( coco_set.NUM_CLASSES, len(coco_set.CAT_LIST))
#print( coco_set[0])

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

batch_size=4

# Create the DataLoader with your collate_fn
dataset_iter = DataLoader(
    coco_set,
    batch_size=batch_size,
    shuffle=True,
    collate_fn=coco_collate_fn
)

print_batch(dataset_iter)

######## COCO 1 ================

def run_inference_batch(model, images):
    #print('shape', images[0].shape), targets[0].shape)
    results = model( images)
    return results

def print_batch_results( batch_idx, batches_cnt, results):
    print('batch loop', batch_idx + 1, '/', batches_cnt, ':', len(results), results[0].keys())
    print('      labels', len(results[0]['labels']), results[0]['labels'])
    print('      scores', len(results[0]['scores']), results[0]['scores'])
    print('      boxes ', len(results[0]['boxes']), results[0]['boxes'][0])
    print('      masks ', len(results[0]['masks']), results[0]['masks'].shape)

from torchvision.utils import save_image

def print_batch_targets( batch_idx, images, targets, save_mask=False):
    for j in range(len(targets)):
        print('shape', batch_idx, j, targets[j].shape)
        save_image( images[j], f'./debug/b{batch_idx:04d}_i{j:04d}_b.jpg')
        non_black_mask = (targets[j] > 1e-5).any(dim=0)
        targets[j][:, non_black_mask] = 255 # 1.0
        if save_mask:
            save_image( targets[j], f'./debug/b{batch_idx:04d}_i{j:04d}_m.png')

def run_inference(model, dataloader, batches_cnt):
    for i, (images, targets) in enumerate( dataloader):
        #print('Batch Loop', i, images, targets)
        #print('Batch Loop', i, len(images), len(targets))
        print_batch_targets( i, images, targets, save_mask=True)
        results = run_inference_batch( model, images)
        print_batch_results( i, batches_cnt, results)

import math

debug_loss=True

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
    #progress_bar = tqdm(total=len(dataloader), desc="Train" if is_training else "Eval")  # Initialize a progress bar
    
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
                #print( ' ', key, val, sum(val))
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
        #progress_bar_dict = dict(loss=loss_item, avg_loss=epoch_loss/(batch_id+1))
        #if is_training:
            #progress_bar_dict.update(lr=lr_scheduler.get_last_lr()[0])
        #progress_bar.set_postfix(progress_bar_dict)
        #progress_bar.update()
        print('batch', batch_id, 'done')

        # If loss is NaN or infinity, stop training
        if is_training:
            stop_training_message = f"Loss is NaN and infinite at epoch {epoch_id}, batch {batch_id}. Stopping training."
            assert not math.isnan(loss_item) or math.isfinite(loss_item), stop_training_message
            assert not math.isnan(loss_item), f"Loss is NaN epoch {epoch_id}, batch {batch_id}. Stopping training."
            assert math.isfinite(loss_item), f"Loss is infinite at epoch {epoch_id}, batch {batch_id}. Stopping training."

    # Cleanup and close the progress bar 
    #progress_bar.close()
    
    # Return the average loss for this epoch
    return epoch_loss / (batch_id + 1)

if False:
    print( 'detection', torchvision.models.list_models(module=torchvision.models.detection))
    print( 'detection.mask_rcnn', torchvision.models.list_models(module=torchvision.models.detection.mask_rcnn))

from torchvision.models.detection.mask_rcnn import maskrcnn_resnet50_fpn, MaskRCNN_ResNet50_FPN_Weights
#maskrcnn_resnet50_fpn(weights=MaskRCNN_ResNet50_FPN_Weights.DEFAULT)
model = maskrcnn_resnet50_fpn(weights=MaskRCNN_ResNet50_FPN_Weights.COCO_V1)

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
    images, first = next( iter( dataset_iter))
    results = model( images)
    print('test', len(results), results[0])

batches_cnt = 1 + (len(coco_set) - 1) // batch_size

#run_inference(model, dataset_iter, batches_cnt)

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

