import base64
import vertexai
from vertexai.generative_models import GenerativeModel, Part, FinishReason
import vertexai.preview.generative_models as generative_models

def generate():
  vertexai.init(project="anti-fraud-chatbot", location="us-central1")
  model = GenerativeModel(
    "gemini-1.5-pro-001",
    system_instruction=[textsi_1]
  )
  responses = model.generate_content(
      [text1],
      generation_config=generation_config,
      safety_settings=safety_settings,
      stream=True,
  )

  for response in responses:
    print(response.text, end="")

text1 = """那應該會愛惜房屋吧我就是想找一個愛惜的租客所以租金方面都算得很優惠啦~
15:20
會喔愛惜房屋是必要的!!房租真的有感動到!
15:23
了解是打算長租還是短租呢
15:26
已讀
15:26
目前想法是半年
好的看屋要禮拜三,你在第五組看屋,請問你方便嗎
15:31
已讀 請問您什麼時候幾點方便
15:34
具體看屋時間我會通知你,因為目前第三位的租客打算預付訂金優先看屋,如果前面的租客看屋滿意簽約了房屋後面的租客就沒有機會看屋了"""

generation_config = {
    "max_output_tokens": 8192,
    "temperature": 1,
    "top_p": 0.95,
}

safety_settings = {
    generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
}

generate()

