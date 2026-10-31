"""Language selection and translated Tkinter labels."""

import tkinter as tk
from tkinter import ttk

from .translations import TRANSLATIONS


class LanguageMixin:
    def t(self, key, *args):
        text = TRANSLATIONS[self.language][key]
        return text.format(*args) if args else text

    def create_flag_images(self):
        self.polish_flag = tk.PhotoImage(width=24, height=16)
        self.polish_flag.put("#ffffff", to=(0, 0, 24, 8))
        self.polish_flag.put("#dc143c", to=(0, 8, 24, 16))

        self.uk_flag = tk.PhotoImage(width=24, height=16)
        for y in range(16):
            for x in range(24):
                distance = min(
                    abs(y * 23 - x * 15), abs(y * 23 - (15 - x) * 15)
                )
                color = "#012169"
                if distance <= 46:
                    color = "#ffffff"
                if distance <= 18:
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
        self.manage_button.configure(text=self.t("manage_league"))
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
        if self.management_window is not None and self.management_window.winfo_exists():
            self.management_window.title(self.t("manage_title"))
            self.rename_button.configure(text=self.t("rename_league"))
            self.clone_button.configure(text=self.t("clone_league"))
            self.delete_button.configure(text=self.t("delete_league"))
            self.close_management_button.configure(text=self.t("close"))
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
            "Nie znaleziono ligi.": "league_not_found",
        }
        key = translations.get(str(error))
        return self.t(key) if key else str(error)
