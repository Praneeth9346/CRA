import yfinance as yf
import pandas as pd
import pandas_ta as ta
from textblob import TextBlob

class CryptoAnalyzer:
    def __init__(self, ticker):
        self.ticker = ticker if ticker.endswith('-USD') else f"{ticker}-USD"
        self.data = None
        self.info = None

    def fetch_data(self):
        try:
            asset = yf.Ticker(self.ticker)
            self.data = asset.history(period="1y")
            self.info = asset.info
            return True
        except Exception as e:
            return False

    def analyze_technicals(self):
        if self.data is None or self.data.empty:
            return None

        # 1. Work directly on self.data so the App can access the columns for plotting
        self.data['RSI'] = ta.rsi(self.data['Close'], length=14)
        self.data['EMA_50'] = ta.ema(self.data['Close'], length=50)
        self.data['EMA_200'] = ta.ema(self.data['Close'], length=200)

        # 2. Extract latest values for the Score Calculation
        current_price = self.data['Close'].iloc[-1]
        
        # Handle cases where not enough data exists for EMA/RSI
        rsi = self.data['RSI'].iloc[-1] if not pd.isna(self.data['RSI'].iloc[-1]) else 50
        ema_50 = self.data['EMA_50'].iloc[-1] if not pd.isna(self.data['EMA_50'].iloc[-1]) else current_price
        ema_200 = self.data['EMA_200'].iloc[-1] if not pd.isna(self.data['EMA_200'].iloc[-1]) else current_price

        # Trend Identification
        if current_price > ema_50 > ema_200:
            trend = "Strong Uptrend 🟢"
        elif current_price < ema_50 < ema_200:
            trend = "Strong Downtrend 🔴"
        elif current_price > ema_200:
            trend = "Moderate Uptrend ↗️"
        else:
            trend = "Choppy/Downtrend ↘️"

        recent_low = self.data['Low'].tail(30).min()
        recent_high = self.data['High'].tail(30).max()

        # Returns summary for the Metrics
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
        if not self.info:
            return None
        
        mcap = self.info.get('marketCap', 0)
        volume = self.info.get('volume24Hr', 0)
        
        if volume == 0 and not self.data.empty:
            volume = self.data['Volume'].iloc[-1]

        vol_mcap_ratio = (volume / mcap) if mcap > 0 else 0

        return {
            "market_cap": mcap,
            "volume": volume,
            "vol_mcap_ratio": vol_mcap_ratio
        }

    def analyze_sentiment(self):
        try:
            asset = yf.Ticker(self.ticker)
            news = asset.news
            
            polarities = []
            headlines = []
            
            # Helper to safely get news
            if news:
                for item in news[:5]: 
                    title = item.get('title', '')
                    blob = TextBlob(title)
                    polarities.append(blob.sentiment.polarity)
                    headlines.append(title)
            
            avg_polarity = sum(polarities) / len(polarities) if polarities else 0
            
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
        score = 50 
        
        if tech['rsi'] < 30: score += 15 
        elif tech['rsi'] > 70: score -= 15 
        
        if "Uptrend" in tech['trend']: score += 15
        elif "Downtrend" in tech['trend']: score -= 15

        if fund['vol_mcap_ratio'] > 0.05: score += 10
        elif fund['vol_mcap_ratio'] < 0.01: score -= 5

        if sent['score'] > 0.1: score += 10
        elif sent['score'] < -0.1: score -= 10

        return max(0, min(100, score))
