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
    """Cloudflare KV check to prevent duplicates"""
    acc, kv, token = os.getenv("CF_ACCOUNT_ID"), os.getenv("CF_KV_NAMESPACE_ID"), os.getenv("CF_API_TOKEN")
    url = f"https://api.cloudflare.com/client/v4/accounts/{acc}/storage/kv/namespaces/{kv}/values/{video_id}"
    headers = {"Authorization": f"Bearer {token}"}
    try: 
        res = requests.get(url, headers=headers)
        return res.status_code == 200
    except: return False

def update_kv(video_id):
    """Mark video as posted in Cloudflare"""
    acc, kv, token = os.getenv("CF_ACCOUNT_ID"), os.getenv("CF_KV_NAMESPACE_ID"), os.getenv("CF_API_TOKEN")
    url = f"https://api.cloudflare.com/client/v4/accounts/{acc}/storage/kv/namespaces/{kv}/values/{video_id}"
    headers = {"Authorization": f"Bearer {token}"}
    requests.put(url, headers=headers, data="posted")

def backup_to_drive(file_path, file_name):
    """Upload video to shared Google Drive folder"""
    print(f"🚀 Backing up {file_name} to Drive...")
    try:
        creds_info = json.loads(os.getenv("GDRIVE_JSON"))
        creds = service_account.Credentials.from_service_account_info(creds_info)
        service = build('drive', 'v3', credentials=creds)
        
        # Using the specific Folder ID you shared
        folder_id = os.getenv("GDRIVE_FOLDER_ID")
        
        file_metadata = {'name': file_name, 'parents': [folder_id]}
        media = MediaFileUpload(file_path, mimetype='video/mp4', resumable=True)
        service.files().create(body=file_metadata, media_body=media).execute()
        print("✅ Drive Backup Successful!")
    except Exception as e: 
        print(f"❌ Drive Error: {e}")

# --- REDGIFS API LOGIC ---

def get_redgifs_token():
    """Get temporary API token from RedGIFs"""
    url = "https://api.redgifs.com/v2/auth/temporary"
    try:
        res = requests.get(url)
        return res.json().get('token')
    except: return None

def get_trending_video(token):
    """Find a new trending video using API"""
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
    """Post to Twitter with keywords and hashtags"""
    # Using your requested hashtags
    caption = f"Trending now by {title}\n\n#RedGIFs #Viral #Trending #Freshubs"
    
    auth = tweepy.OAuth1UserHandler(
        os.getenv("TW_API_KEY"), os.getenv("TW_API_SECRET"),
        os.getenv("TW_ACCESS_TOKEN"), os.getenv("TW_ACCESS_SECRET")
    )
    api = tweepy.API(auth)
    
    print("🐦 Uploading to Twitter...")
    media = api.media_upload(filename=file_path, media_category='tweet_video')
    
    client = tweepy.Client(
        consumer_key=os.getenv("TW_API_KEY"), consumer_secret=os.getenv("TW_API_SECRET"),
        access_token=os.getenv("TW_ACCESS_TOKEN"), access_token_secret=os.getenv("TW_ACCESS_SECRET")
    )
    client.create_tweet(text=caption, media_ids=[media.media_id])

# --- MAIN RUN ---

def run_bot():
    print("🔎 Initializing Bot...")
    token = get_redgifs_token()
    if not token:
        print("❌ Could not get RedGIFs token.")
        return

    video_id, user_name = get_trending_video(token)
    if video_id:
        print(f"🎯 New Video Found: {video_id}")
        video_url = f"https://www.redgifs.com/watch/{video_id}"
        
        ydl_opts = {'outtmpl': 'temp.mp4', 'quiet': True, 'no_warnings': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                ydl.download([video_url])
                
                # Step 1: Backup
                backup_to_drive('temp.mp4', f"{video_id}.mp4")
                
                # Step 2: Twitter Post
                post_to_twitter('temp.mp4', user_name)
                
                # Step 3: Cloudflare Record
                update_kv(video_id)
                
                print("✨ Job finished successfully!")
            except Exception as e:
                print(f"❌ Error during execution: {e}")
    else:
        print("😴 No new trending videos found.")

if __name__ == "__main__":
    run_bot()
