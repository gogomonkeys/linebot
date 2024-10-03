from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage, GetProfileRequest
from linebot.v3.webhooks import MessageEvent, TextMessageContent
import json

app = Flask(__name__)

# LINE Bot 設定
configuration = Configuration(access_token='你的 LINE Bot Access Token')
handler = WebhookHandler('你的 LINE Bot Secret')

# 請假和所有人員名單
leave_list = set()  # 記錄請假人
user_list = set()   # 記錄所有傳送訊息的用戶

@app.route("/callback", methods=['POST'])
def callback():
    # 取得 X-Line-Signature 標頭
    signature = request.headers['X-Line-Signature']

    # 取得請求的主體內容
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # 驗證並處理 Webhook 請求
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_id = event.source.user_id  # 取得用戶ID

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        # 取得用戶名稱
        profile = line_bot_api.get_profile_with_http_info(GetProfileRequest(user_id=user_id))
        user_name = profile[0].display_name  # 用戶的顯示名稱

        user_list.add(user_name)            # 將用戶名稱加入所有人清單

        user_message = event.message.text  # 取得用戶訊息

        # 如果訊息中包含 "請假"，將用戶加入請假清單並回覆
        if "請假" in user_message:
            leave_list.add(user_name)
            reply = f"已將 {user_name} 列入請假名單。"
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply)]
                )
            )
    
        # 如果訊息中包含 "名單"，列出有請假與無請假的人員並回覆
        elif "名單" in user_message:
            on_leave = "\n".join(leave_list) if leave_list else "無人請假"
            no_leave = "\n".join(user_list - leave_list) if (user_list - leave_list) else "無無請假人員"
            reply = f"請假人員:\n{on_leave}\n\n無請假人員:\n{no_leave}"
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply)]
                )
            )

        # 其他訊息不回覆任何內容，避免干擾
        else:
            pass  # 不進行回覆

if __name__ == "__main__":
    app.run()