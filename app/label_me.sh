#!/bin/bash
labelme && (
mv -f LabelmeCoco/train.json LabelmeCoco/train.old
mv -f LabelmeCoco/val.json LabelmeCoco/val.old
mv -f LabelmeCoco/dataset.json LabelmeCoco/dataset.old
labelme2coco LAV LabelmeCoco --category_id_start 1                         # smaller datasets will not be splitted
mv -f LabelmeCoco/dataset.json LabelmeCoco/dataset.curr
labelme2coco LAV LabelmeCoco --category_id_start 1 --train_split_rate 0.80 # split bigger datasets
mv -f LabelmeCoco/dataset.curr LabelmeCoco/dataset.json
)

