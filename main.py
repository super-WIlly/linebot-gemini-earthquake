import logging
import os
import re
import sys
if os.getenv('API_ENV') != 'production':
    from dotenv import load_dotenv

    load_dotenv()


from fastapi import FastAPI, HTTPException, Request
from datetime import datetime
from linebot.v3.webhook import WebhookParser
from linebot.v3.messaging import (
    AsyncApiClient,
    AsyncMessagingApi,
    Configuration,
    ReplyMessageRequest,
    TextMessage)
from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
)

import uvicorn
import requests

logging.basicConfig(level=os.getenv('LOG', 'WARNING'))
logger = logging.getLogger(__file__)

app = FastAPI()

channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)
if channel_secret is None:
    print('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)

configuration = Configuration(
    access_token=channel_access_token
)

async_api_client = AsyncApiClient(configuration)
line_bot_api = AsyncMessagingApi(async_api_client)
parser = WebhookParser(channel_secret)


import google.generativeai as genai
from firebase import firebase
from utils import check_image_quake, check_location_in_message, get_current_weather, get_weather_data, simplify_data


firebase_url = os.getenv('FIREBASE_URL')
gemini_key = os.getenv('GEMINI_API_KEY')


# Initialize the Gemini Pro API
genai.configure(api_key=gemini_key)


@app.get("/health")
async def health():
    return 'ok'


@app.post("/webhooks/line")
async def handle_callback(request: Request):
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = await request.body()
    body = body.decode()

    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    for event in events:
        logging.info(event)
        if not isinstance(event, MessageEvent):
            continue
        if not isinstance(event.message, TextMessageContent):
            continue
        text = event.message.text
        user_id = event.source.user_id

        msg_type = event.message.type
        fdb = firebase.FirebaseApplication(firebase_url, None)
        if event.source.type == 'group':
            user_chat_path = f'chat/{event.source.group_id}'
        else:
            user_chat_path = f'chat/{user_id}'
            chat_state_path = f'state/{user_id}'
        chatgpt = fdb.get(user_chat_path, None)

        if msg_type == 'text':

            if chatgpt is None:
                messages = []
            else:
                messages = chatgpt

            bot_condition = {
                "清空": 'A',
                "提示": 'B',
                "地震": 'C',
                "氣候": 'D',
                "其他": 'E'
            }

            model = genai.GenerativeModel('gemini-1.5-pro')
            response = model.generate_content(
                f'請判斷 {text} 裡面的文字屬於 {bot_condition} 裡面的哪一項？符合條件請回傳對應的英文文字就好，不要有其他的文字與字元。')
            print('='*10)
            text_condition = re.sub(r'[^A-Za-z]', '', response.text)
            print(text_condition)
            print('='*10)
            if text_condition == 'A':
                fdb.delete(user_chat_path, None)
                reply_msg = '已清空對話紀錄'
            elif text_condition == 'B':
                model = genai.GenerativeModel('gemini-pro')
                response = model.generate_content(
                    f'###Context
                    你是一個較柔性且生活化的個性的人，會引導使用者去更了解對話流程進展，作為老鳥提供使用者可以更快入門的方式。相對於提供使用者一個確定的結果，你會提供事實查核的流程，來達到防詐跟雙方保障的目的。如果對方立意良善，也不會阻礙雙方合作。

                    ###Objective
                    有三個主要功能：
                    1. 在接收到下方關於使用者的訊息後，會先用你的LLM來做一個基礎的事實核查，告訴使用者這是否符合常理，如果不符合也請提供原因，提供法規支持，以及可以參考的網址。
                    2. 在第一步之後，避免使用者的盲點，讓使用者不會因為”不知道”而發生後續問題，提供可以進一步讓使用者問的問題，讓使用者能與對方的談話具有安全性。
                    3. 使用者告訴你想要問對方甚麼，可以先提供目前公開資源的質量化參考資料，給使用者一個參考的依據，並且幫使用者包裝問題，使用者可能會輸入相對模糊的資訊，你會協助問題變得精確。
                    
                    ###Style
                    輕鬆且生活化的風格，以便使用者快速理解和應用。
                    
                    ###Tone
                    友善、支持性、鼓勵合作和理解。
                    
                    ###Audience
                    任何尋求幫助避免詐騙和確保交流安全的使用者。
                    
                    ###Task Definition
                    確保在回應使用者時，始終遵循事實核查的流程，避免引導使用者做出可能不安全或不符合法規的行為。
                    
                    ###Output Format
                    以文本形式回應，包括對使用者提出的問題進行解釋和建議的詳細說明。提供具體的法律支持和公開資源來源，確保信息的可靠性。
                    
                    ###Guardrails
                    避免提供不實或模糊的信息。
                    不要促��使用者採取可能不符合法規或安全的行動。
                    確保所有建議和信息基於可靠的公開資源和法律支持。
                    
                    ###Example
                    User: 我正在找房子租，但不確定要問房東些什麼才好，可以幫我看看嗎？
                    Assistant: 當然可以！你目前租房的進度是什麼？例如，你已經看過房子了嗎？還是正在選擇中？
                    User: 我已經看了幾間房子，但是不太了解該問什麼。
                    Assistant: 好的，第一步是確保房東提供的資訊是真實的。你可以問房東關於房租的合理性，例如該地區的市場價格是多少。我可以幫你將問題包裝得更精確，你是否需要幫助？ \n{messages}')
                reply_msg = response.text
            elif text_condition == 'C':
                print('='*10)
                print("地震相關訊息")
                print('='*10)
                model = genai.GenerativeModel('gemini-pro-vision')
                OPEN_API_KEY = os.getenv('OPEN_API_KEY')
                earth_res = requests.get(f'https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/E-A0015-003?Authorization={OPEN_API_KEY}&downloadType=WEB&format=JSON')
                url = earth_res.json()["cwaopendata"]["Dataset"]["Resource"]["ProductURL"]
                reply_msg = check_image_quake(url)+f'\n\n{url}'
            elif text_condition == 'D':
                location_text = '台北市'
                location = check_location_in_message(location_text)
                print('Location is: ' + location)
                weather_data = get_weather_data(location)
                simplified_data = simplify_data(weather_data)
                current_weather = get_current_weather(simplified_data)

                print('The Data is: ' + str(current_weather))

                now = datetime.now()
                formatted_time = now.strftime("%Y/%m/%d %H:%M:%S")

                if current_weather is not None:
                    total_info = f'位置: {location}\n氣候: {current_weather["Wx"]}\n降雨機率: {current_weather["PoP"]}\n體感: {current_weather["CI"]}\n現在時間: {formatted_time}'

                response = model.generate_content(
                    f'你現在身處在台灣，相關資訊 {total_info}，我朋友說了「{text}」，請問是否有誇張、假裝的嫌疑？ 回答是或否。')
                reply_msg = response.text
            # model = genai.GenerativeModel('gemini-pro')
            messages.append({'role': 'user', 'parts': [text]})
            response = model.generate_content(messages)
            messages.append({'role': 'model', 'parts': [text]})
            # 更新firebase中的對話紀錄
            fdb.put_async(user_chat_path, None, messages)
            reply_msg = response.text

            await line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply_msg)]
                ))

    return 'OK'

if __name__ == "__main__":
    port = int(os.environ.get('PORT', default=8080))
    debug = True if os.environ.get(
        'API_ENV', default='develop') == 'develop' else False
    logging.info('Application will start...')
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=debug)
