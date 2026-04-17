from django.apps import AppConfig


class TempleAdminConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'temple_admin'

    def ready(self):
        import os
        from django.contrib.auth import get_user_model
        from django.db.utils import OperationalError, ProgrammingError

        User = get_user_model()

        username = os.getenv("DJANGO_SUPERUSER_USERNAME")
        email = os.getenv("DJANGO_SUPERUSER_EMAIL")
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD")

        try:
            if username and password:
                if not User.objects.filter(username=username).exists():
                    User.objects.create_superuser(username, email, password)
        except (OperationalError, ProgrammingError):
            # DB not ready yet (migrations not applied)
            pass