import streamlit as st
import pandas as pd
import datetime
from streamlit_gsheets import GSheetsConnection
from streamlit_calendar import calendar

# --- ページ設定 ---
st.set_page_config(page_title="筋トレ記録", layout="centered")
st.title("筋トレ記録 & 協力メーター")

# --- スプレッドシート接続設定 ---
# このURLとSecretsの鍵を組み合わせて接続します
spreadsheet_url = "https://docs.google.com/spreadsheets/d/19T5OnYjgOsWX05mQ1fc5IOJ1qd98jCB_5mnd_mKNyDw/edit?usp=sharing"

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=spreadsheet_url, ttl=0)
except Exception as e:
    st.error("データの読み込みに失敗しました。Secretsの設定を確認してください。")
    st.stop()

# データの型変換と日付の処理
if not df.empty:
    df['数値'] = pd.to_numeric(df['数値'], errors='coerce').fillna(0)
    df['日付'] = pd.to_datetime(df['日付']).dt.date
else:
    # 空のデータフレームの場合の初期化
    df = pd.DataFrame(columns=['日付', '名前', '種目', '数値', '単位'])

# --- 今月の設定 ---
today = datetime.date.today()
current_month = today.strftime("%Y-%m")

# サイドバー
user = st.sidebar.radio("ユーザーを選択", ["士温", "咲希"])
st.sidebar.info(f"ログイン中: {user}")

# タブの作成
tab1, tab2, tab3, tab4 = st.tabs(["協力メーター", "カレンダー", "記録する", "過去の履歴"])

# --- タブ1: 協力メーター (今月分のみ) ---
with tab1:
    st.header(f"{current_month} の協力メーター")
    goals = {"プランク": 100, "腹筋": 1000, "レッグレイズ": 1000}
    
    # 今月のデータのみ抽出
    df_for_calc = df.copy()
    df_for_calc['年月'] = pd.to_datetime(df_for_calc['日付']).dt.strftime("%Y-%m")
    month_df = df_for_calc[df_for_calc['年月'] == current_month]
    
    for menu, goal in goals.items():
        current_sum = month_df[month_df['種目'] == menu]['数値'].sum()
        progress = min(float(current_sum) / goal, 1.0)
        st.subheader(menu)
        st.progress(progress)
        st.write(f"現在の合計: {int(current_sum)} / 目標: {goal} ({'分' if menu == 'プランク' else '回'})")

# --- タブ2: カレンダー (二人で一つ) ---
with tab2:
    st.header("トレーニングカレンダー")
    calendar_events = []
    if not df.empty:
        # 日付と名前でグループ化（同じ日に複数回やってもスタンプは1人1つ）
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

    calendar_options = {
        "headerToolbar": {"left": "prev,next", "center": "title", "right": ""},
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
        new_row = pd.DataFrame([{
            '日付': date_input,
            '名前': user,
            '種目': menu_choice,
            '数値': value,
            '単位': unit
        }])
        
        # 保存処理
        updated_df = pd.concat([df, new_row], ignore_index=True)
        try:
            conn.update(spreadsheet=spreadsheet_url, data=updated_df)
            st.success("スプレッドシートに保存しました！")
            st.balloons()
            st.rerun()
        except Exception as e:
            st.error(f"保存に失敗しました。権限設定を確認してください。")

# --- タブ4: 過去の履歴 ---
with tab4:
    st.header("履歴閲覧")
    if not df.empty:
        df_history = df.copy()
        df_history['年月'] = pd.to_datetime(df_history['日付']).dt.strftime("%Y年%m月")
        months = sorted(df_history['年月'].unique(), reverse=True)
        selected_month = st.selectbox("表示月を選択", months)
        
        filtered_df = df_history[df_history['年月'] == selected_month]
        st.dataframe(filtered_df[['日付', '名前', '種目', '数値', '単位']].sort_values('日付', ascending=False))
        
        st.subheader("月間集計")
        pivot = filtered_df.pivot_table(index='種目', columns='名前', values='数値', aggfunc='sum').fillna(0)
        st.table(pivot)
    else:
        st.write("履歴はまだありません。")
