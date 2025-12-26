import streamlit as st
import yt_dlp
import os
from openai import OpenAI
from pydub import AudioSegment

# ページ設定
st.set_page_config(page_title="YouTube冒頭文字起こしアプリ")
st.title("🎥 YouTube冒頭6秒 文字起こしツール")

# --- APIキーの設定（Secretsから読み込み） ---
try:
    api_key = st.secrets["OPENAI_API_KEY"]
except (FileNotFoundError, KeyError):
    st.error("APIキーが設定されていません。StreamlitのSettings > Secretsに 'OPENAI_API_KEY' を設定してください。")
    st.stop()

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
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        target_file = output_filename + ".mp3"
        
        if not os.path.exists(target_file):
            return None, "ダウンロードエラー"

        audio = AudioSegment.from_mp3(target_file)
        cut_audio = audio[:6000] # 冒頭6秒
        cut_audio.export(target_file, format="mp3")
        return target_file, None

    except Exception as e:
        return None, str(e)

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

urls_input = st.text_area("YouTubeのリンクを1行ずつ入力してください", height=150)

if st.button("文字起こし開始"):
    if not urls_input:
        st.error("リンクを入力してください。")
    else:
        urls = urls_input.strip().split('\n')
        st.write(f"全 {len(urls)} 件の動画を処理します...")
        
        progress_bar = st.progress(0)
        results = []

        for i, url in enumerate(urls):
            url = url.strip()
            if not url: continue
            
            with st.spinner(f"処理中 ({i+1}/{len(urls)}): {url}"):
                audio_file, error = download_and_cut_audio(url, f"temp_{i}")
                
                if error:
                    st.error(f"{url}: {error}")
                    results.append({"url": url, "text": "エラー"})
                else:
                    text = transcribe_audio(audio_file)
                    st.success(f"完了: {text}")
                    results.append({"url": url, "text": text})
                    
                    if os.path.exists(audio_file):
                        os.remove(audio_file)

            progress_bar.progress((i + 1) / len(urls))

        st.divider()
        st.subheader("🎉 結果一覧")
        st.table(results)
