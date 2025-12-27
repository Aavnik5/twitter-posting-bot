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
    res = requests.put(url, headers=headers, data="posted")
    if res.status_code == 200:
        print(f"✅ Cloudflare KV Updated for: {v_id}")
    else:
        print(f"❌ KV Update Error: {res.text}")

# --- GOOGLE DRIVE BACKUP (Quota Fix) ---
def backup_to_drive(file_path, file_name):
    folder_id = os.getenv("GDRIVE_FOLDER_ID")
    if not folder_id: return
    try:
        creds_info = json.loads(os.getenv("GDRIVE_JSON"))
        creds = service_account.Credentials.from_service_account_info(creds_info)
        service = build('drive', 'v3', credentials=creds)
        file_metadata = {'name': file_name, 'parents': [folder_id]}
        media = MediaFileUpload(file_path, mimetype='video/mp4', resumable=False)
        service.files().create(body=file_metadata, media_body=media, supportsAllDrives=True, fields='id').execute()
        print("✅ Google Drive Backup Done!")
    except Exception as e: 
        print(f"❌ Drive Error: {e}")

# --- RANDOM ADULT CAPTIONS ---
def get_random_caption(user_name):
    captions = [
        f"Uff! Ye video ekdum hot hai 🔥 Credits: {user_name}",
        f"New NSFW trending clip is here! 🔞 Credits: {user_name}",
        f"Check out this bold content by {user_name} 💎",
        f"Don't miss this spicy clip by {user_name} 🌶️"
    ]
    hashtag_sets = ["#NSFW #AdultContent #Viral", "#HotVideo #TrendingNow #Adult", "#Naughty #Spicy #Xxx"]
    return f"{random.choice(captions)}\n\n{random.choice(hashtag_sets)}"

# --- MAIN RUN ---
def run_bot():
    print("🔎 Starting Bot Operations...")
    try:
        # RedGIFs Auth
        auth_url = "https://api.redgifs.com/v2/auth/temporary"
        token = requests.get(auth_url).json().get('token')
        
        # Get Trending Videos
        res = requests.get("https://api.redgifs.com/v2/gifs/search?search_text=trending&order=trending&count=10", headers={"Authorization": f"Bearer {token}"}).json()
        gifs = res.get('gifs', [])
        
        for gif in gifs:
            v_id, user = gif.get('id'), gif.get('userName', 'Trending')
            if not is_already_posted(v_id):
                print(f"🎯 New Video Found: {v_id}")
                video_url = f"https://www.redgifs.com/watch/{v_id}"
                
                # Download Video
                if os.path.exists('temp.mp4'): os.remove('temp.mp4')
                with yt_dlp.YoutubeDL({'outtmpl': 'temp.mp4', 'quiet': True}) as ydl:
                    ydl.download([video_url])
                
                # Step 1: Backup (Isse 403 aaye toh bhi Twitter post chalega)
                backup_to_drive('temp.mp4', f"{v_id}.mp4")
                
                # Step 2: Twitter Upload
                print("🐦 Uploading to Twitter...")
                auth = tweepy.OAuth1UserHandler(
                    os.getenv("TW_API_KEY"), os.getenv("TW_API_SECRET"),
                    os.getenv("TW_ACCESS_TOKEN"), os.getenv("TW_ACCESS_SECRET")
                )
                api = tweepy.API(auth)
                
                # 1. Upload Video
                media = api.media_upload(filename='temp.mp4', media_category='tweet_video')
                media_id = media.media_id
                
                # 2. Wait for Processing (CRITICAL FIX)
                print("⏳ Waiting for Twitter to process the video...")
                check_count = 0
                while check_count < 10:
                    status = api.get_media_upload_status(media_id)
                    if status.state == 'succeeded':
                        print("✅ Video Processed!")
                        break
                    elif status.state == 'failed':
                        print("❌ Twitter processing failed.")
                        return
                    check_count += 1
                    time.sleep(5) # Har 5 sec mein check karega

                # 3. Create Tweet (v2)
                client = tweepy.Client(
                    consumer_key=os.getenv("TW_API_KEY"),
                    consumer_secret=os.getenv("TW_API_SECRET"),
                    access_token=os.getenv("TW_ACCESS_TOKEN"),
                    access_token_secret=os.getenv("TW_ACCESS_SECRET")
                )
                
                tweet_res = client.create_tweet(text=get_random_caption(user), media_ids=[media_id])
                print(f"🚀 Tweet Response: {tweet_res}")
                
                # Step 3: KV Update
                update_kv(v_id)
                print(f"✨ Mission Successful! Posted: {v_id}")
                if os.path.exists('temp.mp4'): os.remove('temp.mp4')
                return

        print("😴 No new videos found.")
    except Exception as e: 
        print(f"❌ Bot Execution Error: {e}")

if __name__ == "__main__":
    run_bot()
