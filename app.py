import streamlit as st
import pandas as pd
import datetime
import gspread
from google.oauth2.service_account import Credentials
from streamlit_calendar import calendar
# LINE Messaging API SDK
from linebot import LineBotApi
from linebot.models import TextSendMessage

# --- ページ設定 ---
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

# --- LINE Messaging API 送信関数 ---
def send_line_broadcast(message_text):
    try:
        if "line" in st.secrets["connections"] and "access_token" in st.secrets["connections"]["line"]:
            token = st.secrets["connections"]["line"]["access_token"]
            line_bot_api = LineBotApi(token)
            # ブロードキャスト（友達登録している全員＝二人に一斉送信）
            line_bot_api.broadcast(TextSendMessage(text=message_text))
        else:
            print("LINEアクセストークンが設定されていません")
    except Exception as e:
        st.warning(f"LINE送信エラー（記録は保存されました）: {e}")

# --- データの読み込み ---
try:
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    
    if not df.empty:
        df['数値'] = pd.to_numeric(df['数値'], errors='coerce').fillna(0)
        if '日付' in df.columns:
            # 日付処理の強化
            df['日付'] = pd.to_datetime(df['日付'], errors='coerce')
            df = df.dropna(subset=['日付']) # 無効な日付を削除
            df['日付_str'] = df['日付'].dt.strftime('%Y-%m-%d')
            df['年月'] = df['日付'].dt.strftime("%Y-%m")
    else:
        df = pd.DataFrame(columns=['日付', '名前', '種目', '数値', '単位', '日付_str', '年月'])

except Exception as e:
    st.error(f"データ読み込みエラー: {e}")
    df = pd.DataFrame()

# --- 共通設定 ---
today = datetime.date.today()
current_month = today.strftime("%Y-%m")
goals = {"プランク": 100, "腹筋": 1000, "レッグレイズ": 1000}
user = st.sidebar.radio("ユーザーを選択", ["士温", "咲希"])

tab1, tab2, tab3, tab4 = st.tabs(["📊 協力メーター", "📅 カレンダー", "📝 記録する", "📜 分析・履歴"])

# --- タブ1: 協力メーター ---
with tab1:
    st.header(f"{current_month} の進捗")
    if not df.empty:
        month_df = df[df['年月'] == current_month]
        for menu, goal in goals.items():
            current_sum = month_df[month_df['種目'] == menu]['数値'].sum()
            progress = min(float(current_sum) / goal, 1.0)
            st.write(f"**{menu}**: {int(current_sum)} / {goal}")
            st.progress(progress)
    else:
        st.info("データがありません")

# --- タブ2: カレンダー ---
with tab2:
    st.header("トレーニングカレンダー")
    calendar_events = []
    if not df.empty and '日付_str' in df.columns:
        summary = df.groupby(['日付_str', '名前']).size().reset_index()
        for _, row in summary.iterrows():
            emoji = "🔵" if row['名前'] == "士温" else "🌸"
            color = "#1E90FF" if row['名前'] == "士温" else "#FF69B4"
            calendar_events.append({
                "title": emoji,
                "start": row['日付_str'], "end": row['日付_str'], "allDay": True,
                "backgroundColor": color, "borderColor": color
            })

    calendar_options = {
        "headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth"},
        "initialView": "dayGridMonth",
        "locale": "ja",
        "height": 550,
        "contentHeight": "auto"
    }
    calendar(events=calendar_events, options=calendar_options)

# --- タブ3: 記録する（Messaging API対応） ---
with tab3:
    st.header(f"{user} の記録入力")
    date_input = st.date_input("日付を選択", today)
    menu_choice = st.selectbox("メニュー", ["プランク", "腹筋", "レッグレイズ"])
    unit = "分" if menu_choice == "プランク" else "回"
    value = st.number_input(f"内容 ({unit})", min_value=0, step=1)
    
    if st.button("記録を保存"):
        date_str = date_input.strftime("%Y-%m-%d")
        new_row = [date_str, user, menu_choice, value, unit]
        try:
            worksheet.append_row(new_row)
            
            # LINE通知メッセージ作成
            emoji = "💪" if user == "士温" else "🌸"
            message = f"{emoji} {user} が記録しました！\n\n📝 メニュー: {menu_choice}\n🔢 回数: {value} {unit}\n📅 日付: {date_str}"
            
            # 送信実行
            send_line_broadcast(message)
            
            st.success("✅ 保存＆LINE通知しました！")
            st.balloons()
            st.rerun()
        except Exception as e:
            st.error(f"保存失敗: {e}")

# --- タブ4: 分析・履歴 ---
with tab4:
    st.header("🏆 分析・履歴")
    if not df.empty:
        st.subheader("👤 個人の累計")
        st.table(df.pivot_table(index='種目', columns='名前', values='数値', aggfunc='sum').fillna(0).astype(int))
        with st.expander("詳細履歴を見る"):
            st.dataframe(df[['日付_str', '名前', '種目', '数値']].sort_values('日付_str', ascending=False))
