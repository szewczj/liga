"""Dialogs and file-export actions for the graphical interface."""

from tkinter import filedialog, messagebox, simpledialog


class LeagueDialogsMixin:
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
                league_id = self.service.create_league(name, team_names)
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
        try:
            exported_path = self.service.export_league(league["id"], path)
        except (OSError, ValueError) as error:
            messagebox.showerror(self.t("export_error"), str(error))
            return
        messagebox.showinfo(
            self.t("export_title"),
            self.t("export_success").format(exported_path),
        )
