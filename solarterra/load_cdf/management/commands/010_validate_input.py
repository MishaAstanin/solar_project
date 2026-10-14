from django.core.management.base import BaseCommand
import os
import subprocess
from django.conf import settings
from load_cdf.models import make_log_entry
from .evaluate_extras import command_logger
import logging


logger = logging.getLogger('solarterra.upload')


class Command(BaseCommand):

    help = "#0 step in evaluation stage of the dataset upload.\n\
            Command checks that both input files exist and are valid."

    def add_arguments(self, parser):
        parser.add_argument("zip_filename", nargs=1, type=str, help="Specify .zip filename")
        parser.add_argument("match_filename", nargs=1, type=str, help="Specify .json matchifle name")

    @command_logger
    def handle(self, *args, **options):

        zip_filename = options["zip_filename"][0]
        zip_path = os.path.join(settings.UPLOAD_ZIP_DIR, zip_filename)
        match_filename = options["match_filename"][0]
        match_file_path = os.path.join(settings.MATCH_FILE_DIR, match_filename)
        

        # Check if the zip file and match file exist
        if not zip_filename.endswith('.zip') or not os.path.isfile(zip_path):
            message = f"zip file {zip_path} does not exist"
            make_log_entry(message, "ERROR")
            logger.error(message, exc_info=True)
            exit(1)

        make_log_entry(f"found file '{zip_path}'", "INFO")

        if not match_filename.endswith('.json') or not os.path.isfile(match_file_path):
            message = f"match_file {match_file_path} does not exist"
            make_log_entry(message, "ERROR")
            logger.error(message, exc_info=True)
            exit(1)
        
        make_log_entry(f"found file '{match_file_path}'", "INFO")

        # Read the match file
        try:
            result = subprocess.run(
                ['python', '-m', 'json.tool', match_file_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode != 0:
                message = f"error decoding JSON from match file: JSONDecodeError. Check if the file is a valid JSON"
                make_log_entry(message, "ERROR")
                logger.error(message, exc_info=True)
                exit(1)

            make_log_entry(f"match file {match_filename} opens successfully", "INFO")
        
        except subprocess.TimeoutExpired:
            message = f"error processing match file: timeout reading {match_filename}"
            make_log_entry(message, "ERROR")
            logger.error(message, exc_info=True)
            exit(1)

        except Exception as e:
            message = f"error processing match file: {str(e)}"
            make_log_entry(message, "ERROR")
            logger.error(message, exc_info=True)
            exit(1)
