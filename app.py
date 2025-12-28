import streamlit as st
import plotly.graph_objects as go
from analysis_engine import CryptoAnalyzer

st.set_page_config(page_title="Crypto 360 Analyzer", layout="wide")

st.title("🪙 360° Crypto Investment Analyzer")
st.markdown("Analyze **Fundamental, Technical, and Sentiment** factors to get a confidence score.")

# Sidebar for Input
with st.sidebar:
    ticker_input = st.text_input("Enter Coin Symbol (e.g., BTC, ETH, SOL)", value="BTC")
    analyze_btn = st.button("Analyze Coin")

if analyze_btn:
    with st.spinner(f"Analyzing {ticker_input}... Fetching data from API..."):
        analyzer = CryptoAnalyzer(ticker_input)
        success = analyzer.fetch_data()

        if not success:
            st.error(f"Could not fetch data for {ticker_input}. Please check the symbol.")
        else:
            # Run Analyses
            tech = analyzer.analyze_technicals()
            fund = analyzer.analyze_fundamentals()
            sent = analyzer.analyze_sentiment()
            
            # Check if analyses returned valid data
            if tech and fund and sent:
                score = analyzer.calculate_confidence_score(tech, fund, sent)

                # --- DISPLAY DASHBOARD ---
                
                # 1. HEADLINE SCORE
                col1, col2, col3 = st.columns([1,2,1])
                with col2:
                    st.metric(label="Investment Confidence Score (0-100)", value=f"{score:.0f}/100")
                    if score > 70:
                        st.success("Verdict: STRONG BUY 🚀")
                    elif score > 50:
                        st.info("Verdict: MODERATE BUY / HOLD 👍")
                    elif score > 30:
                        st.warning("Verdict: WATCH / RISKY ⚠️")
                    else:
                        st.error("Verdict: STRONG SELL / AVOID 🛑")
                    
                    st.progress(score / 100)

                st.divider()

                # 2. DETAILED BREAKDOWN TABS
                tab1, tab2, tab3 = st.tabs(["📊 Technicals", "💰 Fundamentals", "📢 Sentiment"])

                with tab1:
                    st.subheader("Technical Analysis")
                    t_col1, t_col2, t_col3 = st.columns(3)
                    t_col1.metric("Current Price", f"${tech['current_price']:,.2f}")
                    t_col2.metric("RSI (14)", f"{tech['rsi']:.2f}")
                    t_col3.metric("Trend", tech['trend'])

                    st.write(f"**Support:** ${tech['support']:,.2f} | **Resistance:** ${tech['resistance']:,.2f}")
                    
                    # Chart
                    fig = go.Figure()
                    
                    # Candlestick
                    fig.add_trace(go.Candlestick(x=analyzer.data.index,
                                    open=analyzer.data['Open'],
                                    high=analyzer.data['High'],
                                    low=analyzer.data['Low'],
                                    close=analyzer.data['Close'],
                                    name='Price'))
                    
                    # CORRECTED LINES: Fetching data from analyzer.data instead of 'tech' dictionary
                    if 'EMA_50' in analyzer.data.columns:
                        fig.add_trace(go.Scatter(x=analyzer.data.index, y=analyzer.data['EMA_50'], 
                                                 line=dict(color='orange', width=1), name='EMA 50'))
                    
                    if 'EMA_200' in analyzer.data.columns:
                        fig.add_trace(go.Scatter(x=analyzer.data.index, y=analyzer.data['EMA_200'], 
                                                 line=dict(color='blue', width=1), name='EMA 200'))
                        
                    fig.update_layout(title=f"{ticker_input} Price Chart with EMA", height=500)
                    st.plotly_chart(fig, use_container_width=True)

                with tab2:
                    st.subheader("Fundamental Analysis")
                    f_col1, f_col2 = st.columns(2)
                    f_col1.metric("Market Cap", f"${fund['market_cap']:,.0f}")
                    f_col2.metric("24h Volume", f"${fund['volume']:,.0f}")
                    
                    st.metric("Volume / Market Cap Ratio", f"{fund['vol_mcap_ratio']:.4f}")
                    if fund['vol_mcap_ratio'] > 0.05:
                        st.caption("✅ High liquidity relative to size.")
                    else:
                        st.caption("⚠️ Low liquidity relative to size.")

                with tab3:
                    st.subheader("Sentiment Analysis (News)")
                    st.metric("Sentiment Score", f"{sent['score']:.2f}", sent['text'])
                    
                    st.write("### Recent Headlines Analyzed:")
                    for news in sent['headlines']:
                        st.text(f"• {news}")
            else:
                st.error("Error processing data. Try a different coin.")
