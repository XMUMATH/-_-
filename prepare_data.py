#  Compatibility imports
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
os.environ['CUDA_VISIBLE_DEVICES'] = '0'

import time

import tensorflow as tf
import scipy.io.wavfile as wav
import numpy as np
import pandas as pd

test_inputs_dir = './test_mfcc'
train_inputs_dir = './train_mfcc'


test_data = []
train_data = []
length = 0
#read our data
def data_txt2csv():
    test_listdir =  os.listdir(test_inputs_dir)
    train_listdir =  os.listdir(train_inputs_dir)
    for test_dir in test_listdir:
        with open(test_dir, 'r') as f:
            line = f.read()
    test_data.append(line)
    
    for train_dir in train_listdir:
        with open(train_dir, 'r') as f:
            line = f.read()
    train_data.append(line)


csvFile1 = open('test_mfcc.csv','w', newline='') # 设置newline，否则两行之间会空一行
writer = csv.writer(csvFile1)
m = len(test_data)

for i in range(m):

    writer.writerow(test_data[i])

csvFile1.close()


csvFile2 = open('test_mfcc.csv','w', newline='') # 设置newline，否则两行之间会空一行
writer = csv.writer(csvFile2)
m = len(train_data)

for i in range(m):

    writer.writerow(train_data[i])

csvFile2.close()
