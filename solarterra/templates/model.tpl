from django.db import models
from django.contrib.postgres.fields import ArrayField
import uuid
from solarterra.abstract_models import GetManager
from load_cdf.models import CDFFileStored, Float32Field

class {{ dm_instance.model_name }}(models.Model):

	{% for field in dm_instance.fields.all %}{% with datatype=field.data_type_instance%}{% if field.is_array_field %}
	{{ field.field_name }} = ArrayField({{ datatype.django_field }}(null=True), size={{ field.array_size }}, blank=True, null=True)
	{% else %}
	{{ field.field_name }} = {{ datatype.django_field }}(blank=True, null=True)
	{% endif %}{% endwith %}{% endfor %}
	
	cdf_file = models.ForeignKey(CDFFileStored, on_delete=models.SET_NULL, related_name="{{ dm_instance.model_name}}_data", db_index=False, blank=True, null=True)

	objects = GetManager()	
