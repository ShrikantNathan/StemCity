import azure.cognitiveservices.speech as speechsdk
import json, os

credentials = json.load(open(os.path.join(os.getcwd(), "azure_credentials.json")))
speech_config = speechsdk.SpeechConfig(subscription=credentials["SpeechService"]["SUBSCRIPTION KEY"], region=credentials["SpeechService"]["REGION"])
speech_recognizer = speechsdk.SpeechRecognizer(speech_config)

video_path = os.path.join(os.getcwd(), "downloaded_videos")
test_videos = list(video for video in os.listdir(video_path))
video_file = os.path.join(video_path, test_videos[1])

def extract_video_transcripts():
    audio_config = speechsdk.audio.AudioConfig(filename=video_file)
    result = speech_recognizer.recognize_once()

    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        with open(os.path.join(os.getcwd(), "transcripts", f"transcript_for_{os.path.basename(os.path.join(video_path, test_videos[0])).split('.')[0]}.txt"), mode='w') as transcript_file:
            transcript_file.write(result.text)
        print(f'Transcript saved to {transcript_file}')
    elif result.reason == speechsdk.ResultReason.NoMatch:
        print("No speech could be recognized.")
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancelled_details = result.cancellation_details
        print(f'Speech recognition cancelled: {cancelled_details}.')

import time
def extract_transcripts_with_retry(max_retries=3):
    for attempt in range(max_retries):
        try:
            extract_video_transcripts()
            break  # Success, exit the loop
        except Exception as e:
            print(f"Attempt {attempt + 1} failed with error: {str(e)}")
            if attempt < max_retries - 1:
                print("Retrying in 5 seconds...")
                time.sleep(5)
            else:
                print("Max retries reached. Exiting.")
                break

# async def generate_transcripts():
#     with open(os.path.join(video_path, test_videos[0]), mode='rb') as video_file:
#         # audio_config = speechsdk.AudioConfig.from_data(video_file.read())
#         audio_input_stream = speechsdk.audio.AudioInputStream(video_file.read())
#         # recognize the speech in the audio track
#         recognition_result = await speech_recognizer.recognize_once_async(audio_input_stream)

#         transcript = recognition_result.text

#         with open(os.path.join(os.getcwd(), "transcripts", f"transcript_for_{os.path.basename(os.path.join(video_path, test_videos[0])).split('.')[0]}.txt")) as transcript_file:
#             transcript_file.write(transcript)

extract_transcripts_with_retry(max_retries=6)