import streamlit as st
from openai import OpenAI
from datetime import datetime

from src.task_processing import extract_tasks, save_tasks, get_tasks, delete_task, update_task_status
from src.emotion_processing import classify_emotion

OPENAI_API_KEY=st.secrets["openai"]["api_key"]

client = OpenAI(api_key=OPENAI_API_KEY)

# セッションステートの初期化
if "messages" not in st.session_state:
    st.session_state.messages = []  # チャット履歴
if 'tasks' not in st.session_state:
    st.session_state.tasks = []  # タスクのリスト
if 'task_id_counter' not in st.session_state:
    st.session_state.task_id_counter = 1  # タスクIDのカウンター
if "emotion" not in st.session_state:
    st.session_state.emotion = "無"  # 感情の初期値

# 感情に対応する画像のパス
emotion_images = {
    "喜": "assets\images\kairakun_joy.png",
    "怒": "assets\images\kairakun_angry.png",
    "哀": "assets\images\kairakun_sad.png",
    "楽": "assets\images\kairakun_happy.png",
    "無": "assets\images\kairakun_default.png",
    "祝": "assets\images\kairakun_done.png"
}

# タイトルの表示
st.title("タスク管理AI")
# 画像の表示
st.image(emotion_images[st.session_state.emotion])
# チャット履歴の表示
chat_container = st.container()
with chat_container:
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

          # 感情の分類
          emotion = classify_emotion(bot_reply)
          st.session_state.emotion = emotion

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
    for task_item in tasks:
        col1, col2, col3 = st.sidebar.columns([6, 2, 2])

        task_id = task_item["id"]
        task_text = task_item["task"]
        status = task_item["status"]

        state_key = f"task_status_{task_id}"

        if col2.button("完了", key=f"done_sidebar_{task_id}"):
            st.session_state[f"task_status_{task_id}"] = "done"
            update_task_status(task_id, "done")
            st.session_state.emotion = "祝"
            st.rerun()

        current_status = status if state_key not in st.session_state else st.session_state[state_key]
        col1.write(f"✅ {task_text}" if current_status == "done" else f"⬜ {task_text}")

        if col3.button("削除", key=f"delete_sidebar_{task_id}"):
            delete_task(task_id)
            st.rerun()