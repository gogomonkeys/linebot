from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent
import json

app = Flask(__name__)

# LINE Bot 設定
configuration = Configuration(access_token='Tb4h2RQnphtyXu3ogWSF4oUatDDaJPZRAKFUMyZjuTi8sa3HkoYdtF48038gI03wVMyyMb2mONqZMfez9Ik14MeP2A+vqdRWU4sFMkwxqnAOad1rIcOEZ7Wpv4sZTDF45SNsFWPvyEF5KTKoYWPoPAdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('6413fb6ea05e38e1e6df22a9dd2bd0ee')

# 請假和所有人員名單
leave_list = set()  # 記錄請假人
user_list = set()   # 記錄所有傳送訊息的用戶


def initialize_user_list(group_id):
    """初始化，將群組中的所有用戶加入 user_list"""
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        member_ids = ["USER_ID_1", "USER_ID_2", "USER_ID_3"]  # 請用實際用戶ID替換
        
        # 取得每個成員的名稱並加入 user_list
        for member_id in member_ids:
            try:
                profile = line_bot_api.get_group_member_profile(group_id=group_id, user_id=member_id)
                user_list.add(profile.display_name)
            except Exception as e:
                print(f"無法取得成員 {member_id} 的資料: {e}")


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

        # 如果是群組訊息，初始化群組成員名單
        if event.source.type == 'group':
            group_id = event.source.group_id
            if not user_list:  # 確保只初始化一次
                initialize_user_list(group_id)

        # 取得用戶名稱
        profile = line_bot_api.get_profile(user_id=user_id)
        user_name = profile.display_name    # 用戶的顯示名稱

        user_list.add(user_name)            # 將用戶名稱加入所有人清單

        user_message = event.message.text   # 取得用戶訊息

        # 如果訊息中包含 "請假"，將用戶加入請假清單並回覆
        if "_請假" in user_message:
            leave_list.add(user_name)
            reply = f"已將 {user_name} 列入請假名單。"
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply)]
                )
            )

        # 如果訊息中包含 "打球"，將用戶重新加入打球清單並回覆
        elif "_打球" in user_message:
            leave_list.discard(user_name)
            reply = f"已將 {user_name} 重新加入打球名單。"
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply)]
                )
            )

    
        # 如果訊息中包含 "名單"，列出有請假與無請假的人員並回覆
        elif "_名單" in user_message:
            on_leave = "\n".join(leave_list) if leave_list else "目前無人請假"
            no_leave = "\n".join(user_list - leave_list) if (user_list - leave_list) else "目前沒人出席"
            reply = f"請假人員:\n{on_leave}\n\n打球人員:\n{no_leave}"
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply)]
                )
            )

        # 如果訊息中包含 "重置"，清空請假名單並回覆
        elif "_重置" in user_message:
            leave_list.clear()
            initialize_user_list(group_id)
            reply = "已重置名單。"
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