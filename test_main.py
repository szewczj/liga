import tempfile
import unittest
from pathlib import Path

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
            finally:
                connection.close()


if __name__ == "__main__":
    unittest.main()
