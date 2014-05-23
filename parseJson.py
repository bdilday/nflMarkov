#!/usr/bin/env python


import os, sys
import json
import re, glob


#########################
def parsePlay(desc, vbose=0):
    ''' given the string descrption of the play, parse in to 
    pass, rush, punt, etc + yards gained.
    to make it easier, the minimum we need to 
    pass on to the markov chain code is
    dwn, ytg, yfog, yds
    '''

    if vbose>=2:
        print 'starting desc', desc

    if 'eligble' in desc:
        desc = desc.replace('eligble', 'eligible')

    desc = desc.replace('{','')
    desc = desc.replace('}','')


    playerRegExp = re.compile('([A-Za-z]+\.+\s*[A-Za-z]+)\s+.+\s+')
    playerAndYardsRegExp = re.compile('([A-Za-z]+\.+\s*[A-Za-z]+)\s+.+\s+(-{0,1}[0-9]+)\s+yard')


    fullNames = ['Alex Smith', 'Brad Smith']
    for fn in fullNames:
        if fn in desc:
            abbrev = '.'.join([fn.split()[0][0], fn.split()[1]])
            desc = desc.replace(fn, abbrev)
            if vbose>=2:
                print 'abbrev', fn, abbrev


    if ' Ryan' in desc:
        desc = re.sub('\s+Ryan',' M.Ryan',desc)

    if desc=='(6:22) (Run formation) T.Jones right tackle to NYJ 25 for 4 yards (J.Lacey). Direct Snap to NYJ B. Smith (16).':
        desc = '(6:22) (Run formation) T.Jones right tackle to NYJ 25 for 4 yards (J.Lacey)'


    if 'direct snap' in desc.lower():
        desc = desc.replace('Wildcat:','')
        desc = desc.replace('Tiger Formation','')
        desc = re.sub('Direct [Ss]nap to #[0-9]+\s+[A-Z]\.\s+[A-Za-z]+\.*', '', desc)
        desc = re.sub('Direct [Ss]nap to #[0-9]+\s+[A-Za-z]+\.*', '', desc)

        desc = re.sub('Direct snap.+who\s+handed\s+off\s+to\s+#*[0-9]+\s+[A-Za-z]+\.*', '', desc)
        desc = re.sub('Direct [Ss]nap to [A-Z]+\s+#[0-9]+\s+[A-Z]\.\s+[A-Za-z]+\.*', '', desc)
        desc = re.sub('Direct snap to [A-Z]+\.+[A-Za-z]+\.*','',desc)


    if 'reports as eligible' in desc:
        desc = re.sub('as eligible for [A-Z]+\.*','',desc)

    if 'in at QB' in desc:
        desc = re.sub('in at QB for [A-Z]+', 'in at QB', desc)


    if 'new quarterback' in desc.lower():
        desc = re.sub('New quarterback for the [A-Za-z]+ is #*[0-9]+\s+[A-Z]+\.+\s+[A-Za-z]+\.+', '', desc)
        desc = re.sub('New quarterback for [A-Za-z]+\s*[A-Za-z]+ is #*[0-9]+\s+[A-Za-z]+\s*\.*\s*[A-Za-z]+\.+', '', desc)



    if 'lines up as QB':
        desc = re.sub('[0-9]+\s+[A-Za-z]+\s+lines up as QB\.*','',desc)

    if 'New QB' in desc:
        desc = re.sub('New QB\s+-\s+#*[0-9]+\s*\.*\s*[A-Za-z]+\.+\s+[A-Za-z]+\.+', '', desc)
        desc = re.sub('New QB for\s+[A-Za-z]+\s+-\s+No\.\s+[0-9]+\s+-\s+[A-Za-z]+\s+[A-Za-z]+', '', desc)
        desc = re.sub('New QB\s+-\s+#*[0-9]+\s+[A-Z]+\.+[A-Za-z]+\.*', '', desc)

    if 'Direction change to' in desc:
        desc = re.sub('Direction change to the [0-9]+\s+', '', desc)


    cutoffers = ['(Pass formation)'
                 ,'(Shotgun)'
                 ,'(Punt formation)'
                 ,'(Field Goal formation)'
                 ,'at QB.'
                 ,'at QB'
                 ,'in at QB'
                 ,'returns as QB'
                 ,'lines up at Quarterback.'

                 ,'in at Quarterback.'
                 ,'in at Quarterback'

                 ,'takes over at QB.'
                 ,'takes over at QB'


                 ,'Direct snap to #23 Brown, whom then handed off to #34 Williams.'

                 ,'on change of possession.'
                 ,'on the change of possession.'
                 ,'due to change of possession.'
                 ,'after change of possession.'
                 ,'result of change of possession.'
                 ,'with change of possession.'

                 ,'on change of possession'
                 ,'on the change of possession'
                 ,'due to change of possession'
                 ,'after change of possession'
                 ,'result of change of possession'
                 ,'with change of possession'

                 ,'Seminole Formation.'
                 ,'Seminole Formation'

                 ,'Seminole formation.'
                 ,'Seminole formation'

                 ,'elibible reciever.'

                 ,'eligible receiver'
                 ,'eligible.'
                 ,'Eligible'
                 ,'eligible'

                 ,'Direct snap to B.Smith.'

                 ,'Ball spotted incorrectly.'
                 ,'after ball flip.'
                 ,'for the start of the drive.'


                 ,'Direct snap to #29 L. Washington.'
                 ,'Direct snap'
                 ,'Direct Snap'


                 ,'is now playing'

                 ,'Direction Change.'
                 ,'Direction Change!'

                 ,'NFL debut.'
                 ,'with a shoulder injury.'
                 ,'with a concussion'

                 ,'victory formation'

                 ]


    for x in cutoffers:
        if x in desc:
            desc = desc.split(x)[-1]

    replacers = ['(No Huddle)'
                 ,'(No Huddle, Shotgun)'
                 ,'(Run formation)'

                 ,'Flynn in at qb'

                 ,'Reverse'

                 ,'New BAL QB - T.Taylor'
                 ,'New QB CIN - B.Gradkowski'

                 ,'for BLT.'

                 ,'One-yard difference on change of possession.'
                 ,'NE-61 reports eligible'
                 ,'77 - reports eligible'
                 ,'{line of scimmage changed with change of possession}'
                 ,'#7 in at QB'
                 ,'#70 is eligible.'
                 ,'direct snap to 44-Snelling. (Shotgun)'
                 ,'direct snap to 23-Brown. (Shotgun)'
                 ,'Yardline moved on change of possession.'
                 ,'Wildcat, direct snap to B.Smith (M.Sanchez at WR).'
                 ,'Wildcat, direct snap to F.Jackson (R.Fitzpatrick not on field).'
                 ,' change in yard line due to change in possession '

                 ,'{Yard line changed due to change of possession}'
                 ,'Yardline difference due to change of possession.'
                 ,'{Yard line changed with change of possession} '
                 ,'Yardline difference due to change of possession.'
                 ,'#78 and #61 are eligible.'
                 ,'Min #7 - T. Jackson in at QB.'
                 ,'MIA #75 Garner reports as eligible. Direct snap to #23 Brown, whom then handed off to #34 Williams.'
                 'MIA 7-Henne now at QB.'
                 ,'MIA #75 Garner reports as eligible. Direct snap to #23 Brown, whom then handed off to #34 Williams.'
                 ,'MIA 7-Henne now at QB.'
                 ,'MIA 16-Thigpen now at QB.'
                 ,'Direct snap to #23 Brown, whom then handed off to #34 Williams.'
                 ,'Direct snap to 16 Smith who handed off to 23 Greene.'
                 ]

    for r in replacers:
        if r in desc:
            desc = desc.replace(r, '')

    if 'NE 12-Brady 38th' in desc:
        desc = desc.split('NE 12-Brady 38th')[0]
#    desc = desc.replace('.','')

    hyphers = ['Jones-Drew'
               , 'Stephens-Howling'
               ,'Heyward-Bey'
               ,'Green-Ellis'
               ]
    for h in hyphers:
        desc = desc.replace(h, h.replace('-',''))

    aposters = ['O\'Sullivan'
                ,'W.Ta\'ufo\'ou'
                ]

    for h in aposters:
        desc = desc.replace(h, h.replace('\'',''))

    playerName = None
    if 'TWO-POINT CONVERSION' in desc:
        type = 'TWOP'
        yds = 0

    elif 'substitution infraction' in desc:
        type = 'NOPL'
        yds = 0

    elif 'play was not reviewable' in desc:
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
        m = re.search(playerRegExp, desc)
        playerName = m.group(1)
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
                    m = re.search(playerAndYardsRegExp, desc)
                    print m.groups()
                    playerName = m.group(1)
                    yds = int(m.group(2))
                except AttributeError:
                    print '***************'
                    print 'regexp failed. exit.'
                    print desc
                    sys.exit()

    elif 'field goal' in desc:

        print 'xxx', desc
        yds = 0
        if 'no good' in desc.lower():
            type = 'FG00'
        elif 'BLOCKED' in desc:
            type = 'FG00'
        elif 'fake field goal' in desc.lower():
            try:
                m = re.search(playerAndYardsRegExp, desc)
                print m.groups()
                playerName = m.group(1)
                yds = int(m.group(2))
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

    elif 'spiked' in desc:
        type = 'PASS'
        m = re.search(playerRegExp, desc)
        playerName = m.group(1)
        yds = 0

    elif 'FUMBLE' in desc:
        type = 'TO'
        m = re.search(playerRegExp, desc)
        playerName = m.group(1)
        yds = 0

    elif 'punt' in desc:
        type ='PUNT'
        yds = 0

    elif 'extra point' in desc:
        type = 'FG10'
        yds = 0

    elif 'Neutral Zone Infrac' in desc:
        type = 'PENA'
        m = re.search('\s+(-{0,1}[0-9]+)\s+yard', desc)
        yds = int(m.group(1))

    elif 'declined' in desc:
        type = 'PENA'
        yds = 0

    elif 'sacked' in desc:
        type = 'PASS'
        m = re.search(playerAndYardsRegExp, desc)
        playerName = m.group(1)
        yds = int(m.group(2))

    elif 'kicks' in desc:
        type = 'KICK'
        yds = 0

    else:
        type = 'RUSH'
        if 'no gain' in desc:
            yds = 0
            m = re.search(playerRegExp, desc)
            playerName = m.group(1)
        else:
            try:
                m = re.search(playerAndYardsRegExp, desc)
                playerName = m.group(1)
                yds = int(m.group(2))
            except AttributeError:
                print '***************'
                print 'regexp failed. exit.'
                print desc
                sys.exit()

    questionables = ['in', 'is', 'line', 'reports', 'yard','and','ball','Yard','Yardline','change','direct'
                     ,'Min', 'MIA', 'MIN'
                     ,'TB', 'TEN'
                     ,'The', 'Tiger'
                     , 'ARI', 'BUF'
                     , 'Ball', 'Change'
                     ,'Direct', 'Direction'
                     ,'Eligible', 'Field'
                     , 'IND', 'Kevin'
                     ,'Alex', 'Brad', 'Clemens', 'Cutler'
                     ,'Jackson', 'Line'
                     ,'Matt', 'McNabb', 'NFL', 'New'
                     ,'Flynn','Pass','Ravens','Reverse','Rodgers','Ryan'
                     ,'Seminole'
                     ,'Smith', 'Svitek', 'Vick', 'for', 'h.Hill'
                     ,'ou', 'receiver', 'to'
                     ,'Rodgers left', 'Rodgers right', 'Rodgers up'
                     ]

    if type=='PASS' and playerName in questionables:
        print '**************************'
        print 'the player name (%s) is questionable!' % playerName
        print desc
        print type, yds, playerName
        raise Exception

    if not playerName is None:
        playerName = playerName.replace(' ','')

    return type, yds, playerName

#########################
def parseJson(ifile, vbose=0):
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
            type, yds, playerName = parsePlay(desc, vbose=vbose)
            data.append(tuple([dwn, dist, yfog, type, yds, playerName]))
    return data

#########################
if __name__=='__main__':
    fs = glob.glob('./jsonFiles/*json')
    ifile = fs[0]
    ifile = '2009110801.json'
    vbose = 0

    for ia, a in enumerate(sys.argv):
        if a=='-vbose':
            vbose = int(sys.argv[ia+1])

    ofp = open('pbpJson.csv', 'w')
    ofp.write('game_id,seas,dwn,ytg,yfog,type,yds\n')
    ig = 0
#    for ifile in fs[0:10]:
    for ifile in fs[:]:
        ig += 1
        fname = ifile.split('/')[-1]
        seas = int(fname[0:4])
        data = parseJson(ifile, vbose=vbose)
        for d in data:
            print ig, seas, d 
            ofp.write('%d,%d,' % (ig, seas))
            for v in d[0:-1]:
                ofp.write('%s,' % str(v))
            v = d[-1]
            ofp.write('%s\n' % str(v))
    ofp.close()
