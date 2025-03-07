import streamlit as st
from openai import OpenAI
from datetime import datetime


OPENAI_API_KEY=st.secrets["openai"]["api_key"]

client = OpenAI(api_key=OPENAI_API_KEY)

# セッションステートの初期化
if 'tasks' not in st.session_state:
    st.session_state.tasks = []  # タスクのリスト
    
if 'task_id_counter' not in st.session_state:
    st.session_state.task_id_counter = 1  # タスクIDのカウンター

# タスクをOpenAI APIから抽出
def extract_tasks(user_input):
    prompt = f"""
    ユーザーが以下のように会話を進めています：
    "{user_input}"
    この内容がタスクに関係しているかを判断してください。
    - 関連があるなら、その内容を具体的なタスクとしてリストアップしてください。
    - 関連がなければ、「なし」と答えてください。

    出力は以下のフォーマットで：
    タスクリスト:
    - タスク1
    - タスク2
    （または「なし」）
    """

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": "あなたはユーザーの相談を受け、タスクがあるかを判断するAIです。"},
                  {"role": "user", "content": prompt}]
    )

    extracted_text = response.choices[0].message.content
    if "なし" in extracted_text:
        return []

    tasks = [task.strip("- ") for task in extracted_text.split("\n") if task.strip() and not task.startswith("タスクリスト")]
    return tasks

# タスクを保存する関数
def save_tasks(tasks):
    for task in tasks:
        # 新しいタスクを辞書形式で追加
        new_task = {
            'id': st.session_state.task_id_counter,
            'task': task,
            'status': 'pending',
            'created_at': datetime.now()
        }
        st.session_state.tasks.append(new_task)
        st.session_state.task_id_counter += 1

# タスクの一覧を取得する関数
def get_tasks():
    # 作成日時の降順でソート
    return sorted(st.session_state.tasks, key=lambda x: x['created_at'], reverse=True)

# タスクを削除する関数
def delete_task(task_id):
    st.session_state.tasks = [task for task in st.session_state.tasks if task['id'] != task_id]


# タスクの完了状態を更新する関数
def update_task_status(task_id, status):
    for task in st.session_state.tasks:
        if task['id'] == task_id:
            task['status'] = status
            break