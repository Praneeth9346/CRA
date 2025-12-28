import streamlit as st
import plotly.graph_objects as go
from analysis_engine import CryptoAnalyzer

st.set_page_config(page_title="Crypto 360 Pro", layout="wide")

st.title("🪙 360° Crypto Pro Analyzer")
st.markdown("Advanced Analysis: **Fundamental (Supply/Value)**, **Technical (Trend/RSI)**, and **Sentiment (News)**.")

# Sidebar
with st.sidebar:
    st.header("Analysis Settings")
    ticker_input = st.text_input("Symbol (e.g., BTC, ETH, DOGE)", value="BTC")
    analyze_btn = st.button("Run Deep Analysis 🔎")
    st.info("Note: Analysis uses real-time data from Yahoo Finance.")

if analyze_btn:
    with st.spinner(f"Gathering Deep Data for {ticker_input}..."):
        analyzer = CryptoAnalyzer(ticker_input)
        success = analyzer.fetch_data()

        if not success:
            st.error(f"❌ Could not find data for '{ticker_input}'. Try standard symbols like BTC, ETH, SOL.")
        else:
            # Run All Analyses
            tech = analyzer.analyze_technicals()
            fund = analyzer.analyze_fundamentals()
            sent = analyzer.analyze_sentiment()
            
            if tech and fund and sent:
                score = analyzer.calculate_confidence_score(tech, fund, sent)

                # --- HEADER SCORE ---
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.metric(label="💰 Current Price", value=f"${tech['current_price']:,.2f}")
                with col2:
                    st.metric(label="Investment Confidence", value=f"{score:.0f}/100")
                    
                # Score Bar
                progress_color = "green" if score > 70 else "orange" if score > 40 else "red"
                st.progress(score / 100)
                if score >= 75: st.success("💎 STRONG BUY / BULLISH")
                elif score >= 55: st.info("✅ BUY / ACCUMULATE")
                elif score >= 40: st.warning("⚠️ HOLD / NEUTRAL")
                else: st.error("🛑 SELL / AVOID")

                st.divider()

                # --- DETAILED TABS ---
                tab_tech, tab_fund, tab_news = st.tabs(["📊 Technicals", "🏦 Fundamentals", "📰 News & Sentiment"])

                # 1. TECHNICALS TAB
                with tab_tech:
                    c1, c2, c3 = st.columns(3)
                    c1.metric("RSI (14)", f"{tech['rsi']:.1f}", delta="Overbought" if tech['rsi']>70 else "Oversold" if tech['rsi']<30 else "Neutral", delta_color="inverse")
                    c2.metric("Trend", tech['trend'])
                    c3.metric("Support / Resist", f"${tech['support']:,.0f} / ${tech['resistance']:,.0f}")

                    # Interactive Chart
                    fig = go.Figure()
                    fig.add_trace(go.Candlestick(x=analyzer.data.index,
                                    open=analyzer.data['Open'], high=analyzer.data['High'],
                                    low=analyzer.data['Low'], close=analyzer.data['Close'], name='Price'))
                    
                    if 'EMA_50' in analyzer.data.columns:
                        fig.add_trace(go.Scatter(x=analyzer.data.index, y=analyzer.data['EMA_50'], line=dict(color='orange', width=1), name='EMA 50'))
                    if 'EMA_200' in analyzer.data.columns:
                        fig.add_trace(go.Scatter(x=analyzer.data.index, y=analyzer.data['EMA_200'], line=dict(color='blue', width=1), name='EMA 200'))
                        
                    fig.update_layout(height=500, xaxis_rangeslider_visible=False, title=f"{ticker_input} Price Action")
                    st.plotly_chart(fig, use_container_width=True)

                # 2. FUNDAMENTALS TAB
                with tab_fund:
                    st.subheader("Tokenomics & Valuation")
                    
                    fc1, fc2, fc3 = st.columns(3)
                    fc1.metric("Market Cap", f"${fund['market_cap']:,.0f}")
                    fc2.metric("24h Volume", f"${fund['volume']:,.0f}")
                    fc3.metric("Vol/MCap Ratio", f"{fund['vol_mcap_ratio']:.3f}", help=">0.05 is Healthy Liquidity")

                    st.divider()
                    
                    # Supply Section
                    st.write("**Supply Stats**")
                    if fund['max_supply']:
                        st.progress(fund['supply_percent'] / 100)
                        st.caption(f"{fund['supply_percent']:.1f}% of Max Supply Circulating ({fund['circulating_supply']:,.0f} / {fund['max_supply']:,.0f})")
                    else:
                        st.metric("Circulating Supply", f"{fund['circulating_supply']:,.0f}", "Unlimited Max Supply ⚠️")

                    st.divider()

                    # 52 Week Range Position
                    st.write(f"**Price Position in 52-Week Range** ({fund['range_position']:.0f}%)")
                    st.caption("0% = Yearly Low (Value Buy) | 100% = Yearly High (Potential Top)")
                    st.slider("", min_value=0.0, max_value=100.0, value=fund['range_position'], disabled=True)
                    col_low, col_high = st.columns(2)
                    col_low.write(f"Low: ${fund['year_low']:,.2f}")
                    col_high.write(f"High: ${fund['year_high']:,.2f}")

                # 3. NEWS TAB
                with tab_news:
                    st.subheader(f"Sentiment Analysis: {sent['text']}")
                    st.metric("Sentiment Score", f"{sent['score']:.2f}")
                    
                    st.markdown("### Latest Headlines")
                    if not sent['news_list']:
                        st.write("No recent news found.")
                    
                    for item in sent['news_list']:
                        # Color code sentiment
                        if item['sentiment'] > 0.1: s_icon = "🟢"
                        elif item['sentiment'] < -0.1: s_icon = "🔴"
                        else: s_icon = "⚪"
                        
                        st.markdown(f"""
                        **{s_icon} [{item['title']}]({item['link']})** *{item['publisher']}*
                        ---
                        """)

            else:
                st.error("Error processing technical data.")
