import horovod.tensorflow.keras as hvd
import tensorflow.keras.backend as K
import tensorflow as tf

from datetime import datetime
import argparse
import os
import numpy as np
import codecs
import json
import boto3

import tensorflow.keras.backend as K
from tensorflow import keras
from tensorflow.keras.layers import Input, Activation, Conv2D, Dense, Dropout, Flatten, MaxPooling2D, BatchNormalization
from tensorflow.keras.models import Model, Sequential
from tensorflow.keras.utils import multi_gpu_model
from tensorflow.keras.optimizers import Adam, SGD, RMSprop
from tensorflow.keras.callbacks import TensorBoard, ModelCheckpoint
from keras.models import load_model


HEIGHT = 150
WIDTH = 150
DEPTH  = 3
NUM_CLASSES = 3
NUM_TRAIN_IMAGES = 9600
NUM_VALID_IMAGES = 1200
NUM_TEST_IMAGES  = 1200

mapper_fruit_names = [1, 2, 3]


class Sync2S3(tf.keras.callbacks.Callback):
    def __init__(self, logdir, s3logdir):
        super(Sync2S3, self).__init__()
        print('Sync2S3 created like a boss!')
        self.logdir = logdir
        self.s3logdir = s3logdir
    
    def on_epoch_end(self, batch, logs={}):
        print('does it run')
        os.system('aws s3 sync '+self.logdir+' '+self.s3logdir)

def single_example_parser(serialized_example):
    """Parses a single tf.Example into image and label tensors."""
   .
    features = tf.io.parse_single_example(
        serialized_example,
        features={
            'image': tf.io.FixedLenFeature([], tf.string),
            'label': tf.io.FixedLenFeature([], tf.int64),
        })
    image = tf.decode_raw(features['image'], tf.uint8)
    image.set_shape([DEPTH * HEIGHT * WIDTH])

    # Reshape from [depth * height * width] to [depth, height, width].
    image = tf.cast(
        tf.transpose(tf.reshape(image, [DEPTH, HEIGHT, WIDTH]), [1, 2, 0]),
        tf.float32)
    label = tf.cast(features['label'], tf.int32)
    
    image = train_preprocess_fn(image)
    label = tf.one_hot(label, NUM_CLASSES)
    
    return image, label

def train_preprocess_fn(image):

    # Resize the image to add four extra pixels on each side.
    image = tf.image.resize_with_crop_or_pad(image, HEIGHT + 8, WIDTH + 8)

    # Randomly crop a [HEIGHT, WIDTH] section of the image.
    image = tf.image.random_crop(image, [HEIGHT, WIDTH, DEPTH])

    # Randomly flip the image horizontally.
    image = tf.image.random_flip_left_right(image)
    return image

def get_dataset(filenames, batch_size):
    """Read the images and labels from 'filenames'."""
    # Repeat infinitely.
    dataset = tf.data.TFRecordDataset(filenames).repeat().shuffle(10000)

    # Parse records.
    dataset = dataset.map(single_example_parser, num_parallel_calls=tf.data.experimental.AUTOTUNE)

    # Batch it up.
    dataset = dataset.batch(batch_size, drop_remainder=True)
    return dataset

def save_history(path, history):

    history_for_json = {}
    # transform float values that aren't json-serializable
    for key in list(history.history.keys()):
        if type(history.history[key]) == np.ndarray:
            history_for_json[key] == history.history[key].tolist()
        elif type(history.history[key]) == list:
           if  type(history.history[key][0]) == np.float32 or type(history.history[key][0]) == np.float64:
               history_for_json[key] = list(map(float, history.history[key]))

    with codecs.open(path, 'w', encoding='utf-8') as f:
        json.dump(history_for_json, f, separators=(',', ':'), sort_keys=True, indent=4) 

def get_model(input_shape, learning_rate, weight_decay, optimizer, momentum, hvd):

#     model = Sequential()
#     model.add(Conv2D(32, (3, 3), padding='same', input_shape=input_shape))
#     model.add(BatchNormalization())
#     model.add(Activation('relu'))
#     model.add(Conv2D(32, (3, 3)))
#     model.add(BatchNormalization())
#     model.add(Activation('relu'))
#     model.add(MaxPooling2D(pool_size=(2, 2)))
#     model.add(Dropout(0.2))

#     model.add(Conv2D(64, (3, 3), padding='same'))
#     model.add(BatchNormalization())
#     model.add(Activation('relu'))
#     model.add(Conv2D(64, (3, 3)))
#     model.add(BatchNormalization())
#     model.add(Activation('relu'))
#     model.add(MaxPooling2D(pool_size=(2, 2)))
#     model.add(Dropout(0.3))

#     model.add(Conv2D(128, (3, 3), padding='same'))
#     model.add(BatchNormalization())
#     model.add(Activation('relu'))
#     model.add(Conv2D(128, (3, 3)))
#     model.add(BatchNormalization())
#     model.add(Activation('relu'))
#     model.add(MaxPooling2D(pool_size=(2, 2)))
#     model.add(Dropout(0.4))

#     model.add(Flatten())
#     model.add(Dense(512))
#     model.add(Activation('relu'))
#     model.add(Dropout(0.5))
#     model.add(Dense(NUM_CLASSES))
#     model.add(Activation('softmax'))

    shape_img = (150,150,3)
    
    model = Sequential()

    model.add(Conv2D(filters=32, kernel_size=(3,3),input_shape=shape_img, activation='relu', padding = 'same'))
    model.add(MaxPooling2D(pool_size=(2, 2)))

    model.add(Conv2D(filters=64, kernel_size=(3,3),input_shape=shape_img, activation='relu', padding = 'same'))
    model.add(MaxPooling2D(pool_size=(2, 2)))

    model.add(Conv2D(filters=64, kernel_size=(3,3),input_shape=shape_img, activation='relu', padding = 'same'))
    model.add(MaxPooling2D(pool_size=(2, 2)))

    model.add(Conv2D(filters=64, kernel_size=(3,3),input_shape=shape_img, activation='relu', padding = 'same'))
    model.add(MaxPooling2D(pool_size=(2, 2)))

    model.add(Conv2D(filters=64, kernel_size=(3,3),input_shape=shape_img, activation='relu', padding = 'same'))
    model.add(MaxPooling2D(pool_size=(2, 2)))

    model.add(Conv2D(filters=64, kernel_size=(3,3),input_shape=shape_img, activation='relu', padding = 'same'))
    model.add(MaxPooling2D(pool_size=(2, 2)))

    model.add(Flatten())

    model.add(Dense(256))
    model.add(Activation('relu'))
    model.add(Dropout(0.5))

    model.add(Dense(NUM_CLASSES))
    model.add(Activation('softmax'))

    size = hvd.size()

    # Change 4: Scale the learning using the size of the cluster (total number of workers)
    if optimizer.lower() == 'sgd':
        opt = SGD(lr=learning_rate * size, decay=weight_decay, momentum=momentum)
    elif optimizer.lower() == 'rmsprop':
        opt = RMSprop(lr=learning_rate * size, decay=weight_decay)
    else:
        opt = Adam(lr=learning_rate * size, decay=weight_decay)

    # Change 5: Wrap your Keras optimizer using Horovod to make it a distributed optimizer
    opt = hvd.DistributedOptimizer(opt)

    model.compile(loss='categorical_crossentropy',
                  optimizer=opt,
                  metrics=['accuracy'])
    
    return model


def main(args):
    # Hyper-parameters
    epochs = args.epochs
    lr = args.learning_rate
    batch_size = args.batch_size
    momentum = args.momentum
    weight_decay = args.weight_decay
    optimizer = args.optimizer

    # SageMaker options
    gpu_count = args.gpu_count
    training_dir = args.train
    validation_dir = args.validation
    eval_dir = args.eval
    tensorboard_logs = args.tensorboard_logs
    
    # Change 2: Initialize horovod and get the size of the cluster
    hvd.init()
    size = hvd.size()
    
    # Change 3 - Pin GPU to local process (one GPU per process)
    config = tf.ConfigProto()
    config.gpu_options.allow_growth = True
    config.gpu_options.visible_device_list = str(hvd.local_rank())
    K.set_session(tf.Session(config=config))
    
    train_dataset = get_dataset(training_dir+'/train.tfrecords',  batch_size)
    val_dataset = get_dataset(validation_dir+'/validation.tfrecords', batch_size)
    eval_dataset = get_dataset(eval_dir+'/eval.tfrecords', batch_size)
    
    input_shape = (HEIGHT, WIDTH, DEPTH)
    
    # Change 6: Add callbacks for syncing initial state, and saving checkpoints only on 1st worker (rank 0)
    callbacks = []
    callbacks.append(hvd.callbacks.BroadcastGlobalVariablesCallback(0))
    callbacks.append(hvd.callbacks.MetricAverageCallback())
    callbacks.append(hvd.callbacks.LearningRateWarmupCallback(warmup_epochs=5, verbose=1))
    callbacks.append(tf.keras.callbacks.ReduceLROnPlateau(patience=10, verbose=1))
    if hvd.rank() == 0:
        callbacks.append(ModelCheckpoint(args.output_data_dir + '/checkpoint-{epoch}.h5'))
        logdir = args.output_data_dir + '/' + datetime.now().strftime("%Y%m%d-%H%M%S")
        callbacks.append(TensorBoard(log_dir=logdir))
        callbacks.append(Sync2S3(logdir=logdir, s3logdir=tensorboard_logs))
    
    model = get_model(input_shape, lr, weight_decay, optimizer, momentum, hvd)
    # To use ResNet model instead of custom model comment the above line and uncomment the following: 
    #model = get_resnet_model(input_shape, lr, weight_decay, optimizer, momentum, hvd)

    # Train model
    # Change 7: Update the number of steps/epoch
    history = model.fit(train_dataset,
                        steps_per_epoch  = (NUM_TRAIN_IMAGES // batch_size) // size,
                        validation_data  = val_dataset,
                        validation_steps = (NUM_VALID_IMAGES // batch_size) // size,
                        verbose          = 1 if hvd.rank() == 0 else 0,
                        epochs           = epochs, callbacks=callbacks)
    
     # creates a HDF5 file 'my_model.h5'

    # returns a compiled model
    # identical to the previous one
    # model = load_model('my_model.h5')
    
    # Evaluate model performance
    score = model.evaluate(eval_dataset,
                           steps=NUM_TEST_IMAGES // args.batch_size,
                           verbose=0)
    
    
    
    print('Test loss    :', score[0])
    print('Test accuracy:', score[1])

    if hvd.rank() == 0:
        save_history(args.output_data_dir + "/hvd_history.p", history)
    callbacks.append(model.save(args.output_data_dir + '/fruit_model.h5'))

if __name__ == "__main__":
    
    # Change 8: Update script to accept hyperparameters as command line arguments
    parser = argparse.ArgumentParser()

    # Hyper-parameters
    parser.add_argument('--epochs',        type=int,   default=15)
    parser.add_argument('--learning-rate', type=float, default=0.001)
    parser.add_argument('--batch-size',    type=int,   default=256)
    parser.add_argument('--weight-decay',  type=float, default=2e-4)
    parser.add_argument('--momentum',      type=float, default='0.9')
    parser.add_argument('--optimizer',     type=str,   default='adam')

    # SageMaker parameters
    parser.add_argument('--output_data_dir',    type=str,   default=os.environ['SM_OUTPUT_DATA_DIR'])
    parser.add_argument('--tensorboard_logs',   type=str)
    parser.add_argument('--model_dir',   type=str)
    
    # Data directories and other options
    parser.add_argument('--gpu-count',        type=int,   default=os.environ['SM_NUM_GPUS'])
    parser.add_argument('--train',            type=str,   default=os.environ['SM_CHANNEL_TRAIN'])
    parser.add_argument('--validation',       type=str,   default=os.environ['SM_CHANNEL_VALIDATION'])
    parser.add_argument('--eval',             type=str,   default=os.environ['SM_CHANNEL_EVAL'])
    
    args = parser.parse_args()

    main(args)