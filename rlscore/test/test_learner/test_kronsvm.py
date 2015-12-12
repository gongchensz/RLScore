import unittest
import random as pyrandom


import cPickle
import numpy as np
from numpy import random as numpyrandom
from rlscore.kernel import LinearKernel
from rlscore.learner.kron_svm import KronSVM
from rlscore.pairwise_predictor import LinearPairwisePredictor
from rlscore.pairwise_predictor import KernelPairwisePredictor

from rlscore.utilities import sparse_kronecker_multiplication_tools_python

def dual_svm_objective(a, K1, K2, Y, rowind, colind, lamb):
    #dual form of the objective function for support vector machine
    #a: current dual solution
    #K1: samples x samples kernel matrix for domain 1
    #K2: samples x samples kernel matrix for domain 2
    #rowind: row indices for training pairs
    #colind: column indices for training pairs
    #lamb: regularization parameter
    P =  sparse_kronecker_multiplication_tools_python.compute_R_times_M_kron_N_times_C_times_v(a, K2, K1, rowind, colind, rowind, colind)
    z = (1. - Y*P)
    z = np.where(z>0, z, 0)
    Ka = sparse_kronecker_multiplication_tools_python.compute_R_times_M_kron_N_times_C_times_v(a, K2, K1, rowind, colind, rowind, colind)
    return 0.5*(np.dot(z,z)+lamb*np.dot(a, Ka))

def primal_svm_objective(w, X1, X2, Y, rowind, colind, lamb):
    #primal form of the objective function for support vector machine
    #w: current primal solution
    #X1: samples x features data matrix for domain 1
    #X2: samples x features data matrix for domain 2
    #rowind: row indices for training pairs
    #colind: column indices for training pairs
    #lamb: regularization parameter
    #P = np.dot(X,v)
    P = sparse_kronecker_multiplication_tools_python.x_gets_subset_of_A_kron_B_times_v(w, X2, X1.T, colind, rowind)
    z = (1. - Y*P)
    z = np.where(z>0, z, 0)
    return 0.5*(np.dot(z,z)+lamb*np.dot(w,w))

def load_data(primal=True, fold_index=0):
    fname =  "examples/data/FOLDS-nr-q4"
    f = open(fname)
    dfolds, tfolds = cPickle.load(f)
    dfold = dfolds[fold_index / 3]
    tfold = tfolds[fold_index % 3]
    Y = np.loadtxt('examples/data/nr_admat_dgc.txt')
    Y = np.where(Y>=0.5, 1., -1.)
    dtraininds = list(set(range(Y.shape[0])).difference(dfold))
    ttraininds = list(set(range(Y.shape[1])).difference(tfold))
    X1 = np.loadtxt('examples/data/nr_simmat_dc.txt')
    X2 = np.loadtxt('examples/data/nr_simmat_dg.txt')
    X1_train = X1[dtraininds, :]
    X2_train = X2[ttraininds, :]
    X1_test = X1[dfold,:]
    X2_test = X2[tfold,:]
    KT = np.mat(X2)
    KT = KT * KT.T
    KD = np.mat(X1)
    KD = KD * KD.T
    K1_train = KD[np.ix_(dtraininds, dtraininds)]
    K2_train = KT[np.ix_(ttraininds, ttraininds)]
    Y_train = Y[np.ix_(dtraininds, ttraininds)]
    K1_test = KD[np.ix_(dfold,dtraininds)]
    K2_test = KT[np.ix_(tfold,ttraininds)]
    Y_test = Y[np.ix_(dfold, tfold)]
    ssize = Y_train.shape[0]*Y_train.shape[1]*0.25
    rows = numpyrandom.random_integers(0, K1_train.shape[0]-1, ssize)
    cols = numpyrandom.random_integers(0, K2_train.shape[0]-1, ssize)
    ind = np.ravel_multi_index([rows, cols], (K1_train.shape[0], K2_train.shape[0]))
    Y_train = Y_train.ravel()[ind]
    Y_test = Y_test.ravel(order='F')
    if primal:
        return X1_train, X2_train, Y_train, rows, cols, X1_test, X2_test, Y_test
    else:
        return K1_train, K2_train, Y_train, rows, cols, K1_test, K2_test, Y_test

class Test(unittest.TestCase):
    
    def setUp(self):
        np.random.seed(55)
    
    

    def test_kronsvm(self):
        
        regparam = 0.01
        pyrandom.seed(100)
        numpyrandom.seed(100)      
        X1_train, X2_train, Y_train, rows, cols, X1_test, X2_test, Y_test = load_data(primal=True)

        
        class PrimalCallback(object):
            def __init__(self):
                self.iter = 0
            def callback(self, learner):
                X1 = learner.resource_pool['xmatrix1']
                X2 = learner.resource_pool['xmatrix2']
                rowind = learner.label_row_inds
                colind = learner.label_col_inds
                w = learner.W.ravel()
                loss = primal_svm_objective(w, X1, X2, Y_train, rowind, colind, regparam)
                #loss = learner.bestloss
                print "iteration", self.iter
                print "Primal SVM loss", loss
                self.iter += 1
            def finished(self, learner):
                pass        
        params = {}
        params["xmatrix1"] = X1_train
        params["xmatrix2"] = X2_train
        params["Y"] = Y_train
        params["label_row_inds"] = rows
        params["label_col_inds"] = cols
        params["maxiter"] = 100
        params["inneriter"] = 100
        params["regparam"] = regparam
        params['callback'] = PrimalCallback()  
        learner = KronSVM(**params)
        P_linear = learner.predictor.predict(X1_test, X2_test)

        pyrandom.seed(100)
        numpyrandom.seed(100)         
        K1_train, K2_train, Y_train, rows, cols, K1_test, K2_test, Y_test = load_data(primal=False)       
        
        class DualCallback(object):
            def __init__(self):
                self.iter = 0
                self.atol = None
    
            def callback(self, learner):
                K1 = learner.resource_pool['kmatrix1']
                K2 = learner.resource_pool['kmatrix2']
                rowind = learner.label_row_inds
                colind = learner.label_col_inds
                loss = dual_svm_objective(learner.A, K1, K2, Y_train, rowind, colind, regparam)
                #loss = learner.bestloss
                print "iteration", self.iter
                print "Dual SVM loss", loss
                #model = learner.predictor
                self.iter += 1
            def finished(self, learner):
                pass
        params = {}
        params["kmatrix1"] = K1_train
        params["kmatrix2"] = K2_train
        params["Y"] = Y_train
        params["label_row_inds"] = rows
        params["label_col_inds"] = cols
        params["maxiter"] = 100
        params["inneriter"] = 10
        params["regparam"] = regparam  
        params['callback'] = DualCallback()     
        learner = KronSVM(**params)
        rowind = learner.label_row_inds
        colind = learner.label_col_inds
        P_dual = learner.predictor.predict(K1_test, K2_test).ravel(order='F')
        assert np.max(1. - np.abs(P_linear / P_dual)) < 0.0001       




if __name__=="__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(Test)
    unittest.TextTestRunner(verbosity=2).run(suite)