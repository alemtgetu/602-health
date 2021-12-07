import os
import numpy as np
import matplotlib.pyplot as plt
from imutils import paths
from cancernet import config
from cancernet.cancernet import CancerNet
from sklearn.metrics import confusion_matrix
from sklearn.metrics import classification_report
from keras.utils import np_utils
from tensorflow.keras.optimizers import Adagrad
from keras.callbacks import LearningRateScheduler
from keras.preprocessing.image import ImageDataGenerator
import matplotlib
matplotlib.use("Agg")


# set intial values for epochs, learning rate, and batch size
NUM_EPOCHS = 40
INIT_LR = 1e-2
BS = 32

# get the number of paths in the directories (training, validation, and testing)
trainPaths = list(paths.list_images(config.TRAIN_PATH))
lenTrain = len(trainPaths)
lenVal = len(list(paths.list_images(config.VAL_PATH)))
lenTest = len(list(paths.list_images(config.TEST_PATH)))

# get the class weight of the training data (so we can deal with imbalance)
trainLabels = [int(p.split(os.path.sep)[-2]) for p in trainPaths]
trainLabels = np_utils.to_categorical(trainLabels)
classTotals = trainLabels.sum(axis=0)
classWeight = classTotals.max()/classTotals
classWeightDict = {0: classWeight[0], 1: classWeight[1]}

# initialize training data augmentation object
trainAug = ImageDataGenerator(
    rescale=1/255.0,
    rotation_range=20,
    zoom_range=0.05,
    width_shift_range=0.1,
    height_shift_range=0.1,
    shear_range=0.05,
    horizontal_flip=True,
    vertical_flip=True,
    fill_mode="nearest")

# intialize validation data augmentation object
valAug = ImageDataGenerator(rescale=1 / 255.0)

# initialize generators
# can generate batches of images of size batch_size
trainGen = trainAug.flow_from_directory(
    config.TRAIN_PATH,
    class_mode="categorical",
    target_size=(48, 48),
    color_mode="rgb",
    shuffle=True,
    batch_size=BS)
valGen = valAug.flow_from_directory(
    config.VAL_PATH,
    class_mode="categorical",
    target_size=(48, 48),
    color_mode="rgb",
    shuffle=False,
    batch_size=BS)
testGen = valAug.flow_from_directory(
    config.TEST_PATH,
    class_mode="categorical",
    target_size=(48, 48),
    color_mode="rgb",
    shuffle=False,
    batch_size=BS)

# intialize the model using Adagrad optimizer
# and compile it with a binary_crossentropy loss funtion
model = CancerNet.build(width=48, height=48, depth=3, classes=2)
opt = Adagrad(lr=INIT_LR, decay=INIT_LR/NUM_EPOCHS)
model.compile(loss="binary_crossentropy", optimizer=opt, metrics=["accuracy"])

# fit the model
M = model.fit(
    trainGen,
    steps_per_epoch=lenTrain//BS,
    validation_data=valGen,
    validation_steps=lenVal//BS,
    class_weight=classWeightDict,
    epochs=NUM_EPOCHS
)
# M = model.fit_generator(
#     trainGen,
#     steps_per_epoch=lenTrain//BS,
#     validation_data=valGen,
#     validation_steps=lenVal//BS,
#     class_weight=classWeight,
#     epochs=NUM_EPOCHS)

print("Now evaluating the model")
testGen.reset()
pred_indices = model.predict_generator(testGen, steps=(lenTest//BS)+1)

pred_indices = np.argmax(pred_indices, axis=1)

print(classification_report(testGen.classes, pred_indices,
                            target_names=testGen.class_indices.keys()))

cm = confusion_matrix(testGen.classes, pred_indices)
total = sum(sum(cm))
accuracy = (cm[0, 0]+cm[1, 1])/total
specificity = cm[1, 1]/(cm[1, 0]+cm[1, 1])
sensitivity = cm[0, 0]/(cm[0, 0]+cm[0, 1])
print(cm)
print(f'Accuracy: {accuracy}')
print(f'Specificity: {specificity}')
print(f'Sensitivity: {sensitivity}')

N = NUM_EPOCHS
plt.style.use("ggplot")
plt.figure()
plt.plot(np.arange(0, N), M.history["loss"], label="train_loss")
plt.plot(np.arange(0, N), M.history["val_loss"], label="val_loss")
plt.plot(np.arange(0, N), M.history["acc"], label="train_acc")
plt.plot(np.arange(0, N), M.history["val_acc"], label="val_acc")
plt.title("Training Loss and Accuracy on the IDC Dataset")
plt.xlabel("Epoch No.")
plt.ylabel("Loss/Accuracy")
plt.legend(loc="lower left")
plt.savefig('plot.png')
