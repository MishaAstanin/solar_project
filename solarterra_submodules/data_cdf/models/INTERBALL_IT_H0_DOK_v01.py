from django.db import models
from django.contrib.postgres.fields import ArrayField
import uuid
from solarterra.abstract_models import GetManager
from load_cdf.models import CDFFileStored, Float32Field

class INTERBALL_IT_H0_DOK_v01_data(models.Model):

	
	dtime_1 = Float32Field(blank=True, null=True)
	
	dtime_2 = Float32Field(blank=True, null=True)
	
	dtime_3 = Float32Field(blank=True, null=True)
	
	dtime_4 = Float32Field(blank=True, null=True)
	
	epoch_1 = models.BigIntegerField(blank=True, null=True)
	
	epoch_2 = models.BigIntegerField(blank=True, null=True)
	
	epoch_3 = models.BigIntegerField(blank=True, null=True)
	
	epoch_4 = models.BigIntegerField(blank=True, null=True)
	
	format_time = ArrayField(models.TextField(null=True), size=3, blank=True, null=True)
	
	label_time = ArrayField(models.TextField(null=True), size=3, blank=True, null=True)
	
	time_pb5_1 = ArrayField(models.IntegerField(null=True), size=3, blank=True, null=True)
	
	time_pb5_2 = ArrayField(models.IntegerField(null=True), size=3, blank=True, null=True)
	
	time_pb5_3 = ArrayField(models.IntegerField(null=True), size=3, blank=True, null=True)
	
	time_pb5_4 = ArrayField(models.IntegerField(null=True), size=3, blank=True, null=True)
	
	unit_time = ArrayField(models.TextField(null=True), size=3, blank=True, null=True)
	
	a_theta_2 = Float32Field(blank=True, null=True)
	
	a_theta_4 = Float32Field(blank=True, null=True)
	
	ener_e_1 = ArrayField(Float32Field(null=True), size=55, blank=True, null=True)
	
	ener_e_2 = ArrayField(Float32Field(null=True), size=55, blank=True, null=True)
	
	ener_e_3 = ArrayField(Float32Field(null=True), size=56, blank=True, null=True)
	
	ener_e_4 = ArrayField(Float32Field(null=True), size=56, blank=True, null=True)
	
	fmode_1 = models.PositiveIntegerField(blank=True, null=True)
	
	fmode_2 = models.PositiveIntegerField(blank=True, null=True)
	
	fmode_3 = models.PositiveIntegerField(blank=True, null=True)
	
	fmode_4 = models.PositiveIntegerField(blank=True, null=True)
	
	gap_flag_1 = models.IntegerField(blank=True, null=True)
	
	gap_flag_2 = models.IntegerField(blank=True, null=True)
	
	gap_flag_3 = models.IntegerField(blank=True, null=True)
	
	gap_flag_4 = models.IntegerField(blank=True, null=True)
	
	label_e_1 = ArrayField(models.TextField(null=True), size=55, blank=True, null=True)
	
	label_e_2 = ArrayField(models.TextField(null=True), size=55, blank=True, null=True)
	
	label_e_3 = ArrayField(models.TextField(null=True), size=56, blank=True, null=True)
	
	label_e_4 = ArrayField(models.TextField(null=True), size=56, blank=True, null=True)
	
	se_1 = ArrayField(Float32Field(null=True), size=55, blank=True, null=True)
	
	se_2 = ArrayField(Float32Field(null=True), size=55, blank=True, null=True)
	
	si_3 = ArrayField(Float32Field(null=True), size=56, blank=True, null=True)
	
	si_4 = ArrayField(Float32Field(null=True), size=56, blank=True, null=True)
	
	
	cdf_file = models.ForeignKey(CDFFileStored, on_delete=models.SET_NULL, related_name="INTERBALL_IT_H0_DOK_v01_data_data", db_index=False, blank=True, null=True)

	objects = GetManager()	
