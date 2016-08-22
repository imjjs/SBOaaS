import numpy as np
from __GP_SE__ import GP_SE 
import logging

def find_average_error(Y,Y_,mu, var, N):

    # Y     is the original run time from the table
    # Y_    is the actuall run time.
    # mu     is the old avarage of error %
    # Var   is the error variance %
    # N     is the number of of feedback that have been used to calculate E
    recentE = float(Y_-Y)/Y
    N += 1
    deltaX = recentE - mu
    mu += deltaX/(N)
    if N > 1:
        M2 = var * (N-2)
        M2 += deltaX * (recentE- mu)
        var = M2/(N-1)
    else:
        var = 0

    std = var ** 0.5
    errorBias = mu + 1.5 * std
    return errorBias, mu, var, N



'''
def find_average_error(Y,Y_,E):

    #Y    is the original run time from the table 
    #Y_   is the actuall run time. 
    #E    is the old avarage of error
    recentE = (Y_ - Y)*1.0/Y
    if E == 0.0:
	E = recentE
    Enew = (E*5 + recentE )/6
    #Enew = recentE
    return Enew
'''

def estimate_exec_time_table(x_array, y_array, strategy):
	X = np.array(x_array)
	Y = np.array(y_array).flatten()
	if strategy == "1":
		logging.info("applying regresssion for strategy 1")
		hyp = [5000000.1, 0.5, 0.000005]
		n = 20000
	else:
		logging.info("applying regresssion for other strategy")
		hyp = [50000000000.1, 0.5, 0.0000005]
		n = 100000
	
	winSize = 1000
	Xtable, Ytable =  [0]*n, [0]*n
	for indx in range (0,  (n/winSize)):
	    Xstar = np.array(range((winSize*indx)+1, winSize*(indx+1)+1)).reshape(-1,1)
	    mu, s = GP_SE(hyp,X,Y,Xstar)
	    Ytable[Xstar[0]-1 : Xstar[winSize-1]] = mu
	return Ytable

