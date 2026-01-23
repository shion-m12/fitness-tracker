import streamlit as st
import pandas as pd
import datetime
import gspread
from google.oauth2.service_account import Credentials
from streamlit_calendar import calendar

# --- ページ設定 ---
st.set_page_config(page_title="筋トレ記録", layout="centered")
st.title("💪 筋トレ記録 & 協力メーター")

# --- スプレッドシート接続設定（gspread使用） ---
# スプレッドシートのURL
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/19T5OnYjgOsWX05mQ1fc5IOJ1qd98jCB_5mnd_mKNyDw/edit"

# 認証スコープ（許可する操作の範囲）
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

@st.cache_resource
def connect_to_gsheets():
    try:
        # Secretsから認証情報を取得して辞書に変換
        secrets_dict = dict(st.secrets["connections"]["gsheets"])
        
        # 念のため private_key の改行コードを修正
        if "private_key" in secrets_dict:
            secrets_dict["private_key"] = secrets_dict["private_key"].replace("\\n", "\n")

        # 認証を実行
        creds = Credentials.from_service_account_info(secrets_dict, scopes=SCOPES)
        client = gspread.authorize(creds)
        
        # スプレッドシートを開く
        spreadsheet = client.open_by_url(SPREADSHEET_URL)
        return spreadsheet.sheet1  # 1枚目のシートを返す
        
    except Exception as e:
        st.error(f"⚠️ 接続エラーが発生しました。\nSecretsの設定を確認してください。\nエラー詳細: {e}")
        return None

# シート接続
worksheet = connect_to_gsheets()

if worksheet is None:
    st.stop()  # 接続できない場合はここで停止

# --- データの読み込み ---
# 全データを取得してDataFrameにする
try:
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
except Exception:
    # データが空の場合
    df = pd.DataFrame(columns=['日付', '名前', '種目', '数値', '単位'])

# データ型変換
if not df.empty:
    df['数値'] = pd.to_numeric(df['数値'], errors='coerce').fillna(0)
    # 日付列があれば変換
    if '日付' in df.columns:
        df['日付'] = pd.to_datetime(df['日付']).dt.date

# --- 今月の設定 ---
today = datetime.date.today()
current_month = today.strftime("%Y-%m")

# サイドバー
user = st.sidebar.radio("ユーザーを選択", ["士温", "咲希"])
st.sidebar.info(f"ログイン中: {user}")

# タブ作成
tab1, tab2, tab3, tab4 = st.tabs(["📊 協力メーター", "📅 カレンダー", "📝 記録する", "📜 履歴"])

# --- タブ1: 協力メーター ---
with tab1:
    st.header(f"{current_month} の協力メーター")
    goals = {"プランク": 100, "腹筋": 1000, "レッグレイズ": 1000}
    
    if not df.empty and '日付' in df.columns:
        df_calc = df.copy()
        df_calc['年月'] = pd.to_datetime(df_calc['日付']).dt.strftime("%Y-%m")
        month_df = df_calc[df_calc['年月'] == current_month]
        
        for menu, goal in goals.items():
            current_sum = month_df[month_df['種目'] == menu]['数値'].sum()
            progress = min(float(current_sum) / goal, 1.0)
            st.subheader(menu)
            st.progress(progress)
            st.write(f"現在の合計: {int(current_sum)} / 目標: {goal} ({'分' if menu == 'プランク' else '回'})")
    else:
        st.info("データがまだありません。")

# --- タブ2: カレンダー ---
with tab2:
    st.header("トレーニングカレンダー")
    calendar_events = []
    if not df.empty and '日付' in df.columns:
        summary = df.groupby(['日付', '名前']).size().reset_index()
        for _, row in summary.iterrows():
            emoji = "🔵" if row['名前'] == "士温" else "🌸"
            calendar_events.append({
                "title": f"{row['名前']} {emoji}",
                "start": str(row['日付']),
                "end": str(row['日付']),
                "allDay": True,
                "color": "#1E90FF" if row['名前'] == "士温" else "#FF69B4"
            })

    calendar(events=calendar_events, options={"locale": "ja", "headerToolbar": {"left": "prev,next", "center": "title", "right": ""}})

# --- タブ3: 記録する ---
with tab3:
    st.header(f"{user} の記録入力")
    date_input = st.date_input("日付を選択", today)
    menu_choice = st.selectbox("メニュー", ["プランク", "腹筋", "レッグレイズ"])
    unit = "分" if menu_choice == "プランク" else "回"
    value = st.number_input(f"内容 ({unit})", min_value=0, step=1)
    
    if st.button("記録を保存"):
        # 保存用のデータリストを作成
        new_row_list = [
            date_input.strftime("%Y-%m-%d"),
            user,
            menu_choice,
            value,
            unit
        ]
        
        try:
            # gspreadを使って行を追加（一番確実な方法）
            worksheet.append_row(new_row_list)
            st.success("✅ 保存しました！")
            st.balloons()
            # データの再読み込みのためにリロード
            st.rerun()
        except Exception as e:
            st.error(f"❌ 保存に失敗しました: {e}")

# --- タブ4: 過去の履歴 ---
with tab4:
    st.header("履歴閲覧")
    if not df.empty and '日付' in df.columns:
        df_h = df.copy()
        df_h['年月'] = pd.to_datetime(df_h['日付']).dt.strftime("%Y年%m月")
        months = sorted(df_h['年月'].unique(), reverse=True)
        if months:
            selected_month = st.selectbox("表示月を選択", months)
            filtered_df = df_h[df_h['年月'] == selected_month]
            st.dataframe(filtered_df[['日付', '名前', '種目', '数値', '単位']].sort_values('日付', ascending=False))
