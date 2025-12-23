import os, requests, tweepy, yt_dlp, json, random
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- CLOUDFLARE KV HELPERS ---
def is_already_posted(v_id):
    """Checks Cloudflare KV to skip duplicate videos"""
    acc, kv, token = os.getenv("CF_ACCOUNT_ID"), os.getenv("CF_KV_NAMESPACE_ID"), os.getenv("CF_API_TOKEN")
    url = f"https://api.cloudflare.com/client/v4/accounts/{acc}/storage/kv/namespaces/{kv}/values/{v_id}"
    headers = {"Authorization": f"Bearer {token}"}
    try: 
        res = requests.get(url, headers=headers)
        return res.status_code == 200
    except: return False

def update_kv(v_id):
    """Saves Video ID to Cloudflare KV using Edit permissions"""
    acc, kv, token = os.getenv("CF_ACCOUNT_ID"), os.getenv("CF_KV_NAMESPACE_ID"), os.getenv("CF_API_TOKEN")
    url = f"https://api.cloudflare.com/client/v4/accounts/{acc}/storage/kv/namespaces/{kv}/values/{v_id}"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        # Putting data marks the video as posted
        res = requests.put(url, headers=headers, data="posted")
        if res.status_code == 200:
            print(f"✅ Cloudflare KV Updated: {v_id} skip hoga agli baar.")
        else:
            print(f"❌ KV Update Failed! Status: {res.status_code}, Response: {res.text}")
    except Exception as e:
        print(f"❌ Cloudflare Connection Error: {e}")

# --- GOOGLE DRIVE BACKUP (Fixed for Quota Error) ---
def backup_to_drive(file_path, file_name):
    """Uploads to Shared Folder using parents and supportsAllDrives"""
    folder_id = os.getenv("GDRIVE_FOLDER_ID")
    if not folder_id: return
    try:
        creds_info = json.loads(os.getenv("GDRIVE_JSON"))
        creds = service_account.Credentials.from_service_account_info(creds_info)
        service = build('drive', 'v3', credentials=creds)
        
        file_metadata = {'name': file_name, 'parents': [folder_id]}
        # resumable=False avoids quota issues for Service Accounts
        media = MediaFileUpload(file_path, mimetype='video/mp4', resumable=False)
        service.files().create(body=file_metadata, media_body=media, supportsAllDrives=True).execute()
        print("✅ Google Drive Backup Done!")
    except Exception as e: 
        print(f"❌ Drive Error: {e}")

# --- RANDOM ADULT CAPTIONS & BRANDING ---
def get_random_caption(user_name):
    """Large list of spicy captions and hashtags for Freepornx.site"""
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

# --- MAIN BOT RUN ---
def run_bot():
    print("🔎 Starting Bot Operations...")
    try:
        # RedGIFs Authentication
        auth_url = "https://api.redgifs.com/v2/auth/temporary"
        token = requests.get(auth_url).json().get('token')
        
        # Search Trending Content
        res = requests.get("https://api.redgifs.com/v2/gifs/search?search_text=trending&order=trending&count=10", headers={"Authorization": f"Bearer {token}"}).json()
        gifs = res.get('gifs', [])
        
        for gif in gifs:
            v_id, user = gif.get('id'), gif.get('userName', 'Trending')
            
            # Step 1: Check Cloudflare KV for duplicates
            if not is_already_posted(v_id):
                print(f"🎯 New Video Found: {v_id}")
                video_url = f"https://www.redgifs.com/watch/{v_id}"
                
                # Download Video
                with yt_dlp.YoutubeDL({'outtmpl': 'temp.mp4', 'quiet': True}) as ydl:
                    ydl.download([video_url])
                
                # Step 2: Backup to Google Drive
                backup_to_drive('temp.mp4', f"{v_id}.mp4")
                
                # Step 3: Twitter Post (Tokens:)
                print("🐦 Uploading to Twitter...")
                caption = get_random_caption(user)
                auth = tweepy.OAuth1UserHandler(os.getenv("TW_API_KEY"), os.getenv("TW_API_SECRET"), os.getenv("TW_ACCESS_TOKEN"), os.getenv("TW_ACCESS_SECRET"))
                api = tweepy.API(auth)
                media = api.media_upload(filename='temp.mp4', media_category='tweet_video')
                
                client = tweepy.Client(os.getenv("TW_API_KEY"), os.getenv("TW_API_SECRET"), os.getenv("TW_ACCESS_TOKEN"), os.getenv("TW_ACCESS_SECRET"))
                client.create_tweet(text=caption, media_ids=[media.media_id])
                
                # Step 4: Update Cloudflare KV to avoid repeat
                update_kv(v_id)
                print(f"✨ Mission Successful! Posted: {v_id}")
                return
        print("😴 No new unique videos found.")
    except Exception as e:
        print(f"❌ Bot Execution Error: {e}")

if __name__ == "__main__":
    run_bot()
