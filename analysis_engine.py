import yfinance as yf
import pandas as pd
import pandas_ta as ta
from textblob import TextBlob
import requests

class CryptoAnalyzer:
    def __init__(self, ticker):
        self.ticker = ticker if ticker.endswith('-USD') else f"{ticker}-USD"
        self.data = None
        self.info = None
        self.news_sentiment = 0

    def fetch_data(self):
        """Fetches historical data and basic asset info."""
        try:
            asset = yf.Ticker(self.ticker)
            # Fetch 1 year of data for robust technicals
            self.data = asset.history(period="1y")
            self.info = asset.info
            return True
        except Exception as e:
            return False

    def analyze_technicals(self):
        """
        1. Chart analysis (Uptrend/Downtrend via EMA)
        2. RSI & EMA
        3. Support & Resistance
        """
        if self.data is None or self.data.empty:
            return None

        df = self.data.copy()
        
        # Calculate Indicators
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['EMA_50'] = ta.ema(df['Close'], length=50)
        df['EMA_200'] = ta.ema(df['Close'], length=200)

        current_price = df['Close'].iloc[-1]
        rsi = df['RSI'].iloc[-1]
        ema_50 = df['EMA_50'].iloc[-1]
        ema_200 = df['EMA_200'].iloc[-1]

        # Trend Identification
        if current_price > ema_50 > ema_200:
            trend = "Strong Uptrend 🟢"
        elif current_price < ema_50 < ema_200:
            trend = "Strong Downtrend 🔴"
        elif current_price > ema_200:
            trend = "Moderate Uptrend ↗️"
        else:
            trend = "Choppy/Downtrend ↘️"

        # Simple Support/Resistance (using recent swing highs/lows)
        recent_low = df['Low'].tail(30).min()
        recent_high = df['High'].tail(30).max()

        return {
            "current_price": current_price,
            "rsi": rsi,
            "ema_50": ema_50,
            "ema_200": ema_200,
            "trend": trend,
            "support": recent_low,
            "resistance": recent_high
        }

    def analyze_fundamentals(self):
        """
        1. Market Cap
        2. Volume
        3. Volume/Market Cap Ratio
        """
        if not self.info:
            return None
        
        mcap = self.info.get('marketCap', 0)
        volume = self.info.get('volume24Hr', 0)
        
        # Fallback if yfinance misses 24h volume
        if volume == 0 and not self.data.empty:
            volume = self.data['Volume'].iloc[-1]

        vol_mcap_ratio = (volume / mcap) if mcap > 0 else 0

        return {
            "market_cap": mcap,
            "volume": volume,
            "vol_mcap_ratio": vol_mcap_ratio
        }

    def analyze_sentiment(self):
        """
        Fetches news headlines from yfinance and calculates polarity.
        """
        try:
            asset = yf.Ticker(self.ticker)
            news = asset.news
            
            polarities = []
            headlines = []
            
            for item in news[:5]: # Analyze top 5 news items
                title = item.get('title', '')
                blob = TextBlob(title)
                polarities.append(blob.sentiment.polarity)
                headlines.append(title)
            
            avg_polarity = sum(polarities) / len(polarities) if polarities else 0
            
            # Map score to text
            if avg_polarity > 0.1: sent_text = "Bullish 🟢"
            elif avg_polarity < -0.1: sent_text = "Bearish 🔴"
            else: sent_text = "Neutral ⚪"

            return {
                "score": avg_polarity,
                "text": sent_text,
                "headlines": headlines
            }
        except Exception:
            return {"score": 0, "text": "Neutral (No Data)", "headlines": []}

    def calculate_confidence_score(self, tech, fund, sent):
        """
        Weighted Score Calculation (0-100).
        """
        score = 50 # Start neutral

        # Technical Weights (Max impact: +/- 30)
        if tech['rsi'] < 30: score += 15 # Oversold -> Buy signal
        elif tech['rsi'] > 70: score -= 15 # Overbought -> Sell signal
        
        if "Uptrend" in tech['trend']: score += 15
        elif "Downtrend" in tech['trend']: score -= 15

        # Fundamental Weights (Max impact: +/- 10)
        # High volume/mcap ratio indicates high liquidity/interest
        if fund['vol_mcap_ratio'] > 0.05: score += 10
        elif fund['vol_mcap_ratio'] < 0.01: score -= 5

        # Sentiment Weights (Max impact: +/- 10)
        if sent['score'] > 0.1: score += 10
        elif sent['score'] < -0.1: score -= 10

        return max(0, min(100, score)) # Clamp between 0 and 100