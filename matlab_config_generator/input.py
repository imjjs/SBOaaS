#! /usr/bin/env python
###############################################
## Input Randomizer for DDDAS                ##
## 'tab' used for all indentation            ##
###############################################

import random

##############################################################################
##  Takes a list of lists as input, each sub list needs to be structured:   ##
##    [ MinTemp, MaxTemp, guessPercent (if any), uniformOrGauss(if any) ]   ##
##    for Uniform/Gaussian  1=Uniform, 2=Gaussian                           ##
##############################################################################
def calculateRandomizedStartPercentages(values):
	for counter in len(values):
		print "hello"

def getRandomHeatPercent(minPercent, maxPercent, guess=-1, curve=1, standardDeviation=3):

	if (curve == 1):
		return random.uniform(minPercent,maxPercent)
	elif (curve == 2):
		return random.gauss(guess,standardDeviation)
