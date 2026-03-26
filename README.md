to deactivate expired poojas 
python manage.py deactivate_past_poojas


cron jobs celery beat how to start

Terminal 1 – Redis
redis-server

Terminal 2 – Celery Worker
celery -A tprmsystem worker -l info --pool=solo

Terminal 3 – Celery Beat
celery -A tprmsystem beat -l info
