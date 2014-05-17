#!/usr/bin/env python

import os, sys
import pylab
import pickle
import minuit

xx_f = []
yy_f = []
ss_f = []
mm_f = []

#########################
def doRushDist(data, lplot=False):
    mx = max(data['yds'])
    mn=min(data['yds'])
    print mn, mx, mx-mn
#    ans = pylab.hist(data['yds'], bins=(mx-mn), normed=True)
    ans = pylab.hist(data['yds'], bins=range(mn, mx+2), normed=True)

#    xx = ans[1][1:]
    xx = ans[1][0:-1]
    yy = ans[0][:]
    for i, v in enumerate(xx):
        x = xx[i]
        y = yy[i]
        
        if y>0:
#            s = 0.5/pylab.sqrt(y)
            s = 1.0
        else:
            s = 1000

        # for the pass distribution, deweight the incompletes at x=0
        if x==0:
            s = 1e6

        xx_f.append(x)
        yy_f.append(y)
        ss_f.append(s)
        mm_f.append(0)

    m0 = sum(xx*yy)/sum(yy)

#    mm = minuit.Minuit(fitGamma, A=1, k=pylab.mean(xx), t=1)
#    mm = minuit.Minuit(fit2Gauss, x0=m0*3.7/5, s1=1.9, s2=2.5, xin=xx_f, yin=yy_f, sin=ss_f)
#    mm = minuit.Minuit(fit2Gauss, x0=m0*3.7/5, s1=1.9, s2=2.5, nn=1)


#    mm = minuit.Minuit(fitBazin, A=0.1, x0=4.0, s1=2.0, s2=6.0)

    mm = minuit.Minuit(fitBazinPlusGaus, A=0.1, x0=4.0, s1=2.0, s2=6.0, G=0.05, g0=-7.0, gs=2.0)


#    mm.limits['s1'] = (0, 9e9)
#    mm.limits['s2'] = (0, 9e9)
#    mm = minuit.Minuit(fitGaussTimesPoly, A=0.02, x0=4.5, B=-0.5, C=0.5, s1=2.5)


#    mm = minuit.Minuit(fitExpPoly, A=max(yy), x0=m0, a1=1, b1=1, a2=1, b2=1)
    mm.migrad()
    return mm

#########################
def fitExpPoly(A, x0, a1, b1, a2, b2):
    llk = 0.0
    xxp = []
    yyp = []
    for i, v in enumerate(xx_f):

        if v>x0:            
            tx = abs(v-x0)
            test = A * pylab.exp(-(a1 * tx**2 + b1 * tx))
        else:
            tx = abs(v-x0)
            test = A * pylab.exp(-(a2 * tx**2 + b2 * tx))

        lk = (test-yy_f[i])/ss_f[i]
        llk += lk*lk
        xxp.append(v)
        yyp.append(test)        
    print A, x0, a1, b1, a2, b2, llk
    pylab.clf()
    pylab.plot(xxp, yyp)
#    pylab.show()
    return llk

#########################
def fitGaussTimesPoly(A, x0, B, C, s1):
    llk = 0.0
    xxp = []
    yyp = []
    for i, v in enumerate(xx_f):
        tx = v-x0
        test = A * (1 + B*tx + C*tx**2 ) * pylab.exp(-0.5*(tx/s1)**2)

        lk = (test-yy_f[i])/ss_f[i]
        llk += lk*lk
        xxp.append(v)
        yyp.append(test)
        mm_f[i] = test        

    print A, x0, B, C, s1, llk
    pylab.clf()
    pylab.plot(xxp, yyp)
#    pylab.show()
    return llk

#########################
def fitBazin(A, x0, s1, s2):
    llk = 0.0
    xxp = []
    yyp = []
    for i, v in enumerate(xx_f):
        k1 = 1.0*s1
        k2 = (s2*s1)/(1.0*s1+s2)
        tx = 1.0*(v-x0)

#        test = A * pylab.exp(tx/s1)/(1.0 + pylab.exp(tx/s2))
        test = A * pylab.exp(tx/k1)/(1.0 + pylab.exp(tx/k2))

        lk = (test-yy_f[i])/ss_f[i]
        llk += lk*lk
        xxp.append(v)
        yyp.append(test)
        mm_f[i] = test        

    print A, x0, s1, s2, llk
#    pylab.clf()
#    pylab.plot(xxp, yyp)
#    pylab.show()
    return llk

#########################
def fitBazinPlusGaus(A, x0, s1, s2, G, g0, gs):
    llk = 0.0
    xxp = []
    yyp = []
    for i, v in enumerate(xx_f):
        k1 = 1.0*s1
        k2 = (s2*s1)/(1.0*s1+s2)
        tx = 1.0*(v-x0)

#        test = A * pylab.exp(tx/s1)/(1.0 + pylab.exp(tx/s2))
        test = A * pylab.exp(tx/k1)/(1.0 + pylab.exp(tx/k2))
        test += G*pylab.exp(-0.5*((v-g0)/gs)**2)

        lk = (test-yy_f[i])/ss_f[i]
        llk += lk*lk
        xxp.append(v)
        yyp.append(test)
        mm_f[i] = test        

    print A, x0, s1, s2, G, g0, gs, llk
#    pylab.clf()
#    pylab.plot(xxp, yyp)
#    pylab.show()
    return llk

#########################
def fit2Gauss(x0, s1, s2, nn):
    llk = 0.0
    xxp = []
    yyp = []
    A = 1/(s1  + pylab.sqrt(pylab.pi/2)*s2)
    for i, v in enumerate(xx_f):

        if v>x0:            
            tx = abs(v-x0)
            test = A * pylab.exp(-(tx/s1)**nn)
        else:
            tx = abs(v-x0)
            test = A * pylab.exp(-0.5*(tx/s2)**2)

        mm_f[i] = test
        lk = (test-yy_f[i])/ss_f[i]
        llk += lk*lk
        xxp.append(v)
        yyp.append(test)
    
    print A, x0, sum(xx_f*pylab.array(yy_f))/sum(yy_f), s1, s2, nn, llk
    pylab.clf()
    pylab.plot(xxp, yyp)
#    pylab.show()
    return llk

#########################
def fitGamma(A, k, t):
    llk = 0.0
    xxp = []
    yyp = []
    for i, v in enumerate(xx_f):
        test = A * v**(k-1.0) * pylab.exp(-1.0*v*t)
        lk = (test-yy_f[i])/ss_f[i]
        llk += lk*lk
        xxp.append(v)
        yyp.append(test)        
    print A, k, t, llk
    pylab.clf()
    pylab.plot(xxp, yyp)
    pylab.show()
    return llk

#########################
def readCsv(ifile='nflPlayFreq.csv'):
    lines = [l.strip() for l in open(ifile).readlines()]
    hd = lines[0]
    tmp = []
    skeys = ['type']
    ikeys = ['game_id'
             ,'seas','drive_id','dwn','ytg'
             ,'yfog','yds','pts','dseq','suc','pts_o','pts_d', 'pts'
             ]
    
    for k in hd.split(','):
        if k in skeys:
            x = [k, 'S16']
        elif k in ikeys: 
            x = [k, 'i4']
        elif k in fkeys: 
            x = [k, 'f4']
        else:
            x = [k,'f8']
        tmp.append(tuple(x))
    dt = pylab.dtype(tmp) 
    q = pylab.genfromtxt(ifile, dtype=dt, skip_header=1, delimiter=',')
    return q

#########################
def doPlot_ydsVsFpos(data, cols=['k','b']):
    xx = []
    yy = []
    ss = []
    for i in range(1,100):
        cc = pylab.logical_and(data['yfog']==i, True)
        xx.append(i)
        if sum(cc)==0:
            y = 0
            s = 0
        else:
            y = pylab.mean(data[cc]['yds'])
            s = pylab.std(data[cc]['yds'])
        print i, y, s, sum(cc)
        yy.append(y)
        ss.append(s)

    ss = pylab.array(ss)
    pylab.plot(xx, yy,cols[0])
    pylab.plot(xx, yy+ss,cols[1]+'--')
    pylab.plot(xx, yy-ss,cols[1]+'--')
    pylab.xlabel('yards from own goal')
    pylab.ylabel('yards')
    pylab.ylim(-10, 25)

#########################
def doPlot_ydsVsYtg(data, cols=['k','b']):
    xx = []
    yy = []
    ss = []
    for i in range(1,21):
        cc = pylab.logical_and(data['ytg']==i, True)
        xx.append(i)
        if sum(cc)==0:
            y = 0
            s = 0
        else:
            y = pylab.mean(data[cc]['yds'])
            s = pylab.std(data[cc]['yds'])
        print i, y, s, sum(cc)
        yy.append(y)
        ss.append(s)

    ss = pylab.array(ss)
    pylab.plot(xx, yy,cols[0])
    pylab.plot(xx, yy+ss,cols[1]+'--')
    pylab.plot(xx, yy-ss,cols[1]+'--')
    pylab.xlabel('yards to go')
    pylab.ylabel('yards gained')
    pylab.ylim(-10, 25)

#########################
def doPlot_runpassVsYfog(data, cols=['k','b']):
    nall = len(data)
    xx = []
    yy = []
    ss = []
    for i in range(1,100):
        cc = pylab.logical_and(data['yfog']==i, True)
        xx.append(i)
        if sum(cc)==0:
            y = 0
            s = 0
        else:
            np = sum(pylab.logical_and(data['type']=='PASS', data['yfog']==i))
            nr = sum(pylab.logical_and(data['type']=='RUSH', data['yfog']==i))
            nall = np+1.0*nr                     
            if nall>0:
                y = pylab.mean(np/nall)
                s = 0.5/pylab.sqrt(nall)
            else:
                y = 0
                s = 0

        print i, y, s, nall, sum(cc)
        yy.append(y)
        ss.append(s)

    ss = pylab.array(ss)
    pylab.plot(xx, yy,cols[0])
#    pylab.plot(xx, yy+ss,cols[1]+'--')
#    pylab.plot(xx, yy-ss,cols[1]+'--')
    pylab.xlabel('yards from own goal')
    pylab.ylabel('fraction passing')
    pylab.ylim(0, 1)

#########################
def doPlot_runpassVsYtg(data, cols=['k','b']):
    nall = len(data)
    xx = []
    yy = []
    ss = []
    for i in range(1,21):
        cc = pylab.logical_and(data['ytg']==i, True)
        xx.append(i)
        if sum(cc)==0:
            y = 0
            s = 0
        else:
            np = sum(pylab.logical_and(data['type']=='PASS', data['ytg']==i))
            nr = sum(pylab.logical_and(data['type']=='RUSH', data['ytg']==i))
            nall = np+1.0*nr                     
            if nall>0:
                y = pylab.mean(np/nall)
                s = 0.5/pylab.sqrt(nall)
            else:
                y = 0
                s = 0

        print i, y, s, nall, sum(cc)
        yy.append(y)
        ss.append(s)

    ss = pylab.array(ss)
    pylab.plot(xx, yy,cols[0])
#    pylab.plot(xx, yy+ss,cols[1]+'--')
#    pylab.plot(xx, yy-ss,cols[1]+'--')
    pylab.xlabel('yards from own goal')
    pylab.ylabel('fraction passing')
    pylab.ylim(0, 1)


#########################
def doRushByYfog(data, iShow=True):

    xx = []
    mm = []
    ss1 = []
    ss2 = []

    dy = 100
    y0 = 1

    rdata = {}
    rdata['xx'] = []
    for i in range(y0,100,dy):


        rdata['xx'].append(i)

#        cc = pylab.logical_and(data['yfog']==i, True)
        cc = pylab.logical_and(data['yfog']>=i, data['yfog']<(i+dy)) 
        print '*** i =', i, sum(cc)        
        if sum(cc)==0:
            for v in ans.values:
                if not v in rdata:
                    rdata[v] = []
                rdata[v].append(ans.values[v])
            continue
        while(len(xx_f))>0:
            xx_f.pop()
            yy_f.pop()
            mm_f.pop()
            ss_f.pop()
        ans = doRushDist(data[cc])


        for v in ans.values:
            if not v in rdata:
                rdata[v] = []
            rdata[v].append(ans.values[v])

#        nb = max(data['yds'])-min(data['yds'])
        nb = range(min(data['yds']), max(data['yds'])+2, 1)
        pylab.clf()
        pylab.plot(xx_f, mm_f, 'k-')
        pylab.hist(data[cc]['yds'], bins=nb, normed=True, align='left')

        if iShow:
            pylab.show()

    return rdata


#########################
def doRushByYtg(data, iShow=True):

    xx = []
    mm = []
    ss1 = []
    ss2 = []

    dy = 2
    y0 = 1
    rdata = {}
    rdata['xx'] = []
    for i in range(y0,20,dy):

        rdata['xx'].append(i)
#        cc = pylab.logical_and(data['yfog']==i, True)
        cc = pylab.logical_and(data['ytg']>=i, data['ytg']<(i+dy)) 
        print '*** i =', i, sum(cc)        
        if sum(cc)==0:
            for v in ans.values:
                if not v in rdata:
                    rdata[v] = []
                rdata[v].append(ans.values[v])
            continue
        while(len(xx_f))>0:
            xx_f.pop()
            yy_f.pop()
            mm_f.pop()
            ss_f.pop()
        ans = doRushDist(data[cc])


        for v in ans.values:
            if not v in rdata:
                rdata[v] = []
            rdata[v].append(ans.values[v])

#        nb = max(data['yds'])-min(data['yds'])
        nb = range(min(data['yds']), max(data['yds'])+2, 1)
        pylab.clf()
        pylab.plot(xx_f, mm_f, 'k-')
        pylab.hist(data[cc]['yds'], bins=nb, normed=True, align='left')

        if iShow:
            pylab.show()

    return rdata


#########################
if __name__=='__main__':
    pfile = 'nflPlayFreq.pkl'
    if os.path.exists(pfile):
        pfp = open(pfile,'rb')
        q = pickle.load(pfp)
        pfp.close()
    else:
        q = readCsv()
    print q


#    cc = pylab.logical_and(q['type']=='RUSH', q['dwn']<=4)
    cc = pylab.logical_and(q['type']=='PASS', q['dwn']<=4)

#    cc = pylab.logical_and(q['type']=='RUSH', q['dwn']==1)

#    cc = pylab.logical_and(q['type']=='RUSH', q['dwn']==3)
    tmp = q[cc]
#    xx, mm, ss1, ss2 = 

#    tmp = doRushByYfog(tmp, iShow=True)
    tmp = doRushByYfog(tmp, iShow=False)
#    tmp = doRushByYtg(tmp, iShow=True)


    pylab.clf()
    pylab.plot(tmp['xx'], tmp['x0'], 'k-')
    pylab.plot(tmp['xx'], tmp['s1'], 'b-')
    pylab.plot(tmp['xx'], tmp['s2'], 'r-')

    ga = []
    for i, v in enumerate(tmp['xx']):
        print '%d ' % v,
        for k in ['A', 'x0', 's1', 's2', 'G', 'g0', 'gs']:
            print '%.3f ' % (tmp[k][i]),
        print '%.3f ' % (tmp['G'][i]/tmp['A'][i]),
        ga.append(tmp['G'][i]/tmp['A'][i])
        print 

    for k in ['A', 'x0', 's1', 's2', 'G', 'g0', 'gs']:
        print k, pylab.mean(tmp[k]),
    print k, pylab.mean(ga)
    print 


    pylab.show()

#    nb = max(q[cc]['yds'])-min(q[cc]['yds'])
#    pylab.hist(q[cc]['yds'], bins=nb, normed=True)
#    pylab.show()
