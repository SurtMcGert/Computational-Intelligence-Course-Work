# Import the necessary libraries
import torch
import torch.nn as nn
import random
import numpy as np
import threading
from queue import Queue
import copy
import math


class GeneticOptimizer(torch.optim.Optimizer):
    # Init Method:
    def __init__(self, device, model, lossFn, weightLowerBound, weightUpperBound, numOfBits=32, pop=20, elites=1):
        params = model.last_layer.parameters()
        super(GeneticOptimizer, self).__init__(params, defaults={'pop': pop})
        self.popSize = pop  # save the population size
        self.elites = elites  # save the number of elites to take to the next population
        self.device = device  # save the device
        self.model = model  # save the model that this optimizer is for
        self.lossFn = lossFn  # save the loss function for this optimizer
        self.state = {}  # a dictionary to store the populations
        self.numOfBits = numOfBits  # the number of bits for each weight
        # the lower bound for the weight values
        self.weightLowerBound = weightLowerBound
        # the upper bound for the weight values
        self.weightUpperBound = weightUpperBound
        if (elites > pop):
            raise ("you cant have more elites than in your population")
        # loop over the param groups
        for group in self.param_groups:
            # loop over first the weights then the bias
            for p in group['params']:
                stddev = 1. / math.sqrt(p.size(-1))
                arr = list()
                for i in range(pop):
                    # add the gray coded weights/biases to a dictionary
                    numpyData = np.random.uniform(
                        -stddev, stddev, size=list(np.shape(p.data)))
                    tensor = torch.tensor(numpyData)
                    arr.append(self.encodeIndividual(
                        tensor, numOfBits=self.numOfBits))
                self.state[p] = arr

    # Step Method
    def step(self):
        # move the model and the loss function to the device
        self.model = self.model.to(self.device)
        self.lossFn = self.lossFn.to(self.device)
        for group in self.param_groups:
            # loop over each group i.e. the weights, then the biases
            for index, p in enumerate(group['params']):
                # make an array to store all the current fitness values
                currentFitness = np.zeros(self.popSize)
                # decode the individuals
                decoded = self.decodeIndividuals(
                    np.copy(self.state[p]), numOfBits=self.numOfBits)

                # make an array to store all the binary strings of each individual
                binaryArrays = np.full((
                    (self.popSize, ((self.state[p])[0].numel()) * self.numOfBits)), '0')

                threads = list()  # create a list for storing threads

                # loop over all of the individuals in the population
                for individual, weights in enumerate(decoded):
                    # make a queue of functions for the threads to run
                    queue = Queue()
                    # add the function to calculate fitness
                    queue.put((self.calculateFitness, (copy.deepcopy(
                        self.model), individual, index, weights, currentFitness)))
                    # add the function to turn the individual to a binary array
                    queue.put((self.individualToBinaryArray,
                              (individual, np.copy((self.state[p])[individual]), binaryArrays, self.numOfBits)))
                    t = threading.Thread(
                        target=self.worker_thread, args=(queue,))
                    threads.append(t)
                    t.start()
                for t in threads:
                    t.join()

                # now we have the fitness of each individual, we can perform crossover and mutate
                # calculate the fitness proportionate
                fitnessProportionates = self.calculateFitnessProprtionate(
                    np.copy(currentFitness))
                newBinaryArrays = np.full(np.shape(binaryArrays), '0')
                best = np.argpartition(currentFitness, self.elites)[
                    :self.elites]

                threads = list()  # create a list for storing threads
                # for each individual, replace it with an offspring
                for individual, binary in enumerate(binaryArrays):
                    t = threading.Thread(target=self.generateOffspring, args=(
                        individual, best, binary, binaryArrays, fitnessProportionates, newBinaryArrays))
                    threads.append(t)
                    t.start()

                # wait for the threads to finish
                for t in threads:
                    t.join()

                # now we can convert the binary arrays back into weights, then encode them and set them as the new population
                self.state[p] = self.binaryArraysToIndividuals(
                    newBinaryArrays, list((self.state[p])[0].size()), numOfBits=self.numOfBits)

                # set the weights to that of the best offspring
                self.setWeights(self.model, index, decoded[best[0]])

    def worker_thread(self, queue):
        """function allowing a thread to perform a series of queued operations"""
        while not queue.empty():
            function, args = queue.get()
            function(*args)

    def generateOffspring(self, individual, best, binary, binaryArrays, fitnessProportionates, newBinaryArrays):
        """function to generate an offspring for an individual"""
        if individual in best:
            offspring = binary
        else:
            choices = np.arange(self.popSize)
            choices = np.delete(choices, individual)
            proportions = np.delete(fitnessProportionates, individual)
            # get the parents
            p1 = individual
            p2 = random.choices(choices, proportions)[0]
            # perform one point crossover
            offspring = self.onePointCrossover(
                binaryArrays[p1], binaryArrays[p2])
            # now we can mutate this new offspring
            probability = 1 / len(offspring)
            offspring = self.mutate(offspring, probability)
        newBinaryArrays[individual] = offspring

    def calculateFitness(self, model, individual, index, weights, currentFitness):
        """function to calculate the fitness of an individual for the given index parameter (weights or biases) then save the loss in currentFitness"""
        # assign these weights to the last layer
        self.setWeights(model, index, weights)
        # calculate the individuals fitness
        # set the model in evaluation mode
        model.eval()
        x = model.input
        y = model.y
        y_pred = model(x)
        loss = self.lossFn(y_pred, y)
        loss = loss.cpu().detach().item()
        if loss == 0:
            loss = 0.000001
        currentFitness[individual] = loss

    def setWeights(self, model, index, weights):
        """function to set the weights for the given indexed parameter"""
        with torch.no_grad():
            count = 0
            for param in model.last_layer.parameters():
                if (count == index):
                    param.copy_(nn.Parameter(weights))
                    break
                count += 1

    def grayCode(self, n):
        """function to gray code a number n"""
        # gray code the number
        n ^= np.right_shift(n, 1)
        return n

    def encodeIndividual(self, i, numOfBits=4):
        """function to encode an individual with graycoding"""
        numpyArr = i.detach().cpu().numpy()
        numpyArr = self.encodeRealValue(
            numpyArr, lower=self.weightLowerBound, upper=self.weightUpperBound, numOfBits=numOfBits)
        indiv = torch.tensor(numpyArr)
        return indiv

    def decodeIndividuals(self, i, numOfBits=4):
        """function to decode all the individuals back into weights"""
        numpyArr = np.array(i)
        numpyArr = self.decodeRealValue(
            numpyArr, lower=self.weightLowerBound, upper=self.weightUpperBound, numOfBits=numOfBits)
        indiv = [torch.from_numpy(row) for row in numpyArr]
        return indiv

    def encodeRealValue(self, x, lower, upper, numOfBits=4):
        """function to encode a real value x as a graycoded integer"""
        integer = ((x - (lower)) * ((2 ** numOfBits) - 1))/(upper - (lower))
        integer = np.round(integer, 0)
        integer = integer.astype(np.int64)
        grayCoded = self.grayCode(integer)
        return grayCoded

    def decodeRealValue(self, n, lower, upper, numOfBits=4):
        """function to decode a graycoded integer n to a real value"""
        # convert the binary to an integer
        decoded = (lower) + (((upper - (lower)) / ((2 ** numOfBits) - 1)) * n)
        return decoded

    def individualToBinaryArray(self, individual, weights, outputArray, numOfBits=4):
        """function to turn an individual to a binary array and store it in the output array"""
        binary = np.vectorize(np.binary_repr)(weights, numOfBits)
        flattened = np.ravel(binary)
        flattened = [i for ele in flattened for i in ele]
        outputArray[individual] = flattened

    def binaryArraysToIndividuals(self, b, shape, numOfBits=4):
        """function to convert a dictionary of binary arrays to a dictionary of pytorch tensors (individuals)"""
        binary = np.ravel(b)
        binary = np.reshape(binary, (-1, numOfBits))
        binary = np.apply_along_axis(lambda row: ''.join(row), 1, binary)
        integers = np.array([int(binary_string, 2)
                            for binary_string in binary])
        shape = list([len(b)]) + shape
        shape = tuple((shape))
        individuals = np.reshape(integers, shape)
        individuals = [torch.from_numpy(row) for row in individuals]
        return individuals

    def calculateFitnessProprtionate(self, fitnesses):
        """function to calculate the fitness proportionate of each individual"""
        fitnessProprtionates = fitnesses
        reciprocals = np.reciprocal(fitnesses)
        denominator = reciprocals.sum()
        for i, fitness in enumerate(fitnesses):
            fitnessProprtionates[i] = (1 / fitness) / denominator
        return fitnessProprtionates

    def onePointCrossover(self, p1, p2):
        """function to perform 1 point crossover on two parents and return one of the children"""
        point = random.randint(1, len(p1) - 1)
        firstHalf = p1[0:point]
        secondHalf = p2[point:len(p2)]
        offspring = np.concatenate((firstHalf, secondHalf))
        return offspring

    def mutate(self, i, p):
        """function to mutate i with a probability of p"""
        newInt = np.vectorize(int)
        random_floats = np.random.random(len(i))
        flipped_array = np.where(random_floats < p,
                                 (1 - newInt(np.copy(i))).astype(str), i)
        return flipped_array