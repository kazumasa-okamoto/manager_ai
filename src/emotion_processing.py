import streamlit as st
from openai import OpenAI
from datetime import datetime

OPENAI_API_KEY=st.secrets["openai"]["api_key"]

client = OpenAI(api_key=OPENAI_API_KEY)

def classify_emotion(bot_reply):
    prompt = f"""
    以下の文章の感情を「喜」「怒」「哀」「楽」「驚」「困」「疑」「焦」のいずれかに分類してください。
    
    文章: {bot_reply}
    
    出力は必ず「喜」「怒」「哀」「楽」「驚」「困」「疑」「焦」のいずれか一文字のみを返してください。
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": "あなたはテキストの感情を分類する優秀なAIです。"},
                  {"role": "user", "content": prompt}]
    )
    
    emotion = response.choices[0].message.content.strip()
    return emotion

