

import librosa
import scipy.signal as scipy_signal
from typing import List, Union, AnyStr, Optional
import os
import numpy as np
import time
import shutil
from glob import glob
import noisereduce
import soundfile as sf
import pydub
from moviepy.editor import VideoFileClip, AudioFileClip
import time
import whisper
from pytube import Playlist, YouTube
import soundfile
import math


class MultimediaFileProcessorTool:
    def __init__(self) -> None:
        self.audio_dir = os.path.join(os.getcwd(), "Main Audio Files")
        self.processed_audio_dir = os.path.join(os.getcwd(), "Processed Audio Files")
        os.makedirs(self.audio_dir, exist_ok=True)
        os.makedirs(self.processed_audio_dir, exist_ok=True)
        os.makedirs(os.path.join(os.getcwd(), "downloaded_videos"), exist_ok=True)  # create a temporary downloaded video dir for storing sample videos
        time.sleep(1)
        self.audio_file: str = None

    def download_videos_from_youtube(self):
        """This is just a boilerplate for testing some videos, this will be soon replaced with client's videos."""
        playlist_url = "https://www.youtube.com/watch?v=5t16bsGwdRY&list=PL6ayoRPgAupGdFRe9n882-iuVxNEEVVNU"
        playlist = Playlist(playlist_url)
        os.chdir(os.path.join(os.getcwd(), "downloaded_videos"))
        test_video_urls = ["https://www.youtube.com/watch?v=QAqIdljrUno&t=338s"]

        for video_url in test_video_urls:
            yt = YouTube(video_url)
            try:
                stream = yt.streams.get_highest_resolution()
                stream.download()
                print(f'Downloaded {yt.title}')
            except Exception as e:
                print(f'Error downloading {yt.title}: {e}')
        print("Download completed.")

        # for video in playlist.videos:
        #     try:
        #         video.streams.get_highest_resolution().download()
        #         print(f'Downloaded {video.title}')

        #     except Exception as e:
        #         print(f'Error downloading {video.title}: {e}')

        # print("Download completed playlist.")
        os.chdir('..')

    def process_large_videos(self, input_video_path: os.PathLike):
        video = VideoFileClip(input_video_path)
        total_duration, chunk_duration = video.duration, 600
        chunk_count = math.ceil(total_duration / chunk_duration)
        output_audio_folder = os.path.join(os.getcwd(), "Large Videos", os.path.basename(input_video_path).split('.')[0], "audio_chunks")

        if not os.path.exists(output_audio_folder):
            os.makedirs(output_audio_folder, exist_ok=True)

        # Set the desired audio parameters
        audio_params = {
            "codec": ["pcm_s16le", "libmp3lame"],
            "fps": 16000,  # Set the desired sampling rate: 16000 Hz
            # "fps": 8000,  # Alternatively, set the sampling rate to 8000 Hz
            "nchannels": 1,  # Mono audio
            "bitrate": "16k"  # Set the desired bitrate
        }

        for i in range(chunk_count):
            start_time = i * chunk_duration
            end_time = min((i + 1) * chunk_duration, total_duration)
            output_audio_path = os.path.join(output_audio_folder, f'audio_chunk_{i + 1}.wav')
            chunk_video = video.subclip(start_time, end_time)
            chunk_audio = chunk_video.audio
            chunk_audio.write_audiofile(output_audio_path, codec=audio_params["codec"][0], fps=audio_params["fps"], nbytes=2, bitrate=audio_params["bitrate"])

        video.close()

    def process_downloaded_videos(self, downloaded_video_dir: os.PathLike):
        if not os.listdir(downloaded_video_dir):    # to start off with, test the pipeline with sample videos from the youtube.
            print("no videos present, so downloading from youtube.")
            self.download_videos_from_youtube()

        for video_file in os.listdir(downloaded_video_dir):
            if video_file.endswith('.mp4'):
                video_file_path = os.path.join(downloaded_video_dir, video_file)
                audio_file = os.path.join(self.audio_dir, f'Audio for {os.path.basename(video_file_path).split(".")[0]}.wav')
                video_clip = VideoFileClip(video_file_path)
                if video_clip.audio.duration >= 1800:   # only if the video is larger and of duration exceeding 30 mins
                    print('Large video detected..')
                    self.process_large_videos(video_file_path)
                    time.sleep(1)
                    large_video_dir = os.path.join(os.getcwd(), "Large Videos") # this video directory gets created automatically
                    extract_transcripts_from_large_audio_files(large_video_dir)
                    continue
                else:
                    # For small videos, this will extract the audio version and save it in folder.
                    # Set the desired audio parameters
                    audio_params = {
                        "codec": ["pcm_s16le", "libmp3lame"],
                        "fps": 16000,  # Set the desired sampling rate: 16000 Hz
                        # "fps": 8000,  # Alternatively, set the sampling rate to 8000 Hz
                        "nchannels": 1,  # Mono audio
                        "bitrate": "16k"  # Set the desired bitrate
                    }
                    video_clip.audio.write_audiofile(audio_file, codec=audio_params["codec"][0], fps=audio_params["fps"], nbytes=2, bitrate=audio_params["bitrate"])
                    print(f'Audio file generated for {os.path.basename(audio_file)} :: Successful.')

    def preprocess_audio_and_denoise_background(self):
        for audio_file in os.listdir(self.audio_dir):
            if audio_file.endswith('.wav'):
                audio_file_path = os.path.join(self.audio_dir, audio_file)

                y, sr = librosa.load(os.path.join(self.audio_dir, audio_file_path))
                reduced_noise = noisereduce.reduce_noise(y, sr)
                denoised_audio = scipy_signal.wiener(reduced_noise)
                sf.write(os.path.join(self.processed_audio_dir, f"Cleaned_Audio of - {os.path.basename(audio_file_path).split('.')[0]}.wav"), denoised_audio, sr)
        # print(f"Filtered audio saved to {os.path.basename(self.output_audio_file)}")

    def increase_noise_from_the_processed_audio(self):
        if len(os.listdir(self.processed_audio_dir)) == 1:
            cleaned_audio_path = os.path.join(self.processed_audio_dir, "Cleaned_Audio.wav")
            cleaned_audio = pydub.AudioSegment.from_wav(cleaned_audio_path)
            # Additional processing block
            volume_gain_DB = 20
            louder_audio = cleaned_audio + volume_gain_DB
            incr_vol_dir = os.path.join(self.processed_audio_dir, "Louder Version")
            os.makedirs(incr_vol_dir, exist_ok=True)

            time.sleep(1)
            louder_audio.export(os.path.join(incr_vol_dir, "louder_audio.wav"), format="wav")

        elif len(os.listdir(self.processed_audio_dir)) > 1:
            for cleaned_audio_file in os.listdir(self.processed_audio_dir):
                cleaned_audio_file_path = os.path.join(self.processed_audio_dir, cleaned_audio_file)
                if os.path.isfile(cleaned_audio_file_path) and cleaned_audio_file_path.endswith('.wav'):
                    cleaned_audio = pydub.AudioSegment.from_wav(cleaned_audio_file_path)

                    # # Additional processing block
                    volume_gain_DB = 10
                    louder_audio = cleaned_audio + volume_gain_DB
                    incr_vol_dir = os.path.join(self.processed_audio_dir, "Louder Version")
                    os.makedirs(incr_vol_dir, exist_ok=True)
                    time.sleep(1)
                    louder_audio.export(os.path.join(incr_vol_dir, f"louder_audio_for_{os.path.basename(cleaned_audio_file_path).split('.')[0]}.wav"), format="wav")

        else:
            print("no files in the directory")
            # return False

    def extract_audio_transcripts_using_openai(self):
        loud_version_audio_dir = os.path.join(self.processed_audio_dir, "Louder Version")
        output_folder = os.path.join(os.getcwd(), "Transcripts")
        os.makedirs(output_folder, exist_ok=True)
        model = whisper.load_model("medium")

        if len(os.listdir(loud_version_audio_dir)) == 1:
            audio_file_path = os.path.join(loud_version_audio_dir, list(loud_audio_file for loud_audio_file in os.listdir(loud_version_audio_dir)[-1]))
            result = model.transcribe(audio_file_path)

            with open(os.path.join(output_folder, f'{os.path.basename(audio_file_path).split(".")[0]}.txt'), mode='w') as f:
                f.write(result["text"])
                print("Transcript written successfully.")

        elif len(os.listdir(loud_version_audio_dir)) > 1:
            for large_audio_file in os.listdir(loud_version_audio_dir):
                if large_audio_file.endswith('.wav'):
                    large_audio_file_path = os.path.join(loud_version_audio_dir, large_audio_file)
                    result2 = model.transcribe(large_audio_file_path)
                    transcript_output_path = os.path.join(output_folder, f'{os.path.basename(large_audio_file_path).split(".")[0]}.txt')

                    with open(transcript_output_path, mode='w') as f:
                        print(f"Transcript process started for :: {os.path.basename(transcript_output_path)}.")
                        f.write(result2["text"])
                        print(f"Transcript written successfully under file named :: {os.path.basename(transcript_output_path)}.")

        else:
            print("No files in this folder.")


def extract_transcript_results_for_larger_audio_directory_chunks(magazine_folder_path: Union[os.PathLike, str], nested_folder_audio_chunk_path: os.PathLike):
    output_folder = os.path.join(os.getcwd(), "Transcripts")
    os.makedirs(output_folder, exist_ok=True)
    model = whisper.load_model("medium")

    result = model.transcribe(nested_folder_audio_chunk_path)
    chunked_transcript_output_dir = os.path.join(output_folder, os.path.basename(magazine_folder_path))
    os.makedirs(chunked_transcript_output_dir, exist_ok=True)

    with open(os.path.join(chunked_transcript_output_dir, f'{os.path.basename(nested_folder_audio_chunk_path).split(".")[0]}.txt'), mode='w') as f:
        f.write(result["text"])
        print(f"Transcript written successfully for {os.path.basename(nested_folder_audio_chunk_path)}.")

def extract_transcripts_from_large_audio_files(large_audio_file_path: os.PathLike):
    if len(os.listdir(large_audio_file_path)) == 1:
        for magazine_folders in os.listdir(large_audio_file_path):
            print(f'Processing :: {os.path.basename(os.path.join(large_audio_file_path, magazine_folders))}')
            for audio_chunk_folder in os.listdir(os.path.join(large_audio_file_path, magazine_folders)):
                audio_chunk_dir = os.path.join(large_audio_file_path, magazine_folders, audio_chunk_folder)
                for audio_chunk_file in os.listdir(audio_chunk_dir):
                    audio_chunk_file_path = os.path.join(audio_chunk_dir, audio_chunk_file)
                    extract_transcript_results_for_larger_audio_directory_chunks(os.path.join(large_audio_file_path, magazine_folders), audio_chunk_file_path)
            print(f'Processing done for :: {os.path.basename(os.path.join(large_audio_file_path, magazine_folders))}')

    # elif len(os.listdir(large_audio_file_path)) > 1:
    #     print("Multiple files detected. new fix coming soon.")


def process_extraction_of_transcripts():
    audio_proc = MultimediaFileProcessorTool()
    audio_proc.process_downloaded_videos(os.path.join(os.getcwd(), "downloaded_videos"))
    audio_proc.preprocess_audio_and_denoise_background()
    audio_proc.increase_noise_from_the_processed_audio()
    audio_proc.extract_audio_transcripts_using_openai()
    
# Testing
lg_dir = os.path.join(os.getcwd(), "Large Videos")
dwl_dir = os.path.join(os.getcwd(), "downloaded_videos")
if os.path.exists(lg_dir) and os.path.isdir(lg_dir):
    shutil.rmtree(lg_dir)
if os.path.exists(dwl_dir):
    shutil.rmtree(dwl_dir)

