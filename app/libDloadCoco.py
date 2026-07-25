import os
import keras

def _expected_extract_dir( zip_name):
        download_dir = './datasets'
        unpacked_dir = os.path.join( download_dir, zip_name.replace( '.zip', '_extracted'))
        #print(unpacked_dir)
        return unpacked_dir

def _download_annotations( split, year):
        if (year == '2014' or year == '2017') and (split == 'val' or split == 'train'):
            zip_name = f"annotations_trainval{year}.zip"
        if (year == '2014' or year == '2015' or year == '2017') and (split == 'test'):
            zip_name = f"image_info_{split}{year}.zip"
        unpacked_dir = _expected_extract_dir( zip_name)
        if not os.path.exists( unpacked_dir):
            unzipdir = keras.utils.get_file(
                fname=zip_name,
                origin=f"http://images.cocodataset.org/annotations/{zip_name}",
                extract=True,
                archive_format="zip",  # downloaded file format
                cache_dir=".",  # cache and extract in current directory
            )
            print(unzipdir)
            assert unpacked_dir == unzipdir
        ann_dir = os.path.join( unpacked_dir, 'annotations')
        ann_file = os.path.join( ann_dir, 'instances_{}{}.json'.format(split, year))
        #print(ann_file)
        ids_file = os.path.join( ann_dir, '{}_ids_{}.pth'.format(split, year))
        #print(ids_file)
        # 'image_info_{}{}'.format(split, year))
        # 'captions_{}{}'.format(split, year))
        # 'person_keypoints_{}{}'.format(split, year))
        return ann_file, ids_file

def _download_images( split, year):
        zip_name=f'{split}{year}.zip'
        unpacked_dir = _expected_extract_dir( zip_name)
        if not os.path.exists( unpacked_dir):
            unzipdir = keras.utils.get_file(
                fname=zip_name,
                origin=f"http://images.cocodataset.org/zips/{zip_name}",
                extract=True,
                archive_format="zip",  # downloaded file format
                cache_dir=".",  # cache and extract in current directory
            )
            assert unpacked_dir == unzipdir
        imagedir = os.path.join( unpacked_dir, '{}{}'.format(split, year))
        #print('imagedir', imagedir)
        return imagedir

def download_coco_files( split, year):
        assert year == '2014' or year == '2015' or year == '2017'
        assert split == 'val' or split == 'train' or split == 'test'
        assert year != '2015' or split == 'test'
        ann_file, ids_file = _download_annotations( split=split, year=year)
        imagedir = _download_images( split=split, year=year)
        #print('imagedir', imagedir)
        return ann_file, ids_file, imagedir

def main() -> int:
    ann_file, ids_file, imagedir = download_coco_files( year='2014', split='train')
    ann_file, ids_file, imagedir = download_coco_files( year='2014', split='val')
    ann_file, ids_file, imagedir = download_coco_files( year='2017', split='train')
    ann_file, ids_file, imagedir = download_coco_files( year='2017', split='val')

    ann_file, ids_file, imagedir = download_coco_files( year='2014', split='test')
    ann_file, ids_file, imagedir = download_coco_files( year='2015', split='test')
    ann_file, ids_file, imagedir = download_coco_files( year='2017', split='test')

    # ann_file, ids_file, imagedir = download_coco_files( year='2015', split='train') # could not find aaotationfiles for these
    # ann_file, ids_file, imagedir = download_coco_files( year='2015', split='val') # could not find aaotationfiles for these

import sys

if __name__ == '__main__':
    sys.exit(main())
