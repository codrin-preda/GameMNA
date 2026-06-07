"""
GameMNA — Game-Theoretic M&A Decision Support Tool
==================================================
Operationalises the three dissertation findings:
  H1  Winner's Curse         -> bidder-count auction risk (now also quantified in $B)
  H2  Regulatory Equilibrium -> Clean-vs-Remedies strategy via the game model
  H3  Cultural Constraint    -> hard non-linear cultural-fit threshold

This version adds: tabbed layout, styled Altair charts with legends, historical
case-study presets (reproducing the Chapter 5.4.3 validation in-tool), and a live
sensitivity / threshold explorer.

Run with:  streamlit run app.py
"""

import math
import datetime
import pandas as pd
import altair as alt
import streamlit as st

# ======================================================================
# 0. SHARED GAME MODEL  (identical to microsoft_activision_simulation.py)
# ======================================================================
MAX_SYNERGY       = 25.0
REMEDY_COST       = 3.0
BREAKUP_FEE       = 3.0
LITIGATION_COST   = 1.0
FAILURE_PAYOFF    = -(BREAKUP_FEE + LITIGATION_COST)   # -4.0
P_REMEDY_SUCCESS  = 0.95
C_MID             = 0.25
STEEPNESS         = 14.0
CULTURE_CRITICAL_LIMIT = 0.113            # solved in the simulation
REG_RISK_TO_CLEAN_SUCCESS = {"Low": 0.95, "Medium": 0.65, "High": 0.35}

# Expected maximum of N standard normals (winner's-curse correction term, H1).
# Pre-tabulated so the app needs no Monte Carlo at runtime.
EXP_MAX_STD_NORMAL = {1: 0.000, 2: 0.564, 3: 0.846, 4: 1.029, 5: 1.163,
                      6: 1.267, 7: 1.352, 8: 1.424, 9: 1.485, 10: 1.539}
SIGMA_MAX = 4.0   # uncertainty ($B) at zero due-diligence quality

def _sigmoid(x):
    return 1.0 / (1.0 + math.exp(-x))

def realised_synergy(C):
    return MAX_SYNERGY * _sigmoid(STEEPNESS * (C - C_MID))

def ev_clean(C, p_clean_success):
    return p_clean_success * realised_synergy(C) + (1 - p_clean_success) * FAILURE_PAYOFF

def ev_remedy(C):
    return P_REMEDY_SUCCESS * (realised_synergy(C) - REMEDY_COST) + (1 - P_REMEDY_SUCCESS) * FAILURE_PAYOFF

def expected_overpayment(num_bidders, dd_quality):
    """H1 quantified: expected winner's-curse cost ($B) for a naive bidder.
    Maps due-diligence quality q to information uncertainty sigma = (1-q)*SIGMA_MAX,
    then expected overpayment is sigma * E[max of N standard normals]."""
    sigma = (1 - dd_quality) * SIGMA_MAX
    return sigma * EXP_MAX_STD_NORMAL.get(int(num_bidders), 1.5)

# ======================================================================
# 1. HISTORICAL CASE PRESETS  (reproduce the Chapter 5.4.3 validation)
# ======================================================================
PRESETS = {
    "Custom / manual":             None,
    "RJR Nabisco (1988)":          dict(n=8, q=0.30, c=0.40, reg="Low"),
    "AOL-Time Warner (2000)":      dict(n=2, q=0.10, c=0.05, reg="Medium"),
    "Disney-Pixar (2006)":         dict(n=2, q=0.90, c=0.90, reg="Low"),
    "Microsoft-Activision (2023)": dict(n=2, q=0.70, c=0.45, reg="High"),
}

# ======================================================================
# 2. LOGIC
# ======================================================================
class DealAnalyzer:
    RISK_THRESHOLD_HIGH     = 75
    RISK_THRESHOLD_MODERATE = 40
    CULTURE_CRITICAL_LIMIT  = CULTURE_CRITICAL_LIMIT

    def calculate_risk_breakdown(self, num_bidders, dd_quality, cultural_fit, regulatory_risk):
        breakdown = {"Auction Dynamics": 0, "Info Asymmetry": 0,
                     "Cultural Constraints": 0, "Regulatory Exposure": 0}
        reasons = []

        if num_bidders > 6:
            breakdown["Auction Dynamics"] = 50
            reasons.append("Extreme competition (>6 bidders) - overpayment near-certain")
        elif num_bidders > 4:
            breakdown["Auction Dynamics"] = 40
            reasons.append("High competition (>4 bidders) - strong Winner's-Curse risk")
        elif num_bidders >= 2:
            breakdown["Auction Dynamics"] = 20
            reasons.append("Standard competitive pressure")

        if dd_quality < 0.3:
            breakdown["Info Asymmetry"] = 30
            reasons.append("Opaque information (near-blind bidding)")
        elif dd_quality < 0.7:
            breakdown["Info Asymmetry"] = 15
            reasons.append("Partial information / incomplete diligence")

        if cultural_fit < self.CULTURE_CRITICAL_LIMIT:
            breakdown["Cultural Constraints"] = 50
            reasons.append(f"Critical culture failure (C < {self.CULTURE_CRITICAL_LIMIT}) - value destroyed regardless of price")
        elif cultural_fit < 0.5:
            breakdown["Cultural Constraints"] = 20
            reasons.append("Poor cultural alignment")

        if regulatory_risk == "High":
            breakdown["Regulatory Exposure"] = 30
            reasons.append("High antitrust exposure - veto player active")
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

    def recommend_strategy(self, cultural_fit, regulatory_risk, num_bidders):
        """H2 recommendation (EV-driven) plus a competition-aware tactical note."""
        p_clean = REG_RISK_TO_CLEAN_SUCCESS[regulatory_risk]
        evc, evr = ev_clean(cultural_fit, p_clean), ev_remedy(cultural_fit)

        if cultural_fit < self.CULTURE_CRITICAL_LIMIT:
            move = "ABANDON"
            rationale = ("Cultural fit is below the critical threshold; the deal is "
                         "NPV-negative even if the regulator approves it (H3).")
        elif evr >= evc:
            move = "OFFER PRE-EMPTIVE REMEDIES"
            rationale = (f"Under {regulatory_risk.lower()} regulatory risk, remedies "
                         f"(E[V]=${evr:.1f}B) dominate litigation (E[V]=${evc:.1f}B). "
                         "This is the subgame-perfect equilibrium (H2).")
        else:
            move = "CLEAN BID ACCEPTABLE"
            rationale = (f"Regulatory risk is low enough that a clean bid "
                         f"(E[V]=${evc:.1f}B) beats paying for remedies (E[V]=${evr:.1f}B).")

        # Tactical note combining regulation x competition (interpretive guidance,
        # NOT a model output - labelled as such in the UI).
        hi_comp = num_bidders > 4
        if regulatory_risk == "High":
            note = ("War-of-attrition conditions: signal cooperation early with divestitures."
                    if hi_comp else "Bilateral bargaining with the regulator: settle, don't litigate.")
        else:
            note = ("Classic auction: bid decisively but keep bid < (value - integration cost)."
                    if hi_comp else "You hold leverage: bid near the target's reservation price.")
        return move, rationale, evc, evr, note

    def get_benchmark(self, score):
        if score >= 75:
            return "Comparable to RJR Nabisco (1988) / AOL-Time Warner (2000) - value-destructive"
        elif score >= 40:
            return "Moderate-risk transaction - manageable with concessions"
        return "Comparable to Disney-Pixar (2006) / managed Microsoft-Activision - sound fundamentals"


def generate_briefing_text(score, level, rec, drivers, inputs, strategy, curse_cost):
    date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    move, rationale, evc, evr, note = strategy
    text = f"""==================================================
GAMEMNA STRATEGIC BRIEFING
Generated: {date_str}
==================================================

1. EXECUTIVE SUMMARY
   Risk score:      {score}/100  ({level})
   Recommendation:  {rec}

2. INPUTS
   Bidders (N):        {inputs['n']}
   Due-diligence (q):  {inputs['dd']*100:.0f}%
   Cultural fit (C):   {inputs['culture']}   (critical threshold {CULTURE_CRITICAL_LIMIT})
   Regulatory risk:    {inputs['reg']}

3. WINNER'S-CURSE EXPOSURE (H1)
   Expected overpayment if bidding naively: ~${curse_cost:.1f}B

4. GAME-THEORETIC STRATEGY (H2 / subgame-perfect equilibrium)
   Optimal move: {move}
   E[V] clean = ${evc:.2f}B   |   E[V] remedies = ${evr:.2f}B
   {rationale}
   Tactical note: {note}

5. KEY RISK DRIVERS
"""
    for d in drivers:
        text += f"   [!] {d}\n"
    text += "==================================================\n"
    return text

# ======================================================================
# 3. STYLING
# ======================================================================
CSS = """
<style>
.block-container {padding-top: 2.2rem; max-width: 1200px;}
h1 {font-weight: 800; letter-spacing:-0.5px;}
section[data-testid="stSidebar"] {background:#f4f6f9;}
.gm-card {border:1px solid #e6e9ef; border-radius:12px; padding:18px 20px; background:#fff;
          box-shadow:0 1px 3px rgba(16,24,40,.05); margin-bottom:14px;}
.gm-score {font-size:46px; font-weight:800; line-height:1; margin:2px 0;}
.gm-sub {color:#667085; font-size:13px;}
.gm-meter {height:14px; border-radius:8px; margin:10px 0 4px 0;
           background:linear-gradient(90deg,#1a9850 0%,#fee08b 45%,#d73027 100%); position:relative;}
.gm-needle {position:absolute; top:-4px; width:3px; height:22px; background:#101828; border-radius:2px;}
.gm-pill {display:inline-block; padding:3px 12px; border-radius:999px; font-weight:700; font-size:13px;}
</style>
"""

LEVEL_COLOR = {"CRITICAL": "#d73027", "HIGH": "#f08c00", "LOW": "#1a9850"}
FACTOR_COLORS = {"Auction Dynamics": "#2c5f8a", "Info Asymmetry": "#5b8c5a",
                 "Cultural Constraints": "#b5651d", "Regulatory Exposure": "#7a5195"}

def score_card(score, level):
    color = LEVEL_COLOR[level]
    return f"""
    <div class="gm-card">
      <div class="gm-sub">TRANSACTION RISK SCORE</div>
      <div class="gm-score" style="color:{color}">{score}<span style="font-size:20px;color:#98a2b3">/100</span></div>
      <div class="gm-meter"><div class="gm-needle" style="left:calc({score}% - 1.5px)"></div></div>
      <div style="display:flex;justify-content:space-between;" class="gm-sub"><span>0</span><span>40</span><span>75</span><span>100</span></div>
      <div style="margin-top:10px"><span class="gm-pill" style="background:{color}1a;color:{color}">{level}</span></div>
    </div>"""

# ======================================================================
# 4. CHARTS
# ======================================================================
def contribution_chart(breakdown):
    df = pd.DataFrame({"Factor": list(breakdown.keys()), "Contribution": list(breakdown.values())})
    # Explicit descending order so the bars and labels share one sort.
    order = df.sort_values("Contribution", ascending=False)["Factor"].tolist()
    base = alt.Chart(df).encode(
        y=alt.Y("Factor:N", sort=order, title=None,
                axis=alt.Axis(labelLimit=220, labelFontSize=12, labelPadding=8),
                scale=alt.Scale(paddingInner=0.35, paddingOuter=0.2)),
        x=alt.X("Contribution:Q", title="Risk points", scale=alt.Scale(domain=[0, 55]),
                axis=alt.Axis(grid=True, gridColor="#eef0f4")),
        color=alt.Color("Factor:N",
                        scale=alt.Scale(domain=list(FACTOR_COLORS), range=list(FACTOR_COLORS.values())),
                        legend=alt.Legend(title="Risk factor (hypothesis)", orient="bottom", columns=2)),
        tooltip=["Factor", "Contribution"])
    bars = base.mark_bar(cornerRadiusEnd=4)
    labels = base.mark_text(align="left", dx=5, fontSize=12, fontWeight="bold", color="#344054").encode(
        text="Contribution:Q")
    # alt.Step sizes each category row independently -> bars can never overlap.
    return (bars + labels).properties(height=alt.Step(54))

def ev_chart(evc, evr):
    df = pd.DataFrame({"Strategy": ["Clean (litigate)", "Remedies (concede)"], "EV": [evc, evr]})
    base = alt.Chart(df).encode(
        x=alt.X("Strategy:N", title=None, axis=alt.Axis(labelAngle=0, labelFontSize=12)),
        y=alt.Y("EV:Q", title="Expected payoff ($B)"),
        color=alt.Color("Strategy:N", scale=alt.Scale(range=["#98a2b3", "#101828"]), legend=None),
        tooltip=["Strategy", alt.Tooltip("EV:Q", format=".2f")])
    bars = base.mark_bar(size=70, cornerRadiusEnd=4)
    labels = base.mark_text(dy=-8, fontSize=13, fontWeight="bold").encode(text=alt.Text("EV:Q", format="$.1f"))
    zero = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color="#d73027").encode(y="y:Q")
    return (zero + bars + labels).properties(height=300)

def sensitivity_chart(kind, n, q, c, reg):
    p_clean = REG_RISK_TO_CLEAN_SUCCESS[reg]
    if kind.startswith("Cultural"):
        xs = [i / 100 for i in range(0, 101)]
        long = pd.DataFrame({"C": xs, "Remedies": [ev_remedy(x) for x in xs],
                             "Clean": [ev_clean(x, p_clean) for x in xs]}).melt(
            "C", var_name="Strategy", value_name="EV")
        line = alt.Chart(long).mark_line(strokeWidth=2.5).encode(
            x=alt.X("C:Q", title="Cultural Fit (C)"),
            y=alt.Y("EV:Q", title="Expected payoff ($B)"),
            color=alt.Color("Strategy:N", scale=alt.Scale(range=["#98a2b3", "#101828"]),
                            legend=alt.Legend(orient="bottom")))
        thr = alt.Chart(pd.DataFrame({"x": [CULTURE_CRITICAL_LIMIT]})).mark_rule(
            color="#d73027", strokeDash=[4, 4]).encode(x="x:Q")
        cur = alt.Chart(pd.DataFrame({"x": [c]})).mark_rule(color="#2c5f8a").encode(x="x:Q")
        return (line + thr + cur).properties(height=320), \
               f"Red dashed = cultural threshold C~{CULTURE_CRITICAL_LIMIT}; blue = your current C={c}."
    elif kind.startswith("Number"):
        xs = list(range(1, 11))
        df = pd.DataFrame({"N": xs, "Expected overpayment ($B)": [expected_overpayment(x, q) for x in xs]})
        line = alt.Chart(df).mark_line(point=True, strokeWidth=2.5, color="#2c5f8a").encode(
            x=alt.X("N:O", title="Number of bidders (N)"), y=alt.Y("Expected overpayment ($B):Q"))
        cur = alt.Chart(pd.DataFrame({"x": [n]})).mark_rule(color="#d73027").encode(x="x:O")
        return (line + cur).properties(height=320), \
               f"Expected naive overpayment at your q={q}. Red = your current N={n}."
    else:
        xs = [i / 100 for i in range(0, 101)]
        df = pd.DataFrame({"q": xs, "Expected overpayment ($B)": [expected_overpayment(n, x) for x in xs]})
        line = alt.Chart(df).mark_line(strokeWidth=2.5, color="#5b8c5a").encode(
            x=alt.X("q:Q", title="Due-diligence quality (q)"), y=alt.Y("Expected overpayment ($B):Q"))
        cur = alt.Chart(pd.DataFrame({"x": [q]})).mark_rule(color="#d73027").encode(x="x:Q")
        return (line + cur).properties(height=320), \
               f"Lower diligence -> larger curse (at your N={n}). Red = your current q={q}."

# ======================================================================
# 5. UI
# ======================================================================
def apply_preset():
    p = PRESETS[st.session_state["preset"]]
    if p:
        st.session_state.update({"n": p["n"], "q": p["q"], "c": p["c"], "reg": p["reg"]})

def main():
    st.set_page_config(page_title="GameMNA", layout="wide", page_icon="♟")
    st.markdown(CSS, unsafe_allow_html=True)
    for k, v in {"n": 6, "q": 0.5, "c": 0.4, "reg": "Medium"}.items():
        st.session_state.setdefault(k, v)

    st.title("GameMNA - Game-Theoretic M&A Risk Analyzer")
    st.caption("Based on the dissertation *Game Theory in Mergers and Acquisitions* (2026). "
               "Operationalises Auction Theory (H1), the regulatory equilibrium (H2) and the cultural constraint (H3).")

    with st.sidebar:
        st.header("Deal Parameters")
        st.selectbox("Load a historical case", list(PRESETS), key="preset", on_change=apply_preset,
                     help="Reproduces the Chapter 5.4.3 validation cases.")
        st.divider()
        num_bidders = st.slider("Number of Bidders (N)", 1, 10, key="n",
                                help="N>4 sharply raises Winner's-Curse risk (H1).")
        dd_quality = st.slider("Due-Diligence Quality (q)", 0.0, 1.0, step=0.05, key="q",
                               help="0 = blind bidding, 1 = full information. Distinct from the simulation's uncertainty sigma.")
        culture_fit = st.slider("Cultural Fit Score (C)", 0.0, 1.0, step=0.05, key="c",
                                help=f"C below {CULTURE_CRITICAL_LIMIT} destroys value regardless of price (H3).")
        regulatory_risk = st.selectbox("Regulatory Risk", ["Low", "Medium", "High"], key="reg",
                                       help="Antitrust/veto exposure - drives the Clean-vs-Remedies strategy (H2).")

    analyzer = DealAnalyzer()
    score, level, rec, breakdown, drivers = analyzer.calculate_risk_breakdown(
        num_bidders, dd_quality, culture_fit, regulatory_risk)
    strategy = analyzer.recommend_strategy(culture_fit, regulatory_risk, num_bidders)
    move, rationale, evc, evr, note = strategy
    curse_cost = expected_overpayment(num_bidders, dd_quality)

    tab_dash, tab_strat, tab_sens, tab_about = st.tabs(
        ["Risk Dashboard", "Strategy (H2)", "Sensitivity", "Methodology"])

    with tab_dash:
        left, right = st.columns([1, 1.25], gap="large")
        with left:
            st.markdown(score_card(score, level), unsafe_allow_html=True)
            _raw = sum(breakdown.values())
            if _raw > 100:
                st.caption(f"Raw factor total = {_raw} points, capped at 100 "
                           "(the maximum-risk / walk-away level).")
            st.caption(analyzer.get_benchmark(score))
            (st.error if level == "CRITICAL" else st.warning if level == "HIGH" else st.success)(
                f"**{level}** - {rec}")
            with st.expander("Key risk drivers", expanded=True):
                for d in drivers:
                    st.markdown(f"- {d}")
            st.download_button("Download strategic briefing",
                               generate_briefing_text(score, level, rec, drivers,
                                   {"n": num_bidders, "dd": dd_quality, "culture": culture_fit, "reg": regulatory_risk},
                                   strategy, curse_cost),
                               file_name="GameMNA_Strategic_Briefing.txt", mime="text/plain")
        with right:
            st.markdown("##### Risk contribution by factor")
            st.altair_chart(contribution_chart(breakdown), width='stretch')

    with tab_strat:
        c1, c2 = st.columns([1, 1], gap="large")
        with c1:
            st.markdown("##### Optimal regulatory strategy (subgame-perfect)")
            st.info(f"### {move}\n\n{rationale}")
            st.metric("Winner's-Curse exposure (H1)", f"~ ${curse_cost:.1f}B",
                      help="Expected overpayment if bidding naively, given N and q.")
            st.caption(f"**Tactical note** (interpretive): {note}")
        with c2:
            st.markdown("##### Expected payoff: Clean vs. Remedies")
            st.altair_chart(ev_chart(evc, evr), width='stretch')
            st.caption("Remedies cost a fixed concession but raise the probability of approval; "
                       "Clean risks a regulatory veto. The higher bar is the equilibrium strategy.")

    with tab_sens:
        st.markdown("##### How the outcome moves when one parameter changes")
        kind = st.radio("Sweep variable", ["Cultural Fit (C) - H3 threshold",
                                           "Number of Bidders (N) - H1 curse",
                                           "Due-Diligence Quality (q)"], horizontal=True)
        chart, caption = sensitivity_chart(kind, num_bidders, dd_quality, culture_fit, regulatory_risk)
        st.altair_chart(chart, width='stretch')
        st.caption(caption)

    with tab_about:
        st.markdown(f"""
**How the score maps to the research**

| Factor | Hypothesis | Logic |
|---|---|---|
| Auction Dynamics | **H1** Winner's Curse | Overpayment probability rises with bidder count N; expected loss scales with uncertainty. |
| Info Asymmetry | Signalling | Low due-diligence quality widens valuation error. |
| Cultural Constraints | **H3** Cultural threshold | Non-linear synergy collapse below **C = {CULTURE_CRITICAL_LIMIT}**. |
| Regulatory Exposure | **H2** Regulatory equilibrium | Veto-player risk; drives the Clean-vs-Remedies choice via backward induction. |

The strategy recommendation solves the regulatory subgame by comparing E[V] of a
clean (litigated) bid against a remedies (concession) bid, using the same payoff
model as `microsoft_activision_simulation.py`.

The headline score is a **capped severity index**: factor points are additive and
truncated at 100 (the maximum-risk, "walk-away" level). For very high-risk deals the
individual bars can therefore sum to more than the displayed score — this is by design,
not an error.
""")

    st.divider()
    st.caption("(c) 2026 Game Theory in Mergers and Acquisitions - George-Codrin Preda. Validated via Python simulation.")


if __name__ == "__main__":
    main()
