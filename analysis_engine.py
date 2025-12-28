import yfinance as yf
import pandas as pd
import pandas_ta as ta
from textblob import TextBlob
import datetime

class CryptoAnalyzer:
    def __init__(self, ticker):
        # Ensure ticker format is correct (e.g., BTC -> BTC-USD)
        self.ticker = ticker if ticker.endswith('-USD') else f"{ticker}-USD"
        self.data = None
        self.info = None

    def fetch_data(self):
        """Fetches historical data and detailed asset info."""
        try:
            asset = yf.Ticker(self.ticker)
            # Fetch 1 year of data for technicals
            self.data = asset.history(period="1y")
            self.info = asset.info
            return not self.data.empty
        except Exception as e:
            return False

    def analyze_technicals(self):
        """
        Analyzes Price, Trends, RSI, and Moving Averages.
        """
        if self.data is None or self.data.empty:
            return None

        # Calculate Indicators directly on the dataframe
        self.data['RSI'] = ta.rsi(self.data['Close'], length=14)
        self.data['EMA_50'] = ta.ema(self.data['Close'], length=50)
        self.data['EMA_200'] = ta.ema(self.data['Close'], length=200)

        # Get latest values
        current_price = self.data['Close'].iloc[-1]
        rsi = self.data['RSI'].iloc[-1]
        ema_50 = self.data['EMA_50'].iloc[-1]
        ema_200 = self.data['EMA_200'].iloc[-1]

        # Trend Logic
        if current_price > ema_50 > ema_200:
            trend = "Strong Uptrend 🟢"
        elif current_price < ema_50 < ema_200:
            trend = "Strong Downtrend 🔴"
        elif current_price > ema_200:
            trend = "Moderate Uptrend ↗️"
        else:
            trend = "Weak/Choppy ↘️"

        # Support & Resistance (Simple 30-day Low/High)
        support = self.data['Low'].tail(30).min()
        resistance = self.data['High'].tail(30).max()

        return {
            "current_price": current_price,
            "rsi": rsi,
            "ema_50": ema_50,
            "ema_200": ema_200,
            "trend": trend,
            "support": support,
            "resistance": resistance
        }

    def analyze_fundamentals(self):
        """
        Analyzes Market Cap, Volume, Supply, and 52-Week Range.
        """
        if not self.info:
            return None
        
        mcap = self.info.get('marketCap', 0)
        volume = self.info.get('volume24Hr', 0)
        # Fallback for volume
        if volume == 0 and not self.data.empty:
            volume = self.data['Volume'].iloc[-1]

        circulating_supply = self.info.get('circulatingSupply', 0)
        max_supply = self.info.get('maxSupply', 0)
        
        # Supply Emission Logic
        if max_supply and max_supply > 0:
            supply_percent = (circulating_supply / max_supply) * 100
        else:
            supply_percent = None # Infinite or unknown supply

        # Valuation vs 52-Week Range
        year_high = self.info.get('fiftyTwoWeekHigh', 0)
        year_low = self.info.get('fiftyTwoWeekLow', 0)
        current_price = self.data['Close'].iloc[-1]

        # Where is price relative to 52w range? (0% = Low, 100% = High)
        if year_high > year_low:
            range_position = ((current_price - year_low) / (year_high - year_low)) * 100
        else:
            range_position = 50

        vol_mcap_ratio = (volume / mcap) if mcap > 0 else 0

        return {
            "market_cap": mcap,
            "volume": volume,
            "vol_mcap_ratio": vol_mcap_ratio,
            "circulating_supply": circulating_supply,
            "max_supply": max_supply,
            "supply_percent": supply_percent,
            "year_high": year_high,
            "year_low": year_low,
            "range_position": range_position # Lower is often better for "value" buys
        }

    def analyze_sentiment(self):
        """
        Analyzes News headlines, extracts Publisher/Links, and scores sentiment.
        """
        try:
            asset = yf.Ticker(self.ticker)
            news_items = asset.news
            
            analyzed_news = []
            total_polarity = 0
            count = 0
            
            if news_items:
                for item in news_items[:7]: # Analyze up to 7 items
                    title = item.get('title', '')
                    publisher = item.get('publisher', 'Unknown')
                    link = item.get('link', '#')
                    
                    blob = TextBlob(title)
                    polarity = blob.sentiment.polarity
                    total_polarity += polarity
                    count += 1
                    
                    analyzed_news.append({
                        "title": title,
                        "publisher": publisher,
                        "link": link,
                        "sentiment": polarity
                    })
            
            avg_polarity = (total_polarity / count) if count > 0 else 0
            
            # Text Interpretation
            if avg_polarity > 0.15: sent_text = "Bullish 🟢"
            elif avg_polarity < -0.15: sent_text = "Bearish 🔴"
            else: sent_text = "Neutral ⚪"

            return {
                "score": avg_polarity,
                "text": sent_text,
                "news_list": analyzed_news
            }
        except Exception:
            return {"score": 0, "text": "Neutral (No Data)", "news_list": []}

    def calculate_confidence_score(self, tech, fund, sent):
        """
        Advanced Weighted Score Calculation (0-100).
        """
        score = 50 # Base Score

        # --- 1. TECHNICALS (Weight: 40%) ---
        # RSI
        if tech['rsi'] < 30: score += 10    # Oversold (Buy)
        elif tech['rsi'] > 70: score -= 10  # Overbought (Sell)
        elif tech['rsi'] > 50: score += 2   # Mild Momentum
        
        # Trend
        if "Strong Uptrend" in tech['trend']: score += 10
        elif "Strong Downtrend" in tech['trend']: score -= 15 # Don't catch falling knives
        
        # EMA Cross
        if tech['current_price'] > tech['ema_200']: score += 5

        # --- 2. FUNDAMENTALS (Weight: 30%) ---
        # Liquidity Check
        if fund['vol_mcap_ratio'] > 0.10: score += 10  # High interest
        elif fund['vol_mcap_ratio'] < 0.02: score -= 5 # Zombie coin

        # Buying the Dip? (52-Week Range)
        # If price is at bottom 20% of yearly range, it's a "Value" buy
        if fund['range_position'] < 20: score += 10
        # If price is at top 90% of yearly range, it's risky
        elif fund['range_position'] > 90: score -= 10

        # Supply Shock Risk
        if fund['supply_percent'] and fund['supply_percent'] < 50:
            score -= 5 # High inflation risk (lots of tokens yet to unlock)

        # --- 3. SENTIMENT (Weight: 30%) ---
        if sent['score'] > 0.15: score += 15
        elif sent['score'] < -0.15: score -= 15
        else: score += 0

        return max(0, min(100, score))
