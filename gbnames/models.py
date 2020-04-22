#libraries
from django.contrib.gis.db import models

#kde
class names_kde(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.TextField(blank=True,null=True)
    freq = models.IntegerField(blank=True,null=True)
    bw = models.IntegerField(blank=True,null=True)
    kde = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'names_kde'

class names_all(models.Model):
    surname = models.TextField(primary_key=True)
    period = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'names_all'

#statistics
class names_fns_hist(models.Model):
    surname = models.TextField(primary_key=True)
    forename = models.TextField(blank=True,null=True)
    sex = models.TextField(blank=True,null=True)
    freq = models.IntegerField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'names_fns_hist'

class names_fns_cont(models.Model):
    surname = models.TextField(primary_key=True)
    forename = models.TextField(blank=True,null=True)
    sex = models.TextField(blank=True,null=True)
    freq = models.IntegerField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'names_fns_cont'

class names_loc_hist(models.Model):
    surname = models.TextField(primary_key=True)
    regcnty = models.TextField(blank=True,null=True)
    conparid = models.FloatField(blank=True,null=True)
    parish = models.TextField(blank=True,null=True)
    freq = models.IntegerField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'names_loc_hist'

class names_loc_cont(models.Model):
    surname = models.TextField(primary_key=True)
    msoa11cd = models.TextField(blank=True,null=True)
    oa_freq = models.IntegerField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'names_loc_cont'

class names_oac(models.Model):
    surname = models.TextField(primary_key=True)
    oaccd = models.TextField(blank=True,null=True)
    oacnm = models.IntegerField(blank=True,null=True)
    score = models.FloatField(blank=True,null=True)
    type = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'names_oac'

class names_imd(models.Model):
    surname = models.TextField(primary_key=True)
    imddec = models.IntegerField(blank=True,null=True)
    score = models.FloatField(blank=True,null=True)
    type = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'names_imd'

class names_ahah(models.Model):
    surname = models.TextField(primary_key=True)
    ahahdec = models.IntegerField(blank=True,null=True)
    score = models.FloatField(blank=True,null=True)
    type = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'names_ahah'

class names_iuc(models.Model):
    surname = models.TextField(primary_key=True)
    iuccd = models.IntegerField(blank=True,null=True)
    iucnm = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'names_iuc'

class names_bbs(models.Model):
    surname = models.TextField(primary_key=True)
    bbs = models.TextField(blank=True,null=True)
    bbsdec = models.IntegerField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'names_bbs'

#lookup tables
class lookup_loc_hist(models.Model):
    conparid = models.FloatField(primary_key=True)
    regcnty = models.TextField(blank=True,null=True)
    parish = models.TextField(blank=True,null=True)
    country = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'lookup_loc_hist'

class lookup_loc_cont(models.Model):
    pcdc = models.TextField(blank=True,null=True)
    oa11cd = models.TextField(blank=True,null=True)
    lsoa11cd = models.TextField(blank=True,null=True)
    msoa11cd = models.TextField(blank=True,null=True)
    ladcd = models.TextField(blank=True,null=True)
    lsoa11nm = models.TextField(blank=True,null=True)
    msoa11nm = models.TextField(blank=True,null=True)
    ladnm = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'lookup_loc_cont'

class lookup_iuc(models.Model):
    iuccd = models.TextField(primary_key=True)
    iucdesc = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'lookup_iuc'

class lookup_oac(models.Model):
    oa11cd = models.TextField(primary_key=True)
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
        db_table = 'lookup_oac'

class lookup_oac_desc(models.Model):
    type = models.TextField(blank=True,null=True)
    code = models.TextField(primary_key=True)
    colour = models.TextField(blank=True,null=True)
    names = models.TextField(blank=True,null=True)
    order1 = models.TextField(blank=True,null=True)
    order2 = models.TextField(blank=True,null=True)
    desc = models.TextField(blank=True,null=True)

    class Meta:
        managed = True
        db_table = 'lookup_oac_desc'

class spatial_conpar51(models.Model):
    conparid = models.FloatField(primary_key=True)
    geom = models.MultiPolygonField(srid=27700)
    centroid = models.PointField(srid=27700)

    class Meta:
        managed = True
        db_table = 'spatial_conpar51'

class spatial_conpar01(models.Model):
    conparid = models.FloatField(primary_key=True)
    geom = models.MultiPolygonField(srid=27700)
    centroid = models.PointField(srid=27700)

    class Meta:
        managed = True
        db_table = 'spatial_conpar01'

class spatial_msoa(models.Model):
    msoa11cd = models.TextField(primary_key=True)
    msoa11nm = models.TextField(blank=True,null=True)
    geom = models.MultiPolygonField(srid=27700)
    centroid = models.PointField(srid=27700)

    class Meta:
        managed = True
        db_table = 'spatial_msoa'
