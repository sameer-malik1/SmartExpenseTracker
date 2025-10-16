from google import genai
from google.genai import types
import wave


# myfile = client.files.upload(file=audio_file)
prompt = 'Generate a transcript of the speech. written in engligh wording not in hindi language'



# print(stt_response.text)

def speech_to_text(audio_file):
    myfile = client.files.upload(file=audio_file)
    stt_response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents=[prompt, myfile]
    )
    return stt_response.text

# gemini tts
# Set up the wave file to save the output:
def wave_file(filename, pcm, channels=1, rate=24000, sample_width=2):
   with wave.open(filename, "wb") as wf:
      wf.setnchannels(channels)
      wf.setsampwidth(sample_width)
      wf.setframerate(rate)
      wf.writeframes(pcm)

# response = client.models.generate_content(
#    model="gemini-2.5-flash-preview-tts",
#    contents=stt_response.text,
#    config=types.GenerateContentConfig(
#       response_modalities=["AUDIO"],
#       speech_config=types.SpeechConfig(
#          voice_config=types.VoiceConfig(
#             prebuilt_voice_config=types.PrebuiltVoiceConfig(
#                voice_name='Kore',
#             )
#          )
#       ),
#    )
# )

# data = response.candidates[0].content.parts[0].inline_data.data

# file_name='Kore.wav'
# wave_file(file_name, data) # Saves the file to current directory

def text_to_speech(text, output_path="outputs/tts_output.wav"):
    response = client.models.generate_content(
       model="gemini-2.5-flash-preview-tts",
       contents=text,
       config=types.GenerateContentConfig(
          response_modalities=["AUDIO"],
          speech_config=types.SpeechConfig(
             voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                   voice_name='Kore',
                )
             )
          ),
       )
    )

    data = response.candidates[0].content.parts[0].inline_data.data

    wave_file(output_path, data) # Saves the file to current directory
    return output_path

def llm(prompt):
    response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents=[prompt]
    )
    return response.text