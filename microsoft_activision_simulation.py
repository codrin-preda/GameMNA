"""
================================================================================
MICROSOFT / ACTIVISION (2023) — DYNAMIC REGULATORY GAME
Hypothesis 2: The Regulatory Equilibrium Hypothesis
Hypothesis 3: The Cultural Constraint Hypothesis
================================================================================

Model
-----
Microsoft (the Acquirer) moves first, choosing a deal structure:
    S_MS = { CLEAN MERGER , REMEDIES }
The Regulator (FTC / CMA, a veto player) responds. Backward induction gives the
Subgame-Perfect Equilibrium.

  * CLEAN MERGER : invites a regulatory challenge. The deal then closes only if
                   Microsoft prevails in court, with probability P_CLEAN_SUCCESS.
                   Otherwise it fails (breakup fee + litigation cost).
  * REMEDIES     : pre-emptive divestitures (e.g. cloud rights to Ubisoft, 10-yr
                   Call of Duty licences). Costs REMEDY_COST but secures approval
                   with high probability P_REMEDY_SUCCESS.

Terminal payoff depends on post-merger CULTURAL FIT C in [0,1] through a
NON-LINEAR synergy-realisation function (H3):

    realised_synergy(C) = MAX_SYNERGY * sigmoid( STEEPNESS * (C - C_MID) )

i.e. cultural friction acts as an S-curve "tax" on synergy. Below a transition
region synergy collapses toward zero, producing a genuine non-linear cliff in
NPV — unlike the previous version, where payoff was a straight line in C and the
"C = 0.12 cliff" was simply REMEDY_COST / MAX_SYNERGY.

Two key quantities are SOLVED numerically and reported (not asserted):
    * the strategy CROSSOVER C* where Remedies begins to dominate Clean;
    * the cultural THRESHOLD C_break where the (dominant) strategy's NPV = 0.

Note (corrected): P_CLEAN_SUCCESS is the probability the clean deal CLOSES, so the
clean strategy's *failure* probability is (1 - P_CLEAN_SUCCESS). The previous code
labelled a 70% WIN probability while the text described a 70% FAILURE probability.
================================================================================
"""

import os
import numpy as np
import matplotlib.pyplot as plt
import networkx as nx

# ==========================================
# 1. CONFIGURATION (Billions USD)
# ==========================================
OUTPUT_FOLDER     = "Dissertation_Graphs"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

DEAL_VALUE        = 68.7    # Headline deal value (announced)
MAX_SYNERGY       = 25.0    # Gross potential synergy NPV
REMEDY_COST       = 3.0     # Cost of divestitures / concessions
BREAKUP_FEE       = 3.0     # Paid if the deal is blocked
LITIGATION_COST   = 1.0     # Sunk legal cost if challenged
FAILURE_PAYOFF    = -(BREAKUP_FEE + LITIGATION_COST)   # = -4.0

# Regulatory outcome probabilities (corrected & made explicit)
P_CLEAN_SUCCESS   = 0.35    # P(no-concessions deal ultimately CLOSES) under HIGH
                            # multi-jurisdiction opposition (FTC + CMA + EU; the
                            # CMA initially blocked the deal). => 65% failure prob.
                            # Matches the "High" regulatory case in app.py.
P_REMEDY_SUCCESS  = 0.95    # P(approval) once pre-emptive remedies are offered.

# Non-linear synergy realisation as a function of cultural fit C (H3)
C_MID             = 0.25    # Midpoint of the S-curve transition
STEEPNESS         = 14.0    # Larger => sharper "cliff"


# ==========================================
# 2. PAYOFF MODEL
# ==========================================
def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))

def realised_synergy(C):
    """Non-linear (S-curve) synergy realisation. Cultural friction taxes synergy."""
    return MAX_SYNERGY * sigmoid(STEEPNESS * (C - C_MID))

def ev_clean(C):
    S = realised_synergy(C)
    return P_CLEAN_SUCCESS * S + (1 - P_CLEAN_SUCCESS) * FAILURE_PAYOFF

def ev_remedy(C):
    S = realised_synergy(C)
    return P_REMEDY_SUCCESS * (S - REMEDY_COST) + (1 - P_REMEDY_SUCCESS) * FAILURE_PAYOFF

def optimal_strategy(C):
    r, c = ev_remedy(C), ev_clean(C)
    return ("Remedies", r) if r >= c else ("Clean", c)


# ==========================================
# 3. SOLVE FOR CROSSOVER AND THRESHOLD
# ==========================================
def find_root(f, lo=0.0, hi=1.0, tol=1e-6):
    """Bisection for a monotone-ish sign change; returns None if no crossing."""
    flo, fhi = f(lo), f(hi)
    if flo == 0: return lo
    if fhi == 0: return hi
    if np.sign(flo) == np.sign(fhi):
        return None
    for _ in range(200):
        mid = 0.5 * (lo + hi); fm = f(mid)
        if abs(fm) < tol: return mid
        if np.sign(fm) == np.sign(flo): lo, flo = mid, fm
        else: hi = mid
    return 0.5 * (lo + hi)

C_CROSS = find_root(lambda C: ev_remedy(C) - ev_clean(C))      # Remedies overtakes Clean
C_BREAK = find_root(lambda C: ev_remedy(C))                     # Remedies NPV = 0


# ==========================================
# 4. GRAPH C — STRATEGY PAYOFFS vs CULTURAL FIT
# ==========================================
def make_payoff_curves():
    print("Generating Graph C: strategy payoffs vs cultural fit...")
    Cs = np.linspace(0, 1, 300)
    clean  = [ev_clean(c)  for c in Cs]
    remedy = [ev_remedy(c) for c in Cs]

    plt.rcParams["font.family"] = "serif"
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(Cs, clean,  color="gray", linestyle="--", linewidth=2,
            label='Strategy A: "Clean Merger" (litigate)')
    ax.plot(Cs, remedy, color="black", linewidth=2.2,
            label='Strategy B: "Remedies" (concede)')
    ax.axhline(0, color="red", linewidth=1, label="Profit / loss threshold")

    if C_BREAK is not None:
        ax.axvspan(0, C_BREAK, alpha=0.10, color="red")
        ax.text(C_BREAK/2, ax.get_ylim()[0]*0.6, "ZONE OF\nVALUE DESTRUCTION",
                color="darkred", fontsize=9, ha="center")
        ax.axvline(C_BREAK, color="darkred", linestyle=":", linewidth=1)
        ax.annotate(f"Cultural threshold\nC ≈ {C_BREAK:.3f}",
                    xy=(C_BREAK, 0), xytext=(C_BREAK+0.12, 4),
                    fontsize=8, arrowprops=dict(arrowstyle="->", color="darkred"))
    if C_CROSS is not None:
        ax.axvline(C_CROSS, color="black", linestyle=":", linewidth=0.8, alpha=0.6)
        ax.annotate(f"Strategy crossover\nC* ≈ {C_CROSS:.3f}",
                    xy=(C_CROSS, ev_remedy(C_CROSS)), xytext=(C_CROSS+0.10, -3),
                    fontsize=8, arrowprops=dict(arrowstyle="->", color="black"))

    ax.set_title("Graph C: Expected Payoff — Clean Merger vs. Remedies\n"
                 "(non-linear synergy realisation in cultural fit)",
                 fontsize=12, fontweight="bold")
    ax.set_xlabel("Cultural Integration Score (C)", fontsize=10)
    ax.set_ylabel("Microsoft Expected Payoff ($B)", fontsize=10)
    ax.grid(alpha=0.3); ax.legend(loc="upper left")
    path = os.path.join(OUTPUT_FOLDER, "MSFT_Strategy_Payoffs.png")
    plt.savefig(path, dpi=300, bbox_inches="tight"); plt.close()
    print(f"  saved -> {path}")


# ==========================================
# 5. GRAPH D — EXTENSIVE-FORM GAME TREE
# ==========================================
def make_game_tree():
    print("Generating Graph D: extensive-form game tree...")
    pos = {
        "Microsoft":            (0, 4),
        "Clean Bid":            (-2.2, 3),
        "Remedy Bid":           (2.2, 3),
        "Regulator\n(Sue)":     (-2.2, 2),
        "Regulator\n(Approve)": (2.2, 2),
        "Court\nWin":           (-3.3, 1),
        "Deal\nFails":          (-1.1, 1),
        "Integration\n(payoff ~ C)": (2.2, 1),
    }
    edges = [
        ("Microsoft", "Clean Bid"), ("Microsoft", "Remedy Bid"),
        ("Clean Bid", "Regulator\n(Sue)"), ("Remedy Bid", "Regulator\n(Approve)"),
        ("Regulator\n(Sue)", "Court\nWin"), ("Regulator\n(Sue)", "Deal\nFails"),
        ("Regulator\n(Approve)", "Integration\n(payoff ~ C)"),
    ]
    G = nx.DiGraph(); G.add_edges_from(edges)
    plt.figure(figsize=(12, 7)); plt.rcParams["font.family"] = "serif"
    nx.draw_networkx_nodes(G, pos, node_size=3200, node_color="white", edgecolors="black")
    nx.draw_networkx_edges(G, pos, arrowstyle="-|>", arrowsize=20, edge_color="black")
    nx.draw_networkx_labels(G, pos, font_size=8, font_family="serif", font_weight="bold")
    edge_labels = {
        ("Microsoft", "Clean Bid"): "Strategy A",
        ("Microsoft", "Remedy Bid"): "Strategy B",
        ("Clean Bid", "Regulator\n(Sue)"): "challenged",
        ("Remedy Bid", "Regulator\n(Approve)"): f"approve ({P_REMEDY_SUCCESS*100:.0f}%)",
        ("Regulator\n(Sue)", "Court\nWin"): f"win ({P_CLEAN_SUCCESS*100:.0f}%)",
        ("Regulator\n(Sue)", "Deal\nFails"): f"lose ({(1-P_CLEAN_SUCCESS)*100:.0f}%)",
        ("Regulator\n(Approve)", "Integration\n(payoff ~ C)"): "closes",
    }
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=8, label_pos=0.5)
    plt.text(pos["Deal\nFails"][0], 0.55, f"Payoff = ${FAILURE_PAYOFF:.0f}B",
             ha="center", fontsize=8, color="red",
             bbox=dict(facecolor="white", alpha=0.8, edgecolor="red"))
    plt.text(pos["Integration\n(payoff ~ C)"][0], 0.55, "Payoff = S(C) − cost",
             ha="center", fontsize=8,
             bbox=dict(facecolor="white", alpha=0.8, edgecolor="gray"))
    plt.title("Graph D: Extensive-Form Game Tree (Microsoft / Activision)",
              fontsize=13, fontweight="bold")
    plt.axis("off")
    path = os.path.join(OUTPUT_FOLDER, "MSFT_Game_Tree.png")
    plt.savefig(path, dpi=300, bbox_inches="tight"); plt.close()
    print(f"  saved -> {path}")


# ==========================================
# 6. RUN + SUMMARY
# ==========================================
if __name__ == "__main__":
    make_payoff_curves()
    make_game_tree()

    print("\n================= SUMMARY (for the dissertation text) =================")
    print(f"P(clean deal closes)  = {P_CLEAN_SUCCESS}  => failure probability = {1-P_CLEAN_SUCCESS:.2f}")
    print(f"P(remedy approval)    = {P_REMEDY_SUCCESS}")
    print(f"Synergy S-curve: midpoint C_MID={C_MID}, steepness={STEEPNESS}")
    print()
    print(f"Strategy crossover  C* = {C_CROSS:.4f}  (Remedies dominates Clean for C > C*)")
    print(f"Cultural threshold  C_break = {C_BREAK:.4f}  (Remedies NPV > 0 for C > C_break)")
    print()
    print("  C     EV_clean   EV_remedy   optimal")
    for C in [0.0, 0.05, 0.10, 0.15, 0.20, 0.30, 0.50, 0.90]:
        name, _ = optimal_strategy(C)
        print(f" {C:0.2f}   {ev_clean(C):8.2f}   {ev_remedy(C):8.2f}    {name}")
    print()
    print("Interpretation:")
    print(f"  * For C > {C_CROSS:.2f}, pre-emptive Remedies strictly beat litigation (H2).")
    print(f"  * Below C ≈ {C_BREAK:.2f}, even the optimal strategy yields NEGATIVE NPV (H3):")
    print(f"    regulatory approval is necessary but NOT sufficient for value creation.")
    print(f"  * The S-curve makes this a genuine non-linear collapse, not a straight line.")
    print("=======================================================================")
