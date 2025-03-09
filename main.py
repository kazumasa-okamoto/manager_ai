import streamlit as st
from openai import OpenAI
from datetime import datetime
import os
import google.oauth2.credentials
import googleapiclient.discovery

from src.task_processing import extract_tasks, save_tasks, get_tasks, delete_task, update_task_status
from src.emotion_processing import classify_emotion
from src.authorization import get_authorization_url, get_credentials

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
if "credentials" not in st.session_state:
    st.session_state.credentials = None # 認証情報

# 感情に対応する画像のパス
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
emotion_images = {
    "喜": os.path.join(BASE_DIR, "assets", "images", "kairakun_joy.png"),
    "怒": os.path.join(BASE_DIR, "assets", "images", "kairakun_angry.png"),
    "哀": os.path.join(BASE_DIR, "assets", "images", "kairakun_sad.png"),
    "楽": os.path.join(BASE_DIR, "assets", "images", "kairakun_happy.png"),
    "無": os.path.join(BASE_DIR, "assets", "images", "kairakun_default.png"),
    "祝": os.path.join(BASE_DIR, "assets", "images", "kairakun_done.png")
}

# 認証処理
creds = None
query_params = st.query_params
if "code" in query_params and "state" in query_params:
    try:
        auth_code = query_params["code"].strip()
        state = query_params["state"].strip()
        credentials = get_credentials(auth_code, state)
        st.session_state.credentials = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
        # クエリパラメータをクリア
        st.query_params.clear()
        st.rerun()
    except Exception as e:
        st.error(f"認証エラー: {e}")
        # 認証エラーの場合、認証情報をリセット
        st.session_state.credentials = None
        # クエリパラメータをクリア
        st.query_params.clear()

if st.session_state.credentials is None:
    auth_url = get_authorization_url()
    st.markdown(f"[Google Tasksと同期]({auth_url})")
else:
    try:
        creds = google.oauth2.credentials.Credentials(**st.session_state.credentials)
        service = googleapiclient.discovery.build("tasks", "v1", credentials=creds)
    except Exception as e:
        st.error(f"認証情報の復元に失敗しました: {e}")
        st.session_state.credentials = None
        st.rerun()

# タイトルの表示
st.title("タスク管理AI")

st.write("")
st.write("")

# 画像の表示
col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    st.image(emotion_images[st.session_state.emotion], width=200)

st.write("")
st.write("")

# チャット履歴の表示
chat_container = st.container(height=500)
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
              save_tasks(tasks, creds)

          # UIを更新
          st.rerun()

st.sidebar.write("## タスク一覧")
tasks = get_tasks(creds)
if not tasks:
    st.sidebar.write("現在、タスクはありません。")
else:
    for task_item in tasks:
        col1, col2, col3 = st.sidebar.columns([6, 2, 2])

        task_id = task_item["id"]
        task_text = task_item["title"]
        status = task_item["status"]

        state_key = f"task_status_{task_id}"

        if col2.button("完了", key=f"done_sidebar_{task_id}"):
            st.session_state[f"task_status_{task_id}"] = "completed"
            update_task_status(task_id, "completed", creds)
            st.session_state.emotion = "祝"
            st.rerun()

        current_status = status if state_key not in st.session_state else st.session_state[state_key]
        col1.write(f"✅ {task_text}" if current_status == "completed" else f"⬜ {task_text}")

        if col3.button("削除", key=f"delete_sidebar_{task_id}"):
            delete_task(task_id, creds)
            st.rerun()
