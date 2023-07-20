from __future__ import unicode_literals

from django.apps import AppConfig


class HelplineConfig(AppConfig):
    name = 'helpline'
    verbose = "Helpline"

    def ready(self):
        import helpline.signals # register the signals
