#django
from .models import *
import pandas as pd

#combine statistics
def surname_statistics(name_search):

    #statistics -- forename
    forenames_hist = names_fns_hist.objects.filter(surname=name_search).values('forename','sex')
    forenames_cont = names_fns_cont.objects.filter(surname=name_search).values('forename','sex')
    fore_female_hist, fore_male_hist = forenames_stats(forenames_hist)
    fore_female_cont, fore_male_cont = forenames_stats(forenames_cont)
    
    #statistics -- parish
    parishes = names_loc_hist.objects.filter(surname=name_search).values('regcnty','parish')
    par_top = parish_stats(parishes)

    #statistics -- msoa
    msoas = names_loc_cont.objects.filter(surname=name_search).values('msoa11cd')
    msoa_top = msoa_stats(msoas)

    #statistics -- oac
    oac = names_oac.objects.filter(surname=name_search,type='mode').values('oaccd','oacnm')
    oac_mod = oac_stats(oac)

    #statistics -- loac
    loac = names_loac.objects.filter(surname=name_search,type='mode').values('loaccd','loacnm')
    loac_mod = loac_stats(loac)
  
    #statistics -- iuc
    iuc = names_iuc.objects.filter(surname=name_search).values('iuccd','iucnm')
    iuc_mod = iuc_stats(iuc)
    

    # #statistics -- ahah
    ahah = names_ahah.objects.filter(surname=name_search,type='mode').values('ahahdec')
    ahah_mod = ahah_stats(ahah)
    

    #statistics -- imd
    imd = names_imd.objects.filter(surname=name_search,type='mode').values('imddec')
    imd_mod = imd_stats(imd)

    #statistics -- imd // avg, sd
    imd_std = names_imd_std.objects.filter(surname=name_search).values('avg','sd')
    imd_mod_std = imd_std_stats(imd_std)

    #statistics -- bbs
    bbs = names_bbs.objects.filter(surname=name_search).values('bbsdec','bbs')
    bbs_mod = bband_stats(bbs)

    #statistics -- eee
    eee = names_eee.objects.filter(surname=name_search).values('code','eee')
    eee_mod = eee_stats(eee)

    #return
    return([fore_female_hist,fore_male_hist,fore_female_cont,fore_male_cont,par_top,msoa_top,oac_mod,loac_mod,iuc_mod,ahah_mod,imd_mod,bbs_mod,eee_mod,imd_mod_std])

#forenames (freqs)
def forenames_stats(forenames):
    if not forenames:
        fore_female = ['No forenames found']
        fore_male = ['No forenames found']
    else:
        fore_female = [f['forename'] for f in forenames if f['sex'] == 'F']
        fore_male = [f['forename'] for f in forenames if f['sex'] == 'M']
    return(fore_female,fore_male)

#parish frequencies (freqs)
def parish_stats(parishes):
    if not parishes:
        par_top = [['No data','No data']]
    else:
        par_top = list(map(list, set(map(lambda i: tuple(i), [[p['regcnty'].title(),p['parish']] for p in parishes]))))
    return(par_top[:5])

#msoa frequencies (freqs)
def msoa_stats(msoas):
    if not msoas:
        msoa_top = [['No data','No data']]
    else:
        msoa_top = [[lookup_loc_cont.objects.filter(msoa11cd=o['msoa11cd']).values('ladnm')[0]['ladnm'], \
                    lookup_loc_cont.objects.filter(msoa11cd=o['msoa11cd']).values('msoa11nm')[0]['msoa11nm']] for o in msoas]
    return(msoa_top[:5])

#output area classification (mode)
def oac_stats(oac):
    if not oac:
        oac_mod = ['No data','No data','','','99']
    else:
        oac_sg = lookup_oac.objects.filter(groupcd=oac[0]['oaccd']).values('supergroupnm')[0]['supergroupnm']
        oac_sg_desc = lookup_oac_desc.objects.filter(code=oac[0]['oaccd'][0]).values('desc')[0]['desc']
        oac_sn = oac[0]['oacnm']
        oac_sn_desc = lookup_oac_desc.objects.filter(code=oac[0]['oaccd']).values('desc')[0]['desc']
        oac_mod = [oac_sg,oac_sn,oac_sg_desc,oac_sn_desc,oac[0]['oaccd']]
    return(oac_mod)

#london output area classification (mode)
def loac_stats(loac):
    if not loac:
        loac_mod = ['No data','No data','','','99']
    else:
        loac_sg = lookup_loac.objects.filter(groupcd=loac[0]['loaccd']).values('supergroupnm')[0]['supergroupnm']
        loac_sg_desc = lookup_loac_desc.objects.filter(code=loac[0]['loaccd'][0]).values('desc')[0]['desc']
        loac_sn = loac[0]['loacnm']
        loac_sn_desc = lookup_loac_desc.objects.filter(code=loac[0]['loaccd']).values('desc')[0]['desc']
        loac_mod = [loac_sg,loac_sn,loac_sg_desc,loac_sn_desc,loac[0]['loaccd']]
    return(loac_mod)

#internet user classification (mode)
def iuc_stats(iuc):
    if not iuc:
        iuc_mod = ['99','No data','']
    else:
        iuc_dsc = lookup_iuc.objects.filter(iuccd=iuc[0]['iuccd']).values('iucdesc')[0]['iucdesc']
        iuc_mod = [iuc[0]['iuccd'],iuc[0]['iucnm'],iuc_dsc,]
    return(iuc_mod)

#access to health and hazards (mode)
def ahah_stats(ahah):
    if not ahah:
        ahah_mod = ['No data']
    else:
        ahah_mod = ahah[0]['ahahdec']
    return(ahah_mod)

#index of multiple deprivation (mode)
def imd_stats(imd):
    if not imd:
        imd_mod = ['No data']
    else:
        imd_mod = imd[0]['imddec']
    return(imd_mod)

#index of multiple deprivation (avg, sd)
def imd_std_stats(imd_std):
    if not imd_std:
        imd_std = ['No data','No data']
    else:
        imd_std = [imd_std[0]['avg'],imd_std[0]['sd']]
    return(imd_std)

#broadband speed (mode)
def bband_stats(bbs):
    if not bbs:
        bbs_mod = ['99','No data']
    else:
        bbs_mod = [bbs[0]['bbsdec'],bbs[0]['bbs']]
    return(bbs_mod)

#ethnicity estimator
def eee_stats(eee):
    if not eee:
        eee_mod = ['99','No data']
    else:
        eee_mod = [eee[0]['code'],eee[0]['eee']]
    return(eee_mod)
