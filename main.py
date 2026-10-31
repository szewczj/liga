"""Console entry point and backwards-compatible league API."""

from league.cli import ConsoleLeagueApp, ask_integer, main
from league.repository import DATABASE_PATH, SQLiteLeagueRepository, connect_database
from league.schedule import generate_schedule
from league.service import LeagueService

__all__ = [
    "DATABASE_PATH",
    "ConsoleLeagueApp",
    "LeagueService",
    "SQLiteLeagueRepository",
    "ask_integer",
    "connect_database",
    "create_league",
    "create_league_from_prompt",
    "enter_result",
    "generate_schedule",
    "get_leagues",
    "get_rounds",
    "get_standings",
    "main",
    "open_league",
    "print_fixtures",
    "print_standings",
    "record_result",
    "select_league",
]


def _service_for(connection):
    return LeagueService(SQLiteLeagueRepository(connection))


def create_league(connection, name, team_names):
    return _service_for(connection).create_league(name, team_names)


def get_leagues(connection):
    return _service_for(connection).get_leagues()


def get_standings(connection, league_id):
    return _service_for(connection).get_standings(league_id)


def get_rounds(connection, league_id):
    return _service_for(connection).get_rounds(league_id)


def record_result(connection, match_id, home_score, away_score):
    return _service_for(connection).record_result(
        match_id, home_score, away_score
    )


def print_standings(connection, league_id):
    return ConsoleLeagueApp(_service_for(connection)).print_standings(league_id)


def print_fixtures(connection, league_id):
    return ConsoleLeagueApp(_service_for(connection)).print_fixtures(league_id)


def enter_result(connection, league_id):
    return ConsoleLeagueApp(_service_for(connection)).enter_result(league_id)


def open_league(connection, league):
    return ConsoleLeagueApp(_service_for(connection)).open_league(league)


def create_league_from_prompt(connection):
    return ConsoleLeagueApp(_service_for(connection)).create_league()


def select_league(connection):
    return ConsoleLeagueApp(_service_for(connection)).select_league()


if __name__ == "__main__":
    main()
