import os
import requests
import tweepy
import yt_dlp
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- CONFIGURATION & HELPERS ---

def already_posted(video_id):
    """Cloudflare KV se check karna ki video purana hai ya nahi"""
    acc = os.getenv("CF_ACCOUNT_ID")
    kv = os.getenv("CF_KV_NAMESPACE_ID")
    token = os.getenv("CF_API_TOKEN")
    url = f"https://api.cloudflare.com/client/v4/accounts/{acc}/storage/kv/namespaces/{kv}/values/{video_id}"
    headers = {"Authorization": f"Bearer {token}"}
    return requests.get(url, headers=headers).status_code == 200

def update_kv(video_id):
    """Post hone ke baad Cloudflare KV mein save karna"""
    acc = os.getenv("CF_ACCOUNT_ID")
    kv = os.getenv("CF_KV_NAMESPACE_ID")
    token = os.getenv("CF_API_TOKEN")
    url = f"https://api.cloudflare.com/client/v4/accounts/{acc}/storage/kv/namespaces/{kv}/values/{video_id}"
    headers = {"Authorization": f"Bearer {token}"}
    requests.put(url, headers=headers, data="posted")

def backup_to_drive(file_path, file_name):
    """Google Drive mein video backup karna"""
    print(f"Backing up {file_name} to Google Drive...")
    creds_json = json.loads(os.getenv("GDRIVE_JSON"))
    creds = service_account.Credentials.from_service_account_info(creds_json)
    service = build('drive', 'v3', credentials=creds)
    
    file_metadata = {
        'name': file_name,
        'parents': [os.getenv("GDRIVE_FOLDER_ID")]
    }
    media = MediaFileUpload(file_path, mimetype='video/mp4')
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    print(f"Backup Successful! File ID: {file.get('id')}")

def post_to_twitter(file_path, title):
    """Twitter par keywords aur hashtags ke saath post karna"""
    # Hashtags aur Keywords customize karein
    hashtags = "#RedGIFs #ViralVideo #Trending #KroldIT"
    caption = f"{title}\n\n{hashtags}"

    auth = tweepy.OAuth1UserHandler(
        os.getenv("TW_API_KEY"), os.getenv("TW_API_SECRET"),
        os.getenv("TW_ACCESS_TOKEN"), os.getenv("TW_ACCESS_SECRET")
    )
    api = tweepy.API(auth)
    
    print("Uploading to Twitter...")
    media = api.media_upload(filename=file_path, media_category='tweet_video')
    
    client = tweepy.Client(
        consumer_key=os.getenv("TW_API_KEY"),
        consumer_secret=os.getenv("TW_API_SECRET"),
        access_token=os.getenv("TW_ACCESS_TOKEN"),
        access_token_secret=os.getenv("TW_ACCESS_SECRET")
    )
    client.create_tweet(text=caption, media_ids=[media.media_id])

# --- MAIN FLOW ---

def run_bot():
    # Example URL (Isko aap dynamic bhi bana sakte hain)
    target_url = "https://www.redgifs.com/watch/stunningkeyalligator" 

    ydl_opts = {'outtmpl': 'temp_video.mp4', 'quiet': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(target_url, download=True)
        video_id = info['id']
        title = info.get('title', 'Check this out!')

    if not already_posted(video_id):
        # 1. Backup to Google Drive
        backup_to_drive('temp_video.mp4', f"{video_id}.mp4")
        
        # 2. Post to Twitter
        post_to_twitter('temp_video.mp4', title)
        
        # 3. Update Cloudflare KV
        update_kv(video_id)
        print("Done!")
    else:
        print("Already posted, skipping...")

    if os.path.exists('temp_video.mp4'):
        os.remove('temp_video.mp4')

if __name__ == "__main__":
    import json
    run_bot()
