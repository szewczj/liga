"""Application service coordinating validation, scheduling and persistence."""

from pathlib import Path

from .repository import DATABASE_PATH, SQLiteLeagueRepository, connect_database
from .schedule import RoundRobinScheduler


class LeagueService:
    def __init__(self, repository, scheduler=None):
        self.repository = repository
        self.scheduler = scheduler or RoundRobinScheduler()

    @classmethod
    def open(cls, path=DATABASE_PATH, scheduler=None):
        return cls(SQLiteLeagueRepository(connect_database(path)), scheduler)

    def create_league(self, name, team_names):
        if not name or not name.strip():
            raise ValueError("Nazwa ligi nie może być pusta.")
        if len(team_names) < 2:
            raise ValueError("Liga musi mieć co najmniej dwie drużyny.")
        cleaned_names = [team.strip() for team in team_names]
        if any(not team for team in cleaned_names):
            raise ValueError("Nazwa drużyny nie może być pusta.")
        if len({team.casefold() for team in cleaned_names}) != len(cleaned_names):
            raise ValueError("Nazwy drużyn w lidze muszą być unikalne.")
        schedule = self.scheduler.generate(cleaned_names)
        return self.repository.create_league(
            name.strip(), cleaned_names, schedule
        )

    def get_leagues(self):
        return self.repository.get_leagues()

    def get_league(self, league_id):
        return self.repository.get_league(league_id)

    def rename_league(self, league_id, name):
        if not name or not name.strip():
            raise ValueError("Nazwa ligi nie może być pusta.")
        self.repository.rename_league(league_id, name.strip())

    def delete_league(self, league_id):
        self.repository.delete_league(league_id)

    def clone_league(self, league_id, new_name):
        if not new_name or not new_name.strip():
            raise ValueError("Nazwa ligi nie może być pusta.")
        return self.repository.clone_league(league_id, new_name.strip())

    def get_teams(self, league_id):
        return self.repository.get_teams(league_id)

    def get_rounds(self, league_id):
        return self.repository.get_matches(league_id)

    def get_standings(self, league_id):
        teams = self.repository.get_teams(league_id)
        standings = {
            team["id"]: {
                "team_id": team["id"],
                "name": team["name"],
                "played": 0,
                "points": 0,
                "goals_for": 0,
                "goals_against": 0,
            }
            for team in teams
        }
        for match in self.repository.get_matches(league_id):
            home_score, away_score = match["home_score"], match["away_score"]
            if home_score is None or away_score is None:
                continue
            home = standings[match["home_team_id"]]
            away = standings[match["away_team_id"]]
            home["played"] += 1
            away["played"] += 1
            home["goals_for"] += home_score
            home["goals_against"] += away_score
            away["goals_for"] += away_score
            away["goals_against"] += home_score
            if home_score > away_score:
                home["points"] += 3
            elif home_score < away_score:
                away["points"] += 3
            else:
                home["points"] += 1
                away["points"] += 1
        return sorted(
            standings.values(),
            key=lambda team: (
                -team["points"],
                -(team["goals_for"] - team["goals_against"]),
                -team["goals_for"],
                team["name"].casefold(),
            ),
        )

    def record_result(self, match_id, home_score, away_score):
        if not isinstance(home_score, int) or not isinstance(away_score, int):
            raise ValueError("Wynik musi być liczbą całkowitą.")
        if home_score < 0 or away_score < 0:
            raise ValueError("Wynik nie może zawierać ujemnej liczby bramek.")
        self.repository.set_result(match_id, home_score, away_score)

    def export_league(self, league_id, path):
        from excel_export import export_league_to_excel

        league = self.repository.get_league(league_id)
        if league is None:
            raise ValueError("Nie znaleziono ligi.")
        return export_league_to_excel(
            Path(path),
            league["name"],
            self.get_teams(league_id),
            self.get_rounds(league_id),
        )

    def close(self):
        self.repository.close()
