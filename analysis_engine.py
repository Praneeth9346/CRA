import yfinance as yf
import pandas as pd
import pandas_ta as ta
from textblob import TextBlob
import requests
from bs4 import BeautifulSoup

class CryptoAnalyzer:
    def __init__(self, ticker):
        # Ensure ticker format (e.g., BTC -> BTC-USD)
        self.clean_ticker = ticker.upper().replace("-USD", "")
        self.ticker = f"{self.clean_ticker}-USD"
        self.data = None
        self.info = None

    def fetch_data(self):
        """Fetches historical data and detailed asset info."""
        try:
            asset = yf.Ticker(self.ticker)
            self.data = asset.history(period="1y")
            self.info = asset.info
            return not self.data.empty
        except Exception as e:
            return False

    def analyze_technicals(self):
        """Analyzes Price, Trends, RSI, and Moving Averages."""
        if self.data is None or self.data.empty:
            return None

        # Calculate Indicators
        self.data['RSI'] = ta.rsi(self.data['Close'], length=14)
        self.data['EMA_50'] = ta.ema(self.data['Close'], length=50)
        self.data['EMA_200'] = ta.ema(self.data['Close'], length=200)

        # Get latest values
        current_price = self.data['Close'].iloc[-1]
        
        # Handle cases where RSI might be NaN
        rsi = self.data['RSI'].iloc[-1] if pd.notna(self.data['RSI'].iloc[-1]) else 50
        ema_50 = self.data['EMA_50'].iloc[-1] if pd.notna(self.data['EMA_50'].iloc[-1]) else current_price
        ema_200 = self.data['EMA_200'].iloc[-1] if pd.notna(self.data['EMA_200'].iloc[-1]) else current_price

        # Trend Logic
        if current_price > ema_50 > ema_200:
            trend = "Strong Uptrend 🟢"
        elif current_price < ema_50 < ema_200:
            trend = "Strong Downtrend 🔴"
        elif current_price > ema_200:
            trend = "Moderate Uptrend ↗️"
        else:
            trend = "Weak/Choppy ↘️"

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
        """Analyzes Market Cap, Volume, Supply."""
        if not self.info:
            return None
        
        mcap = self.info.get('marketCap', 0)
        volume = self.info.get('volume24Hr', 0)
        
        if volume == 0 and not self.data.empty:
            volume = self.data['Volume'].iloc[-1]

        circulating_supply = self.info.get('circulatingSupply', 0)
        max_supply = self.info.get('maxSupply', 0)
        
        if max_supply and max_supply > 0:
            supply_percent = (circulating_supply / max_supply) * 100
        else:
            supply_percent = 0 

        year_high = self.info.get('fiftyTwoWeekHigh', 0)
        year_low = self.info.get('fiftyTwoWeekLow', 0)
        current_price = self.data['Close'].iloc[-1]

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
            "range_position": range_position 
        }

    def analyze_sentiment(self):
        """
        Fetches news from Yahoo Finance OR Google News RSS (Fallback).
        """
        news_items = []
        
        # --- SOURCE 1: Yahoo Finance ---
        try:
            asset = yf.Ticker(self.ticker)
            yf_news = asset.news
            if yf_news:
                for item in yf_news[:5]:
                    title = item.get('title')
                    # CRITICAL FIX: Only add if title is a valid string
                    if title and isinstance(title, str):
                        news_items.append({
                            "title": title,
                            "link": item.get('link'),
                            "publisher": item.get('publisher', 'Yahoo Finance'),
                        })
        except Exception:
            pass 

        # --- SOURCE 2: Google News RSS Fallback ---
        if len(news_items) < 2:
            try:
                query = f"{self.clean_ticker} crypto currency"
                url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
                response = requests.get(url, timeout=5)
                soup = BeautifulSoup(response.content, features="xml")
                
                items = soup.findAll('item')[:5] 
                for item in items:
                    # Safety check for XML tags
                    if item.title and item.title.text:
                        news_items.append({
                            "title": item.title.text,
                            "link": item.link.text if item.link else "#",
                            "publisher": item.source.text if item.source else "Google News"
                        })
            except Exception as e:
                print(f"Google News error: {e}")

        # --- Analyze Sentiment ---
        total_polarity = 0
        analyzed_news = []
        
        if not news_items:
            return {"score": 0, "text": "Neutral (No News)", "news_list": []}

        for item in news_items:
            try:
                # Double safety check before passing to TextBlob
                if item['title']:
                    blob = TextBlob(str(item['title']))
                    polarity = blob.sentiment.polarity
                    total_polarity += polarity
                    
                    analyzed_news.append({
                        "title": item['title'],
                        "publisher": item['publisher'],
                        "link": item['link'],
                        "sentiment": polarity
                    })
            except Exception:
                continue # Skip bad items

        avg_polarity = total_polarity / len(analyzed_news) if analyzed_news else 0
        
        if avg_polarity > 0.1: sent_text = "Bullish 🟢"
        elif avg_polarity < -0.1: sent_text = "Bearish 🔴"
        else: sent_text = "Neutral ⚪"

        return {
            "score": avg_polarity,
            "text": sent_text,
            "news_list": analyzed_news
        }

    def calculate_confidence_score(self, tech, fund, sent):
        score = 50 

        # Technicals (40%)
        if tech['rsi'] < 30: score += 10    
        elif tech['rsi'] > 70: score -= 10  
        elif tech['rsi'] > 50: score += 2   
        
        if "Uptrend" in tech['trend']: score += 10
        elif "Downtrend" in tech['trend']: score -= 15
        
        if tech['current_price'] > tech['ema_200']: score += 5

        # Fundamentals (30%)
        if fund['vol_mcap_ratio'] > 0.10: score += 10  
        elif fund['vol_mcap_ratio'] < 0.02: score -= 5 

        if fund['range_position'] < 20: score += 10
        elif fund['range_position'] > 90: score -= 10

        # Sentiment (30%)
        sent_impact = sent['score'] * 15
        score += sent_impact

        return max(0, min(100, score))
