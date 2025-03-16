import streamlit as st
import google_auth_oauthlib.flow
import google.oauth2.credentials
import googleapiclient.discovery
import os
import secrets

# Streamlit の secrets から OAuth クライアント情報を取得
CLIENT_ID = st.secrets["google"]["client_id"]
CLIENT_SECRET = st.secrets["google"]["client_secret"]
REDIRECT_URI = st.secrets["google"]["redirect_uri"]
SCOPES = ["https://www.googleapis.com/auth/tasks"]


def get_authorization_url():
    """認証 URL を生成"""
    # セッションごとに一意のステートパラメータを生成
    if "oauth_state" not in st.session_state:
        st.session_state.oauth_state = secrets.token_urlsafe(16)
    
    flow = google_auth_oauthlib.flow.Flow.from_client_config(
        {
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "redirect_uris": [REDIRECT_URI],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
    )
    flow.redirect_uri = REDIRECT_URI
    
    # state パラメータを使用して CSRF 対策
    auth_url, _ = flow.authorization_url(
        prompt="consent",
        state=st.session_state.oauth_state,
        access_type="offline",  # リフレッシュトークンを取得するために必要
        include_granted_scopes="true"  # 以前に許可されたスコープも含める
    )
    return auth_url


def get_credentials(auth_code, state=None):
    """認証コードからトークンを取得"""
    # ステートパラメータの検証
    if state and "oauth_state" in st.session_state and state != st.session_state.oauth_state:
        raise ValueError("認証ステートが一致しません。セキュリティ上の理由により認証を中止します。")
    
    flow = google_auth_oauthlib.flow.Flow.from_client_config(
        {
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "redirect_uris": [REDIRECT_URI],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
        state=st.session_state.get("oauth_state")
    )
    flow.redirect_uri = REDIRECT_URI
    
    try:
        flow.fetch_token(code=auth_code)
        return flow.credentials
    except Exception as e:
        st.error(f"トークンの取得に失敗しました: {e}")
        raise

