import os
import json
from typing import Union, List, AnyStr, Optional
from pytube import YouTube
import azure.cognitiveservices.speech as speechsdk
import noisereduce as nr
import soundfile as sf
import time
from pydub import AudioSegment
import subprocess

def download_youtube_videos(video_urls: Union[AnyStr, List[AnyStr]], output_path: Optional[AnyStr]=os.getcwd()):
  try:
    yt = YouTube(video_urls)
    video_stream = yt.streams.filter(file_extension="mp4", progressive=True).desc().first()

    if not video_stream:
      print("No suitable video stream found.")
      return

    video_stream.download(output_path)
    print(f'Downloaded {yt.title}.')

  except Exception as e:
    print(f'Error: {e}')


video_storage_dir = os.path.join(os.getcwd(), "downloaded_videos")
if not os.path.exists(video_storage_dir):
  os.makedirs("downloaded_videos")


def extract_audio_commandline_call(video_path: Union[AnyStr, List[AnyStr]], audio_output_path: Union[AnyStr, List[AnyStr]]):
  # print(video_path)
  os.system(f'ffmpeg -i "{video_path}" -vn -acodec pcm_s16le -ar 44100 -ac 2 "{audio_output_path}"')
  print("Audio conversion complete.")

def transcribe_audio(audio_file: AnyStr):
  speech_credentials = json.load(open(os.path.join(os.getcwd(), "azure_credentials.json")))
  subscription_key = speech_credentials["SpeechService"]["SUBSCRIPTION KEY"]
  region = speech_credentials["SpeechService"]["REGION"]

  # create a speech recognition recognizer
  speech_config = speechsdk.SpeechConfig(subscription_key, region)
  audio_input = speechsdk.AudioConfig(filename=audio_file)
  recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_input)
  transcript = str()

  # start a speech recognition session
  try:
    result = recognizer.recognize_once()
    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        transcript = result.text
    elif result.reason == speechsdk.ResultReason.NoMatch:
        print(f"No speech could be recognized for {audio_file}")
        transcript = ""
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            print(f"Speech Recognition Error: {cancellation_details.reason}")
            print(f"Error Details: {cancellation_details.reason}")
        elif cancellation_details.reason == speechsdk.CancellationReason.EndOfStream:
            print(f"End of audio stream reached for {audio_file}")
        transcript = ""
  except Exception as ex:
    print(f"Error occured {ex}.")

  return transcript

def reduce_background_noise_from_audio(audio_file: AnyStr):
  red_audio_dir = os.path.join(os.getcwd(), "Reduced Audios")
  os.makedirs(red_audio_dir, exist_ok=True)

  audio = AudioSegment.from_file(audio_file)
  segment_length_ms = 30000   # Adjust as needed
  segment_data, sample_rate = sf.read(audio_file)
  # Calculate the number of segments
  num_segments = len(audio) // segment_length_ms

  # Process and save each segment
  for i in range(num_segments):
    start_sample = i * segment_length_ms
    end_sample = (i + 1) * segment_length_ms
    segment_audio = audio[start_sample: end_sample]

    # Reduce noise in the segment
    segment_filename = f'reduced_audio_for_{os.path.basename(audio_file).split(".")[0]}_segment_{i}.wav'
    segment_audio.export(segment_filename, format='wav')

    reduced_segment = nr.reduce_noise(y=segment_data, sr=sample_rate, stationary=True)
    # Save the noise-reduced segment
    sf.write(os.path.join(red_audio_dir, segment_filename), reduced_segment, sample_rate)
    # Remove the temporary WAV file to free up memory
    os.remove(segment_filename)


def test_segment_audio_for_instance_demo():
  # Path to the input audio file
  input_audio_file = 'E:\\StemCityAIProject\\extracted_audios\\A well educated mind vs a well formed mind Dr Shashi Tharoor at TEDxGateway 2013.wav'

  # Directory to save the segmented audio files
  segment_dir = 'E:\\StemCityAIProject\\segmented_audio'

  # Create the segment directory if it doesn't exist
  os.makedirs(segment_dir, exist_ok=True)

  # Run FFmpeg to split the audio file into segments
  command = [
      'ffmpeg',
      '-i', input_audio_file,
      '-f', 'segment',
      '-segment_time', '300',  # Split into 5-minute segments
      '-c', 'copy',
      os.path.join(segment_dir, 'segment_%03d.wav')
  ]

  try:
      subprocess.run(command, check=True)
      print("Audio file segmented successfully.")
  except subprocess.CalledProcessError as e:
      print(f"Error segmenting audio: {e}")


def extract_audio_segments_from_directory(stored_audio_dir: Union[AnyStr, List[AnyStr]]):
  segment_dir = os.path.join(os.getcwd(), "segmented_audio")
  os.makedirs(segment_dir, exist_ok=True)

  for audio_test_file in os.listdir(stored_audio_dir):
    segment_audio_output_dir = os.path.join(segment_dir, os.path.basename(audio_test_file).split(".")[0])
    os.makedirs(segment_audio_output_dir, exist_ok=True)
    # Run FFmpeg to split the audio file into segments
    command = [
        'ffmpeg',
        '-i', os.path.join(stored_audio_dir, audio_test_file),
        '-f', 'segment',
        '-segment_time', '300',  # Split into 5-minute segments
        '-c', 'copy',
        os.path.join(segment_audio_output_dir, 'segment_%03d.wav')
    ]
    try:
      subprocess.run(command, check=True)
      print("Audio file segmented successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error segmenting audio: {e}")


def extract_transcripts_from_audio_segments(segment_folder: Union[AnyStr, List[AnyStr]]):
  for audio_folder in os.listdir(segment_folder):
    for audio_file in os.listdir(os.path.join(segment_folder, audio_folder)):
      try:
        transcript = transcribe_audio(os.path.join(segment_folder, audio_folder, audio_file))

        # Save transcript to a file
        with open(os.path.join('transcripts', f'{os.path.basename(audio_file).split(".")[0]}.txt'), 'w') as transcript_file:
          transcript_file.write(transcript)
      except Exception as ex:
        print(f"Error processing {audio_file}: {ex}")

# def test_extract_transcripts_using_deepspeech_model()

test_audio_files = list(audio_file for audio_file in os.listdir(os.path.join(os.getcwd(), "extracted_audios")))
audio_file = test_audio_files[0]
# extract_audio_segments_from_directory(os.path.join(os.getcwd(), "extracted_audios"))
# extract_transcripts_from_audio_segments(os.path.join(os.getcwd(), "segmented_audio"))
# reduce_background_noise_from_audio(os.path.join(os.getcwd(), "extracted_audios", audio_file))