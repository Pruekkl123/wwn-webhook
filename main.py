from fastapi import FastAPI, Request
import httpx
import json
import base64
import os

app = FastAPI()

# ดึงค่าความลับจาก Environment Variables บน Vercel
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "Pruekkl123/wwn-news") # ชื่อ GitHub Repository เว็บข่าวของคุณเพตัน

@app.post("/webhook")
async def line_webhook(request: Request):
    body = await request.json()
    events = body.get("events", [])
    
    for event in events:
        if event["type"] == "message" and event["message"]["type"] == "text":
            user_text = event["message"]["text"]
            
            # รูปแบบเวลาพิมพ์สั่งในแชท LINE:
            # NEWS: หัวข้อข่าว | รายละเอียดเนื้อหาข่าว
            if user_text.startswith("NEWS:"):
                news_content = user_text.replace("NEWS:", "").strip()
                parts = news_content.split("|")
                if len(parts) >= 2:
                    new_title = parts[0].strip()
                    new_desc = parts[1].strip()
                    
                    # สั่งอัปเดตไฟล์ news.json บน GitHub ทันที
                    await update_github_news(new_title, new_desc)
                    
    return {"status": "ok"}

async def update_github_news(title, desc):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/news.json"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    
    async with httpx.AsyncClient() as client:
        # 1. ดึงไฟล์ news.json ปัจจุบันลงมา
        resp = await client.get(url, headers=headers)
        if resp.status_code != 200:
            return
        
        file_data = resp.json()
        sha = file_data["sha"]
        
        current_content = json.loads(base64.b64decode(file_data["content"]).decode("utf-8"))
        
        # 2. สร้างเรคอร์ดข่าวใหม่ ยัดไว้บนสุดเพื่อให้ขึ้นเว็บเป็นข่าวล่าสุด
        new_item = {
            "cat": "Sweden",
            "date": "NOV 3, 2026",
            "title": title,
            "desc": desc,
            "img": "https://picsum.photos/seed/line_sync_" + str(len(current_content) + 10) + "/800/600"
        }
        current_content.insert(0, new_item)
        
        # 3. เข้ารหัสแล้วยิง API อัปเดตขึ้น GitHub
        updated_json_str = json.dumps(current_content, indent=4, ensure_ascii=False)
        encoded_content = base64.b64encode(updated_json_str.encode("utf-8")).decode("utf-8")
        
        payload = {
            "message": "Sync news from LINE Bot automatically",
            "content": encoded_content,
            "sha": sha
        }
        
        await client.put(url, headers=headers, json=payload)
