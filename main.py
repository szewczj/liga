"""Konsolowa aplikacja do prowadzenia lig piłkarskich (Python 3)."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


DATABASE_PATH = Path(__file__).with_name("league_db.db")


def generate_schedule(team_names: Sequence[str]) -> List[List[Tuple[str, str]]]:
    """Tworzy terminarz każdy z każdym metodą kołową."""
    if len(team_names) < 2:
        raise ValueError("Liga musi mieć co najmniej dwie drużyny.")

    rotation: List[Optional[str]] = list(team_names)
    if len(rotation) % 2:
        rotation.append(None)

    rounds: List[List[Tuple[str, str]]] = []
    for round_index in range(len(rotation) - 1):
        fixtures: List[Tuple[str, str]] = []
        for index in range(len(rotation) // 2):
            home = rotation[index]
            away = rotation[-index - 1]
            if home is not None and away is not None:
                # Zamiana gospodarza ogranicza przewagę gry u siebie.
                if round_index % 2:
                    home, away = away, home
                fixtures.append((home, away))
        rounds.append(fixtures)
        rotation = [rotation[0], rotation[-1]] + rotation[1:-1]

    return rounds


def connect_database(path: Path = DATABASE_PATH) -> sqlite3.Connection:
    connection = sqlite3.connect(str(path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(
        """
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
    )
    return connection


def create_league(
    connection: sqlite3.Connection, name: str, team_names: Sequence[str]
) -> int:
    if not name.strip():
        raise ValueError("Nazwa ligi nie może być pusta.")
    if len(team_names) < 2:
        raise ValueError("Liga musi mieć co najmniej dwie drużyny.")
    cleaned_names = [team.strip() for team in team_names]
    if any(not team for team in cleaned_names):
        raise ValueError("Nazwa drużyny nie może być pusta.")
    if len({team.casefold() for team in cleaned_names}) != len(cleaned_names):
        raise ValueError("Nazwy drużyn w lidze muszą być unikalne.")

    schedule = generate_schedule(cleaned_names)
    try:
        with connection:
            cursor = connection.execute(
                "INSERT INTO app_leagues (name) VALUES (?)", (name.strip(),)
            )
            league_id = cursor.lastrowid
            team_ids: Dict[str, int] = {}
            for team_name in cleaned_names:
                cursor = connection.execute(
                    "INSERT INTO app_teams (league_id, name) VALUES (?, ?)",
                    (league_id, team_name),
                )
                team_ids[team_name] = cursor.lastrowid

            for round_number, fixtures in enumerate(schedule, start=1):
                for home, away in fixtures:
                    connection.execute(
                        """
                        INSERT INTO app_matches
                            (league_id, round_number, home_team_id, away_team_id)
                        VALUES (?, ?, ?, ?)
                        """,
                        (league_id, round_number, team_ids[home], team_ids[away]),
                    )
        return league_id
    except sqlite3.IntegrityError as error:
        if "app_leagues.name" in str(error):
            raise ValueError("Liga o takiej nazwie już istnieje.") from error
        raise


def get_leagues(connection: sqlite3.Connection) -> List[sqlite3.Row]:
    return connection.execute(
        "SELECT id, name FROM app_leagues ORDER BY name COLLATE NOCASE"
    ).fetchall()


def get_standings(
    connection: sqlite3.Connection, league_id: int
) -> List[Dict[str, int]]:
    teams = connection.execute(
        "SELECT id, name FROM app_teams WHERE league_id = ?", (league_id,)
    ).fetchall()
    standings: Dict[int, Dict[str, int]] = {
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
    matches = connection.execute(
        """
        SELECT home_team_id, away_team_id, home_score, away_score
        FROM app_matches
        WHERE league_id = ? AND home_score IS NOT NULL AND away_score IS NOT NULL
        """,
        (league_id,),
    )
    for match in matches:
        home = standings[match["home_team_id"]]
        away = standings[match["away_team_id"]]
        home_score, away_score = match["home_score"], match["away_score"]
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


def get_rounds(
    connection: sqlite3.Connection, league_id: int
) -> List[sqlite3.Row]:
    return connection.execute(
        """
        SELECT m.id, m.round_number, m.home_score, m.away_score,
               home.name AS home_name, away.name AS away_name,
               m.home_team_id, m.away_team_id
        FROM app_matches AS m
        JOIN app_teams AS home ON home.id = m.home_team_id
        JOIN app_teams AS away ON away.id = m.away_team_id
        WHERE m.league_id = ?
        ORDER BY m.round_number, m.id
        """,
        (league_id,),
    ).fetchall()


def record_result(
    connection: sqlite3.Connection, match_id: int, home_score: int, away_score: int
) -> None:
    if home_score < 0 or away_score < 0:
        raise ValueError("Wynik nie może zawierać ujemnej liczby bramek.")
    with connection:
        cursor = connection.execute(
            "UPDATE app_matches SET home_score = ?, away_score = ? WHERE id = ?",
            (home_score, away_score, match_id),
        )
        if cursor.rowcount != 1:
            raise ValueError("Nie znaleziono meczu.")


def ask_integer(prompt: str, minimum: int, maximum: Optional[int] = None) -> int:
    while True:
        value = input(prompt).strip()
        try:
            number = int(value)
        except ValueError:
            print("Wpisz poprawną liczbę całkowitą.")
            continue
        if number < minimum or (maximum is not None and number > maximum):
            if maximum is None:
                print("Wartość musi wynosić co najmniej {}.".format(minimum))
            else:
                print("Wpisz liczbę od {} do {}.".format(minimum, maximum))
            continue
        return number


def print_standings(connection: sqlite3.Connection, league_id: int) -> None:
    rows = get_standings(connection, league_id)
    print("\nTabela ligowa")
    print("{:<4} {:<24} {:>7} {:>8} {:>8} {:>8}".format(
        "Lp.", "Drużyna", "Mecze", "Punkty", "Bramki+", "Bramki-"
    ))
    for position, team in enumerate(rows, start=1):
        print("{:<4} {:<24} {:>7} {:>8} {:>8} {:>8}".format(
            position, team["name"][:24], team["played"], team["points"],
            team["goals_for"], team["goals_against"]
        ))


def print_fixtures(connection: sqlite3.Connection, league_id: int) -> None:
    rounds = get_rounds(connection, league_id)
    team_rows = connection.execute(
        "SELECT id, name FROM app_teams WHERE league_id = ?", (league_id,)
    ).fetchall()
    team_names = {team["id"]: team["name"] for team in team_rows}
    round_numbers = sorted({match["round_number"] for match in rounds})
    for round_number in round_numbers:
        matches = [match for match in rounds if match["round_number"] == round_number]
        print("\nKolejka {}".format(round_number))
        playing = set()
        for index, match in enumerate(matches, start=1):
            playing.update((match["home_team_id"], match["away_team_id"]))
            if match["home_score"] is None:
                result = "do rozegrania"
            else:
                result = "{} : {}".format(match["home_score"], match["away_score"])
            print("  {}. {} - {} ({})".format(
                index, match["home_name"], match["away_name"], result
            ))
        byes = [team_names[team_id] for team_id in team_names if team_id not in playing]
        if byes:
            print("  Pauzuje: {}".format(", ".join(byes)))


def enter_result(connection: sqlite3.Connection, league_id: int) -> None:
    rounds = get_rounds(connection, league_id)
    round_numbers = sorted({match["round_number"] for match in rounds})
    if not round_numbers:
        print("Brak zaplanowanych meczów.")
        return
    print("\nDostępne kolejki: {}".format(", ".join(map(str, round_numbers))))
    round_number = ask_integer("Wybierz kolejkę: ", 1, max(round_numbers))
    matches = [match for match in rounds if match["round_number"] == round_number]
    if not matches:
        print("Nie ma takiej kolejki.")
        return

    for index, match in enumerate(matches, start=1):
        result = (
            "do rozegrania"
            if match["home_score"] is None
            else "{} : {}".format(match["home_score"], match["away_score"])
        )
        print("{}. {} - {} ({})".format(
            index, match["home_name"], match["away_name"], result
        ))
    match_number = ask_integer("Wybierz numer meczu: ", 1, len(matches))
    match = matches[match_number - 1]
    home_score = ask_integer("Bramki drużyny {}: ".format(match["home_name"]), 0)
    away_score = ask_integer("Bramki drużyny {}: ".format(match["away_name"]), 0)
    record_result(connection, match["id"], home_score, away_score)
    print("Wynik został zapisany.")


def open_league(connection: sqlite3.Connection, league: sqlite3.Row) -> None:
    while True:
        print("\nLiga: {}".format(league["name"]))
        print("1. Tabela ligowa")
        print("2. Terminarz i wyniki kolejek")
        print("3. Wprowadź lub popraw wynik")
        print("4. Eksportuj ligę do Excela")
        print("0. Powrót")
        choice = input("Wybierz opcję: ").strip()
        if choice == "1":
            print_standings(connection, league["id"])
        elif choice == "2":
            print_fixtures(connection, league["id"])
        elif choice == "3":
            enter_result(connection, league["id"])
        elif choice == "4":
            path = input("Podaj ścieżkę pliku .xlsx (puste pole anuluje): ").strip()
            if not path:
                continue
            teams = connection.execute(
                "SELECT id, name FROM app_teams WHERE league_id = ? ORDER BY id",
                (league["id"],),
            ).fetchall()
            try:
                from excel_export import export_league_to_excel

                exported = export_league_to_excel(
                    path, league["name"], teams, get_rounds(connection, league["id"])
                )
            except (OSError, ValueError) as error:
                print("Nie udało się wyeksportować ligi: {}".format(error))
            else:
                print("Wyeksportowano ligę do pliku: {}".format(exported))
        elif choice == "0":
            return
        else:
            print("Nieznana opcja.")


def create_league_from_prompt(connection: sqlite3.Connection) -> None:
    team_count = ask_integer("Podaj liczbę drużyn (minimum 2): ", 2)
    team_names: List[str] = []
    while len(team_names) < team_count:
        name = input("Podaj nazwę drużyny {}: ".format(len(team_names) + 1)).strip()
        if not name:
            print("Nazwa drużyny nie może być pusta.")
        elif any(name.casefold() == existing.casefold() for existing in team_names):
            print("Ta nazwa drużyny została już podana.")
        else:
            team_names.append(name)

    while True:
        league_name = input("Podaj nazwę ligi: ").strip()
        try:
            league_id = create_league(connection, league_name, team_names)
            break
        except ValueError as error:
            print(error)

    rounds_count = len(generate_schedule(team_names))
    print("Utworzono ligę „{}” ({} kolejek).".format(league_name, rounds_count))
    league = connection.execute(
        "SELECT id, name FROM app_leagues WHERE id = ?", (league_id,)
    ).fetchone()
    open_league(connection, league)


def select_league(connection: sqlite3.Connection) -> None:
    leagues = get_leagues(connection)
    if not leagues:
        print("Nie ma jeszcze żadnej ligi.")
        return
    for index, league in enumerate(leagues, start=1):
        print("{}. {}".format(index, league["name"]))
    number = ask_integer("Wybierz ligę (0 - powrót): ", 0, len(leagues))
    if number:
        open_league(connection, leagues[number - 1])


def main() -> None:
    connection = connect_database()
    try:
        while True:
            print("\n=== Liga piłkarska ===")
            print("1. Utwórz nową ligę")
            print("2. Otwórz istniejącą ligę")
            print("0. Zakończ")
            choice = input("Wybierz opcję: ").strip()
            if choice == "1":
                create_league_from_prompt(connection)
            elif choice == "2":
                select_league(connection)
            elif choice == "0":
                print("Do widzenia!")
                return
            else:
                print("Nieznana opcja.")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
