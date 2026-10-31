"""Score entry and match result actions."""

from tkinter import messagebox


class ResultEntryMixin:
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
            self.service.record_result(match["id"], home_score, away_score)
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
