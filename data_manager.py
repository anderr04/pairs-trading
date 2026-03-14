import pandas as pd
import yfinance as yf
import logging
import time

logger = logging.getLogger(__name__)

class DataManager:
    def __init__(self, config):
        self.lookback = config['data']['lookback_days']
        self.interval = config['data']['interval']

    def load_pairs(self, filepath: str) -> list[tuple[str, str]]:
        """
        Loads the pairs from the provided CSV file.
        Expects a CSV with 'stock1' and 'stock2' columns.
        """
        try:
            df = pd.read_csv(filepath)
            pairs = list(zip(df['stock1'], df['stock2']))
            logger.info(f"Loaded {len(pairs)} pairs from {filepath}")
            return pairs
        except Exception as e:
            logger.error(f"Failed to load pairs file {filepath}: {e}")
            return []

    def fetch_data(self, ticker_list: list[str], days: int) -> pd.DataFrame:
        """
        Fetch historical close data for a list of tickers.
        Includes retry logic for resilience against network/API errors.
        """
        data = {}
        for ticker in ticker_list:
            retries = 3
            while retries > 0:
                try:
                    logger.debug(f"Fetching data for {ticker}...")
                    ticker_data = yf.download(ticker, period=f"{days}d", interval=self.interval, progress=False)
                    
                    if not ticker_data.empty:
                        # Extract the unadjusted or adjusted close depending on availability
                        if 'Adj Close' in ticker_data.columns:
                            series = ticker_data['Adj Close']
                        else:
                            series = ticker_data['Close']
                        
                        # Handle MultiIndex dropping if multiple tickers were queried (yfinance behavior detail)
                        if isinstance(series, pd.DataFrame):
                            series = series[ticker]
                            
                        data[ticker] = series.squeeze()
                        break
                    else:
                        logger.warning(f"Empty data received for {ticker}. Retrying...")
                except Exception as e:
                    logger.warning(f"Error fetching {ticker}: {e}. Retrying ({retries-1} left)")
                
                time.sleep(2)
                retries -= 1
                
            if retries == 0:
                logger.error(f"Failed to fetch data for {ticker} after 3 attempts.")
        
        # Combine all tickers into one DataFrame
        if data:
            df = pd.DataFrame(data)
            # Forward fill missing data, then drop any rows that still have NaNs
            df = df.ffill().dropna()
            return df
            
        return pd.DataFrame()
