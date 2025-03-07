import streamlit as st
import sqlite3
from openai import OpenAI

from src.task_processing import extract_tasks, save_tasks, get_tasks, delete_task, update_task_status

OPENAI_API_KEY=st.secrets["openai"]["api_key"]

client = OpenAI(api_key=OPENAI_API_KEY)

# SQLite データベースの初期化
conn = sqlite3.connect("tasks.db", check_same_thread=False)
c = conn.cursor()
c.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task TEXT,
        status TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
conn.commit()

# チャット履歴をセッションに保存
if "messages" not in st.session_state:
    st.session_state.messages = []

# チャット履歴の表示
st.write("## 会話履歴")
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

with st.form("相談内容",clear_on_submit=True):
    user_input = st.text_input("相談内容を入力してください")
    submitted = st.form_submit_button("送信")
    if submitted:
      if user_input:
          # ユーザーメッセージを保存
          st.session_state.messages.append({"role": "user", "content": user_input})

          # OpenAI に会話の続きを依頼
          response = client.chat.completions.create(
              model="gpt-4o",
              messages=[{"role": "system", "content": "あなたは親身に相談に乗るAIアシスタントです。"},
                        *st.session_state.messages]
          )
          bot_reply = response.choices[0].message.content
          st.session_state.messages.append({"role": "assistant", "content": bot_reply})

          # タスクの抽出
          tasks = extract_tasks(user_input)
          if tasks:
              st.session_state.messages.append({"role": "assistant", "content": "以下のタスクを作成しました:"})
              for task in tasks:
                  st.session_state.messages.append({"role": "assistant", "content": f"- {task}"})
              save_tasks(tasks)

          # UIを更新
          st.rerun()

st.sidebar.write("## タスク一覧")
tasks = get_tasks()
if not tasks:
    st.sidebar.write("現在、タスクはありません。")
else:
    for task_id, task, status in tasks:
        col1, col2, col3 = st.sidebar.columns([6, 2, 2])

        state_key = f"task_status_{task_id}"

        if col2.button("完了", key=f"done_sidebar_{task_id}"):
            st.session_state[f"task_status_{task_id}"] = "done"
            update_task_status(task_id, "done")
            st.rerun()

        current_status = status if state_key not in st.session_state else st.session_state[state_key]
        col1.write(f"✅ {task}" if current_status == "done" else f"⬜ {task}")

        if col3.button("削除", key=f"delete_sidebar_{task_id}"):
            delete_task(task_id)
            st.rerun()