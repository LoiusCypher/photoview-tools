# Module Imports
import os
import sys
import argparse

from mylib.PhotoviewObjectServer import PhotoviewObjectServer

from torchvision.transforms import v2
from torchvision.models.detection import MaskRCNN_ResNet50_FPN_Weights, maskrcnn_resnet50_fpn
from torchvision.models.detection import MaskRCNN_ResNet50_FPN_V2_Weights, maskrcnn_resnet50_fpn_v2
import torch
#print("After import torch")

from PIL import Image, ImageOps
import numpy as np

# Root directory of the model
OBJECT_DETECTOR_ROOT_DIR = os.path.abspath("/Mask-RCNN_model")
#print(OBJECT_DETECTOR_ROOT_DIR)

tools_db_name = "object_detector"
photo_db_name = "photoview"

# Import Mask RCNN
sys.path.append(OBJECT_DETECTOR_ROOT_DIR)  # To find local version of the library
from mrcnn import utils
import mrcnn.model as modellib
#from mrcnn import visualize
#print("After import mrcnn")

# Import COCO config
sys.path.append(os.path.join(OBJECT_DETECTOR_ROOT_DIR, "samples/coco/"))  # To find local version
import coco
#print("After import coco")

def load_trained_model_torch():
    # model = maskrcnn_resnet50_fpn(weights=MaskRCNN_ResNet50_FPN_Weights.DEFAULT)
    weights = MaskRCNN_ResNet50_FPN_Weights.COCO_V1
    transforms = weights.transforms()
    category_names = weights.meta["categories"]
    model = maskrcnn_resnet50_fpn(weights=weights)
    model.eval()
    return model, transforms, category_names

def load_trained_model_torch_v2():
    weights = MaskRCNN_ResNet50_FPN_V2_Weights.COCO_V1
    transforms = weights.transforms()
    category_names = weights.meta["categories"]
    model = maskrcnn_resnet50_fpn_v2(weights=weights)
    model.eval()
    return model, transforms, category_names

class InferenceConfig(coco.CocoConfig):
    # Set batch size to 1 since we'll be running inference on
    GPU_COUNT = 1
    IMAGES_PER_GPU = 1

def load_trained_model(object_detector_root_dir):
    # Directory to save logs and trained model
    MODEL_DIR = os.path.join(object_detector_root_dir, "logs")

    # Local path to trained weights file
    #coco_model_path = os.path.join(object_detector_root_dir, "mask_rcnn_coco.h5")
    coco_model_path = os.path.join(MODEL_DIR, "mask_rcnn_coco.h5")
    # Download COCO trained weights from Releases if needed
    if not os.path.exists(coco_model_path):
        utils.download_trained_weights(coco_model_path)

    config = InferenceConfig()
    config.display()

    # Create model object in inference mode.
    model = modellib.MaskRCNN(mode="inference", model_dir=MODEL_DIR, config=config)

    # Load weights trained on MS-COCO
    model.load_weights(coco_model_path, by_name=True)

    return model

def print_results( file_names, results, class_names):
    #print( 'File(s):', file_names, 'results: ', len(results))

    # Print class names
    for file_name, r in zip( file_names, results):
        print( 'File:', file_name)

        #print( 'keys:', len(r.items()), end=" ")
        #for key, value in r.items() :
            #print (key, end=" ")
        #print(' ')

        print( 'labels: ', len(r['labels']), r['labels'])
        print( 'boxes: ', len(r['boxes']), r['boxes'])
        #print( 'masks:', len(r['masks']), len(r['masks'][0]), len(r['masks'][0][0]), r['masks'][0])

        for idx in r['labels'] :
            print( idx, class_names[idx], end=" ")
        print(' ')

        print( 'scores:', len(r['scores']), r['scores'])

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument( "--version", "-V", action="store_true", help="show version")
    parser.add_argument( "--debug", "-D", action="store_true", help="enable debug output")
    parser.add_argument( "--restart", "-R", action="store_true", help="Restart scanning from first file",)
    parser.add_argument( "--detection-remove", "-r", action="store_true", help="Run single inference",)
    parser.add_argument( "--single", "-s", action="store_true", help="Run single inference",)
    parser.add_argument( "--detection-status", "-S", action="store_true", help="Run single inference",)
    args = parser.parse_args()
    print(f"{args.detection_status}")

    db_server = PhotoviewObjectServer( root="root", root_pwd="superphotosecret",
                                       user="photoview", user_pwd="photosecret",
                                       host="192.168.2.227",
                                       tools_db_name=tools_db_name, photo_db_name=photo_db_name)
    if args.detection_status:
        db_server.count_scanned_media_id( 0)
        return 0

    #model = load_trained_model(OBJECT_DETECTOR_ROOT_DIR)
    #model, transformations, classnames = load_trained_model_torch()
    model, transformations, classnames = load_trained_model_torch_v2()
    #print(f"Got model")

    conn = db_server.new_conn()
    if conn is None: return

    detection = 2
    last_id = -1
    #last_id = 1
    #last_id = 2
    if not args.restart:
        print(f"Continue to process files")
        last_id = db_server.get_last_media_id( detection, conn)
        if (last_id != -1):
            last_id, path = next(db_server.get_next_filename( last_id, conn))
            cur = conn.cursor()
            db_server.store_skipped_media_id( detection, last_id, cur)
            db_server.store_scanned_media_id( detection, last_id, cur)
            cur.close()
            conn.commit()
            print(f"Skip: {last_id}, Path: {path}")

    # If not starting from scratch, skip current, because we probably crashed on current
    for media_id, path in db_server.get_next_filename( last_id, conn):
        print(f"ID: {media_id}, Path: {path}")
        if not os.path.isfile(path):
            print(f"Error {path} does not exist")
            return 1

        if args.detection_remove:
            db_server.remove_media_detections( media_id, detection)
            db_server.remove_media_detections( media_id, 1)

        #try:
            #with skimage.io.imread(path) as image:
                #print( type(image), np.dtype(image), image.shape)

        if path.endswith(".mp4") or path.endswith(".svg"):
            db_server.store_skipped_media_id( media_id, conn)
            conn.commit()
            print(f"Skipping: {media_id}, Path: {path}")
            continue

        # Open the image
        pil_img = Image.open(path)
        #print( f"pil_img        {type(pil_img) = } {pil_img.mode = } {pil_img.size = }")

        # Automatically read EXIF tags and transpose the image correctly
        #pil_img_trans = ImageOps.exif_transpose(pil_img)
        #print( f"pil_img_trans {type(pil_img_trans) = } {pil_img_trans.mode = } {pil_img_trans.size = }")
        #match pil_img_trans.mode:
            #case "1" | "P" | "I" | "L" | "RGBA":
                #pil_img_trans = pil_img_trans.convert("RGB")
                #print( "pil_img_trans convert to RGB", type(pil_img_trans), pil_img_trans.mode)

        tensor_img_oriented = transformations( ImageOps.exif_transpose( pil_img))
        #print( "tensor_img_oriented:", type(tensor_img_oriented), type(tensor_img_oriented[0]), tensor_img_oriented.dtype, tensor_img_oriented.shape)
        result = model([tensor_img_oriented])[0]

        cur = conn.cursor()
        # print( f"media_id: {media_id}  Width: {width} Height: {height}")
        for box, label, score in zip( result['boxes'], result['labels'], result['scores']):
            if score > 0.9:
                width = tensor_img_oriented.shape[2]
                height = tensor_img_oriented.shape[1]
                print(f"  {detection = } {classnames[label]:20s} {width = } {height = } {score = }")
                #print(f"  {box = }")
                min0 = min(box[0],box[2])
                min1 = min(box[1],box[3])
                max0 = max(box[0],box[2])
                max1 = max(box[1],box[3])
                rect = f"{min0/width:8.6f}:{max0/width:8.6f}:{min1/height:8.6f}:{max1/height:8.6f}"

                face_group_id = db_server.get_face_group_id( classnames[label], cur)
                db_server.store_result( detection, media_id, rect, face_group_id, score, cur)
                #break
            else:
                if score > 0.75:
                    print( f"skipped: {media_id}  {classnames[label]:20s} {score:03f}")
        db_server.store_scanned_media_id( detection, media_id, cur)
        conn.commit()
        #conn.rollback()

        if args.single:
            break

    conn.close()
    return 0

if __name__ == '__main__':
    sys.exit(main())

