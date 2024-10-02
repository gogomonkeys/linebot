from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage, ImageMessage, LocationMessage, StickerMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent, ImageMessageContent, LocationMessageContent, StickerMessageContent
import json

app = Flask(__name__)

configuration = Configuration(access_token='Tb4h2RQnphtyXu3ogWSF4oUatDDaJPZRAKFUMyZjuTi8sa3HkoYdtF48038gI03wVMyyMb2mONqZMfez9Ik14MeP2A+vqdRWU4sFMkwxqnAOad1rIcOEZ7Wpv4sZTDF45SNsFWPvyEF5KTKoYWPoPAdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('6413fb6ea05e38e1e6df22a9dd2bd0ee')


@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    json_data = json.loads(body)
    print(json_data)               # 印出 json_data

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'


@handler.add(MessageEvent)
def handle_message(event):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        # 根據接收到的訊息類型進行對應回覆
        if isinstance(event.message, TextMessageContent):
            reply_message = TextMessage(text=event.message.text)
        elif isinstance(event.message, ImageMessageContent):
            reply_message = ImageMessage(
                original_content_url=event.message.content_provider.original_content_url,
                preview_image_url=event.message.content_provider.preview_image_url
            )
        elif isinstance(event.message, LocationMessageContent):
            reply_message = LocationMessage(
                title=event.message.title,
                address=event.message.address,
                latitude=event.message.latitude,
                longitude=event.message.longitude
            )
        elif isinstance(event.message, StickerMessageContent):
            reply_message = StickerMessage(
                package_id=event.message.package_id,
                sticker_id=event.message.sticker_id
            )
        else:
            reply_message = TextMessage(text="不支援的訊息類型")

        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(reply_token=event.reply_token, messages=[reply_message])
        )



if __name__ == "__main__":
    app.run()