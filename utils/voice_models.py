from google import genai
from google.genai import types
import wave
from dotenv import load_dotenv
import os

load_dotenv()  # Load environment variables from .env file

gemini_api_key = os.getenv("gemini_api_key")

client = genai.Client(api_key=gemini_api_key)
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

def speech_to_text2(uploaded_file):
    """
    Transcribe a Streamlit UploadedFile (from st.audio_input or st.file_uploader)
    using Gemini.
    """
    try:
        # Save uploaded file temporarily
        temp_path = f"temp_{uploaded_file.name}"
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.read())

        # Upload to Gemini Files
        myfile = client.files.upload(temp_path)

        # Perform transcription
        stt_response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=["Transcribe this audio into text:", myfile]
        )

        # Clean up temp file
        os.remove(temp_path)

        return getattr(stt_response, "text", "(No transcription result)")

    except Exception as e:
        print(f"Speech-to-text failed: {e}")
        return ""



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