from app.core.config import settings


def test_settings_tiene_campos_de_auth():
    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30
    assert settings.REFRESH_TOKEN_EXPIRE_MINUTES == 10080
    assert settings.ADMIN_CORREO
    assert settings.ADMIN_PASSWORD
    assert settings.ADMIN_NOMBRE
