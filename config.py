import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY                = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    JWT_SECRET_KEY            = os.environ.get("JWT_SECRET_KEY", SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES  = timedelta(hours=8)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_TOKEN_LOCATION        = ["headers", "cookies"]
    JWT_COOKIE_SECURE         = os.environ.get("FLASK_ENV") == "production"
    JWT_COOKIE_SAMESITE       = "Lax"
    JWT_ACCESS_COOKIE_NAME    = "access_token_cookie"
    JWT_COOKIE_CSRF_PROTECT   = False
    BCRYPT_LOG_ROUNDS         = 12
    DATABASE                  = os.environ.get("DATABASE", "timetrack.db")

def get_config():
    return Config