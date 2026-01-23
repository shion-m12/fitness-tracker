import streamlit as st
import pandas as pd
import datetime
import gspread
from google.oauth2.service_account import Credentials
from streamlit_calendar import calendar

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

# --- データの読み込み ---
try:
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    
    # データ処理
    if not df.empty:
        # 数値変換
        df['数値'] = pd.to_numeric(df['数値'], errors='coerce').fillna(0)
        # 日付変換（カレンダー用に文字列化）
        if '日付' in df.columns:
            df['日付'] = pd.to_datetime(df['日付'])
            df['日付_str'] = df['日付'].dt.strftime('%Y-%m-%d') # カレンダー用
            df['年月'] = df['日付'].dt.strftime("%Y-%m") # 集計用
    else:
        # 空の場合の列定義
        df = pd.DataFrame(columns=['日付', '名前', '種目', '数値', '単位', '日付_str', '年月'])

except Exception as e:
    st.error(f"データ読み込みエラー: {e}")
    st.stop()

# --- 共通設定 ---
today = datetime.date.today()
current_month = today.strftime("%Y-%m")
goals = {"プランク": 100, "腹筋": 1000, "レッグレイズ": 1000}
user = st.sidebar.radio("ユーザーを選択", ["士温", "咲希"])

# タブ作成
tab1, tab2, tab3, tab4 = st.tabs(["📊 協力メーター", "📅 カレンダー", "📝 記録する", "📜 分析・履歴"])

# --- タブ1: 今月の協力メーター ---
with tab1:
    st.header(f"{current_month} の進捗")
    
    if not df.empty:
        month_df = df[df['年月'] == current_month]
        
        for menu, goal in goals.items():
            current_sum = month_df[month_df['種目'] == menu]['数値'].sum()
            progress = min(float(current_sum) / goal, 1.0)
            
            col1, col2 = st.columns([3, 1])
            with col1:
                st.subheader(menu)
                st.progress(progress)
            with col2:
                st.write(f"\n**{int(current_sum)}** / {goal}")
    else:
        st.info("データがありません")

# --- タブ2: カレンダー ---
with tab2:
    st.header("トレーニングカレンダー")
    
    calendar_events = []
    if not df.empty and '日付_str' in df.columns:
        # 日付と名前で活動をまとめる
        summary = df.groupby(['日付_str', '名前']).size().reset_index()
        
        for _, row in summary.iterrows():
            emoji = "🔵" if row['名前'] == "士温" else "🌸"
            color = "#1E90FF" if row['名前'] == "士温" else "#FF69B4"
            
            calendar_events.append({
                "title": f"{emoji}", 
                "start": row['日付_str'],
                "end": row['日付_str'],
                "allDay": True,
                "backgroundColor": color,
                "borderColor": color,
                "display": "block" # これで四角いブロック表示になります
            })

    # カレンダー設定（シンプル化）
    calendar_options = {
        "headerToolbar": {
            "left": "prev,next today",
            "center": "title",
            "right": "dayGridMonth"
        },
        "initialView": "dayGridMonth",
        "locale": "ja",
        "height": 500, # 高さを指定して表示崩れを防ぐ
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
            st.success("✅ 保存しました！")
            st.rerun()
        except Exception as e:
            st.error(f"保存失敗: {e}")

# --- タブ4: 分析・履歴（新機能！） ---
with tab4:
    st.header("🏆 累計データ & 過去ログ")

    if not df.empty:
        # 1. 個人の種目ごとの合計記録
        st.subheader("👤 個人の累計記録")
        # ピボットテーブルを作成（行：種目、列：名前、値：合計）
        pivot_df = df.pivot_table(index='種目', columns='名前', values='数値', aggfunc='sum').fillna(0).astype(int)
        st.table(pivot_df)

        st.divider() # 区切り線

        # 2. 月ごとの協力メーター（過去ログ）
        st.subheader("📅 過去の協力メーター確認")
        
        # 存在する月のリストを作成
        available_months = sorted(df['年月'].unique(), reverse=True)
        selected_month = st.selectbox("確認したい月を選択", available_months)
        
        if selected_month:
            st.write(f"**{selected_month} の達成状況**")
            past_month_df = df[df['年月'] == selected_month]
            
            for menu, goal in goals.items():
                past_sum = past_month_df[past_month_df['種目'] == menu]['数値'].sum()
                past_progress = min(float(past_sum) / goal, 1.0)
                st.caption(f"{menu}: {int(past_sum)} / {goal}")
                st.progress(past_progress)
        
        st.divider()
        
        # 3. 全データ履歴
        with st.expander("全データ履歴を表示"):
            st.dataframe(df[['日付_str', '名前', '種目', '数値', '単位']].sort_values('日付_str', ascending=False))
    else:
        st.write("まだデータがありません。")
