import streamlit as st
import pandas as pd
from deal_analyzer import DealAnalyzer

# Page Config
st.set_page_config(page_title="GameMNA: Risk Analyzer", layout="wide")

# Initialize Logic
analyzer = DealAnalyzer()

# --- SIDEBAR: INPUTS ---
with st.sidebar:
    st.header("1. Deal Parameters")
    st.write("Configure the game environment:")
    
    # 1. Auction Dynamics
    num_bidders = st.slider(
        "Number of Bidders ($N$)", 
        1, 10, 4, 
        help="Derived from RJR Nabisco Simulation. >4 increases overpayment risk."
    )
    
    # 2. Due Diligence
    due_diligence = st.slider(
        "Due Diligence Quality ($\sigma$)", 
        0.0, 1.0, 0.5, 
        help="0=Opaque (High Risk), 1=Transparent. Derived from Signaling Games."
    )
    
    # 3. Cultural Fit
    culture_fit = st.slider(
        "Cultural Fit Score ($C$)", 
        0.0, 1.0, 0.5, 
        help="Derived from Microsoft Simulation. <0.12 is critical failure."
    )

    st.markdown("---")
    
    # 4. Strategic Context (Restored Dropdowns)
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

# Run Calculations
risk_report = analyzer.calculate_risk_score(num_bidders, due_diligence, culture_fit)
strategy_rec = analyzer.recommend_strategy(reg_risk, comp_level)

# --- SECTION 1: EXECUTIVE SUMMARY (Heads-Up Display) ---
with st.container(border=True):
    col_score, col_rec = st.columns([1, 3])
    
    with col_score:
        st.caption("TRANSACTION RISK SCORE")
        
        # --- CUSTOM HTML LOGIC FOR SCORE & ARROW ---
        # 1. Define Color and Arrow Direction
        if risk_report['score'] < 40:
            # Low Risk -> Green, Down Arrow
            text_color = "#09ab3b"  # Green
            arrow = "↓"
        elif risk_report['score'] > 75:
            # High Risk -> Red, Up Arrow
            text_color = "#ff2b2b"  # Red
            arrow = "↑"
        else:
            # Medium Risk -> Orange, Up Arrow
            text_color = "#ffaa00"  # Orange
            arrow = "↑"

        # 2. Render using HTML (Removes default Streamlit arrow, adds custom Bold one on Right)
        st.markdown(f"""
            <div style="line-height: 1;">
                <span style="font-size: 3.5rem; font-weight: 700;">{risk_report['score']}/100</span>
                <br>
                <span style="color: {text_color}; font-size: 1.5rem; font-weight: 800; display: block; margin-top: 8px;">
                    {risk_report['risk_level']} <span style="font-size: 2rem;">{arrow}</span>
                </span>
            </div>
        """, unsafe_allow_html=True)
    
    with col_rec:
        st.caption("STRATEGIC RECOMMENDATION")
        if risk_report['score'] >= 75:
            st.error(f"**{risk_report['recommendation']}**")
        elif risk_report['score'] >= 40:
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
        
        # Risk Breakdown Data
        risk_data = {
            "Auction Dynamics": 0,
            "Info Asymmetry": 0,
            "Cultural Constraints": 0
        }
        
        if num_bidders > 4: risk_data["Auction Dynamics"] = 50
        elif num_bidders >= 2: risk_data["Auction Dynamics"] = 20
        
        if due_diligence < 0.3: risk_data["Info Asymmetry"] = 30
        elif due_diligence < 0.7: risk_data["Info Asymmetry"] = 15
        
        if culture_fit < 0.12: risk_data["Cultural Constraints"] = 50
        elif culture_fit < 0.5: risk_data["Cultural Constraints"] = 20

        chart_df = pd.DataFrame(list(risk_data.items()), columns=["Factor", "Points"])
        
        # Vertical Bar Chart (Points Upwards)
        st.bar_chart(chart_df.set_index("Factor"))

# --- SECTION 3: STRATEGY & REPORT ---
with st.container(border=True):
    st.subheader("Optimal Strategy (Game Tree Output)")
    st.info(strategy_rec, icon="♟️")

    # Download Button logic
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
