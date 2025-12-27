import os, requests, tweepy, yt_dlp, json, random
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- CLOUDFLARE KV HELPERS ---
def is_already_posted(v_id):
    """Cloudflare KV check taaki duplicate posts na ho"""
    acc, kv, token = os.getenv("CF_ACCOUNT_ID"), os.getenv("CF_KV_NAMESPACE_ID"), os.getenv("CF_API_TOKEN")
    url = f"https://api.cloudflare.com/client/v4/accounts/{acc}/storage/kv/namespaces/{kv}/values/{v_id}"
    headers = {"Authorization": f"Bearer {token}"}
    try: 
        res = requests.get(url, headers=headers)
        return res.status_code == 200
    except: return False

def update_kv(v_id):
    """Video ID ko Cloudflare mein save karna (Edit Permission:)"""
    acc, kv, token = os.getenv("CF_ACCOUNT_ID"), os.getenv("CF_KV_NAMESPACE_ID"), os.getenv("CF_API_TOKEN")
    url = f"https://api.cloudflare.com/client/v4/accounts/{acc}/storage/kv/namespaces/{kv}/values/{v_id}"
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.put(url, headers=headers, data="posted")
    if res.status_code == 200:
        print(f"✅ Cloudflare KV Updated for: {v_id}")
    else:
        print(f"❌ KV Update Error: {res.text}")

# --- GOOGLE DRIVE BACKUP (Fixed for 403 Quota Error) ---
def backup_to_drive(file_path, file_name):
    """Upload to shared folder bypasses quota by using parent folder's space"""
    folder_id = os.getenv("GDRIVE_FOLDER_ID")
    if not folder_id: return
    try:
        creds_info = json.loads(os.getenv("GDRIVE_JSON"))
        creds = service_account.Credentials.from_service_account_info(creds_info)
        service = build('drive', 'v3', credentials=creds)
        
        file_metadata = {
            'name': file_name, 
            'parents': [folder_id]
        }
        # resumable=False is mandatory for Service Accounts on small shared folders
        media = MediaFileUpload(file_path, mimetype='video/mp4', resumable=False)
        
        # supportsAllDrives allows the service account to interact with your shared folder
        service.files().create(
            body=file_metadata, 
            media_body=media, 
            supportsAllDrives=True, 
            fields='id'
        ).execute()
        print("✅ Google Drive Backup Done!")
    except Exception as e: 
        print(f"❌ Drive Error (Check Folder Permission): {e}")

# --- RANDOM ADULT CAPTIONS LOGIC ---
def get_random_caption(user_name):
    """Har baar unique spicy text aur hashtags"""
    captions = [
        f"Uff! Ye video ekdum hot hai 🔥 Credits: {user_name}",
        f"New NSFW trending clip is here! 🔞 Credits: {user_name}",
        f"Check out this bold content by {user_name} 💎",
        f"Aaj ka sabse best adult video! 🚀 Credits: {user_name}",
        f"Don't miss this spicy clip by {user_name} 🌶️",
        f"Naya spicy maal aa gaya! 🌟 Credits: {user_name}",
        f"Ye clip dekh kar maza aa jayega! 🎯 Credits: {user_name}",
        f"Maza aa jayega ye dekh kar! 🔥 Credits: {user_name}",
        f"Bohot hi bold aur spicy content 🔞. Made by {user_name}",
        f"Is clip ko miss mat karna 💎. Credits: {user_name}",
        f"Late night special video for you 🌙. Credits: {user_name}",
        f"Extreme hotness in this clip! 🌶️ By {user_name}",
        f"Pakka pasand aayega ye maal 🎯. Credits: {user_name}",
        f"Sabse viral adult video abhi tak ka 🚀. By {user_name}",
        f"Truly wild and uncut version! ✨ Credits: {user_name}",
        f"Amateur beauty at its best 🔞. By {user_name}",
        f"Spicy content level 100! 🔥 Credits: {user_name}"
    ]
    hashtag_sets = [
        "#NSFW #AdultContent #Freepornx.site #Viral #PornVideo",
        "#HotVideo #Porn #Freepornx.site #TrendingNow #Adult",
        "#Naughty #Spicy #Freshubs #NSFWVideo #Xxx",
        "#AdultVideo #Freepornx.site #ViralVideo #Hottest #Pornstar",
        "#Explicit #Trending #NSFW #Nude #Freshubs",
        "#Porn #DailyViral #Freepornx.site #Explore #Sextape",
        "#Amateur #HotClip #Freepornx.site #Viral #Naughty",
        "#Sextape #Bhabhi #ViralVideo #Adult #Spicy",
        "#Freepornx.site #Desi #AdultContent #Hot #Nsfw",
        "#Xxx #Sex #Trending #ViralClip #Freshubs",
        "#Dirty #Horny #Freepornx.site #AdultVideo #Explicit",
        "#Wild #Sexy #SpicyContent #TrendingNow #Nsfw",
        "#NaughtyVideo #HotBhabhi #Freepornx.site #Freshubs #Viral",
        "#AmateurPorn #ViralVideo #Freepornx.site #Adult #Hot",
        "#LateNight #Sexting #Freepornx.site #SpicyMaal #Nsfw",
        "#HotAdult #TrendingVideo #Freepornx.site #DailyViral #Sex"
    ]
    return f"{random.choice(captions)}\n\n{random.choice(hashtag_sets)}"

# --- MAIN RUN ---
def run_bot():
    print("🔎 Starting Bot Operations...")
    try:
        # RedGIFs Authentication
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
                with yt_dlp.YoutubeDL({'outtmpl': 'temp.mp4', 'quiet': True}) as ydl:
                    ydl.download([video_url])
                
                # Step 1: Backup
                backup_to_drive('temp.mp4', f"{v_id}.mp4")
                
                # Step 2: Twitter Upload (v1.1 for Media, v2 for Tweet)
                # Ensure these keys match exactly with GitHub Secrets
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
                client.create_tweet(text=get_random_caption(user), media_ids=[media.media_id])
                
                # Step 3: KV Update
                update_kv(v_id)
                print(f"✨ Mission Successful! Posted: {v_id}")
                return
        print("😴 No new videos found.")
    except Exception as e: 
        print(f"❌ Bot Execution Error: {e}")

if __name__ == "__main__":
    run_bot()
