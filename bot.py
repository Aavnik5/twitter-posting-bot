import os, requests, tweepy, yt_dlp, json, random, time
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- CLOUDFLARE KV HELPERS ---
def is_already_posted(v_id):
    acc, kv, token = os.getenv("CF_ACCOUNT_ID"), os.getenv("CF_KV_NAMESPACE_ID"), os.getenv("CF_API_TOKEN")
    url = f"https://api.cloudflare.com/client/v4/accounts/{acc}/storage/kv/namespaces/{kv}/values/{v_id}"
    headers = {"Authorization": f"Bearer {token}"}
    try: 
        res = requests.get(url, headers=headers)
        return res.status_code == 200
    except: return False

def update_kv(v_id):
    acc, kv, token = os.getenv("CF_ACCOUNT_ID"), os.getenv("CF_KV_NAMESPACE_ID"), os.getenv("CF_API_TOKEN")
    url = f"https://api.cloudflare.com/client/v4/accounts/{acc}/storage/kv/namespaces/{kv}/values/{v_id}"
    headers = {"Authorization": f"Bearer {token}"}
    requests.put(url, headers=headers, data="posted")

# --- GOOGLE DRIVE BACKUP (Silent Error Fix) ---
def backup_to_drive(file_path, file_name):
    folder_id = os.getenv("GDRIVE_FOLDER_ID")
    if not folder_id: return
    try:
        creds_info = json.loads(os.getenv("GDRIVE_JSON"))
        creds = service_account.Credentials.from_service_account_info(creds_info)
        service = build('drive', 'v3', credentials=creds)
        file_metadata = {'name': file_name, 'parents': [folder_id]}
        media = MediaFileUpload(file_path, mimetype='video/mp4', resumable=False)
        service.files().create(body=file_metadata, media_body=media, supportsAllDrives=True).execute()
        print("✅ Drive Backup Done!")
    except: 
        print("⚠️ Drive Quota full, skipping backup...")

# --- MAIN RUN ---
def run_bot():
    print("🔎 Starting Bot Operations...")
    try:
        auth_url = "https://api.redgifs.com/v2/auth/temporary"
        token = requests.get(auth_url).json().get('token')
        res = requests.get("https://api.redgifs.com/v2/gifs/search?search_text=trending&order=trending&count=10", headers={"Authorization": f"Bearer {token}"}).json()
        gifs = res.get('gifs', [])
        
        for gif in gifs:
            v_id, user = gif.get('id'), gif.get('userName', 'Trending')
            if not is_already_posted(v_id):
                print(f"🎯 Target: {v_id}")
                
                if os.path.exists('temp.mp4'): os.remove('temp.mp4')
                with yt_dlp.YoutubeDL({'outtmpl': 'temp.mp4', 'quiet': True}) as ydl:
                    ydl.download([f"https://www.redgifs.com/watch/{v_id}"])
                
                # Step 1: Drive Backup (Silent)
                backup_to_drive('temp.mp4', f"{v_id}.mp4")
                
                # Step 2: Twitter Upload
                print("🐦 Uploading to Twitter...")
                auth = tweepy.OAuth1UserHandler(
                    os.getenv("TW_API_KEY"), os.getenv("TW_API_SECRET"),
                    os.getenv("TW_ACCESS_TOKEN"), os.getenv("TW_ACCESS_SECRET")
                )
                api = tweepy.API(auth)
                media = api.media_upload(filename='temp.mp4', media_category='tweet_video')
                
                # Hard Wait (Status check skip karne ke liye)
                print("⏳ Waiting 40s for Twitter processing (Bypassing 404 Status Check)...")
                time.sleep(40)

                # Step 3: Post Tweet (v2)
                client = tweepy.Client(
                    consumer_key=os.getenv("TW_API_KEY"),
                    consumer_secret=os.getenv("TW_API_SECRET"),
                    access_token=os.getenv("TW_ACCESS_TOKEN"),
                    access_token_secret=os.getenv("TW_ACCESS_SECRET")
                )
                
                # Caption logic
                captions = [f"Uff! Ye video hot hai 🔥", f"New trending clip! 🔞", f"Check this bold content 💎"]
                caption = f"{random.choice(captions)}\n\n#NSFW #Viral #Trending"
                
                response = client.create_tweet(text=caption, media_ids=[media.media_id])
                print(f"🚀 Tweet Posted! ID: {response.data['id']}")
                
                update_kv(v_id)
                if os.path.exists('temp.mp4'): os.remove('temp.mp4')
                return

    except Exception as e: 
        print(f"❌ Actual Bot Error: {e}")

if __name__ == "__main__":
    run_bot()
