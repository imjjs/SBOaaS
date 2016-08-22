from __future__ import division
import numpy as np

""" This is code for simple GP regression. It assumes a zero mean GP Prior """
# Define the kernel
def _kernelSE(hyp, a, b):
    """ GP squared exponential kernel """
    kernelParameter = hyp[0]
    sqdist = np.sum(a**2,1).reshape(-1,1) + np.sum(b**2,1) - 2*np.dot(a, b.T)
    return (np.exp(-hyp[1] * (1/kernelParameter) * sqdist))



def GP_SE(hyp, X, Y, Xtest):
    #Inilizations
    s = hyp[2]    # noise variance.
    N = len(X)     # number of training points.
    try: 
        X = X.reshape(-1,1)
        K = _kernelSE(hyp, X, X) 
        L = np.linalg.cholesky(K + (s)*np.eye(N))
    except :   #add noise to X to prevent nonpositve define error#
        X = X.flatten() +   ((s/3)*np.random.randn(N))
        X = X.reshape(-1,1)
        K = _kernelSE(hyp, X, X) 
        #add the noise kernel
        L = np.linalg.cholesky(K + (s/3)*np.eye(N))        
    
    
    
    # points we're going to make predictions at.
    Xtest = Xtest.reshape(-1,1)
    
    # compute the mean at our test points.
    Lk = np.linalg.solve(L, _kernelSE(hyp, X, Xtest))
    mu = np.dot(Lk.T, np.linalg.solve(L, Y.flatten()))
    
    # compute the variance at our test points.
    K_ = _kernelSE(hyp, Xtest, Xtest)
    s2 = np.diag(K_) - np.sum(Lk**2, axis=0)
    s = np.sqrt(s2)
    return mu, s