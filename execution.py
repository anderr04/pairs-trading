import logging
import json
import csv
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class Execution:
    def __init__(self, config: dict):
        self.capital = config['trading'].get('capital', 100000.0)
        self.commission_pct = config['trading'].get('commission_pct', 0.001)
        self.slippage_pct = config['trading'].get('slippage_pct', 0.0005)
        
        self.positions_file = "open_positions.json"
        self.history_file = "trades_history.csv"
        
        # Load from disk if exists, otherwise empty dictionary
        self.positions = self._load_positions()
        self._init_history_file()

    def _load_positions(self) -> dict:
        if os.path.exists(self.positions_file):
            try:
                with open(self.positions_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load positions from {self.positions_file}: {e}")
        return {}

    def _save_positions(self):
        try:
            with open(self.positions_file, 'w') as f:
                json.dump(self.positions, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save positions to {self.positions_file}: {e}")

    def _init_history_file(self):
        if not os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Date', 'Pair', 'Signal', 'Z_Score', 'Price_Y', 'Qty_Y', 'Price_X', 'Qty_X', 'Realized_PnL'])
            except Exception as e:
                logger.error(f"Failed to initialize {self.history_file}: {e}")

    def _log_trade(self, pair_key, signal, z_score, price_y, qty_y, price_x, qty_x, pnl):
        try:
            with open(self.history_file, 'a', newline='') as f:
                writer = csv.writer(f)
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                writer.writerow([timestamp, pair_key, signal, round(z_score, 4), round(price_y, 4), round(qty_y, 4), round(price_x, 4), round(qty_x, 4), round(pnl, 4)])
        except Exception as e:
            logger.error(f"Failed to log trade to CSV: {e}")

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

    def execute_order(self, pair: tuple[str, str], signal: str, hedge_ratio: float, price_y: float, price_x: float, z_score: float = 0.0):
        stock_y, stock_x = pair
        pair_key = f"{stock_y}_{stock_x}"
        
        try:
            if signal == "LONG_SPREAD":
                logger.info(f"[{pair_key}] Executing LONG_SPREAD: Buy {stock_y}, Sell Short {stock_x}")
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
                
                self._save_positions()
                self._log_trade(pair_key, signal, z_score, eff_price_y, qty_y, eff_price_x, qty_x, 0.0)
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
                
                self._save_positions()
                self._log_trade(pair_key, signal, z_score, eff_price_y, qty_y, eff_price_x, qty_x, 0.0)
                logger.info(f"[{pair_key}] SHORT_SPREAD filled. {stock_y} Qty: {qty_y:.2f} @ {eff_price_y:.2f} | {stock_x} Qty: {qty_x:.2f} @ {eff_price_x:.2f}")
                
            elif signal == "CLOSE":
                pos = self.positions.pop(pair_key, None)
                if pos:
                    pnl = 0.0
                    if pos['type'] == "LONG_SPREAD":
                        close_y = self.apply_slippage_commission(price_y, 'sell')
                        pnl_y = (close_y - pos['y_price']) * pos['y_qty']
                        
                        close_x = self.apply_slippage_commission(price_x, 'buy')
                        pnl_x = (pos['x_price'] - close_x) * pos['x_qty']
                        pnl = pnl_y + pnl_x
                        
                    elif pos['type'] == "SHORT_SPREAD":
                        close_y = self.apply_slippage_commission(price_y, 'buy')
                        pnl_y = (pos['y_price'] - close_y) * pos['y_qty']
                        
                        close_x = self.apply_slippage_commission(price_x, 'sell')
                        pnl_x = (close_x - pos['x_price']) * pos['x_qty']
                        pnl = pnl_y + pnl_x
                        
                    self._save_positions()
                    self._log_trade(pair_key, signal, z_score, price_y, pos['y_qty'], price_x, pos['x_qty'], pnl)
                    logger.info(f"[{pair_key}] Closed Position. Realized PnL: {pnl:.2f}")
                    
        except Exception as e:
            logger.error(f"Order Execution Failed for {pair_key}: {e}", exc_info=True)
