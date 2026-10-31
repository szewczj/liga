"""SQLite repository: persistence details for leagues, teams and matches."""

import sqlite3
import os
import shutil
import sys
from pathlib import Path


def _database_path(
    frozen=None, executable=None, bundle_dir=None, legacy_database=None
):
    if frozen is None:
        frozen = getattr(sys, "frozen", False)
    if frozen:
        executable = Path(executable or sys.executable).resolve()
        path = executable.parent / "league_db.db"
        if path.exists():
            return path

        if legacy_database is None:
            local_data = Path(
                os.environ.get("LOCALAPPDATA", Path.home())
            ) / "LigaPil" / "league_db.db"
            legacy_database = local_data
        bundled_dir = bundle_dir or getattr(sys, "_MEIPASS", None)
        candidates = [Path(legacy_database)]
        if bundled_dir:
            candidates.append(Path(bundled_dir) / "league_db.db")
        for candidate in candidates:
            if candidate.is_file():
                shutil.copy2(str(candidate), str(path))
                break
        return path
    return Path(__file__).resolve().parent.parent / "league_db.db"


DATABASE_PATH = _database_path()

SCHEMA = """
CREATE TABLE IF NOT EXISTS app_leagues (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL COLLATE NOCASE UNIQUE
);
CREATE TABLE IF NOT EXISTS app_teams (
    id INTEGER PRIMARY KEY,
    league_id INTEGER NOT NULL REFERENCES app_leagues(id) ON DELETE CASCADE,
    name TEXT NOT NULL COLLATE NOCASE,
    UNIQUE (league_id, name)
);
CREATE TABLE IF NOT EXISTS app_matches (
    id INTEGER PRIMARY KEY,
    league_id INTEGER NOT NULL REFERENCES app_leagues(id) ON DELETE CASCADE,
    round_number INTEGER NOT NULL,
    home_team_id INTEGER NOT NULL REFERENCES app_teams(id),
    away_team_id INTEGER NOT NULL REFERENCES app_teams(id),
    home_score INTEGER,
    away_score INTEGER,
    CHECK (home_team_id != away_team_id),
    CHECK (home_score IS NULL OR home_score >= 0),
    CHECK (away_score IS NULL OR away_score >= 0)
);
"""

MATCH_QUERY = """
SELECT m.id, m.round_number, m.home_score, m.away_score,
       home.name AS home_name, away.name AS away_name,
       m.home_team_id, m.away_team_id
FROM app_matches AS m
JOIN app_teams AS home ON home.id = m.home_team_id
JOIN app_teams AS away ON away.id = m.away_team_id
WHERE m.league_id = ?
ORDER BY m.round_number, m.id
"""


def connect_database(path=None):
    if path is None:
        path = _database_path()
    connection = sqlite3.connect(str(path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(SCHEMA)
    return connection


class SQLiteLeagueRepository:
    """Encapsulate SQL access; the application service does not issue SQL."""

    def __init__(self, connection):
        self.connection = connection

    def create_league(self, name, team_names, schedule):
        try:
            with self.connection:
                cursor = self.connection.execute(
                    "INSERT INTO app_leagues (name) VALUES (?)", (name,)
                )
                league_id = cursor.lastrowid
                team_ids = {}
                for team_name in team_names:
                    cursor = self.connection.execute(
                        "INSERT INTO app_teams (league_id, name) VALUES (?, ?)",
                        (league_id, team_name),
                    )
                    team_ids[team_name] = cursor.lastrowid
                for round_number, fixtures in enumerate(schedule, start=1):
                    for home, away in fixtures:
                        self.connection.execute(
                            """
                            INSERT INTO app_matches
                                (league_id, round_number, home_team_id, away_team_id)
                            VALUES (?, ?, ?, ?)
                            """,
                            (
                                league_id,
                                round_number,
                                team_ids[home],
                                team_ids[away],
                            ),
                        )
            return league_id
        except sqlite3.IntegrityError as error:
            if "app_leagues.name" in str(error):
                raise ValueError("Liga o takiej nazwie już istnieje.") from error
            raise

    def get_leagues(self):
        return self.connection.execute(
            "SELECT id, name FROM app_leagues ORDER BY name COLLATE NOCASE"
        ).fetchall()

    def get_league(self, league_id):
        return self.connection.execute(
            "SELECT id, name FROM app_leagues WHERE id = ?", (league_id,)
        ).fetchone()

    def get_teams(self, league_id):
        return self.connection.execute(
            "SELECT id, name FROM app_teams WHERE league_id = ? ORDER BY id",
            (league_id,),
        ).fetchall()

    def get_matches(self, league_id):
        return self.connection.execute(MATCH_QUERY, (league_id,)).fetchall()

    def set_result(self, match_id, home_score, away_score):
        with self.connection:
            cursor = self.connection.execute(
                "UPDATE app_matches SET home_score = ?, away_score = ? WHERE id = ?",
                (home_score, away_score, match_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("Nie znaleziono meczu.")

    def close(self):
        self.connection.close()
