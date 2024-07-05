# import os
# import azure.cognitiveservices.speech as speechsdk
# from playsound import playsound
from gtts import gTTS
from io import BytesIO
import pygame

def playtext(text):
    # # speech_key, service_region = "ece226900a9c434a8a4f61a436c68977", "eastus"
    # speech_config = speechsdk.SpeechConfig(subscription=os.environ.get('SPEECH_KEY'), region=os.environ.get('SPEECH_REGION'))
    # audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
    # # The language of the voice that speaks.
    # speech_config.speech_synthesis_voice_name=f'en-US-{voice}Neural'
    #
    # speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
    #
    # # Get text from the console and synthesize to the default speaker.
    #
    # speech_synthesis_result = speech_synthesizer.speak_text_async(text).get()
    #
    # if speech_synthesis_result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
    #     print("Speech synthesized for text [{}]".format(text))
    # elif speech_synthesis_result.reason == speechsdk.ResultReason.Canceled:
    #     cancellation_details = speech_synthesis_result.cancellation_details
    #     print("Speech synthesis canceled: {}".format(cancellation_details.reason))
    #     if cancellation_details.reason == speechsdk.CancellationReason.Error:
    #         if cancellation_details.error_details:
    #             print("Error details: {}".format(cancellation_details.error_details))
    #             print("Did you set the speech resource key and region values?")


    fp = BytesIO()
    tts = gTTS(text=text, lang='ru', slow=False)
    tts.write_to_fp(fp)

    fp.seek(0)

    pygame.init()
    pygame.mixer.init()
    pygame.mixer.music.load(fp)
    pygame.mixer.music.play()


# from openai import OpenAI
#
# client = OpenAI()
#
# response = client.audio.speech.create(
#     model="tts-1",
#     voice="alloy",
#     input="Сәлем! Менің атым Қожа. Мен Қарағанды қаласында туылдым. Сен өзін қайдан боласын?",
# )
#
# response.stream_to_file("output.mp3")