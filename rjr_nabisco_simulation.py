"""
================================================================================
RJR NABISCO (1988) — COMMON-VALUE AUCTION SIMULATION
Hypothesis 1: The Behavioral Amplification (Winner's Curse) Hypothesis
================================================================================

Model
-----
A common-value first-price sealed-bid auction. Nature draws a single true value
V ~ Normal(mu_V, tau_V). Each of N bidders observes a private, noisy signal
    s_i = V + e_i ,   e_i ~ Normal(0, sigma)
where sigma is the degree of information uncertainty / asymmetry.

Three bidder behaviours are compared:

  * NAIVE   : bids its raw signal s_i. Makes no correction for the fact that
              winning is "bad news" (the winner tends to be the most optimistic
              bidder). This is the textbook source of the Winner's Curse.

  * RATIONAL: applies the equilibrium winner's-curse correction. Conditional on
              winning (i.e. holding the highest of N signals), the expected
              upward noise in one's signal is approximately the expected maximum
              of N standard normals, m_N. The rational bidder therefore SHADES:
                    b_i = s_i - sigma * m_N
              Under a diffuse prior this makes E[winning bid] = V, so expected
              profit is ~0 and the systematic curse disappears. (Milgrom & Weber,
              1982; Thaler, 1988.)

  * BIASED  : a "hubris" bidder (Roll, 1986) who over-values the target by a
              factor (1+alpha) and does NOT shade:  b_i = (1+alpha) * s_i.

Why this matters
----------------
The PREVIOUS version of this script labelled the unshaded (naive) bidder as
"rational". That made the Winner's Curse a mechanical identity:
        P(overpay) = 1 - (1/2)^N ,  independent of sigma.
i.e. ~75% even with only N=2 bidders, and the heatmap's sigma-axis did nothing.

Because the *sign* of profit is scale-invariant in sigma, P(overpay) can only
ever depend on N. sigma instead drives the *magnitude* of the loss. The heatmap
below therefore plots the EXPECTED OVERPAYMENT IN $B (= sigma * m_N for the naive
bidder), which is genuinely informative in both N and sigma.
================================================================================
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# ==========================================
# 1. CONFIGURATION  (single source of truth)
# ==========================================
OUTPUT_FOLDER = "Dissertation_Graphs"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

RANDOM_SEED      = 42
NUM_SIMULATIONS  = 10_000

# --- Calibration (Billions USD) -------------------------------------------------
TRUE_VALUE_MEAN  = 20.0    # Analyst consensus intrinsic value of RJR Nabisco
TRUE_VALUE_STD   = 1.0     # Volatility of intrinsic value (Nature's draw)
WINNING_BID_HIST = 25.0    # KKR's actual winning bid (~$109/share)

# RJR calibration point used for the histogram / summary.
#   N=8 reflects the full field of interested groups at the auction's peak
#   (Management/Shearson, KKR, First Boston consortium, Forstmann Little, etc.).
#   NOTE for the write-up: the SERIOUS final-round bidders were ~3. If you prefer
#   to model only the final round, set RJR_N = 3 and re-quote the summary numbers.
RJR_N            = 8
RJR_SIGMA        = 2.0     # Valuation uncertainty ($B). ~10% of value; large
                          # enough to reproduce a realistic ~$3-5B overpayment.

HUBRIS_ALPHA     = 0.10    # Over-valuation of the "biased" (hubris) bidder (10%)

# Ranges explored in the heatmap
N_RANGE          = [2, 3, 4, 5, 6, 7, 8]
SIGMA_RANGE      = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]

# ==========================================
# 2. EXPECTED MAX OF N STANDARD NORMALS  (m_N)
# ==========================================
# Used for the rational bidder's winner's-curse correction. Computed once by
# Monte Carlo and cached so every call uses identical, reproducible values.
_MN_CACHE = {}
def expected_max_standard_normal(n, draws=400_000, seed=7):
    if n not in _MN_CACHE:
        rng = np.random.default_rng(seed + n)
        _MN_CACHE[n] = float(np.mean(np.max(rng.standard_normal((draws, n)), axis=1)))
    return _MN_CACHE[n]

# ==========================================
# 3. CORE SIMULATION
# ==========================================
def run_auction_iteration(rng, num_bidders, sigma_info, mode="naive"):
    """One auction. Returns (winner_profit, overpayment_amount).

    winner_profit      = V - winning_bid          (negative => Winner's Curse)
    overpayment_amount = max(0, winning_bid - V)   (size of the overpayment)
    """
    true_val = rng.normal(TRUE_VALUE_MEAN, TRUE_VALUE_STD)
    signals  = rng.normal(true_val, sigma_info, num_bidders)

    if mode == "naive":
        bids = signals
    elif mode == "rational":
        # Equilibrium winner's-curse correction (shade by sigma * m_N).
        bids = signals - sigma_info * expected_max_standard_normal(num_bidders)
    elif mode == "biased":
        bids = (1.0 + HUBRIS_ALPHA) * signals
    else:
        raise ValueError(f"Unknown mode: {mode}")

    winning_bid = float(np.max(bids))
    return true_val - winning_bid, max(0.0, winning_bid - true_val)


def overpayment_probability(rng, n, sigma, mode, iters=NUM_SIMULATIONS):
    return np.mean([run_auction_iteration(rng, n, sigma, mode)[0] < 0 for _ in range(iters)])


def expected_overpayment_cost(rng, n, sigma, mode, iters=NUM_SIMULATIONS):
    """Expected size of the winner's curse cost in $B (mean of winning_bid - V,
    floored at 0). This is what varies meaningfully with sigma."""
    return np.mean([run_auction_iteration(rng, n, sigma, mode)[1] for _ in range(iters)])


# ==========================================
# 4. GRAPH A — HEATMAP OF EXPECTED OVERPAYMENT ($B)
# ==========================================
def make_heatmap():
    print("Generating Graph A: expected overpayment magnitude (naive bidders)...")
    rng = np.random.default_rng(RANDOM_SEED)
    data = [[expected_overpayment_cost(rng, n, s, "naive") for s in SIGMA_RANGE]
            for n in N_RANGE]
    df = pd.DataFrame(data, index=N_RANGE, columns=SIGMA_RANGE)

    plt.rcParams["font.family"] = "serif"
    fig, ax = plt.subplots(figsize=(9, 6))
    sns.heatmap(df, annot=True, fmt=".2f", cmap="Greys", linewidths=.5,
                linecolor="black", ax=ax,
                cbar_kws={"label": "Expected overpayment ($B)"})
    ax.set_title("Graph A: Expected Winner's-Curse Cost ($B)\n"
                 "by Number of Bidders and Information Uncertainty (naive bidding)",
                 fontsize=12, fontweight="bold")
    ax.set_xlabel("Information Uncertainty (σ, $B)", fontsize=10)
    ax.set_ylabel("Number of Bidders (N)", fontsize=10)
    ax.invert_yaxis()
    path = os.path.join(OUTPUT_FOLDER, "RJR_Overpayment_Heatmap.png")
    plt.savefig(path, dpi=300, bbox_inches="tight"); plt.close()
    print(f"  saved -> {path}")
    return df


# ==========================================
# 5. GRAPH B — PROFIT DISTRIBUTIONS (3 behaviours)
# ==========================================
def make_histogram():
    print(f"Generating Graph B: profit distributions at N={RJR_N}, σ={RJR_SIGMA}...")
    rng = np.random.default_rng(RANDOM_SEED)
    naive    = [run_auction_iteration(rng, RJR_N, RJR_SIGMA, "naive")[0]    for _ in range(NUM_SIMULATIONS)]
    rational = [run_auction_iteration(rng, RJR_N, RJR_SIGMA, "rational")[0] for _ in range(NUM_SIMULATIONS)]
    biased   = [run_auction_iteration(rng, RJR_N, RJR_SIGMA, "biased")[0]   for _ in range(NUM_SIMULATIONS)]

    plt.rcParams["font.family"] = "serif"
    fig, ax = plt.subplots(figsize=(11, 6))
    sns.histplot(rational, color="dimgray", label="Rational (bid-shading)",
                 kde=True, stat="density", element="step", fill=True, alpha=0.35, ax=ax)
    sns.histplot(naive, color="black", label="Naive (bids signal)",
                 kde=True, stat="density", element="step", fill=False, linewidth=1.5, ax=ax)
    sns.histplot(biased, color="black", label="Biased (hubris, +10%)",
                 kde=True, stat="density", element="step", fill=False,
                 linewidth=1.5, linestyle="--", ax=ax)
    ax.axvline(0, color="red", linewidth=1.5, label="Break-even")
    ax.set_title("Graph B: Winner's Profit Distribution by Bidder Behaviour\n"
                 f"(N={RJR_N}, σ={RJR_SIGMA})", fontsize=12, fontweight="bold")
    ax.set_xlabel("Winner Profit / Loss ($B)", fontsize=10)
    ax.set_ylabel("Density", fontsize=10)
    ax.grid(alpha=0.3); ax.legend()
    path = os.path.join(OUTPUT_FOLDER, "RJR_Profit_Distributions.png")
    plt.savefig(path, dpi=300, bbox_inches="tight"); plt.close()
    print(f"  saved -> {path}")
    return np.array(naive), np.array(rational), np.array(biased)


# ==========================================
# 6. RUN + SUMMARY (numbers to quote in the paper)
# ==========================================
if __name__ == "__main__":
    df = make_heatmap()
    naive, rational, biased = make_histogram()

    rng = np.random.default_rng(RANDOM_SEED)
    print("\n================= SUMMARY (for the dissertation text) =================")
    print(f"Calibration: N={RJR_N}, sigma={RJR_SIGMA}B, hubris alpha={HUBRIS_ALPHA}")
    print("\nP(overpayment) by N (naive bidder) — note: independent of sigma,")
    print("because the SIGN of profit is scale-invariant in sigma:")
    for n in N_RANGE:
        p_sim   = overpayment_probability(rng, n, RJR_SIGMA, "naive")
        p_theo  = 1 - 0.5 ** n
        print(f"   N={n}:  simulated={p_sim:5.3f}   theoretical 1-(1/2)^N={p_theo:5.3f}")

    print("\nMean winner profit ($B) at calibration:")
    print(f"   Naive    : {naive.mean():6.2f}   P(loss)={np.mean(naive<0)*100:4.1f}%")
    print(f"   Rational : {rational.mean():6.2f}   P(loss)={np.mean(rational<0)*100:4.1f}%   <- shading removes the systematic curse")
    print(f"   Biased   : {biased.mean():6.2f}   P(loss)={np.mean(biased<0)*100:4.1f}%")
    hubris_cost = rational.mean() - biased.mean()
    print(f"\n   'Hubris cost' (Rational - Biased mean) = {hubris_cost:5.2f}B")
    print(f"   Naive-vs-Biased gap                    = {naive.mean()-biased.mean():5.2f}B")
    print(f"\nHistorical check: model winning bid (biased) implies overpayment of")
    print(f"   ~${-biased.mean():.1f}B vs intrinsic ~${TRUE_VALUE_MEAN:.0f}B; KKR paid ~${WINNING_BID_HIST:.0f}B.")
    print("=======================================================================")
