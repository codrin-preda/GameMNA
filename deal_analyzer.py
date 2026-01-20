"""
GameMNA: A Game-Theoretic M&A Decision Support Tool.
Logic Module.
"""

class DealAnalyzer:
    def __init__(self):
        # Calibration based on Dissertation Chapter 4 Findings
        self.RISK_THRESHOLD_HIGH = 75
        self.RISK_THRESHOLD_MODERATE = 40
        self.CULTURE_CRITICAL_LIMIT = 0.12  # From Microsoft/Activision Simulation

    def calculate_risk_score(self, num_bidders, due_diligence_quality, cultural_fit):
        """
        Calculates a Transaction Risk Score (0-100) based on Auction Theory 
        and Integration constraints.
        """
        score = 0
        reasons = []

        # 1. Auction Dynamics Factor (RJR Nabisco Finding)
        # Findings showed N > 4 leads to ~100% probability of Winner's Curse.
        if num_bidders > 6:
            score += 50
            reasons.append("Critical Risk: Extreme Competition (>6 Bidders) guarantees Winner's Curse.")
        elif num_bidders > 4:
            score += 40
            reasons.append("High Risk: High Competition increases overpayment probability >90%.")
        elif num_bidders >= 2:
            score += 20
            reasons.append("Moderate Risk: Standard Competitive Pressure.")

        # 2. Information Asymmetry Factor (Signaling Games)
        # Low due diligence acts as a multiplier for overpayment risk.
        if due_diligence_quality < 0.3:
            score += 30
            reasons.append("Critical Risk: Opaque Information (Blind Bidding).")
        elif due_diligence_quality < 0.7:
            score += 15
            reasons.append("Moderate Risk: Incomplete Information signals.")

        # 3. Cultural Integration Constraint (Microsoft Finding)
        # Findings showed fit < 0.12 destroys value regardless of deal logic.
        if cultural_fit < self.CULTURE_CRITICAL_LIMIT:
            score += 50  # Critical Failure Factor
            reasons.append(f"Critical Risk: Cultural Fit {cultural_fit} is below the viability threshold ({self.CULTURE_CRITICAL_LIMIT}).")
        elif cultural_fit < 0.5:
            score += 20
            reasons.append("High Risk: Poor Cultural Alignment suggests synergy leakage.")

        # Cap score at 100
        final_score = min(score, 100)

        # Determine Recommendation
        if final_score >= self.RISK_THRESHOLD_HIGH:
            risk_level = "CRITICAL"
            rec = "WALK AWAY. Expected Value is negative due to Winner's Curse or Integration Failure."
        elif final_score >= self.RISK_THRESHOLD_MODERATE:
            risk_level = "HIGH"
            rec = "PROCEED WITH CAUTION. Require structural protections (e.g., lower bid, earn-outs)."
        else:
            risk_level = "LOW"
            rec = "PROCEED. Deal fundamentals are sound within game-theoretic bounds."

        return {
            "score": final_score,
            "risk_level": risk_level,
            "recommendation": rec,
            "drivers": reasons
        }

    def recommend_strategy(self, regulatory_risk, competition_level):
        """
        Recommends the optimal Game-Theoretic move based on Backward Induction.
        """
        if regulatory_risk == 'High':
            if competition_level == 'High':
                return (
                    "STRATEGY: Preemptive Remedies (Subgame Perfect Equilibrium).\n"
                    "Logic: High competition + High Regulation creates a 'War of Attrition'.\n"
                    "Action: Offer divestitures (e.g., licensing) immediately to signal "
                    "cooperation and deter regulatory veto, mimicking Microsoft's 2023 strategy."
                )
            else:
                return (
                    "STRATEGY: Negotiated Settlement.\n"
                    "Logic: With low competition, you are in a bilateral monopoly with the regulator.\n"
                    "Action: Do not bid aggressively. Focus on 'tit-for-tat' negotiation to clear hurdles."
                )
        
        elif regulatory_risk == 'Low':
            if competition_level == 'High':
                return (
                    "STRATEGY: Aggressive Sealed Bid (The 'Bulldozer').\n"
                    "Logic: Classic Auction Theory applies. Regulatory veto is unlikely.\n"
                    "Action: Bid high early (Shock & Awe) to signal strength and force rivals "
                    "to fold, but ensure bid < (True Value - Integration Cost)."
                )
            else:
                return (
                    "STRATEGY: Low-Ball / Opportunistic.\n"
                    "Logic: You have leverage. No external threats exist.\n"
                    "Action: Bid near the target's reservation price to maximize surplus."
                )
        
        return "Input Error: Define risks correctly."