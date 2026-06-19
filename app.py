import streamlit as st
import ccxt
import pandas as pd
import pandas_ta_classic as ta
import plotly.graph_objects as go
import google.generativeai as genai

# 1. 网页全局配置
st.set_page_config(page_title="ETHUSDT 超短线共振终端", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
           .block-container {
                padding-top: 2rem;
                padding-bottom: 0rem;
            }
    </style>
    """, unsafe_allow_html=True)

# 2. 侧边栏：安全配置 (结合 Secrets 自动读取)
with st.sidebar:
    st.markdown("### ⚙️ 系统设置")
    
    # 💡 自动读取云端金库密码，若没有则显示输入框
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
        st.success("✅ 已自动连接云端 API 密钥")
    else:
        api_key = st.text_input("请输入你的 Gemini API Key", type="password")
    
    selected_model = None
    if api_key:
        genai.configure(api_key=api_key)
        try:
            available_models = [m.name.replace("models/", "") for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            if available_models:
                default_idx = available_models.index('gemini-1.5-pro') if 'gemini-1.5-pro' in available_models else 0
                selected_model = st.selectbox("🤖 选择分析模型", available_models, index=default_idx)
        except Exception as e:
            st.error(f"模型列表拉取失败: {e}")

# 3. 核心数据引擎 (云端直连版)
@st.cache_data(ttl=15) 
def fetch_resonance_data():
    exchange = ccxt.bitget() 
    
    timeframes = ['5m', '15m', '1h']
    resonance_data = {}
    chart_df = None
    
    for tf in timeframes:
        bars = exchange.fetch_ohlcv('ETH/USDT:USDT', timeframe=tf, limit=100)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms') + pd.Timedelta(hours=8)
        
        df.ta.rsi(length=14, append=True)
        df.ta.macd(fast=12, slow=26, signal=9, append=True)
        df.ta.bbands(length=20, std=2, append=True)
        
        resonance_data[tf] = df.iloc[-1]
        if tf == '5m':
            chart_df = df 
            
    return resonance_data, chart_df

try:
    multi_data, df_5m = fetch_resonance_data()
except Exception as e:
    st.error("数据拉取失败，请检查网络。")
    st.stop()

# 4. 生成超级 Prompt
def generate_resonance_prompt(data):
    return f"""
    作为一位资深的加密货币【超短线（Scalping）】交易专家，请基于以下 ETH/USDT 永续合约的三个时间级别实时数据，进行多级别共振深度分析：
    
    【1小时级别（大方向/关键阻力支撑）】
    - 收盘价: ${data['1h']['close']:.2f} | RSI: {data['1h']['RSI_14']:.2f} | MACD: {data['1h']['MACD_12_26_9']:.2f}
    - 布林带: [{data['1h']['BBL_20_2.0']:.2f}, {data['1h']['BBU_20_2.0']:.2f}]

    【15分钟级别（波段结构/动能）】
    - 收盘价: ${data['15m']['close']:.2f} | RSI: {data['15m']['RSI_14']:.2f} | MACD: {data['15m']['MACD_12_26_9']:.2f}
    - 布林带: [{data['15m']['BBL_20_2.0']:.2f}, {data['15m']['BBU_20_2.0']:.2f}]

    【5分钟级别（精准入场/短线情绪）】
    - 收盘价: ${data['5m']['close']:.2f} | RSI: {data['5m']['RSI_14']:.2f} | MACD: {data['5m']['MACD_12_26_9']:.2f}
    - 布林带: [{data['5m']['BBL_20_2.0']:.2f}, {data['5m']['BBU_20_2.0']:.2f}]
    
    【你的任务】
    1. 趋势共振研判：这三个级别是否形成共振？如果有分歧，目前该采取什么态度？
    2. 超短线操作策略：基于预期几分钟到两小时内平仓，当前是该市价进场、挂单还是观望？
    3. 点位建议：精确的进场区间、极小止损位和第一止盈位。排版清晰美观，重点加粗。
    """

# 5. UI 布局
st.markdown("### 🤖 ETHUSDT 超短线多级别共振终端") 

col_chart, col_ai = st.columns([3, 7])

with col_chart:
    st.markdown("#### 📊 5分钟快照") 
    
    current_price = df_5m.iloc[-1]['close']
    st.markdown(
        f"<div style='text-align: center; color: #1E90FF; font-size: 3.8rem; font-weight: 900; margin-bottom: -10px; font-family: Arial, sans-serif;'>{current_price:.2f}</div>", 
        unsafe_allow_html=True
    )
    
    fig = go.Figure(data=[go.Candlestick(x=df_5m['timestamp'],
                    open=df_5m['open'], high=df_5m['high'], low=df_5m['low'], close=df_5m['close'], name='K线')])
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), xaxis_rangeslider_visible=False, height=350)
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("##### ⏱️ 级别快览")
    st.caption(f"**1H RSI:** {multi_data['1h']['RSI_14']:.1f} | **15M RSI:** {multi_data['15m']['RSI_14']:.1f} | **5M RSI:** {multi_data['5m']['RSI_14']:.1f}")

with col_ai:
    st.markdown("#### 🧠 深度共振研判") 
    
    if st.button("🚀 综合 [1H+15M+5M] 数据生成策略", type="primary", use_container_width=True):
        if not api_key:
            st.error("⚠️ 请先在侧边栏填入 API Key！")
        elif not selected_model:
            st.error("⚠️ 还未获取到可用模型列表。请稍等几秒或检查网络。")
        else:
            with st.spinner(f"正在进行多级别共振计算..."):
                try:
                    model = genai.GenerativeModel(selected_model)
                    prompt = generate_resonance_prompt(multi_data)
                    response = model.generate_content(prompt)
                    
                    st.success("✅ 分析完成！请查阅下方策略：")
                    st.markdown("---")
                    st.markdown(response.text)
                except Exception as e:
                    st.error(f"调用失败，报错信息: {e}")
