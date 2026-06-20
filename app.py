import streamlit as st
import ccxt
import pandas as pd
import pandas_ta_classic as ta
import plotly.graph_objects as go
import google.generativeai as genai
import markdown 
import base64

# 1. 网页全局配置
st.set_page_config(page_title="ETHUSDT 机构级终端", layout="wide", initial_sidebar_state="collapsed")

# 💡 核心排版、色彩定制与打印优化 CSS
st.markdown("""
    <style>
           .block-container { padding-top: 2rem; padding-bottom: 2rem; }
           
           /* 定制左侧生成按钮为专业金融蓝 */
           div.stButton > button {
               background-color: #2E86C1 !important;
               color: white !important;
               border: none !important;
               height: 52px !important;
               font-size: 16px !important;
               font-weight: bold !important;
               border-radius: 8px !important;
               margin-top: 10px !important;
               box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
               transition: all 0.3s ease;
           }
           div.stButton > button:hover {
               background-color: #1B4F72 !important;
               box-shadow: 0 6px 8px rgba(0,0,0,0.15) !important;
           }

           /* 🖨️ 打印时隐藏所有控制区，只保留底部纯文本报告 */
           @media print {
               header, [data-testid="stSidebar"], [data-testid="column"] { display: none !important; }
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

# 4. 生成超级 Prompt (💡 增加防插针的实战常识与清爽排版)
def generate_resonance_prompt(data):
    return f"""
    作为一位顶级的加密货币【超短线（Scalping）】机构交易员，请基于以下 ETH/USDT 永续合约实时快照，输出深度实战报告：
    
    【行情快照】
    - 1小时：收盘价 ${data['1h']['close']:.2f} | RSI {data['1h']['RSI_14']:.2f} | MACD {data['1h']['MACD_12_26_9']:.2f} | 布林带 [{data['1h']['BBL_20_2.0']:.2f}, {data['1h']['BBU_20_2.0']:.2f}]
    - 15分钟：收盘价 ${data['15m']['close']:.2f} | RSI {data['15m']['RSI_14']:.2f} | MACD {data['15m']['MACD_12_26_9']:.2f} | 布林带 [{data['15m']['BBL_20_2.0']:.2f}, {data['15m']['BBU_20_2.0']:.2f}]
    - 5分钟：收盘价 ${data['5m']['close']:.2f} | RSI {data['5m']['RSI_14']:.2f} | MACD {data['5m']['MACD_12_26_9']:.2f} | 布林带 [{data['5m']['BBL_20_2.0']:.2f}, {data['5m']['BBU_20_2.0']:.2f}]
    
    【必须严格按以下结构输出，使用 Markdown】：
    1. 🧭 核心趋势定调：一句话极简总结多空力量。
    2. 🧱 关键点位矩阵（必须严格使用 Markdown 表格，指出上方两档阻力与下方两档支撑，并说明理由）：
       | 关键点位 | 价格 | 判定技术依据 | 攻防意义 |
       | :--- | :--- | :--- | :--- |
       | 阻力 R2 | $xxx.xx | ... | ... |
       | 阻力 R1 | $xxx.xx | ... | ... |
       | 当前价位 | ${data['5m']['close']:.2f} | 现价 | 观察突破方向 |
       | 支撑 S1 | $xxx.xx | ... | ... |
       | 支撑 S2 | $xxx.xx | ... | ... |
    3. 🔬 多级别共振剖析：结合各级别 RSI 超买超卖与 MACD 动能，深度剖析当前是共振发力还是指标背离。
    4. ⚔️ 实战操作预案（超短线持仓）：
       - 【操作方向】与【进场区间】（给出明确的核心进场价）。
       - 【精确止损价】。⚠️实战硬性规定：止损必须基于技术结构（如前低、支撑位等）。考虑 ETH 的正常波动摩擦，**严禁设置极小空间（如小于 2 美元）的无效止损**，以免被市场噪音轻易扫损。
       - 【阶梯止盈价】（TP1, TP2）。
       - ⚖️【盈亏比验算】：请用一句话简明列出预期盈亏比的绝对值（即 TP1利润空间 ÷ 止损空间）。必须确保该数值 >= 1.5，否则说明当前非高胜率开仓良机，直接建议观望。排版要求清爽专业，**严禁像做算术题一样写出冗长的加减乘除推导过程**。
    """

def create_print_button(md_text, is_active):
    # 如果还没有生成报告，显示灰色不可点击状态
    if not is_active:
        return '<div style="display: block; width: 100%; text-align: center; padding: 14px; background-color: #F2F3F4; color: #A6ACAF; border: 2px dashed #BDC3C7; border-radius: 8px; font-weight: bold; font-size: 16px; margin-top: 10px; cursor: not-allowed; box-sizing: border-box;">🖨️ 下载独立打印版 (请先生成策略)</div>'

    # 生成报告后，激活为绿色按钮
    html_content = markdown.markdown(md_text, extensions=['tables'])
    full_html = f"""
    <!DOCTYPE html><html><head><meta charset="utf-8"><title>ETHUSDT 机构级深度研报</title>
    <style>
        body {{ font-family: 'Microsoft YaHei', sans-serif; line-height: 1.8; color: #1a1a1a; max-width: 850px; margin: 0 auto; padding: 40px; }}
        h1, h2, h3 {{ color: #1E90FF; border-bottom: 1px solid #eee; padding-bottom: 10px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; font-size: 14px; }}
        th, td {{ border: 1px solid #e0e0e0; padding: 12px 15px; text-align: left; }}
        th {{ background-color: #f8f9fa; }}
        @media print {{ body {{ padding: 0; }} }}
    </style></head><body onload="setTimeout(() => window.print(), 500)">
    <h1 style="text-align: center;">🚀 ETH/USDT 超短线共振交易报告</h1><hr>{html_content}</body></html>
    """
    b64 = base64.b64encode(full_html.encode('utf-8')).decode()
    return f'<a href="data:text/html;base64,{b64}" download="ETHUSDT_打印版报告.html" style="display: block; width: 100%; text-align: center; padding: 16px; background-color: #27AE60; color: white; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px; margin-top: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); box-sizing: border-box;">🖨️ 下载独立打印版 (双击打开生成 PDF)</a>'


# 5. UI 全新排版落地
st.markdown("### 🤖 ETHUSDT 机构级超短线终端") 

# 第一层：图表与数据矩阵
col_chart, col_metrics = st.columns([7, 3])

with col_chart:
    st.markdown("#### 📊 5分钟快照") 
    current_price = df_5m.iloc[-1]['close']
    st.markdown(f"<div style='text-align: center; color: #1E90FF; font-size: 4rem; font-weight: 900; margin-bottom: -10px; font-family: Arial, sans-serif;'>{current_price:.2f}</div>", unsafe_allow_html=True)
    fig = go.Figure(data=[go.Candlestick(x=df_5m['timestamp'], open=df_5m['open'], high=df_5m['high'], low=df_5m['low'], close=df_5m['close'], name='K线')])
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), xaxis_rangeslider_visible=False, height=350)
    st.plotly_chart(fig, use_container_width=True)

with col_metrics:
    st.markdown("#### 🎛️ 实时动能矩阵") 
    st.markdown("<br>", unsafe_allow_html=True) # 增加一点顶部间距
    
    # 提取核心数据
    macd_1h = multi_data['1h']['MACD_12_26_9']
    rsi_15m = multi_data['15m']['RSI_14']
    bb_width_5m = multi_data['5m']['BBU_20_2.0'] - multi_data['5m']['BBL_20_2.0']
    
    # 判断情绪状态
    trend_color, trend_text = ("🔴 空头控盘", "需警惕做多") if macd_1h < 0 else ("🟢 多头控盘", "回踩可接多")
    rsi_state = "🔥 严重超买 (防回落)" if rsi_15m > 70 else "❄️ 严重超卖 (防反弹)" if rsi_15m < 30 else "⚡ 震荡区间 (待突破)"
    
    # 使用多彩色块丰富版面
    st.info(f"**1H 宏观趋势：{trend_color}**\n\nMACD值: {macd_1h:.2f} | 策略: {trend_text}")
    st.warning(f"**15M 波段情绪：{rsi_state}**\n\n当前 RSI: {rsi_15m:.2f}")
    st.success(f"**5M 短线空间：${bb_width_5m:.2f}**\n\n布林带上下轨宽度，值越小说明面临变盘")

st.markdown("---")

# 第二层：中控操作按钮
if 'report_text' not in st.session_state:
    st.session_state.report_text = ""

col_btn_gen, col_btn_dl = st.columns(2)

with col_btn_gen:
    generate_clicked = st.button("🚀 综合 [1H+15M+5M] 数据生成策略", use_container_width=True)

# 必须先处理生成逻辑，再渲染右侧的下载按钮，确保状态实时同步
if generate_clicked:
    if not api_key:
        st.error("⚠️ 请先在侧边栏填入 API Key！")
    elif not selected_model:
        st.error("⚠️ 正在连接模型，请稍候...")
    else:
        with st.spinner(f"正在进行机构级多维度计算..."):
            try:
                model = genai.GenerativeModel(selected_model)
                response = model.generate_content(generate_resonance_prompt(multi_data))
                st.session_state.report_text = response.text 
            except Exception as e:
                st.error(f"调用失败，报错信息: {e}")

with col_btn_dl:
    has_report = bool(st.session_state.get('report_text'))
    st.markdown(create_print_button(st.session_state.get('report_text', ''), has_report), unsafe_allow_html=True)

# 第三层：底部全宽报告区
if st.session_state.get('report_text'):
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 📜 深度共振研判报告")
    st.markdown(st.session_state.report_text)
