# タスク管理AI
[KaiRA生成AIハッカソン2025](https://kaira-thesis-reading.connpass.com/event/347239/)で制作したタスク管理チャットボットです。

Google Tasks APIを用いて生成したタスクを同期することができます。

## 仮想環境での実行
1. **リポジトリをクローン**
```
git clone https://github.com/kazumasa-okamoto/manager_ai
cd manager_ai
```
2. **環境変数の設定**

`.streamlit/secret.toml`ファイルを作成し、以下の内容を設定してください。
```
[openai]
api_key = "YOUR_OPENAI_API_KEY"
[google]
client_id = "YOUR_GOOGLE_CLIENT_ID"
client_secret = "YOUR_GOOGLE_CLIENT_SECRET"
redirect_uri = "YOUR_GOOGLE_REDIRECT_URI"
```
3. **依存関係のインストール**
```
conda create -n manager_ai python
conda activate manager_ai
pip install -r requirements.txt
```
4. **アプリの実行**
```
streamlit run main.py
```