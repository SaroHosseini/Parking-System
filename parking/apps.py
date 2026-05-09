from django.apps import AppConfig


class ParkingConfig(AppConfig):
    name = 'parking'


    def ready(self):

        import parking.signals