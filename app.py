import streamlit as st
import ccxt
import pandas as pd
import pandas_ta_classic as ta
import plotly.graph_objects as go
import google.generativeai as genai

# 1. 网页全局配置
st.set_page_config(page_title="ETHUSDT 超短线共振终端", layout="wide", initial_sidebar_state="collapsed")

# 💡 核心排版与打印优化 CSS
st.markdown("""
    <style>
           .block-container {
                padding-top: 2rem;
                padding-bottom: 0rem;
            }
           /* 🖨️ 专为打印机（打包 PDF）准备的黑科技 */
           @media print {
               /* 打印时隐藏侧边栏、顶部栏和所有按钮 */
               header, [data-testid="stSidebar"], button { display: none !important; }
               /* 打印时隐藏左侧图表区，专心打印报告 */
               [data-testid="column"]:nth-child(1) { display: none !important; }
               /* 强制右侧报告区占满全屏宽度，并解除所有滚动条限制 */
               [data-testid="column"]:nth-child(2) { width: 100% !important; max-width: 100% !important; flex: 100% !important; }
               .stApp, .main, .block-container, div { overflow: visible !important; height: auto !important; }
           }
    </style>
    """, unsafe_allow_html=True)

# 2. 侧边栏：安全配置 
with st.sidebar:
    st.markdown("### ⚙️ 系统设置")
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

# 3. 核心数据引擎
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

# 4. 生成超级 Prompt (💡 报告内容史诗级升级)
def generate_resonance_prompt(data):
    return f"""
    作为一位顶级的加密货币【超短线（Scalping）】机构交易员，请基于以下 ETH/USDT 永续合约的三个时间级别实时快照，输出一份极具深度的实战交易报告：
    
    【行情数据快照】
    - 1小时级别：收盘价 ${data['1h']['close']:.2f} | RSI {data['1h']['RSI_14']:.2f} | MACD {data['1h']['MACD_12_26_9']:.2f} | 布林带 [{data['1h']['BBL_20_2.0']:.2f}, {data['1h']['BBU_20_2.0']:.2f}]
    - 15分钟级别：收盘价 ${data['15m']['close']:.2f} | RSI {data['15m']['RSI_14']:.2f} | MACD {data['15m']['MACD_12_26_9']:.2f} | 布林带 [{data['15m']['BBL_20_2.0']:.2f}, {data['15m']['BBU_20_2.0']:.2f}]
    - 5分钟级别：收盘价 ${data['5m']['close']:.2f} | RSI {data['5m']['RSI_14']:.2f} | MACD {data['5m']['MACD_12_26_9']:.2f} | 布林带 [{data['5m']['BBL_20_2.0']:.2f}, {data['5m']['BBU_20_2.0']:.2f}]
    
    【报告撰写要求（必须严格按以下结构输出，使用 Markdown，关键数字加粗）】
    1. 🧭 核心趋势定调：一句话总结当前多空力量对比（例如：大级别震荡，小级别看跌共振）。
    2. 🧱 关键支撑与阻力位（必须提供精确到小数点的价格）：
       - 上方阻力位（R1, R2）及其判定理由（结合布林带或各项指标）。
       - 下方支撑位（S1, S2）及其判定理由。
    3. 🔬 动能与共振深度剖析：从 1H 到 5M 逐级拆解，指出 RSI 是否超买超卖、MACD 动能变化，以及各级别之间是否存在冲突。
    4. ⚔️ 实战执行计划（预期持仓 5~120 分钟）：
       - 操作倾向（做多 / 做空 / 观望等待）。
       - 精确的【进场区间】。
       - 严格的【止损价位】（要求极小止损，盈亏比至少 1:2）。
       - 阶梯【止盈价位】（T1, T2）。
    5. ⚠️ 风险提示：说明在何种意外极端行情下，此策略将立刻失效（例如跌破某关键点位）。
    """

# 5. UI 布局
st.markdown("### 🤖 ETHUSDT 超短线多级别共振终端") 

col_chart, col_ai = st.columns([3, 7])

with col_chart:
    st.markdown("#### 📊 5分钟快照") 
    current_price = df_5m.iloc[-1]['close']
    st.markdown(f"<div style='text-align: center; color: #1E90FF; font-size: 3.8rem; font-weight: 900; margin-bottom: -10px; font-family: Arial, sans-serif;'>{current_price:.2f}</div>", unsafe_allow_html=True)
    
    fig = go.Figure(data=[go.Candlestick(x=df_5m['timestamp'], open=df_5m['open'], high=df_5m['high'], low=df_5m['low'], close=df_5m['close'], name='K线')])
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), xaxis_rangeslider_visible=False, height=350)
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"**1H RSI:** {multi_data['1h']['RSI_14']:.1f} | **15M RSI:** {multi_data['15m']['RSI_14']:.1f} | **5M RSI:** {multi_data['5m']['RSI_14']:.1f}")

with col_ai:
    st.markdown("#### 🧠 深度共振研判") 
    
    # 💡 状态保持：避免点击下载按钮时报告消失
    if 'report_text' not in st.session_state:
        st.session_state.report_text = ""
    
    if st.button("🚀 综合 [1H+15M+5M] 数据生成策略", type="primary", use_container_width=True):
        if not api_key:
            st.error("⚠️ 请先在侧边栏填入 API Key！")
        elif not selected_model:
            st.error("⚠️ 正在连接模型，请稍候...")
        else:
            with st.spinner(f"正在进行机构级多维度计算..."):
                try:
                    model = genai.GenerativeModel(selected_model)
                    response = model.generate_content(generate_resonance_prompt(multi_data))
                    st.session_state.report_text = response.text # 存入缓存
                except Exception as e:
                    st.error(f"调用失败，报错信息: {e}")

    # 显示报告与下载按钮
    if st.session_state.report_text:
        st.success("✅ 分析完成！")
        st.markdown("---")
        st.markdown(st.session_state.report_text)
        st.markdown("---")
        
        # 💡 新增的原生下载按钮
        st.download_button(
            label="💾 一键下载此报告 (.md)",
            data=st.session_state.report_text,
            file_name="ETHUSDT_超短线研报.md",
            mime="text/markdown",
            use_container_width=True
        )
