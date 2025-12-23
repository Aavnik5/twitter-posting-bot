import os
import requests
import tweepy
import yt_dlp
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- CLOUDFLARE & DRIVE HELPERS ---

def is_already_posted(video_id):
    acc, kv, token = os.getenv("CF_ACCOUNT_ID"), os.getenv("CF_KV_NAMESPACE_ID"), os.getenv("CF_API_TOKEN")
    url = f"https://api.cloudflare.com/client/v4/accounts/{acc}/storage/kv/namespaces/{kv}/values/{video_id}"
    headers = {"Authorization": f"Bearer {token}"}
    try: return requests.get(url, headers=headers).status_code == 200
    except: return False

def update_kv(video_id):
    acc, kv, token = os.getenv("CF_ACCOUNT_ID"), os.getenv("CF_KV_NAMESPACE_ID"), os.getenv("CF_API_TOKEN")
    url = f"https://api.cloudflare.com/client/v4/accounts/{acc}/storage/kv/namespaces/{kv}/values/{video_id}"
    headers = {"Authorization": f"Bearer {token}"}
    requests.put(url, headers=headers, data="posted")

def backup_to_drive(file_path, file_name):
    print("🚀 Backing up to Drive...")
    try:
        creds_info = json.loads(os.getenv("GDRIVE_JSON"))
        creds = service_account.Credentials.from_service_account_info(creds_info)
        service = build('drive', 'v3', credentials=creds)
        file_metadata = {'name': file_name, 'parents': [os.getenv("GDRIVE_FOLDER_ID")]}
        media = MediaFileUpload(file_path, mimetype='video/mp4')
        service.files().create(body=file_metadata, media_body=media).execute()
        print("✅ Drive Backup Done!")
    except Exception as e: print(f"❌ Drive Error: {e}")

# --- REDGIFS API LOGIC ---

def get_redgifs_token():
    """RedGIFs se temporary API token lena"""
    url = "https://api.redgifs.com/v2/auth/temporary"
    try:
        res = requests.get(url)
        return res.json().get('token')
    except: return None

def get_trending_video(token):
    """API ka use karke trending video dhoondhna"""
    url = "https://api.redgifs.com/v2/gifs/search?search_text=trending&order=trending&count=10"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        res = requests.get(url, headers=headers)
        gifs = res.json().get('gifs', [])
        for gif in gifs:
            video_id = gif.get('id')
            if not is_already_posted(video_id):
                return video_id, gif.get('userName', 'Trending')
    except: return None, None
    return None, None

# --- TWITTER LOGIC ---

def post_to_twitter(file_path, title):
    caption = f"Trending now: {title}\n\n#RedGIFs #Viral #Freshubs"
    auth = tweepy.OAuth1UserHandler(os.getenv("TW_API_KEY"), os.getenv("TW_API_SECRET"), os.getenv("TW_ACCESS_TOKEN"), os.getenv("TW_ACCESS_SECRET"))
    api = tweepy.API(auth)
    print("🐦 Uploading to Twitter...")
    media = api.media_upload(filename=file_path, media_category='tweet_video')
    client = tweepy.Client(consumer_key=os.getenv("TW_API_KEY"), consumer_secret=os.getenv("TW_API_SECRET"), access_token=os.getenv("TW_ACCESS_TOKEN"), access_token_secret=os.getenv("TW_ACCESS_SECRET"))
    client.create_tweet(text=caption, media_ids=[media.media_id])

# --- MAIN RUN ---

def run_bot():
    print("🔎 Fetching RedGIFs Token...")
    token = get_redgifs_token()
    if not token:
        print("❌ Token nahi mila!")
        return

    video_id, user_name = get_trending_video(token)
    if video_id:
        print(f"🎯 Video Found: {video_id}")
        video_url = f"https://www.redgifs.com/watch/{video_id}"
        
        # Download logic
        ydl_opts = {'outtmpl': 'temp.mp4', 'quiet': True, 'no_warnings': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                ydl.download([video_url])
                backup_to_drive('temp.mp4', f"{video_id}.mp4")
                post_to_twitter('temp.mp4', user_name)
                update_kv(video_id)
                print("✨ Mission Successful!")
            except Exception as e:
                print(f"❌ Error: {e}")
    else:
        print("😴 No new videos to post.")

if __name__ == "__main__":
    run_bot()
