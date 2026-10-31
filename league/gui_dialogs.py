"""Dialogs and file-export actions for the graphical interface."""

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk


class LeagueDialogsMixin:
    def open_league_management(self):
        league = self.selected_league()
        if league is None:
            return
        if (
            self.management_window is not None
            and self.management_window.winfo_exists()
        ):
            self.management_window.lift()
            return

        window = tk.Toplevel(self.root)
        window.title(self.t("manage_title"))
        window.transient(self.root)
        window.resizable(False, False)
        self.management_window = window
        self.management_league = league
        frame = ttk.Frame(window, padding=16)
        frame.pack(fill="both", expand=True)
        self.rename_button = ttk.Button(
            frame, command=self.rename_managed_league
        )
        self.rename_button.pack(fill="x", pady=3)
        self.clone_button = ttk.Button(
            frame, command=self.clone_managed_league
        )
        self.clone_button.pack(fill="x", pady=3)
        self.delete_button = ttk.Button(
            frame, command=self.delete_managed_league
        )
        self.delete_button.pack(fill="x", pady=3)
        self.close_management_button = ttk.Button(
            frame, text=self.t("close"), command=self.close_league_management
        )
        self.close_management_button.pack(fill="x", pady=(10, 0))
        window.protocol("WM_DELETE_WINDOW", self.close_league_management)
        self.update_language_widgets()
        self.root.update_idletasks()
        window.update_idletasks()
        window_width = window.winfo_reqwidth()
        window_height = window.winfo_reqheight()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - window_width) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - window_height) // 2
        x = min(max(0, x), window.winfo_screenwidth() - window_width)
        y = min(max(0, y), window.winfo_screenheight() - window_height)
        frame_x = window.winfo_rootx() - window.winfo_x()
        frame_y = window.winfo_rooty() - window.winfo_y()
        window.geometry("+{}+{}".format(x - frame_x, y - frame_y))
        window.grab_set()

    def close_league_management(self):
        if self.management_window is not None:
            if self.management_window.winfo_exists():
                self.management_window.grab_release()
                self.management_window.destroy()
            self.management_window = None

    def rename_managed_league(self):
        league = self.management_league
        while True:
            name = simpledialog.askstring(
                self.t("manage_title"),
                self.t("rename_prompt"),
                initialvalue=league["name"],
                parent=self.management_window,
            )
            if name is None:
                return
            try:
                self.service.rename_league(league["id"], name)
            except ValueError as error:
                messagebox.showerror(
                    self.t("create_error"), self.translate_core_error(error),
                    parent=self.management_window,
                )
                continue
            self.close_league_management()
            self.refresh_leagues(league["id"])
            messagebox.showinfo(
                self.t("manage_title"), self.t("rename_success"), parent=self.root
            )
            return

    def clone_managed_league(self):
        league = self.management_league
        while True:
            name = simpledialog.askstring(
                self.t("manage_title"),
                self.t("clone_prompt"),
                initialvalue=league["name"] + " (kopia)",
                parent=self.management_window,
            )
            if name is None:
                return
            try:
                clone_id = self.service.clone_league(league["id"], name)
            except ValueError as error:
                messagebox.showerror(
                    self.t("create_error"), self.translate_core_error(error),
                    parent=self.management_window,
                )
                continue
            self.close_league_management()
            self.refresh_leagues(clone_id)
            messagebox.showinfo(
                self.t("manage_title"), self.t("clone_success"), parent=self.root
            )
            return

    def delete_managed_league(self):
        league = self.management_league
        if not messagebox.askyesno(
            self.t("delete_league"),
            self.t("delete_confirm").format(league["name"]),
            parent=self.management_window,
            icon="warning",
        ):
            return
        try:
            self.service.delete_league(league["id"])
        except ValueError as error:
            messagebox.showerror(
                self.t("delete_league"),
                self.translate_core_error(error),
                parent=self.management_window,
            )
            return
        self.close_league_management()
        self.refresh_leagues()
        messagebox.showinfo(
            self.t("delete_league"), self.t("delete_success"), parent=self.root
        )

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
