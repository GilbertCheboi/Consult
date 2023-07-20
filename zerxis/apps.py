from __future__ import unicode_literals

from django.apps import AppConfig


class ZerxisConfig(AppConfig):
    name = 'zerxis'
    verbose = "Zerxis"

    def ready(self):
        import zerxis.signals # register the signals
