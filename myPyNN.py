import numpy as np
DEBUG = 0

class MyPyNN(object):

    def __init__(self, layers=[3, 4, 2]):

        self.layers = layers

        # Network
        self.weights = [np.random.randn(x+1, y) 
                        for x, y in zip(self.layers[:-1], self.layers[1:])]

        # For mean-centering
        self.meanX = np.zeros((1, self.layers[0]))

        # Default options
        self.learningRate = 1.0
        self.regLambda = 0
        self.adaptLearningRate = False
        self.normalizeInputs = False
        self.meanCentering = False
        self.visible = False

    def predict(self, X, visible=False):
        self.visible = visible
        # mean-centering
        inputs = self.preprocessTestingInputs(X) - self.meanX

        if inputs.ndim!=1 and inputs.ndim!=2:
            print "X is not one or two dimensional, please check."
            return

        if DEBUG or self.visible:
            print "PREDICT:"
            print inputs

        for l, w in enumerate(self.weights):
            inputs = self.addBiasTerms(inputs)
            inputs = self.sigmoid(np.dot(inputs, w))
            if DEBUG or self.visible:
                print "Layer "+str(l+1)
                print inputs
        
        return inputs

    def trainUsingMinibatchGD(self, X, y, nEpochs=1000, minibatchSize=100,
                        learningRate=0.05, regLambda=0, adaptLearningRate=False, 
                        normalizeInputs=False, meanCentering=False, 
                        printTestAccuracy=False, testX=None, testY=None, 
                        visible=False):
        self.learningRate = float(learningRate)
        self.regLambda = regLambda
        self.adaptLearningRate = adaptLearningRate
        self.normalizeInputs = normalizeInputs
        self.meanCentering = meanCentering
        self.visible = visible
        
        X = self.preprocessTrainingInputs(X)
        y = self.preprocessOutputs(y)
        
        yPred = self.predict(X, visible=self.visible)
        
        if yPred.shape != y.shape:
            print "Shape of y ("+str(y.shape)+") does not match what shape of y is supposed to be: "+str(yPred.shape)
            return
        
        self.trainAccuracy = (np.sum([np.argmax(yPred[k])==np.argmax(y[k])
                            for k in range(len(y))])).astype(float)/len(y)
        print "train accuracy = " + str(self.trainAccuracy)
        
        self.prevCost = 0.5*np.sum((yPred-y)**2)/len(y)
        print "cost = " + str(self.prevCost)
        self.cost = self.prevCost

        # mean-centering
        if self.meanCentering:
            X = X - self.meanX
        else:
            X = X

        self.inputs = X
        
        if DEBUG or self.visible:
            print "train input:"+str(inputs)

        # Just to ensure minibatchSize !> len(X)
        if minibatchSize > len(X):
            minibatchSize = int(len(X)/10)+1

        # Test data
        if printTestAccuracy:
            if testX==None and testY==None:
                print "No test data given"
                testX = np.zeros((1, len(X)))
                testY = np.zeros((1,1))
            elif testX==None or testY==None:
                print "One of testData not available"
                return
            else:
                testX = self.preprocessTrainingInputs(testX)
                testY = self.preprocessOutputs(testY)
            if len(testX)!=len(testY):
                print "Test Datas not of same length"
                return
            
            yTestPred = self.predict(testX, visible=self.visible)
            self.testAccuracy = np.sum([np.argmax(yTestPred[k])==np.argmax(testY[k])
                                for k in range(len(testY))])/float(len(testY))
            print "test accuracy = " + str(self.testAccuracy)

        # Randomly initialize old weights (for adaptive learning), will copy values later 
        if adaptLearningRate:
            self.oldWeights = [np.random.randn(i+1, j) 
                    for i, j in zip(self.layers[:-1], self.layers[1:])]
        
        # For each epoch
        for i in range(nEpochs):
            
            print "Epoch "+str(i)+" of "+str(nEpochs)
            
            ## Find minibatches
            # Generate list of indices of full training data
            fullIdx = list(range(len(X)))
            # Shuffle the list
            np.random.shuffle(fullIdx)
            # Make list of mininbatches
            minibatches = [fullIdx[k:k+minibatchSize] 
                            for k in xrange(0, len(X), minibatchSize)]

            # For each minibatch
            for mininbatch in mininbatches:
                # Find X and y for each minibatch
                miniX = X[idx]
                miniY = y[idx]
                
                # Forward propagate through miniX
                a = self.forwardProp(miniX)
                
                # Check if Forward Propagation was successful
                if a==False:
                    return

                # Save old weights before backProp in case of adaptLR
                if adaptLearningRate:
                    for i in range(len(self.weights)):
                        self.oldWeights[i] = np.array(self.weights[i])

                # Back propagate, update weights for minibatch
                self.backPropGradDescent(miniX, miniY)

            yPred = self.predict(X, visible=self.visible)

            self.trainAccuracy = (np.sum([np.argmax(yPred[k])==np.argmax(y[k])
                                for k in range(len(y))])).astype(float)/len(y)
            print "train accuracy = " + str(self.trainAccuracy)
            if printTestAccuracy:
                yTestPred = self.predict(testX, visible=self.visible)
                self.testAccuracy = (np.sum([np.argmax(yTestPred[k])==np.argmax(testY[k])
                                    for k in range(len(testY))])).astype(float)/len(testY)
                print "test accuracy = " + str(self.testAccuracy)

            self.cost = 0.5*np.sum((yPred-y)**2)/len(y)            
            print "cost = " + str(self.cost)
            
            if adaptLearningRate:
                self.adaptLR()
            
            self.evaluate(X, y)

            self.prevCost = self.cost

    def forwardProp(self, inputs):
        inputs = self.preprocessInputs(inputs)
        print "Forward..."

        if inputs.ndim!=1 and inputs.ndim!=2:
            print "Input argument " + str(inputs.ndim) + \
                "is not one or two dimensional, please check."
            return False

        if (inputs.ndim==1 and len(inputs)!=self.layers[0]) or \
            (inputs.ndim==2 and inputs.shape[1]!=self.layers[0]):
            print "Input argument does not match input dimensions (" + \
                str(self.layers[0]) + ") of network."
            return False
        
        if DEBUG or self.visible:
            print inputs

        # Save the outputs of each layer
        self.outputs = []

        # For each layer
        for l, w in enumerate(self.weights):
            # Add bias term to the input
            inputs = self.addBiasTerms(inputs)

            # Calculate the output
            self.outputs.append(self.sigmoid(np.dot(inputs, w)))

            # Set this as the input to the next layer
            inputs = np.array(self.outputs[-1])

            if DEBUG or self.visible:
                print "Layer "+str(l+1)
                print "inputs: "+str(inputs)
                print "weights: "+str(w)
                print "output: "+str(inputs)
        del inputs

        return True

    def backPropGradDescent(self, X, y):
        print "...Backward"

        # Correct the formats of inputs and outputs
        X = self.preprocessInputs(X)
        y = self.preprocessOutputs(y)

        # Compute first error
        bpError = self.outputs[-1] - y

        if DEBUG or self.visible:
            print "error = self.outputs[-1] - y:"
            print error

        # For each layer in reverse order (last layer to first layer)
        for l, w in enumerate(reversed(self.weights)):
            if DEBUG or self.visible:
                print "LAYER "+str(len(self.weights)-l)
            
            # The calculated output "z" of that layer
            predOutputs = self.outputs[-l-1]

            if DEBUG or self.visible:
                print "predOutputs"
                print predOutputs

            # delta = error*(z*(1-z)) === nxneurons
            delta = np.multiply(error, np.multiply(predOutputs, 1 - predOutputs))

            if DEBUG or self.visible:
                print "To compute error to be backpropagated:"
                print "del = predOutputs*(1 - predOutputs)*error :"
                print delta
                print "weights:"
                print w

            # Compute new error to be propagated back (bias term neglected in backpropagation)
            bpError = np.dot(delta, w[1:,:].T)

            if DEBUG or self.visible:
                print "backprop error = np.dot(del, w[1:,:].T) :"
                print error

            # If we are at first layer, inputs are data points
            if l==len(self.weights)-1:
                inputs = self.addBiasTerms(X)
            # Else, inputs === outputs from previous layer
            else:
                inputs = self.addBiasTerms(self.outputs[-l-2])
            
            if DEBUG or self.visible:
                print "To compute errorTerm:"
                print "inputs:"
                print inputs
                print "del:"
                print delta

            # errorTerm = (inputs.T).*(delta)/n
            # delta === nxneurons, inputs === nxprev, W === prevxneurons
            errorTerm = np.dot(inputs.T, delta)/len(y)
            if errorTerm.ndim==1:
                errorTerm.reshape((len(errorTerm), 1))

            if DEBUG or self.visible:
                print "errorTerm = np.dot(inputs.T, del) :"
                print errorTerm
            
            # regularization term
            regWeight = np.zeros(w.shape)
            regWeight[1:,:] = self.regLambda #bias term neglected

            if DEBUG or self.visible:
                print "To update weights:"
                print "learningRate*errorTerm:"
                print self.learningRate*errorTerm
                print "regWeight:"
                print regWeight
                print "weights:"
                print w
                print "regTerm = regWeight*w :"
                print regWeight*w

            # Update weights
            self.weights[-l-1] = w - \
                (self.learningRate*errorTerm + np.multiply(regWeight,w))
            
            if DEBUG or self.visible:
                print "Updated 'weights' = learningRate*errorTerm + regTerm :"
                print self.weights[len(self.weights)-l-1]

    def adaptLR(self):
        if self.cost > self.prevCost:
            print "Cost increased!!"
            self.learningRate /= 2.0
            print "   - learningRate halved to: "+str(self.learningRate)
            for i in range(len(self.weights)):
                self.weights[i] = self.oldWeights[i]
            print "   - weights reverted back"
        # good function
        else:
            self.learningRate *= 1.05
            print "   - learningRate increased by 5% to: "+str(self.learningRate)

    def preprocessTrainingInputs(self, X):
        X = self.preprocessInputs(X)
        if self.normalizeInputs and np.max(X) > 1.0:
            X = X/255.0
        if np.all(self.meanX == np.zeros((1, self.layers[0]))) and self.meanCentering:
            self.meanX = np.reshape(np.mean(X, axis=0), (1, X.shape[1]))
        return X

    def preprocessTestingInputs(self, X):
        X = self.preprocessInputs(X)
        if self.normalizeInputs and np.max(X) > 1.0:
            X = X/255.0
        return X

    def preprocessInputs(self, X):
        X = np.array(X, dtype=float)
        # if X is int
        if X.ndim==0:
            X = np.array([X])
        # if X is 1D
        if X.ndim==1:
            if self.layers[0]==1: #if ndim=1
                X = np.reshape(X, (len(X),1))
            else: #if X is only 1 nd-ndimensional vector
                X = np.reshape(X, (1,len(X)))
        return X

    def preprocessOutputs(self, Y):
        Y = np.array(Y, dtype=float)
        # if Y is int
        if Y.ndim==0:
            Y = np.array([Y])
        # if Y is 1D
        if Y.ndim==1:
            if self.layers[-1]==1:
                Y = np.reshape(Y, (len(Y),1))
            else:
                Y = np.reshape(Y, (1,len(Y)))
        return Y

    def addBiasTerms(self, X):
        if X.ndim==0 or X.ndim==1:
            X = np.insert(X, 0, 1)
        elif X.ndim==2:
            X = np.insert(X, 0, 1, axis=1)
        return X

    def sigmoid(self, z):
        return 1/(1 + np.exp(-z))

    def evaluate(self, X, Y):
        yPreds = forwardProp(X, self.weights)[-1]
        test_results = [(np.argmax(yPreds[i]), np.argmax(Y[i]))
                            for i in range(len(Y))]
        yes = sum(int(x == y) for (x, y) in test_results)
        print(str(yes)+" out of "+str(len(Y)))

    def loadMNISTData(self, path='/Users/vikram.v/Downloads/mnist.npz'):
        # Use numpy.load() to load the .npz file
        f = np.load(path)

        # To check files stored in .npz file
        f.files

        # Saving the files
        x_train = f['x_train']
        y_train = f['y_train']
        x_test = f['x_test']
        y_test = f['y_test']
        f.close()

        # Preprocess inputs
        x_train_new = np.array([x.flatten() for x in x_train])
        y_train_new = np.zeros((len(y_train), 10))
        for i in range(len(y_train)):
            y_train_new[i][y_train[i]] = 1

        x_test_new = np.array([x.flatten() for x in x_test])
        y_test_new = np.zeros((len(y_test), 10))
        for i in range(len(y_test)):
            y_test_new[i][y_test[i]] = 1

        return [x_train_new, y_train_new, x_test_new, y_test_new]
