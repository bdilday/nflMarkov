#! /usr/bin/env python

import os, sys
import nflMarkov 
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import pylab


#########################
def readCsv(ifile):
    skeys = ['date', 'homeTeam', 'awayTeam', 'game_id','player','posteam','oldstate','newstate']
    ikeys = ['seas','igame_id','yds']
    fkeys = []

    dt = []
    lines = [l.strip() for l in open(ifile).readlines()]
    hd = lines[0]
    ks = hd.split(',')
    for k in ks:
        if k in skeys:
            tmp = (k, 'S64')
        elif k in ikeys:
            tmp = (k, 'i4')
        elif k in fkeys:
            tmp = (k, 'f4')
        else:
            tmp = (k, 'f8')
        dt.append(tmp)

    dt = pylab.dtype(dt)
    data = pylab.genfromtxt(ifile, dtype=dt, skip_header=1, delimiter=',')
    return data

#########################
def loadPlayByPlay(csvfile, vbose=0):
    skeys = ['game_id','type','playerName','posTeam','awayTeam','homeTeam']
    ikeys = ['seas','igame_id','dwn','ytg','yfog','yds']
    fkeys = []

    lines = [l.strip() for l in open(csvfile).readlines()]
    hd = lines[0]
    ks = hd.split(',')
    dt = []
    for k in ks:
        # postgres copy to file makes headers lower-case; this is a kludge
        if k=='playername':
            k = 'playerName'
        elif k=='posteam':
            k = 'posTeam'
        elif k=='away_team':
            k = 'awayTeam'
        elif k=='awayteam':
            k = 'awayTeam'
        elif k=='home_team':
            k = 'homeTeam'
        elif k=='hometeam':
            k = 'homeTeam'

        if k in skeys:
            tmp = (k, 'S16')
        elif k in ikeys:
            tmp = (k, 'i4')
        else:
            tmp = (k, 'f8')

        if vbose>=1:
            print k, tmp

        dt.append(tmp)
    dt = pylab.dtype(dt)
    data = pylab.genfromtxt(csvfile, dtype=dt, delimiter=',', skip_header=1)
    return data


#########################
def getExpectedPoints(nm, state):
    i = nm.state2int[state]
    return nm.expectedPoints[i,0]

#########################
def loadStoredModels(nm, modName):
    nm.readPickle(modName)

#########################
if __name__=='__main__':

    nm = nflMarkov.nflMarkov()

#    modName = 'outputData/emp_05142014.pkl'
    modName = 'outputData/emp_05312014.pkl'

#    csvfile = 'inputData/pbp_2009_2013.csv'
#    csvfile = 'inputData/pbp_2002_2010.csv'
    csvfile = 'inputData/pbp_nfldb_2009_2013.csv'

    loadStoredModels(nm, modName)
    k = nm.storedModels.keys()[0]
    mod = nm.storedModels[k]

    tm = mod['transitionMatrix']
    rs = np.transpose(mod['resultMatrix'])
    x = np.reshape(np.array(nm.endStatePoints), (4,1))

    nm.expectedPoints = rs.dot(x)
    xp = np.transpose(nm.expectedPoints)

    pbp = loadPlayByPlay(csvfile, vbose=0)
    print pbp
    
    pp = []
    ishow = True
#    csvfile = 'pe7920_2013.csv'
#    csvfile = 'pe7920_2002_2010.csv'
    csvfile = 'pe7920_nfldb_2009_2013.csv'
    ofp = open(csvfile, 'w')
    ofp.write('seas,game_id,awayTeam,homeTeam,player,posteam,oldstate,oldpoints,pltype,yds,newstate,newpoints,dPE\n')
    for p in pbp:
        print 'hereisp', p
#        print p.dtype
        seas = p['seas']
        if seas!=2013:
#            continue
            pass
        ptype = p['type']
        if not ptype in ['PASS', 'RUSH']:
            continue
        dwn, ytg, yfog, yds = p['dwn'], p['ytg'], p['yfog'], p['yds']
        pl = p['playerName']
        posteam = p['posTeam']

        if dwn==0:
            continue
        if yfog==0:
            continue
        if ytg>20:
            ytg=20

        
        oldState = nm.infoToState(dwn, ytg, yfog)
        newState = nm.getNewState(yds, oldState)
        oldPoints = getExpectedPoints(nm, oldState)
        newPoints = getExpectedPoints(nm, newState)

        ii = nm.state2int[oldState]
        y = np.reshape(tm[:,ii], (7924, 1))
        ans = xp.dot(y)

        avgNewPoints = ans[0,0]
        
        dPE = newPoints-oldPoints
        aPE = avgNewPoints-oldPoints
        PEAA = dPE-aPE


        if not 'game_id' in p.dtype.fields:
            gid = '%4d_%04d' % (seas, p['igame_id'])
        else:
            gid = p['game_id']

        if not 'awayTeam' in p.dtype.fields:
            awayTeam = 'AAA'
        else:
            awayTeam = p['awayTeam']

        if not 'homeTeam' in p.dtype.fields:
            homeTeam = 'HHH'
        else:
            homeTeam = p['homeTeam']

        print (p['seas'], gid, pl, p['posTeam'], oldState, oldPoints, p['type'], yds, newState, newPoints, dPE)

        ofp.write('%d,%s,%s,%s,%s,%s,%s,%.4f,%s,%d,%s,%.4f,%.6f\n'
                      % 
                  (p['seas']
                   , gid
                   , awayTeam, homeTeam
                   , pl
                   , p['posTeam']
                   , oldState, oldPoints, p['type']
                   , yds, newState
                   , newPoints, dPE
                   )
                  )
        
        pp.append(dPE)
    ofp.close()
                  
    pylab.hist(pp, bins=90, color='c')
    pylab.xlabel('d(Points Expectancy)')
    pylab.ylabel('N')
    ax = pylab.gca()
    pylab.text(0.65, 0.8, 'mean= %.3f' % pylab.mean(pp), transform=ax.transAxes)
    pylab.text(0.65, 0.75, 'std = %.3f' % pylab.std(pp), transform=ax.transAxes)
    pylab.title('PE7920 (2013)')
    pylab.savefig('PE7920_2013_1.png')

    if ishow:
        pylab.show()

    data = readCsv(csvfile)
