from django.contrib.gis.db import models

class KdeLookup(models.Model):
    uid = models.AutoField(primary_key=True)
    surname = models.TextField(blank=True, null=True)
    freq1851 = models.IntegerField(blank=True, null=True)
    freq1861 = models.IntegerField(blank=True, null=True)
    freq1871 = models.IntegerField(blank=True, null=True)
    freq1881 = models.IntegerField(blank=True, null=True)
    freq1891 = models.IntegerField(blank=True, null=True)
    freq1901 = models.IntegerField(blank=True, null=True)
    freq1911 = models.IntegerField(blank=True, null=True)
    freq1997 = models.IntegerField(blank=True, null=True)
    freq1998 = models.IntegerField(blank=True, null=True)
    freq1999 = models.IntegerField(blank=True, null=True)
    freq2000 = models.IntegerField(blank=True, null=True)
    freq2001 = models.IntegerField(blank=True, null=True)
    freq2002 = models.IntegerField(blank=True, null=True)
    freq2003 = models.IntegerField(blank=True, null=True)
    freq2004 = models.IntegerField(blank=True, null=True)
    freq2005 = models.IntegerField(blank=True, null=True)
    freq2006 = models.IntegerField(blank=True, null=True)
    freq2007 = models.IntegerField(blank=True, null=True)
    freq2008 = models.IntegerField(blank=True, null=True)
    freq2009 = models.IntegerField(blank=True, null=True)
    freq2010 = models.IntegerField(blank=True, null=True)
    freq2011 = models.IntegerField(blank=True, null=True)
    freq2012 = models.IntegerField(blank=True, null=True)
    freq2013 = models.IntegerField(blank=True, null=True)
    freq2014 = models.IntegerField(blank=True, null=True)
    freq2015 = models.IntegerField(blank=True, null=True)
    freq2016 = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'kde_lookup'

class KdeGridxy(models.Model):
    gid = models.IntegerField(primary_key=True)
    x = models.DecimalField(max_digits=65535, decimal_places=65535, blank=True, null=True)
    y = models.DecimalField(max_digits=65535, decimal_places=65535, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'kde_gridxy'

class KdevClus1851(models.Model):
    uid = models.AutoField(primary_key=True)
    kde = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus1851'

class KdevClus1861(models.Model):
    uid = models.AutoField(primary_key=True)
    kde = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus1861'

class KdevClus1871(models.Model):
    uid = models.AutoField(primary_key=True)
    kde = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus1871'

class KdevClus1881(models.Model):
    uid = models.AutoField(primary_key=True)
    kde = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus1881'

class KdevClus1891(models.Model):
    uid = models.AutoField(primary_key=True)
    kde = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus1891'

class KdevClus1901(models.Model):
    uid = models.AutoField(primary_key=True)
    kde = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus1901'

class KdevClus1911(models.Model):
    uid = models.AutoField(primary_key=True)
    kde = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus1911'

class KdevClus1997(models.Model):
    uid = models.AutoField(primary_key=True)
    kde = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus1997'

class KdevClus1998(models.Model):
    uid = models.AutoField(primary_key=True)
    kde = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus1998'

class KdevClus1999(models.Model):
    uid = models.AutoField(primary_key=True)
    kde = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus1999'

class KdevClus2000(models.Model):
    uid = models.AutoField(primary_key=True)
    kde = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus2000'

class KdevClus2001(models.Model):
    uid = models.AutoField(primary_key=True)
    kde = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus2001'

class KdevClus2002(models.Model):
    uid = models.AutoField(primary_key=True)
    kde = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus2002'

class KdevClus2003(models.Model):
    uid = models.AutoField(primary_key=True)
    kde = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus2003'

class KdevClus2004(models.Model):
    uid = models.AutoField(primary_key=True)
    kde = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus2004'

class KdevClus2005(models.Model):
    uid = models.AutoField(primary_key=True)
    kde = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus2005'

class KdevClus2006(models.Model):
    uid = models.AutoField(primary_key=True)
    kde = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus2006'

class KdevClus2007(models.Model):
    uid = models.AutoField(primary_key=True)
    kde = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus2007'

class KdevClus2008(models.Model):
    uid = models.AutoField(primary_key=True)
    kde = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus2008'

class KdevClus2009(models.Model):
    uid = models.AutoField(primary_key=True)
    kde = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus2009'

class KdevClus2010(models.Model):
    uid = models.AutoField(primary_key=True)
    kde = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus2010'

class KdevClus2011(models.Model):
    uid = models.AutoField(primary_key=True)
    kde = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus2011'

class KdevClus2012(models.Model):
    uid = models.AutoField(primary_key=True)
    kde = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus2012'

class KdevClus2013(models.Model):
    uid = models.AutoField(primary_key=True)
    kde = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus2013'

class KdevClus2014(models.Model):
    uid = models.AutoField(primary_key=True)
    kde = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus2014'

class KdevClus2015(models.Model):
    uid = models.AutoField(primary_key=True)
    kde = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus2015'

class KdevClus2016(models.Model):
    uid = models.AutoField(primary_key=True)
    kde = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'kdev_clus2016'

class LsoaTopnames(models.Model):
    lsoa = models.TextField(primary_key=True)
    long = models.DecimalField(max_digits=65535, decimal_places=65535, blank=True, null=True)
    lat = models.DecimalField(max_digits=65535, decimal_places=65535, blank=True, null=True)
    topnames = models.TextField(blank=True, null=True)
    unique_n = models.IntegerField(blank=True, null=True)
    total_n = models.IntegerField(blank=True, null=True)
    shape = models.PolygonField(srid=27700)
    diversity_a = models.DecimalField(max_digits=65535, decimal_places=65535, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'lsoa_topnames'

class GeoTopnames(models.Model):
    agg_geo = models.TextField(primary_key=True)
    topnames = models.TextField(blank=True, null=True)
    unique_n = models.IntegerField(blank=True, null=True)
    total_n = models.IntegerField(blank=True, null=True)
    diversity_a = models.DecimalField(max_digits=65535, decimal_places=65535, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'geo_topnames'
