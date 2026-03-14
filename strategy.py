import logging

logger = logging.getLogger(__name__)

class Strategy:
    def __init__(self, config: dict):
        self.entry_threshold = config['trading'].get('zscore_entry_threshold', 2.0)
        self.exit_threshold = config['trading'].get('zscore_exit_threshold', 0.5)

    def generate_signals(self, analysis_result: dict, current_position: dict | None) -> str:
        """
        Determine if we should enter or exit positions based on the Z-Score.
        
        Returns a signal string: "LONG_SPREAD", "SHORT_SPREAD", "CLOSE", or "HOLD".
        - LONG_SPREAD: Buy stock Y, Sell stock X (when Z_Score < -entry)
        - SHORT_SPREAD: Sell stock Y, Buy stock X (when Z_Score > entry)
        - CLOSE: Close existing long/short spread position
        """
        if not analysis_result:
            return "HOLD"
            
        z_score = analysis_result['z_score']
        
        # 1. Evaluate Exits if we have an open position
        if current_position:
            position_type = current_position.get('type')
            
            if position_type == "LONG_SPREAD" and z_score >= -self.exit_threshold:
                return "CLOSE"
                
            elif position_type == "SHORT_SPREAD" and z_score <= self.exit_threshold:
                return "CLOSE"
                
            else:
                return "HOLD"
        
        # 2. Evaluate Entries if we have no open position
        if z_score > self.entry_threshold:
            # Spread is too high, expect reversion downwards
            return "SHORT_SPREAD"
            
        elif z_score < -self.entry_threshold:
            # Spread is too low, expect reversion upwards
            return "LONG_SPREAD"
            
        return "HOLD"
