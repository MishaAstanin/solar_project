from django.core.management.base import BaseCommand
from django.core import management
from load_cdf.models import Upload
from load_cdf.models import make_log_entry
from load_cdf.utils import get_upload_tag, get_dataset_tag
from .evaluate_extras import command_logger
import json


"""
Command for loading additional data into an existing dataset.

Assumes that:
- evaluate already done for this dataset
- Dataset, Variable, and DynamicModel instances already exist
- Migrations have already been completed

the call is:
    python manage.py load_data <zip_filename> <matchfile_filename>

Both parameters are required.
"""


class Command(BaseCommand):

    help = "Loads additional data from a new zip file into an existing dataset."

    def add_arguments(self, parser):
        parser.add_argument("zip_filename", nargs=1, type=str, help="Specify .zip filename")
        parser.add_argument("match_filename", nargs=1, type=str, help="Specify .json matchifle name")
    
    @command_logger
    def handle(self, *args, **options):

        zip_filename = options["zip_filename"][0]
        match_filename = options["match_filename"][0]
        upload_tag = get_upload_tag(zip_filename)
        dataset_tag = get_dataset_tag(zip_filename)

        self._check_dataset_exists(dataset_tag)
        management.call_command("010_validate_input", zip_filename, match_filename)
        management.call_command("011_create_managing_instances", zip_filename, match_filename)

        upload = Upload.objects.get(u_tag=upload_tag, dataset__tag=dataset_tag)

        matchfile_version = ""
        try:
            with open(upload.match_file_path, "r") as f:
                match_data = json.load(f)
            matchfile_version = match_data['GlobalAttributes']['MATCHFILE_VERSION']['value']
        except Exception as e:
            make_log_entry(f"Could not read MATCHFILE_VERSION from matchfile: {e}", "WARNING", upload=upload)

        upload.update(
            is_initial=False,
            matchfile_version=matchfile_version
        )

        management.call_command("012_filesystem_work", upload_tag, dataset_tag)
        management.call_command("save_data", upload_tag, dataset_tag)

    def _check_dataset_exists(self, dataset_tag):

        from load_cdf.models import Dataset

        dataset = Dataset.objects.get_or_none(tag=dataset_tag)

        if dataset is None:
            make_log_entry(f"Dataset '{dataset_tag}' does not exist. Run 'evaluate' first.", "ERROR")
            exit(1)

        if not hasattr(dataset, 'dynamic') or dataset.dynamic is None:
            make_log_entry(f"DynamicModel for '{dataset_tag}' does not exist. Run 'evaluate' first.", "ERROR")
            exit(1)

        try:
            model_class = dataset.dynamic.resolve_class()
            if model_class is None:
                raise Exception("resolve_class() returned None")
        except Exception as e:
            make_log_entry(f"Data model class for '{dataset_tag}' is not accessible: {e}.", "ERROR")
            exit(1)

        make_log_entry(f"Dataset '{dataset_tag}' and its model '{dataset.dynamic.model_name}' verified.", "INFO")
