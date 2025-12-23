import os, requests, tweepy, yt_dlp, json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- HELPERS ---
def is_already_posted(v_id):
    acc, kv, token = os.getenv("CF_ACCOUNT_ID"), os.getenv("CF_KV_NAMESPACE_ID"), os.getenv("CF_API_TOKEN")
    url = f"https://api.cloudflare.com/client/v4/accounts/{acc}/storage/kv/namespaces/{kv}/values/{v_id}"
    headers = {"Authorization": f"Bearer {token}"}
    try: return requests.get(url, headers=headers).status_code == 200
    except: return False

def update_kv(v_id):
    acc, kv, token = os.getenv("CF_ACCOUNT_ID"), os.getenv("CF_KV_NAMESPACE_ID"), os.getenv("CF_API_TOKEN")
    url = f"https://api.cloudflare.com/client/v4/accounts/{acc}/storage/kv/namespaces/{kv}/values/{v_id}"
    headers = {"Authorization": f"Bearer {token}"}
    requests.put(url, headers=headers, data="posted")

def backup_to_drive(file_path, file_name):
    folder_id = os.getenv("GDRIVE_FOLDER_ID")
    print(f"🛠️ Debug: Attempting upload to shared folder: {folder_id}")
    if not folder_id:
        print("❌ Error: GDRIVE_FOLDER_ID environment variable is missing!")
        return

    try:
        creds_info = json.loads(os.getenv("GDRIVE_JSON"))
        creds = service_account.Credentials.from_service_account_info(creds_info)
        service = build('drive', 'v3', credentials=creds)
        
        file_metadata = {'name': file_name, 'parents': [folder_id]}
        # Resumable=False is safer for small files with service accounts
        media = MediaFileUpload(file_path, mimetype='video/mp4', resumable=False)
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        print(f"✅ Drive Backup Successful! ID: {file.get('id')}")
    except Exception as e:
        print(f"❌ Drive Error (Check API Enablement): {e}")

# --- MAIN RUN ---
def run_bot():
    print("🔎 Starting Bot Operations...")
    try:
        # RedGIFs Auth
        auth_res = requests.get("https://api.redgifs.com/v2/auth/temporary").json()
        token = auth_res.get('token')
        
        # Search Content
        res = requests.get("https://api.redgifs.com/v2/gifs/search?search_text=trending&order=trending&count=5", headers={"Authorization": f"Bearer {token}"}).json()
        gif = res.get('gifs', [])[0]
        v_id, user = gif.get('id'), gif.get('userName', 'Trending')

        if not is_already_posted(v_id):
            print(f"🎯 New Video Found: {v_id}")
            with yt_dlp.YoutubeDL({'outtmpl': 'temp.mp4', 'quiet': True}) as ydl:
                ydl.download([f"https://www.redgifs.com/watch/{v_id}"])
            
            # Step 1: Drive Backup
            backup_to_drive('temp.mp4', f"{v_id}.mp4")
            
            # Step 2: Twitter Post
            print("🐦 Uploading to Twitter...")
            auth = tweepy.OAuth1UserHandler(os.getenv("TW_API_KEY"), os.getenv("TW_API_SECRET"), os.getenv("TW_ACCESS_TOKEN"), os.getenv("TW_ACCESS_SECRET"))
            api = tweepy.API(auth)
            media = api.media_upload(filename='temp.mp4', media_category='tweet_video')
            
            client = tweepy.Client(
                consumer_key=os.getenv("TW_API_KEY"), consumer_secret=os.getenv("TW_API_SECRET"),
                access_token=os.getenv("TW_ACCESS_TOKEN"), access_token_secret=os.getenv("TW_ACCESS_SECRET")
            )
            client.create_tweet(text=f"Trending now by {user} #RedGIFs #Viral #Freshubs", media_ids=[media.media_id])
            
            # Step 3: Mark as Done
            update_kv(v_id)
            print("✨ Mission Successful!")
        else:
            print("😴 No new videos found.")
    except Exception as e:
        print(f"❌ Bot Error: {e}")

if __name__ == "__main__":
    run_bot()
