from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage, TemplateMessage, ButtonsTemplate, PostbackAction, ShowLoadingAnimationRequest
from linebot.v3.webhooks import MessageEvent, TextMessageContent, PostbackEvent

app = Flask(__name__)

# LINE Bot 設定
configuration = Configuration(access_token='Tb4h2RQnphtyXu3ogWSF4oUatDDaJPZRAKFUMyZjuTi8sa3HkoYdtF48038gI03wVMyyMb2mONqZMfez9Ik14MeP2A+vqdRWU4sFMkwxqnAOad1rIcOEZ7Wpv4sZTDF45SNsFWPvyEF5KTKoYWPoPAdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('6413fb6ea05e38e1e6df22a9dd2bd0ee')

# 請假和所有人員名單
leave_list = set()  # 記錄請假人
user_list = set()   # 記錄參加打球的人員
drink_list = set()  # 紀錄參加飲料盃人員

def initialize_user_list():
    """初始化，將群組中的所有用戶加入 user_list"""
    members_name = ["陳永慶", "Chris煒智🎸", "Kuan Shu Fan", "Wei", "傑仁", "吳建鋒","呂呂","柏燐","育豪(Fortitude)","莊阿嘎","金庸","鐘小豬","阿勛（運動按摩-史考特）","陳阿祥"]
        
    for member_name in members_name:
        try:
            user_list.add(member_name)
            drink_list.add(member_name)
        except Exception as e:
            print(f"無法取得成員 {member_name} 的資料: {e}")

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

# 處理文字訊息事件
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_id = event.source.user_id
    user_message = event.message.text  # 取得用戶訊息
    
    
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        print(line_bot_api)
        profile = line_bot_api.get_profile(user_id=user_id)
        user_name = profile.display_name
        print(f'{user_name}={user_id}')

        # Step 1: 顯示等待動畫
        line_bot_api.show_loading_animation(
            ShowLoadingAnimationRequest(
                chatId=user_id,  # 指定用戶 ID
                loadingSeconds=5  # 顯示動畫 5 秒
            )
        )
        
        if "_STAR" in user_message:  # 當訊息包含 "_STAR" 才顯示樣板訊息
            # 取得用戶名稱
            profile = line_bot_api.get_profile(user_id=user_id)
            print(profile)
            user_name = profile.display_name

            # 發送樣板訊息給用戶，包含圖片
            template_message = TemplateMessage(
                alt_text="這是樣板訊息",
                template=ButtonsTemplate(
                    thumbnail_image_url="https://www.deafsports.org.tw/web/wp-content/uploads/2017/01/Basketball.jpg",  # 加入圖片
                    title="Star Knight ",
                    text="請選擇您要進行的操作",
                    actions=[
                        PostbackAction(label="請假", data="action=leave"),
                        PostbackAction(label="打球", data="action=play"),
                        PostbackAction(label="飲料盃PASS", data="action=no_drink"),
                        #PostbackAction(label="加入飲料盃", data="action=join_drink"),  # 新增加入飲料盃的選項
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

        elif "_reset" in user_message:  # 當訊息包含 "_reset" 才執行
            leave_list.clear()
            initialize_user_list()
            reply = "已重置名單。"

            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply)]
                )
            )

        elif "_drink" in user_message:  # 當訊息包含 "_drink" 才執行
            # 取得用戶名稱
            profile = line_bot_api.get_profile(user_id=user_id)
            user_name = profile.display_name

            if user_name not in leave_list:  # 檢查是否在請假名單中
                drink_list.add(user_name)
                reply = f"已將 {user_name} 加入飲料盃名單。"
            else:
                reply = f"{user_name} 在請假名單中，無法加入飲料盃。"

            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply)]
                )
            )

        elif "_請假" in user_message:  # 當訊息包含 "_請假" 才執行
            profile = line_bot_api.get_profile(user_id=user_id)
            requester_name = profile.display_name

            if event.message.mention:
                mentionees = event.message.mention.mentionees
                mentioned_user_ids = [mention.user_id for mention in mentionees]
                print(event.message.mention)


                for mentioned_user_id in mentioned_user_ids:
                    mentioned_profile = line_bot_api.get_profile(user_id=mentioned_user_id)
                    target_name = mentioned_profile.display_name
            
                    if target_name in user_list or target_name in drink_list:
                        leave_list.add(target_name)
                        user_list.discard(target_name)
                        drink_list.discard(target_name)
                        reply = f"{requester_name} 已為 {target_name} 請假，將其加入請假名單並從打球和飲料盃名單中移除。"
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

# 處理按鈕回傳事件
@handler.add(PostbackEvent)
def handle_postback(event):
    action_data = event.postback.data
    print(event)
    print(event.postback)
    print(action_data)
    user_id = event.source.user_id
    print(event.source)

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        # Step 1: 顯示等待動畫
        line_bot_api.show_loading_animation(
            ShowLoadingAnimationRequest(
                chatId=user_id,  # 指定用戶 ID
                loadingSeconds=5  # 顯示動畫 5 秒
            )
        )
        
        # Step 2: 取得用戶名稱並處理回傳動作
        profile = line_bot_api.get_profile(user_id=user_id)
        user_name = profile.display_name

        if action_data == "action=leave":
            leave_list.add(user_name)
            user_list.discard(user_name)
            drink_list.discard(user_name)
            reply = f"已將 {user_name} 列入請假名單。"
            on_leave = "\n".join(leave_list) if leave_list else "目前無人請假"
            reply = f"請假人員:\n{on_leave}"
        elif action_data == "action=play":
            leave_list.discard(user_name)
            user_list.add(user_name)
            drink_list.add(user_name)
            reply = f"已將 {user_name} 加入打球名單。"
            no_leave = "\n".join(user_list - leave_list) if (user_list - leave_list) else "目前沒人出席"
            reply = f"打球人員:\n{no_leave}"
        elif action_data == "action=no_drink":
            drink_list.discard(user_name)
            reply = f"已將 {user_name} 從飲料盃名單中移除。" 
            on_drink = "\n".join(drink_list) if drink_list else "目前無人參加飲料盃"
            reply = f"飲料盃:\n{on_drink}"
        elif action_data == "action=view_list":
            on_leave = "\n".join(leave_list) if leave_list else "目前無人請假"
            no_leave = "\n".join(user_list - leave_list) if (user_list - leave_list) else "目前沒人出席"
            on_drink = "\n".join(drink_list) if drink_list else "目前無人參加飲料盃"
            reply = f"打球人員:\n{no_leave}\n\n飲料盃:\n{on_drink}\n\n請假人員:\n{on_leave}"

        # Step 3: 回覆用戶操作結果
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply)]
            )
        )

if __name__ == "__main__":
    app.run()