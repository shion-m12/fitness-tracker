import streamlit as st
import pandas as pd
import datetime
from streamlit_calendar import calendar

# --- ページ設定 ---
st.set_page_config(page_title="筋トレ記録", layout="centered")
st.title("筋トレ記録 & 協力メーター")

# --- スプレッドシート設定 ---
# ⚠️ 共有設定を「リンクを知っている全員が編集者」にしてください
spreadsheet_id = "19T5OnYjgOsWX05mQ1fc5IOJ1qd98jCB_5mnd_mKNyDw"
csv_export_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv"

# データの読み込み
@st.cache_data(ttl=0)
def load_data():
    try:
        return pd.read_csv(csv_export_url)
    except:
        return pd.DataFrame(columns=['日付', '名前', '種目', '数値', '単位'])

df = load_data()

# 日付の処理
if not df.empty:
    df['日付'] = pd.to_datetime(df['日付']).dt.date
    df['数値'] = pd.to_numeric(df['数値'], errors='coerce').fillna(0)

today = datetime.date.today()
current_month = today.strftime("%Y-%m")
user = st.sidebar.radio("ユーザーを選択", ["士温", "咲希"])

tab1, tab2, tab3, tab4 = st.tabs(["協力メーター", "カレンダー", "記録する", "過去の履歴"])

# --- タブ1: メーター ---
with tab1:
    st.header(f"{current_month} のメーター")
    goals = {"プランク": 100, "腹筋": 1000, "レッグレイズ": 1000}
    df_calc = df.copy()
    df_calc['年月'] = pd.to_datetime(df_calc['日付']).dt.strftime("%Y-%m")
    m_df = df_calc[df_calc['年月'] == current_month]
    for menu, goal in goals.items():
        curr = m_df[m_df['種目'] == menu]['数値'].sum()
        st.subheader(menu)
        st.progress(min(float(curr) / goal, 1.0))
        st.write(f"現在: {int(curr)} / 目標: {goal}")

# --- タブ2: カレンダー ---
with tab2:
    events = []
    if not df.empty:
        summary = df.groupby(['日付', '名前']).size().reset_index()
        for _, row in summary.iterrows():
            emoji = "🔵" if row['名前'] == "士温" else "🌸"
            events.append({"title": f"{row['名前']} {emoji}", "start": str(row['日付']), "allDay": True, "color": "#1E90FF" if row['名前'] == "士温" else "#FF69B4"})
    calendar(events=events, options={"locale": "ja"})

# --- タブ3: 記録する ---
with tab3:
    st.header(f"{user} の記録入力")
    d_in = st.date_input("日付", today)
    m_in = st.selectbox("メニュー", ["プランク", "腹筋", "レッグレイズ"])
    v_in = st.number_input("数値", min_value=0, step=1)
    
    st.warning("⚠️ 現在、保存機能はスプレッドシートを直接開いて入力する形が最も確実です。")
    st.link_button("スプレッドシートを開いて入力", f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit")
    
    st.write("※スプレッドシートに追記して戻ってくると、カレンダーやメーターに反映されます。")
