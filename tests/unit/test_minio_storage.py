import pytest

from app.core.config import Settings
from app.storage.minio_service import MinioStorageService, MinioUrlError


def settings(**overrides):
    values = {
        "minio_enabled": True,
        "minio_endpoint": "minio:9000",
        "minio_public_base_url": "http://storage.example:9002",
        "minio_bucket": "wiki-documents",
        "minio_access_key": "access",
        "minio_secret_key": "secret",
        "minio_secure": False,
    }
    values.update(overrides)
    return Settings(**values)


def test_public_and_internal_minio_endpoints_are_independent():
    service = MinioStorageService(settings())
    ref = service.parse_image_url(
        "http://storage.example:9002/wiki-documents/docs/a/page%2001.jpg"
    )
    assert ref.bucket == "wiki-documents"
    assert ref.object_key == "docs/a/page 01.jpg"
    assert service._client_endpoint() == ("minio:9000", False)


def test_minio_url_rejects_unconfigured_host_port():
    service = MinioStorageService(settings())
    with pytest.raises(MinioUrlError):
        service.parse_image_url(
            "http://storage.example:9003/wiki-documents/docs/a/page.jpg"
        )


def test_minio_url_rejects_other_bucket():
    service = MinioStorageService(settings())
    with pytest.raises(MinioUrlError):
        service.parse_image_url(
            "http://storage.example:9002/other-bucket/docs/a/page.jpg"
        )


def test_build_public_url_uses_configured_external_base():
    service = MinioStorageService(settings())
    assert service.build_public_url("docs/a/page 01.jpg") == (
        "http://storage.example:9002/wiki-documents/docs/a/page%2001.jpg"
    )
