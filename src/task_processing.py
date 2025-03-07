import streamlit as st
import sqlite3
from openai import OpenAI

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

# タスクをデータベースに保存
def save_tasks(tasks):
    for task in tasks:
        c.execute("INSERT INTO tasks (task, status) VALUES (?, 'pending')", (task,))
    conn.commit()

# タスクの一覧を取得
def get_tasks():
    c.execute("SELECT id, task, status FROM tasks ORDER BY created_at DESC")
    return c.fetchall()

# タスクを削除
def delete_task(task_id):
    c.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()

# タスクの完了状態を更新
def update_task_status(task_id, status):
    c.execute("UPDATE tasks SET status=? WHERE id=?", (status, task_id))
    conn.commit()