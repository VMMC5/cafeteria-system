import os


class Config:
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-secret")
    API_BASE_URL = os.environ.get("API_BASE_URL", "http://api:8000/api/v1")
