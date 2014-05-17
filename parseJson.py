#!/usr/bin/env python


import os, sys
import json
import re, glob


#########################
def parsePlay(desc):
    ''' given the string descrption of the play, parse in to 
    pass, rush, punt, etc + yards gained.
    to make it easier, the minimum we need to 
    pass on to the markov chain code is
    dwn, ytg, yfog, yds
    '''

    if 'TWO-POINT CONVERSION' in desc:
        type = 'TWOP'
        yds = 0

    elif 'substitution infraction' in desc:
        type = 'NOPL'
        yds = 0

    elif 'Replay Ass' in desc:
        type = 'NOPL'
        yds = 0

    elif 'play under review' in desc:
        type = 'NOPL'
        yds = 0

    elif 'INJURY UPDATE' in desc:
        type = 'NOPL'
        yds = 0

    elif len(desc)==0:
        type = 'NOPL'
        yds = 0

    elif 'temporary suspension of play' in desc:
        type = 'NOPL'
        yds = 0

    elif len(''.join(desc.split(')')[1:]))==0:
        type = 'NOPL'
        yds = 0

    elif 'enforced between downs' in desc:
        type = 'PENA'
        try:
            m = re.search('\s+(-{0,1}[0-9]+)\s+yard', desc)
            yds = int(m.group(1))
        except AttributeError:
            yds = 0

    elif 'no play' in desc.lower():
        type = 'NOPL'
        try:
            m = re.search('\s+(-{0,1}[0-9]+)\s+yard', desc)
            yds = int(m.group(1))
        except AttributeError:
            yds = 0

    elif 'pass' in desc:
        type = 'PASS'
        if 'incomplete' in desc:
            yds = 0
        else:
            if 'no gain' in desc:
                yds = 0
            elif 'INTERCEP' in desc:
                type = 'TO'
                yds = 0
            else:
                try:
                    m = re.search('\s+(-{0,1}[0-9]+)\s+yard', desc)
                    print m.group(1)
                    yds = int(m.group(1))
                except AttributeError:
                    print '***************'
                    print 'regexp failed. exit.'
                    print desc
                    sys.exit()

    elif 'spiked' in desc:
        type = 'PASS'
        yds = 0
    elif 'FUMBLE' in desc:
        type = 'TO'
        yds = 0
    elif 'punt' in desc:
        type ='PUNT'
        yds = 0

    elif 'extra point' in desc:
        type = 'FG10'
        yds = 0

    elif 'field goal' in desc:

        print 'xxx', desc
        yds = 0
        if 'no good' in desc.lower():
            type = 'FG00'
        elif 'BLOCKED' in desc:
            type = 'FG00'
        elif 'fake field goal' in desc.lower():
            try:
                m = re.search('\s+(-{0,1}[0-9]+)\s+yard', desc)
                print m.group(1)
                yds = int(m.group(1))
            except AttributeError:
                print '***************'
                print 'regexp failed. exit.'
                print desc
                sys.exit()    
            type = 'RUSH'

        elif 'good' in desc.lower():
            type = 'FG01'

        else:
            print '**********'
            print desc
            raise Exception


    elif 'Neutral Zone Infrac' in desc:
        type = 'PENA'
        m = re.search('\s+(-{0,1}[0-9]+)\s+yard', desc)
        yds = int(m.group(1))

    elif 'declined' in desc:
        type = 'PENA'
        yds = 0

    elif 'sacked' in desc:
        type = 'PASS'
        m = re.search('\s+(-{0,1}[0-9]+)\s+yard', desc)
        yds = int(m.group(1))

    elif 'kicks' in desc:
        type = 'KICK'
        yds = 0

    else:
        type = 'RUSH'
        if 'no gain' in desc:
            yds = 0
        else:
            try:
                m = re.search('for\s+(-{0,1}[0-9]+)\s+yard', desc)
                yds = int(m.group(1))
            except AttributeError:
                print '***************'
                print 'regexp failed. exit.'
                print desc
                sys.exit()

    return type, yds

#########################
def parseJson(ifile):
    ''' output should be game_id, seas, drive_id, dwn, ytg, yfog, type, 
    yds, pts, dseq, suc, pts_o, pts_d. Then it will be straight-forward to 
    use existing code to generate transition matrix '''

    vetoKeys = ['END GAME', 'Minute Warning', 'Timeout', 'END QUARTER']

    fp = open(ifile)
    j = json.load(fp)
    fp.close()

    data = []

    try:
        dk = j.keys()[1]
        ns = j[dk]['drives'].keys()
    except TypeError:
        dk = j.keys()[0]
        ns = j[dk]['drives'].keys()
    for n in ns:
        if n=='crntdrv':
            continue
        print dk, n
        ps = j[dk]['drives'][n]['plays'].keys()
        print dk, n, ps
        for p in ps:
#            print p, 
            x=j[dk]['drives'][n]['plays'][p]
            dwn = x['down']
            dist = x['ydstogo']
            sfog = x['yrdln']
            posteam = x['posteam']
            desc = x['desc']
            if len(sfog)==0:
                continue
            print p, dwn, dist, posteam, desc , '|', sfog

            iveto = False
            for vk in vetoKeys:
                if vk in desc:
                    iveto = True

            if iveto:
                continue

            try:
                yfog = int(sfog.split()[1])
            except IndexError:
                print x
                yfog = int(sfog.split()[0])
            if not posteam in sfog:
                yfog = 100 - yfog
            print p, dwn, dist, yfog, posteam
            type, yds = parsePlay(desc)
            data.append(tuple([dwn, dist, yfog, type, yds]))
    return data

#########################
if __name__=='__main__':
    fs = glob.glob('*json')
    ifile = fs[0]
    ifile = '2009110801.json'

    ofp = open('pbpJson.csv', 'w')
    ofp.write('game_id,seas,dwn,ytg,yfog,type,yds\n')
    ig = 0
#    for ifile in fs[0:10]:
    for ifile in fs[:]:
        ig += 1
        seas = int(ifile[0:4])
        data = parseJson(ifile)
        for d in data:
            print ig, seas, d 
            ofp.write('%d,%d,' % (ig, seas))
            for v in d[0:-1]:
                ofp.write('%s,' % str(v))
            v = d[-1]
            ofp.write('%s\n' % str(v))
    ofp.close()
