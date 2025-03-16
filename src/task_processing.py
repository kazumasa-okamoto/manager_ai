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
def extract_tasks(chat_history=None, task_content=None):
    chat_log = "会話がありません。" if chat_history is None else chat_history.strip()
    task_list = "現在タスクはありません。" if task_content is None else task_content.strip()
    
    prompt = f"""
    【現在のタスク一覧】
    {task_list}

    【会話履歴】
    {chat_log}

    【指示】
    上記の会話履歴から、タスクとして管理すべき項目を抽出してください。

    以下の基準で判断してください：
    1. ユーザーが実行する必要がある具体的な行動であること
    2. 既存のタスク一覧に含まれていない新規のタスクであること
    3. 期限や具体的な行動が明確なものを優先すること

    【出力形式】
    必ず以下のフォーマットで出力してください：
    タスクリスト:
    - [具体的なタスク内容]
    - [具体的なタスク内容]

    ※抽出すべきタスクがない場合は「なし」と出力してください
    """

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": "あなたはユーザーの会話から適切にタスクを抽出する優秀なAIです。"},
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

def determine_priority_bulk(task_titles):
    prompt = """
    以下のタスクの優先度を High, Medium, Low の3段階で判定してください。

    【判定基準】
    - 期限が近いもの、高い影響を持つもの → High
    - 期限があるが緊急性が低いもの、または重要だが期限がないもの → Medium
    - 緊急性も低く、影響も小さいもの → Low

    【出力形式】
    - タスク1: 優先度
    - タスク2: 優先度
    ...

    【タスク一覧】
    """

    prompt += "\n".join([f"- {title}" for title in task_titles])

    response =client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": "あなたはタスクの優先度を適切に評価するAIです。"},
                  {"role": "user", "content": prompt}]
    )

    extracted_text = response.choices[0].message.content


    # 結果を辞書形式でパース
    priorities = {}
    for line in extracted_text.split("\n"):
        parts = line.split(": ")
        if len(parts) == 2:
            task_title, priority = parts
            priorities[task_title.strip("- ")] = priority.strip()

    return priorities


# タスクを保存する関数
def save_tasks(tasks, creds):
    priorities = determine_priority_bulk(tasks)

    for task in tasks:
        temp_id = str(st.session_state.task_id_counter)
        priority = priorities.get(task, "Medium")  # 確実に辞書から取得


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
            'priority': priority , 
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
        tasks = response.get('items', [])

        # タスク名のリストを取得（タイトルが存在する場合のみ）
        task_titles = [task["title"] for task in tasks if "title" in task]

        # 優先順位を判定
        priorities = determine_priority_bulk(task_titles) if task_titles else {}

        formatted_tasks = []  

        for task in tasks:
            formatted_tasks.append({
                'kind': task.get('kind', 'tasks#task'),
                'id': task['id'],
                'title': task['title'],
                'status': task.get('status', 'needsAction'),
                'updated': task.get('updated', datetime.now(timezone.utc).isoformat()),
                'priority': priorities.get(task["title"], "Medium"),
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

    