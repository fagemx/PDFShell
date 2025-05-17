import shutil
import time
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Cleans up old session directories from the PDF_UPLOADS_ROOT.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Delete session directories older than this many days (based on last modification time). Default is 7.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate the cleanup without actually deleting anything.',
        )

    def handle(self, *args, **options):
        days_old = options['days']
        dry_run = options['dry_run']
        
        if days_old < 0:
            raise CommandError("Value for --days cannot be negative.")

        uploads_root = getattr(settings, 'PDF_UPLOADS_ROOT', None)
        if not uploads_root:
            raise CommandError("PDF_UPLOADS_ROOT is not defined in settings.")

        uploads_path = Path(uploads_root)
        if not uploads_path.is_dir():
            self.stdout.write(self.style.WARNING(f"PDF_UPLOADS_ROOT '{uploads_path}' does not exist or is not a directory. Nothing to clean."))
            return

        self.stdout.write(self.style.NOTICE(f"Starting cleanup of session directories older than {days_old} days in '{uploads_path}'."))
        if dry_run:
            self.stdout.write(self.style.NOTICE("DRY RUN active. No directories will actually be deleted."))

        current_time = time.time()
        cutoff_time = current_time - (days_old * 24 * 60 * 60)
        
        deleted_count = 0
        error_count = 0

        for session_dir in uploads_path.iterdir():
            if session_dir.is_dir(): # Ensure it's a directory
                try:
                    dir_mod_time = session_dir.stat().st_mtime
                    if dir_mod_time < cutoff_time:
                        self.stdout.write(f"Found old session directory: {session_dir.name} (Last modified: {time.ctime(dir_mod_time)})")
                        if not dry_run:
                            try:
                                shutil.rmtree(session_dir)
                                self.stdout.write(self.style.SUCCESS(f"Successfully deleted: {session_dir.name}"))
                                deleted_count += 1
                            except Exception as e:
                                self.stderr.write(self.style.ERROR(f"Error deleting {session_dir.name}: {e}"))
                                logger.error(f"Failed to delete directory {session_dir}: {e}", exc_info=True)
                                error_count += 1
                        else:
                            # In dry run, just increment what would be deleted
                            deleted_count +=1 
                    else:
                        logger.debug(f"Skipping recent directory: {session_dir.name} (Last modified: {time.ctime(dir_mod_time)})")
                except FileNotFoundError:
                    # This can happen if the directory is deleted by another process between iterdir() and stat()
                    logger.warning(f"Directory {session_dir.name} was not found during stat, skipping.")
                    continue
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"Error processing directory {session_dir.name}: {e}"))
                    logger.error(f"Failed to process directory {session_dir}: {e}", exc_info=True)
                    error_count += 1
            else:
                logger.debug(f"Skipping non-directory item in uploads_root: {session_dir.name}")


        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"DRY RUN finished. Would have deleted {deleted_count} session directories."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Cleanup finished. Deleted {deleted_count} session directories."))
        
        if error_count > 0:
            self.stdout.write(self.style.WARNING(f"{error_count} errors occurred during cleanup. Check logs for details."))

        self.stdout.write(self.style.NOTICE("Cleanup process complete.")) 