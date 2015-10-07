

import numpy as np
import numpy.linalg as la
import scipy

from rlscore import predictor

class OrthogonalMatchingPursuit(object):
    
    def loadResources(self):
        """
        Loads the resources from the previously set resource pool.
        
        @raise Exception: when some of the resources required by the learner is not available in the ResourcePool object.
        """
        
        self.Y = Y
        #Number of training examples
        self.size = Y.shape[0]
        if not Y.shape[1] == 1:
            raise Exception('GreedyRLS currently supports only one output at a time. The output matrix is now of shape ' + str(Y.shape) + '.')
        
        X = self.resource_pool['X']
        if isinstance(X, scipy.sparse.base.spmatrix):
            self.X = X.todense()
        else:
            self.X = X
        #if self.resource_pool.has_key('bias'):
        #    self.bias = float(self.resource_pool['bias'])
        #else:
        #    self.bias = 0.
    
    
    def train(self):
        
        X = self.X
        Y = self.Y
        
        tsize = self.size
        fsize = X.shape[1]
        assert X.shape[0] == tsize
        
        if not self.resource_pool.has_key('subsetsize'):
            raise Exception("Parameter 'subsetsize' must be given.")
        desiredfcount = int(self.resource_pool['subsetsize'])
        if not fsize >= desiredfcount:
            raise Exception('The overall number of features ' + str(fsize) + ' is smaller than the desired number ' + str(desiredfcount) + ' of features to be selected.')
        
        su = np.sum(X, axis = 0).T
        
        allinds = []
        for ci in range(fsize):
            if su[ci] == 0:
                print 'WARNING: the feature number '+str(ci)+' has a zero norm.'
            else:
                allinds.append(ci)
        
        self.selected = []
        self.selected_plus_bias = []
        
        currentfcount = 0
        self.performances = []
        
        D = np.array(np.hstack([X, np.ones((tsize, 1))]))
        R = np.array(Y)[:, 0]
        B = np.zeros((0, fsize + 1), dtype = np.float64)
        alphavec = np.zeros(0)
        print
        while currentfcount < desiredfcount:
            
            besterrdiff = float('-Inf')
            
            Dnorms = np.sqrt(np.sum(np.multiply(D, D), axis = 0))
            DR = np.dot(D.T, R)
            dirs = np.divide(np.abs(DR), Dnorms)
            dirs[self.selected_plus_bias] = float('-Inf')
            bestind = np.argmax(dirs)
            if len(self.selected_plus_bias) == 0:
                bestind = fsize
            else:
                self.selected.append(bestind)
                currentfcount += 1
            self.selected_plus_bias.append(bestind)
                
            al = DR[bestind] / (Dnorms[bestind] * Dnorms[bestind])
            R = R - al * D[:, bestind]
            alphavec = alphavec - al * B[:, bestind].T
            alphavec = np.hstack([alphavec, al])
            betavec = np.zeros(fsize + 1)
            for i in range(fsize + 1):
                if i == bestind: continue
                betavec[i] = np.dot(D[:, bestind], D[:, i]) / (Dnorms[bestind] * Dnorms[bestind])
                D[:, i] = D[:, i] - betavec[i] * D[:, bestind]
                B[:, i] = B[:, i] - betavec[i] * B[:, bestind]
            
            D[:, bestind] = 0
            B[:, bestind] = 0
            betavec[bestind] = 1
            B = np.vstack([B, betavec])
            
            print self.selected, len(self.selected)
            print la.norm(np.multiply(R, R)) ** 2.
            
            self.W = alphavec[1:len(alphavec)]
            self.b = alphavec[0]
            if not self.callbackfun == None:
                self.callbackfun.callback(self)
        if not self.callbackfun == None:
            self.callbackfun.finished(self)
        print la.norm(np.array(Y)[:, 0] - np.dot(X[:, self.selected], self.W) - self.b) ** 2.
        self.resource_pool['selected_features'] = self.selected
        self.resource_pool['GreedyRLS_LOO_performances'] = self.performances
    
    
    def getModel(self):
        return predictor.LinearPredictor(self.W, self.b)

