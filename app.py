import streamlit as st
import pandas as pd
import datetime
from streamlit_gsheets import GSheetsConnection
from streamlit_calendar import calendar

st.set_page_config(page_title="筋トレ記録", layout="centered")
st.title("筋トレ記録 & 協力メーター")

# --- スプレッドシート接続 ---
# URLを直接書くのではなく、Secretsの設定を読み込むようにします
conn = st.connection("gsheets", type=GSheetsConnection)

# データの読み込み（ここもurlを直接指定せず、connにお任せします）
df = conn.read(ttl=0)
# データの型変換と日付の処理
if not df.empty:
    df['数値'] = pd.to_numeric(df['数値'], errors='coerce').fillna(0)
    df['日付'] = pd.to_datetime(df['日付']).dt.date

# --- 今月の設定 ---
today = datetime.date.today()
current_month = today.strftime("%Y-%m")

# サイドバー
user = st.sidebar.radio("ユーザーを選択", ["士温", "咲希"])
st.sidebar.write(f"現在の月: {current_month}")

tab1, tab2, tab3, tab4 = st.tabs(["協力メーター", "カレンダー", "記録する", "過去の履歴"])

with tab1:
    st.header(f"{current_month} の協力メーター")
    goals = {"プランク": 100, "腹筋": 1000, "レッグレイズ": 1000}
    
    # 今月のデータのみ抽出
    month_df = df[pd.to_datetime(df['日付']).dt.strftime("%Y-%m") == current_month]
    
    if month_df.empty:
        st.info("今月はまだ記録がありません。")
    else:
        for menu, goal in goals.items():
            current_sum = month_df[month_df['種目'] == menu]['数値'].sum()
            progress = min(float(current_sum) / goal, 1.0)
            st.subheader(menu)
            st.progress(progress)
            st.write(f"現在の合計: {int(current_sum)} / 目標: {goal}")

with tab2:
    st.header("トレーニングカレンダー")
    # カレンダー用のイベントデータ作成
    calendar_events = []
    if not df.empty:
        # 日付×名前でグループ化して、その日に誰がやったか特定
        daily_summary = df.groupby(['日付', '名前']).size().reset_index()
        for _, row in daily_summary.items():
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
        updated_df = pd.concat([df, new_row], ignore_index=True)
        conn.update(spreadsheet=url, data=updated_df)
        st.success("保存しました！")
        st.rerun()

with tab4:
    st.header("過去の履歴")
    if not df.empty:
        # 月ごとに集計
        df['年月'] = pd.to_datetime(df['日付']).dt.strftime("%Y年%m月")
        history_month = st.selectbox("表示する月を選択", df['年月'].unique()[::-1])
        
        display_df = df[df['年月'] == history_month].copy()
        st.dataframe(display_df[['日付', '名前', '種目', '数値', '単位']].sort_values('日付', ascending=False))
        
        # 月別の合計
        st.subheader(f"{history_month} の合計データ")
        summary = display_df.groupby(['種目', '名前'])['数値'].sum().unstack().fillna(0)
        st.table(summary)

