"""Tkinter application composed from layout, language and action mixins."""

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from .gui_dialogs import LeagueDialogsMixin
from .gui_language import LanguageMixin
from .gui_layout import LeagueLayoutMixin
from .gui_results import ResultEntryMixin
from .repository import DATABASE_PATH
from .service import LeagueService


class LeagueApp(
    LanguageMixin, LeagueLayoutMixin, LeagueDialogsMixin, ResultEntryMixin
):
    """Window controller coordinating the view and application service."""

    def __init__(self, root, service=None):
        self.root = root
        self.language = "pl"
        self.root.title(self.t("window_title"))
        icon_path = Path(__file__).resolve().parent.parent / "voxelowa_postac.png"
        self.app_icon = tk.PhotoImage(master=self.root, file=str(icon_path))
        self.root.iconphoto(True, self.app_icon)
        self.root.geometry("1150x700")
        self.service = service or LeagueService.open(DATABASE_PATH)
        self.leagues = []
        self.matches_by_id = {}
        self.saved_scores = {}
        self.save_buttons = {}
        self.score_entries = {}
        self.round_numbers = []
        self.current_round = 1
        self.round_mode = tk.StringVar(value="single")
        self.round_input_var = tk.StringVar(value="1")
        self.language_popup = None
        self.management_window = None
        self.team_name_editor = None

        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.create_flag_images()
        self.build_interface()
        self.update_language_widgets()
        self.refresh_leagues()

    def refresh_leagues(self, selected_id=None):
        self.leagues = self.service.get_leagues()
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
            self.manage_button.configure(state="disabled")
            self.clear_views()
        else:
            self.league_box.current(selected_index)
            self.manage_button.configure(state="normal")
            self.refresh_views()

    def selected_league(self):
        index = self.league_box.current()
        if index < 0 or index >= len(self.leagues):
            return None
        return self.leagues[index]

    def on_league_selected(self, _event=None):
        self.refresh_views()

    def clear_views(self):
        self.cancel_team_name_edit()
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
        matches = self.service.get_rounds(league["id"])
        teams = self.service.get_teams(league["id"])
        team_names = {team["id"]: team["name"] for team in teams}
        self.round_numbers = sorted(
            {match["round_number"] for match in matches}
        )
        if self.round_numbers:
            self.current_round = min(
                max(self.current_round, self.round_numbers[0]),
                self.round_numbers[-1],
            )
        else:
            self.current_round = 1
        self.round_input.configure(
            from_=self.round_numbers[0] if self.round_numbers else 1,
            to=self.round_numbers[-1] if self.round_numbers else 1,
        )
        self.round_input_var.set(str(self.current_round))
        single_round = self.round_mode.get() == "single"
        navigation_enabled = single_round and bool(self.round_numbers)
        self.previous_round_button.configure(
            state=(
                "normal"
                if navigation_enabled
                and self.current_round > self.round_numbers[0]
                else "disabled"
            )
        )
        self.next_round_button.configure(
            state=(
                "normal"
                if navigation_enabled
                and self.current_round < self.round_numbers[-1]
                else "disabled"
            )
        )
        self.round_input.configure(
            state="normal" if navigation_enabled else "disabled"
        )
        visible_rounds = self.round_numbers
        if single_round:
            visible_rounds = (
                [self.current_round]
                if self.current_round in self.round_numbers
                else []
            )
        for round_number in visible_rounds:
            self._render_round(
                round_number, matches, team_names, pending_scores
            )

    def _render_round(self, round_number, matches, team_names, pending_scores):
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
            self._render_match(round_frame, match, pending_scores)
        for team_id, team_name in team_names.items():
            if team_id not in playing:
                ttk.Label(
                    round_frame,
                    text=self.t("bye") + team_name,
                    foreground="#666666",
                ).pack(anchor="w", pady=2)

    def _render_match(self, parent, match, pending_scores):
        match_id = str(match["id"])
        match_frame = ttk.Frame(parent)
        match_frame.pack(fill="x", pady=2)
        ttk.Label(
            match_frame, text=match["home_name"], anchor="e", width=16
        ).pack(side="left", fill="x", expand=True)
        saved = (
            "" if match["home_score"] is None else str(match["home_score"]),
            "" if match["away_score"] is None else str(match["away_score"]),
        )
        current = pending_scores.get(match_id, saved)
        home_score_var = tk.StringVar(value=current[0])
        ttk.Entry(
            match_frame, textvariable=home_score_var, width=4, justify="center"
        ).pack(side="left", padx=(5, 2))
        ttk.Label(match_frame, text=":").pack(side="left")
        away_score_var = tk.StringVar(value=current[1])
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

    def refresh_standings(self, league_id):
        self.standings_tree.delete(*self.standings_tree.get_children())
        for position, team in enumerate(
            self.service.get_standings(league_id), start=1
        ):
            self.standings_tree.insert(
                "",
                "end",
                iid=str(team["team_id"]),
                values=(
                    position,
                    team["name"],
                    team["played"],
                    team["points"],
                    team["goals_for"],
                    team["goals_against"],
                    team["goal_difference"],
                ),
            )

    def on_standings_double_click(self, event):
        if self.standings_tree.identify_region(event.x, event.y) != "cell":
            return
        if self.standings_tree.identify_column(event.x) == "#2":
            team_id = self.standings_tree.identify_row(event.y)
            if team_id:
                self.start_team_name_edit(team_id)

    def rename_selected_team(self):
        selection = self.standings_tree.selection()
        if selection:
            self.start_team_name_edit(selection[0])

    def start_team_name_edit(self, team_id):
        self.cancel_team_name_edit()
        league = self.selected_league()
        if league is None:
            return
        item = self.standings_tree.item(team_id)
        if not item["values"]:
            return
        bounds = self.standings_tree.bbox(team_id, "team")
        if not bounds:
            return
        x, y, width, height = bounds
        editor = ttk.Entry(self.standings_tree)
        editor.insert(0, item["values"][1])
        editor.select_range(0, "end")
        editor.place(x=x, y=y, width=width, height=height)
        self.team_name_editor = (team_id, league["id"], editor)
        editor.bind("<Return>", self.commit_team_name_edit)
        editor.bind("<Escape>", self.cancel_team_name_edit)
        editor.bind("<FocusOut>", self.commit_team_name_edit)
        editor.focus_set()

    def commit_team_name_edit(self, _event=None):
        if self.team_name_editor is None:
            return "break"
        team_id, league_id, editor = self.team_name_editor
        name = editor.get()
        try:
            self.service.rename_team(league_id, int(team_id), name)
        except ValueError as error:
            messagebox.showerror(
                self.t("rename_team"), self.translate_core_error(error)
            )
            editor.after_idle(editor.focus_set)
            return "break"
        pending_scores = {
            match_id: (home.get(), away.get())
            for match_id, (home, away) in self.score_entries.items()
        }
        self.team_name_editor = None
        editor.destroy()
        self.refresh_views(pending_scores)
        return "break"

    def cancel_team_name_edit(self, _event=None):
        if self.team_name_editor is not None:
            _team_id, _league_id, editor = self.team_name_editor
            self.team_name_editor = None
            editor.destroy()
        return "break"

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

    def close(self):
        self.service.close()
        self.root.destroy()


def main():
    root = tk.Tk()
    LeagueApp(root)
    root.mainloop()
