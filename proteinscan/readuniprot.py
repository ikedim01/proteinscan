# AUTOGENERATED! DO NOT EDIT! File to edit: 01_readuniprot.ipynb (unless otherwise specified).

__all__ = ['iterDat', 'datEntryLnsWithCode', 'datEntryPrimaryAC', 'scanDat', 'allPrimaryACsInDat', 'datEntryPE',
           'datEntryName', 'datEntrySeq', 'datEntryGOLines', 'datEntryGOTermPresent', 'datEntryIsAtpBinding',
           'datEntryIsGtpBinding', 'datEntryIsMetalBinding', 'datEntryKWs', 'listIfStr', 'filterDatEntry', 'aaLetters',
           'aaLettersSet', 'parseClustersFromUniref']

# Cell

import collections
import csv
import itertools
import random
import re

from proteinscan import utils

# Cell

def iterDat(datFPath) :
    """
    Iterator yielding a list of lines for each entry in the .dat file.
    """
    with utils.openGzipOrText(datFPath) as f :
        for (isEnd,it) in itertools.groupby(f, lambda ln : ln.strip()=='//') :
            if not isEnd :
                yield(list(it))

def datEntryLnsWithCode(datEntry,code) :
    "Returns a list of the lines in a .dat file entry with the given code."
    res = []
    for ln in datEntry :
        ln = ln.strip()
        if ln.startswith(code+' ') :
            res.append(ln[len(code):].lstrip())
    return res

def datEntryPrimaryAC(datEntry) :
    "Returns the primary accession number from a .det file entry."
    acLns = datEntryLnsWithCode(datEntry,'AC')
    return acLns[0].split(';')[0]

# Cell

def scanDat(datFPath, fn, returnFull=False, **kwargs) :
    """
    Scan a function across each entry in a .dat file, accumulating the results.
    If the function returns None, the entry is ignored; otherwise the result
    is added to the returned results list. Accepts additional keyword arguments,
    which are passed on to the function to be scanned.

    If returnFull is True, also returns a list of the corresponding full entries.
    """
    res = []
    if returnFull : fullRes = []
    for datEntry in iterDat(datFPath) :
        item = fn(datEntry, **kwargs)
        if item is not None :
            res.append(item)
            if returnFull :
                fullRes.append(datEntry)
    return (res,fullRes) if returnFull else res

def allPrimaryACsInDat(datFPath) :
    "Returns a list of all primary accession numbers in a .dat file."
    return scanDat(datFPath,datEntryPrimaryAC)

def datEntryPE(datEntry) :
    "Returns the level of evidence for a protein's existence (1-5, lower is stronger)."
    peLns = datEntryLnsWithCode(datEntry,'PE')
    return int(peLns[0][0])

def datEntryName(datEntry) :
    "Returns a descriptive name from a .dat file entry."
    deLns = datEntryLnsWithCode(datEntry,'DE')
    name = deLns[0].split('=')[1].rstrip(';')
    flagSet = set()
    for deLn in deLns[1:] :
        if deLn.startswith('Flags') :
            flagSet.update(flag.rstrip(';') for flag in deLn.split()[1:])
    if len(flagSet) > 0 :
        name += ' (' + '; '.join(sorted(flagSet)) +')'
    return name

def datEntrySeq(datEntry) :
    "Returns the amino acid sequence from a .dat file entry as a single string."
    seqL = []
    for ln in reversed(datEntry) :
        ln = ln.strip()
        if ln.startswith('SQ ') :
            break
        seqL.append(ln.replace(' ',''))
    return ''.join(reversed(seqL))

# Cell

def datEntryGOLines(datEntry) :
    "Returns the lines with GO terms from the database x-ref section of a .dat file entry."
    drLns = datEntryLnsWithCode(datEntry,'DR')
    return [drLn for drLn in drLns if drLn.startswith('GO;')]

def datEntryGOTermPresent(datEntry,goTerm) :
    "Returns 'pos' or 'neg' accordingly as a .dat file entry includes the given GO term."
    if any(goTerm in goLn for goLn in datEntryGOLines(datEntry)) :
        return 'pos'
    return 'neg'

def datEntryIsAtpBinding(datEntry) :
    "Returns 'pos' or 'neg accordingly as a .dat file entry has the ATP binding GO term."
    return datEntryGOTermPresent(datEntry,'GO:0005524;')
def datEntryIsGtpBinding(datEntry) :
    "Returns 'pos' or 'neg accordingly as a .dat file entry has the GTP binding GO term."
    return datEntryGOTermPresent(datEntry,'GO:0005525;')
def datEntryIsMetalBinding(datEntry) :
    "Returns 'pos' or 'neg accordingly as a .dat file entry has the metal binding GO term."
    return datEntryGOTermPresent(datEntry,'GO:0046872;')

def datEntryKWs(datEntry) :
    "Returns a list of the keywords from the KW section of a .dat file entry."
    res = []
    for kwLn in datEntryLnsWithCode(datEntry,'KW') :
        for kw in kwLn.split(';') :
            kw = kw.strip().rstrip('.').strip().lower()
            if kw != '' :
                res.append(kw)
    return res

# Cell

aaLetters = 'ACDEFGHIKLMNPQRSTVWY'
aaLettersSet = set(aaLetters)

def listIfStr(lOrStr) :
    return [lOrStr] if isinstance(lOrStr,str) else lOrStr

def filterDatEntry(datEntry, restrictTo20AA=True,
            minLen=50, maxLen=400, maxPE=None,
            requireInSpecies='', elimKWs=[], requireKWs=[],
            requireInName='', excludeStrs=[]) :
    """
    Filters a .dat file entry for inclusion in a LM or classification data set.
    The filtering is based on the keyword arguments.

    Returns (primary_accession_num,sequence) if the entry passes the filter, else None.
    """
    seq = datEntrySeq(datEntry)
    kws = datEntryKWs(datEntry)
    elimKWs = listIfStr(elimKWs)
    requireKWs = listIfStr(requireKWs)
    excludeStrs = listIfStr(excludeStrs)
    if ((restrictTo20AA and any(c not in aaLettersSet for c in seq))
        or any(elimKW in kws for elimKW in elimKWs)
        or any(requireKW not in kws for requireKW in requireKWs)
        or (minLen is not None and len(seq)<minLen)
        or (maxLen is not None and len(seq)>maxLen)
        or (maxPE is not None and datEntryPE(datEntry)>maxPE)
        or requireInSpecies not in datEntryLnsWithCode(datEntry,'OS')[0].lower()) :
        return None
    lName = datEntryName(datEntry).lower()
    if ((requireInName not in lName)
        or any (excludeStr in lName for excludeStr in excludeStrs)) :
        return None
    return (datEntryPrimaryAC(datEntry),seq)

# Cell

def parseClustersFromUniref(unirefFPath,clusterFPath,encoding='ISO-8859-1') :
    """
    Reads a UniRef XML file and generates a file just giving the cluster info.
    Each line of the file is a space-separated list of primary accession numbers
    from UniProt, which have been grouped into a cluster in the UniRef file.
    Only keeps the entries in UniRef that have a UniProt accession number.
    """
    nEntries = nAccNos = 0
    with utils.openGzipOrText(unirefFPath,encoding) as f :
        with open(clusterFPath,'w') as outF :
            for i,ln in enumerate(f) :
                if (i%100000000)==0 :  # print every 100-millionth line
                    print(i,ln.strip())
                if '<entry' in ln :  # start a cluster
                    memCount = 0
                    expectedMemCount = None
                    entryAccNos = []
                    nEntries += 1
                elif '</entry' in ln :  # end a cluster
                    if memCount != expectedMemCount :
                        print('member count mismatch',memCount,expectedMemCount)
                    nAccNos += len(entryAccNos)
                    if len(entryAccNos) >= 1 :
                        outF.write(" ".join(entryAccNos)+'\n')
                elif '<member' in ln or '<representativeMember' in ln :  # start a sequence member
                    memAccNos = []
                elif '</member' in ln or '</representativeMember' in ln :  # end a sequence member
                    entryAccNos.extend(memAccNos)
                    memCount += 1
                elif '<property' in ln :  # parse a property line
                    m = re.search(r'<property.*type="(.*?)".*value="(.*?)"',ln)
                    if m is not None :
                        t,v = m.groups()
                        if t.lower()=='member count' :  # member count from entry element
                            expectedMemCount = int(v.strip())
                        elif t.lower()=='uniprotkb accession' : # accession number from member element
                            memAccNos.append(v.strip())
    print(nEntries,'entries',nAccNos,'accNos')