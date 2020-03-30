#django
from .models import *

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

    # #statistics -- ahah
    # oah = names_ahah.objects.filter(surname=name_search).values('surname','ahah_dec_rev')
    # oah_mod = oah_stats(oah)
    #
    # #statistics -- imd
    # imd = names_imd.objects.filter(surname=name_search).values('surname','imd_dec')
    # imd_mod = imd_stats(imd)
    #
    # #statistics -- bbs
    # bbs = names_bbs.objects.filter(surname=name_search).values('surname','bbs')
    # bbs_mod = bband_stats(bbs)
    #
    # #statistics -- iuc
    # iuc = names_iuc.objects.filter(surname=name_search).values('surname','iuccd','iucnm')
    # iuc_mod = iuc_stats(iuc)

    #return
    return([fore_female_hist,fore_male_hist,fore_female_cont,fore_male_cont,par_top,msoa_top,oac_mod])#,oah_mod,imd_mod,bbs_mod,iuc_mod])

#forenames
def forenames_stats(forenames):
    if not forenames:
        fore_female = ['No forenames found']
        fore_male = ['No forenames found']
    else:
        fore_female = [f['forename'] for f in forenames if f['sex'] == 'F']
        fore_male = [f['forename'] for f in forenames if f['sex'] == 'M']
    return(fore_female,fore_male)

#parish frequencies
def parish_stats(parishes):
    if not parishes:
        par_top = [['No data','No data']]
    else:
        par_top = list(map(list, set(map(lambda i: tuple(i), [[p['regcnty'].title(),p['parish']] for p in parishes]))))
    return(par_top[:5])

#msoa frequencies
def msoa_stats(msoas):
    if not msoas:
        msoa_top = [['No data','No data']]
    else:
        msoa_top = [[lookup_loc_cont.objects.filter(msoa11cd=o['msoa11cd']).values('ladnm')[0]['ladnm'], \
                    lookup_loc_cont.objects.filter(msoa11cd=o['msoa11cd']).values('msoa11nm')[0]['msoa11nm']] for o in msoas]
    return(msoa_top[:5])

#output area classification
def oac_stats(oac):
    if not oac:
        oac_sn = ['No data','No data','99']
    else:
        oac_sn = [lookup_oac.objects.filter(groupcd=oac[0]['oaccd']).values('supergroupnm')[0]['supergroupnm'],oac[0]['oacnm'],oac[0]['oaccd']]
    return(oac_sn)

#access to health and hazards
def oah_stats(oah):
    if not oah:
        oah_dc = 99
    else:
        oah_dc = oah[0]['ahah_dec_rev']
    return(oah_dc)

#index of multiple deprivation
def imd_stats(imd):
    if not imd:
        imd_dc = 99
    else:
        imd_dc = imd[0]['imd_dec']
    return(imd_dc)

#broadband speed
def bband_stats(bband):
    if not bband:
        bband_sc = 99
    else:
        bband_sc = bband[0]['bbandcd']
    return(bband_sc)

#internet user classification
def iuc_stats(iuc):
    if not iuc:
        iuc_sc = [99,'No classification found']
    else:
        iuc_sc = [iuc[0]['iuccd'],iuc[0]['iucnm']]
    return(iuc_sc)
