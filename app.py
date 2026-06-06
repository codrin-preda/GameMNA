"""
GameMNA — Game-Theoretic M&A Decision Support Tool
==================================================
Operationalises the three dissertation findings into a single decision aid:

  H1  Winner's Curse        -> bidder-count (auction) risk
  H2  Regulatory Equilibrium-> Clean-vs-Remedies strategy via the game model
  H3  Cultural Constraint   -> hard cultural-fit threshold

This version (a) ADDS the regulatory/Subgame-Perfect-Equilibrium logic that the
dissertation describes but the previous app never implemented, (b) decouples
"Due-Diligence Quality" from the simulation symbol sigma, and (c) uses the same
non-linear synergy curve as microsoft_activision_simulation.py so the tool and
the thesis agree.

Run with:  streamlit run app.py
"""

import math
import datetime
import pandas as pd
import streamlit as st

# ======================================================================
# 0. SHARED GAME MODEL  (kept identical to microsoft_activision_simulation.py)
# ======================================================================
MAX_SYNERGY       = 25.0
REMEDY_COST       = 3.0
BREAKUP_FEE       = 3.0
LITIGATION_COST   = 1.0
FAILURE_PAYOFF    = -(BREAKUP_FEE + LITIGATION_COST)   # -4.0
P_REMEDY_SUCCESS  = 0.95
C_MID             = 0.25
STEEPNESS         = 14.0

# Cultural threshold below which NPV turns negative (solved in the simulation).
CULTURE_CRITICAL_LIMIT = 0.113

# Regulatory risk -> probability a "clean" (no-concessions) deal ultimately closes.
# Low risk => clean bid is essentially safe and remedies are an unnecessary cost;
# Medium/High => the clean path is risky and pre-emptive remedies dominate (H2).
REG_RISK_TO_CLEAN_SUCCESS = {"Low": 0.95, "Medium": 0.65, "High": 0.35}

def _sigmoid(x):
    return 1.0 / (1.0 + math.exp(-x))

def realised_synergy(C):
    return MAX_SYNERGY * _sigmoid(STEEPNESS * (C - C_MID))

def ev_clean(C, p_clean_success):
    S = realised_synergy(C)
    return p_clean_success * S + (1 - p_clean_success) * FAILURE_PAYOFF

def ev_remedy(C):
    S = realised_synergy(C)
    return P_REMEDY_SUCCESS * (S - REMEDY_COST) + (1 - P_REMEDY_SUCCESS) * FAILURE_PAYOFF


# ======================================================================
# 1. LOGIC CLASS
# ======================================================================
class DealAnalyzer:
    """Game-theoretic M&A risk scorer. Pure logic, no UI dependencies."""

    RISK_THRESHOLD_HIGH     = 75
    RISK_THRESHOLD_MODERATE = 40
    CULTURE_CRITICAL_LIMIT  = CULTURE_CRITICAL_LIMIT

    def calculate_risk_breakdown(self, num_bidders, dd_quality, cultural_fit, regulatory_risk):
        """Returns score, level, recommendation text, factor breakdown, reasons."""
        breakdown = {
            "Auction Dynamics":     0,   # H1
            "Info Asymmetry":       0,
            "Cultural Constraints": 0,   # H3
            "Regulatory Exposure":  0,   # H2
        }
        reasons = []

        # --- H1: Auction / Winner's Curse risk (bidder count) ---
        if num_bidders > 6:
            breakdown["Auction Dynamics"] = 50
            reasons.append("Extreme competition (>6 bidders) — overpayment near-certain")
        elif num_bidders > 4:
            breakdown["Auction Dynamics"] = 40
            reasons.append("High competition (>4 bidders) — strong Winner's-Curse risk")
        elif num_bidders >= 2:
            breakdown["Auction Dynamics"] = 20
            reasons.append("Standard competitive pressure")

        # --- Information asymmetry (due-diligence quality) ---
        if dd_quality < 0.3:
            breakdown["Info Asymmetry"] = 30
            reasons.append("Opaque information (near-blind bidding)")
        elif dd_quality < 0.7:
            breakdown["Info Asymmetry"] = 15
            reasons.append("Partial information / incomplete diligence")

        # --- H3: Cultural constraint ---
        if cultural_fit < self.CULTURE_CRITICAL_LIMIT:
            breakdown["Cultural Constraints"] = 50
            reasons.append(f"Critical culture failure (C < {self.CULTURE_CRITICAL_LIMIT}) — value destroyed regardless of price")
        elif cultural_fit < 0.5:
            breakdown["Cultural Constraints"] = 20
            reasons.append("Poor cultural alignment")

        # --- H2: Regulatory exposure ---
        if regulatory_risk == "High":
            breakdown["Regulatory Exposure"] = 30
            reasons.append("High antitrust exposure — veto player active")
        elif regulatory_risk == "Medium":
            breakdown["Regulatory Exposure"] = 15
            reasons.append("Moderate regulatory scrutiny")

        final_score = min(sum(breakdown.values()), 100)

        if final_score >= self.RISK_THRESHOLD_HIGH:
            level, rec = "CRITICAL", "WALK AWAY. Expected value is negative."
        elif final_score >= self.RISK_THRESHOLD_MODERATE:
            level, rec = "HIGH", "PROCEED WITH CAUTION. Mitigate via concessions / earn-outs."
        else:
            level, rec = "LOW", "PROCEED. Fundamentals are sound."

        return final_score, level, rec, breakdown, reasons

    def recommend_strategy(self, cultural_fit, regulatory_risk):
        """H2 / Subgame-Perfect-Equilibrium recommendation: Clean vs. Remedies."""
        p_clean = REG_RISK_TO_CLEAN_SUCCESS[regulatory_risk]
        evc, evr = ev_clean(cultural_fit, p_clean), ev_remedy(cultural_fit)

        if cultural_fit < self.CULTURE_CRITICAL_LIMIT:
            move = "ABANDON"
            rationale = ("Cultural fit is below the critical threshold; the deal is "
                         "NPV-negative even if the regulator approves it (H3).")
        elif evr >= evc:
            move = "OFFER PRE-EMPTIVE REMEDIES"
            rationale = (f"With {regulatory_risk.lower()} regulatory risk, remedies "
                         f"(E[V]=${evr:.1f}B) dominate litigation (E[V]=${evc:.1f}B). "
                         "This is the subgame-perfect equilibrium (H2).")
        else:
            move = "CLEAN BID ACCEPTABLE"
            rationale = (f"Regulatory risk is low enough that a clean bid "
                         f"(E[V]=${evc:.1f}B) beats paying for remedies "
                         f"(E[V]=${evr:.1f}B).")
        return move, rationale, evc, evr

    def get_benchmark(self, score):
        if score >= 75:
            return "Ref: RJR Nabisco (1988) / AOL–Time Warner (2000) — value-destructive"
        elif score >= 40:
            return "Ref: Moderate-risk transaction — manageable with concessions"
        else:
            return "Ref: Disney–Pixar (2006) / managed Microsoft–Activision — sound fundamentals"


# ======================================================================
# 2. BRIEFING TEXT
# ======================================================================
def generate_briefing_text(score, level, rec, drivers, inputs, strategy):
    date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    move, rationale, evc, evr = strategy
    text = f"""==================================================
GAMEMNA STRATEGIC BRIEFING
Generated: {date_str}
==================================================

1. EXECUTIVE SUMMARY
--------------------
RISK SCORE:       {score}/100
RISK LEVEL:       {level}
RECOMMENDATION:   {rec}

2. INPUT PARAMETERS
-------------------
- Number of Bidders:      {inputs['n']}
- Due-Diligence Quality:  {inputs['dd']*100:.0f}%
- Cultural Fit Score:     {inputs['culture']}  (critical threshold: {CULTURE_CRITICAL_LIMIT})
- Regulatory Risk:        {inputs['reg']}

3. GAME-THEORETIC STRATEGY (H2 / Subgame-Perfect Equilibrium)
-------------------------------------------------------------
OPTIMAL MOVE: {move}
 E[V] clean (litigate) = ${evc:.2f}B
 E[V] remedies         = ${evr:.2f}B
 Rationale: {rationale}

4. KEY RISK DRIVERS
-------------------
"""
    for d in drivers:
        text += f" [!] {d}\n"
    text += """
--------------------------------------------------
Methodology:
- Auction risk: Winner's-Curse Monte Carlo (Chapter 5.2)
- Strategy: Backward induction on the regulatory game (Chapter 5.3)
- Cultural threshold: non-linear synergy realisation (Chapter 5.3.3)
==================================================
"""
    return text


# ======================================================================
# 3. STREAMLIT UI
# ======================================================================
def main():
    st.set_page_config(page_title="GameMNA Tool", layout="wide")
    st.title("GameMNA: Game-Theoretic M&A Risk Analyzer")
    st.markdown(
        "*Based on the dissertation 'Game Theory in Mergers and Acquisitions' (2026).* "
        "Operationalises **Auction Theory** (H1), **Backward Induction / regulatory "
        "equilibrium** (H2) and the **cultural constraint** (H3)."
    )
    st.divider()

    # --- Sidebar inputs ---
    st.sidebar.header("Deal Parameters")
    num_bidders = st.sidebar.slider("Number of Bidders (N)", 1, 10, 6,
                                    help="N>4 sharply raises Winner's-Curse risk (H1).")
    dd_quality = st.sidebar.slider("Due-Diligence Quality (q)", 0.0, 1.0, 0.5, 0.1,
                                   help="0.0 = blind bidding, 1.0 = full information. "
                                        "(Distinct from the simulation's uncertainty σ.)")
    culture_fit = st.sidebar.slider("Cultural Fit Score (C)", 0.0, 1.0, 0.4, 0.05,
                                    help=f"C below {CULTURE_CRITICAL_LIMIT} destroys value regardless of price (H3).")
    regulatory_risk = st.sidebar.selectbox("Regulatory Risk", ["Low", "Medium", "High"], index=2,
                                           help="Antitrust/veto exposure. Drives the Clean-vs-Remedies strategy (H2).")

    analyzer = DealAnalyzer()
    score, level, rec, breakdown, drivers = analyzer.calculate_risk_breakdown(
        num_bidders, dd_quality, culture_fit, regulatory_risk)
    strategy = analyzer.recommend_strategy(culture_fit, regulatory_risk)
    move, rationale, evc, evr = strategy

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Transaction Risk Score")
        st.metric("Risk (0-100)", f"{score}/100")
        st.caption(analyzer.get_benchmark(score))

        st.subheader("Risk Recommendation")
        (st.error if level == "CRITICAL" else st.warning if level == "HIGH" else st.success)(
            f"**{level}:** {rec}")

        st.subheader("Strategic Move (H2)")
        st.info(f"**{move}**\n\n{rationale}")
        st.caption(f"E[V] clean = ${evc:.2f}B   ·   E[V] remedies = ${evr:.2f}B")

        st.markdown("**Key Risk Drivers:**")
        for d in drivers:
            st.markdown(f"- {d}")

        st.markdown("---")
        briefing = generate_briefing_text(
            score, level, rec, drivers,
            {"n": num_bidders, "dd": dd_quality, "culture": culture_fit, "reg": regulatory_risk},
            strategy)
        st.download_button("Download Strategic Briefing", briefing,
                           file_name="GameMNA_Strategic_Briefing.txt", mime="text/plain")

    with col2:
        st.subheader("Risk Contribution Breakdown")
        df_chart = pd.DataFrame({"Risk Factor": list(breakdown.keys()),
                                 "Contribution": list(breakdown.values())})
        st.bar_chart(df_chart.set_index("Risk Factor"))
        st.caption(
            "**Auction Dynamics** (H1): Winner's-Curse risk from bidder count.  \n"
            "**Info Asymmetry:** penalty for bidding on noisy signals.  \n"
            "**Cultural Constraints** (H3): hard non-linear synergy threshold.  \n"
            "**Regulatory Exposure** (H2): antitrust veto risk driving the strategy choice."
        )

    st.divider()
    st.markdown("© 2026 *Game Theory in Mergers and Acquisitions* — George-Codrin Preda · "
                "Validated via Python simulation.")


if __name__ == "__main__":
    main()
