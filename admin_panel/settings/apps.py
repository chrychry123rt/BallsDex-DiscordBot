import asyncio
import logging
import sys

from asgiref.sync import sync_to_async
from django.apps import AppConfig

log = logging.getLogger(__name__)


class SettingsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "settings"

    def ready(self):
        # TODO: change this mess
        if (
            "makemigrations" in sys.argv
            or "migrate" in sys.argv
            or "startapp" in sys.argv
            or "collectstatic" in sys.argv
        ):
            return

        from .models import load_settings
        from django.db import connection

        # Check if the settings table exists before trying to load settings
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM information_schema.tables WHERE table_name='settings_settings'")
                table_exists = cursor.fetchone()
        except Exception:
            table_exists = False

        if not table_exists:
            log.warning("Settings table does not exist, skipping load_settings")
            return

        try:
            # using uvicorn, the process will be in an async context and refuse to run sync db queries
            # so yes, we have to make a sync function async, and run it in a sync function
            task = asyncio.get_running_loop().create_task(sync_to_async(load_settings)())
            task.add_done_callback(lambda t: log.info("Settings read successfully."))
        except RuntimeError:
            # if the bot is running in a sync context
            try:
                load_settings()
            except Exception as e:
                log.warning(f"Could not load settings during app initialization: {e}")
