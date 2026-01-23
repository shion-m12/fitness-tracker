import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.title("接続テスト")

# スプレッドシートID
ss_id = "19T5OnYjgOsWX05mQ1fc5IOJ1qd98jCB_5mnd_mKNyDw"
url = f"https://docs.google.com/spreadsheets/d/{ss_id}/edit?usp=sharing"

conn = st.connection("gsheets", type=GSheetsConnection)

# 1. 読み込みテスト
st.subheader("1. 読み込みテスト")
try:
    df = conn.read(spreadsheet=url, ttl=0)
    st.write("✅ 読み込み成功！現在の行数:", len(df))
    st.dataframe(df.tail(3))
except Exception as e:
    st.error(f"❌ 読み込み失敗: {e}")

# 2. 書き込みテスト
st.subheader("2. 書き込みテスト")
if st.button("テストデータを1行追加"):
    try:
        test_data = pd.DataFrame([{"日付": "2024-01-01", "名前": "テスト", "種目": "テスト", "数値": 0, "単位": "回"}])
        updated_df = pd.concat([df, test_data], ignore_index=True)
        
        # ここで書き込みを実行
        conn.update(spreadsheet=url, data=updated_df)
        st.success("✅ 書き込み成功！スプレッドシートを確認してください。")
    except Exception as e:
        # ⚠️ ここで出るエラーメッセージを教えてください！
        st.error("❌ 書き込み失敗")
        st.exception(e)
