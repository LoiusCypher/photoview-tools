import os
import shlex
import sys

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
#dataset_iter = cap_val2017_data
#print(next(dataset_iter))

import torch
import torchvision.transforms.v2 as T
from torchvision.io import decode_image
from torchvision.utils import draw_bounding_boxes
from torchvision.transforms import functional

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvas
from matplotlib.figure import Figure
from PIL import Image, ImageDraw
from functools import partial
from distinctipy import distinctipy
import random

class COCOSegmentation(Dataset):

    def __init__(self,
                 ann_file, ids_file, imagedir,
                 image_size=513,
                 split='train'):
        super().__init__()
        assert split == 'val' or split == 'train' or split == 'test'
        self.split = split
        assert os.path.exists(imagedir)
        self.imagedir = imagedir
        assert os.path.exists(ann_file)
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


    def __iter__(self):
        return iter(range(self.start, self.end))

    def __getitem__(self, index):
        _img, _target = self._make_img_gt_point_pair(index)
        #sample = {'image': _img, 'label': _target}
        #sample = {'image': _img, 'target': _target}
        sample = ( _img, _target)

        if self.split == "train":
            return self.transform_tr(sample)
        elif self.split == 'val':
            return self.transform_val(sample)

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
            #T.Resize((self.image_size,self.image_size)),
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
        #composed_transforms = transforms.Compose([
            #tr.RandomHorizontalFlip(),
            #tr.RandomScaleCrop(base_size=self.args.base_size, crop_size=self.args.crop_size),
            #tr.RandomGaussianBlur(),
            #tr.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
            #tr.ToTensor()])
        #return composed_transforms(sample)
        return self.transform_val(sample)

    def __len__(self):
        return len(self.ids)

    def loadCats(self, catIds):
        print( 'loadCats catIds', catIds)
        return self.coco.loadCats(catIds)

    def cat_name(self, cat_id):
        #print( 'cat_name cat_id', cat_id)
        return self.coco.loadCats(cat_id)[0]['name']

    def create_polygon_boxes( self, image_size, boxes):
        """
        Create a grayscale image with a white polygonal area on a black background.

        Parameters:
        - image_size (tuple): A tuple representing the dimensions (width, height) of the image.
        - vertices (list): A list of tuples, each containing the x, y coordinates of a vertex
                            of the polygon. Vertices should be in clockwise or counter-clockwise order.

        Returns:
        - PIL.Image.Image: A PIL Image object containing the polygonal mask.
        """

        # Create a new black image with the given dimensions
        mask_img = Image.new('L', image_size, 0)
    
        # Draw the polygon on the image. The area inside the polygon will be white (255).
        for idx, box in enumerate( boxes):
            ImageDraw.Draw(mask_img, 'L').polygon(((box[0],box[1]),(box[2],box[1]),(box[2],box[3]),(box[0],box[3])), fill=(round(255*idx/len(boxes))))
        # Return the image with the drawn polygon
        return mask_img


import libDloadCoco

def main() -> int:
    """Echo the input arguments to standard output"""
    phrase = shlex.join(sys.argv)
    print(phrase)
    ann_file, ids_file, imagedir = libDloadCoco.download_coco_files( year='2014', split='val')
    coco_set = COCOSegmentation( ann_file, ids_file, imagedir, split='val')
    print( 'Dataset size', len(coco_set))

    cats_ids = coco_set.coco.getCatIds()
    print( 'Categories count', len(cats_ids)+1, 'NUM_CLASSES(max)', coco_set.NUM_CLASSES)
    #print( len(coco_set.CAT_LIST))
    print( 'Dataset length', len(coco_set))
    img_idx = random.randrange(len(coco_set))
    #print( 'image index to display', img_idx)
    coco_set.display_image_target( img_idx)
    return 0

if __name__ == '__main__':
    sys.exit(main())

