import os
import requests
import tweepy
import yt_dlp
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- HELPERS (CLOUDFLARE & DRIVE) ---

def is_already_posted(video_id):
    """Checks if video was already posted to avoid spam"""
    acc, kv, token = os.getenv("CF_ACCOUNT_ID"), os.getenv("CF_KV_NAMESPACE_ID"), os.getenv("CF_API_TOKEN")
    url = f"https://api.cloudflare.com/client/v4/accounts/{acc}/storage/kv/namespaces/{kv}/values/{video_id}"
    headers = {"Authorization": f"Bearer {token}"}
    try: 
        res = requests.get(url, headers=headers)
        return res.status_code == 200
    except: return False

def update_kv(video_id):
    """Marks video as posted in Cloudflare KV"""
    acc, kv, token = os.getenv("CF_ACCOUNT_ID"), os.getenv("CF_KV_NAMESPACE_ID"), os.getenv("CF_API_TOKEN")
    url = f"https://api.cloudflare.com/client/v4/accounts/{acc}/storage/kv/namespaces/{kv}/values/{video_id}"
    headers = {"Authorization": f"Bearer {token}"}
    requests.put(url, headers=headers, data="posted")

def backup_to_drive(file_path, file_name):
    """Uploads video to shared folder to bypass quota limits"""
    folder_id = os.getenv("GDRIVE_FOLDER_ID")
    print(f"DEBUG: Using Folder ID: {folder_id}")
    
    if not folder_id or folder_id == "None":
        print("❌ Error: GDRIVE_FOLDER_ID is missing from Env Variables!")
        return

    try:
        creds_info = json.loads(os.getenv("GDRIVE_JSON"))
        creds = service_account.Credentials.from_service_account_info(creds_info)
        service = build('drive', 'v3', credentials=creds)
        
        # 'parents' is key for using shared storage
        file_metadata = {'name': file_name, 'parents': [folder_id]}
        media = MediaFileUpload(file_path, mimetype='video/mp4', resumable=True)
        service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        print("✅ Google Drive Backup Done!")
    except Exception as e: 
        print(f"❌ Drive Error: {e}")

# --- BOT LOGIC ---

def run_bot():
    print("🔎 Starting Bot Operations...")
    try:
        # Get RedGIFs Token
        auth_url = "https://api.redgifs.com/v2/auth/temporary"
        token = requests.get(auth_url).json().get('token')
        
        # Search Trending
        search_url = "https://api.redgifs.com/v2/gifs/search?search_text=trending&order=trending&count=5"
        res = requests.get(search_url, headers={"Authorization": f"Bearer {token}"})
        gifs = res.json().get('gifs', [])
        
        for gif in gifs:
            v_id = gif.get('id')
            if not is_already_posted(v_id):
                print(f"🎯 New Video Found: {v_id}")
                video_url = f"https://www.redgifs.com/watch/{v_id}"
                
                # Download
                with yt_dlp.YoutubeDL({'outtmpl': 'temp.mp4', 'quiet': True}) as ydl:
                    ydl.download([video_url])
                
                # Backup to Drive
                backup_to_drive('temp.mp4', f"{v_id}.mp4")
                
                # Post to Twitter
                print("🐦 Uploading to Twitter...")
                auth = tweepy.OAuth1UserHandler(
                    os.getenv("TW_API_KEY"), os.getenv("TW_API_SECRET"),
                    os.getenv("TW_ACCESS_TOKEN"), os.getenv("TW_ACCESS_SECRET")
                )
                api = tweepy.API(auth)
                media = api.media_upload(filename='temp.mp4', media_category='tweet_video')
                
                client = tweepy.Client(
                    consumer_key=os.getenv("TW_API_KEY"),
                    consumer_secret=os.getenv("TW_API_SECRET"),
                    access_token=os.getenv("TW_ACCESS_TOKEN"),
                    access_token_secret=os.getenv("TW_ACCESS_SECRET")
                )
                client.create_tweet(text="Trending now! #Viral #Trending #Freshubs", media_ids=[media.media_id])
                
                # Mark as done
                update_kv(v_id)
                print("✨ All steps successful!")
                return
        print("😴 No new videos to post.")
    except Exception as e:
        print(f"❌ Bot Error: {e}")

if __name__ == "__main__":
    run_bot()
