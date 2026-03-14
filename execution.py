import logging

logger = logging.getLogger(__name__)

class Execution:
    def __init__(self, config: dict):
        self.capital = config['trading'].get('capital', 100000.0)
        self.commission_pct = config['trading'].get('commission_pct', 0.001)
        self.slippage_pct = config['trading'].get('slippage_pct', 0.0005)
        # Store positions as: { "StockY_StockX": { "type": "LONG_SPREAD", "y_qty": X, "x_qty": Y, "y_price": P1, "x_price": P2 } }
        self.positions = {} 

    def apply_slippage_commission(self, price: float, action: str) -> float:
        """
        action: 'buy' or 'sell'
        Returns the effective executed price including slippage and commission penalties.
        """
        if action == 'buy':
            price_with_slippage = price * (1 + self.slippage_pct)
            total_price = price_with_slippage * (1 + self.commission_pct)
        else: # sell
            price_with_slippage = price * (1 - self.slippage_pct)
            total_price = price_with_slippage * (1 - self.commission_pct)
        return total_price

    def get_position(self, pair_key: str) -> dict | None:
        return self.positions.get(pair_key, None)

    def execute_order(self, pair: tuple[str, str], signal: str, hedge_ratio: float, price_y: float, price_x: float):
        stock_y, stock_x = pair
        pair_key = f"{stock_y}_{stock_x}"
        
        try:
            if signal == "LONG_SPREAD":
                logger.info(f"[{pair_key}] Executing LONG_SPREAD: Buy {stock_y}, Sell Short {stock_x}")
                # Simple capital allocation - 50% capital to each side
                capital_per_side = self.capital / 2
                
                # Buy Y
                eff_price_y = self.apply_slippage_commission(price_y, 'buy')
                qty_y = capital_per_side / eff_price_y
                
                # Sell Short X
                eff_price_x = self.apply_slippage_commission(price_x, 'sell')
                qty_x = (capital_per_side / eff_price_x) * hedge_ratio
                
                self.positions[pair_key] = {
                    "type": "LONG_SPREAD",
                    "y_qty": qty_y,
                    "x_qty": qty_x,
                    "y_price": eff_price_y,
                    "x_price": eff_price_x
                }
                logger.info(f"[{pair_key}] LONG_SPREAD filled. {stock_y} Qty: {qty_y:.2f} @ {eff_price_y:.2f} | {stock_x} Qty: {qty_x:.2f} @ {eff_price_x:.2f}")
                
            elif signal == "SHORT_SPREAD":
                logger.info(f"[{pair_key}] Executing SHORT_SPREAD: Sell Short {stock_y}, Buy {stock_x}")
                capital_per_side = self.capital / 2
                
                # Sell Short Y
                eff_price_y = self.apply_slippage_commission(price_y, 'sell')
                qty_y = capital_per_side / eff_price_y
                
                # Buy X
                eff_price_x = self.apply_slippage_commission(price_x, 'buy')
                qty_x = (capital_per_side / eff_price_x) * hedge_ratio
                
                self.positions[pair_key] = {
                    "type": "SHORT_SPREAD",
                    "y_qty": qty_y,
                    "x_qty": qty_x,
                    "y_price": eff_price_y,
                    "x_price": eff_price_x
                }
                logger.info(f"[{pair_key}] SHORT_SPREAD filled. {stock_y} Qty: {qty_y:.2f} @ {eff_price_y:.2f} | {stock_x} Qty: {qty_x:.2f} @ {eff_price_x:.2f}")
                
            elif signal == "CLOSE":
                pos = self.positions.pop(pair_key, None)
                if pos:
                    pnl = 0.0
                    if pos['type'] == "LONG_SPREAD":
                        # Close Buy Y -> Sell Y
                        close_y = self.apply_slippage_commission(price_y, 'sell')
                        pnl_y = (close_y - pos['y_price']) * pos['y_qty']
                        
                        # Close Short X -> Buy X
                        close_x = self.apply_slippage_commission(price_x, 'buy')
                        pnl_x = (pos['x_price'] - close_x) * pos['x_qty']
                        
                        pnl = pnl_y + pnl_x
                        
                    elif pos['type'] == "SHORT_SPREAD":
                        # Close Short Y -> Buy Y
                        close_y = self.apply_slippage_commission(price_y, 'buy')
                        pnl_y = (pos['y_price'] - close_y) * pos['y_qty']
                        
                        # Close Buy X -> Sell X
                        close_x = self.apply_slippage_commission(price_x, 'sell')
                        pnl_x = (close_x - pos['x_price']) * pos['x_qty']
                        
                        pnl = pnl_y + pnl_x
                        
                    logger.info(f"[{pair_key}] Closed Position. Realized PnL: {pnl:.2f}")
                    # Could update self.capital += pnl if compounding is desired
                    
        except Exception as e:
            logger.error(f"Order Execution Failed for {pair_key}: {e}", exc_info=True)
