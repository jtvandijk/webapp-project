#django
from .models import *

#combine statistics
def all_statistics(clean_sur):

    #statistics -- forename
    forenames_hist = names_forenames_hist.objects.filter(surname=clean_sur).values('surname','forename','sex')
    forenames_cont = names_forenames_cont.objects.filter(surname=clean_sur).values('surname','forename','sex')
    fore_female_hist, fore_male_hist = forenames_stats(forenames_hist)
    fore_female_cont, fore_male_cont = forenames_stats(forenames_cont)

    #statistics -- parish
    parishes = names_freq_parish.objects.filter(surname=clean_sur).values('regcnty','parish','conparid')
    par_top = parish_stats(parishes)

    #statistics -- oa
    oas = names_freq_oa.objects.filter(surname=clean_sur).values('msoa11cd')
    oa_top = oa_stats(oas)

    #statistics -- oac
    oac = names_cat_oa.objects.filter(surname=clean_sur).values('oagroupcd','oagroupnm')
    oac_mod = oac_stats(oac)

    #statistics -- oah
    oah = names_health_oa.objects.filter(surname=clean_sur).values('surname','ahah_dec_rev')
    oah_mod = oah_stats(oah)

    #statistics -- imd
    imd = names_imd_oa.objects.filter(surname=clean_sur).values('surname','imd_dec')
    imd_mod = imd_stats(imd)

    #statistics -- bband
    bband = names_bband_oa.objects.filter(surname=clean_sur).values('surname','bbandcd')
    bband_mod = bband_stats(bband)

    #statistics -- iuc
    iuc = names_iuc_oa.objects.filter(surname=clean_sur).values('surname','iuccd','iucnm')
    iuc_mod = iuc_stats(iuc)

    #statistics -- crvul
    crvul = names_crvul_oa.objects.filter(surname=clean_sur).values('surname','crvulcd','crvulnm')
    crvul_mod = crvul_stats(crvul)

    #return
    return(fore_female_hist,fore_male_hist,fore_female_cont,fore_male_cont,par_top,oa_top,oac_mod,oah_mod,imd_mod,bband_mod,iuc_mod,crvul_mod)

#forenames
def forenames_stats(forenames):
    if not forenames:
        fore_female = ['No forenames found']
        fore_male = ['No forenames found']
    else:
        fore_female = []
        fore_male = []
        for f in forenames:
            if(f['sex'] == 'F'):
                fore_female.append(f['forename'])
            else:
                fore_male.append(f['forename'])
    return(fore_female,fore_male)

#parish freq
def parish_stats(parishes):
    if not parishes:
        par_top = [['99','No parishes found']]
    else:
        par_top = []
        for p in parishes:
            regcnty = p['regcnty'].title()
            parid = str(int(p['conparid']))
            parish = p['parish']
            parjoin = []
            if parish == '-':
                parish = 'London parishes'
                parjoin.append(parid)
                parjoin.append(regcnty + ': ' + parish)
            else:
                parjoin.append(parid)
                parjoin.append(regcnty + ': ' + parish)
            par_top.append(parjoin)
    return(par_top)

#oa freq
def oa_stats(oas):
    if not oas:
        msoa_top = [['99','No MSOA\'s found']]
    else:
        msoa_top = []
        for o in oas:
            msoajoin = []
            msoaid = o['msoa11cd']
            ladnm = lookup_oa.objects.filter(msoa11cd=o['msoa11cd']).values('ladnm','msoa11nm')[0]
            msoanm = ladnm['ladnm'] + ': ' + ladnm['msoa11nm']
            msoajoin.append(msoaid)
            msoajoin.append(msoanm)
            msoa_top.append(msoajoin)
    return(msoa_top)

#oa classification
def oac_stats(oac):
    if not oac:
        oac_sn = ['No classification found']
        oac_gn = ['No classification found']
        oac_sg = '99'
    else:
        oac_gn = oac[0]['oagroupnm']
        oac_sg = oac[0]['oagroupcd']
        oac_sn = oa_classification.objects.filter(groupcd=oac_sg).values('supergroupnm')[0]['supergroupnm']
    return([oac_sn,oac_gn,oac_sg])

#oa health
def oah_stats(oah):
    if not oah:
        oah_dc = 99
    else:
        oah_dc = oah[0]['ahah_dec_rev']
    return(oah_dc)

#oa imd
def imd_stats(imd):
    if not imd:
        imd_dc = 99
    else:
        imd_dc = imd[0]['imd_dec']
    return(imd_dc)

#oa broadband
def bband_stats(bband):
    if not bband:
        bband_sc = 99
    else:
        bband_sc = bband[0]['bbandcd']
    return(bband_sc)

#oa internet users
def iuc_stats(iuc):
    if not iuc:
        iuc_sc = [99,'No classification found']
    else:
        iuc_sc = [iuc[0]['iuccd'],iuc[0]['iucnm']]
    return(iuc_sc)

#oa consumer vulnerability
def crvul_stats(crvul):
    if not crvul:
        crvul_sc = [99,'No classification found']
    else:
        crvul_sc = [crvul[0]['crvulcd'],crvul[0]['crvulnm']]
    return(crvul_sc)
