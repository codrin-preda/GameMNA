import streamlit as st
import pandas as pd
from deal_analyzer import DealAnalyzer

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="GameMNA: Risk Analyzer", layout="wide")

# Initialize Logic
analyzer = DealAnalyzer()

# --- SIDEBAR: INPUTS ---
with st.sidebar:
    st.header("1. Deal Parameters")
    st.write("Configure the game environment:")
    
    # 1. Auction Dynamics (Quantitative)
    # Kept strict range 1-10 as per your original
    num_bidders = st.slider(
        "Number of Bidders (N)", 
        min_value=1, max_value=10, value=4, 
        help="Derived from RJR Nabisco Simulation. N > 4 significantly increases overpayment risk."
    )
    
    # 2. Due Diligence (Mapped: String -> Float)
    # User sees labels, Logic gets numbers
    dd_label = st.select_slider(
        "Due Diligence Quality (σ)", 
        options=["Low", "Medium", "High"], 
        value="Medium",
        help="Low = Opaque (High Risk), High = Transparent."
    )
    # Mapping for DealAnalyzer
    dd_mapping = {"Low": 0.0, "Medium": 0.5, "High": 1.0}
    due_diligence = dd_mapping[dd_label]
    
    # 3. Cultural Fit (Mapped: String -> Float)
    # User sees labels, Logic gets numbers
    culture_label = st.select_slider(
        "Cultural Fit Score (C)", 
        options=["Friction (Low)", "Neutral", "Synergy (High)"], 
        value="Neutral",
        help="Derived from Microsoft Simulation. < Friction is critical failure."
    )
    # Mapping for DealAnalyzer
    culture_mapping = {"Friction (Low)": 0.0, "Neutral": 0.5, "Synergy (High)": 1.0}
    culture_fit = culture_mapping[culture_label]

    st.markdown("---")
    
    # 4. Strategic Context (Qualitative)
    st.subheader("2. Strategic Context")
    reg_risk = st.selectbox("Regulatory Scrutiny", ["Low", "High"])
    comp_level = st.selectbox("Competition Intensity", ["Low", "High"])
    
    st.markdown("---")
    st.caption("Adjust sliders to simulate different M&A scenarios.")


# --- MAIN PAGE: OUTPUTS ---
st.title("GameMNA: Game-Theoretic M&A Risk Analyzer")
st.markdown("""
*Based on Dissertation Research: 'Game Theory in Mergers and Acquisitions' (2025)* This tool operationalizes **Auction Theory** and **Backward Induction** into a decision support system.
""")
st.markdown("---")

# --- EXECUTION ---
# Pass the variables exactly as your DealAnalyzer expects them
risk_report = analyzer.calculate_risk_score(num_bidders, due_diligence, culture_fit)
strategy_rec = analyzer.recommend_strategy(reg_risk, comp_level)

# --- SECTION 1: EXECUTIVE SUMMARY ---
with st.container(border=True):
    col_score, col_rec = st.columns([1, 3])
    
    with col_score:
        st.caption("TRANSACTION RISK SCORE")
        # Dynamic Metric Color Logic
        score_val = risk_report['score']
        score_color = "normal"
        if score_val > 75: score_color = "inverse"
        
        st.metric(
            label="", 
            value=f"{score_val}/100", 
            delta=risk_report['risk_level'], 
            delta_color=score_color
        )
    
    with col_rec:
        st.caption("STRATEGIC RECOMMENDATION")
        if score_val >= 75:
            st.error(f"**{risk_report['recommendation']}**")
        elif score_val >= 40:
            st.warning(f"**{risk_report['recommendation']}**")
        else:
            st.success(f"**{risk_report['recommendation']}**")
            
        st.caption(f"**Benchmark Reference:** RJR Nabisco (1988) scored **92/100** (Critical Failure).")

# --- SECTION 2: DEEP DIVE (Drivers & Data) ---
col_drivers, col_chart = st.columns([1, 1])

with col_drivers:
    with st.container(border=True):
        st.subheader("Key Risk Drivers")
        if not risk_report['drivers']:
            st.info("No critical risk drivers identified at current settings.")
        else:
            for driver in risk_report['drivers']:
                if "Critical" in driver:
                    st.error(f"• {driver}")
                elif "High" in driver:
                    st.warning(f"• {driver}")
                else:
                    st.info(f"• {driver}")

with col_chart:
    with st.container(border=True):
        st.subheader("Risk Contribution")
        
        # Breakdown logic tailored to inputs
        risk_data = {
            "Auction Dynamics": 0,
            "Info Asymmetry": 0,
            "Cultural Constraints": 0
        }
        
        # Logic mirroring your original setup
        if num_bidders > 4: risk_data["Auction Dynamics"] = 50
        elif num_bidders >= 2: risk_data["Auction Dynamics"] = 20
        
        # Inverted logic: Low DD (0.0) = High Risk
        if due_diligence < 0.3: risk_data["Info Asymmetry"] = 30
        elif due_diligence < 0.7: risk_data["Info Asymmetry"] = 15
        
        # Inverted logic: Low Culture (0.0) = High Risk
        if culture_fit < 0.12: risk_data["Cultural Constraints"] = 50
        elif culture_fit < 0.5: risk_data["Cultural Constraints"] = 20

        chart_df = pd.DataFrame(list(risk_data.items()), columns=["Factor", "Points"])
        st.bar_chart(chart_df.set_index("Factor"), horizontal=True, color="#1f77b4")

# --- SECTION 3: STRATEGY & REPORT ---
with st.container(border=True):
    st.subheader("Optimal Strategy (Game Tree Output)")
    st.info(strategy_rec, icon="♟️")

    # Download Button Logic
    report_text = f"""
    M&A GAME THEORETIC RISK BRIEFING
    --------------------------------
    Risk Score: {risk_report['score']}/100
    Risk Level: {risk_report['risk_level']}
    Recommendation: {risk_report['recommendation']}

    STRATEGIC ADVICE:
    {strategy_rec}

    KEY DRIVERS:
    {chr(10).join(['- ' + d for d in risk_report['drivers']])}

    Generated by GameMNA
    """

    st.download_button(
        label="Download Strategy Briefing",
        data=report_text,
        file_name="deal_briefing.txt",
        help="Generate a text file report of this analysis."
    )

# Footer
st.markdown("---")
st.caption("© 2026 Game Theory in Mergers and Acquisitions Dissertation Artifact by George-Codrin Preda | Validated via Python Simulation")
