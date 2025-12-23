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
    res = requests.get(url, headers=headers)
    return res.status_code == 200

def update_kv(video_id):
    acc = os.getenv("CF_ACCOUNT_ID")
    kv = os.getenv("CF_KV_NAMESPACE_ID")
    token = os.getenv("CF_API_TOKEN")
    url = f"https://api.cloudflare.com/client/v4/accounts/{acc}/storage/kv/namespaces/{kv}/values/{video_id}"
    headers = {"Authorization": f"Bearer {token}"}
    requests.put(url, headers=headers, data="posted")

def backup_to_drive(file_path, file_name):
    print("Backing up to Google Drive...")
    try:
        creds_info = json.loads(os.getenv("GDRIVE_JSON"))
        creds = service_account.Credentials.from_service_account_info(creds_info)
        service = build('drive', 'v3', credentials=creds)
        file_metadata = {'name': file_name, 'parents': [os.getenv("GDRIVE_FOLDER_ID")]}
        media = MediaFileUpload(file_path, mimetype='video/mp4')
        service.files().create(body=file_metadata, media_body=media).execute()
        print("Backup done!")
    except Exception as e: print(f"Drive Error: {e}")

def post_to_twitter(file_path, title):
    caption = f"{title}\n\n#RedGIFs #Viral #Trending"
    auth = tweepy.OAuth1UserHandler(os.getenv("TW_API_KEY"), os.getenv("TW_API_SECRET"), os.getenv("TW_ACCESS_TOKEN"), os.getenv("TW_ACCESS_SECRET"))
    api = tweepy.API(auth)
    print("Uploading to Twitter...")
    media = api.media_upload(filename=file_path, media_category='tweet_video')
    client = tweepy.Client(consumer_key=os.getenv("TW_API_KEY"), consumer_secret=os.getenv("TW_API_SECRET"), access_token=os.getenv("TW_ACCESS_TOKEN"), access_token_secret=os.getenv("TW_ACCESS_SECRET"))
    client.create_tweet(text=caption, media_ids=[media.media_id])

# --- DYNAMIC TRENDING LOGIC ---

def run_bot():
    # Trending URL
    search_url = "https://www.redgifs.com/gifs/browse/trending" 
    
    ydl_opts_list = {'quiet': True, 'extract_flat': True}

    with yt_dlp.YoutubeDL(ydl_opts_list) as ydl:
        print("Fetching trending list...")
        result = ydl.extract_info(search_url, download=False)
        
        if 'entries' in result:
            for entry in result['entries']:
                video_id = entry['id']
                if not is_already_posted(video_id):
                    print(f"New trending video found: {video_id}. Downloading...")
                    
                    video_url = f"https://www.redgifs.com/watch/{video_id}"
                    with yt_dlp.YoutubeDL({'outtmpl': 'temp.mp4', 'quiet': True}) as dl:
                        info = dl.extract_info(video_url, download=True)
                        title = info.get('title', 'Trending Video')
                        
                        # Process
                        backup_to_drive('temp.mp4', f"{video_id}.mp4")
                        post_to_twitter('temp.mp4', title)
                        update_kv(video_id)
                        
                        print(f"Successfully posted: {video_id}")
                        return # Exit after one post
                else:
                    print(f"Skipping {video_id}, already posted.")
        else:
            print("Trending section mein koi video nahi mila.")

if __name__ == "__main__":
    run_bot()
