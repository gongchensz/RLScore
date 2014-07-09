'''
Created on May 19, 2011

@author: aatapa
'''
import math

from numpy import mat, multiply, zeros, float64, ones
from scipy.sparse import csr_matrix
from numpy import matrix
from scipy.sparse.base import spmatrix
from math import sqrt
from scipy import sparse as sp
import numpy as np

from rlscore.utilities import decomposition
from rlscore import model
from rlscore.utilities import array_tools


class SvdAdapter(object):
    '''
    classdocs
    '''
    
    
    def createAdapter(cls, **kwargs):
        adapter = cls()
        svals, rsvecs, U, Z = adapter.decompositionFromPool(kwargs)
        if 'kernel_obj' in kwargs:
            adapter.kernel = kwargs['kernel_obj']
        adapter.svals = svals
        adapter.rsvecs = rsvecs
        adapter.U = U
        adapter.Z = Z
        if 'basis_vectors' in kwargs:
            adapter.basis_vectors = kwargs['basis_vectors']
        else:
            adapter.basis_vectors = None
        return adapter
    createAdapter = classmethod(createAdapter)
    
    
    def decompositionFromPool(self, rpool):
        """Builds decomposition representing the training data from resource pool.
        Default implementation
        builds and decomposes the kernel matrix itself (standard case), or the 
        empirical kernel map of the training data, if reduced set approximation is
        used. Inheriting classes may also re-implement this by decomposing the feature
        map of the data (e.g. linear kernel with low-dimensional data).
        @param rpool: resource pool
        @type rpool: dict
        @return: svals, evecs, U, Z
        @rtype: tuple of numpy matrices
        """
        train_X = rpool['train_features']
        kernel = rpool['kernel_obj']
        if rpool.has_key('basis_vectors'):
            basis_vectors = rpool['basis_vectors']
            K = kernel.getKM(train_X).T
            svals, evecs, U, Z = decomposition.decomposeSubsetKM(K, basis_vectors)
        else:
            K = kernel.getKM(train_X).T
            svals, evecs = decomposition.decomposeKernelMatrix(K)
            U, Z = None, None
        return svals, evecs, U, Z
    
    
    def reducedSetTransformation(self, A):
        if self.Z != None:
            #Maybe we could somehow guarantee that Z is always coupled with basis_vectors?
            A_red = self.Z * (self.U.T * multiply(self.svals.T,  self.rsvecs.T * A))
            return A_red
        else: return csr_matrix(A)
    
    
    def createModel(self, svdlearner):
        A = svdlearner.A
        A = self.reducedSetTransformation(A)
        mod = model.DualModel(A, self.kernel)
        return mod

class LinearSvdAdapter(SvdAdapter):
    '''
    classdocs
    '''
    
    
    def decompositionFromPool(self, rpool):
        kernel = rpool['kernel_obj']
        self.X = rpool['train_features']
        if rpool.has_key('basis_vectors'):
            basis_vectors = rpool['basis_vectors']
        else:
            basis_vectors = None
        if "bias" in rpool:
            self.bias = float(rpool["bias"])
        else:
            self.bias = 0.
        if basis_vectors != None or self.X.shape[1] > self.X.shape[0]:
            K = kernel.getKM(self.X).T
            #First possibility: subset of regressors has been invoked
            if basis_vectors != None:
                svals, evecs, U, Z = decomposition.decomposeSubsetKM(K, basis_vectors)
            #Second possibility: dual mode if more attributes than examples
            else:
                svals, evecs = decomposition.decomposeKernelMatrix(K)
                U, Z = None, None
        #Third possibility, primal decomposition
        else:
            #Invoking getPrimalDataMatrix adds the bias feature
            X = getPrimalDataMatrix(self.X,self.bias)
            svals, evecs, U = decomposition.decomposeDataMatrix(X.T)
            U, Z = None, None
        return svals, evecs, U, Z
    
    
    def createModel(self, svdlearner):
        A = svdlearner.A
        A = self.reducedSetTransformation(A)
        fs = self.X
        if self.basis_vectors != None:
            fs = self.X[self.basis_vectors]
        bias = self.bias
        X = getPrimalDataMatrix(fs, bias)
        #The hyperplane is a linear combination of the feature vectors of the basis examples
        W = X.T * A
        if bias != 0:
            W_biaz = W[W.shape[0]-1] * math.sqrt(bias)
            W_features = W[range(W.shape[0]-1)]
            mod = model.LinearModel(W_features, W_biaz)
        else:
            mod = model.LinearModel(W, 0.)
        return mod

def getPrimalDataMatrix(X, bias):
    """
    Constructs the feature representation of the data.
    If bias is defined, a bias feature with value
    sqrt(bias) is added to each example. This function
    should be used when making predictions, or training
    the primal formulation of the learner.
    @param X: matrix containing the data
    @type X: scipy.sparse.base.spmatrix
    @param dimensionality: dimensionality of the feature space
    (by default the number of rows in the data matrix)
    @type dimensionality: integer
    @return: data matrix
    @rtype: scipy sparse matrix in csc format
    """
    #if sp.issparse(X):
    #    X = X.todense()
    X = array_tools.as_dense_matrix(X)
    if bias!=0:
        bias_slice = sqrt(bias)*ones((X.shape[0],1),dtype=float64)
        X = np.hstack([X,bias_slice])
    return X

class PreloadedKernelMatrixSvdAdapter(SvdAdapter):
    '''
    classdocs
    '''
    
    
    def decompositionFromPool(self, rpool):
        K_train = rpool['kernel_matrix']
        if rpool.has_key('basis_vectors'):
            svals, rsvecs, U, Z = decomposition.decomposeSubsetKM(K_train, rpool['basis_vectors'])
        else:
            svals, rsvecs = decomposition.decomposeKernelMatrix(K_train)
            U, Z = None, None
        return svals, rsvecs, U, Z
    
    
    def createModel(self, svdlearner):
        A = svdlearner.A
        A = self.reducedSetTransformation(A)
        mod = model.LinearModel(A, 0.)
        return mod
