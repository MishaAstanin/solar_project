from django.core.management.base import BaseCommand
import os
from django.template.loader import render_to_string
from load_cdf.models import *
from .evaluate_extras import command_logger, UploadRequired
import logging


logger = logging.getLogger('solarterra.upload')


class Command(UploadRequired, BaseCommand):

    help = "#8 step in evaluation process. Command creates data model template file."
    
    def add_arguments(self, parser):
        parser.add_argument("upload_tag", nargs=1, type=str)
        parser.add_argument("dataset_tag", nargs=1, type=str)

    @command_logger
    def handle(self, *args, **options):
        
        upload = super().handle(**options)

        try:
            dynamic_model = upload.dataset.dynamic
        except Exception as e:
            message = "dynamic model instance: {e}"
            make_log_entry(message, "ERROR", upload=upload)
            logger.error(message, exc_info=True)
            upload.terminate()


        if  os.path.exists(dynamic_model.model_file_path):
            message = f"data model file '{dynamic_model.model_file_path}' already exists"
            make_log_entry(message, "ERROR", upload=upload)
            logger.error(message, exc_info=True)
            exit(0)

        
        content = render_to_string('model.tpl', context={ 'dm_instance' : dynamic_model })

        with open(dynamic_model.model_file_path, "w+") as model_file:
            model_file.write(content)

        make_log_entry(f"saved data model template file '{dynamic_model.model_file_path}'", "INFO", upload=upload)
