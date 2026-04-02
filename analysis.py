import pandas as pd
import json
import os

def analyze_trades():
    csv_file = "trades_history.csv"
    json_file = "open_positions.json"
    
    print("\n" + "="*50)
    print("      PAIRS TRADING BOT - PERFORMANCE ANALYTICS")
    print("="*50 + "\n")
    
    if os.path.exists(csv_file):
        df = pd.read_csv(csv_file)
        if df.empty:
            print("Trade history is empty.")
        else:
            # Filter only closed trades to calculate PnL
            closed_trades = df[df['Signal'] == 'CLOSE'].copy()
            total_trades = len(closed_trades)
            total_pnl = closed_trades['Realized_PnL'].sum() if not closed_trades.empty else 0.0
            
            wins = len(closed_trades[closed_trades['Realized_PnL'] > 0])
            losses = len(closed_trades[closed_trades['Realized_PnL'] <= 0])
            win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
            
            print(f"--- HISTORICAL METRICS ---")
            print(f"Total Closed Trades:  {total_trades}")
            print(f"Total Realized PnL:   ${total_pnl:.2f}")
            print(f"Total Wins:           {wins}")
            print(f"Total Losses:         {losses}")
            print(f"Win Rate:             {win_rate:.1f}%\n")
            
            print(f"--- MOST RECENT CLOSED TRADES ---")
            recent = closed_trades.tail(5)
            for _, row in recent.iterrows():
                pnl_str = f"+${row['Realized_PnL']:.2f}" if row['Realized_PnL'] > 0 else f"-${abs(row['Realized_PnL']):.2f}"
                print(f"[{row['Date']}] {row['Pair']} -> {pnl_str}")
            print()
    else:
        print(f"--- HISTORICAL METRICS ---")
        print("No trades_history.csv found yet.\n")
        
    print(f"--- CURRENT OPEN POSITIONS ---")
    if os.path.exists(json_file):
        with open(json_file, 'r') as f:
            try:
                positions = json.load(f)
                if not positions:
                    print("No currently open positions (100% Cash).")
                else:
                    for pair, data in positions.items():
                        print(f"- {pair}: {data['type']} | Bought Y: {data['y_qty']:.2f} @ ${data['y_price']:.2f} | Shorteó X: {data['x_qty']:.2f} @ ${data['x_price']:.2f}")
            except Exception as e:
                print(f"Error reading open_positions.json: {e}")
    else:
        print("No open_positions.json found yet (100% Cash).")
        
    print("\n" + "="*50)

if __name__ == "__main__":
    analyze_trades()
