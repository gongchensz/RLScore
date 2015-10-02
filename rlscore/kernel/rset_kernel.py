'''
Created on May 22, 2011
@author: aatapa
'''

import numpy.linalg as la
import numpy as np

class RsetKernel(object):
    '''
    This class is for testing reduced set approximation.
    '''
    
    def __init__(self, base_kernel, train_features, basis_features):
        """Default implementation uses the scipy sparse matrices for internal representation of the data."""
        self.base_kernel = base_kernel
        Krr = self.base_kernel.getKM(basis_features)
        K_r = self.base_kernel.getKM(train_features)
        invKrr = la.inv(Krr)
        self.predcache = np.dot(K_r, invKrr)

    
    def getKM(self, test_X):
        Ktr = self.base_kernel.getKM(test_X)
        return np.dot(Ktr, self.predcache.T)
    
    