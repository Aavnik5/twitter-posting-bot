import os, requests, tweepy, yt_dlp, time

# --- 1. CLOUDFLARE KV CHECK (Duplicate Rokne ke liye) ---
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

# --- 2. MAIN BOT RUN ---
def run_bot():
    print("🔎 Starting Bot Operations...")
    try:
        # RedGIFs Auth
        auth_url = "https://api.redgifs.com/v2/auth/temporary"
        token = requests.get(auth_url).json().get('token')
        
        # Get Trending Videos
        res = requests.get("https://api.redgifs.com/v2/gifs/search?search_text=trending&order=trending&count=5", headers={"Authorization": f"Bearer {token}"}).json()
        gifs = res.get('gifs', [])
        
        for gif in gifs:
            v_id, user = gif.get('id'), gif.get('userName', 'Trending')
            if not is_already_posted(v_id):
                print(f"🎯 New Video Found: {v_id}")
                
                # Download Video
                if os.path.exists('temp.mp4'): os.remove('temp.mp4')
                with yt_dlp.YoutubeDL({'outtmpl': 'temp.mp4', 'quiet': True}) as ydl:
                    ydl.download([f"https://www.redgifs.com/watch/{v_id}"])
                
                # Twitter Authentication (v1.1 for Media)
                auth = tweepy.OAuth1UserHandler(
                    os.getenv("TW_API_KEY"), os.getenv("TW_API_SECRET"),
                    os.getenv("TW_ACCESS_TOKEN"), os.getenv("TW_ACCESS_SECRET")
                )
                api = tweepy.API(auth)
                
                print("🐦 Uploading media to Twitter...")
                media = api.media_upload(filename='temp.mp4', media_category='tweet_video')
                media_id = media.media_id
                
                # CRITICAL: Processing Wait
                print("⏳ Waiting 45 seconds for Twitter to process the video...")
                time.sleep(45) 
                
                # Twitter Authentication (v2 for Tweeting)
                client = tweepy.Client(
                    consumer_key=os.getenv("TW_API_KEY"),
                    consumer_secret=os.getenv("TW_API_SECRET"),
                    access_token=os.getenv("TW_ACCESS_TOKEN"),
                    access_token_secret=os.getenv("TW_ACCESS_SECRET")
                )
                
                caption = f"Check this out! 🔥 Credits: {user}\n\n#Viral #Trending #TrendingNow"
                client.create_tweet(text=caption, media_ids=[media_id])
                
                # KV Update & Cleanup
                update_kv(v_id)
                print(f"✅ Mission Successful! Posted: {v_id}")
                if os.path.exists('temp.mp4'): os.remove('temp.mp4')
                return
                
        print("😴 No new videos found.")
    except Exception as e: 
        print(f"❌ Bot Execution Error: {e}")

if __name__ == "__main__":
    run_bot()
