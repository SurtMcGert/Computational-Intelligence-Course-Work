# Computational Intelligence Course Work
# imports
import numpy as np
import torch
import matplotlib.pyplot as plt
from torch import nn
from torch.optim import Adam
from torchvision.datasets import CIFAR10
from torchvision.transforms import ToTensor
from torch.utils.data import DataLoader
from torch.utils.data import random_split
from sklearn.metrics import classification_report
from cnn import *
from batOptimizer import BatOptimizer
from geneticOptimizer import GeneticOptimizer
from greyWolfOptimizer import GreyWolfOptimizer
from rcgaOptimizer import RCGAOptimizer
from nsga_iiOptimizer import NSGAIIOptimizer
from customOptimizer import CustomWolfOptimizer
from torchvision import transforms
import matplotlib
import time
import os
from deap.benchmarks.tools import diversity, convergence, hypervolume
matplotlib.use("Agg")

# global variables
DATASET_PATH = 'dataset'  # the directory that the dataset files are
IMAGE_DIM = 32  # the dimension of all the images is 32 x 32
IMAGE_CHANNELS = 3  # each image is RGB so has 3 channels
NO_OF_CLASSES = 10  # there are 10 classes of images in the dataset
# the name of the files for storing trained networks and training history
CNN_MODEL_FILE = "cnnModel"
CNN_MODEL_TRAIN_HISTORY_FILE = "cnnModelHistory"
RESNET_MODEL_FILE = "resnetModel"
RESNET_MODEL_TRAIN_HISTORY_FILE = "resnetModelHistory"
MODEL_WITH_CUSTOM_ALGORITHM_FILE = "cnnWithAlgorithm"
MODEL_WITH_CUSTOM_ALGORITHM_TRAIN_HISTORY_FILE = "cnnWithAlgorithmHistory"
BCGA_MODEL_FILE = "bcgaModel"
BCGA_MODEL_TRAIN_HISTORY_FILE = "bcgaModelHistory"
RCGA_MODEL_FILE = "rcgaModel"
RCGA_MODEL_TRAIN_HISTORY_FILE = "rcgaModelHistory"
RCGA_RESNET_MODEL_FILE = "rcgaResnetModel"
RCGA_RESNET_MODEL_TRAIN_HISTORY_FILE = "rcgaResnetModelHistory"
BAT_MODEL_FILE = "batModel"
BAT_MODEL_TRAIN_HISTORY_FILE = "batModelHistory"
WOLF_MODEL_FILE = "wolfModel"
WOLF_MODEL_TRAIN_HISTORY_FILE = "wolfModelHistory"
NSGAII_MODEL_FILE = "nsgaiiModel"
NSGAII_MODEL_TRAIN_HISTORY_FILE = "nsgaiiModelHistory"
NSGAII_3_EPOCHS_MODEL_FILE = "nsgaii3EpochsModel"
NSGAII_3_EPOCHS_MODEL_TRAIN_HISTORY_FILE = "nsgaii3EpochsModelHistory"
NSGAII_RESNET_MODEL_FILE = "nsgaiiResnetModel"
NSGAII_RESNET_MODEL_HISTORY_FILE = "nsgaiiResnetModelHistory"
BCGA_RESNET_MODEL_FILE = "bcgaResnetModel"
BCGA_RESNET_MODEL_HISTORY_FILE = "bcgaResnetModelHistory"
# define training hyperparameters
BATCH_SIZE = 128
EPOCHS = 9
# define the train and val splits
TRAIN_SPLIT = 0.75
VAL_SPLIT = 1 - TRAIN_SPLIT


# function to build a CNN
# inputs:
# device - the device to train the model on
# trainingData - the data that will be used to train the model
# channels - the number of channels the images have
#
# returns: a CNN model, the optimizer and the loss function
def modelCNN(device, trainingData, channels):
    print("making a CNN")
    print("device: ", device)
    model = CNN(
        numChannels=channels,
        classes=len(trainingData.dataset.classes)).to(device)
    # initialize our optimizer and loss function
    opt = Adam(model.parameters(), lr=0.001)
    lossFn = nn.CrossEntropyLoss()
    return model, opt, lossFn

# function to build a ResNet-4
# inputs:
# device - the device to train the model on
# trainingData - the data that will be used to train the model
# channels - the number of channels the images have
#
# returns: a CNN model, the optimizer and the loss function


def modelResNet(device):
    print("making a ResNet")
    print("device: ", device)
    model = ResNet(
        ResidualBlock,
        [1, 1, 1, 1]).to(device)
    # initialize our optimizer and loss function
    opt = Adam(model.parameters(), lr=0.001)
    lossFn = nn.CrossEntropyLoss()
    return model, opt, lossFn


# function to train a given model and save its weights to a file
# inputs:
# device - the device to train the model on
# device - the device to train the model on
# model - the model to train
# opt - the optimization algorithm
# lossFn - the loss function
# trainingDataLoader - the data loader for the training data
# valDataLoader - the data loader for the validation data
# epochs - the number of epochs
# batchSize - the batch size
#
# returns: the trained model and the training history
def trainModel(device, model, opt, lossFn, trainingDataLoader, valDataLoader, epochs, batchSize):
    print("training model")
    model = model.to(device)
    trainStart = time.time()
    # calculate steps per epoch for training and validation set
    trainSteps = len(trainingDataLoader.dataset) // batchSize
    valSteps = len(valDataLoader.dataset) // batchSize
    # initialize a dictionary to store training history
    H = {
        "train_loss": [],
        "train_acc": [],
        "val_loss": [],
        "val_acc": []
    }
    # loop over our epochs
    for e in range(0, epochs):
        epochStart = time.time()
        # set the model in training mode
        # initialize the total training and validation loss
        totalTrainLoss = 0
        totalValLoss = 0
        # initialize the number of correct predictions in the training
        # and validation step
        trainCorrect = 0
        valCorrect = 0
        # loop over the training set
        for (x, y) in trainingDataLoader:
            # send the input to the device
            (x, y) = (x.to(device), y.to(device))
            # perform a forward pass and calculate the training loss
            pred = model(x)
            loss = lossFn(pred, y)
            model.y = y
            # zero out the gradients, perform the backpropagation step,
            # and update the weights
            opt.zero_grad()
            loss.backward()
            opt.step()
            # add the loss to the total training loss so far and
            # calculate the number of correct predictions
            totalTrainLoss += loss
            trainCorrect += (pred.argmax(1) == y).type(
                torch.float).sum().item()

        # switch off autograd for evaluation
        with torch.no_grad():
            # set the model in evaluation mode
            model.eval()
            # loop over the validation set
            for (x, y) in valDataLoader:
                # send the input to the device
                (x, y) = (x.to(device), y.to(device))
                # make the predictions and calculate the validation loss
                pred = model(x)
                totalValLoss += lossFn(pred, y)
                # calculate the number of correct predictions
                valCorrect += (pred.argmax(1) == y).type(
                    torch.float).sum().item()

            epochEnd = time.time()

        # calculate the average training and validation loss
        avgTrainLoss = totalTrainLoss / trainSteps
        avgValLoss = totalValLoss / valSteps
        # calculate the training and validation accuracy
        trainCorrect = trainCorrect / len(trainingDataLoader.dataset)
        valCorrect = valCorrect / len(valDataLoader.dataset)
        # update our training history
        H["train_loss"].append(avgTrainLoss.cpu().detach().numpy())
        H["train_acc"].append(trainCorrect)
        H["val_loss"].append(avgValLoss.cpu().detach().numpy())
        H["val_acc"].append(valCorrect)
        # print the model training and validation information
        print("[INFO] EPOCH: {}/{}".format(e + 1, epochs))
        print("Train loss: {:.6f}, Train accuracy: {:.4f}".format(
            avgTrainLoss, trainCorrect))
        print("Val loss: {:.6f}, Val accuracy: {:.4f}".format(
            avgValLoss, valCorrect))
        epochTimeTaken = (epochEnd - epochStart) / 60
        print("time to train epoch: ", epochTimeTaken, " minutes\n")

    trainEnd = time.time()
    trainTimeTaken = (trainEnd - trainStart) / 60
    print("time to train: ", trainTimeTaken, " minutes\n")
    return model, H


# function to save a model and its history
# inputs:
# model - the model to save
# H - the training history for the model
# modelFileName - the file name to save the model into
# historyFileName - the file name to save the training history into
def saveModel(model, H, modelFileName, historyFileName):
    print("saving model: ", modelFileName)
    folder = "models/"
    torch.save(model, folder+modelFileName)
    torch.save(H, folder+historyFileName)


# function to load a model and its history
# inputs:
# modelFileName - the file name to load the model from
# historyFileName - the file name to load the training history from
#
# returns: the model, and the history
def loadModel(modelFileName, historyFileName):
    print("loading model: ", modelFileName)
    folder = "models/"
    model = torch.load(folder+modelFileName)
    H = torch.load(folder+historyFileName)
    return model, H

# function to check if the model file exists
# inputs:
# file - the file name to look for
#
# returns: wether the file exists or not


def trainingFileExists(file):
    folder = "models/"
    return os.path.isfile(folder + file)

# function to evaluate a model
# inputs:
# device - the device this model was trained on
# model - the model to evaluate
# testDataLoader - the data loader for the test data
# testingData - the testing data
# H - the training history
# plotName - the name of the file to save the plot for this evaluation


def evaluateModel(device, model, testDataLoader, testingData, H, plotName):
    print("evaluating model...")
    folder = "evaluations/"
    model = model.to(device)
    # turn off autograd for testing evaluation
    with torch.no_grad():
        # set the model in evaluation mode
        model.eval()

        # initialize a list to store our predictions
        preds = []
        # loop over the test set
        for (x, y) in testDataLoader:
            # send the input to the device
            x = x.to(device)
            # make the predictions and add them to the list
            pred = model(x)
            preds.extend(pred.argmax(axis=1).cpu().numpy())
    # generate a classification report
    print(classification_report(testingData.targets,
                                np.array(preds), target_names=testingData.classes, zero_division=0))

    # plot the training loss and accuracy
    plt.style.use("ggplot")
    plt.figure()
    plt.plot(H["train_loss"], label="train_loss")
    plt.plot(H["val_loss"], label="val_loss")
    plt.plot(H["train_acc"], label="train_acc")
    plt.plot(H["val_acc"], label="val_acc")
    plt.title("Training Loss and Accuracy on Dataset")
    plt.xlabel("Epoch #")
    plt.ylabel("Loss/Accuracy")
    plt.legend(loc="lower left")
    plt.savefig(folder+plotName)


# main method
def main():
    print("getting training and testing data")
    trainingData = CIFAR10(root="dataset", train=True, download=True,
                           transform=ToTensor())
    testingData = CIFAR10(root="dataset", train=False, download=True,
                          transform=ToTensor())

    # calculate the train/validation split
    print("generating the train/validation split...")
    numTrainSamples = int(len(trainingData) * TRAIN_SPLIT)
    numValSamples = int(len(trainingData) * VAL_SPLIT)
    (trainingData, valData) = random_split(trainingData,
                                           [numTrainSamples, numValSamples],
                                           generator=torch.Generator().manual_seed(42))

    # initialize the train, validation, and test data loaders
    print("initializing the data loaders...")
    trainingDataLoader = DataLoader(trainingData, shuffle=True,
                                    batch_size=BATCH_SIZE)
    valDataLoader = DataLoader(valData, batch_size=BATCH_SIZE)
    testDataLoader = DataLoader(testingData, batch_size=BATCH_SIZE)

    # set the device we will be using to train the model
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # make a CNN model
    cnn, opt, lossFn = modelCNN(device, trainingData, IMAGE_CHANNELS)

    # train the cnn model
    if trainingFileExists(CNN_MODEL_FILE):
        cnn, H = loadModel(
            CNN_MODEL_FILE, CNN_MODEL_TRAIN_HISTORY_FILE)
    else:
        cnn, H = trainModel(
            device, cnn, opt, lossFn, trainingDataLoader, valDataLoader, EPOCHS, BATCH_SIZE)
        # reset the last layer of the resnet model
        cnn.reInitializeFinalLayer()
        # save resnet model to disk
        saveModel(cnn, H, CNN_MODEL_FILE, CNN_MODEL_TRAIN_HISTORY_FILE)

    # evaluate the model before using the optimization algorithm
    print("=====================================================\nEvaluating resnet model before using optimization algorithms\n=====================================================")
    evaluateModel(device, cnn, testDataLoader, testingData,
                  H, "originalResnetEvaluationPlot.png")

    # train the model using the genetic optimization algorithm
    print("binary coded genetic optimizer")
    opt = GeneticOptimizer(device, cnn, lossFn=lossFn,
                           weightLowerBound=-1, weightUpperBound=1, numOfBits=8, pop=20, elites=10)
    if trainingFileExists(BCGA_MODEL_FILE):
        cnn, H = loadModel(
            BCGA_MODEL_FILE, BCGA_MODEL_TRAIN_HISTORY_FILE)
    else:
        cnn, H = trainModel(device, cnn, opt, lossFn, trainingDataLoader,
                            valDataLoader, EPOCHS, BATCH_SIZE)
        saveModel(cnn, H, BCGA_MODEL_FILE, BCGA_MODEL_TRAIN_HISTORY_FILE)

    # evaluate the model after using the optimization algorithm
    print("=====================================================\nEvaluating model after using binary coded genetic algorithm\n=====================================================")
    evaluateModel(device, cnn, testDataLoader, testingData,
                  H, "geneticAlgorithmEvaluationPlot.png")
    cnn.reInitializeFinalLayer()

    # train the model using the real coded genetic optimization algorithm
    print("real coded genetic optimizer")
    opt = RCGAOptimizer(device, cnn, lossFn=lossFn,
                        weightLowerBound=-1, weightUpperBound=1, pop=40, elites=10)
    if trainingFileExists(RCGA_MODEL_FILE):
        cnn, H = loadModel(
            RCGA_MODEL_FILE, RCGA_MODEL_TRAIN_HISTORY_FILE)
    else:
        cnn, H = trainModel(device, cnn, opt, lossFn, trainingDataLoader,
                            valDataLoader, EPOCHS, BATCH_SIZE)
        saveModel(cnn, H, RCGA_MODEL_FILE, RCGA_MODEL_TRAIN_HISTORY_FILE)

    # evaluate the model after using the optimization algorithm
    print("=====================================================\nEvaluating model after using real coded genetic algorithm\n=====================================================")
    evaluateModel(device, cnn, testDataLoader, testingData,
                  H, "RCGAEvaluationPlot.png")
    cnn.reInitializeFinalLayer()

    # # train the model using the grey wolf optimization algorithm
    if trainingFileExists(WOLF_MODEL_FILE):
        cnn, H = loadModel(
            WOLF_MODEL_FILE, WOLF_MODEL_TRAIN_HISTORY_FILE)
    else:
        numOfIters = len(trainingDataLoader) * EPOCHS
        opt = GreyWolfOptimizer(device, cnn, lossFn,
                                numOfIters=numOfIters, pop=40, debug=False)
        cnn, H = trainModel(device, cnn, opt, lossFn, trainingDataLoader,
                            valDataLoader, EPOCHS, BATCH_SIZE)
        saveModel(cnn, H, WOLF_MODEL_FILE, WOLF_MODEL_TRAIN_HISTORY_FILE)

    # evaluate the model after using the optimization algorithm
    print("=====================================================\nEvaluating model after using grey wolf algorithm\n=====================================================")
    evaluateModel(device, cnn, testDataLoader, testingData,
                  H, "greyWolfAlgorithmEvaluationPlot.png")
    cnn.reInitializeFinalLayer()

    # train the model using the bat optimizer
    print("bat PS optimizer")
    if trainingFileExists(BAT_MODEL_FILE):
        cnn, H = loadModel(
            BAT_MODEL_FILE, BAT_MODEL_TRAIN_HISTORY_FILE)
    else:
        opt = BatOptimizer(device, cnn, lossFn,
                           populationSize=40, debug=False)
        cnn, H = trainModel(device, cnn, opt, lossFn, trainingDataLoader,
                            valDataLoader, EPOCHS, BATCH_SIZE)
        saveModel(cnn, H, BAT_MODEL_FILE, BAT_MODEL_TRAIN_HISTORY_FILE)

    # evaluate the model after using the optimization algorithm
    print("=====================================================\nEvaluating model after using bat algorithm\n=====================================================")
    evaluateModel(device, cnn, testDataLoader, testingData,
                  H, "BatAlgorithmEvaluationPlot.png")
    cnn.reInitializeFinalLayer()

    # evaluate the model after using the NSGAII optimization algorithm
    if trainingFileExists(NSGAII_MODEL_FILE):
        cnn, H = loadModel(
            NSGAII_MODEL_FILE, NSGAII_MODEL_TRAIN_HISTORY_FILE)
    else:
        opt = NSGAIIOptimizer(device, cnn, lossFn, weightLowerBound=-1,
                              weightUpperBound=1, pop=72, numOfBits=16)
        cnn, H = trainModel(device, cnn, opt, lossFn, trainingDataLoader,
                            valDataLoader, EPOCHS, BATCH_SIZE)
        saveModel(cnn, H, NSGAII_MODEL_FILE, NSGAII_MODEL_TRAIN_HISTORY_FILE)

    # evaluate the model after using the optimization algorithm
    print("=====================================================\nEvaluating model after using NSGAII algorithm\n=====================================================")
    evaluateModel(device, cnn, testDataLoader, testingData,
                  H, "NSGAIIAlgorithmEvaluationPlot.png")
    cnn.reInitializeFinalLayer()

    # evaluate the model after using the NSGAII optimization algorithm
    if trainingFileExists(NSGAII_3_EPOCHS_MODEL_FILE):
        cnn, H = loadModel(
            NSGAII_3_EPOCHS_MODEL_FILE, NSGAII_3_EPOCHS_MODEL_TRAIN_HISTORY_FILE)
        # cnn, populations = loadModel(
        #     NSGAII_3_EPOCHS_MODEL_FILE, "nsgaii3EpochPopFile")
    else:
        opt = NSGAIIOptimizer(device, cnn, lossFn, weightLowerBound=-1,
                              weightUpperBound=1, pop=240, numOfBits=16)
        cnn, H = trainModel(device, cnn, opt, lossFn, trainingDataLoader,
                            valDataLoader, 3, BATCH_SIZE)
        populations = opt.getPop()
        saveModel(cnn, H, NSGAII_3_EPOCHS_MODEL_FILE,
                  NSGAII_3_EPOCHS_MODEL_TRAIN_HISTORY_FILE)
        saveModel(cnn, populations, NSGAII_3_EPOCHS_MODEL_FILE,
                  "nsgaii3EpochPopFile")

    # evaluate the model after using the optimization algorithm
    print("=====================================================\nEvaluating model after using NSGAII algorithm with 3 epochs\n=====================================================")
    evaluateModel(device, cnn, testDataLoader, testingData,
                  H, "NSGAII_3epochs_AlgorithmEvaluationPlot.png")
    # for index, pop in enumerate(populations):
    #     print("population: ", index)
    #     print("Final population hypervolume is %f" %
    #           hypervolume(pop, [11.0, 11.0]))
    cnn.reInitializeFinalLayer()

    # TESTING WITH RESNET
    # load data to correct dimensions
    trainingData = CIFAR10(root="dataset", train=True, download=True,
                           transform=transforms.Compose([
                               transforms.Resize((224, 224)),
                               transforms.ToTensor(),
                           ]))
    testingData = CIFAR10(root="dataset", train=False, download=True,
                          transform=transforms.Compose([
                              transforms.Resize((224, 224)),
                              transforms.ToTensor(),
                          ]))
    # calculate the train/validation split
    print("generating the train/validation split...")
    numTrainSamples = int(len(trainingData) * TRAIN_SPLIT)
    numValSamples = int(len(trainingData) * VAL_SPLIT)
    (trainingData, valData) = random_split(trainingData,
                                           [numTrainSamples, numValSamples],
                                           generator=torch.Generator().manual_seed(42))
    # initialize the train, validation, and test data loaders
    print("initializing the data loaders...")
    trainingDataLoader = DataLoader(trainingData, shuffle=True,
                                    batch_size=BATCH_SIZE)
    valDataLoader = DataLoader(valData, batch_size=BATCH_SIZE)
    testDataLoader = DataLoader(testingData, batch_size=BATCH_SIZE)

    # make a resnet model
    resnet, opt, lossFn = modelResNet(device)

    # test with Adam optimizer
    print("resnet with Adam")
    if trainingFileExists(RESNET_MODEL_FILE):
        resnet, H = loadModel(
            RESNET_MODEL_FILE, RESNET_MODEL_TRAIN_HISTORY_FILE)
    else:
        resnet, H = trainModel(device, resnet, opt, lossFn, trainingDataLoader,
                               valDataLoader, EPOCHS, BATCH_SIZE)
        saveModel(resnet, H, RESNET_MODEL_FILE,
                  RESNET_MODEL_TRAIN_HISTORY_FILE)

    # evaluate the model after training Resnet with Adam
    print("=====================================================\nEvaluating Resnet with Adam\n=====================================================")
    evaluateModel(device, resnet, testDataLoader, testingData,
                  H, "ResnetEvaluationPlot.png")
    resnet.reInitializeFinalLayer()

    # train Resnet with custom optimizer
    print("custom optimizer on Resnet")
    if trainingFileExists(MODEL_WITH_CUSTOM_ALGORITHM_FILE):
        resnet, H = loadModel(
            MODEL_WITH_CUSTOM_ALGORITHM_FILE, MODEL_WITH_CUSTOM_ALGORITHM_TRAIN_HISTORY_FILE)
    else:
        numOfIters = len(trainingDataLoader) * EPOCHS
        opt = CustomWolfOptimizer(device, resnet, lossFn,
                                  numOfIters=numOfIters, pop=20, debug=False)
        resnet, H = trainModel(device, resnet, opt, lossFn, trainingDataLoader,
                               valDataLoader, EPOCHS, BATCH_SIZE)
        saveModel(resnet, H, MODEL_WITH_CUSTOM_ALGORITHM_FILE,
                  MODEL_WITH_CUSTOM_ALGORITHM_TRAIN_HISTORY_FILE)

    # evaluate the model after training Resnet with Custom optimizer
    print("=====================================================\nEvaluating Resnet with custom optimizer\n=====================================================")
    evaluateModel(device, resnet, testDataLoader, testingData,
                  H, "customOptimizerEvaluationPlot.png")
    resnet.reInitializeFinalLayer()

    # train the model using the real coded genetic optimization algorithm
    print("RCGA on Resnet")
    opt = RCGAOptimizer(device, resnet, lossFn=lossFn,
                        weightLowerBound=-1, weightUpperBound=1, pop=20, elites=10)
    if trainingFileExists(RCGA_RESNET_MODEL_FILE):
        resnet, H = loadModel(
            RCGA_RESNET_MODEL_FILE, RCGA_RESNET_MODEL_TRAIN_HISTORY_FILE)
    else:
        resnet, H = trainModel(device, resnet, opt, lossFn, trainingDataLoader,
                               valDataLoader, EPOCHS, BATCH_SIZE)
        saveModel(resnet, H, RCGA_RESNET_MODEL_FILE,
                  RCGA_RESNET_MODEL_TRAIN_HISTORY_FILE)

    # evaluate the model after using the optimization algorithm
    print("=====================================================\nEvaluating model after using real coded genetic algorithm\n=====================================================")
    evaluateModel(device, resnet, testDataLoader, testingData,
                  H, "RCGAOnResnetEvaluationPlot.png")
    resnet.reInitializeFinalLayer()

    # train bcga on resnet
    print("BCGA on Resnet")
    opt = GeneticOptimizer(device, cnn, lossFn=lossFn,
                           weightLowerBound=-1, weightUpperBound=1, numOfBits=8, pop=20, elites=10)
    if trainingFileExists(BCGA_RESNET_MODEL_FILE):
        resnet, H = loadModel(
            BCGA_RESNET_MODEL_FILE, BCGA_RESNET_MODEL_HISTORY_FILE)
    else:
        resnet, H = trainModel(device, resnet, opt, lossFn, trainingDataLoader,
                               valDataLoader, EPOCHS, BATCH_SIZE)
        saveModel(resnet, H, BCGA_RESNET_MODEL_FILE,
                  BCGA_RESNET_MODEL_HISTORY_FILE)

    # evaluate the model after using the optimization algorithm
    print("=====================================================\nEvaluating model after using binary coded genetic algorithm\n=====================================================")
    evaluateModel(device, resnet, testDataLoader, testingData,
                  H, "BCGAOnResnetEvaluationPlot.png")
    resnet.reInitializeFinalLayer()

    # train NSGA-II on resent
    print("NSGA-II on resnet")
    if trainingFileExists(NSGAII_RESNET_MODEL_FILE):
        resnet, H = loadModel(
            NSGAII_RESNET_MODEL_FILE, NSGAII_RESNET_MODEL_HISTORY_FILE)
    else:
        opt = NSGAIIOptimizer(device, resnet, lossFn, weightLowerBound=-1,
                              weightUpperBound=1, pop=10, numOfBits=8)
        resnet, H = trainModel(device, resnet, opt, lossFn, trainingDataLoader,
                               valDataLoader, EPOCHS, 8)
        saveModel(resnet, H, NSGAII_RESNET_MODEL_FILE,
                  NSGAII_RESNET_MODEL_HISTORY_FILE)
        saveModel(resnet, populations, NSGAII_RESNET_MODEL_FILE,
                  "nsgaiiResnetPopFile")

    # evaluate the model after training Resnet with Custom optimizer
    print("=====================================================\nEvaluating Resnet with NSGAII\n=====================================================")
    evaluateModel(device, resnet, testDataLoader, testingData,
                  H, "NSGAIIResnetEvaluationPlot.png")


# run the main method
main()
