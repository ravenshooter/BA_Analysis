'''
Created on 17.02.2016

@author: Steve
'''


import numpy
import matplotlib
import random
matplotlib.use('agg')

import matplotlib.pyplot as plt
import scipy
import mdp
import csv
import Oger
import datetime
from matplotlib.backends.backend_pdf import PdfPages
from DataSet import *
from sklearn.metrics import f1_score
from Evaluation import * 
import Evaluation
import os
from DataAnalysis import plot
from DataAnalysis import subPlot
from SparseNode import SparseNode


def getProjectPath():
    projectPath = 'C:\Users\Steve\Documents\Eclipse Projects\BA_Analysis\\'
    #projectPath = os.environ['HOME']+'/pythonProjects/BA_Analysis2/BA_Analysis/'
    return projectPath

def transformToDelta(vals):
    newVals = numpy.zeros((len(vals),len(vals[0])))
    for i in range(1,len(vals)):
        newVals[i-1] = vals[i]-vals[i-1]
    return newVals

def readFileToNumpy(fileName):
    reader=csv.reader(open(fileName,"rb"),delimiter=';')
    x=list(reader)
    return numpy.array(x[1:]).astype('float')

def centerAndNormalize(inputData):
    means = numpy.mean(inputData, 0)
    centered = inputData - means
    vars = numpy.std(centered, 0)
    normalized = centered/vars
    return normalized

def multiplyData(data, multiplier):
    newData = data
    for i in range(0,multiplier):
        newData = numpy.append(newData, data, 0)
        newData = numpy.append(newData, numpy.zeros((50,len(data[0]))), 0)
    return newData

def separateInputData(fileData):
    fused = numpy.atleast_2d(fileData[:,0:3])
    gyro = numpy.atleast_2d(fileData[:,3:6])
    acc = numpy.atleast_2d(fileData[:,6:9])
    targets = numpy.atleast_2d(fileData[:,9:])
    return fused, gyro, acc, targets

def runningAverage(inputData, width):
    inputData = numpy.atleast_2d(inputData)
    target = numpy.zeros((inputData.shape))
    for i in range(width,len(inputData-width)):
            target[i,:] = numpy.mean(inputData[i-width:i+width,:],0)
    return target

def writeToReportFile(text):
    print getProjectPath()+'results/report.csv'
    with open(getProjectPath()+'results/report.csv', 'ab') as csvfile:
        spamwriter = csv.writer(csvfile, delimiter=';',
                            quotechar='|', quoting=csv.QUOTE_MINIMAL)
        spamwriter.writerow(text)

def splitBySignals(dataStep):
#    pass
#if __name__ == '__main__':
    segments= []
    for input, target in dataStep:
        targetInt = np.argmax(addNoGestureSignal(target), 1)

        
        inds= np.append(np.where(targetInt[:-1]!= targetInt[1:]),[len(targetInt)-1])
        
        lastInd = -1
        for ind in inds:
            if targetInt[ind] != np.max(targetInt):
                iSegment = input[lastInd+1:ind+1]
                tSegement = target[lastInd+1:ind+1]
                tSegement[0,:]=0
                tSegement[-1,:]=0
                segments.append((iSegment,tSegement))
                lastInd = ind
    return segments

def shuffleDataStep(dataStep, nFolds):
    segs = splitBySignals(dataStep)
    random.shuffle(segs)
    segs = [ segs[i::nFolds] for i in xrange(nFolds) ]
    dataStep=[]
    for segList in segs:
        ind = np.concatenate([x[0] for x in segList],0)
        t   = np.concatenate([x[1] for x in segList],0)
        dataStep.append((ind,t))
    return dataStep

def calcWeightedAverage(input_signal, target_signal):
    global tresholdF1
    
    nDataPoints = len(input_signal.flatten())
    signals = []
    signalValue = 0
    nSignalPoints = 0
    for i in range(1,nDataPoints):
        if target_signal[i] == 1:
            signalValue = signalValue + input_signal[i]
            nSignalPoints = nSignalPoints+1
        elif target_signal[i] == 0 & target_signal[i-1] == 1:
            signals.append(signalValue/nSignalPoints)
            signalValue = 0
            nSignalPoints = 0
        else:
            pass
            
            
def calcSingleValueF1Score(input_signal, target_signal):
    nDataPoints = len(input_signal.flatten())
    bin_input_signal = numpy.ones((nDataPoints,1))
    bin_input_signal[input_signal < 0] = 0
    bin_target_signal = numpy.ones((nDataPoints,1))
    bin_target_signal[input_signal < 0] = 0
    score = f1_score(target_signal.astype('int'),bin_input_signal.astype('int'),average='binary')
    return 1-score

def calcSingleGestureF1Score(input_signal, target_signal):
    treshold = 0.5
    nDataPoints = len(input_signal)
    t_target = numpy.copy(target_signal)
    n_truePositive = 0
    n_falsePositive = 0
    i = 0
    while i < nDataPoints:
        n_true = 0
        n_false = 0
        removeTargetSignal = False
        while i < nDataPoints and input_signal[i] > treshold:
            if t_target[i] == 1:
                n_true = n_true + 1
            else: 
                n_false = n_false +1
            i = i+1
        if n_true > n_false:
            n_truePositive = n_truePositive + 1
            removeTargetSignal = True
        elif n_true < n_false:
            n_falsePositive = n_falsePositive + 1
        if removeTargetSignal:
            j = i
            while (j < nDataPoints) and (t_target[j] == 1) :   #remove this positive
                t_target[j] = 0
                j = j+1
        i = i+1
    
    
    n_totalPositives = 0
    lastVal = 0
    for i in range(0,nDataPoints):
        if target_signal[i] > lastVal:
            n_totalPositives = n_totalPositives+1
        lastVal = target_signal[i] 
    n_falseNegative = n_totalPositives - n_truePositive
    
    f1 = (2.*n_truePositive)/(2.*n_truePositive + n_falseNegative + n_falsePositive)
    print 1-f1   
    return 1-f1


def showMissClassifiedGesture(testSetNr,act,pred):
    mcInds = missClassifiedGestures[testSetNr][act][pred]
    data = randTestSets[testSetNr].getDataForTraining(usedGestures,2)[0]
    mcDatas = []
    for mcInd in mcInds:
        mcData = data[mcInd[0]:mcInd[1],:]
        mcDatas.append(mcData)
    subPlot(mcDatas[:5])



def w_in_init_function(output_dim, input_dim):
    w_in = numpy.ones((output_dim,input_dim))*1.7
    rand = np.random.random(w_in.shape)<0.8
    w_in[rand]= 0
    
    for i in range(input_dim):
        w_in[np.random.randint(output_dim),i]=1.7

    return w_in


def evaluateTestFile(iFile,inputGestures,usedGestures, bestFlow, tresholds, f1Scores,f1BestPossibleScores, f1ppScores, f1maxAppScores, f1maxAppBestPossibleScores, levs, levs_pp, pp):
    testData = createData(iFile, inputGestures, usedGestures)
    if shuffle:
        testData = shuffleDataStep([testData], 1)[0]
       
    t_target = testData[1]
    t_prediction = bestFlow(testData[0])
    t_maxApp_prediction = calcMaxActivityPrediction(t_prediction,t_target,0.5,10)
    #t_prediction = t_maxApp_prediction
    t_pp_prediction = postProcessPrediction(t_prediction, tresholds)
    _, bestPossibleMaxAppF1Score,_ =  calcTPFPForThresholds(t_prediction, t_target, iFile+' - target treshold', False)
    pp.savefig()
    _, bestPossibleF1Score,_ =  calcTPFPForThresholds(t_prediction, t_target, iFile+' - target treshold', True)
    
    lev = calcLevenshteinError(t_prediction, t_target, 0.4)
    lev_pp = calcLevenshteinError(t_pp_prediction, t_target, 0.05)
    levs.append(lev)
    levs_pp.append(lev_pp)
    fig = plt.figure(figsize=(30,30))
    fig.suptitle(iFile)
    plt.clf()
    ax1 = plt.subplot(211)
    plt.title('Prediction on test ' +iFile)
    cmap = mpl.cm.jet
    for i in range(t_prediction.shape[1]):
        plt.plot(t_prediction[:,i],c=cmap(float(i)/prediction.shape[1]),label=totalGestureNames[usedGestures[i]],linewidth=3)
        plt.fill_between(range(len(t_prediction)), 1.4, 1.6, where=testData[1][:,i]==1,facecolor=cmap(float(i)/prediction.shape[1]), alpha=0.7)
        plt.fill_between(range(len(t_prediction)), 1.2, 1.4, where=t_prediction[:,i]==np.max(addTresholdSignal(t_prediction,0.4),1),facecolor=cmap(float(i)/prediction.shape[1]), alpha=0.7)
        plt.fill_between(range(len(t_prediction)), 1.0, 1.2, where=t_maxApp_prediction[:,i]==1,facecolor=cmap(float(i)/prediction.shape[1]), alpha=0.7)
        
        #plt.plot(testData[1][:,i],c=cmap(float(i)/prediction.shape[1]))
        plt.fill_between(range(len(t_prediction)), 0, t_prediction[:,i], where=t_prediction[:,i]==np.max(t_prediction,1), facecolor=cmap(float(i)/prediction.shape[1]), alpha=0.5)
    for limCounter in range(5):
        plt.annotate('Target', xy=(limCounter*1000,1.45))
        plt.annotate('Max Signal Prediction',xy=(limCounter*1000,1.25))
        plt.annotate('Activity Treshold Prediction',xy=(limCounter*1000,1.05))
    plt.legend()
    plt.subplot(212, sharex=ax1)
    plt.title('Input')
    if(bestFlow[0].useNormalized==1):
        plt.plot(testData[0][:,0:3]/reservoir.colStdFactor[0:3],label='Fused')
        plt.plot(testData[0][:,3:6]/reservoir.colStdFactor[3:6],label='Rot')
        plt.plot(testData[0][:,6:9]/reservoir.colStdFactor[6:9],label='Acc')
    elif (bestFlow[0].useNormalized==2):
        plt.plot(testData[0][:,0:3]/reservoir.colMaxFactor[0:3],label='Fused')
        plt.plot(testData[0][:,3:6]/reservoir.colMaxFactor[3:6],label='Rot')
        plt.plot(testData[0][:,6:9]/reservoir.colMaxFactor[6:9],label='Acc')
    plt.plot(np.sum(np.abs(bestFlow[0].states),1)/100,label='Res Energy /100')
    #plt.plot(testData[1])
    plt.legend()
    
    for limCounter in range(5):
        
        
        plt.xlim(limCounter*1000,(limCounter+1)*1000)
        pp.savefig()
     
    pred, targ = calcInputSegmentSeries(t_prediction, t_target, 0.4, False)
    pp_pred, pp_targ = calcInputSegmentSeries(t_pp_prediction, t_target, 0.05, False)
    pred_maxApp, targ_maxApp = calcInputSegmentSeries(t_maxApp_prediction, t_target, 0.5)
    
    cm = sklearn.metrics.confusion_matrix(targ, pred)
    confMatrices.append(cm)
    fig1 = plot_confusion_matrix(cm,gestureNames,iFile)
    pp.savefig()
     
    pp_cm = sklearn.metrics.confusion_matrix(pp_targ, pp_pred)
    fig2 = plot_confusion_matrix(pp_cm,gestureNames,'pp_'+iFile)
    pp.savefig()
    
    maxApp_cm = sklearn.metrics.confusion_matrix(targ_maxApp, pred_maxApp)
    plot_confusion_matrix(maxApp_cm,gestureNames,'maxApp_'+iFile)
    pp.savefig()
    
    
    f1 = np.mean(sklearn.metrics.f1_score(targ,pred,average=None))
    f1_pp = np.mean(sklearn.metrics.f1_score(pp_targ,pp_pred,average=None))
    f1_maxApp = np.mean(sklearn.metrics.f1_score(targ_maxApp,pred_maxApp,average=None))
        
    f1Scores.append(f1)
    f1ppScores.append(f1_pp)
    f1maxAppBestPossibleScores.append(bestPossibleMaxAppF1Score)
    f1BestPossibleScores.append(bestPossibleF1Score)
    f1ScoreNames.append(iFile)    
    f1maxAppScores.append(f1_maxApp)
    
    return t_target,t_prediction, t_pp_prediction, t_maxApp_prediction


#def main(name, concFactor):
#     pass  

if __name__ == '__main__':
    matplotlib.rcParams.update({'font.size': 20})
    
    #name = 'Test'
    name = input('name')
    normalized = False
    nmse = False
    inputGestures = [0,1,2,3,4,5,6,7,8,9]
    usedGestures = [0,1,2,3,4,5,6,7,8,9]
    concFactor = 1
    noiseFactor = 1
    nFolds = 4
    shuffle = True
    
    plt.switch_backend('Qt4Agg')

    plt.close('all')
    now = datetime.datetime.now()
    resultsPath = getProjectPath()+'results/'
    pdfFileName = now.strftime("%Y-%m-%d-%H-%M")+'_'+name+'.pdf'
    pdfFilePath = resultsPath+'pdf/'+pdfFileName
    npzFileName = now.strftime("%Y-%m-%d-%H-%M")+'_'+name+'.npz'
    npzFilePath = resultsPath+'npz/'+npzFileName
    bestFlowPath = resultsPath+'nodes/'+now.strftime("%Y-%m-%d-%H-%M")+'_'+name+'.p'
    
    totalGestureNames = ['left','right','forward','backward','bounce up','bounce down','turn left','turn right','shake lr','shake ud', \
                         'tap 1','tap 2','tap 3','tap 4','tap 5','tap 6','no gesture']
    gestureNames = []
    for i in usedGestures:
        gestureNames.append(totalGestureNames[i])
    gestureNames.append('no gesture')
    
     
    inputFiles = ['line','stephan','julian','nadja']
    
    #inputFiles = ['nadja_0_1.npz', 'nadja_0_2.npz', 'nadja_0_3.npz']
    testFiles = ['nike']
    #randTestFiles = ['lana_0_0.npz','lana_1_0.npz','stephan_0_2.npz','stephan_1_2.npz']
    randTestFiles = []
    
    pp = PdfPages(pdfFilePath)
    

    trainSets = []
    randTestSets = []
    dataStep = []
    
    for fileName in inputFiles:
        ind, t  = createData(fileName, inputGestures,usedGestures)
        dataStep.append((ind,t))
        
    if(shuffle):
        dataStep = shuffleDataStep(dataStep, nFolds)
    
    
    ## stretch testset
    newDataStep = []
    for ind, t in dataStep:
        
        indSets = []
        tSets = []
        for concer in range(concFactor):
            indSets.append(ind)
            tSets.append(t)
        ind = np.concatenate(indSets,0)
        t = np.concatenate(tSets,0)
        if noiseFactor > 0:
            for i in ind:
                i[0:3] = i[0:3]+np.random.normal(0,0.05 *noiseFactor)
                i[3:6] = i[3:6]+np.random.normal(0,0.5 * noiseFactor)
                i[6:9] = i[6:9]+np.random.normal(0,1.25 * noiseFactor)
        newDataStep.append((ind,t))
    dataStep = newDataStep
        ## no gesture as single class
        #   t = np.append(t,np.subtract(np.ones((t.shape[0],1)),np.max(t,1,None,True)),1)
            
            
    data=[dataStep,dataStep]

    for iFile in randTestFiles:
        randTestSets.append(createDataSetFromFile(iFile))
    #data = [[b.getDataForTraining(useFused, useGyro, useAcc, 2),c.getDataForTraining(useFused, useGyro, useAcc, 2),d.getDataForTraining(useFused, useGyro, useAcc, 2)], \
    #        [b.getDataForTraining(useFused, useGyro, useAcc, 2),c.getDataForTraining(useFused, useGyro, useAcc, 2),d.getDataForTraining(useFused, useGyro, useAcc, 2)]]












    #---------------------------------------------------------------------------------------------------#
    #--------------------------------------------GRIDSEARCH---------------------------------------------#
    #---------------------------------------------------------------------------------------------------#  

    ######
    #   gridsearch_parameters = {reservoir:{'spectral_radius':mdp.numx.arange(0.6, 1.1, 0.1),'output_dim':[1,40,400,401],'input_scaling': mdp.numx.arange(0.1, 1.1, 0.1),'_instance':range(6)},readoutnode:{'ridge_param':[0.0000001,0.000001,0.00001,0.001]}}
    ######
    reservoir = SparseNode()
    reservoir.updateInputScaling(dataStep)
    readoutnode = Oger.nodes.RidgeRegressionNode()
    flow = mdp.Flow( [reservoir,readoutnode])
    
    
    gridsearch_parameters = {reservoir:{'useSparse':[True], \
                                        'inputSignals':['FGA'], \
                                        'useNormalized':[2], \
                                        'leak_rate':[0.3], \
                                        'spectral_radius':[0.99], \
                                        'output_dim':[400], \
                                         'input_scaling':[6], \
                                        '_instance':range(4)}, \
                             readoutnode:{'ridge_param':[2]}} 
    gridsearch_parameters = {reservoir:{'useSparse':[True], \
                                        'inputSignals':['FGA'], \
                                        'useNormalized':[2], \
                                        'leak_rate':[0.2], \
                                        'spectral_radius':[0.9], \
                                        'output_dim':[400], \
                                         'input_scaling':[10], \
                                        '_instance':range(5)}, \
                             readoutnode:{'ridge_param':[4]}} 
    
    if nmse:
        opt = Oger.evaluation.Optimizer(gridsearch_parameters, Oger.utils.nrmse)
    else:
        #opt = Oger.evaluation.Optimizer(gridsearch_parameters, Evaluation.calc1MinusF1Average)
        #opt = Oger.evaluation.Optimizer(gridsearch_parameters, Evaluation.calc1MinusF1FromInputSegment)    
        #opt = Oger.evaluation.Optimizer(gridsearch_parameters, Oger.utils.nmse)
        opt = Oger.evaluation.Optimizer(gridsearch_parameters, Evaluation.calcLevenshteinError)    
        
        
    #opt.scheduler = mdp.parallel.ProcessScheduler(n_processes=2, verbose=True)
    #opt.scheduler = mdp.parallel.pp_support.LocalPPScheduler(ncpus=2, max_queue_length=0, verbose=True)
    #mdp.activate_extension("parallel")
    opt.grid_search(data, flow, n_folds=nFolds, cross_validate_function=Oger.evaluation.n_fold_random)
    

    

    
#    if gridsearch_parameters.has_key(readoutnode):
#        plt.figure()
#        opt.plot_results([(reservoir, '_instance'),(reservoir, 'output_dim'),(readoutnode, 'ridge_param')],plot_variance=False)
#        pp.savefig()
#        plt.figure()
#        opt.plot_results([(reservoir, '_instance'),(reservoir, 'input_scaling'),(reservoir, 'spectral_radius')],plot_variance=False)
#        pp.savefig()
#    else:
#        opt.plot_results([(reservoir, '_instance')],plot_variance=False)
        
    plotMinErrors(opt.errors, opt.parameters, opt.parameter_ranges, pp)
    
    i = 0
    inputSignalAxis = -1
    inputScalingAxis = -1
    normAxis = -1
    
    for node , param in opt.parameters:
        if param == 'inputSignals':
            inputSignalAxis = i
        elif param == 'input_scaling':
            inputScalingAxis = i
        elif param == 'useNormalized':
            normAxis = i
        i =i+1
    
    if normAxis != -1:
        if inputSignalAxis != -1:
            if inputScalingAxis != -1:
                plotAlongAxisErrors(opt.errors, opt.parameters, opt.parameter_ranges, normAxis, inputSignalAxis, inputScalingAxis, pp)
    
    bestFlow = opt.get_optimal_flow(True)
    
    
    
    bestFlow.train(data)
    
    
    #---------------------------------------------------------------------------------------------------#
    #---------------------------------------------TRAIN EVAL--------------------------------------------#
    #---------------------------------------------------------------------------------------------------# 

    
    nInputFiles = len(inputFiles)
    fig, axes = plt.subplots(nInputFiles, 1, sharex=True, figsize=(20,20))
    plt.tight_layout()
    plt.title('Prediction on training')  
    i = 0 
    trainCms = []
    trainPredicitions = []
    trainTargets = []
    for row in axes:
        prediction = bestFlow([data[0][i][0]])
        t_target = data[0][i][1]
        #visCalcConfusionFromMaxTargetSignal(prediction, t_target)
        row.set_title(inputFiles[i])
        row.plot(prediction)
        row.plot(numpy.atleast_2d(data[0][i][1]))
        pred, targ = calcInputSegmentSeries(prediction, t_target, 0.4, False)
        conf = sklearn.metrics.confusion_matrix(targ, pred)
        trainCms.append(conf)
        trainPredicitions.append(prediction)
        trainTargets.append(t_target)
        i = i+1
    #plt.plot(data[0][0][0])
    pp.savefig()
   
    
    
    for fileName,trainCm in zip(inputFiles,trainCms):
        plot_confusion_matrix(trainCm, gestureNames, 'trainging: '+fileName)
        pp.savefig()
   
   
    totalTrainInputData = [x[0] for x in dataStep]
    totalTrainTargetData = [x[1] for x in dataStep]
    totalTrainInputData = np.concatenate(totalTrainInputData,0)
    totalTrainTargetData = np.concatenate(totalTrainTargetData,0)
    totalTrainPrediction = bestFlow(totalTrainInputData)
    tresholds, _,_= calcTPFPForThresholds(totalTrainPrediction, totalTrainTargetData, 'Train Data Confusion - Target Treshold', False)
    pp.savefig()
   
    #---------------------------------------------------------------------------------------------------#
    #----------------------------------------------TESTING----------------------------------------------#
    #---------------------------------------------------------------------------------------------------#  
   
    confMatrices = []
    missClassifiedGestures = []
    f1Scores = []
    f1BestPossibleScores = []
    f1ppScores = []
    f1maxAppScores = []
    f1maxAppBestPossibleScores= []
    f1ScoreNames = []
    levs = []
    levs_pp = []
    for set, setName in zip(randTestSets,randTestFiles):
        #set = DataSet.appendDataSets(set,DataSet.createDataSetFromFile('stephan_1_0.npz'))
        t_prediction = bestFlow([set.getDataForTraining(usedGestures, 2)[0]])
        t_target = set.getDataForTraining(usedGestures,2)[1]
        fig = plt.figure()
        fig.suptitle(setName)
        plt.clf()
        plt.subplot(211)
        plt.title('Prediction on test ' +setName)
        plt.plot(t_prediction)
        plt.plot(set.getDataForTraining(usedGestures,2)[1])
        plt.subplot(212)
        plt.title('Smoothed prediction')
        plt.plot(runningAverage(t_prediction, 10))
        plt.plot(set.getDataForTraining(usedGestures,2)[1])
        pp.savefig()
        print setName
        pred, targ = calcInputSegmentSeries(t_prediction, t_target, 0.4, False)
        cm = sklearn.metrics.confusion_matrix(targ, pred)
        f1,_ = calcF1ScoreFromConfusionMatrix(cm,True)
        confMatrices.append(cm)
        f1Scores.append(f1)
        f1ScoreNames.append(setName)
        f1ppScores.append(-1)
        plot_confusion_matrix(cm,gestureNames,setName + ' - full gesture ranking')
        pp.savefig()

    
    for iFile in testFiles:
        t_target,t_prediction, t_pp_prediction, t_maxApp_prediction = evaluateTestFile(iFile,inputGestures,usedGestures, bestFlow, tresholds, f1Scores,f1BestPossibleScores, f1ppScores, f1maxAppScores, f1maxAppBestPossibleScores, levs, levs_pp, pp)
        
    
    totalCm = confMatrices[0]
    for cm in confMatrices[1:]:
        totalCm = totalCm+cm
    plot_confusion_matrix(totalCm,gestureNames,'total test confusion')    
    pp.savefig()
    visCM = np.copy(totalCm)
    plot_confusion_matrix(visCM,gestureNames,'total test confusion')    
    pp.savefig()
    
    
    

    
    pp.close();  
    #plt.close('all')
    
    print pdfFilePath    
    #---------------------------------------------------------------------------------------------------#
    #-----------------------------------------------REPORT----------------------------------------------#
    #---------------------------------------------------------------------------------------------------#  

    inFiles = inputFiles
    result = [str(now),name,inputFiles,testFiles,opt.loss_function, \
              'TrainError',str(opt.get_minimal_error()[0]), 'meanF1Score', f1Scores, 'maxPosF1Score',f1BestPossibleScores,'meanPPF1Score',f1ppScores,'maxAppF1Score',f1maxAppScores,'bestPossibleMaxAppF1',f1maxAppBestPossibleScores,\
              'Levenshtein',levs,'Levenshtein_pp',levs_pp]
    

    result.extend(['inputGestures',inputGestures])
    result.extend(['usedGestures',usedGestures])
    result.extend(['stretchFactor',concFactor])
    result.extend(['noiseFactor',noiseFactor])
    
      
    minErrDict = opt.get_minimal_error()[1]
    sparseDict = minErrDict.get(reservoir)
    ridgeDict = minErrDict.get(readoutnode)
    
    for para in ['_instance','inputSignals','useNormalized','input_scaling','output_dim','spectral_radius','useSparse','leak_rate','ridge_param']:
        result.append(para)
        if sparseDict is not None and sparseDict.has_key(para):
            result.append(sparseDict.get(para)) 
        elif ridgeDict is not None and ridgeDict.has_key(para):
            result.append(ridgeDict.get(para)) 
        else:
            result.append('')
     
     
     
    print 'w outputdim:' + str(bestFlow[0].w.shape)
     
    
    for a in opt.get_minimal_error()[1].iterkeys():
        result.append(a)
        for attribute in opt.get_minimal_error()[1].get(a).iterkeys():
            result.append(attribute)
            result.append('['+str(opt.get_minimal_error()[1].get(a).get(attribute))+']')
            
            




    result.append('gridSpace:')
    for a in opt.optimization_dict.get(reservoir).iterkeys():
        result.append(a)
        result.append(opt.optimization_dict.get(reservoir).get(a))
    if(opt.optimization_dict.get(readoutnode) != None):
        for a in opt.optimization_dict.get(readoutnode).iterkeys():
            result.append(a)
            result.append(str(opt.optimization_dict.get(readoutnode).get(a)))

    result.extend(['paraList',opt.parameter_ranges])
    #result.extend(['errors',numpy.array2string(opt.errors).replace('\n', ',').replace('  ',',').replace(',,',',').replace(',,',',')])
    


    
    result.append('=HYPERLINK(\"'+pdfFilePath+'\")')
    result.append('=HYPERLINK(\"'+npzFilePath+'\")')
    result.append('=HYPERLINK(\"'+bestFlowPath+'\")')
    
    if name != 'test':
        writeToReportFile(result)
        np.savez(npzFilePath,errors=opt.errors,params=opt.parameters,paraRanges=opt.parameter_ranges,randTestFiles=randTestFiles,\
                 confMatrices=confMatrices, \
                 testFileList=randTestFiles,\
                 f1Scores=f1Scores,\
                 f1ScoreNames=f1ScoreNames,\
                 bestRes_w_in=bestFlow[0].w_in, \
                 bestRes_w=bestFlow[0].w, \
                 )
        bestFlow.save(bestFlowPath)
        

    print 'f1test:' + str(zip(f1ScoreNames,f1Scores))

    #return bestFlow, opt
    #return fig1, fig2

def bla():
#if __name__ == '__main__':
    #main('a_NMSE_F',True,False,False)
    #print 'one done'
    #main('a_NMSE_G',False,True,False)  
    #print 'two done'
    #main('a_NMSE_A',False,False,True)  
    #print '3 done' 
    #main('a_NMSE_FA',True,False,True)
    #print '4 done'

    #main('noise_noconc_julian',['line','stephan','nike','nadja'],['julian'])
    #main('noise_noconc_nadja',['julian','line','stephan','nike'],['nadja'])
    #main('noise_noconc_nike',['nadja','julian','line','stephan'],['nike'])
    #main('noise_noconc_stephan',['nike','nadja','julian','line'],['stephan'])
    #main('test',['stephan','nike','nadja','julian'],['line'])
    #main('conc1',1)
    #main('conc2',2)
    #main('conc4',4)
    #main('conc8',8)
    #main('conc16',16)
    main('same',1)
    main('same',1)
    main('same',1)
    #main('test',1)
def bla(): 
    pdfFileName ='resSizeInfluence.pdf'
    resultsPath = getProjectPath()+'results/'
    pdfFilePath = resultsPath+'pdf/'+pdfFileName
    pp = PdfPages(pdfFilePath)
    
    for out in [10,20,30,40,60]:
        fig1, fig2 = main(out)
        pp.savefig(fig1)
        pp.savefig(fig2)
        
    
    pp.close()
    