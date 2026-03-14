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
    Wrapped in broad try/except to prevent loop failure from stopping the VM service.
    """
    pairs = data_mgr.load_pairs(config['common'].get('pairs_file', 'pairs.csv'))
    if not pairs:
        logger.warning("No pairs loaded. Will wait and try next cycle.")
        return
        
    # Collect unique tickers for batched downloading
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

        for stock_y, stock_x in pairs:
            pair_key = f"{stock_y}_{stock_x}"
            
            # Verify we have data for both legs
            if stock_y not in df_prices.columns or stock_x not in df_prices.columns:
                logger.warning(f"Data missing for pair {pair_key}. Skipping.")
                continue
                
            series_y = df_prices[stock_y]
            series_x = df_prices[stock_x]
            
            # Analyze mathematically (OLS -> ADF -> Spread -> Z-Score)
            analysis = analyzer.perform_cointegration_analysis(series_y, series_x)
            if not analysis:
                logger.debug(f"Analysis failed for {pair_key}. Skipping.")
                continue
                
            current_pos = execution.get_position(pair_key)
            
            # Filter entries: only consider trading statistically cointegrated pairs
            if not current_pos and not analysis["is_cointegrated"]:
                logger.debug(f"{pair_key} not currently cointegrated (p_val={analysis['p_value']:.4f}). Skipping.")
                continue

            # Check logic strategy for action
            signal = strategy.generate_signals(analysis, current_pos)
            
            if signal != "HOLD":
                logger.info(f"Signal {signal} for {pair_key} | Z-Score: {analysis['z_score']:.2f}")
                execution.execute_order(
                    pair=(stock_y, stock_x),
                    signal=signal,
                    hedge_ratio=analysis['hedge_ratio'],
                    price_y=series_y.iloc[-1],
                    price_x=series_x.iloc[-1]
                )
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
