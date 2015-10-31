import os
import sys
import optparse
import ROOT
import commands
import getpass

"""
get distributions from file
"""
def getDistsFrom(directory):
    obs=None
    exp={}
    dirName=directory.GetName()
    for key in directory.GetListOfKeys():
        obj=directory.Get(key.GetName())
        if not obj.InheritsFrom('TH1') : continue
        if obj.GetName()==dirName : 
            obs=obj.Clone('data_obs')
            obs.SetDirectory(0)
        else : 
            newName=obj.GetName().split(dirName+'_')[-1]
            for token in ['+','-','*',' ','#','{','(',')','}']:
                newName=newName.replace(token,'')
            exp[newName]=obj.Clone(newName)
            exp[newName].SetDirectory(0)
            for xbin in xrange(1,exp[newName].GetXaxis().GetNbins()+1):
                binContent=exp[newName].GetBinContent(xbin)
                if binContent>0: continue
                newBinContent=ROOT.TMath.Max(ROOT.TMath.Abs(binContent),1e-3)
                exp[newName].SetBinContent(xbin,newBinContent)
                exp[newName].SetBinError(xbin,newBinContent)
    return obs,exp

"""
save distributions to file
"""
def saveToShapesFile(outDir,shapeColl,directory=''):
    fOut=ROOT.TFile.Open('%s/shapes.root'%outDir,'UPDATE')
    if len(directory)==0:
        fOut.cd()     
    else:
        outDir=fOut.mkdir(directory)
        outDir.cd()
    for key in shapeColl:shapeColl[key].Write(key,ROOT.TObject.kOverwrite)
    fOut.Close()


"""
steer the script
"""
def main():

    #configuration
    usage = 'usage: %prog [options]'
    parser = optparse.OptionParser(usage)
    parser.add_option('-i', '--input',          dest='input',       help='input plotter',       default=None,          type='string')
    parser.add_option('-d', '--dist',           dest='dist',        help='distribution',        default='njetsnbtags', type='string')
    parser.add_option('-s', '--signal',         dest='signal',      help='signal (csv)',        default='tbart',       type='string')
    parser.add_option('-o', '--output',         dest='output',      help='output directory',    default='datacards',   type='string')
    (opt, args) = parser.parse_args()

    signalList=opt.signal.split(',')

    #prepare output directory and ROOT file
    os.system('mkdir -p %s'%opt.output)
    fOut=ROOT.TFile.Open('%s/shapes.root'%opt.output,'RECREATE')
    fOut.Close()

    #get data and nominal expectations
    fIn=ROOT.TFile.Open(opt.input)
    obs,exp=getDistsFrom(directory=fIn.Get(opt.dist+'_nom'))

    #start the datacard
    datacard=open('%s/datacard.dat'%opt.output,'w')
    datacard.write('#\n')
    datacard.write('# Generated by %s with git hash %s\n' % (getpass.getuser(),
                                                            commands.getstatusoutput('git log --pretty=format:\'%h\' -n 1')[1]) )
    datacard.write('#\n')
    datacard.write('imax *\n')
    datacard.write('jmax *\n')
    datacard.write('kmax *\n')
    datacard.write('-'*50+'\n')
    datacard.write('shapes *        * shapes.root nom/$PROCESS $SYSTEMATIC/$PROCESS\n')
    datacard.write('-'*50+'\n')
    datacard.write('bin 1\n')
    datacard.write('observation %3.1f\n' % obs.Integral())
    datacard.write('-'*50+'\n')

    #expectations
    datacard.write('\t\t\t %15s'%'bin')
    for i in xrange(0,len(exp)): datacard.write('%15s'%'1')
    datacard.write('\n')
    datacard.write('\t\t\t %15s'%'process')
    for sig in signalList: datacard.write('%15s'%sig)
    for proc in exp: 
        if proc in signalList: continue
        datacard.write('%15s'%proc)
    datacard.write('\n')
    datacard.write('\t\t\t %15s'%'process')
    for i in xrange(0,len(signalList)) : datacard.write('%15s'%str(i+1-len(signalList)))
    i=0
    for proc in exp: 
        if proc in signalList: continue
        i=i+1
        datacard.write('%15s'%str(i))
    datacard.write('\n')
    datacard.write('\t\t\t %15s'%'rate')
    for sig in signalList: datacard.write('%15s'%('%3.2f'%exp[sig].Integral()))
    for proc in exp: 
        if proc in signalList: continue
        datacard.write('%15s'%('%3.2f'%exp[proc].Integral()))
    datacard.write('\n')
    datacard.write('-'*50+'\n')

    nomShapes=exp.copy()
    nomShapes['data_obs']=obs
    saveToShapesFile(opt.output,nomShapes,'nom')
    
    #weighting systematics: syst name, white list, black list
    weightSysts=[
        ('pu',      []       ,['Multijetsdata']),
        ('muEff',   []       ,['Multijetsdata']),
        ('eEff',    []       ,['Multijetsdata']),
        ('umet',    []       ,['Multijetsdata']),
        ('jes',     []       ,['Multijetsdata']),
        ('jer',     []       ,['Multijetsdata']),
        ('beff',    []       ,['Multijetsdata']),
        ('mistag',  []       ,['Multijetsdata']),
        ('qcdScale',['tbart'],['Multijetsdata'])
        ]
    for syst,whiteList,blackList in weightSysts:
        datacard.write('%32s shapeN2'%syst)        
        for sig in signalList: 
            if (len(whiteList)==0 and not sig in blackList) or sig in whiteList:
                datacard.write('%15s'%'1') 
            else:
                datacard.write('%15s'%'-')
        for proc in exp: 
            if proc in signalList: continue
            if (len(whiteList)==0 and not proc in blackList) or proc in whiteList:
                datacard.write('%15s'%'1')
            else:
                datacard.write('%15s'%'-')
        datacard.write('\n')

        for var in ['Up','Down']:
            obs,exp=getDistsFrom(directory=fIn.Get(opt.dist+'_'+syst+var))
            saveToShapesFile(opt.output,exp,syst+var)

    #reate systematics
    rateSysts=[
        ('lumi',           1.12,    'lnN',    []                ,['Multijetsdata','tbart']),
        ('Wth',            1.041,   'lnN',    ['Wl','Wc','Wb']  ,[]),
        ('DYth',           1.041,   'lnN',    ['DY']            ,[]),
#        ('MultiJetsNorm',  1.041,  'lnU',    ['Multijetsdata']     ,[]),
        ]
    for syst,val,pdf,whiteList,blackList in rateSysts:

        datacard.write('%32s %8s'%(syst,pdf))

        for sig in signalList: 
            if (len(whiteList)==0 and not sig in blackList) or sig in whiteList:
                datacard.write('%15s'%str(val)) 
            else:
                datacard.write('%15s'%'-')
        for proc in exp: 
            if proc in signalList: continue
            if (len(whiteList)==0 and not proc in blackList) or proc in whiteList:
                datacard.write('%15s'%str(val))
            else:
                datacard.write('%15s'%'-')

        datacard.write('\n')

    
    datacard.close()




"""                                                                                                                                                                                                               
for execution from another script                                                                                                                                                                           
"""
if __name__ == "__main__":
    sys.exit(main())
