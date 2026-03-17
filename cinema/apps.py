from django.apps import AppConfig


class CinemaConfig(AppConfig):
    name = 'cinema'

    def ready(self):
        from . import signals  # noqa: F401
