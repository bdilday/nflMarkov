
import numpy as np
from matplotlib import pyplot as plt
import nflMarkov
from matplotlib import cm

def enumerateDowns(nm):
    aa = {}
    for i in range(nm.transitionMatrix.shape[0]):
        dwn, ytg, yfog, parity = nm.stateToInfo(nm.int2state[i])
        if dwn is None:
            continue
        xfog = yfog + 100*parity
        k = '%d_%03d' % (dwn, xfog)
        if not k in aa:
            aa[k] = []
        aa[k].append(i)
    return aa

def parseStateColumn(s, aa):
    kk = np.zeros((5, 200))
    for parity in range(2):
        for dwn in range(1, 4+1):
            for yfog in range(1, 99+1):
                xfog = yfog + 100*parity
                k = '%d_%03d' % (dwn, xfog)
                idx = aa[k]
                v = s[idx].sum()
                kk[dwn-1, xfog-1] = v
    kmax = kk.max()
    smax = s[0:4].max()
    if smax<1e-6:
        smax = 1.0
    kk[4, 10] = s[0]
    kk[4, 20] = s[1]
    kk[4, 30] = s[2]
    kk[4, 40] = s[3]

    kk[4, 110] = s[4]
    kk[4, 120] = s[5]
    kk[4, 130] = s[6]
    kk[4, 140] = s[7]

    #kk[4, 99] = 1

    return kk


def stateColumnToHeatmap(s, aa):
    kk = parseStateColumn(s, aa)

    plt.pcolor(kk, cmap=cm.Greys)
    return kk

def makeGif(nm, state0, nfinal=20):

    i = nm.state2int[state0]
    s = np.zeros(nm.transitionMatrix.shape[0])
    s[i] = 1.0
    mt = nm.transitionMatrix.transpose()
    aa = enumerateDowns(nm)

    i = 0
    ofile =  'tmp/pca_%05d.jpg' % i
    kk = stateColumnToPlot(s, aa)
    plt.savefig(ofile)

    plt.subplot(5,2,1)
    plt.text(1, 0.9*plt.ylim()[1], 'step: %03d' % i, fontsize=6)

    for i in range(1, 1+nfinal):
        s = s.dot(mt); kk = stateColumnToPlot(s, aa)
        ofile =  'tmp/pca_%05d.jpg' % i
        plt.subplot(5,2,1)
        plt.text(1, 0.9*plt.ylim()[1], 'step: %03d' % i, fontsize=6)
        plt.savefig(ofile)

def stateColumnToPlot(s, aa, makeGif=False):
    kk = parseStateColumn(s, aa)

    plt.clf()

    ylabs = ['1st down', '2nd down', '3rd down', '4th down', 'scoring events']

    for i in range(5):
        for j in range(2):
            plt.subplot(5, 2, 2*i+j + 1)
            if j==0:
                plt.plot(kk[i, 0:100], drawstyle='steps', color='k')
                plt.ylabel(ylabs[i])
            else:
                plt.plot(kk[i, 100:], drawstyle='steps', color='k')
            plt.xticks([])
            plt.yticks([])
            plt.ylim(0,kk[0:4].max())

            if i==0:
                plt.title('team %d' % (j+1), fontsize=8)

            if i==4:
                plt.xlabel('yards-from-own-goal')
                plt.text(11, 0.5*plt.ylim()[1], 'S', fontsize=6)
                plt.text(32, 0.5*plt.ylim()[1], 'FG', fontsize=6)
                plt.text(41, 0.5*plt.ylim()[1], 'TD', fontsize=6)


    plt.subplots_adjust(wspace=0.001, hspace=0.001)

    return kk


if __name__=='__main__':
    nm = nflMarkov.nflMarkov()
    nm.modelType = 'emp_2009_2013'
    nm.modelName = 'emp_2009_2013'

    paramFile = ['nm.default.params.txt']
    ipkl = False
    vbose = 0
    inModelType= None
    inModelName = None


    for p in paramFile:
        print 'loading file', p
        nm.loadParamsFromFile(p)

    if not inModelType is None:
        nm.modelType = inModelType
    if not inModelName is None:
        nm.modelName = inModelName

    nm.createModelFunctions()

    print 'making transition matrix...'
    nm.makeTransitionMatrix(modelType=nm.modelType)
    imax, jmax = np.shape(nm.transitionMatrix)

    idx_start = nm.state2int[nm.infoToState(1, 10, 20)]
    s = np.zeros(imax)
    s[idx_start] = 1

