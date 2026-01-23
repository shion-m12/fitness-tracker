import streamlit as st
import pandas as pd
import datetime
import gspread
from google.oauth2.service_account import Credentials
from streamlit_calendar import calendar

st.set_page_config(page_title="筋トレ記録", layout="centered")
st.title("💪 筋トレ記録 & 協力メーター")

# --- 接続設定 ---
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/19T5OnYjgOsWX05mQ1fc5IOJ1qd98jCB_5mnd_mKNyDw/edit"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

@st.cache_resource
def connect_to_gsheets():
    try:
        secrets_dict = dict(st.secrets["connections"]["gsheets"])
        if "private_key" in secrets_dict:
            secrets_dict["private_key"] = secrets_dict["private_key"].replace("\\n", "\n")
        creds = Credentials.from_service_account_info(secrets_dict, scopes=SCOPES)
        client = gspread.authorize(creds)
        return client.open_by_url(SPREADSHEET_URL).sheet1
    except Exception as e:
        st.error(f"接続エラー: {e}")
        return None

worksheet = connect_to_gsheets()
if not worksheet: st.stop()

# --- データの読み込みと強力な型変換 ---
try:
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    
    # データがある場合のみ処理
    if not df.empty:
        # 数値変換
        df['数値'] = pd.to_numeric(df['数値'], errors='coerce').fillna(0)
        
        # 【重要】日付を強制的にカレンダー用文字列(YYYY-MM-DD)に変換
        if '日付' in df.columns:
            df['日付'] = pd.to_datetime(df['日付']).dt.strftime('%Y-%m-%d')
            
except Exception as e:
    st.error(f"データ読み込みエラー: {e}")
    df = pd.DataFrame(columns=['日付', '名前', '種目', '数値', '単位'])

# --- 今月の設定 ---
today = datetime.date.today()
current_month = today.strftime("%Y-%m")
user = st.sidebar.radio("ユーザーを選択", ["士温", "咲希"])

tab1, tab2, tab3, tab4 = st.tabs(["📊 協力メーター", "📅 カレンダー", "📝 記録する", "📜 履歴"])

# --- タブ1: 協力メーター ---
with tab1:
    st.header(f"{current_month} の協力メーター")
    goals = {"プランク": 100, "腹筋": 1000, "レッグレイズ": 1000}
    
    if not df.empty and '日付' in df.columns:
        df['年月'] = pd.to_datetime(df['日付']).dt.strftime("%Y-%m")
        month_df = df[df['年月'] == current_month]
        
        for menu, goal in goals.items():
            current_sum = month_df[month_df['種目'] == menu]['数値'].sum()
            progress = min(float(current_sum) / goal, 1.0)
            st.subheader(menu)
            st.progress(progress)
            st.write(f"合計: {int(current_sum)} / {goal}")

# --- タブ2: カレンダー（修正版） ---
with tab2:
    st.header("トレーニングカレンダー")
    
    # デバッグ表示：ここにデータが出なければ読み込みの問題
    with st.expander("データの中身を確認する（デバッグ用）"):
        st.dataframe(df)

    calendar_events = []
    if not df.empty and '日付' in df.columns:
        # 日付と名前でまとめてカウント
        summary = df.groupby(['日付', '名前']).size().reset_index()
        
        for _, row in summary.iterrows():
            # 色とアイコンの設定
            emoji = "🔵" if row['名前'] == "士温" else "🌸"
            color = "#1E90FF" if row['名前'] == "士温" else "#FF69B4"
            
            calendar_events.append({
                "title": f"{emoji}",  # 文字が多いと見づらいので絵文字だけにしてみる
                "start": row['日付'], # YYYY-MM-DD形式の文字列
                "end": row['日付'],
                "allDay": True,
                "backgroundColor": color,
                "borderColor": color
            })

    # カレンダーの表示オプション
    calendar_options = {
        "headerToolbar": {
            "left": "today prev,next",
            "center": "title",
            "right": "dayGridMonth,listMonth"
        },
        "initialView": "dayGridMonth",
        "locale": "ja",
    }
    
    calendar(events=calendar_events, options=calendar_options)

# --- タブ3: 記録する ---
with tab3:
    st.header(f"{user} の記録入力")
    date_input = st.date_input("日付を選択", today)
    menu_choice = st.selectbox("メニュー", ["プランク", "腹筋", "レッグレイズ"])
    unit = "分" if menu_choice == "プランク" else "回"
    value = st.number_input(f"内容 ({unit})", min_value=0, step=1)
    
    if st.button("記録を保存"):
        new_row = [date_input.strftime("%Y-%m-%d"), user, menu_choice, value, unit]
        try:
            worksheet.append_row(new_row)
            st.success("保存しました！")
            st.balloons()
            st.rerun()
        except Exception as e:
            st.error(f"保存失敗: {e}")

# --- タブ4: 履歴 ---
with tab4:
    st.header("履歴")
    if not df.empty:
        st.dataframe(df.sort_values('日付', ascending=False))
