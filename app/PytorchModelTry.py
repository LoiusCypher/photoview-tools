import torchvision
##from torchvision.models import resnet50, ResNet50_Weights
#from torchvision.models import maskrcnn_resnet50_fpn_v2

# Using pretrained weights:
##resnet50(weights=ResNet50_Weights.IMAGENET1K_V1)
##resnet50(weights="IMAGENET1K_V1")

# Using no weights:
##resnet50(weights=None)
##resnet50()

from pycocotools.coco import COCO

from torchvision.datasets import CocoDetection
#import torchvision.datasets.CocoDetection(root: Union[str, Path], annFile: str, transform: Optional[Callable] = None, target_transform: Optional[Callable] = None, transforms: Optional[Callable] = None)

import keras

def load_coco(purpose='test'):
    zip_name=f"{purpose}2017.zip"
    path_to_downloaded_file = keras.utils.get_file(
        fname=zip_name,
        origin=f"http://images.cocodataset.org/zips/{zip_name}",
        extract=True,
        archive_format="zip",  # downloaded file format
        cache_dir=".",  # cache and extract in current directory
    )
    print(path_to_downloaded_file)

    zip_name=f"annotations_trainval2017.zip"
    path_to_downloaded_file = keras.utils.get_file(
        fname=zip_name,
        origin=f"http://images.cocodataset.org/annotations/{zip_name}",
        extract=True,
        archive_format="zip",  # downloaded file format
        cache_dir=".",  # cache and extract in current directory
    )
    print(path_to_downloaded_file)

load_coco('val')

#shutil.unpack_archive( os.path.join(download_base_dir, "caltech_101_zipped/caltech-101", "101_ObjectCategories.tar.gz"), ".")

from torchvision.datasets import CocoDetection

#cap_val2017_data = CocoDetection(
    #root="datasets/val2017_extracted/val2017",
    #annFile="datasets/annotations_trainval2017_extracted/annotations/captions_val2017.json"
#)
#print('cap_val2017_data:', cap_val2017_data)
#dataset_iter = iter(cap_val2017_data)
#print(next(dataset_iter))

import torch
import torchvision.transforms.v2 as T

image_size = 512

transforms = T.Compose([
    T.Resize(( image_size, image_size)),
    T.ToImage(),
    T.ToDtype(torch.float32, scale=True), 
])

ins_val2017_data = CocoDetection(
    root="datasets/val2017_extracted/val2017",
    annFile="datasets/annotations_trainval2017_extracted/annotations/instances_val2017.json",
    transform=transforms
)
print('ins_val2017_data:', ins_val2017_data)
print('len:', len(ins_val2017_data))

def coco_collate_fn(batch):
    images = []
    targets = []
    
    #print(len(batch),len(batch[0]),len(batch[0][0]),len(batch[0][1]))
    #print('len(batch),len(batch[0])', len(batch),len(batch[0]))
    for image, target in batch:
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
    #print('images[0].shape',images[0].shape)
    print('len(images)',len(images), 'images[0].shape',images[0].shape)
    return images, targets

collate_fn=lambda x: tuple(zip(*x))

from torch.utils.data import DataLoader

# Create the DataLoader with your collate_fn
dataset_iter = DataLoader(
    ins_val2017_data,
    batch_size=2,
    shuffle=True,
    collate_fn=coco_collate_fn
)

if False:
    #for images, first in dataset_iter:
        images, first = next( dataset_iter)
        print('iter images.shape',len(images),'len(first)',len(first))
        print('iter images[0].shape',images[0].shape)
        print('iter images[0].shape[-2:]',images[0].shape[-2:])
        #first = next(dataset_iter)
        print('iter len(first)',len(first))
        #print(first[0].keys())
        #print('iter first[0]',first[0])
        print('iter len(first[0])',len(first[0]))
        #print(first[0][0])
        #print()
        #print(first[1][0].keys())
        print()
        #break

if False:
    print(len(cap_train2017_data), len(ins_train2017_data), len(pk_train2017_data))
# (118287, 118287, 118287)


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
data_len = len(ins_val2017_data)
for i, (images, first) in enumerate( dataset_iter):
    results = model( images)
    print('loop', i, '/', data_len // dataset_iter.batch_size, ':', len(results), results[0])

from torchvision.models.detection.mask_rcnn import maskrcnn_resnet50_fpn_v2, MaskRCNN_ResNet50_FPN_V2_Weights
maskrcnn_resnet50_fpn_v2(weights=MaskRCNN_ResNet50_FPN_V2_Weights.DEFAULT)
maskrcnn_resnet50_fpn_v2(weights=MaskRCNN_ResNet50_FPN_V2_Weights.COCO_V1)

