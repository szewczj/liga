"""Graficzny interfejs do prowadzenia lig piłkarskich (Python 3)."""

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from main import (
    connect_database,
    create_league,
    get_leagues,
    get_rounds,
    get_standings,
    record_result,
)
from excel_export import export_league_to_excel

TRANSLATIONS = {
    "pl": {
        "window_title": "Liga piłkarska",
        "league": "Liga:",
        "create_league": "Utwórz ligę",
        "refresh": "Odśwież",
        "export_excel": "Eksportuj do Excela",
        "export_title": "Eksport ligi do Excela",
        "export_success": "Skoroszyt zapisano w pliku:\n{}",
        "export_error": "Nie udało się wyeksportować ligi",
        "standings": "Tabela ligowa",
        "fixtures": "Kolejki i wyniki — wpisz wynik przy meczu",
        "position": "Lp.",
        "team": "Drużyna",
        "played": "M",
        "points": "Pkt",
        "goals_for": "B+",
        "goals_against": "B-",
        "all_rounds": "Wszystkie kolejki",
        "single_round": "Pojedyncza kolejka",
        "previous": "Poprzednia",
        "next": "Następna",
        "show": "Pokaż",
        "round": "Kolejka {}",
        "save": "Zapisz",
        "bye": "Pauzuje: ",
        "new_league": "Nowa liga",
        "team_count_prompt": "Podaj liczbę drużyn (minimum 2):",
        "team_name_prompt": "Podaj nazwę drużyny {} z {}:",
        "league_name_prompt": "Podaj nazwę ligi:",
        "invalid_name": "Nieprawidłowa nazwa",
        "empty_team": "Nazwa drużyny nie może być pusta.",
        "duplicate_name": "Powtórzona nazwa",
        "unique_teams": "Nazwy drużyn muszą być unikalne.",
        "create_error": "Nie można utworzyć ligi",
        "league_created": "Liga utworzona",
        "created_rounds": "Utworzono ligę z terminarzem na {} kolejek.",
        "invalid_round": "Nieprawidłowa kolejka",
        "round_integer": "Wpisz numer kolejki jako liczbę całkowitą.",
        "round_range": "Wpisz numer od {} do {}.",
        "missing_match": "Brak meczu",
        "match_not_found": "Nie znaleziono wybranego meczu.",
        "invalid_score": "Nieprawidłowy wynik",
        "score_nonnegative": "Podaj nieujemne liczby całkowite dla obu drużyn.",
        "save_error": "Nie można zapisać wyniku",
        "error_empty_league": "Nazwa ligi nie może być pusta.",
        "error_min_teams": "Liga musi mieć co najmniej dwie drużyny.",
        "error_duplicate_team": "Nazwy drużyn w lidze muszą być unikalne.",
        "error_duplicate_league": "Liga o takiej nazwie już istnieje.",
    },
    "en": {
        "window_title": "Football League",
        "league": "League:",
        "create_league": "Create league",
        "refresh": "Refresh",
        "export_excel": "Export to Excel",
        "export_title": "Export league to Excel",
        "export_success": "Workbook saved to:\n{}",
        "export_error": "Could not export league",
        "standings": "League table",
        "fixtures": "Rounds and results — enter scores beside each match",
        "position": "Pos.",
        "team": "Team",
        "played": "P",
        "points": "Pts",
        "goals_for": "GF",
        "goals_against": "GA",
        "all_rounds": "All rounds",
        "single_round": "Single round",
        "previous": "Previous",
        "next": "Next",
        "show": "Show",
        "round": "Round {}",
        "save": "Save",
        "bye": "Bye: ",
        "new_league": "New league",
        "team_count_prompt": "Enter the number of teams (minimum 2):",
        "team_name_prompt": "Enter the name of team {} of {}:",
        "league_name_prompt": "Enter the league name:",
        "invalid_name": "Invalid name",
        "empty_team": "Team name cannot be empty.",
        "duplicate_name": "Duplicate name",
        "unique_teams": "Team names must be unique.",
        "create_error": "Could not create league",
        "league_created": "League created",
        "created_rounds": "League created with a {}-round schedule.",
        "invalid_round": "Invalid round",
        "round_integer": "Enter the round number as a whole number.",
        "round_range": "Enter a number from {} to {}.",
        "missing_match": "No match",
        "match_not_found": "The selected match could not be found.",
        "invalid_score": "Invalid score",
        "score_nonnegative": "Enter non-negative whole numbers for both teams.",
        "save_error": "Could not save result",
        "error_empty_league": "League name cannot be empty.",
        "error_min_teams": "A league must have at least two teams.",
        "error_duplicate_team": "Team names in a league must be unique.",
        "error_duplicate_league": "A league with this name already exists.",
    },
}


class LeagueApp:
    def __init__(self, root):
        self.root = root
        self.language = "pl"
        self.root.title(self.t("window_title"))
        self.app_icon = tk.PhotoImage(
            master=self.root, file=str(Path(__file__).with_name("voxelowa_postac.png"))
        )
        self.root.iconphoto(True, self.app_icon)
        self.root.geometry("1150x700")
        self.connection = connect_database()
        self.leagues = []
        self.matches_by_id = {}
        self.saved_scores = {}
        self.save_buttons = {}
        self.round_numbers = []
        self.current_round = 1
        self.round_mode = tk.StringVar(value="single")
        self.round_input_var = tk.StringVar(value="1")
        self.language_popup = None
        self._create_flag_images()

        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self._build_interface()
        self.update_language_widgets()
        self.refresh_leagues()

    def t(self, key, *args):
        text = TRANSLATIONS[self.language][key]
        return text.format(*args) if args else text

    def _create_flag_images(self):
        self.polish_flag = tk.PhotoImage(width=24, height=16)
        self.polish_flag.put("#ffffff", to=(0, 0, 24, 8))
        self.polish_flag.put("#dc143c", to=(0, 8, 24, 16))

        self.uk_flag = tk.PhotoImage(width=24, height=16)
        for y in range(16):
            for x in range(24):
                diagonal_distance = min(
                    abs(y * 23 - x * 15), abs(y * 23 - (15 - x) * 15)
                )
                color = "#012169"
                if diagonal_distance <= 46:
                    color = "#ffffff"
                if diagonal_distance <= 18:
                    color = "#c8102e"
                if 5 <= y <= 10 or 9 <= x <= 14:
                    color = "#ffffff"
                if 7 <= y <= 8 or 11 <= x <= 12:
                    color = "#c8102e"
                self.uk_flag.put(color, to=(x, y))

    def update_language_widgets(self):
        self.root.title(self.t("window_title"))
        self.league_label.configure(text=self.t("league"))
        self.create_league_button.configure(text=self.t("create_league"))
        self.refresh_button.configure(text=self.t("refresh"))
        self.export_button.configure(text=self.t("export_excel"))
        self.standings_panel.configure(text=self.t("standings"))
        self.fixtures_panel.configure(text=self.t("fixtures"))
        for column, key in (
            ("position", "position"),
            ("team", "team"),
            ("played", "played"),
            ("points", "points"),
            ("gf", "goals_for"),
            ("ga", "goals_against"),
        ):
            self.standings_tree.heading(column, text=self.t(key))
        self.all_rounds_button.configure(text=self.t("all_rounds"))
        self.single_round_button.configure(text=self.t("single_round"))
        self.previous_round_button.configure(text=self.t("previous"))
        self.next_round_button.configure(text=self.t("next"))
        self.show_round_button.configure(text=self.t("show"))
        self.language_button.configure(
            text="polski ▼" if self.language == "pl" else "english ▼",
            image=self.polish_flag if self.language == "pl" else self.uk_flag,
            compound="left",
        )

    def set_language(self, language):
        if language == self.language:
            return
        pending_scores = {
            match_id: (home.get(), away.get())
            for match_id, (home, away) in self.score_entries.items()
        }
        self.language = language
        self.update_language_widgets()
        self.refresh_views(pending_scores)

    def show_language_options(self):
        if self.language_popup is not None and self.language_popup.winfo_exists():
            self.close_language_options()
            return

        popup = tk.Toplevel(self.root)
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
        self.language_popup = popup
        options = ttk.Frame(popup, relief="solid", borderwidth=1)
        options.pack()
        self.language_option_buttons = {}
        for language, label, flag in (
            ("pl", "polski", self.polish_flag),
            ("en", "english", self.uk_flag),
        ):
            button = ttk.Button(
                options,
                text=label,
                image=flag,
                compound="left",
                command=lambda selected=language: self.select_language_option(
                    selected
                ),
            )
            button.pack(fill="x")
            self.language_option_buttons[language] = button
        popup.bind("<Escape>", lambda _event: self.close_language_options())
        popup.update_idletasks()
        x = self.language_button.winfo_rootx()
        y = self.language_button.winfo_rooty() + self.language_button.winfo_height()
        x = min(x, popup.winfo_screenwidth() - popup.winfo_width())
        y = min(y, popup.winfo_screenheight() - popup.winfo_height())
        popup.geometry("+{}+{}".format(max(0, x), max(0, y)))
        popup.lift()
        popup.focus_force()

    def select_language_option(self, language):
        self.close_language_options()
        self.set_language(language)

    def close_language_options(self):
        if self.language_popup is not None:
            if self.language_popup.winfo_exists():
                self.language_popup.destroy()
            self.language_popup = None

    def translate_core_error(self, error):
        translations = {
            "Nazwa ligi nie może być pusta.": "error_empty_league",
            "Liga musi mieć co najmniej dwie drużyny.": "error_min_teams",
            "Nazwy drużyn w lidze muszą być unikalne.": "error_duplicate_team",
            "Liga o takiej nazwie już istnieje.": "error_duplicate_league",
        }
        key = translations.get(str(error))
        return self.t(key) if key else str(error)

    def _build_interface(self):
        header = ttk.Frame(self.root, padding=12)
        header.pack(fill="x")
        self.league_label = ttk.Label(header)
        self.league_label.pack(side="left")
        self.league_var = tk.StringVar()
        self.league_box = ttk.Combobox(
            header, textvariable=self.league_var, state="readonly", width=35
        )
        self.league_box.pack(side="left", padx=(8, 12))
        self.league_box.bind("<<ComboboxSelected>>", self.on_league_selected)
        self.create_league_button = ttk.Button(
            header, command=self.create_league_dialog
        )
        self.create_league_button.pack(side="left")
        self.refresh_button = ttk.Button(header, command=self.refresh_leagues)
        self.refresh_button.pack(side="left", padx=8)
        self.export_button = ttk.Button(
            header, command=self.export_selected_league
        )
        self.export_button.pack(side="left")
        self.language_button = ttk.Button(header, command=self.show_language_options)
        self.language_button.pack(side="right")

        content = ttk.Panedwindow(self.root, orient="horizontal")
        content.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.standings_panel = ttk.LabelFrame(content, padding=10)
        self.fixtures_panel = ttk.LabelFrame(content, padding=10)
        content.add(self.standings_panel, weight=1)
        content.add(self.fixtures_panel, weight=2)

        self.standings_tree = ttk.Treeview(
            self.standings_panel,
            columns=("position", "team", "played", "points", "gf", "ga"),
            show="headings",
        )
        standings_columns = (
            ("position", 42, "center"),
            ("team", 160, "w"),
            ("played", 40, "center"),
            ("points", 45, "center"),
            ("gf", 40, "center"),
            ("ga", 40, "center"),
        )
        for column, width, anchor in standings_columns:
            self.standings_tree.column(column, width=width, anchor=anchor)
        self.standings_tree.pack(fill="both", expand=True)

        round_controls = ttk.Frame(self.fixtures_panel)
        round_controls.pack(fill="x", pady=(0, 8))
        self.all_rounds_button = ttk.Radiobutton(
            round_controls,
            variable=self.round_mode,
            value="all",
            command=self.refresh_views,
        )
        self.all_rounds_button.pack(side="left")
        self.single_round_button = ttk.Radiobutton(
            round_controls,
            variable=self.round_mode,
            value="single",
            command=self.refresh_views,
        )
        self.single_round_button.pack(side="left", padx=(8, 16))
        self.previous_round_button = ttk.Button(
            round_controls, command=lambda: self.change_round(-1)
        )
        self.previous_round_button.pack(side="left")
        self.round_input = ttk.Spinbox(
            round_controls,
            from_=1,
            to=1,
            textvariable=self.round_input_var,
            width=5,
            justify="center",
        )
        self.round_input.pack(side="left", padx=5)
        self.round_input.bind("<Return>", self.show_entered_round)
        self.show_round_button = ttk.Button(
            round_controls, command=self.show_entered_round
        )
        self.show_round_button.pack(side="left")
        self.next_round_button = ttk.Button(
            round_controls, command=lambda: self.change_round(1)
        )
        self.next_round_button.pack(side="left", padx=(5, 0))

        rounds_container = ttk.Frame(self.fixtures_panel)
        rounds_container.pack(fill="both", expand=True)
        self.rounds_canvas = tk.Canvas(rounds_container, highlightthickness=0)
        rounds_scrollbar = ttk.Scrollbar(
            rounds_container, orient="vertical", command=self.rounds_canvas.yview
        )
        self.rounds_canvas.configure(yscrollcommand=rounds_scrollbar.set)
        rounds_scrollbar.pack(side="right", fill="y")
        self.rounds_canvas.pack(side="left", fill="both", expand=True)
        self.rounds_frame = ttk.Frame(self.rounds_canvas)
        self.rounds_window = self.rounds_canvas.create_window(
            (0, 0), window=self.rounds_frame, anchor="nw"
        )
        self.rounds_frame.bind(
            "<Configure>",
            lambda _event: self.rounds_canvas.configure(
                scrollregion=self.rounds_canvas.bbox("all")
            ),
        )
        self.rounds_canvas.bind(
            "<Configure>",
            lambda event: self.rounds_canvas.itemconfigure(
                self.rounds_window, width=event.width
            ),
        )
        self.score_entries = {}

    def refresh_leagues(self, selected_id=None):
        self.leagues = get_leagues(self.connection)
        self.league_box["values"] = [league["name"] for league in self.leagues]
        selected_index = next(
            (
                index
                for index, league in enumerate(self.leagues)
                if league["id"] == selected_id
            ),
            0 if self.leagues else None,
        )
        if selected_index is None:
            self.league_var.set("")
            self.clear_views()
        else:
            self.league_box.current(selected_index)
            self.refresh_views()

    def selected_league(self):
        index = self.league_box.current()
        if index < 0 or index >= len(self.leagues):
            return None
        return self.leagues[index]

    def on_league_selected(self, _event=None):
        self.refresh_views()

    def clear_views(self):
        self.standings_tree.delete(*self.standings_tree.get_children())
        for child in self.rounds_frame.winfo_children():
            child.destroy()
        self.matches_by_id.clear()
        self.saved_scores.clear()
        self.save_buttons.clear()
        self.score_entries.clear()

    def refresh_views(self, pending_scores=None):
        if pending_scores is None:
            pending_scores = {
                match_id: (home.get(), away.get())
                for match_id, (home, away) in self.score_entries.items()
            }
        league = self.selected_league()
        self.clear_views()
        if league is None:
            return

        self.refresh_standings(league["id"])

        matches = get_rounds(self.connection, league["id"])
        teams = self.connection.execute(
            "SELECT id, name FROM app_teams WHERE league_id = ? ORDER BY name",
            (league["id"],),
        ).fetchall()
        team_names = {team["id"]: team["name"] for team in teams}
        round_numbers = sorted({match["round_number"] for match in matches})
        self.round_numbers = round_numbers
        if round_numbers:
            self.current_round = min(
                max(self.current_round, round_numbers[0]), round_numbers[-1]
            )
        else:
            self.current_round = 1
        self.round_input.configure(
            from_=round_numbers[0] if round_numbers else 1,
            to=round_numbers[-1] if round_numbers else 1,
        )
        self.round_input_var.set(str(self.current_round))
        single_round = self.round_mode.get() == "single"
        navigation_enabled = single_round and bool(round_numbers)
        self.previous_round_button.configure(
            state=(
                "normal"
                if navigation_enabled and self.current_round > round_numbers[0]
                else "disabled"
            )
        )
        self.next_round_button.configure(
            state=(
                "normal"
                if navigation_enabled and self.current_round < round_numbers[-1]
                else "disabled"
            )
        )
        controls_state = "normal" if navigation_enabled else "disabled"
        self.round_input.configure(state=controls_state)
        if single_round:
            round_numbers = (
                [self.current_round] if self.current_round in round_numbers else []
            )
        for round_number in round_numbers:
            round_matches = [
                match for match in matches if match["round_number"] == round_number
            ]
            playing = set()
            round_frame = ttk.LabelFrame(
                self.rounds_frame,
                text=self.t("round", round_number),
                padding=6,
            )
            round_frame.pack(fill="x", pady=(0, 8))
            for match in round_matches:
                playing.update((match["home_team_id"], match["away_team_id"]))
                match_id = str(match["id"])
                match_frame = ttk.Frame(round_frame)
                match_frame.pack(fill="x", pady=2)
                ttk.Label(
                    match_frame, text=match["home_name"], anchor="e", width=16
                ).pack(side="left", fill="x", expand=True)
                home_score_var = tk.StringVar(
                    value=pending_scores.get(
                        match_id,
                        (
                            "" if match["home_score"] is None else str(match["home_score"]),
                            "" if match["away_score"] is None else str(match["away_score"]),
                        ),
                    )[0]
                )
                ttk.Entry(
                    match_frame, textvariable=home_score_var, width=4, justify="center"
                ).pack(side="left", padx=(5, 2))
                ttk.Label(match_frame, text=":").pack(side="left")
                away_score_var = tk.StringVar(
                    value=pending_scores.get(
                        match_id,
                        (
                            "" if match["home_score"] is None else str(match["home_score"]),
                            "" if match["away_score"] is None else str(match["away_score"]),
                        ),
                    )[1]
                )
                ttk.Entry(
                    match_frame, textvariable=away_score_var, width=4, justify="center"
                ).pack(side="left", padx=(2, 5))
                ttk.Label(
                    match_frame, text=match["away_name"], anchor="w", width=16
                ).pack(side="left", fill="x", expand=True)
                save_button = ttk.Button(
                    match_frame,
                    text=self.t("save"),
                    command=lambda mid=match_id: self.save_result(mid),
                )
                save_button.pack(side="left", padx=(5, 0))
                self.score_entries[match_id] = (home_score_var, away_score_var)
                self.saved_scores[match_id] = (
                    match["home_score"],
                    match["away_score"],
                )
                self.save_buttons[match_id] = save_button
                home_score_var.trace_add(
                    "write", lambda *_args, mid=match_id: self.update_save_button(mid)
                )
                away_score_var.trace_add(
                    "write", lambda *_args, mid=match_id: self.update_save_button(mid)
                )
                self.update_save_button(match_id)
                self.matches_by_id[match_id] = match
            byes = [
                team_names[team_id]
                for team_id in team_names
                if team_id not in playing
            ]
            for team_name in byes:
                ttk.Label(
                    round_frame,
                    text=self.t("bye") + team_name,
                    foreground="#666666",
                ).pack(anchor="w", pady=2)

    def refresh_standings(self, league_id):
        self.standings_tree.delete(*self.standings_tree.get_children())
        for position, team in enumerate(
            get_standings(self.connection, league_id), start=1
        ):
            self.standings_tree.insert(
                "",
                "end",
                values=(
                    position,
                    team["name"],
                    team["played"],
                    team["points"],
                    team["goals_for"],
                    team["goals_against"],
                ),
            )

    def update_save_button(self, match_id):
        if match_id not in self.score_entries or match_id not in self.save_buttons:
            return
        saved = self.saved_scores.get(match_id)
        home_var, away_var = self.score_entries[match_id]
        home_text, away_text = home_var.get().strip(), away_var.get().strip()
        enabled = bool(home_text and away_text)
        if enabled:
            try:
                entered = (int(home_text), int(away_text))
                if entered[0] < 0 or entered[1] < 0:
                    enabled = True
                else:
                    enabled = entered != saved
            except ValueError:
                enabled = True
        self.save_buttons[match_id].configure(
            state="normal" if enabled else "disabled"
        )

    def change_round(self, offset):
        if not self.round_numbers:
            return
        self.current_round = min(
            max(self.current_round + offset, self.round_numbers[0]),
            self.round_numbers[-1],
        )
        self.refresh_views()

    def show_entered_round(self, _event=None):
        if not self.round_numbers:
            return
        try:
            round_number = int(self.round_input_var.get().strip())
        except ValueError:
            messagebox.showerror(
                self.t("invalid_round"), self.t("round_integer")
            )
            self.round_input_var.set(str(self.current_round))
            return
        if round_number not in self.round_numbers:
            messagebox.showerror(
                self.t("invalid_round"),
                self.t("round_range").format(
                    self.round_numbers[0], self.round_numbers[-1]
                ),
            )
            self.round_input_var.set(str(self.current_round))
            return
        self.current_round = round_number
        self.round_mode.set("single")
        self.refresh_views()

    def create_league_dialog(self):
        team_count = simpledialog.askinteger(
            self.t("new_league"),
            self.t("team_count_prompt"),
            parent=self.root,
            minvalue=2,
        )
        if team_count is None:
            return

        team_names = []
        for index in range(team_count):
            while True:
                name = simpledialog.askstring(
                    self.t("new_league"),
                    self.t("team_name_prompt").format(index + 1, team_count),
                    parent=self.root,
                )
                if name is None:
                    return
                name = name.strip()
                if not name:
                    messagebox.showerror(
                        self.t("invalid_name"), self.t("empty_team")
                    )
                elif any(name.casefold() == team.casefold() for team in team_names):
                    messagebox.showerror(
                        self.t("duplicate_name"), self.t("unique_teams")
                    )
                else:
                    team_names.append(name)
                    break

        while True:
            name = simpledialog.askstring(
                self.t("new_league"), self.t("league_name_prompt"), parent=self.root
            )
            if name is None:
                return
            try:
                league_id = create_league(self.connection, name, team_names)
                break
            except ValueError as error:
                messagebox.showerror(
                    self.t("create_error"), self.translate_core_error(error)
                )

        self.refresh_leagues(league_id)
        messagebox.showinfo(
            self.t("league_created"),
            self.t("created_rounds").format(
                (team_count if team_count % 2 else team_count - 1)
            ),
        )

    def export_selected_league(self):
        league = self.selected_league()
        if league is None:
            return
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title=self.t("export_title"),
            defaultextension=".xlsx",
            initialfile="liga.xlsx",
            filetypes=(("Excel (*.xlsx)", "*.xlsx"),),
        )
        if not path:
            return
        teams = self.connection.execute(
            "SELECT id, name FROM app_teams WHERE league_id = ? ORDER BY id",
            (league["id"],),
        ).fetchall()
        matches = get_rounds(self.connection, league["id"])
        try:
            exported_path = export_league_to_excel(
                path, league["name"], teams, matches
            )
        except (OSError, ValueError) as error:
            messagebox.showerror(self.t("export_error"), str(error))
            return
        messagebox.showinfo(
            self.t("export_title"),
            self.t("export_success").format(exported_path),
        )

    def save_result(self, match_id):
        if match_id not in self.matches_by_id or match_id not in self.score_entries:
            messagebox.showerror(
                self.t("missing_match"), self.t("match_not_found")
            )
            return
        try:
            home_score_var, away_score_var = self.score_entries[match_id]
            home_score = int(home_score_var.get().strip())
            away_score = int(away_score_var.get().strip())
            if home_score < 0 or away_score < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror(
                self.t("invalid_score"), self.t("score_nonnegative")
            )
            return

        match = self.matches_by_id[match_id]
        try:
            record_result(self.connection, match["id"], home_score, away_score)
        except ValueError as error:
            messagebox.showerror(
                self.t("save_error"), self.translate_core_error(error)
            )
            return
        self.saved_scores[match_id] = (home_score, away_score)
        self.update_save_button(match_id)
        league = self.selected_league()
        if league is not None:
            self.refresh_standings(league["id"])

    def close(self):
        self.connection.close()
        self.root.destroy()


def main():
    root = tk.Tk()
    LeagueApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
