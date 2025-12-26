import streamlit as st
import yt_dlp
import os
from openai import OpenAI
from pydub import AudioSegment
import time

# ページ設定
st.set_page_config(page_title="YouTube冒頭文字起こしアプリ", layout="wide")
st.title("🎥 YouTube冒頭6秒 文字起こしツール")

# --- サイドバー設定 ---
st.sidebar.header("設定")

# 1. APIキーの設定
try:
    api_key = st.secrets["OPENAI_API_KEY"]
    st.sidebar.success("APIキー: 読み込み成功 ✅")
except (FileNotFoundError, KeyError):
    api_key = st.sidebar.text_input("OpenAI API Key", type="password")
    if not api_key:
        st.warning("APIキーが設定されていません。")
        st.stop()

# 2. Cookieファイルのアップロード (403エラー回避用)
st.sidebar.markdown("---")
st.sidebar.subheader("YouTube接続設定")
st.sidebar.info("403 Forbiddenエラーが出る場合は、ここに `cookies.txt` をアップロードしてください。")
cookies_file = st.sidebar.file_uploader("cookies.txt (Netscape形式)", type=["txt"])

# Cookieファイルを一時保存するパス
COOKIE_PATH = "cookies.txt"
if cookies_file is not None:
    with open(COOKIE_PATH, "wb") as f:
        f.write(cookies_file.getbuffer())
    st.sidebar.success("Cookiesを使用します ✅")
elif os.path.exists(COOKIE_PATH):
    # アップロードがない場合は古いファイルを削除（念のため）
    os.remove(COOKIE_PATH)

client = OpenAI(api_key=api_key)

# ユーティリティ関数: YouTubeから音声ダウンロード＆6秒カット
def download_and_cut_audio(url, output_filename="temp_audio"):
    try:
        # yt-dlpの設定
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_filename,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
            'noplaylist': True,
            # ブラウザのフリをする設定
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
            },
        }

        # Cookieファイルがある場合は設定に追加
        if cookies_file is not None:
            ydl_opts['cookiefile'] = COOKIE_PATH

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        target_file = output_filename + ".mp3"
        
        if not os.path.exists(target_file):
            return None, "ダウンロード失敗: ファイルが生成されませんでした"

        # Pydubでカット処理
        audio = AudioSegment.from_mp3(target_file)
        cut_audio = audio[:6000] # 冒頭6秒 (ミリ秒)
        cut_audio.export(target_file, format="mp3")
        
        return target_file, None

    except Exception as e:
        # エラーメッセージを短く整形
        error_msg = str(e)
        if "HTTP Error 403" in error_msg:
            return None, "HTTP Error 403: YouTubeにブロックされました。サイドバーからcookies.txtをアップロードしてください。"
        return None, error_msg

# ユーティリティ関数: Whisperで文字起こし
def transcribe_audio(file_path):
    try:
        with open(file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file,
                language="ja"
            )
        return transcript.text
    except Exception as e:
        return f"文字起こしエラー: {str(e)}"

# --- メインUI ---

urls_input = st.text_area("YouTubeのリンクを1行ずつ入力してください", height=150, placeholder="https://www.youtube.com/watch?v=...\nhttps://youtu.be/...")

col1, col2 = st.columns([1, 3])
with col1:
    start_btn = st.button("文字起こし開始", type="primary")

if start_btn:
    if not urls_input:
        st.error("リンクを入力してください。")
    else:
        # 入力データのクリーニング
        raw_lines = urls_input.strip().split('\n')
        urls = [u.strip() for u in raw_lines if u.strip().startswith(("http://", "https://"))]
        
        if not urls:
            st.warning("有効なURLが見つかりませんでした。")
        else:
            st.write(f"全 {len(urls)} 件の処理を開始します...")
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            results = []

            for i, url in enumerate(urls):
                status_text.text(f"処理中 ({i+1}/{len(urls)}): {url}")
                
                # 1. ダウンロード & カット
                audio_file, error = download_and_cut_audio(url, f"temp_{i}")
                
                if error:
                    st.error(f"❌ {url}\n{error}")
                    results.append({"url": url, "status": "Error", "text": error})
                else:
                    # 2. 文字起こし
                    text = transcribe_audio(audio_file)
                    st.success(f"✅ {url}\n{text}")
                    results.append({"url": url, "status": "Success", "text": text})
                    
                    # 掃除
                    if os.path.exists(audio_file):
                        os.remove(audio_file)
                
                # サーバー負荷軽減のため少し待機
                time.sleep(1)
                progress_bar.progress((i + 1) / len(urls))

            status_text.text("処理完了！")
            st.divider()
            
            # 結果表示（データフレームで見やすく）
            st.subheader("🎉 結果一覧")
            st.dataframe(results, use_container_width=True)
