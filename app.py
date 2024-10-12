from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage, TemplateMessage, ButtonsTemplate, PostbackAction, ShowLoadingAnimationRequest, ImageMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent, PostbackEvent
import time
import firebase_admin
from firebase_admin import credentials, firestore
import json
import os
import requests

# 從環境變數讀取 JSON 格式的憑證
service_account_info = json.loads(os.getenv('GOOGLE_CREDENTIALS'))
cred = credentials.Certificate(service_account_info)
firebase_admin.initialize_app(cred)

# 初始化 Firestore 客戶端
db = firestore.client()

app = Flask(__name__)

# 建立 Configuration 和 ApiClient 的實例
configuration = Configuration(access_token=os.getenv('LINE_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_SECRET'))

def show_loading_animation(user_id, loading_seconds=5):
    url = 'https://api.line.me/v2/bot/chat/loading/start'
    LINE_ACCESS_TOKEN = os.getenv('LINE_ACCESS_TOKEN')
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {LINE_ACCESS_TOKEN}'
    }
    payload = {
        "chatId": user_id,
        "loadingSeconds": loading_seconds
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        print("成功顯示載入動畫")
    else:
        print(f"顯示載入動畫失敗: {response.status_code}, {response.text}")

def initialize_user_list():
    """初始化，將群組中的所有用戶加入 user_list 和 drink_list"""
    members_name = ["陳永慶", "Chris煒智🎸", "Kuan Shu Fan", "Wei", "傑仁", "吳建鋒","呂呂","柏燐","育豪(Fortitude)","莊阿嘎","金庸","鐘小豬","阿勛（運動按摩-史考特）","陳阿祥"]

    user_list_ref = db.collection("user_list")
    drink_list_ref = db.collection("drink_list")

    for member_name in members_name:
        try:
            user_doc = user_list_ref.document(member_name).get()
            if not user_doc.exists:
                user_list_ref.document(member_name).set({"name": member_name})

            drink_doc = drink_list_ref.document(member_name).get()
            if not drink_doc.exists:
                drink_list_ref.document(member_name).set({"name": member_name})

        except Exception as e:
            print(f"無法儲存成員 {member_name} 的資料: {e}")

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("Invalid signature.")
        abort(400)

    return 'OK'

# 處理文字訊息事件
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_id = event.source.user_id
    user_message = event.message.text
    
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        profile = line_bot_api.get_profile(user_id=user_id)
        user_name = profile.display_name

        show_loading_animation(user_id, loading_seconds=5)

        if "_STAR" in user_message:
            template_message = TemplateMessage(
                alt_text="這是樣板訊息",
                template=ButtonsTemplate(
                    thumbnail_image_url="https://www.deafsports.org.tw/web/wp-content/uploads/2017/01/Basketball.jpg",
                    title="Star Knight",
                    text="請選擇您要進行的操作",
                    actions=[
                        PostbackAction(label="請假", data="action=leave"),
                        PostbackAction(label="打球", data="action=play"),
                        PostbackAction(label="飲料盃PASS", data="action=no_drink"),
                        PostbackAction(label="查看名單", data="action=view_list")
                    ]
                )
            )

            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[template_message]
                )
            )

        elif "_reset" in user_message:
            leave_list_ref = db.collection("leave_list")
            leave_docs = leave_list_ref.stream()
            for doc in leave_docs:
                leave_list_ref.document(doc.id).delete()

            initialize_user_list()
            reply = "已重置名單。"
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply)]
                )
            )

        elif "_drink" in user_message:
            leave_list_ref = db.collection("leave_list").where("name", "==", user_name).get()
            if not leave_list_ref:
                drink_list_ref = db.collection("drink_list")
                drink_list_ref.document(user_name).set({"user_id": user_id, "name": user_name})
                reply = f"已將 {user_name} 加入飲料盃名單。"
            else:
                reply = f"{user_name} 在請假名單中，無法加入飲料盃。"

            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply)]
                )
            )

        elif "_請假" in user_message:
            if event.message.mention:
                mentionees = event.message.mention.mentionees
                mentioned_user_ids = [mention.user_id for mention in mentionees]
                
                for mentioned_user_id in mentioned_user_ids:
                    mentioned_profile = line_bot_api.get_profile(user_id=mentioned_user_id)
                    target_name = mentioned_profile.display_name

                    user_list_ref = db.collection("user_list").where("name", "==", target_name).get()
                    drink_list_ref = db.collection("drink_list").where("name", "==", target_name).get()

                    if user_list_ref or drink_list_ref:
                        leave_list_ref = db.collection("leave_list")
                        leave_list_ref.document(target_name).set({"user_id": user_id, "name": target_name})

                        for doc in user_list_ref:
                            db.collection("user_list").document(doc.id).delete()
                        for doc in drink_list_ref:
                            db.collection("drink_list").document(doc.id).delete()

                        reply = f"{user_name} 已為 {target_name} 請假。"
                    else:
                        reply = f"無法找到 {target_name}，請確認名稱是否正確。"
            else:
                reply = "請使用@提及要請假的對象。"

            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply)]
                )
            )

        elif "_天氣" in user_message:
            img_url = f'https://cwaopendata.s3.ap-northeast-1.amazonaws.com/Observation/O-A0058-001.png?{time.time_ns()}'
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[ImageMessage(original_content_url=img_url, preview_image_url=img_url)]
                )
            )

# 處理按鈕回傳事件
@handler.add(PostbackEvent)
def handle_postback(event):
    action_data = event.postback.data
    user_id = event.source.user_id

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        show_loading_animation(user_id, loading_seconds=5)

        profile = line_bot_api.get_profile(user_id=user_id)
        user_name = profile.display_name

        if action_data == "action=leave":
            leave_list_ref = db.collection("leave_list")
            leave_list_ref.document(user_name).set({"user_id": user_id, "name": user_name})

            user_docs = db.collection("user_list").where("name", "==", user_name).get()
            for doc in user_docs:
                db.collection("user_list").document(doc.id).delete()
            drink_docs = db.collection("drink_list").where("name", "==", user_name).get()
            for doc in drink_docs:
                db.collection("drink_list").document(doc.id).delete()

            leave_list = [doc.to_dict()["name"] for doc in leave_list_ref.stream()]
            on_leave = "\n".join(leave_list) if leave_list else "目前無人請假"
            reply = f"請假人員:\n{on_leave}"

        elif action_data == "action=play":
            leave_docs = db.collection("leave_list").where("name", "==", user_name).get()
            for doc in leave_docs:
                db.collection("leave_list").document(doc.id).delete()

            user_list_ref = db.collection("user_list")
            user_list_ref.document(user_name).set({"user_id": user_id, "name": user_name})
            drink_list_ref = db.collection("drink_list")
            drink_list_ref.document(user_name).set({"user_id": user_id, "name": user_name})

            user_list = [doc.to_dict()["name"] for doc in user_list_ref.stream()]

            reply = f"{user_name} 已加入打球名單， \n打球人員: {', '.join(user_list)}"

        elif action_data == 'action=view_list':
            user_list = [doc.to_dict()["name"] for doc in db.collection("user_list").stream()]
            drink_list = [doc.to_dict()["name"] for doc in db.collection("drink_list").stream()]
            leave_list = [doc.to_dict()["name"] for doc in db.collection("leave_list").stream()]

            reply = (f"🏀出戰名單🏀({len(user_list)}): \n{', '.join(user_list)}\n\n"
                     f"🥤飲料盃名單🥤({len(drink_list)}): \n{', '.join(drink_list)}\n\n"
                     f"💤休戰名單💤({len(leave_list)}): \n{', '.join(leave_list)}\n\n")

        elif action_data == "action=no_drink":
            db.collection("drink_list").document(user_name).delete()
            reply = f"{user_name} 已退出飲料盃。"

        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply)]
            )
        )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)))