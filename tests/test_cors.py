import importlib
import pathlib
import sys
from contextlib import asynccontextmanager

from fastapi.testclient import TestClient

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(PROJECT_ROOT / "simple_snowplow"))

from core.config import SecurityConfig  # noqa: E402


def _reload_main_module():
    return importlib.import_module("simple_snowplow.main")


def _no_op_lifespan(_app):
    @asynccontextmanager
    async def _lifespan(_application):
        yield

    return _lifespan(_app)


def test_security_config_normalizes_cors_origins():
    security = SecurityConfig(
        cors_allowed_origins=["https://Example.com/"],
    )

    assert security.cors_allowed_origins == ["https://example.com"]


def test_security_config_defaults_to_allow_all_credentialed_cors():
    security = SecurityConfig()

    assert security.cors_allowed_origins == ["*"]
    assert security.cors_allow_credentials is True


def test_create_app_allows_credentialed_cors_for_explicit_origins(monkeypatch):
    monkeypatch.chdir(PROJECT_ROOT / "simple_snowplow")
    main_module = _reload_main_module()
    monkeypatch.setattr(main_module, "lifespan", _no_op_lifespan)
    monkeypatch.setattr(
        main_module.settings.security,
        "cors_allowed_origins",
        ["https://example.com"],
    )
    monkeypatch.setattr(
        main_module.settings.security,
        "cors_allow_credentials",
        True,
    )

    app = main_module.create_app()

    with TestClient(app) as client:
        response = client.options(
            "/tracker",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://example.com"
    assert response.headers["access-control-allow-credentials"] == "true"


def test_create_app_supports_credentialed_cors_with_allow_all_origins(monkeypatch):
    monkeypatch.chdir(PROJECT_ROOT / "simple_snowplow")
    main_module = _reload_main_module()
    monkeypatch.setattr(main_module, "lifespan", _no_op_lifespan)
    monkeypatch.setattr(main_module.settings.security, "cors_allowed_origins", ["*"])
    monkeypatch.setattr(
        main_module.settings.security,
        "cors_allow_credentials",
        True,
    )

    app = main_module.create_app()

    with TestClient(app) as client:
        response = client.options(
            "/tracker",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://example.com"
    assert response.headers["access-control-allow-credentials"] == "true"
