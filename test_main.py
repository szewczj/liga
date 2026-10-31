import tempfile
import unittest
from pathlib import Path

from league.repository import SQLiteLeagueRepository
from league.service import LeagueService
from main import connect_database, create_league, generate_schedule, get_standings, record_result


class ScheduleTests(unittest.TestCase):
    def assert_valid_schedule(self, team_names, expected_rounds):
        schedule = generate_schedule(team_names)
        self.assertEqual(len(schedule), expected_rounds)
        expected_pairs = {
            frozenset((team_names[first], team_names[second]))
            for first in range(len(team_names))
            for second in range(first + 1, len(team_names))
        }
        actual_pairs = []
        for round_fixtures in schedule:
            playing = []
            for home, away in round_fixtures:
                playing.extend((home, away))
                actual_pairs.append(frozenset((home, away)))
            self.assertEqual(len(playing), len(set(playing)))
            self.assertLessEqual(len(playing), len(team_names))
        self.assertEqual(len(actual_pairs), len(expected_pairs))
        self.assertEqual(set(actual_pairs), expected_pairs)

    def test_even_number_of_teams(self):
        self.assert_valid_schedule(["Orły", "Lisy", "Wilki", "Sowy"], 3)

    def test_odd_number_of_teams_has_one_bye_each_round(self):
        teams = ["Orły", "Lisy", "Wilki", "Sowy", "Rysie"]
        schedule = generate_schedule(teams)
        self.assert_valid_schedule(teams, 5)
        for fixtures in schedule:
            self.assertEqual(len(fixtures), 2)

    def test_league_results_update_standings(self):
        with tempfile.TemporaryDirectory() as directory:
            connection = connect_database(Path(directory) / "league.db")
            try:
                league_id = create_league(connection, "Testowa liga", ["Orły", "Lisy", "Wilki"])
                match = connection.execute(
                    """
                    SELECT id FROM app_matches
                    WHERE league_id = ? AND round_number = 1
                    """,
                    (league_id,),
                ).fetchone()
                record_result(connection, match["id"], 2, 1)

                standings = get_standings(connection, league_id)
                self.assertEqual(sum(team["played"] for team in standings), 2)
                self.assertEqual(sorted(team["points"] for team in standings), [0, 0, 3])
                self.assertEqual(sum(team["goals_for"] for team in standings), 3)
                self.assertEqual(sum(team["goals_against"] for team in standings), 3)
                self.assertEqual(
                    sum(team["goal_difference"] for team in standings), 0
                )
            finally:
                connection.close()

    def test_rename_team_updates_fixtures_and_rejects_duplicate_or_empty_name(self):
        with tempfile.TemporaryDirectory() as directory:
            connection = connect_database(Path(directory) / "league.db")
            try:
                service = LeagueService(SQLiteLeagueRepository(connection))
                league_id = service.create_league(
                    "Testowa liga", ["Orły", "Lisy", "Wilki"]
                )
                team = service.get_teams(league_id)[0]
                service.rename_team(league_id, team["id"], "Jastrzębie")
                self.assertEqual(
                    {match["home_name"] for match in service.get_rounds(league_id)}
                    | {match["away_name"] for match in service.get_rounds(league_id)},
                    {"Jastrzębie", "Lisy", "Wilki"},
                )
                match = service.get_rounds(league_id)[0]
                service.record_result(match["id"], 2, 0)
                standings = {
                    row["team_id"]: row for row in service.get_standings(league_id)
                }
                self.assertEqual(
                    standings[match["home_team_id"]]["goal_difference"], 2
                )
                self.assertEqual(
                    standings[match["away_team_id"]]["goal_difference"], -2
                )
                with self.assertRaises(ValueError):
                    service.rename_team(league_id, team["id"], "Lisy")
                with self.assertRaises(ValueError):
                    service.rename_team(league_id, team["id"], "   ")
                self.assertEqual(
                    service.get_teams(league_id)[0]["name"], "Jastrzębie"
                )
            finally:
                connection.close()

    def test_clone_copies_teams_schedule_and_results_without_sharing_records(self):
        with tempfile.TemporaryDirectory() as directory:
            connection = connect_database(Path(directory) / "league.db")
            try:
                service = LeagueService(SQLiteLeagueRepository(connection))
                original_id = service.create_league(
                    "Oryginał", ["Orły", "Lisy", "Wilki"]
                )
                original_matches = service.get_rounds(original_id)
                service.record_result(original_matches[0]["id"], 3, 2)
                original_matches = service.get_rounds(original_id)

                clone_id = service.clone_league(original_id, "Kopia")
                clone_matches = service.get_rounds(clone_id)

                self.assertEqual(
                    [team["name"] for team in service.get_teams(clone_id)],
                    [team["name"] for team in service.get_teams(original_id)],
                )
                self.assertEqual(len(clone_matches), len(original_matches))
                self.assertEqual(
                    [
                        (
                            match["round_number"],
                            match["home_name"],
                            match["away_name"],
                            match["home_score"],
                            match["away_score"],
                        )
                        for match in clone_matches
                    ],
                    [
                        (
                            match["round_number"],
                            match["home_name"],
                            match["away_name"],
                            match["home_score"],
                            match["away_score"],
                        )
                        for match in original_matches
                    ],
                )
                self.assertNotEqual(clone_matches[0]["id"], original_matches[0]["id"])
                service.record_result(clone_matches[0]["id"], 0, 0)
                self.assertEqual(
                    service.get_rounds(original_id)[0]["home_score"], 3
                )
            finally:
                connection.close()

    def test_rename_and_delete_are_scoped_to_selected_league(self):
        with tempfile.TemporaryDirectory() as directory:
            connection = connect_database(Path(directory) / "league.db")
            try:
                service = LeagueService(SQLiteLeagueRepository(connection))
                first_id = service.create_league("Pierwsza", ["A", "B"])
                second_id = service.create_league("Druga", ["C", "D"])
                service.rename_league(first_id, "Nowa nazwa")
                self.assertEqual(service.get_league(first_id)["name"], "Nowa nazwa")
                with self.assertRaises(ValueError):
                    service.rename_league(first_id, "Druga")

                service.delete_league(first_id)
                self.assertIsNone(service.get_league(first_id))
                self.assertEqual(service.get_league(second_id)["name"], "Druga")
                self.assertEqual(len(service.get_teams(second_id)), 2)
            finally:
                connection.close()


if __name__ == "__main__":
    unittest.main()
