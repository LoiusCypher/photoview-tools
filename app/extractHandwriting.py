# Module Imports
import os
from PIL import Image, ImageOps
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

def extract_all_markings( orig_dir, gen_dir):
    class_files = {}
    # Travers all the branch of a specified path
    for (cur_dir, _, files) in os.walk( orig_dir, topdown=True):
        for file in files:
            if file.endswith('.json'):
                #print('gen', os.path.join( gen_dir, cur_dir[len(orig_dir):])) 
                sub_dir = ''
                if cur_dir != orig_dir:
                    sub_dir = cur_dir[len(orig_dir)+1:]
                class_files = crop_patterns( orig_dir, gen_dir, sub_dir, file, class_files) 
    return class_files

class_files = extract_all_markings( '/handwriting/orig', '/handwriting/generated')
