[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/F1hjDb63)

## S3 media storage setup

1. Install dependencies with `pip install -r requirements.txt`.
2. Create a local `.env` file.
3. For local testing, start with `DJANGO_DEBUG=True`, `DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost`, and `USE_S3=False`.
4. Set `USE_S3=True` only when you have real AWS storage configured.
5. Add `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_STORAGE_BUCKET_NAME`, and `AWS_S3_REGION_NAME`.
6. Add the same variables to Heroku with `heroku config:set`.

For production-style deployments with `DJANGO_DEBUG=False`, also set `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `GOOGLE_CLIENT_ID`, and `GOOGLE_CLIENT_SECRET`.
