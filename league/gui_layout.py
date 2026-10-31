"""Reusable widget construction for the league window."""

import tkinter as tk
from tkinter import ttk


class LeagueLayoutMixin:
    def build_interface(self):
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
        self.export_button = ttk.Button(header, command=self.export_selected_league)
        self.export_button.pack(side="left")
        self.manage_button = ttk.Button(
            header, command=self.open_league_management
        )
        self.manage_button.pack(side="left", padx=(8, 0))
        self.language_button = ttk.Button(header, command=self.show_language_options)
        self.language_button.pack(side="right")

        content = ttk.Panedwindow(self.root, orient="horizontal")
        content.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.standings_panel = ttk.LabelFrame(content, padding=10)
        self.fixtures_panel = ttk.LabelFrame(content, padding=10)
        content.add(self.standings_panel, weight=1)
        content.add(self.fixtures_panel, weight=2)
        self._build_standings(self.standings_panel)
        self._build_fixtures(self.fixtures_panel)

    def _build_standings(self, parent):
        self.standings_tree = ttk.Treeview(
            parent,
            columns=("position", "team", "played", "points", "gf", "ga"),
            show="headings",
        )
        columns = (
            ("position", 42, "center"),
            ("team", 160, "w"),
            ("played", 40, "center"),
            ("points", 45, "center"),
            ("gf", 40, "center"),
            ("ga", 40, "center"),
        )
        for column, width, anchor in columns:
            self.standings_tree.column(column, width=width, anchor=anchor)
        self.standings_tree.pack(fill="both", expand=True)

    def _build_fixtures(self, parent):
        controls = ttk.Frame(parent)
        controls.pack(fill="x", pady=(0, 8))
        self.all_rounds_button = ttk.Radiobutton(
            controls,
            variable=self.round_mode,
            value="all",
            command=self.refresh_views,
        )
        self.all_rounds_button.pack(side="left")
        self.single_round_button = ttk.Radiobutton(
            controls,
            variable=self.round_mode,
            value="single",
            command=self.refresh_views,
        )
        self.single_round_button.pack(side="left", padx=(8, 16))
        self.previous_round_button = ttk.Button(
            controls, command=lambda: self.change_round(-1)
        )
        self.previous_round_button.pack(side="left")
        self.round_input = ttk.Spinbox(
            controls,
            from_=1,
            to=1,
            textvariable=self.round_input_var,
            width=5,
            justify="center",
        )
        self.round_input.pack(side="left", padx=5)
        self.round_input.bind("<Return>", self.show_entered_round)
        self.show_round_button = ttk.Button(
            controls, command=self.show_entered_round
        )
        self.show_round_button.pack(side="left")
        self.next_round_button = ttk.Button(
            controls, command=lambda: self.change_round(1)
        )
        self.next_round_button.pack(side="left", padx=(5, 0))

        container = ttk.Frame(parent)
        container.pack(fill="both", expand=True)
        self.rounds_canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(
            container, orient="vertical", command=self.rounds_canvas.yview
        )
        self.rounds_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
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
