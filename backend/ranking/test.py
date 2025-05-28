# -----------------------------------------------------------
# demo_margin_effect.py   –  run with:  python demo_margin_effect.py
# -----------------------------------------------------------

from own_packetlucet import PlackettLuce


def pretty(label, team):
    """Return the Δµ for each player in team as a string."""
    return f"{label:9s}  " + "  ".join(
        f"{p.name}: {p.mu - 25:+.3f}"  # Δµ versus the starting 25.0
        for p in team
    )


def run_once(margin):
    # --- create a fresh model ----------------------------------------------
    model = PlackettLuce(margin=1) if margin else PlackettLuce()
    tag = f"margin={margin}" if margin else "NO margin"

    # --- four brand-new players (µ=25, σ≈8.33) ------------------------------
    A, B = model.rating(name="Alice"), model.rating(name="Bob")
    C, D = model.rating(name="Carol"), model.rating(name="Dave")

    # --- 2-v-2 match: Alice/Bob beat Carol/Dave 10-3 ------------------------
    teams = [[A, B], [C, D]]
    scores = [10, 0]
    teams = model.rate(teams, scores=scores)

    w, l = teams  # winners & losers after update
    print(pretty(tag, w))
    print(pretty("", l))
    print("-" * 52)
    scores = [3, 10]  # raw goals
    teams = model.rate(teams, scores=scores)


for m in (1, 2.0):
    run_once(m)
