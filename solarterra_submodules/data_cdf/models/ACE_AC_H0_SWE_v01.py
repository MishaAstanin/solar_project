from django.db import models
from django.contrib.postgres.fields import ArrayField
import uuid
from solarterra.abstract_models import GetManager
from load_cdf.models import CDFFileStored, Float32Field

class ACE_AC_H0_SWE_v01_data(models.Model):

	
	epoch = models.BigIntegerField(blank=True, null=True)
	
	time_pb5_day_of_year = models.IntegerField(blank=True, null=True)
	
	time_pb5_elapsed_milliseconds_of_day = models.IntegerField(blank=True, null=True)
	
	time_pb5_year = models.IntegerField(blank=True, null=True)
	
	alpha_ratio = Float32Field(blank=True, null=True)
	
	np = Float32Field(blank=True, null=True)
	
	sc_pos_gse_x = Float32Field(blank=True, null=True)
	
	sc_pos_gse_y = Float32Field(blank=True, null=True)
	
	sc_pos_gse_z = Float32Field(blank=True, null=True)
	
	sc_pos_gsm_x = Float32Field(blank=True, null=True)
	
	sc_pos_gsm_y = Float32Field(blank=True, null=True)
	
	sc_pos_gsm_z = Float32Field(blank=True, null=True)
	
	tpr = Float32Field(blank=True, null=True)
	
	v_gse_vx = Float32Field(blank=True, null=True)
	
	v_gse_vy = Float32Field(blank=True, null=True)
	
	v_gse_vz = Float32Field(blank=True, null=True)
	
	v_gsm_vx = Float32Field(blank=True, null=True)
	
	v_gsm_vy = Float32Field(blank=True, null=True)
	
	v_gsm_vz = Float32Field(blank=True, null=True)
	
	v_rtn_vn = Float32Field(blank=True, null=True)
	
	v_rtn_vr = Float32Field(blank=True, null=True)
	
	v_rtn_vt = Float32Field(blank=True, null=True)
	
	vp = Float32Field(blank=True, null=True)
	
	
	cdf_file = models.ForeignKey(CDFFileStored, on_delete=models.SET_NULL, related_name="ACE_AC_H0_SWE_v01_data_data", db_index=False, blank=True, null=True)

	objects = GetManager()	
