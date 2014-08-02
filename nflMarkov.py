#!/usr/bin/env python

import pylab
import os, sys
import re
import pickle
import numpy
import copy
from scipy import interpolate
import scipy.sparse
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib
from matplotlib import pyplot as plt

############################
class nflMarkov:
    
    def getExpectedPoints(self, state):
        i = self.state2int[state]
        return self.expectedPoints[i,0]

#########################
    def makeHeatmap(self, dwns=[1,2,3]
                    , htype='expectedPoints'
                    , ytgmin = 1, ytgmax = 20
                    , yfogmin=1, yfogmax = 99
                    , vbose = 0, ishow=False):
        nytg = ytgmax-ytgmin+1
        nyfog = yfogmax-yfogmin+1
        ndwns = len(dwns)
        nrows = ndwns*nytg + (ndwns-1)
        ncols = nyfog
        mm = pylab.zeros((nrows, ncols))
        
        row_cnt = 0
        
        yt = []
        ylabs = []

        for dwn_cnt, idwn in enumerate(dwns):
            for c, i in enumerate(list(pylab.array([4,9,14])+dwn_cnt*20)):
                yt.append(i+0.5)
                ylabs.append((c+1)*5)
            for iytg in range(ytgmin, ytgmax+1):            
                col_cnt = 0
                for iyfog in range(yfogmin, yfogmax+1):
                    state = self.infoToState(idwn, iytg, iyfog)
#                    print idwn, iytg, iyfog, state

                    if htype=='expectedPoints':
                        val = self.getExpectedPoints(state)
                    elif htype=='ydist':
                        # this option doesnt work yet.
                        ydist = self.getYardsDist(state, modelType=self.modelType)
                        ks = ydist.keys()
                        ks.sort()
                        for i in ks:
                            xx.append(i)
                            yy.append(ydist[i])

                    else:
                        raise Exception

                    mm[row_cnt, col_cnt] = val
                    col_cnt += 1
                row_cnt += 1
            row_cnt += 1


        pylab.pcolor(mm, cmap=plt.cm.Blues_r)
        ax = pylab.gca()
        if vbose>=1:
            print yt
            print ylabs
            
        ax.set_yticks(yt, minor=False)

        tmp = list(pylab.ylim())
        tmp.sort()
        pylab.ylim(tuple(tmp[::-1]))

        ax.set_yticklabels(ylabs, minor=False, size='xx-small')
        pylab.ylabel('yards-to-go')
        pylab.xlabel('yards-from-own-goal')

        pylab.title(htype + ' (downs %d-%d)' % (dwns[0], dwns[-1]))
        if ishow:
            pylab.show()
        return mm


    def __init__(self
                 , paramFile=None
                 , transitionMatrixFile=None
                 ):

        self.pdfDir = './diagnosticPlots'
        self.inDataDir = './inputData'
        self.outDataDir = './outputData'

        self.vbose = 0
        self.minYd = -20

        self.transitionMatrixFile = transitionMatrixFile
        self.transitionMatrix = None
        self.resultMatrix = None
        self.expectedPoints = None
        self.enumerateStates = None
        self.endStates = ['S', 'TO', 'FG', 'TD'] + ['Sm', 'TOm', 'FGm', 'TDm']
        self.endStatePoints = [-2, 0, 3, 7, +2, 0, -3, -7]
        self.initProb = {}
        self.modelType = None
        self.modelName = None

        self.doSparse = False

        self.state2int = {}
        self.int2state = {}

        self.initEnumerateStates()
        self.initTransitionMatrix()
        
        self.empInit_2002_2010 = False
        self.empInit_2009_2013 = False
        self.emp_2002_2010 = None
        self.emp_2009_2013 = None

        self.storedModels = {}
        self.defaultParamFile = 'nm.default.params.txt'
        self.paramFile = paramFile
        self.params = {}

        self.initParams()

        self.modelFunctions = {}

        self.fparsP = {}
        self.fparsR = {}

        self.fvalsP = {}
        self.fvalsR = {}

        # probfunctionvals has indices 
        # [type][dwn][idx_ytg][yfog]
        
        self.probFuncVals = {}

        self.ytgIdx = {}


    def getYtgIdx(self, ptype, ytg):
        if not ptype in self.ytgIdx:
            self.ytgIdx[ptype] = {}
        if not ytg in self.ytgIdx[ptype]:
            self.ytgIdx[ptype][ytg] = None

        return ytg

    def createModelFunctions(self, params=None):
        if params is None:
            params = self.params
        
        self.modelFunctions = {}

        for k in params:
            if k=='interp-type':
                continue

            if self.vbose>=1:
                print 'create k', k
                print 'params[k]', params[k]
            xx = {}
            yy = {}
            icols = params[k].keys()
            icols.sort()

            ncols = len(icols)
            ndata = len(params[k][icols[0]])

            if self.vbose>=1:
                print 'icols', icols, ncols, ndata
                print k, params[k]

            for idata in range(ndata):
                dwn = params[k][0][idata]
                ytgMin = params[k][1][idata]
                ytgMax = params[k][2][idata]
                yfog = params[k][3][idata]

                if not dwn in yy:
                    yy[dwn] = {}
                    xx[dwn] = {}

                for iytg in range(ytgMin, ytgMax+1):
                    if not iytg in yy[dwn]:
                        yy[dwn][iytg] = {}
                        xx[dwn][iytg] = {}

                    for iy in range(4, ncols):
                        if not iy in yy[dwn][iytg]:
                            yy[dwn][iytg][iy] = []
                            xx[dwn][iytg][iy] = []
                        if self.vbose>=1:
                            print k, dwn, iytg, iy, params[k]
                        yy[dwn][iytg][iy].append(params[k][iy][idata])
                        xx[dwn][iytg][iy].append(yfog)

# May 11, 2014
# change it so that all functions have the same signature
#    0    1      2      3     4     5
# name down ytgMin ytgMax  yfog value(s)
# if down = 0 it means 1-4 are all the same.
            dwns = yy.keys()
            dwns.sort()
            
            for dwn in dwns:
                iytgs = yy[dwn].keys()
                for iytg in iytgs:
                    icols = yy[dwn][iytg].keys()
                    for icol in icols:
                        if self.vbose>=1:
                            print 'with k=', k, 'dwn=', dwn, 'iytg', iytg, 'at icol=', icol, 'creating interp function with '
                            print 'xx= ', xx[dwn][iytg][icol]
                            print 'yy= ', yy[dwn][iytg][icol]
                        interpFunc = \
                            interpolate.interp1d(xx[dwn][iytg][icol], 
                                                 yy[dwn][iytg][icol],
                                                 kind='linear', 
                                                 copy=False,
                                                 bounds_error=False, 
                                                 fill_value=0
                                                 )

                        if not k in self.modelFunctions:
                            self.modelFunctions[k] = {}
                        if not dwn in self.modelFunctions[k]:
                            self.modelFunctions[k][dwn] = {}
                        if not iytg in self.modelFunctions[k][dwn]:
                            self.modelFunctions[k][dwn][iytg] = {}
                        if not icol in self.modelFunctions[k][dwn][iytg]:
                            self.modelFunctions[k][dwn][iytg][icol] = interpFunc

                        if dwn==0:
                            for idwn in [1,2,3,4]:
                                if not k in self.modelFunctions:
                                    self.modelFunctions[k] = {}
                                if not idwn in self.modelFunctions[k]:
                                    self.modelFunctions[k][idwn] = {}
                                if not iytg in self.modelFunctions[k][idwn]:
                                    self.modelFunctions[k][idwn][iytg] = {}
                                if not icol in self.modelFunctions[k][idwn][iytg]:
                                    self.modelFunctions[k][idwn][iytg][icol] = interpFunc

        if self.vbose>=2:
            print 'modelFunctions:', self.modelFunctions

    def makeDiagnosticPlots(self, pdfFile=None):
        if pdfFile is None:
            pdfFile = self.pdfDir + '/' + self.modelName + '.pdf'

        pdf = PdfPages(pdfFile)

        # plot TO and FG probs
        # use 4th and 1
        xx = []
        tt = []
        ff = []
        gfps = []

        for i in range(1, 99):
            dwn = 4
            ytg = 1
            state = '4_%02d_%02d_00' % (ytg, i)
            #            print i, state
            t = self.getProb(state, probType='TO', modelType=self.modelType) 
            f = self.getProb(state, probType='FG', modelType=self.modelType) 
            xx.append(i)
            tt.append(t)
            ff.append(f)
            
            # only go for it if past the threshold,
            k = '4thGoForItThresh'
            idx = self.getYtgIdx(k, ytg)
            self.addProbFuncVal(k, dwn, ytg, i)
            gthresh = self.probFuncVals[k][dwn][idx][i]

            # how often do we go for it?
            k = '4thGoForItProb'
            idx = self.getYtgIdx(k, ytg)
            self.addProbFuncVal(k, dwn, ytg, i)

            if ytg>gthresh:
                gfp = 0.0
            else:                            
                gfp = self.probFuncVals[k][dwn][idx][i]
            gfps.append(gfp)

        fig = matplotlib.pyplot.figure()
        matplotlib.pyplot.plot(xx, tt, 'b', label='TO', drawstyle='steps')
        matplotlib.pyplot.xlabel('yfog')
        matplotlib.pyplot.ylabel('prob')
        matplotlib.pyplot.plot(xx, ff, 'r', label='FG', drawstyle='steps')
        matplotlib.pyplot.ylim(0, 1)
        matplotlib.pyplot.legend()
        matplotlib.pyplot.title('TO/FG at 4th and 1')
        pdf.savefig(fig)

        fig = matplotlib.pyplot.figure()
        matplotlib.pyplot.plot(xx, gfps, 'k', label='4thGoForIt', drawstyle='steps')
        matplotlib.pyplot.xlabel('yfog')
        matplotlib.pyplot.ylabel('prob')
        matplotlib.pyplot.ylim(0, 1)
        matplotlib.pyplot.legend()
        matplotlib.pyplot.title('4thGoForIt at 4th and 1')
        pdf.savefig(fig)


        xx = []
        tt = []
        ff = []
        pp = []
        gfps = []

        for i in range(1, 99):
            dwn = 4
            ytg = 10
            state = '4_%02d_%02d_00' % (ytg, i)
            #            print i, state
            t = self.getProb(state, probType='TO', modelType=self.modelType) 
            f = self.getProb(state, probType='FG', modelType=self.modelType) 
            xx.append(i)
            tt.append(t)
            ff.append(f)
        
            # only go for it if past the threshold,
            ytg = 2
            k = '4thGoForItThresh'
            idx = self.getYtgIdx(k, ytg)
            self.addProbFuncVal(k, dwn, idx, i)
            gthresh = self.probFuncVals[k][dwn][idx][i]

            # how often do we go for it?
            k = '4thGoForItProb'
            idx = self.getYtgIdx(k, ytg)
            self.addProbFuncVal(k, dwn, idx, i)

            if ytg>gthresh:
                gfp = 0.0
            else:                            
                gfp = self.probFuncVals[k][dwn][idx][i]
            gfps.append(gfp)


            dwn = 1
            ytg = 10
            state = '1_10_%02d_00' % i
            
            p = self.modelFunctions['passProb'][dwn][ytg][4](i)
            pp.append(p)


        fig = matplotlib.pyplot.figure()
        matplotlib.pyplot.plot(xx, tt, 'b', label='TO', drawstyle='steps')
        matplotlib.pyplot.xlabel('yfog')
        matplotlib.pyplot.ylabel('prob')
        matplotlib.pyplot.plot(xx, ff, 'r', label='FG', drawstyle='steps')
        matplotlib.pyplot.ylim(0, 1)
        matplotlib.pyplot.legend()
        matplotlib.pyplot.title('TO/FG at 4th and 10')
        pdf.savefig(fig)

        fig = matplotlib.pyplot.figure()
        matplotlib.pyplot.plot(xx, gfps, 'k', label='4thGoForIt', drawstyle='steps')
        matplotlib.pyplot.xlabel('yfog')
        matplotlib.pyplot.ylabel('prob')
        matplotlib.pyplot.ylim(0, 1)
        matplotlib.pyplot.legend()
        matplotlib.pyplot.title('4thGoForIt prob at 4th and 2')
        pdf.savefig(fig)

        fig = matplotlib.pyplot.figure()
        matplotlib.pyplot.plot(xx, pp, 'b', label='PASS', drawstyle='steps')
        matplotlib.pyplot.plot(xx, 1.0-numpy.array(pp), 'r', label='RUSH', drawstyle='steps')
        matplotlib.pyplot.xlabel('yfog')
        matplotlib.pyplot.ylabel('prob')
        matplotlib.pyplot.ylim(0, 1)
        matplotlib.pyplot.legend()
        matplotlib.pyplot.title('PASS prob at 1st and 10')
        pdf.savefig(fig)

        fig = matplotlib.pyplot.figure()
        xx = []
        yy = []
        state = '1_10_20_00'
        ydist = self.getYardsDist(state, modelType=self.modelType)
        ks = ydist.keys()
        ks.sort()
        for i in ks:
            xx.append(i)
            yy.append(ydist[i])

        matplotlib.pyplot.plot(xx, yy, drawstyle='steps', color='k', label=state)
        matplotlib.pyplot.xlabel('yards')
        matplotlib.pyplot.ylabel('prob')
        matplotlib.pyplot.title('yards dist at 1st & 10 from the 20')
        matplotlib.pyplot.xlim(-20,100)
        matplotlib.pyplot.ylim(0,0.25)
        pdf.savefig(fig)

        fig = matplotlib.pyplot.figure()
        xx = []
        yy = []
        state = '3_01_20_00'
        ydist = self.getYardsDist(state, modelType=self.modelType)
        ks = ydist.keys()
        ks.sort()
        for i in ks:
            xx.append(i)
            yy.append(ydist[i])

        matplotlib.pyplot.plot(xx, yy, drawstyle='steps', color='k', label=state)
        matplotlib.pyplot.xlabel('yards')
        matplotlib.pyplot.ylabel('prob')
        matplotlib.pyplot.title('yards dist at 3rd & 1 from the 20')
        matplotlib.pyplot.xlim(-20,100)
        matplotlib.pyplot.ylim(0,0.25)
        pdf.savefig(fig)


        fig = matplotlib.pyplot.figure()
        xx = []
        yy = []
        state = '4_10_20_00'
        ydist = self.getYardsDist(state, modelType=self.modelType)
        ks = ydist.keys()
        ks.sort()
        for i in ks:
            xx.append(i)
            yy.append(ydist[i])

        matplotlib.pyplot.plot(xx, yy, drawstyle='steps', color='k', label=state)
        matplotlib.pyplot.xlabel('yards')
        matplotlib.pyplot.ylabel('prob')
        matplotlib.pyplot.title('yards dist at 4th & 10 from the 20')
        matplotlib.pyplot.xlim(-20,100)
        matplotlib.pyplot.ylim(0,0.25)
        pdf.savefig(fig)

        fig = matplotlib.pyplot.figure()
        xx = []
        yy = []
        state = '2_07_42_00'
        ydist = self.getYardsDist(state, modelType=self.modelType)
        ks = ydist.keys()
        ks.sort()
        for i in ks:
            xx.append(i)
            yy.append(ydist[i])

        matplotlib.pyplot.plot(xx, yy, drawstyle='steps', color='k', label=state)
        matplotlib.pyplot.xlabel('yards')
        matplotlib.pyplot.ylabel('prob')
        matplotlib.pyplot.title('yards dist at 2nd & 7 from the 42')
        matplotlib.pyplot.xlim(-20,100)
        matplotlib.pyplot.ylim(0,0.25)
        pdf.savefig(fig)

        xx = []
        tds = []
        fgs = []
        tos = []
        ss = []

        for i in range(1, 99):
            xx.append(i)
            state = '1_10_%02d_00' % i
            ss.append(self.resultMatrix[self.state2int['S'], self.state2int[state]])
            tos.append(self.resultMatrix[self.state2int['TO'], self.state2int[state]])
            tds.append(self.resultMatrix[self.state2int['TD'], self.state2int[state]])
            fgs.append(self.resultMatrix[self.state2int['FG'], self.state2int[state]])

        fig = matplotlib.pyplot.figure()
        matplotlib.pyplot.plot(xx, tds, 'k', label='TDs', drawstyle='steps')
        matplotlib.pyplot.plot(xx, fgs, 'b', label='FGs', drawstyle='steps')
        matplotlib.pyplot.plot(xx, tos, 'r', label='TOs', drawstyle='steps')
        matplotlib.pyplot.plot(xx, ss, 'c', label='Ss', drawstyle='steps')

        matplotlib.pyplot.xlabel('yfog')
        matplotlib.pyplot.ylabel('prob')
        matplotlib.pyplot.title('probs at 1st and 10')
        matplotlib.pyplot.ylim(0, 1)
        matplotlib.pyplot.legend()

        pdf.savefig(fig)

        xx = []
        ss = []
        tos = []
        tds = []
        fgs = []
        for i in range(1, 99):
            xx.append(i)
            state = '2_10_%02d_00' % i

            ss.append(self.resultMatrix[self.state2int['S'], self.state2int[state]])
            tos.append(self.resultMatrix[self.state2int['TO'], self.state2int[state]])
            tds.append(self.resultMatrix[self.state2int['TD'], self.state2int[state]])
            fgs.append(self.resultMatrix[self.state2int['FG'], self.state2int[state]])

        fig = matplotlib.pyplot.figure()
        matplotlib.pyplot.plot(xx, tds, 'k', label='TDs', drawstyle='steps')
        matplotlib.pyplot.plot(xx, fgs, 'b', label='FGs', drawstyle='steps')
        matplotlib.pyplot.plot(xx, tos, 'r', label='TOs', drawstyle='steps')
        matplotlib.pyplot.plot(xx, ss, 'c', label='Ss', drawstyle='steps')

        matplotlib.pyplot.xlabel('yfog')
        matplotlib.pyplot.ylabel('prob')
        matplotlib.pyplot.title('probs at 2nd and 10')
        matplotlib.pyplot.ylim(0, 1)
        matplotlib.pyplot.legend()
        pdf.savefig(fig)

        xx = []
        ss = []
        tos = []
        tds = []
        fgs = []
        for i in range(1, 99):
            xx.append(i)
            state = '3_10_%02d_00' % i

            ss.append(self.resultMatrix[self.state2int['S'], self.state2int[state]])
            tos.append(self.resultMatrix[self.state2int['TO'], self.state2int[state]])
            tds.append(self.resultMatrix[self.state2int['TD'], self.state2int[state]])
            fgs.append(self.resultMatrix[self.state2int['FG'], self.state2int[state]])

        fig = matplotlib.pyplot.figure()
        matplotlib.pyplot.plot(xx, tds, 'k', label='TDs', drawstyle='steps')
        matplotlib.pyplot.plot(xx, fgs, 'b', label='FGs', drawstyle='steps')
        matplotlib.pyplot.plot(xx, tos, 'r', label='TOs', drawstyle='steps')
        matplotlib.pyplot.plot(xx, ss, 'c', label='Ss', drawstyle='steps')

        matplotlib.pyplot.xlabel('yfog')
        matplotlib.pyplot.ylabel('prob')
        matplotlib.pyplot.title('probs at 3rd and 10')
        matplotlib.pyplot.ylim(0, 1)
        matplotlib.pyplot.legend()
        pdf.savefig(fig)

        xx = []
        ss = []
        tos = []
        tds = []
        fgs = []
        for i in range(1, 99):
            xx.append(i)
            state = '4_10_%02d_00' % i

            ss.append(self.resultMatrix[self.state2int['S'], self.state2int[state]])
            tos.append(self.resultMatrix[self.state2int['TO'], self.state2int[state]])
            tds.append(self.resultMatrix[self.state2int['TD'], self.state2int[state]])
            fgs.append(self.resultMatrix[self.state2int['FG'], self.state2int[state]])

        fig = matplotlib.pyplot.figure()
        matplotlib.pyplot.plot(xx, tds, 'k', label='TDs', drawstyle='steps')
        matplotlib.pyplot.plot(xx, fgs, 'b', label='FGs', drawstyle='steps')
        matplotlib.pyplot.plot(xx, tos, 'r', label='TOs', drawstyle='steps')
        matplotlib.pyplot.plot(xx, ss, 'c', label='Ss', drawstyle='steps')

        matplotlib.pyplot.xlabel('yfog')
        matplotlib.pyplot.ylabel('prob')
        matplotlib.pyplot.title('probs at 4th and 10')
        matplotlib.pyplot.ylim(0, 1)
        matplotlib.pyplot.legend()
        pdf.savefig(fig)

        xx = []
        ss = []
        tos = []
        tds = []
        fgs = []
        for i in range(1, 99):
            xx.append(i)
            state = '3_01_%02d_00' % i

            ss.append(self.resultMatrix[self.state2int['S'], self.state2int[state]])
            tos.append(self.resultMatrix[self.state2int['TO'], self.state2int[state]])
            tds.append(self.resultMatrix[self.state2int['TD'], self.state2int[state]])
            fgs.append(self.resultMatrix[self.state2int['FG'], self.state2int[state]])

        fig = matplotlib.pyplot.figure()
        matplotlib.pyplot.plot(xx, tds, 'k', label='TDs', drawstyle='steps')
        matplotlib.pyplot.plot(xx, fgs, 'b', label='FGs', drawstyle='steps')
        matplotlib.pyplot.plot(xx, tos, 'r', label='TOs', drawstyle='steps')
        matplotlib.pyplot.plot(xx, ss, 'c', label='Ss', drawstyle='steps')

        matplotlib.pyplot.xlabel('yfog')
        matplotlib.pyplot.ylabel('prob')
        matplotlib.pyplot.title('probs at 3rd and 1')
        matplotlib.pyplot.ylim(0, 1)
        matplotlib.pyplot.legend()
        pdf.savefig(fig)

        xx = []
        ss = []
        tos = []
        tds = []
        fgs = []
        for i in range(1, 99):
            xx.append(i)
            state = '4_01_%02d_00' % i

            ss.append(self.resultMatrix[self.state2int['S'], self.state2int[state]])
            tos.append(self.resultMatrix[self.state2int['TO'], self.state2int[state]])
            tds.append(self.resultMatrix[self.state2int['TD'], self.state2int[state]])
            fgs.append(self.resultMatrix[self.state2int['FG'], self.state2int[state]])

        fig = matplotlib.pyplot.figure()
        matplotlib.pyplot.plot(xx, tds, 'k', label='TDs', drawstyle='steps')
        matplotlib.pyplot.plot(xx, fgs, 'b', label='FGs', drawstyle='steps')
        matplotlib.pyplot.plot(xx, tos, 'r', label='TOs', drawstyle='steps')
        matplotlib.pyplot.plot(xx, ss, 'c', label='Ss', drawstyle='steps')

        matplotlib.pyplot.xlabel('yfog')
        matplotlib.pyplot.ylabel('prob')
        matplotlib.pyplot.title('probs at 4th and 1')
        matplotlib.pyplot.ylim(0, 1)
        matplotlib.pyplot.legend()
        pdf.savefig(fig)

        fig = matplotlib.pyplot.figure()
        mm = self.makeHeatmap(dwns=[1,2,3,4], htype='expectedPoints')
#        plt.title('
        pdf.savefig(fig)

        pdf.close()

    def initParams(self):
        ''' here is where we define the default model, to be 
        overwriten later by param file if needed... 
        lots of parameters to define...'''
        loc = {}
        self.params = copy.copy(loc)
        

    def loadParamsFromFile(self, fileName):
        lines = [l.strip() for l in open(fileName).readlines()]
        for l in lines:
            if len(l)<1:
                continue
            if l[0]=='#':
                continue
        
            st = l.split()
            k = st[0]

            if self.vbose>=1:
                print 'loadParams', k, st

            if k in ['interp-type']:
                self.params[k] = st[1]
                continue

            if k in ['modelType']:
                self.modelType = st[1]
                continue

            if k in ['modelName']:
                self.modelName = st[1]
                continue

            if not k in self.params:
                self.params[k] = {}

            data = st[1:]
            nl = len(data)
            for i in range(len(data)):
                if not i in self.params[k]:
                    self.params[k][i] = []
                if i>=0 and i<=2:
                    # the first 3 should be ints, down, ytgMin, ytgMax
                    # its important to cast them that way since they are keys for a dictionary
                    self.params[k][i].append(int(data[i]))
                else:
                    self.params[k][i].append(float(data[i]))

            
    def initEnumerateStates(self):
        ''' this generates dictionaries that provide a mapping of 
        string valued state to integer. There is one dictionary
        state2int and a second, int2state'''
        
        # end states
        # turnover, field goal, touchdown, safety
        xx = copy.copy(self.endStates)
        
        for parity in range(2):
#        for parity in range(1):
            for dwn in range(1,4+1):
                for ytg in range(1,20+1):
                    for yfog in range(1,99+1):
                        s = '%d_%02d_%02d_%02d' % (dwn, ytg, yfog, parity)
                        xx.append(s)
            
        self.state2int = {}
        self.int2state = {}
        for i, s in enumerate(xx):
            self.state2int[s] = i
            self.int2state[i] = s

        allStates = self.state2int.keys()
        allStates.sort()
        self.allStates = allStates

    def initTransitionMatrix(self):
        ''' transition matrix is n x n where 
        n = (4x20x99)+4, i.e. down is 1-4, yards to go is 1-20,
        yards-from-own-goal is 1-99 
        and the extra 3 are turnover, FG, safety, or TD.
        Numerically this is 7924 x 7924 '''
        sz = len(self.int2state)
        del self.transitionMatrix
        self.transitionMatrix = numpy.zeros((sz, sz))

    def infoToState(self, dwn, ytg, yfog, parity=0):
        k='%d_%02d_%02d_%02d' % (dwn, ytg, yfog, parity)
        return k

    def stateToInfo(self, state):
        ''' state is a string that is coded 
        down_ytg_yfog '''

        if not '_' in state:
            return None, None, None, None

        dwn, ytg, yfog, parity = [int(x) for x in state.split('_')]
        return dwn, ytg, yfog, parity

    def reduceMatrix(self, tMatrix):
        cc = numpy.where(tMatrix>0)
        ans = (numpy.shape(tMatrix), cc, tMatrix[cc])
        return ans

    def expandMatrix(self, rMatrix):
        nx, ny = rMatrix[0]
        ans = numpy.zeros((nx, ny))
        cc = rMatrix[1]
        ans[cc] = rMatrix[2]
        return ans


    def readPickle(self, fileName):
        modelName = ''.join(fileName.split('.pkl')[0:-1])
        self.storedModels[modelName] = {}        
        ofp = open(fileName, 'rb')
        self.storedModels[modelName]['params'] = pickle.load(ofp)
        self.storedModels[modelName]['int2state'] = pickle.load(ofp)
        self.storedModels[modelName]['state2int'] = pickle.load(ofp)
        self.storedModels[modelName]['transitionMatrix'] = self.expandMatrix(pickle.load(ofp))
        self.storedModels[modelName]['resultMatrix'] = pickle.load(ofp)

    def writePickle(self, fileName):
        ofp = open(fileName, 'wb')
        pickle.dump(self.params, ofp)
        pickle.dump(self.int2state, ofp)
        pickle.dump(self.state2int, ofp)
        pickle.dump(self.reduceMatrix(self.transitionMatrix), ofp)
        pickle.dump(self.resultMatrix, ofp)
        ofp.close()

    def reNorm(self, ydist, ynorm=1.0):
        s = 0.0
        for k in ydist:
            s += ydist[k]

        if s==0:
            return ydist

        scale = ynorm/s
        for k in ydist:
            ydist[k] *= scale

        return ydist

    def addProbFuncVal(self, k, dwn, ytg, yfog, idx_f=4):
        idx = ytg
        if not k in self.probFuncVals:
            self.probFuncVals[k] = {}
        if not dwn in self.probFuncVals[k]: 
            self.probFuncVals[k][dwn] = {}
        if not idx in self.probFuncVals[k][dwn]: 
            self.probFuncVals[k][dwn][idx] = {}
        if not yfog in self.probFuncVals[k][dwn][idx]: 
            val = self.modelFunctions[k][dwn][ytg][idx_f](yfog)
            self.probFuncVals[k][dwn][idx][yfog] = val
            if self.vbose>=1:
                print 'adding probFuncVal', k, dwn, idx, yfog, val
        
    def doInitProb(self, probType, modelType):
        ''' given the model, fill in FG and/or TO probs for each state 
        this needs to return a dictionary with keys of states and values
        prob for probType to occur'''

# July 31, 2014
# since I'm changing the transition matrix to account for points the opponent will score,
# need to keep track of punts, fumbles, interceptions, missed field goals separately.
# probType can be FG, PUNT, FUM, INT, FG00 (missed FG),

# the processed data file doenst distinguish fumbles from interceptions, only lables them as TO. therefore, postpine that distinction.
 
        ans = {}
        iemp = False
        if modelType=='emp_2002_2010':
            if not self.empInit_2002_2010:
                pfile = 'nflPlayFreq_2002_2010.pkl'
                pfp = open(self.inDataDir +  '/' + pfile,'rb')
                self.emp_2002_2010 = pickle.load(pfp)
                pfp.close()
                self.empInit_2002_2010 = True
                self.empDist_2002_2010 = self.makeYdistFromPBP(dum=0)
            iemp = True
            obj = self.emp_2002_2010 
        elif modelType=='emp_2009_2013':
            if not self.empInit_2009_2013:
                pfile = 'nflPlayFreq_2009_2013.pkl'
                pfp = open(self.inDataDir + '/' + pfile,'rb')
                self.emp_2009_2013 = pickle.load(pfp)
                pfp.close()
                self.empInit_2009_2013 = True
                self.empDist_2009_2013 = self.makeYdistFromPBP(dum=1)
            iemp = True

            obj = self.emp_2009_2013 

        elif modelType=='userModel':
            iemp = False


        # WARNING, this is a hack so that empirical models 
        # get punt and fg probs computed according to the model
            
        iemp = False

        allStates = self.allStates
        for state in self.endStates:
            ans[state] = 0.0

        for i, state in enumerate(allStates):
                ans[state] = 0.0

        if iemp:

            data_all = {}
            data_pass = {}

            for d in obj:
                if d['type'] in ['NOPL', 'KICK', 'PENA', 'TWOP']:
                    continue

                dwn = d['dwn']
                ytg = d['ytg']
                yfog = d['yfog']            
                state = self.infoToState(dwn, ytg, yfog)
                if not state in data_all:
                    data_all[state] = 0.0
                    data_pass[state] = 0.0
            
                data_all[state] += 1

                if probType=='TO':
                    if d['type'] in ['TO']:
                        data_pass[state] += 1
                elif probType=='PUNT':
                    if d['type'] in ['PUNT']:
                        data_pass[state] += 1
                elif probType=='FG00':
                    if d['type'] in ['FG00']:
                        data_pass[state] += 1
                elif probType=='FG':
                    if d['type'] in ['FG01']:
                        data_pass[state] += 1

            ks = data_all.keys()
            ks.sort()
            for state in ks:
#                print state, data_pass[state], data_all[state]
                ans[state] = data_pass[state]/data_all[state]

        else:
            # if its not empirical, it must be a user model
            print 'non empirical'
            for i, state in enumerate(allStates):

                k = self.state2int[state]
#                print k, state, self.stateToInfo(state)
                dwn, ytg, yfog, parity = self.stateToInfo(state)

                if dwn is None:
                    continue

                if dwn==4:
                    # on 4th  you either go for it, try field goal, 
                    # or punt 
                    
                    # go for it prob
                    
                    # only go for it if past the threshold,
                    k = '4thGoForItThresh'
                    idx = self.getYtgIdx(k, ytg)

                    self.addProbFuncVal(k, dwn, ytg, yfog)
                    gthresh = self.probFuncVals[k][dwn][idx][yfog]

                    # how often do we go for it?
                    k = '4thGoForItProb'
                    idx = self.getYtgIdx(k, ytg)

                    # gfp is the go-for-it prob
                    self.addProbFuncVal(k, dwn, ytg, yfog)
                    if ytg>gthresh:
                        gfp = 0.0
                    else:                            
                        gfp = self.probFuncVals[k][dwn][idx][yfog]

                    # how often field goal?
                    k = '4thFgProb'
                    idx = self.getYtgIdx(k, ytg)

                    # fgp is the attempt FG prob
                    self.addProbFuncVal(k, dwn, ytg, yfog)
                    fgp = self.probFuncVals[k][dwn][idx][yfog]

                    # make field goal prob
                    k = 'FgMakeProb'
                    idx = self.getYtgIdx(k, ytg)

                    # fgmakep is the make FG prob
                    self.addProbFuncVal(k, dwn, ytg, yfog)
                    fgmakep = self.probFuncVals[k][dwn][idx][yfog]

                    # a punt is when you dont go for it and 
                    # dont try a field goal
                    puntp = 1.0-fgp-gfp

                    # a turnover is a punt, a missed fg,
                    # or going for it and fumbling or interceptioning
                    
                    # aug 1, 2014, now we separate out punts, and missed field goals
                    #                        toProb += puntp
                    #                        toProb += fgp*(1-fgmakep)
                    intProb = self.modelFunctions['intProb'][dwn][ytg][4](yfog) 
                    fumProb = self.modelFunctions['fumProb'][dwn][ytg][4](yfog) 

                else:
                    # if its not 4th down, a turnover is
                    # going for it (100%) and fumbling or interceptioning
                    gfp = 1.0
                    fgp = 0.0
                    fgmakep=0.0
                    puntp = 1.0-fgp-gfp

                    intProb = self.modelFunctions['intProb'][dwn][ytg][4](yfog) 
                    fumProb = self.modelFunctions['fumProb'][dwn][ytg][4](yfog) 


                # here is a hack; there is no explicit requirement that 
                # gfp + fgp < 1, so sometimes puntp end up < 0;
                # in that case, rescale them so they add up to one.

                testp = gfp+fgp
                if testp>1:
                    gfp0 = gfp
                    fgp0 = fgp
                    puntp0 = puntp

                    gfp = gfp0/testp
                    fgp = fgp0/testp
                    puntp = 1.0-gfp-fgp

                    if vbose>=1:
                        print '***********'
                        print 'WARNING: rescaling gfp and fgp'
                        print 'state', state, 'testp', testp
                        print 'gfp0 fgp0 puntp0', gfp0, fgp0, puntp0 
                        print 'gfp fgp puntp', gfp, fgp, puntp 

                    puntp = 0.0                        

                if probType=='TO':
                    prob = gfp*(intProb+fumProb)

                elif probType=='PUNT':
                    prob = puntp

                elif probType=='FG00':
                    prob = fgp*(1-fgmakep)

                elif probType=='FG':
                    prob = fgp*fgmakep

                else:
                    # we should never get here
                    raise Exception

                if prob<0:
                    print 'Fatal error: prob<0'
                    print 'gfp', gfp
                    print 'fgp', fgp
                    print 'fgmakep', fgmakep
                    print 'puntp', puntp
                    print 'state', state
                    print 'modelType', modelType
                    sys.exit()
                ans[state] = prob

        return ans

    def getProb(self, state, probType=None, modelType=None):
        ''' given state, get the prob for e.g. field goal, TO '''

        if not probType in self.initProb:
            self.initProb[probType] = {}
        if not modelType in self.initProb[probType]:
            self.initProb[probType][modelType] = self.doInitProb(probType, modelType)

        return self.initProb[probType][modelType][state]


    def fBazinPlusGauss(self, x, A, x0, s1, s2, G, g0, gs):
        ''' x is the input. function is,
        A exp(tx/k1)/(1+exp(tx/k2))
        where tx = x-x0, k1 = s1
        k2 = (s1*s2)/(s1+s2)
        then we add in a gaussian to describe being sacked,
        += G exp(-0.5 ((x-g0)/gs)**2)
        '''

        tx = x-1.0*x0
        k1 = 1.0*s1
        k2 = (s1*s2)/(1.0*s1+s2)
        f1 = A*numpy.exp(tx/k1)/(1.0 + numpy.exp(tx/k2))
        f2 = 0.0
        if G>0:
            f2 = G*numpy.exp(-0.5*((x-1.0*g0)/gs)**2)
        return f1 + f2


    def makeYdistFromPBP(self, 
                         dum=None, 
                         goodTypes = 
                         ['PASS'
                          ,'RUSH'
                          ] 
                         ):
        ydist = {}

        if dum==0:
            obj = self.emp_2002_2010
        elif dum==1:
            obj = self.emp_2009_2013
        else:
            raise Exception

        for d in obj:
            ty = d['type']
            if not ty in goodTypes:
#                print d, 'not in goodTypes'
                continue

            dwn = d['dwn']
            ytg = d['ytg']
            yfog = d['yfog']            
            state = self.infoToState(dwn, ytg, yfog)
            if not state in ydist:
                ydist[state] = {}

            yds = d['yds']
            if not yds in ydist[state]:
                ydist[state][yds] = 0
            ydist[state][yds] += 1

        return ydist

    def getYardsDist(self, state, modelType='emp_2009_2013'):        
        ydist = {}
#        print 'modelType', modelType

        if modelType=='fake1':
            ydist[-1] = 0.1
            ydist[0]  = 0.3
            ydist[1]  = 0.1
            ydist[2]  = 0.1
            ydist[3]  = 0.2
            ydist[5]  = 0.2
            ydist[10] = 0.1
            ydist = self.reNorm(ydist)

        elif modelType=='emp_2002_2010':

            if not self.empInit_2002_2010:
                pfile = 'nflPlayFreq_2002_2010.pkl'
                pfp = open(self.inDataDir+'/' + pfile,'rb')
                self.emp_2002_2010 = pickle.load(pfp)
                pfp.close()
                self.empInit_2002_2010 = True
                self.empDist_2002_2010 = self.makeYdistFromPBP(dum=0)

            if state in self.empDist_2002_2010:
                ydist = self.empDist_2002_2010[state]
                ydist = self.reNorm(ydist)
            else:
                # this is not the best way to handle this...
                # i.e., if no empirical data, for example no empirical 
                # examples of 1st and 1 from the 1, 
                # set yards gained distribution to... what?
                # for now Im using 100% 0 yards gained.
                ydist = {0:1}

        elif modelType=='emp_2009_2013':
            if not self.empInit_2009_2013:
                pfile = 'nflPlayFreq_2009_2013.pkl'
                pfp = open(self.inDataDir+'/' + pfile,'rb')
                self.emp_2009_2013 = pickle.load(pfp)
                pfp.close()
                self.empInit_2009_2013 = True
                self.empDist_2009_2013 = self.makeYdistFromPBP(dum=1)

            if state in self.empDist_2009_2013:
                ydist = self.empDist_2009_2013[state]
                ydist = self.reNorm(ydist)
            else:
                # this is not the best way to handle this...
                # i.e., if no empirical data, for example no empirical 
                # examples of 1st and 1 from the 1, 
                # set yards gained distribution to... what?
                # for now Im using 100% 0 yards gained.
                ydist = {0:1}
                
        elif modelType=='userModel':

            dwn, ytg, yfog, parity = self.stateToInfo(state)

# cache the function values
# WARNING! this means yard dist probs dont depend on down and ytg,
# no matter what you put in the paramater file! 
# July 31, 2014: start fixing this part so that the yadrs gained can depend on 
# down and distance also... I do this by replaceing yfog as an index with k, which is a concatanation of dwn, ytg, yfog

            k = '%d_%03d_%03d' % (dwn, ytg, yfog)
            if not k in self.fparsP:
                A = 1.0
                x0 = self.modelFunctions['yardsDistParsPass'][dwn][ytg][4](yfog)
                s1 = self.modelFunctions['yardsDistParsPass'][dwn][ytg][5](yfog)
                s2 = self.modelFunctions['yardsDistParsPass'][dwn][ytg][6](yfog)
                G  = self.modelFunctions['yardsDistParsPass'][dwn][ytg][7](yfog)
                g0 = self.modelFunctions['yardsDistParsPass'][dwn][ytg][8](yfog)
                gs = self.modelFunctions['yardsDistParsPass'][dwn][ytg][9](yfog)
                self.fparsP[k] = [A, x0, s1, s2, G, g0, gs]
                if self.vbose>=1:
                    print 'pass pars', dwn, ytg, yfog, k, self.fparsP[k]

            xs = range(self.minYd,100)
            if not k in self.fvalsP:
                [A, x0, s1, s2, G, g0, gs] = self.fparsP[k]
                val = self.fBazinPlusGauss(xs, A=A, x0=x0, s1=s1, s2=s2, G=G, g0=g0, gs=gs)
                self.fvalsP[k] = val
                if self.vbose>=1:
                    print 'pass val', dwn, ytg, yfog, k, self.fvalsP[k]


                    
            if not yfog in self.fparsR:
                A = 1.0
                x0 = self.modelFunctions['yardsDistParsRush'][dwn][ytg][4](yfog)
                s1 = self.modelFunctions['yardsDistParsRush'][dwn][ytg][5](yfog)
                s2 = self.modelFunctions['yardsDistParsRush'][dwn][ytg][6](yfog)
                G  = 0.0
                g0 = 1.0
                gs = 1.0

                self.fparsR[k] = [A, x0, s1, s2, G, g0, gs]
                if self.vbose>=1:
                    print 'rush pars', dwn, ytg, yfog, k, self.fparsR[k]

            xs = range(self.minYd,100)
            if not k in self.fvalsR:
                [A, x0, s1, s2, G, g0, gs] = self.fparsR[k]
                val = self.fBazinPlusGauss(xs, A=A, x0=x0, s1=s1, s2=s2, G=G, g0=g0, gs=gs)
                self.fvalsR[k] = val
                if self.vbose>=1:
                    print 'rush vals', dwn, ytg, yfog, self.fvalsP[k]

            # pass ?
            passProb = self.modelFunctions['passProb'][dwn][ytg][4](yfog)
            passYdist = {}
            
            xs = range(self.minYd,100)
            for ic, ix in enumerate(xs):
                [A, x0, s1, s2, G, g0, gs] = self.fparsP[k]

                val = self.fvalsP[k][ic]
#self.fBazinPlusGauss(ix, A=A, x0=x0, s1=s1, s2=s2, G=G, g0=g0, gs=gs)

                if self.vbose>=2:
                    print state, 'pass', 'ic', ic, 'ix', ix, A, x0, s1, s2, G, g0, gs, val

                passYdist[ix] = val



            # if not a pass, it must be a run!
            runProb = 1.0-passProb
            runYdist = {}
            
            for ic, ix in enumerate(xs):
                [A, x0, s1, s2, G, g0, gs] = self.fparsR[k]
#                A = 1.0
#                x0 = self.modelFunctions['yardsDistParsRush'][4](yfog)
#                s1 = self.modelFunctions['yardsDistParsRush'][2](yfog)
#                s2 = self.modelFunctions['yardsDistParsRush'][3](yfog)
#                G  = 0.0
#                g0 = 1.0
#                gs = 1.0

#                val = self.fBazinPlusGauss(ix, A=A, x0=x0, s1=s1, s2=s2, G=G, g0=g0, gs=gs)

                val = self.fvalsR[k][ic]

                if self.vbose>=2:
                    print state, 'rush', 'ic', ic, 'ix', ix, A, x0, s1, s2, G, g0, gs, val


                runYdist[ix] = val

            # now add in explicitly the incompletes
            # first renormalize the ydist to 1.0-incProb, then add in the inc at yards=0
            incProb = self.modelFunctions['incompleteProb'][dwn][ytg][4](yfog)
            self.reNorm(passYdist, 1.0-incProb)
            passYdist[0] += incProb

            # now renormalize them appropriately,
            self.reNorm(passYdist, passProb)
            self.reNorm(runYdist, runProb)

            if self.vbose>=1:
                print 'pass rush incomplete Prob', dwn, ytg, yfog, passProb, runProb, incProb

            # and sum them up...
            for i in range(self.minYd,100):
                if self.vbose>=1:
                    print 'yardsDist ', dwn, ytg, yfog, i, 'RUSH', runYdist[i], 'PASS', passYdist[i]
                ydist[i] = runYdist[i]
                ydist[i] += passYdist[i]
            # and finally, renormalize to 1

            self.reNorm(ydist, 1.0)

        else:
            raise Exception

        return ydist 

    def getNewState(self, y, state):
        ''' given the old state, state, and the yards gained y,
        return the new state. '''
        dwn, ytg, yfog, parity = self.stateToInfo(state)
        # first, if yards gained is more than 100-yfog, 
        # then a td has been scored.
        if y>=(100-yfog):
            ns = 'TD'
        # if yards gained is negative, it could be a safety
        elif y+yfog<=0:
            ns = 'S'            
        # if its 4th down and yards gained isnt more than ytg,
        # then its a turnover
        elif dwn==4 and y<ytg:

#            ns = 'TO'
            # a turnover means switch the field position and change the parity
            ns = self.infoToState(1, 10, 100-yfog, int(not bool(parity))) 

        # if yards gained is more than ytg, its a first down
        elif y>=ytg:
            ndwn = 1
            nytg = 10
            nyfog = yfog + y
            ns = self.infoToState(ndwn, nytg, nyfog, parity)
        # if yards gained is less than ytg, and dwn<=3, increment dwn
        elif y<ytg:
            ndwn = dwn+1
            nytg = ytg-y
            # if ytg > 20, reset it to 20,
            if nytg>20:
                nytg = 20
            nyfog = yfog + y
            ns = self.infoToState(ndwn, nytg, nyfog, parity)
        # should never get here...
        else:
            raise Exception

        if ns in ['TO', 'TD', 'FG', 'S'] and parity==1:
            ns += 'm'

        if self.vbose>=1:
            print 'old', state, self.state2int[state], \
                'y', y, \
                'new', ns, self.state2int[ns], \
                'parity', parity

        return ns

    def makeTransitionMatrix(self, modelType='emp_2009_2013'):
        ''' modelType switches between different options.
        for fake1, just fill a simple matrix as a test. 
        important, element ij is the probability to transition 
        TO i, FROM j.
        '''

# July 31, 2014
# start ading support for turnovers. i.e., a turnover should not be an end state, 
# need to account for probability for opponent to score.
# the way to do this is transition to a state dwn=1, ytg=10, yfog=100-y
# and include a negative sign to account for negative points when your opponent scores        
# as a simple starting point, let fumbles occur at line of scrimmage, interceptions 10 yards down, punts get a 30 yard net.

        self.initTransitionMatrix()
        
        allStates = self.allStates

        for s in self.endStates:
            # if oldState is an end state, i.e. TO, FG, S, TD, 
            # then transition probabilities are 0 to any other state
            # and 1 to itself.
            i = self.state2int[s]
            self.transitionMatrix[i][i] = 1.0

        n = len(allStates)
        for i, oldState in enumerate(allStates):

#            if i>=100:
#                sys.exit()

            if i%1000==0:
                print i, n, oldState

            # if oldState is an end state, its already been set so continue
            if oldState in self.endStates:
                continue

            dwn, ytg, yfog, parity = self.stateToInfo(oldState)

            # get the TO probability
            # this is just the explicit TO prob, 
            # i.e. fumbles, interceptions, punts...
            # turnovers on downs are handled by getYardsDist and getNewState


            # need to get PUNT prob, missed FG prob, INT prob and FUM prob.
            toProb = self.getProb(oldState, probType='TO', modelType=modelType)
            puntProb = self.getProb(oldState, probType='PUNT', modelType=modelType)

            # get the made FG probability
            fgProb01 = self.getProb(oldState, probType='FG', modelType=modelType)

            # get the missed FG probability
            fgProb00 = self.getProb(oldState, probType='FG00', modelType=modelType)

            if self.vbose>=1:
                print '%5d' % i, oldState, 'toProb', toProb, 'fgProb', fgProb

            # ydist comes back normalized to 1
            # change it
            ydist = self.getYardsDist(oldState, modelType=modelType)

            # we will run a play, i.e. draw from the ydist distribution
            # if we didnt try fg, punt, or fumble/intercept
            # so ydist needs to be renormalized accordingly
            ynorm = 1.0-fgProb01-fgProb00-toProb-puntProb
            ydist = self.reNorm(ydist, ynorm)

            keys = ydist.keys()
            iold = self.state2int[oldState]

            # need to initialize the TO prob 
            # since a failed 4th down is considered a TO
            self.transitionMatrix[self.state2int['TO']][iold] = 0.0
            self.transitionMatrix[self.state2int['FG']][iold] = 0.0

            # here is where we fetch the probability, p, 
            # to gain yards, k, 
            # then call method getNewState, 
            # which does the work of translating 
            # oldState+yards to newState
            for k in keys:
                p = ydist[k]
                newState = self.getNewState(k, oldState)
                inew = self.state2int[newState]
                    # need to add probability here, since several different
                    # values of yards gained can result in same end state.
                self.transitionMatrix[inew][iold] += p

            # heres the resulting state from a TO,
            ns = self.infoToState(1, 10, 100-yfog, int(not bool(parity)))
            
            self.transitionMatrix[self.state2int[ns]][iold] += toProb
            self.transitionMatrix[self.state2int[ns]][iold] += fgProb00

            # heres the resulting state from a PUNT,
            ny = yfog+30 # 30 yards net
            if ny>=100:
                ny = 80
                
            ns = self.infoToState(1, 10, 100-ny, int(not bool(parity)))
            self.transitionMatrix[self.state2int[ns]][iold] += puntProb

            # the made field goal state
            ns = 'FG' + ((['', 'm'])[parity])
            self.transitionMatrix[self.state2int[ns]][iold] += fgProb01

    def testMarkov(self, p=0.5, k=2):
        ''' this describes a series of states, 
        -k, ..., -2, -1, 0, 1, 2, ...k
        i.e., move right with prob p, left with prob 1-p,
        if get to +-n, stay there '''
        
        n = 2*k+1
        m = numpy.zeros((n,n))
        for i in range(n):
            ix = i - k
            for j in range(n):
                iy = j - k
                # if i = j + 1, p
                # if i = j - 1, (1-p)
                if ix==iy and abs(ix)==k:
                    m[i][j] = 1
                elif i==(j+1) and abs(iy)<k:
                    m[i][j] = p
                elif i==(j-1) and abs(iy)<k:
                    m[i][j] = 1-p
        print m
        return m

############################
    def converganceStat(self, m1, m2, doSparse=False):
        print 'doing subtraction...'
        nn = (m1-m2)

        if doSparse:
            print 'multiplying ms for converg...'
            k = nn.multiply(nn)            
            print 'getting sum...'
            ans1=k.sum()
        else:
            print 'multiplying ms for converg...'
            k = numpy.multiply(nn,nn)
            print 'getting sum...'
            ans1 = sum(sum(k,0))

#        print 'getting sum...'
#        ans2=nn.sum()

#        ans3 = sum(sum((m1-m2)**2,0))

        return ans1

############################
    def exponentiateMatrix(self, m, n=64, mtol=0.01, doSparse=False):
        # init

        if doSparse:
            print 'making sparse matrix...'
            msparse = scipy.sparse.csc_matrix(m)
            print 'multiplyiing sparse...'
            mnew = msparse.dot(msparse)
        else:
            print 'multiplyiing dense...'
            mnew = m.dot(m)

        print 'doing convergence stat...'
        if doSparse:
            conv = self.converganceStat(msparse, mnew, doSparse=doSparse)
        else:
            conv = self.converganceStat(m, mnew, doSparse=doSparse)

        i = 2
        print 'power', 'convergenceStat'
        print '%3d %.4e' % (i, conv)

        while i<n and conv>mtol:
            if doSparse:

                mnew.eliminate_zeros()
                mnew.prune()                
                print 'copying matrix...'
                print 'mnew has ', mnew.nnz, 'non-zero elements...'
                print 'number < 1e-6: ', numpy.sum(mnew.data<1e-6)
                cc=numpy.where(mnew.data<=1e-6)
                mnew.data[cc]=0
                mnew.eliminate_zeros()
                mnew.prune()                
                print 'now mnew has ', mnew.nnz, 'non-zero elements...'
                print 'number < 1e-6: ', numpy.sum(mnew.data<1e-6)
                mold = copy.copy(mnew)
#                print 'making sparse...'
#                mold = scipy.sparse.csc_matrix(mold)
                print 'multiplying...'
                mnew = mnew.dot(mold)
                print 'getting covergance stat...'
                conv = self.converganceStat(mold, mnew, doSparse=doSparse)
                print 'sum of elements is ', mnew.sum()
                
            else:
                print 'copying matrix...'
                mold = copy.copy(mnew)
                print 'multiplying...'
                mnew = mnew.dot(mold)
                print 'getting covergance stat...'
                conv = self.converganceStat(mold, mnew, doSparse=doSparse)

#            mnew = mnew.dot(mold)

            i *= 2
            print '%3d %.4e' % (i, conv)

        if doSparse:
            return (mnew).todense()
        else:
            return mnew

############################
    def printUsage(self):
        print '***************************'
        print 'USAGE: nflMarkov.py '
        print '*** required'
        print '-paramFile <paramFile>'
        print ' example: paramFiles/nm.default.params.txt'
        print '-modelType <modelType>'
        print ' must be \"emp_2009_2013\" for empirical, or \"userModel\" for a user defined model'
        print '-modelName <modelName>'
        print '*** optional'
        print '-expN <expN>'
        print ' an integer, the power to which to raise the transition matrix (unless it converges sooner)' 
        print ' default=64'
        print '-expTol <expTol>'
        print ' a float, the tolerance that defines convergence of the transition matrix. '
        print ' the test statistic is Sum(|T^(n+1)-T(n)|^2 )'
        print ' default=1e-2 '
        print '-pklFile <pklFile>'
        print ' a string, the name of the pickle file that will store the computed model.'
        print ' defaults to $(modelName).pkl'
        print '-vbose <vbose>'
        print ' an integer, the verbosity level.'
        print ' default=0'
        print ''
############################
if __name__=='__main__':

    nm = nflMarkov()

    expN = 64
    expTol = 0.01

    paramFile = ['paramFiles/nm.default.params.txt']
    ipkl = False
    vbose = 0
    inModelType= None
    inModelName = None
    doSparse = False

    nm.modelType = 'emp_2009_2013'
    nm.modelName = 'emp_2009_2013'

    if len(sys.argv)==1:
        nm.printUsage()
        sys.exit()

    for ia, a in enumerate(sys.argv):
        
        if a=='-expN':
            expN = int(sys.argv[ia+1])
        elif a=='-expTol':            
            expTol = float(sys.argv[ia+1])
        elif a=='-pklFile':            
            ipkl = True
            pklFile = sys.argv[ia+1]
        elif a=='-paramFile':
            paramFile = (sys.argv[ia+1]).split(',')
        elif a=='-modelType':
            inModelType = sys.argv[ia+1]
        elif a=='-modelName':
            inModelName = sys.argv[ia+1]
        elif a=='-vbose':
            vbose = int(sys.argv[ia+1])
        elif a=='-doSparse':
            doSparse = bool(int(sys.argv[ia+1]))
        elif a in ['-h', '-help', '--help']:
            nm.printUsage()
            sys.exit()
        elif '-' in a:
            print 'unknown argument ', a
            raise Exception

    nm.doSparse=doSparse
    nm.vbose = vbose

    for p in paramFile:
        print 'loading file', p
        nm.loadParamsFromFile(p)

    if not inModelType is None:
        nm.modelType = inModelType
    if not inModelName is None:
        nm.modelName = inModelName

    if not ipkl:
        pklFile = '%s.pkl' % nm.modelName

#    print nm.params
    nm.createModelFunctions()

    print 'making transition matrix...'
    nm.makeTransitionMatrix(modelType=nm.modelType)
    imax, jmax = numpy.shape(nm.transitionMatrix)

#    for i in range(imax):
#        if i%1000==0:
#            print i
#        for j in range(jmax):
#            v=nm.transitionMatrix[j][i]

#            if v>1e-2:
#                print i, nm.int2state[i], j, nm.int2state[j], v

    nEndStates = len(nm.endStates)
    mold = copy.deepcopy(nm.transitionMatrix)
    print 'starting exponentiation...'
    mnew = nm.exponentiateMatrix(mold, n=expN, mtol=expTol, doSparse=doSparse)
    nm.resultMatrix = mnew[0:nEndStates,:]
    nm.expectedPoints = (pylab.transpose(nm.resultMatrix)).dot(pylab.reshape(nm.endStatePoints, (nEndStates,1)))


    print 'results for 1st and 10 at the 10, '
    ii = nm.state2int['1_10_10_00']
    for i, v in enumerate(nm.endStates):
        print v, nm.resultMatrix[i,ii]

    print 'results for 1st and 10 at the 20, '
    ii = nm.state2int['1_10_20_00']
    for i, v in enumerate(nm.endStates):
        print v, nm.resultMatrix[i,ii]

    print 'results for 1st and 10 at the 30, '
    ii = nm.state2int['1_10_30_00']

    for i, v in enumerate(nm.endStates):
        print v, nm.resultMatrix[i,ii]

    print 'making diagnostic plots...'
    nm.makeDiagnosticPlots()

    print 'writing pickle...', pklFile
    nm.writePickle(fileName=pklFile)


#    for i in range(imax):
#        for j in range(jmax):
#            v=mnew[j][i]
#            if v>1e-6:
#                print i, nm.int2state[i], j, nm.int2state[j], v
