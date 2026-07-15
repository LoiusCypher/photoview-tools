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
from pycocotools import mask
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

image_size = 514

class COCOSegmentation(Dataset):
    NUM_CLASSES = 21
    CAT_LIST = [0, 5, 2, 16, 9, 44, 6, 3, 17, 62, 21, 67, 18, 19, 4, 1, 64, 20, 63, 7, 72]

    def __init__(self,
                 image_size=513,
                 base_dir='coco', # Path.db_root_dir('coco'),
                 split='train',
                 year='2017'):
        super().__init__()
        assert year == '2017'
        assert split == 'val' or split == 'train' or split == 'test'
        self.split = split
        zip_name = f"annotations_trainval2017.zip"
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
        self.coco_mask = mask
        if os.path.exists(ids_file):
            self.ids = torch.load(ids_file)
        else:
            ids = list(self.coco.imgs.keys())
            self.ids = self._preprocess(ids, ids_file)
        self.image_size = image_size

    def __getitem__(self, index):
        _img, _target = self._make_img_gt_point_pair(index)
        sample = {'image': _img, 'label': _target}

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
        _target = self._gen_seg_mask(
            cocotarget, img_metadata['height'], img_metadata['width'])
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
            mask = self._gen_seg_mask(cocotarget, img_metadata['height'],
                                      img_metadata['width'])
            # more than 1k pixels
            if (mask > 0).sum() > 1000:
                new_ids.append(img_id)
            #tbar.set_description('Doing: {}/{}, got {} qualified images'. \
                                 #format(i, len(ids), len(new_ids)))
        print('Found number of qualified images: ', len(new_ids))
        torch.save(new_ids, ids_file)
        return new_ids

    def _gen_seg_mask(self, target, h, w):
        #mask = np.zeros((h, w), dtype=np.uint8)
        mask = torch.zeros((h, w))
        coco_mask = self.coco_mask
        for instance in target:
            rle = coco_mask.frPyObjects(instance['segmentation'], h, w)
            m = torch.from_numpy(coco_mask.decode(rle))
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
        return mask

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
        #trans = composed_transforms(sample)
        #print('transform Image after', trans['image'], trans['image'].shape)
        #print('transform label after', trans['label'], trans['label'].shape)
        return composed_transforms(sample)

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
        target = elem['label']
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

#print( coco_set[0])
print( 'Dataset size', len(coco_set))

batch_size=2

# Create the DataLoader with your collate_fn
dataset_iter = DataLoader(
    coco_set,
    batch_size=batch_size,
    shuffle=True,
    collate_fn=coco_collate_fn
)

if True:
        images, targets = next( dataset_iter)
        print('iter images.shape',len(images),'len(targets)',len(targets))
        print('iter images[0].shape',images[0].shape)
        print('iter images[0].shape[-2:]',images[0].shape[-2:])
        #images, targets = next(dataset_iter)
        print('iter len(targets)',len(targets))
        #print(targets[0].keys())
        #print('iter targets[0]',targets[0])
        print('iter len(targets[0])',len(targets[0]))
        #print(targets[0][0])
        #print()
        #print(targets[1][0].keys())
        print()

######## COCO 1 ================

if False:
    print( 'detection', torchvision.models.list_models(module=torchvision.models.detection))
    print( 'detection.mask_rcnn', torchvision.models.list_models(module=torchvision.models.detection.mask_rcnn))

from torchvision.models.detection.mask_rcnn import maskrcnn_resnet50_fpn, MaskRCNN_ResNet50_FPN_Weights
maskrcnn_resnet50_fpn(weights=MaskRCNN_ResNet50_FPN_Weights.DEFAULT)
model = maskrcnn_resnet50_fpn(weights=MaskRCNN_ResNet50_FPN_Weights.COCO_V1)

model.eval()
print('before evaluate')
if False:
    images, first = next( iter( dataset_iter))
    results = model( images)
    print('test', len(results), results[0])

batches_cnt = 1 + (len(coco_set) - 1) // batch_size

for i, (images, targets) in enumerate( dataset_iter):
    #print('Batch Loop', i, images, targets)
    #print('Batch Loop', i, len(images), len(targets))
    #print('shape', images[0].shape)
    results = model( images)
    print('batch loop', i + 1, '/', batches_cnt, ':', len(results), results[0].keys())
    print('      labels', len(results[0]['labels']), results[0]['labels'])
    print('      scores', len(results[0]['scores']), results[0]['scores'])
    print('      boxes ', len(results[0]['boxes']), results[0]['boxes'][0])
    print('      masks ', len(results[0]['masks']), results[0]['masks'].shape)

from torchvision.models.detection.mask_rcnn import maskrcnn_resnet50_fpn_v2, MaskRCNN_ResNet50_FPN_V2_Weights
maskrcnn_resnet50_fpn_v2(weights=MaskRCNN_ResNet50_FPN_V2_Weights.DEFAULT)
maskrcnn_resnet50_fpn_v2(weights=MaskRCNN_ResNet50_FPN_V2_Weights.COCO_V1)

