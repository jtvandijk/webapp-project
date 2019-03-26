#models
from django.contrib.gis.db import models

class KdeLookup(models.Model):
    uid = models.AutoField(primary_key=True)
    surname = models.TextField(blank=True,null=True)
    freq1851 = models.IntegerField(blank=True,null=True)
    freq1861 = models.IntegerField(blank=True,null=True)
    freq1881 = models.IntegerField(blank=True,null=True)
    freq1891 = models.IntegerField(blank=True,null=True)
    freq1901 = models.IntegerField(blank=True,null=True)
    freq1911 = models.IntegerField(blank=True,null=True)
    freq1997 = models.IntegerField(blank=True,null=True)
    freq1998 = models.IntegerField(blank=True,null=True)
    freq1999 = models.IntegerField(blank=True,null=True)
    freq2000 = models.IntegerField(blank=True,null=True)
    freq2001 = models.IntegerField(blank=True,null=True)
    freq2002 = models.IntegerField(blank=True,null=True)
    freq2003 = models.IntegerField(blank=True,null=True)
    freq2004 = models.IntegerField(blank=True,null=True)
    freq2005 = models.IntegerField(blank=True,null=True)
    freq2006 = models.IntegerField(blank=True,null=True)
    freq2007 = models.IntegerField(blank=True,null=True)
    freq2008 = models.IntegerField(blank=True,null=True)
    freq2009 = models.IntegerField(blank=True,null=True)
    freq2010 = models.IntegerField(blank=True,null=True)
    freq2011 = models.IntegerField(blank=True,null=True)
    freq2012 = models.IntegerField(blank=True,null=True)
    freq2013 = models.IntegerField(blank=True,null=True)
    freq2014 = models.IntegerField(blank=True,null=True)
    freq2015 = models.IntegerField(blank=True,null=True)
    freq2016 = models.IntegerField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kde_lookup'

class KdeGridxy(models.Model):
    gid = models.IntegerField(primary_key=True)
    x = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    y = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bool = models.IntegerField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kde_gridxy'

class KdevClus1851(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdef_clus1851'

class KdevClus1861(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdef_clus1861'

class KdevClus1881(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdef_clus1881'

class KdevClus1891(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdef_clus1891'

class KdevClus1901(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdef_clus1901'

class KdevClus1911(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdef_clus1911'

class KdevClus1997(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdef_clus1997'

class KdevClus1998(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdef_clus1998'

class KdevClus1999(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdef_clus1999'

class KdevClus2000(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdef_clus2000'

class KdevClus2001(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdef_clus2001'

class KdevClus2002(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdef_clus2002'

class KdevClus2003(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdef_clus2003'

class KdevClus2004(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdef_clus2004'

class KdevClus2005(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdef_clus2005'

class KdevClus2006(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdef_clus2006'

class KdevClus2007(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdef_clus2007'

class KdevClus2008(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdef_clus2008'

class KdevClus2009(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdef_clus2009'

class KdevClus2010(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdef_clus2010'

class KdevClus2011(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdef_clus2011'

class KdevClus2012(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdef_clus2012'

class KdevClus2013(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdef_clus2013'

class KdevClus2014(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdef_clus2014'

class KdevClus2015(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdef_clus2015'

class KdevClus2016(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdef_clus2016'

class ForeNames(models.Model):
    surname = models.TextField(primary_key=True)
    male = models.TextField(blank=True,null=True)
    female = models.TextField(blank=True,null=True)
    male_freq = models.IntegerField(blank=True,null=True)
    female_freq = models.IntegerField(blank=True,null=True)
    year = models.IntegerField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'names_freq_forename'

class ParishLookup(models.Model):
    conparid = models.FloatField(primary_key=True)
    regcnty = models.TextField(blank=True,null=True)
    parish = models.TextField(blank=True,null=True)
    country = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'conpar_lookup'

class ParishNames(models.Model):
    surname = models.TextField(primary_key=True)
    conparid = models.FloatField(blank=True,null=True)
    parish = models.TextField(blank=True,null=True)
    parish_freq = models.IntegerField(blank=True,null=True)
    year = models.IntegerField(blank=True,null=True)
    regcnty = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'names_freq_parish'

class OA_Lookup(models.Model):
    pcdc = models.TextField(blank=True,null=True)
    oa11 = models.TextField(blank=True,null=True)
    lsoacd11 = models.TextField(blank=True,null=True)
    msoacd11 = models.TextField(blank=True,null=True)
    ladcd = models.TextField(blank=True,null=True)
    lsoa11nm = models.TextField(blank=True,null=True)
    msoa11nm = models.TextField(blank=True,null=True)
    ladnm = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'oa_lookup'

class OA_Names(models.Model):
    surname = models.TextField(primary_key=True)
    oa = models.TextField(blank=True,null=True)
    oa_freq = models.IntegerField(blank=True,null=True)
    year = models.IntegerField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'names_freq_oa'

class OA_NamesCat(models.Model):
    surname = models.TextField(primary_key=True)
    oagroupcd = models.TextField(blank=True,null=True)
    oagroupnm = models.IntegerField(blank=True,null=True)
    freq = models.IntegerField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'names_cat_oa'

class CatLookup(models.Model):
    oa11 = models.TextField(primary_key=True)
    ladcd = models.TextField(blank=True,null=True)
    ladnm = models.TextField(blank=True,null=True)
    cntcd = models.TextField(blank=True,null=True)
    cntnm = models.TextField(blank=True,null=True)
    supergroupcd = models.IntegerField(blank=True,null=True)
    supergroupnm = models.TextField(blank=True,null=True)
    groupcd = models.TextField(blank=True,null=True)
    groupnm = models.TextField(blank=True,null=True)
    subgroupcd = models.TextField(blank=True,null=True)
    subgroupmn = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'oa_classification'

class RenderedNames(models.Model):
    surname = models.TextField(primary_key=True)
    source = models.TextField(blank=True,null=True)
    years = models.TextField(blank=True,null=True)
    hr_freq = models.TextField(blank=True,null=True)
    cr_freq = models.TextField(blank=True,null=True)
    contours = models.TextField(blank=True,null=True)
    count = models.IntegerField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'names_rendered'
