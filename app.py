import streamlit as st
import pandas as pd
import datetime
import gspread
from google.oauth2.service_account import Credentials
from streamlit_calendar import calendar
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
        if "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
            secrets_dict = dict(st.secrets["connections"]["gsheets"])
            if "private_key" in secrets_dict:
                secrets_dict["private_key"] = secrets_dict["private_key"].replace("\\n", "\n")
            creds = Credentials.from_service_account_info(secrets_dict, scopes=SCOPES)
            client = gspread.authorize(creds)
            return client.open_by_url(SPREADSHEET_URL).sheet1
        else:
            st.error("Secretsの設定が見つかりません")
            return None
    except Exception as e:
        st.error(f"接続エラー: {e}")
        return None

worksheet = connect_to_gsheets()
# 接続できなくてもカレンダーだけは表示させるためにstopしない（エラー表示のみ）

# --- LINE送信関数 ---
def send_line_broadcast(message_text):
    try:
        if "line" in st.secrets["connections"] and "access_token" in st.secrets["connections"]["line"]:
            token = st.secrets["connections"]["line"]["access_token"]
            line_bot_api = LineBotApi(token)
            line_bot_api.broadcast(TextSendMessage(text=message_text))
    except Exception as e:
        st.warning(f"LINE送信エラー: {e}")

# --- データの読み込み ---
df = pd.DataFrame()
try:
    if worksheet:
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        if not df.empty:
            df['数値'] = pd.to_numeric(df['数値'], errors='coerce').fillna(0)
            if '日付' in df.columns:
                df['日付'] = pd.to_datetime(df['日付'], errors='coerce')
                df = df.dropna(subset=['日付'])
                df['日付_str'] = df['日付'].dt.strftime('%Y-%m-%d')
                df['年月'] = df['日付'].dt.strftime("%Y-%m")
except Exception:
    pass # 読み込み失敗時は空のまま進む

# --- 共通設定 ---
today = datetime.date.today()
current_month = today.strftime("%Y-%m")
goals = {"プランク": 100, "腹筋": 1000, "レッグレイズ": 1000}
user = st.sidebar.radio("ユーザーを選択", ["士温", "咲希"])

tab1, tab2, tab3, tab4 = st.tabs(["📊 協力メーター", "📅 カレンダー", "📝 記録する", "📜 分析・履歴"])

# --- タブ1: 協力メーター ---
with tab1:
    st.header(f"{current_month} の進捗")
    if not df.empty and '年月' in df.columns:
        month_df = df[df['年月'] == current_month]
        if not month_df.empty:
            for menu, goal in goals.items():
                current_sum = month_df[month_df['種目'] == menu]['数値'].sum()
                progress = min(float(current_sum) / goal, 1.0)
                st.write(f"**{menu}**: {int(current_sum)} / {goal}")
                st.progress(progress)
        else:
            st.info("今月のデータはまだありません")
    else:
        st.info("データがありません。まずは記録してみましょう！")

# --- タブ2: カレンダー（修正版：データなしでも表示） ---
with tab2:
    st.header("トレーニングカレンダー")
    
    # 1. イベントリストを初期化（データがなくても空リストを用意）
    calendar_events = []
    
    # 2. データがある場合のみイベントを追加
    if not df.empty and '日付_str' in df.columns:
        summary = df.groupby(['日付_str', '名前']).size().reset_index()
        for _, row in summary.iterrows():
            emoji = "🔵" if row['名前'] == "士温" else "🌸"
            color = "#1E90FF" if row['名前'] == "士温" else "#FF69B4"
            calendar_events.append({
                "title": emoji,
                "start": row['日付_str'],
                "end": row['日付_str'],
                "allDay": True,
                "backgroundColor": color,
                "borderColor": color
            })

    # 3. カレンダーオプション設定
    calendar_options = {
        "headerToolbar": {
            "left": "prev,next today",
            "center": "title",
            "right": "dayGridMonth"
        },
        "initialView": "dayGridMonth",
        "locale": "ja",
        "height": 500,
        "contentHeight": "auto"
    }
    
    # 4. データの有無に関わらずカレンダーを描画（インデントをifの外に出しました）
    calendar(events=calendar_events, options=calendar_options)

# --- タブ3: 記録する ---
with tab3:
    st.header(f"{user} の記録入力")
    date_input = st.date_input("日付を選択", today)
    menu_choice = st.selectbox("メニュー", ["プランク", "腹筋", "レッグレイズ"])
    unit = "分" if menu_choice == "プランク" else "回"
    value = st.number_input(f"内容 ({unit})", min_value=0, step=1)
    
    if st.button("記録を保存"):
        if worksheet:
            date_str = date_input.strftime("%Y-%m-%d")
            new_row = [date_str, user, menu_choice, value, unit]
            try:
                worksheet.append_row(new_row)
                
                # LINE通知
                emoji = "💪" if user == "士温" else "🌸"
                msg = f"{emoji} {user} が記録しました！\n\n📝 メニュー: {menu_choice}\n🔢 回数: {value} {unit}\n📅 日付: {date_str}"
                send_line_broadcast(msg)
                
                st.success("✅ 保存＆LINE通知しました！")
                st.balloons()
                st.rerun()
            except Exception as e:
                st.error(f"保存失敗: {e}")
        else:
            st.error("スプレッドシートに接続できていません")

# --- タブ4: 分析・履歴 ---
with tab4:
    st.header("🏆 分析・履歴")
    if not df.empty and '日付' in df.columns:
        st.subheader("👤 個人の累計")
        st.table(df.pivot_table(index='種目', columns='名前', values='数値', aggfunc='sum').fillna(0).astype(int))
        
        st.divider()
        with st.expander("全データ履歴"):
            st.dataframe(df[['日付_str', '名前', '種目', '数値']].sort_values('日付_str', ascending=False))
    else:
        st.write("データが記録されるとここに分析が表示されます")
