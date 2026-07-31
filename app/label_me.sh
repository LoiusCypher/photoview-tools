#!/bin/bash
labelme
mv LAV/train.json LAV/train.old
mv LAV/val.json LAV/val.old
labelme2coco LAV LAV --train_split_rate 0.90 --category_id_start 1

