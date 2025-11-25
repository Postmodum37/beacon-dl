"""Tests for download history module."""

from src.beacon_dl.history import DownloadHistory, DownloadRecord, VerifyResult


class TestDownloadHistory:
    """Tests for DownloadHistory class."""

    def test_init_creates_database(self, tmp_path):
        """Test database is created on initialization."""
        db_path = tmp_path / "test.db"
        DownloadHistory(db_path)  # Creates database as side effect

        assert db_path.exists()

    def test_record_and_retrieve_download(self, tmp_path):
        """Test recording and retrieving a download."""
        db_path = tmp_path / "test.db"
        history = DownloadHistory(db_path)

        history.record_download(
            content_id="abc123",
            slug="c4-e007-on-the-scent",
            title="C4 E007 | On the Scent",
            filename="Critical.Role.S04E07.On.the.Scent.1080p.mkv",
            file_size=2_500_000_000,
            sha256="abcdef1234567890",
        )

        record = history.get_download("abc123")

        assert record is not None
        assert record.content_id == "abc123"
        assert record.slug == "c4-e007-on-the-scent"
        assert record.title == "C4 E007 | On the Scent"
        assert record.filename == "Critical.Role.S04E07.On.the.Scent.1080p.mkv"
        assert record.file_size == 2_500_000_000
        assert record.sha256 == "abcdef1234567890"
        assert record.status == "completed"

    def test_is_downloaded(self, tmp_path):
        """Test checking if content was downloaded."""
        db_path = tmp_path / "test.db"
        history = DownloadHistory(db_path)

        assert not history.is_downloaded("abc123")

        history.record_download(
            content_id="abc123",
            slug="test-slug",
            title="Test Title",
            filename="test.mkv",
            file_size=1000,
            sha256="abc",
        )

        assert history.is_downloaded("abc123")
        assert not history.is_downloaded("other")

    def test_get_download_not_found(self, tmp_path):
        """Test getting non-existent download returns None."""
        db_path = tmp_path / "test.db"
        history = DownloadHistory(db_path)

        record = history.get_download("nonexistent")
        assert record is None

    def test_get_download_by_filename(self, tmp_path):
        """Test getting download by filename."""
        db_path = tmp_path / "test.db"
        history = DownloadHistory(db_path)

        history.record_download(
            content_id="abc123",
            slug="test-slug",
            title="Test Title",
            filename="test_file.mkv",
            file_size=1000,
            sha256="abc",
        )

        record = history.get_download_by_filename("test_file.mkv")

        assert record is not None
        assert record.content_id == "abc123"
        assert record.filename == "test_file.mkv"

    def test_list_downloads(self, tmp_path):
        """Test listing downloads."""
        db_path = tmp_path / "test.db"
        history = DownloadHistory(db_path)

        # Add multiple downloads
        for i in range(5):
            history.record_download(
                content_id=f"id{i}",
                slug=f"slug{i}",
                title=f"Title {i}",
                filename=f"file{i}.mkv",
                file_size=1000 * i,
                sha256=f"hash{i}",
            )

        downloads = history.list_downloads(limit=3)

        assert len(downloads) == 3
        # Should be in reverse order (newest first)
        assert downloads[0].content_id == "id4"

    def test_count_downloads(self, tmp_path):
        """Test counting downloads."""
        db_path = tmp_path / "test.db"
        history = DownloadHistory(db_path)

        assert history.count_downloads() == 0

        for i in range(3):
            history.record_download(
                content_id=f"id{i}",
                slug=f"slug{i}",
                title=f"Title {i}",
                filename=f"file{i}.mkv",
                file_size=1000,
                sha256=f"hash{i}",
            )

        assert history.count_downloads() == 3

    def test_clear_history(self, tmp_path):
        """Test clearing history."""
        db_path = tmp_path / "test.db"
        history = DownloadHistory(db_path)

        for i in range(3):
            history.record_download(
                content_id=f"id{i}",
                slug=f"slug{i}",
                title=f"Title {i}",
                filename=f"file{i}.mkv",
                file_size=1000,
                sha256=f"hash{i}",
            )

        deleted = history.clear_history()

        assert deleted == 3
        assert history.count_downloads() == 0

    def test_remove_download(self, tmp_path):
        """Test removing a specific download."""
        db_path = tmp_path / "test.db"
        history = DownloadHistory(db_path)

        history.record_download(
            content_id="abc123",
            slug="test-slug",
            title="Test Title",
            filename="test.mkv",
            file_size=1000,
            sha256="abc",
        )

        assert history.is_downloaded("abc123")

        removed = history.remove_download("abc123")

        assert removed
        assert not history.is_downloaded("abc123")

    def test_remove_nonexistent_download(self, tmp_path):
        """Test removing non-existent download returns False."""
        db_path = tmp_path / "test.db"
        history = DownloadHistory(db_path)

        removed = history.remove_download("nonexistent")
        assert not removed

    def test_replace_existing_download(self, tmp_path):
        """Test recording download replaces existing record."""
        db_path = tmp_path / "test.db"
        history = DownloadHistory(db_path)

        # First record
        history.record_download(
            content_id="abc123",
            slug="test-slug",
            title="Old Title",
            filename="old.mkv",
            file_size=1000,
            sha256="old_hash",
        )

        # Replace with new record
        history.record_download(
            content_id="abc123",
            slug="test-slug",
            title="New Title",
            filename="new.mkv",
            file_size=2000,
            sha256="new_hash",
        )

        # Should still have only one record
        assert history.count_downloads() == 1

        record = history.get_download("abc123")
        assert record.title == "New Title"
        assert record.filename == "new.mkv"
        assert record.file_size == 2000

    def test_get_download_by_slug(self, tmp_path):
        """Test getting download by slug."""
        db_path = tmp_path / "test.db"
        history = DownloadHistory(db_path)

        history.record_download(
            content_id="abc123",
            slug="c4-e007-on-the-scent",
            title="Test Title",
            filename="test_file.mkv",
            file_size=1000,
            sha256="abc",
        )

        record = history.get_download_by_slug("c4-e007-on-the-scent")

        assert record is not None
        assert record.content_id == "abc123"
        assert record.slug == "c4-e007-on-the-scent"

    def test_get_download_by_slug_not_found(self, tmp_path):
        """Test getting non-existent slug returns None."""
        db_path = tmp_path / "test.db"
        history = DownloadHistory(db_path)

        record = history.get_download_by_slug("nonexistent-slug")
        assert record is None


class TestVerifyFileByRecord:
    """Tests for verify_file_by_record method."""

    def test_verify_valid_file_by_record(self, tmp_path):
        """Test verifying a valid file with record."""
        db_path = tmp_path / "test.db"
        history = DownloadHistory(db_path)

        # Create a test file
        test_file = tmp_path / "test.mkv"
        test_file.write_bytes(b"test content" * 100)
        file_size = test_file.stat().st_size
        sha256 = history.calculate_sha256(test_file)

        # Record download
        history.record_download(
            content_id="abc123",
            slug="test-slug",
            title="Test Title",
            filename=str(test_file),
            file_size=file_size,
            sha256=sha256,
        )

        record = history.get_download("abc123")
        result = history.verify_file_by_record(record, test_file)

        assert result == VerifyResult.VALID

    def test_verify_file_missing_by_record(self, tmp_path):
        """Test verifying missing file by record."""
        db_path = tmp_path / "test.db"
        history = DownloadHistory(db_path)

        history.record_download(
            content_id="abc123",
            slug="test-slug",
            title="Test Title",
            filename="nonexistent.mkv",
            file_size=1000,
            sha256="abc",
        )

        record = history.get_download("abc123")
        result = history.verify_file_by_record(record, tmp_path / "nonexistent.mkv")

        assert result == VerifyResult.FILE_MISSING

    def test_verify_size_mismatch_by_record(self, tmp_path):
        """Test verifying file with size mismatch."""
        db_path = tmp_path / "test.db"
        history = DownloadHistory(db_path)

        # Create a test file
        test_file = tmp_path / "test.mkv"
        test_file.write_bytes(b"test content")

        # Record with wrong size
        history.record_download(
            content_id="abc123",
            slug="test-slug",
            title="Test Title",
            filename=str(test_file),
            file_size=99999,  # Wrong size
            sha256="abc",
        )

        record = history.get_download("abc123")
        result = history.verify_file_by_record(record, test_file)

        assert result == VerifyResult.SIZE_MISMATCH

    def test_verify_hash_mismatch_by_record(self, tmp_path):
        """Test verifying file with hash mismatch."""
        db_path = tmp_path / "test.db"
        history = DownloadHistory(db_path)

        # Create a test file
        test_file = tmp_path / "test.mkv"
        test_file.write_bytes(b"test content")
        file_size = test_file.stat().st_size

        # Record with wrong hash
        history.record_download(
            content_id="abc123",
            slug="test-slug",
            title="Test Title",
            filename=str(test_file),
            file_size=file_size,
            sha256="wrong_hash_value",
        )

        record = history.get_download("abc123")
        result = history.verify_file_by_record(record, test_file)

        assert result == VerifyResult.HASH_MISMATCH


class TestSHA256Calculation:
    """Tests for SHA256 calculation."""

    def test_calculate_sha256(self, tmp_path):
        """Test SHA256 calculation on a file."""
        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"Hello, World!")

        # Known SHA256 of "Hello, World!"
        expected = "dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f"

        result = DownloadHistory.calculate_sha256(test_file)

        assert result == expected

    def test_calculate_sha256_empty_file(self, tmp_path):
        """Test SHA256 of empty file."""
        test_file = tmp_path / "empty.txt"
        test_file.write_bytes(b"")

        # Known SHA256 of empty string
        expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

        result = DownloadHistory.calculate_sha256(test_file)

        assert result == expected

    def test_calculate_sha256_large_file(self, tmp_path):
        """Test SHA256 calculation on larger file (streaming)."""
        test_file = tmp_path / "large.bin"
        # Create 1MB file
        test_file.write_bytes(b"x" * 1_000_000)

        result = DownloadHistory.calculate_sha256(test_file)

        # Should return a valid hex string
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)


class TestFileVerification:
    """Tests for file verification."""

    def test_verify_valid_file(self, tmp_path):
        """Test verifying a valid file."""
        db_path = tmp_path / "test.db"
        history = DownloadHistory(db_path)

        # Create test file
        test_file = tmp_path / "video.mkv"
        test_file.write_bytes(b"test content")
        file_size = test_file.stat().st_size
        sha256 = DownloadHistory.calculate_sha256(test_file)

        # Record download
        history.record_download(
            content_id="abc123",
            slug="test-slug",
            title="Test",
            filename=str(test_file),
            file_size=file_size,
            sha256=sha256,
        )

        result = history.verify_file("abc123", test_file)

        assert result == VerifyResult.VALID

    def test_verify_file_missing(self, tmp_path):
        """Test verifying missing file."""
        db_path = tmp_path / "test.db"
        history = DownloadHistory(db_path)

        history.record_download(
            content_id="abc123",
            slug="test-slug",
            title="Test",
            filename="nonexistent.mkv",
            file_size=1000,
            sha256="abc",
        )

        result = history.verify_file("abc123", tmp_path / "nonexistent.mkv")

        assert result == VerifyResult.FILE_MISSING

    def test_verify_size_mismatch(self, tmp_path):
        """Test verifying file with wrong size."""
        db_path = tmp_path / "test.db"
        history = DownloadHistory(db_path)

        # Create test file
        test_file = tmp_path / "video.mkv"
        test_file.write_bytes(b"test content")

        # Record with wrong size
        history.record_download(
            content_id="abc123",
            slug="test-slug",
            title="Test",
            filename=str(test_file),
            file_size=9999999,  # Wrong size
            sha256="abc",
        )

        result = history.verify_file("abc123", test_file)

        assert result == VerifyResult.SIZE_MISMATCH

    def test_verify_hash_mismatch(self, tmp_path):
        """Test verifying file with wrong hash."""
        db_path = tmp_path / "test.db"
        history = DownloadHistory(db_path)

        # Create test file
        test_file = tmp_path / "video.mkv"
        test_file.write_bytes(b"test content")
        file_size = test_file.stat().st_size

        # Record with wrong hash but correct size
        history.record_download(
            content_id="abc123",
            slug="test-slug",
            title="Test",
            filename=str(test_file),
            file_size=file_size,
            sha256="wrong_hash_value",
        )

        result = history.verify_file("abc123", test_file)

        assert result == VerifyResult.HASH_MISMATCH

    def test_verify_not_in_history(self, tmp_path):
        """Test verifying file not in history."""
        db_path = tmp_path / "test.db"
        history = DownloadHistory(db_path)

        test_file = tmp_path / "video.mkv"
        test_file.write_bytes(b"test content")

        result = history.verify_file("nonexistent", test_file)

        assert result == VerifyResult.NOT_IN_HISTORY


class TestDownloadRecord:
    """Tests for DownloadRecord dataclass."""

    def test_download_record_creation(self):
        """Test creating a DownloadRecord."""
        record = DownloadRecord(
            id=1,
            content_id="abc123",
            slug="test-slug",
            title="Test Title",
            filename="test.mkv",
            file_size=1000,
            sha256="abc",
            downloaded_at="2025-11-25T10:00:00",
            verified_at="2025-11-25T10:00:00",
            status="completed",
        )

        assert record.id == 1
        assert record.content_id == "abc123"
        assert record.status == "completed"


class TestVerifyResult:
    """Tests for VerifyResult enum."""

    def test_verify_result_values(self):
        """Test VerifyResult enum values."""
        assert VerifyResult.VALID.value == "valid"
        assert VerifyResult.SIZE_MISMATCH.value == "size_mismatch"
        assert VerifyResult.HASH_MISMATCH.value == "hash_mismatch"
        assert VerifyResult.FILE_MISSING.value == "file_missing"
        assert VerifyResult.NOT_IN_HISTORY.value == "not_in_history"


class TestUpdateFilename:
    """Tests for update_filename method."""

    def test_update_filename_success(self, tmp_path):
        """Test updating filename for existing record."""
        db_path = tmp_path / "test.db"
        history = DownloadHistory(db_path)

        # Record a download
        history.record_download(
            content_id="abc123",
            slug="test-slug",
            title="Test Title",
            filename="old_filename.mkv",
            file_size=1000,
            sha256="abc",
        )

        # Update filename
        result = history.update_filename("abc123", "new_filename.mkv")

        assert result is True

        # Verify the filename was updated
        record = history.get_download("abc123")
        assert record.filename == "new_filename.mkv"

    def test_update_filename_not_found(self, tmp_path):
        """Test updating filename for non-existent record."""
        db_path = tmp_path / "test.db"
        history = DownloadHistory(db_path)

        # Try to update non-existent record
        result = history.update_filename("nonexistent", "new_filename.mkv")

        assert result is False
