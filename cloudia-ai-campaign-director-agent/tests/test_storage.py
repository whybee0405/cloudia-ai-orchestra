"""Section 15 — MinIO storage tests."""
import pytest
from unittest.mock import patch, MagicMock


class TestStoragePaths:
    def test_object_path_format(self):
        from backend.media.storage import object_path
        path = object_path(1, 5, "raw", "images", "test.jpg")
        assert path == "1/campaigns/5/raw/images/test.jpg"

    def test_object_path_client_prefix(self):
        from backend.media.storage import object_path
        path = object_path(42, 10, "edited", "videos", "test.mp4")
        assert path.startswith("42/")

    def test_different_clients_get_different_paths(self):
        from backend.media.storage import object_path
        path_a = object_path(1, 1, "raw", "images", "test.jpg")
        path_b = object_path(2, 1, "raw", "images", "test.jpg")
        assert path_a != path_b
        assert path_a.startswith("1/")
        assert path_b.startswith("2/")


class TestSignedUrlIsolation:
    def test_signed_url_validates_client_prefix(self):
        from backend.media.storage import signed_url
        mock_minio = MagicMock()
        mock_minio.presigned_get_object.return_value = "https://minio.local/1/campaigns/5/test.jpg?sig=abc"

        with patch("backend.media.storage.get_client", return_value=mock_minio):
            with patch("backend.media.storage.get_settings") as mock_settings:
                mock_settings.return_value.minio_bucket = "cloudia-media"
                # Client 1 requesting their own file — should work
                url = signed_url("1/campaigns/5/raw/images/test.jpg", client_id_prefix="1")
                assert url is not None

    def test_signed_url_rejects_wrong_client_prefix(self):
        from backend.media.storage import signed_url

        # Client 2 requesting client 1's file — should raise before even calling MinIO
        with pytest.raises(PermissionError):
            signed_url("1/campaigns/5/raw/images/test.jpg", client_id_prefix="2")

    def test_signed_url_no_prefix_check_skipped(self):
        from backend.media.storage import signed_url
        mock_minio = MagicMock()
        mock_minio.presigned_get_object.return_value = "https://minio.local/file?sig=abc"

        with patch("backend.media.storage.get_client", return_value=mock_minio):
            with patch("backend.media.storage.get_settings") as mock_settings:
                mock_settings.return_value.minio_bucket = "cloudia-media"
                # No prefix validation if client_id_prefix not provided
                url = signed_url("1/campaigns/5/raw/images/test.jpg")
                assert url is not None


class TestStorageOperations:
    def test_upload_and_download_round_trip(self):
        from tests.mocks.platforms import MockMinIO
        minio = MockMinIO()
        data = b"fake image bytes"
        path = "1/campaigns/1/raw/images/test.jpg"

        minio.upload(data, path, "image/jpeg")
        retrieved = minio.download(path)
        assert retrieved == data

    def test_upload_failure_raises(self):
        from tests.mocks.platforms import MockMinIO
        minio = MockMinIO()
        minio.set_mode("upload_failure")

        with pytest.raises(IOError):
            minio.upload(b"data", "1/test.jpg", "image/jpeg")

    def test_download_timeout_raises(self):
        from tests.mocks.platforms import MockMinIO
        minio = MockMinIO()
        minio.set_mode("download_timeout")

        with pytest.raises(TimeoutError):
            minio.download("1/test.jpg")

    def test_files_stored_under_client_path(self):
        from tests.mocks.platforms import MockMinIO
        from backend.media.storage import object_path

        minio = MockMinIO()
        path = object_path(client_id=3, campaign_id=7, stage="raw", subdir="images", filename="logo.jpg")
        minio.upload(b"logo bytes", path, "image/jpeg")

        minio.assert_stored_at("3/campaigns/7/raw/images/")
