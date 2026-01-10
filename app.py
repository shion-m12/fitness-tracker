import streamlit as st
import pandas as pd
import datetime
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="筋トレ記録", layout="centered")
st.title("筋トレ記録 & 協力メーター")

# --- スプレッドシート接続 ---
url = "https://docs.google.com/spreadsheets/d/19T5OnYjgOsWX05mQ1fc5IOJ1qd98jCB_5mnd_mKNyDw/edit?usp=sharing"

conn = st.connection("gsheets", type=GSheetsConnection)

# データの読み込み
df = conn.read(spreadsheet=url, ttl=0)

# --- サイドバー：ユーザー切り替え ---
user = st.sidebar.radio("ユーザーを選択", ["士温", "咲希"])

tab1, tab2 = st.tabs(["協力メーター", "記録する"])

with tab1:
    st.header("協力メーター")
    # 腹筋とレッグレイズを1000に設定
    goals = {"プランク": 100, "腹筋": 1000, "レッグレイズ": 1000}
    
    if not df.empty:
        df['数値'] = pd.to_numeric(df['数値'], errors='coerce').fillna(0)

    for menu, goal in goals.items():
        current_sum = df[df['種目'] == menu]['数値'].sum()
        progress = min(float(current_sum) / goal, 1.0)
        st.subheader(menu)
        st.progress(progress)
        st.write(f"現在の合計: {current_sum} / 目標: {goal}")

with tab2:
    st.header(f"{user} の記録入力")
    
    # 日付を手入力（カレンダーから選択）できるように変更
    date_input = st.date_input("日付を選択", datetime.date.today())
    
    menu_choice = st.selectbox("メニューを選択", ["プランク", "腹筋", "レッグレイズ"])
    unit = "分" if menu_choice == "プランク" else "回"
    
    value = st.number_input(f"内容を入力 ({unit})", min_value=0, step=1)
    
    if st.button("記録を保存"):
        new_row = pd.DataFrame([{
            '日付': date_input.strftime("%Y-%m-%d"),
            '名前': user,
            '種目': menu_choice,
            '数値': value,
            '単位': unit
        }])
        
        # 保存処理
        updated_df = pd.concat([df, new_row], ignore_index=True)
        conn.update(spreadsheet=url, data=updated_df)
        
        st.success(f"保存しました")
        st.rerun()

st.write("---")
st.subheader("直近の記録")
st.dataframe(df.tail(10))