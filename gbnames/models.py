#libraries
from django.contrib.gis.db import models

#models
class names_kde(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.TextField(blank=True,null=True)
    freq = models.IntegerField(blank=True,null=True)
    bw = models.IntegerField(blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'names_kde'

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

class census_msoa(models.Model):
    msoa11cd = models.TextField(primary_key=True)
    msoa11nm = models.TextField(blank=True,null=True)
    geom = models.MultiPolygonField(srid=27700)
    centroid = models.PointField(srid=27700)

    class Meta:
        managed = True
        db_table = 'census_msoa'
