import streamlit as st
import pandas as pd
import datetime
from streamlit_gsheets import GSheetsConnection
from streamlit_calendar import calendar

# --- ページ設定 ---
st.set_page_config(page_title="筋トレ記録", layout="centered")
st.title("筋トレ記録 & 協力メーター")

# --- スプレッドシート設定 ---
# URLからIDだけを抜き出したものをここに入れます
spreadsheet_id = "19T5OnYjgOsWX05mQ1fc5IOJ1qd98jCB_5mnd_mKNyDw"
spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit?usp=sharing"

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    # 明らかにこのIDを使うように指示します
    df = conn.read(spreadsheet=spreadsheet_url, ttl=0)
except Exception as e:
    st.error(f"読み込みエラー: {e}")
    st.stop()

# --- (中略: データ処理ロジック) ---
if not df.empty:
    df['数値'] = pd.to_numeric(df['数値'], errors='coerce').fillna(0)
    df['日付'] = pd.to_datetime(df['日付']).dt.date
else:
    df = pd.DataFrame(columns=['日付', '名前', '種目', '数値', '単位'])

today = datetime.date.today()
current_month = today.strftime("%Y-%m")
user = st.sidebar.radio("ユーザーを選択", ["士温", "咲希"])

tab1, tab2, tab3, tab4 = st.tabs(["協力メーター", "カレンダー", "記録する", "過去の履歴"])

# --- タブ1: 協力メーター ---
with tab1:
    st.header(f"{current_month} の協力メーター")
    goals = {"プランク": 100, "腹筋": 1000, "レッグレイズ": 1000}
    df_calc = df.copy()
    df_calc['年月'] = pd.to_datetime(df_calc['日付']).dt.strftime("%Y-%m")
    month_df = df_calc[df_calc['年月'] == current_month]
    for menu, goal in goals.items():
        current_sum = month_df[month_df['種目'] == menu]['数値'].sum()
        progress = min(float(current_sum) / goal, 1.0)
        st.subheader(menu)
        st.progress(progress)
        st.write(f"現在の合計: {int(current_sum)} / 目標: {goal}")

# --- タブ2: カレンダー ---
with tab2:
    calendar_events = []
    if not df.empty:
        summary = df.groupby(['日付', '名前']).size().reset_index()
        for _, row in summary.iterrows():
            emoji = "🔵" if row['名前'] == "士温" else "🌸"
            calendar_events.append({"title": f"{row['名前']} {emoji}", "start": str(row['日付']), "end": str(row['日付']), "allDay": True, "color": "#1E90FF" if row['名前'] == "士温" else "#FF69B4"})
    calendar(events=calendar_events, options={"locale": "ja"})

# --- タブ3: 記録する ---
with tab3:
    st.header(f"{user} の記録入力")
    date_input = st.date_input("日付を選択", today)
    menu_choice = st.selectbox("メニュー", ["プランク", "腹筋", "レッグレイズ"])
    unit = "分" if menu_choice == "プランク" else "回"
    value = st.number_input(f"内容 ({unit})", min_value=0, step=1)
    
    if st.button("記録を保存"):
        new_row = pd.DataFrame([{'日付': date_input, '名前': user, '種目': menu_choice, '数値': value, '単位': unit}])
        updated_df = pd.concat([df, new_row], ignore_index=True)
        try:
            # 保存時にもID(URL)を明示
            conn.update(spreadsheet=spreadsheet_url, data=updated_df)
            st.success("保存しました！")
            st.rerun()
        except Exception as e:
            st.error(f"保存失敗: サービスアカウントがスプレッドシートに『編集者』として招待されているか確認してください。")

# --- タブ4: 過去の履歴 ---
with tab4:
    if not df.empty:
        df_h = df.copy()
        df_h['年月'] = pd.to_datetime(df_h['日付']).dt.strftime("%Y年%m月")
        selected_month = st.selectbox("表示月を選択", sorted(df_h['年月'].unique(), reverse=True))
        st.dataframe(df_h[df_h['年月'] == selected_month].sort_values('日付', ascending=False))

