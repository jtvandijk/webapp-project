#libraries
from django.contrib.gis.db import models

#kde
class names_kde(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.TextField(blank=True,null=True)
    freq = models.IntegerField(blank=True,null=True)

    class Meta:
        managed = False
        db_table = 'names_kde'

class names_all(models.Model):
    surname = models.TextField(primary_key=True)

    class Meta:
        managed = False
        db_table = 'names_all'

class names_frq(models.Model):
    surname = models.TextField(primary_key=True)
    year = models.IntegerField(blank=True,null=True)
    freq = models.IntegerField(blank=True,null=True)

    class Meta:
        managed = False
        db_table = 'names_frq'

#statistics
class names_fns_hist(models.Model):
    surname = models.TextField(primary_key=True)
    forename = models.TextField(blank=True,null=True)
    sex = models.TextField(blank=True,null=True)

    class Meta:
        managed = False
        db_table = 'names_fns_hist'

class names_fns_cont(models.Model):
    surname = models.TextField(primary_key=True)
    forename = models.TextField(blank=True,null=True)
    sex = models.TextField(blank=True,null=True)

    class Meta:
        managed = False
        db_table = 'names_fns_cont'

class names_loc_hist(models.Model):
    surname = models.TextField(primary_key=True)
    regcnty = models.TextField(blank=True,null=True)
    parish = models.TextField(blank=True,null=True)

    class Meta:
        managed = False
        db_table = 'names_loc_hist'

class names_loc_cont(models.Model):
    surname = models.TextField(primary_key=True)
    msoa11cd = models.TextField(blank=True,null=True)

    class Meta:
        managed = False
        db_table = 'names_loc_cont'

class names_oac(models.Model):
    surname = models.TextField(primary_key=True)
    oaccd = models.TextField(blank=True,null=True)
    oacnm = models.TextField(blank=True,null=True)
    type = models.TextField(blank=True,null=True)

    class Meta:
        managed = False
        db_table = 'names_oac'

class names_loac(models.Model):
    surname = models.TextField(primary_key=True)
    loaccd = models.TextField(blank=True,null=True)
    loacnm = models.TextField(blank=True,null=True)
    type = models.TextField(blank=True,null=True)

    class Meta:
        managed = False
        db_table = 'names_loac'

class names_imd(models.Model):
    surname = models.TextField(primary_key=True)
    imddec = models.IntegerField(blank=True,null=True)
    type = models.TextField(blank=True,null=True)

    class Meta:
        managed = False
        db_table = 'names_imd'

class names_ahah(models.Model):
    surname = models.TextField(primary_key=True)
    ahahdec = models.IntegerField(blank=True,null=True)
    type = models.TextField(blank=True,null=True)

    class Meta:
        managed = False
        db_table = 'names_ahah'

class names_iuc(models.Model):
    surname = models.TextField(primary_key=True)
    iuccd = models.IntegerField(blank=True,null=True)
    iucnm = models.TextField(blank=True,null=True)

    class Meta:
        managed = False
        db_table = 'names_iuc'

class names_bbs(models.Model):
    surname = models.TextField(primary_key=True)
    bbs = models.TextField(blank=True,null=True)
    bbsdec = models.IntegerField(blank=True,null=True)

    class Meta:
        managed = False
        db_table = 'names_bbs'

class names_eee(models.Model):
    surname = models.TextField(primary_key=True)
    code = models.IntegerField(blank=True,null=True)
    eee = models.TextField(blank=True,null=True)

    class Meta:
        managed = False
        db_table = 'names_eee'

#lookup tables
class lookup_loc_cont(models.Model):
    msoa11cd = models.TextField(blank=True,null=True)
    msoa11nm = models.TextField(blank=True,null=True)
    ladnm = models.TextField(blank=True,null=True)

    class Meta:
        managed = False
        db_table = 'lookup_loc_cont'

class lookup_iuc(models.Model):
    iuccd = models.TextField(primary_key=True)
    iucdesc = models.TextField(blank=True,null=True)

    class Meta:
        managed = False
        db_table = 'lookup_iuc'

class lookup_oac(models.Model):
    supergroupnm = models.TextField(blank=True,null=True)
    groupcd = models.TextField(blank=True,null=True)

    class Meta:
        managed = False
        db_table = 'lookup_oac'

class lookup_oac_desc(models.Model):
    code = models.TextField(primary_key=True)
    desc = models.TextField(blank=True,null=True)

    class Meta:
        managed = False
        db_table = 'lookup_oac_desc'

class lookup_loac(models.Model):
    supergroupnm = models.TextField(blank=True,null=True)
    groupcd = models.TextField(blank=True,null=True)

    class Meta:
        managed = False
        db_table = 'lookup_loac'

class lookup_loac_desc(models.Model):
    code = models.TextField(primary_key=True)
    desc = models.TextField(blank=True,null=True)

    class Meta:
        managed = False
        db_table = 'lookup_loac_desc'
