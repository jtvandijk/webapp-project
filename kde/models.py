#django
from django.contrib.gis.db import models

#kde
class kdelookup(models.Model):
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

class kdegridxy(models.Model):
    gid = models.IntegerField(primary_key=True)
    x = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    y = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bool = models.IntegerField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kde_gridxy'

class kdeclus1851(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus1851'

class kdeclus1861(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus1861'

class kdeclus1881(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus1881'

class kdeclus1891(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus1891'

class kdeclus1901(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus1901'

class kdeclus1911(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus1911'

class kdeclus1997(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus1997'

class kdeclus1998(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus1998'

class kdeclus1999(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus1999'

class kdeclus2000(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus2000'

class kdeclus2001(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus2001'

class kdeclus2002(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus2002'

class kdeclus2003(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus2003'

class kdeclus2004(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus2004'

class kdeclus2005(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus2005'

class kdeclus2006(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus2006'

class kdeclus2007(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus2007'

class kdeclus2008(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus2008'

class kdeclus2009(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus2009'

class kdeclus2010(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus2010'

class kdeclus2011(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus2011'

class kdeclus2012(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus2012'

class kdeclus2013(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus2013'

class kdeclus2014(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus2014'

class kdeclus2015(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus2015'

class kdeclus2016(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    pop = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    bw = models.DecimalField(max_digits=65535,decimal_places=65535,blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus2016'

class names_rendered(models.Model):
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

#stats
class names_forenames_hist(models.Model):
    surname = models.TextField(primary_key=True)
    forename = models.TextField(blank=True,null=True)
    sex = models.TextField(blank=True,null=True)
    freq = models.IntegerField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'names_forenames_hist'

class names_forenames_cont(models.Model):
    surname = models.TextField(primary_key=True)
    forename = models.TextField(blank=True,null=True)
    sex = models.TextField(blank=True,null=True)
    freq = models.IntegerField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'names_forenames_cont'

class names_freq_parish(models.Model):
    surname = models.TextField(primary_key=True)
    conparid = models.FloatField(blank=True,null=True)
    parish = models.TextField(blank=True,null=True)
    parish_freq = models.IntegerField(blank=True,null=True)
    year = models.IntegerField(blank=True,null=True)
    regcnty = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'names_freq_parish'

class names_freq_oa(models.Model):
    surname = models.TextField(primary_key=True)
    msoa11cd = models.TextField(blank=True,null=True)
    oa_freq = models.IntegerField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'names_freq_msoa'

class names_cat_oa(models.Model):
    surname = models.TextField(primary_key=True)
    oagroupcd = models.TextField(blank=True,null=True)
    oagroupnm = models.IntegerField(blank=True,null=True)
    freq = models.IntegerField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'names_cat_oa'

class names_health_oa(models.Model):
    surname = models.TextField(primary_key=True)
    ahah_dec = models.IntegerField(blank=True,null=True)
    ahah_dec_rev = models.IntegerField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'names_health_oa'

class names_imd_oa(models.Model):
    surname = models.TextField(primary_key=True)
    imd_dec = models.IntegerField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'names_imd_oa'

class names_iuc_oa(models.Model):
    surname = models.TextField(primary_key=True)
    iuccd = models.IntegerField(blank=True,null=True)
    iucnm = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'names_iuc_oa'

class names_bband_oa(models.Model):
    surname = models.TextField(primary_key=True)
    bband = models.TextField(blank=True,null=True)
    bbandcd = models.IntegerField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'names_bband_oa'

class names_crvul_oa(models.Model):
    surname = models.TextField(primary_key=True)
    crvulcd = models.TextField(blank=True,null=True)
    crvulnm = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'names_crvul_oa'

#lookup
class lookup_parish(models.Model):
    conparid = models.FloatField(primary_key=True)
    regcnty = models.TextField(blank=True,null=True)
    parish = models.TextField(blank=True,null=True)
    country = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'lookup_parish'

class lookup_oa(models.Model):
    pcdc = models.TextField(blank=True,null=True)
    oa11 = models.TextField(blank=True,null=True)
    lsoa11cd = models.TextField(blank=True,null=True)
    msoa11cd = models.TextField(blank=True,null=True)
    ladcd = models.TextField(blank=True,null=True)
    lsoa11nm = models.TextField(blank=True,null=True)
    msoa11nm = models.TextField(blank=True,null=True)
    ladnm = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'lookup_oa'

class oa_classification(models.Model):
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
    subgroupnm = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'oa_classification'

#spatial
class conpar51(models.Model):
    conparid = models.FloatField(primary_key=True)
    geom = models.MultiPolygonField(srid=27700)
    centroid = models.PointField(srid=27700)

    class Meta:
        managed = True
        db_table = 'conpar51'

class conpar01(models.Model):
    conparid = models.FloatField(primary_key=True)
    geom = models.MultiPolygonField(srid=27700)
    centroid = models.PointField(srid=27700)

    class Meta:
        managed = True
        db_table = 'conpar01'

class census_oa(models.Model):
    oacd11 = models.TextField(primary_key=True)
    geom = models.MultiPolygonField(srid=27700)
    centroid = models.PointField(srid=27700)

    class Meta:
        managed = True
        db_table = 'census_oa'
