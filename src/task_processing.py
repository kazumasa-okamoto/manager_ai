import streamlit as st
from openai import OpenAI
from datetime import datetime, timezone
from googleapiclient.discovery import build

OPENAI_API_KEY=st.secrets["openai"]["api_key"]

client = OpenAI(api_key=OPENAI_API_KEY)

# セッションステートの初期化
if 'tasks' not in st.session_state:
    st.session_state.tasks = []  # タスクのリスト
    
if 'task_id_counter' not in st.session_state:
    st.session_state.task_id_counter = 1  # タスクIDのカウンター

# ユーザーの入力からタスクを抽出する関数
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

# Google Tasks APIにタスクを追加する関数
def add_task_to_google_tasks(title, creds):
    if creds is None:
        return []
    service = build('tasks', 'v1', credentials=creds)
    
    # タスクの情報
    task_body = {
        "title": title,
        "status": "needsAction",
    }
    # タスクリストID（デフォルトを使用）
    tasklist_id = "@default"
    # Google Tasks API にタスクを追加
    task = service.tasks().insert(tasklist=tasklist_id, body=task_body).execute()
    return task  # APIから返されたタスク情報を返す

# タスクを保存する関数
def save_tasks(tasks, creds):
    for task in tasks:
        temp_id = str(st.session_state.task_id_counter)
        
        if creds is None:
            # 認証情報がない場合は、ローカルのセッションステートにのみ保存
            task_id = temp_id
        else:
            try:
                # Google Tasks API にタスクを追加
                google_task = add_task_to_google_tasks(task, creds)
                task_id = google_task["id"]  # Google Tasks APIが発行した正式なID
            except Exception as e:
                st.error(f"Google Tasksへの追加に失敗しました: {e}")
                task_id = temp_id  # エラー時は仮のIDを使用
        
        # 新しいタスクを辞書形式で追加
        new_task = {
            'kind': 'tasks#task',
            'id': task_id,  # Google Tasks APIのID、または仮のID
            'title': task,  # タスク名
            'status': 'needsAction',  # 未完了の状態
            'updated': datetime.now(timezone.utc).isoformat(),  # UTC形式のタイムスタンプ
            'priority': 'Medium', 
        }
        st.session_state.tasks.append(new_task)
        st.session_state.task_id_counter += 1  # 次のタスクのカウンターを更新

# Google Tasks APIからタスクを取得する関数
def fetch_google_tasks(creds):
    if creds is None:
        return []
    
    service = build('tasks', 'v1', credentials=creds)
    # タスクリストID（デフォルトを使用）
    tasklist_id = "@default"

    try:
        response = service.tasks().list(tasklist=tasklist_id).execute()
        formatted_tasks = []  # 結果を入れるリスト

        for task in response.get('items', []):
            formatted_tasks.append({
                'kind': task.get('kind', 'tasks#task'),
                'id': task['id'],
                'title': task['title'],
                'status': task.get('status', 'needsAction'),
                'updated': task.get('updated', datetime.now(timezone.utc).isoformat()),
                'priority': task.get('priority', "Meduim" ) # 優先度を追加
            })
        
        return formatted_tasks

    except Exception as e:
        st.error(f"Google Tasksの取得に失敗しました: {e}")
        return []

# タスクの一覧を取得する関数
def get_tasks(creds):
    if creds is None:
        # 認証情報がない場合はセッションステートから取得し、作成日時の降順でソート
        return sorted(st.session_state.tasks, key=lambda x: x['updated'], reverse=True)
    
    # Google Tasks APIからタスクを取得
    google_tasks = fetch_google_tasks(creds)
    # 既存のタスクIDを取得
    existing_task_ids = {task['id'] for task in st.session_state.tasks}
    # 重複しないタスクのみを追加
    for task in google_tasks:
        if task['id'] not in existing_task_ids:
            st.session_state.tasks.append(task)
    
    # 作成日時の降順でソート
    return sorted(st.session_state.tasks, key=lambda x: x['updated'], reverse=True)

# タスクを削除する関数
def delete_task(task_id, creds):
    if creds is None:
        # 認証情報がない場合はセッションステートから削除
        st.session_state.tasks = [task for task in st.session_state.tasks if task['id'] != task_id]
        return
    service = build('tasks', 'v1', credentials=creds)
    # タスクリスト ID（デフォルトのタスクリストを使用）
    tasklist_id = "@default"

    try:
        # Google Tasks API からタスクを削除
        service.tasks().delete(tasklist=tasklist_id, task=task_id).execute()

    except Exception as e:
        st.error(f"Google Tasks の削除に失敗しました: {e}")

    # session_stateから削除
    st.session_state.tasks = [task for task in st.session_state.tasks if task['id'] != task_id]

# タスクの完了状態を更新する関数
def update_task_status(task_id, status, creds):
    if creds is not None:
        try:
            service = build('tasks', 'v1', credentials=creds)
            tasklist_id = "@default"

            # 現在のタスク情報を取得
            task = service.tasks().get(tasklist=tasklist_id, task=task_id).execute()
            
            # タスクのステータスを更新
            if status == "completed":
                # 完了状態に設定
                task['status'] = "completed"
                task['completed'] = datetime.now(timezone.utc).isoformat()
            else:
                # 未完了状態に設定
                task['status'] = status
                if 'completed' in task:
                    del task['completed']  # 完了日時を削除
            
            # Google Tasks APIでタスクを更新
            service.tasks().update(tasklist=tasklist_id, task=task_id, body=task).execute()
            # セッションステートの更新
            for task in st.session_state.tasks:
                if task['id'] == task_id:
                    task['status'] = status
                    break
                    
        except Exception as e:
            st.error(f"Google Tasksの更新に失敗しました: {e}")
        
    else:
        # 認証情報がない場合は、ローカルのみ更新
        for task in st.session_state.tasks:
            if task['id'] == task_id:
                task['status'] = status
                break


# タスクの優先度を変更する関数
def update_priority(task_id, priority):
    for task in st.session_state.tasks:
        if task['id'] == task_id:
            task['priority'] = priority
            break

    