import time
import yaml
import logging
import sys
from data_manager import DataManager
from analyzer import Analyzer
from strategy import Strategy
from execution import Execution

def setup_logging(config: dict):
    """
    Configures robust logging that outputs to both a file and standard output.
    Essential for 24/7 VM operation.
    """
    log_level_str = config['common'].get('log_level', 'INFO').upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    log_file = config['common'].get('log_file', 'trading_bot.log')
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )

def load_config(config_path: str = "config.yaml") -> dict:
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"CRITICAL: Failed to load config file {config_path}: {e}")
        sys.exit(1)

def run_loop(config: dict, data_mgr: DataManager, analyzer: Analyzer, strategy: Strategy, execution: Execution, logger: logging.Logger):
    """
    Core sequence: Fetch Data -> Analyze Cointegration -> Generate Signals -> Execute Orders
    """
    pairs = data_mgr.load_pairs(config['common'].get('pairs_file', 'pairs.csv'))
    if not pairs:
        logger.warning("No pairs loaded. Will wait and try next cycle.")
        return
        
    tickers = set()
    for y, x in pairs:
        tickers.add(y)
        tickers.add(x)
        
    lookback = config['data'].get('lookback_days', 252)
    
    try:
        df_prices = data_mgr.fetch_data(list(tickers), lookback)
        if df_prices.empty:
            logger.warning("No data retrieved from API. Skipping this cycle.")
            return

        market_state = {}

        for stock_y, stock_x in pairs:
            pair_key = f"{stock_y}_{stock_x}"
            
            if stock_y not in df_prices.columns or stock_x not in df_prices.columns:
                continue
                
            series_y = df_prices[stock_y]
            series_x = df_prices[stock_x]
            
            analysis = analyzer.perform_cointegration_analysis(series_y, series_x)
            if not analysis:
                continue
                
            current_pos = execution.get_position(pair_key)
            
            # Save the current state for transparency and analysis.py
            if analysis["is_cointegrated"]:
                market_state[pair_key] = round(analysis["z_score"], 3)
            
            if not current_pos and not analysis["is_cointegrated"]:
                continue

            signal = strategy.generate_signals(analysis, current_pos)
            
            if signal != "HOLD":
                logger.info(f"Signal {signal} for {pair_key} | Z-Score: {analysis['z_score']:.2f}")
                execution.execute_order(
                    pair=(stock_y, stock_x),
                    signal=signal,
                    hedge_ratio=analysis['hedge_ratio'],
                    price_y=series_y.iloc[-1],
                    price_x=series_x.iloc[-1],
                    z_score=analysis['z_score']
                )

        # Write market state for user visibility
        try:
            import json
            with open("market_state.json", "w") as f:
                json.dump(market_state, f, indent=4)
            # Find the most extreme z-score to log it as a heartbeat metric
            if market_state:
                closest_pair = max(market_state.items(), key=lambda x: abs(x[1]))
                logger.info(f"Market Scan complete. Closest pair to trigger: {closest_pair[0]} (Z-Score: {closest_pair[1]}). All other {len(market_state)-1} valid pairs were REJECTED (Hold).")
        except Exception as e:
            logger.error(f"Failed to dump market state: {e}")

    except Exception as e:
        logger.error(f"Error in main loop cycle: {e}", exc_info=True)

def main():
    config = load_config()
    setup_logging(config)
    logger = logging.getLogger("MainOrchestrator")
    logger.info("Starting Pairs Trading Divergence Bot - 24/7 Mode")
    
    # Initialize Core Modules
    data_mgr = DataManager(config)
    analyzer = Analyzer()
    strategy = Strategy(config)
    execution = Execution(config)
    
    sleep_interval = config['common'].get('sleep_interval_seconds', 3600)
    
    while True:
        logger.info("==== Starting analysis cycle ====")
        run_loop(config, data_mgr, analyzer, strategy, execution, logger)
        logger.info(f"==== Cycle complete. Waiting {sleep_interval} seconds... ====")
        
        try:
            time.sleep(sleep_interval)
        except KeyboardInterrupt:
            logger.info("Bot manually stopped by user (KeyboardInterrupt).")
            break
        except Exception as e:
            logger.error(f"Unexpected error during sleep phase: {e}", exc_info=True)
            time.sleep(60) # Fallback short sleep to prevent instant looping crash

if __name__ == "__main__":
    main()
