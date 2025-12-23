import os
import requests
import tweepy
import yt_dlp
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- CONFIGURATION ---

def is_already_posted(video_id):
    acc = os.getenv("CF_ACCOUNT_ID")
    kv = os.getenv("CF_KV_NAMESPACE_ID")
    token = os.getenv("CF_API_TOKEN")
    url = f"https://api.cloudflare.com/client/v4/accounts/{acc}/storage/kv/namespaces/{kv}/values/{video_id}"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        res = requests.get(url, headers=headers)
        return res.status_code == 200
    except: return False

def update_kv(video_id):
    acc = os.getenv("CF_ACCOUNT_ID")
    kv = os.getenv("CF_KV_NAMESPACE_ID")
    token = os.getenv("CF_API_TOKEN")
    url = f"https://api.cloudflare.com/client/v4/accounts/{acc}/storage/kv/namespaces/{kv}/values/{video_id}"
    headers = {"Authorization": f"Bearer {token}"}
    requests.put(url, headers=headers, data="posted")

def backup_to_drive(file_path, file_name):
    print("🚀 Google Drive par backup ho raha hai...")
    try:
        creds_info = json.loads(os.getenv("GDRIVE_JSON"))
        creds = service_account.Credentials.from_service_account_info(creds_info)
        service = build('drive', 'v3', credentials=creds)
        file_metadata = {'name': file_name, 'parents': [os.getenv("GDRIVE_FOLDER_ID")]}
        media = MediaFileUpload(file_path, mimetype='video/mp4')
        service.files().create(body=file_metadata, media_body=media).execute()
        print("✅ Backup Successful!")
    except Exception as e: print(f"❌ Drive Error: {e}")

def post_to_twitter(file_path, title):
    caption = f"{title}\n\n#RedGIFs #Viral #Trending #Freshubs"
    auth = tweepy.OAuth1UserHandler(os.getenv("TW_API_KEY"), os.getenv("TW_API_SECRET"), os.getenv("TW_ACCESS_TOKEN"), os.getenv("TW_ACCESS_SECRET"))
    api = tweepy.API(auth)
    print("🐦 Twitter par upload ho raha hai...")
    media = api.media_upload(filename=file_path, media_category='tweet_video')
    client = tweepy.Client(consumer_key=os.getenv("TW_API_KEY"), consumer_secret=os.getenv("TW_API_SECRET"), access_token=os.getenv("TW_ACCESS_TOKEN"), access_token_secret=os.getenv("TW_ACCESS_SECRET"))
    client.create_tweet(text=caption, media_ids=[media.media_id])

# --- DYNAMIC TRENDING LOGIC ---

def run_bot():
    # Trending aur Popular dono URLs try karenge
    urls_to_try = [
        "https://www.redgifs.com/gifs/search/popular",
        "https://www.redgifs.com/trending"
    ]
    
    ydl_opts_list = {
        'quiet': True, 
        'extract_flat': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'referer': 'https://www.redgifs.com/'
    }

    found_video = False
    for search_url in urls_to_try:
        if found_video: break
        
        print(f"🔎 Scanning: {search_url}")
        with yt_dlp.YoutubeDL(ydl_opts_list) as ydl:
            try:
                result = ydl.extract_info(search_url, download=False)
                if 'entries' in result and result['entries']:
                    for entry in result['entries']:
                        video_id = entry['id']
                        if not is_already_posted(video_id):
                            print(f"🎯 New Video Found: {video_id}")
                            video_url = f"https://www.redgifs.com/watch/{video_id}"
                            
                            dl_opts = {
                                'outtmpl': 'temp.mp4', 
                                'quiet': True,
                                'user_agent': ydl_opts_list['user_agent']
                            }
                            
                            with yt_dlp.YoutubeDL(dl_opts) as dl:
                                info = dl.extract_info(video_url, download=True)
                                title = info.get('title', 'Trending Now')
                                
                                backup_to_drive('temp.mp4', f"{video_id}.mp4")
                                post_to_twitter('temp.mp4', title)
                                update_kv(video_id)
                                
                                print("✨ Mission Accomplished!")
                                found_video = True
                                break 
                else:
                    print(f"⚠️ No entries in {search_url}, trying next...")
            except Exception as e:
                print(f"⚠️ Error on {search_url}: {e}")

if __name__ == "__main__":
    run_bot()
