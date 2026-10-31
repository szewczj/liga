"""Console interface; application rules are provided by LeagueService."""

from .repository import DATABASE_PATH
from .schedule import generate_schedule
from .service import LeagueService


def ask_integer(prompt, minimum, maximum=None):
    while True:
        try:
            number = int(input(prompt).strip())
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


class ConsoleLeagueApp:
    def __init__(self, service):
        self.service = service

    def run(self):
        while True:
            print("\n=== Liga piłkarska ===")
            print("1. Utwórz nową ligę")
            print("2. Otwórz istniejącą ligę")
            print("0. Zakończ")
            choice = input("Wybierz opcję: ").strip()
            if choice == "1":
                self.create_league()
            elif choice == "2":
                self.select_league()
            elif choice == "0":
                print("Do widzenia!")
                return
            else:
                print("Nieznana opcja.")

    def create_league(self):
        team_count = ask_integer("Podaj liczbę drużyn (minimum 2): ", 2)
        team_names = []
        while len(team_names) < team_count:
            name = input("Podaj nazwę drużyny {}: ".format(len(team_names) + 1)).strip()
            if not name:
                print("Nazwa drużyny nie może być pusta.")
            elif any(name.casefold() == team.casefold() for team in team_names):
                print("Ta nazwa drużyny została już podana.")
            else:
                team_names.append(name)

        while True:
            league_name = input("Podaj nazwę ligi: ").strip()
            try:
                league_id = self.service.create_league(league_name, team_names)
                break
            except ValueError as error:
                print(error)

        print(
            "Utworzono ligę „{}” ({} kolejek).".format(
                league_name, len(generate_schedule(team_names))
            )
        )
        self.open_league(self.service.get_league(league_id))

    def select_league(self):
        leagues = self.service.get_leagues()
        if not leagues:
            print("Nie ma jeszcze żadnej ligi.")
            return
        for index, league in enumerate(leagues, start=1):
            print("{}. {}".format(index, league["name"]))
        number = ask_integer("Wybierz ligę (0 - powrót): ", 0, len(leagues))
        if number:
            self.open_league(leagues[number - 1])

    def open_league(self, league):
        while True:
            print("\nLiga: {}".format(league["name"]))
            print("1. Tabela ligowa")
            print("2. Terminarz i wyniki kolejek")
            print("3. Wprowadź lub popraw wynik")
            print("4. Eksportuj ligę do Excela")
            print("5. Zarządzaj ligą")
            print("0. Powrót")
            choice = input("Wybierz opcję: ").strip()
            if choice == "1":
                self.print_standings(league["id"])
            elif choice == "2":
                self.print_fixtures(league["id"])
            elif choice == "3":
                self.enter_result(league["id"])
            elif choice == "4":
                self.export_league(league["id"])
            elif choice == "5":
                deleted = self.manage_league(league)
                if deleted:
                    return
                league = self.service.get_league(league["id"])
            elif choice == "0":
                return
            else:
                print("Nieznana opcja.")

    def print_standings(self, league_id):
        print("\nTabela ligowa")
        print(
            "{:<4} {:<24} {:>7} {:>8} {:>8} {:>8} {:>8}".format(
                "Lp.", "Drużyna", "Mecze", "Punkty", "Bramki+", "Bramki-", "RB"
            )
        )
        for position, team in enumerate(self.service.get_standings(league_id), 1):
            print(
                "{:<4} {:<24} {:>7} {:>8} {:>8} {:>8} {:>8}".format(
                    position,
                    team["name"][:24],
                    team["played"],
                    team["points"],
                    team["goals_for"],
                    team["goals_against"],
                    team["goal_difference"],
                )
            )

    def print_fixtures(self, league_id):
        matches = self.service.get_rounds(league_id)
        teams = self.service.get_teams(league_id)
        round_numbers = sorted({match["round_number"] for match in matches})
        for round_number in round_numbers:
            round_matches = [
                match for match in matches if match["round_number"] == round_number
            ]
            print("\nKolejka {}".format(round_number))
            playing = set()
            for index, match in enumerate(round_matches, 1):
                playing.update((match["home_team_id"], match["away_team_id"]))
                result = (
                    "do rozegrania"
                    if match["home_score"] is None
                    else "{} : {}".format(match["home_score"], match["away_score"])
                )
                print(
                    "  {}. {} - {} ({})".format(
                        index, match["home_name"], match["away_name"], result
                    )
                )
            byes = [team["name"] for team in teams if team["id"] not in playing]
            if byes:
                print("  Pauzuje: {}".format(", ".join(byes)))

    def enter_result(self, league_id):
        matches = self.service.get_rounds(league_id)
        round_numbers = sorted({match["round_number"] for match in matches})
        if not round_numbers:
            print("Brak zaplanowanych meczów.")
            return
        print("\nDostępne kolejki: {}".format(", ".join(map(str, round_numbers))))
        round_number = ask_integer("Wybierz kolejkę: ", 1, max(round_numbers))
        round_matches = [
            match for match in matches if match["round_number"] == round_number
        ]
        if not round_matches:
            print("Nie ma takiej kolejki.")
            return
        for index, match in enumerate(round_matches, 1):
            result = (
                "do rozegrania"
                if match["home_score"] is None
                else "{} : {}".format(match["home_score"], match["away_score"])
            )
            print(
                "{}. {} - {} ({})".format(
                    index, match["home_name"], match["away_name"], result
                )
            )
        match_number = ask_integer("Wybierz numer meczu: ", 1, len(round_matches))
        match = round_matches[match_number - 1]
        home_score = ask_integer(
            "Bramki drużyny {}: ".format(match["home_name"]), 0
        )
        away_score = ask_integer(
            "Bramki drużyny {}: ".format(match["away_name"]), 0
        )
        self.service.record_result(match["id"], home_score, away_score)
        print("Wynik został zapisany.")

    def export_league(self, league_id):
        path = input("Podaj ścieżkę pliku .xlsx (puste pole anuluje): ").strip()
        if not path:
            return
        try:
            exported = self.service.export_league(league_id, path)
        except (OSError, ValueError) as error:
            print("Nie udało się wyeksportować ligi: {}".format(error))
        else:
            print("Wyeksportowano ligę do pliku: {}".format(exported))

    def manage_league(self, league):
        while True:
            print("\nZarządzanie ligą: {}".format(league["name"]))
            print("1. Zmień nazwę ligi")
            print("2. Sklonuj ligę")
            print("3. Usuń ligę")
            print("4. Zmień nazwę drużyny")
            print("0. Powrót")
            choice = input("Wybierz opcję: ").strip()
            if choice == "1":
                name = input("Podaj nową nazwę ligi: ")
                try:
                    self.service.rename_league(league["id"], name)
                except ValueError as error:
                    print(error)
                else:
                    league = self.service.get_league(league["id"])
                    print("Nazwa ligi została zmieniona.")
            elif choice == "2":
                name = input(
                    "Podaj nazwę kopii ligi [{} (kopia)]: ".format(league["name"])
                ).strip()
                if not name:
                    name = league["name"] + " (kopia)"
                try:
                    self.service.clone_league(league["id"], name)
                except ValueError as error:
                    print(error)
                else:
                    print("Liga została sklonowana jako „{}”.".format(name))
            elif choice == "3":
                confirmation = input(
                    "Czy na pewno usunąć ligę „{}” wraz ze wszystkimi meczami "
                    "i wynikami? (wpisz TAK): ".format(league["name"])
                ).strip()
                if confirmation != "TAK":
                    print("Anulowano usuwanie ligi.")
                    continue
                try:
                    self.service.delete_league(league["id"])
                except ValueError as error:
                    print(error)
                    continue
                print("Liga została usunięta.")
                return True
            elif choice == "4":
                teams = self.service.get_teams(league["id"])
                for index, team in enumerate(teams, 1):
                    print("{}. {}".format(index, team["name"]))
                if not teams:
                    print("Liga nie zawiera drużyn.")
                    continue
                team_number = ask_integer(
                    "Wybierz drużynę (0 - powrót): ", 0, len(teams)
                )
                if not team_number:
                    continue
                team = teams[team_number - 1]
                name = input(
                    "Podaj nową nazwę drużyny [{}]: ".format(team["name"])
                )
                try:
                    self.service.rename_team(league["id"], team["id"], name)
                except ValueError as error:
                    print(error)
                else:
                    print("Nazwa drużyny została zmieniona.")
            elif choice == "0":
                return False
            else:
                print("Nieznana opcja.")


def main():
    service = LeagueService.open(DATABASE_PATH)
    try:
        ConsoleLeagueApp(service).run()
    finally:
        service.close()
