import pytest

from app.models import media
from config import Config

FAKE_URL = "cloudinary://123456:secreto@demo"


@pytest.fixture()
def configured(monkeypatch):
    monkeypatch.setattr(Config, "CLOUDINARY_URL", FAKE_URL)


def test_informes_image_is_none_without_cloudinary(monkeypatch):
    monkeypatch.setattr(Config, "CLOUDINARY_URL", "")
    assert media.informes_image("charts") is None


def test_image_url_applies_auto_format_and_quality(configured):
    url = media.image_url("market-dashboard/informes/charts", 640)
    assert url.startswith("https://res.cloudinary.com/demo/image/upload/")
    assert "f_auto" in url and "q_auto" in url and "w_640" in url
    assert url.endswith("/market-dashboard/informes/charts")


def test_informes_image_builds_responsive_srcset(configured):
    image = media.informes_image("stats")
    assert "w_1280" in image.src
    for width in media.RESPONSIVE_WIDTHS:
        assert f"w_{width}/" in image.srcset
        assert f"market-dashboard/informes/stats {width}w" in image.srcset


def test_invalid_cloudinary_url_raises(monkeypatch):
    monkeypatch.setattr(Config, "CLOUDINARY_URL", "https://no-es-cloudinary")
    with pytest.raises(media.MediaError):
        media.informes_image("charts")


def test_upload_requires_configuration(monkeypatch):
    monkeypatch.setattr(Config, "CLOUDINARY_URL", "")
    with pytest.raises(media.MediaError):
        media.upload_informes_images()


def test_upload_sends_local_images_with_stable_public_ids(configured, monkeypatch):
    calls = []

    def _upload(path, **options):
        calls.append((path, options["public_id"], options["overwrite"]))
        return {"secure_url": f"https://res.cloudinary.com/demo/{options['public_id']}.jpg"}

    monkeypatch.setattr("app.models.media.cloudinary.uploader.upload", _upload)
    urls = media.upload_informes_images()
    assert len(urls) == len(media.INFORMES_IMAGES)
    for (path, public_id, overwrite), name in zip(calls, media.INFORMES_IMAGES):
        assert path.endswith(f"img/informes/{name}.jpg")
        assert public_id == f"market-dashboard/informes/{name}"
        assert overwrite is True


def test_local_source_images_exist():
    for name in media.INFORMES_IMAGES:
        assert (media.LOCAL_IMAGE_DIR / f"{name}.jpg").is_file()
