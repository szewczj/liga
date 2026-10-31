"""Round-robin fixture generation strategy."""

from typing import List, Optional, Sequence, Tuple


class RoundRobinScheduler:
    """Generate a single round-robin schedule using the circle method."""

    def generate(self, team_names: Sequence[str]) -> List[List[Tuple[str, str]]]:
        if len(team_names) < 2:
            raise ValueError("Liga musi mieć co najmniej dwie drużyny.")

        rotation: List[Optional[str]] = list(team_names)
        if len(rotation) % 2:
            rotation.append(None)

        rounds = []
        for round_index in range(len(rotation) - 1):
            fixtures = []
            for index in range(len(rotation) // 2):
                home = rotation[index]
                away = rotation[-index - 1]
                if home is not None and away is not None:
                    if round_index % 2:
                        home, away = away, home
                    fixtures.append((home, away))
            rounds.append(fixtures)
            rotation = [rotation[0], rotation[-1]] + rotation[1:-1]
        return rounds


def generate_schedule(team_names):
    """Compatibility function for callers that prefer the functional API."""
    return RoundRobinScheduler().generate(team_names)
