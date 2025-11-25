"""Download history and integrity verification for beacon-dl.

This module manages download tracking using a SQLite database and provides
file integrity verification through SHA256 checksums.
"""

import hashlib
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

from rich.console import Console

console = Console()


def _get_connection(db_path: Path) -> sqlite3.Connection:
    """Create a database connection with proper settings.

    Args:
        db_path: Path to the database file

    Returns:
        Configured SQLite connection
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


class VerifyResult(Enum):
    """Result of file verification."""

    VALID = "valid"
    SIZE_MISMATCH = "size_mismatch"
    HASH_MISMATCH = "hash_mismatch"
    FILE_MISSING = "file_missing"
    NOT_IN_HISTORY = "not_in_history"


@dataclass
class DownloadRecord:
    """A record of a downloaded file."""

    id: int
    content_id: str
    slug: str
    title: str
    filename: str
    file_size: int | None
    sha256: str | None
    downloaded_at: str
    verified_at: str | None
    status: str


class DownloadHistory:
    """Manages download history and integrity verification.

    Stores download records in a SQLite database for fast lookup and
    provides file integrity verification through SHA256 checksums.
    """

    DB_FILENAME = ".beacon-dl-history.db"

    def __init__(self, db_path: Path | None = None):
        """Initialize download history.

        Args:
            db_path: Path to database file. Defaults to .beacon-dl-history.db
                     in current working directory.
        """
        self.db_path = db_path or Path(self.DB_FILENAME)
        self._init_db()

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> DownloadRecord:
        """Convert a database row to a DownloadRecord.

        Args:
            row: SQLite row with named columns

        Returns:
            DownloadRecord instance
        """
        return DownloadRecord(
            id=row["id"],
            content_id=row["content_id"],
            slug=row["slug"],
            title=row["title"],
            filename=row["filename"],
            file_size=row["file_size"],
            sha256=row["sha256"],
            downloaded_at=row["downloaded_at"],
            verified_at=row["verified_at"],
            status=row["status"],
        )

    def _init_db(self) -> None:
        """Initialize database schema."""
        with closing(_get_connection(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS downloads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content_id TEXT NOT NULL UNIQUE,
                    slug TEXT NOT NULL,
                    title TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    file_size INTEGER,
                    sha256 TEXT,
                    downloaded_at TEXT NOT NULL,
                    verified_at TEXT,
                    status TEXT DEFAULT 'completed'
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_content_id ON downloads(content_id)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_slug ON downloads(slug)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_filename ON downloads(filename)"
            )
            conn.commit()

    def is_downloaded(self, content_id: str) -> bool:
        """Check if content was already downloaded.

        This is a fast check using only the database, no file I/O.

        Args:
            content_id: BeaconTV content ID (MongoDB ObjectId)

        Returns:
            True if content was previously downloaded
        """
        with closing(_get_connection(self.db_path)) as conn:
            cursor = conn.execute(
                "SELECT 1 FROM downloads WHERE content_id = ? AND status = 'completed'",
                (content_id,),
            )
            return cursor.fetchone() is not None

    def get_download(self, content_id: str) -> DownloadRecord | None:
        """Get download record by content ID.

        Args:
            content_id: BeaconTV content ID

        Returns:
            DownloadRecord if found, None otherwise
        """
        with closing(_get_connection(self.db_path)) as conn:
            cursor = conn.execute(
                "SELECT * FROM downloads WHERE content_id = ?", (content_id,)
            )
            row = cursor.fetchone()
            return self._row_to_record(row) if row else None

    def get_download_by_filename(self, filename: str) -> DownloadRecord | None:
        """Get download record by filename.

        Args:
            filename: The filename (without path)

        Returns:
            DownloadRecord if found, None otherwise
        """
        with closing(_get_connection(self.db_path)) as conn:
            cursor = conn.execute(
                "SELECT * FROM downloads WHERE filename = ?", (filename,)
            )
            row = cursor.fetchone()
            return self._row_to_record(row) if row else None

    def get_download_by_slug(self, slug: str) -> DownloadRecord | None:
        """Get download record by content slug.

        Args:
            slug: The content slug (e.g., 'c4-e007-on-the-scent')

        Returns:
            DownloadRecord if found, None otherwise
        """
        with closing(_get_connection(self.db_path)) as conn:
            cursor = conn.execute("SELECT * FROM downloads WHERE slug = ?", (slug,))
            row = cursor.fetchone()
            return self._row_to_record(row) if row else None

    def record_download(
        self,
        content_id: str,
        slug: str,
        title: str,
        filename: str,
        file_size: int,
        sha256: str,
    ) -> None:
        """Record a successful download.

        Args:
            content_id: BeaconTV content ID
            slug: Content slug
            title: Content title
            filename: Generated filename
            file_size: File size in bytes
            sha256: SHA256 hash of file
        """
        now = datetime.now().isoformat()
        with closing(_get_connection(self.db_path)) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO downloads
                (content_id, slug, title, filename, file_size, sha256, downloaded_at, verified_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'completed')
                """,
                (content_id, slug, title, filename, file_size, sha256, now, now),
            )
            conn.commit()

    def verify_file(self, content_id: str, file_path: Path) -> VerifyResult:
        """Verify file integrity against stored record.

        Checks both file size and SHA256 hash.

        Args:
            content_id: BeaconTV content ID
            file_path: Path to file to verify

        Returns:
            VerifyResult indicating verification status
        """
        record = self.get_download(content_id)
        if not record:
            return VerifyResult.NOT_IN_HISTORY

        if not file_path.exists():
            return VerifyResult.FILE_MISSING

        # Check file size first (fast)
        actual_size = file_path.stat().st_size
        if record.file_size and actual_size != record.file_size:
            return VerifyResult.SIZE_MISMATCH

        # Check SHA256 hash (slow but thorough)
        if record.sha256:
            actual_hash = self.calculate_sha256(file_path)
            if actual_hash != record.sha256:
                return VerifyResult.HASH_MISMATCH

        # Update verified_at timestamp
        self._update_verified_at(content_id)

        return VerifyResult.VALID

    def verify_file_by_record(
        self, record: DownloadRecord, file_path: Path
    ) -> VerifyResult:
        """Verify file integrity using an existing record.

        Args:
            record: Download record to verify against
            file_path: Path to file to verify

        Returns:
            VerifyResult indicating verification status
        """
        if not file_path.exists():
            return VerifyResult.FILE_MISSING

        # Check file size first (fast)
        actual_size = file_path.stat().st_size
        if record.file_size and actual_size != record.file_size:
            return VerifyResult.SIZE_MISMATCH

        # Check SHA256 hash (slow but thorough)
        if record.sha256:
            actual_hash = self.calculate_sha256(file_path)
            if actual_hash != record.sha256:
                return VerifyResult.HASH_MISMATCH

        # Update verified_at timestamp
        self._update_verified_at(record.content_id)

        return VerifyResult.VALID

    def _update_verified_at(self, content_id: str) -> None:
        """Update the verified_at timestamp for a record."""
        now = datetime.now().isoformat()
        with closing(_get_connection(self.db_path)) as conn:
            conn.execute(
                "UPDATE downloads SET verified_at = ? WHERE content_id = ?",
                (now, content_id),
            )
            conn.commit()

    @staticmethod
    def calculate_sha256(file_path: Path, chunk_size: int = 65536) -> str:
        """Calculate SHA256 hash of a file.

        Uses streaming to handle large files without loading into memory.

        Args:
            file_path: Path to file
            chunk_size: Size of chunks to read (default 64KB)

        Returns:
            Hex-encoded SHA256 hash
        """
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(chunk_size):
                sha256.update(chunk)
        return sha256.hexdigest()

    def list_downloads(self, limit: int = 50) -> list[DownloadRecord]:
        """List recent downloads.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of DownloadRecord ordered by download date (newest first)
        """
        with closing(_get_connection(self.db_path)) as conn:
            cursor = conn.execute(
                """
                SELECT * FROM downloads
                ORDER BY downloaded_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            return [self._row_to_record(row) for row in cursor.fetchall()]

    def clear_history(self) -> int:
        """Clear all download history.

        Returns:
            Number of records deleted
        """
        with closing(_get_connection(self.db_path)) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM downloads")
            count = cursor.fetchone()[0]
            conn.execute("DELETE FROM downloads")
            conn.commit()
            return count

    def count_downloads(self) -> int:
        """Get total number of downloads in history.

        Returns:
            Number of download records
        """
        with closing(_get_connection(self.db_path)) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM downloads")
            return cursor.fetchone()[0]

    def remove_download(self, content_id: str) -> bool:
        """Remove a download record.

        Args:
            content_id: BeaconTV content ID to remove

        Returns:
            True if record was removed, False if not found
        """
        with closing(_get_connection(self.db_path)) as conn:
            cursor = conn.execute(
                "DELETE FROM downloads WHERE content_id = ?", (content_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
