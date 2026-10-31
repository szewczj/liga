import tempfile
import unittest
from pathlib import Path

from league.repository import _database_path


class FrozenDatabasePathTests(unittest.TestCase):
    def test_database_is_created_beside_executable_and_migrates_old_user_database(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executable_dir = root / "application"
            executable_dir.mkdir()
            executable = executable_dir / "LigaPilkarska.exe"
            executable.write_bytes(b"exe")
            legacy = root / "legacy" / "league_db.db"
            legacy.parent.mkdir()
            legacy.write_bytes(b"user database")
            bundle = root / "bundle"
            bundle.mkdir()
            (bundle / "league_db.db").write_bytes(b"bundled defaults")

            path = _database_path(
                frozen=True,
                executable=executable,
                bundle_dir=bundle,
                legacy_database=legacy,
            )

            self.assertEqual(path, executable_dir / "league_db.db")
            self.assertEqual(path.read_bytes(), b"user database")

    def test_bundled_database_is_copied_when_no_legacy_database_exists(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executable_dir = root / "application"
            executable_dir.mkdir()
            executable = executable_dir / "LigaPilkarska.exe"
            bundle = root / "bundle"
            bundle.mkdir()
            (bundle / "league_db.db").write_bytes(b"bundled defaults")

            path = _database_path(
                frozen=True,
                executable=executable,
                bundle_dir=bundle,
                legacy_database=root / "missing.db",
            )

            self.assertEqual(path.parent, executable_dir)
            self.assertEqual(path.read_bytes(), b"bundled defaults")

    def test_existing_database_beside_executable_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executable_dir = root / "application"
            executable_dir.mkdir()
            executable = executable_dir / "LigaPilkarska.exe"
            database = executable_dir / "league_db.db"
            database.write_bytes(b"existing app data")
            bundle = root / "bundle"
            bundle.mkdir()
            (bundle / "league_db.db").write_bytes(b"bundled defaults")

            path = _database_path(
                frozen=True,
                executable=executable,
                bundle_dir=bundle,
                legacy_database=root / "missing.db",
            )

            self.assertEqual(path, database)
            self.assertEqual(database.read_bytes(), b"existing app data")


if __name__ == "__main__":
    unittest.main()
