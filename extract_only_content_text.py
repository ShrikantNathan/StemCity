import os
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import FormRecognizerClient, FormLine
from msrest.authentication import CognitiveServicesCredentials
from typing import Union, List
import json
from PIL import Image
import time
import asyncio
from spellchecker import SpellChecker
from pdf2image import convert_from_path
from concurrent.futures.thread import ThreadPoolExecutor
from concurrent.futures.process import ProcessPoolExecutor
import random


def is_within_region(line: FormLine, region: tuple):
    line_x = line.bounding_box[0].x
    line_y = line.bounding_box[1].y

    region_x, region_y, region_width, region_height = region

    return (
            line_x >= region_x
            and line_x <= region_x + region_width
            and line_y >= region_y
            and line_y <= region_y + region_height
        )


class MagazineExtractorTextExtractorConcurrent:
    def __init__(self) -> None:
        self.__original_magazine_dir = os.path.join(os.getcwd(), "All Original Magazines")
        self.extracted_magazine_image_dir = os.path.join(os.getcwd(), "All Extracted Magazines")
        self.__credentials = json.load(open(os.path.join(os.getcwd(), "azure_credentials.json")))
        self.__cv_subscription_key = self.__credentials["ComputerVisionService"]["API-KEY"]
        self.cog_creds = CognitiveServicesCredentials(self.__cv_subscription_key)
        
    def extract_pages_from_magazine(self, magazine_pdf_file_path, output_folder):
        # Extract pages from a single magazine PDF
        images = convert_from_path(magazine_pdf_file_path, dpi=300)

        for page_num, image in enumerate(images):
            image_filename = os.path.join(output_folder, f'page_{page_num + 1}.jpg')
            image.save(image_filename, 'JPEG')

        print(f'{os.path.basename(magazine_pdf_file_path)} :: {len(images)} pages extracted and saved as JPEG images')

    def extract_text_from_image(self, image_path, output_folder, form_recognizer_client):
            # Extract text from a single image
            extracted_text = ""
            with open(image_path, 'rb') as image_file:
                poller = form_recognizer_client.begin_recognize_content(image_file)
                result = poller.result()
                for page in result:
                    for line in page.lines:
                        extracted_text += line.text + '\n'

            text_file_path = os.path.join(output_folder, f'{os.path.basename(image_path).split(".")[0]}.txt')
            with open(text_file_path, mode='w', encoding='utf-8') as image_output_text_file:
                image_output_text_file.write(extracted_text)

    def extract_text_using_recognizer(self, magazine_folder):
        header_region = (0, 0, 800, 100)  # Example header region
        footer_region = (0, 974, 800, 100)  # Example footer region

        recognized_output_dir = os.path.join(os.getcwd(), "filtered_text_versions", magazine_folder)
        os.makedirs(recognized_output_dir, exist_ok=True)

        credential = AzureKeyCredential(self.__credentials["FormRecognizer"]["API-KEY"])
        client = FormRecognizerClient(endpoint=self.__credentials["FormRecognizer"]["ENDPOINT"], credential=credential)

        for image in os.listdir(os.path.join(self.extracted_magazine_image_dir, magazine_folder)):
            if image.endswith('.jpg'):
                image_path = os.path.join(self.extracted_magazine_image_dir, magazine_folder, image)
                self.extract_text_from_image(image_path, recognized_output_dir, client)

        print(f'Processed magazine :: {magazine_folder}')

    def process_magazine(self, magazine_pdf_file):
        # Process a single magazine PDF
        output_folder = os.path.join(self.extracted_magazine_image_dir, os.path.basename(magazine_pdf_file).split('.')[0])
        os.makedirs(output_folder, exist_ok=True)
        self.extract_pages_from_magazine(magazine_pdf_file, output_folder)
        self.extract_text_using_recognizer(os.path.basename(magazine_pdf_file).split('.')[0])

    def ensure_spellcheck_and_sentence_correction(self, extracted_text_folder: os.PathLike):
        spell = SpellChecker()
        for filename in os.listdir(extracted_text_folder):
            if filename.endswith('.txt'):
                text_file_path = os.path.join(extracted_text_folder, filename)
                with open(text_file_path, encoding='utf-8', mode='r') as f:
                    text = f.read()

                words = text.split()
                corrected_text = list()
                for word in words:
                    corrected_word = spell.correction(word)
                    if not corrected_word is not None and isinstance(corrected_word, str):
                        corrected_text.append(corrected_word)
                    else:
                        corrected_text.append(word)

                # filter out None and non string values
                corrected_text = [word for word in corrected_text if word is not None and isinstance(word, str)]

                # Join the corrected words back into text
                corrected_text = ' '.join(corrected_text)

                with open(text_file_path, mode='w', encoding='utf-8') as f:
                    f.write(corrected_text)

    def process_magazines_concurrently(self):
        # Process magazines concurrently using multithreading
        with ThreadPoolExecutor(max_workers=4) as executor:
            for magazine_pdf_file in os.listdir(self.__original_magazine_dir):
                magazine_pdf_file_path = os.path.join(self.__original_magazine_dir, magazine_pdf_file)
                executor.submit(self.process_magazine, magazine_pdf_file_path)



class MagazineExtractorTextContentFilter:
    def __init__(self) -> None:
        self.__original_magazine_dir = os.path.join(os.getcwd(), "All Original Magazines")
        self.extracted_magazine_image_dir = os.path.join(os.getcwd(), "All Extracted Magazines")
        self.__credentials = json.load(open(os.path.join(os.getcwd(), "azure_credentials.json")))
        self.__cv_subscription_key = self.__credentials["ComputerVisionService"]["API-KEY"]
        self.cog_creds = CognitiveServicesCredentials(self.__cv_subscription_key)
        # self.client = ComputerVisionClient(endpoint=self.__credentials["ComputerVisionService"]["ENDPOINT"], credentials=self.cog_creds)
        self.extracted_text: Union[str, List[str]] = list()

    def extract_pipeline_for_instance_magazine(self, root_magazine_dir: os.PathLike = os.getcwd()):
        random_magazine = random.choice([magazine for magazine in os.listdir(root_magazine_dir)])
        random_magazine_path = os.path.join(root_magazine_dir, random_magazine)
        print(f'Testing for :: {random_magazine}.')
        output_folder = os.path.join(os.getcwd(), "All Extracted Magazines")
        os.makedirs(output_folder, exist_ok=True)
        output_magazine_path = os.path.join(output_folder, os.path.basename(random_magazine_path).split('.')[0])
        os.makedirs(output_magazine_path, exist_ok=True)

        images = convert_from_path(random_magazine_path, dpi=300)

        # Iterate through the images and save them to the output folder
        for page_num, image in enumerate(images):
            # output_magazine_path = os.path.join(output_folder, os.path.basename(pdf_file_path))
            # os.makedirs(output_magazine_path, exist_ok=True)
            image_filename = os.path.join(output_magazine_path, f'page_{page_num + 1}.jpg')
            image.save(image_filename, 'JPEG')

        print(f'{os.path.basename(random_magazine_path)} :: {len(images)} pages extracted and saved as JPEG images in the folder: {output_folder}')

        # Define header and footer regions as bounding boxes [left, top, width, height]
        header_region = (0, 0, 800, 100)  # Example header region
        footer_region = (0, 974, 800, 100)  # Example footer region

        # Perform the text extraction code
        extracted_file_path = os.path.join(output_folder, os.path.basename(random_magazine_path).split('.')[0])

        for image in os.listdir(extracted_file_path):
            if image.endswith('.jpg'):
                extracted_text = ""
                image_path = os.path.join(extracted_file_path, image)
                credential = AzureKeyCredential(self.__credentials["FormRecognizer"]["API-KEY"])
                client = FormRecognizerClient(endpoint=self.__credentials["FormRecognizer"]["ENDPOINT"], credential=credential)

                with open(image_path, 'rb') as image_file:
                    poller = client.begin_recognize_content(image_file)
                    result = poller.result()
                    for page in result:
                        for line in page.lines:
                            # check if the line is outside the header and footer regions
                            if not is_within_region(line, header_region) and not is_within_region(line, footer_region):
                                extracted_text += line.text + '\n'

                recognized_output_dir = os.path.join(os.getcwd(), "filtered_text_versions", os.path.basename(extracted_file_path))
                os.makedirs(recognized_output_dir, exist_ok=True)
                with open(os.path.join(recognized_output_dir, f'{os.path.basename(image_path).split(".")[0]}.txt'), mode='w', encoding='utf-8') as image_output_text_file:
                    image_output_text_file.write(extracted_text)

                # this below portion checks for grammar issues in the text file and corrects all sentences wherever necessary
                time.sleep(1)
                print(f"checking for corrections in {image_output_text_file.name}..")
                self.ensure_spellcheck_and_sentence_correction(recognized_output_dir)
        print(f'Processed magazine :: {os.path.basename(extracted_file_path)}')

    def extract_pages_from_magazine(self):
        # Output folder for JPEG images
        output_folder = os.path.join(os.getcwd(), "All Extracted Magazines")

        # Create the output folder if it doesn't exist
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        # Save the image to the output folder
        for magazine_pdf_file in os.listdir(self.__original_magazine_dir):
            magazine_pdf_file_path = os.path.join(self.__original_magazine_dir, magazine_pdf_file)
            output_magazine_path = os.path.join(output_folder, os.path.basename(magazine_pdf_file_path).split('.')[0])
            os.makedirs(output_magazine_path, exist_ok=True)

            images = convert_from_path(magazine_pdf_file_path, dpi=300)

            # Iterate through the images and save them to the output folder
            for page_num, image in enumerate(images):
                # output_magazine_path = os.path.join(output_folder, os.path.basename(pdf_file_path))
                # os.makedirs(output_magazine_path, exist_ok=True)
                image_filename = os.path.join(output_magazine_path, f'page_{page_num + 1}.jpg')
                image.save(image_filename, 'JPEG')

            print(f'{os.path.basename(magazine_pdf_file_path)} :: {len(images)} pages extracted and saved as JPEG images in the folder: {output_folder}')

    def ensure_spellcheck_and_sentence_correction(self, extracted_text_folder: os.PathLike):
        spell = SpellChecker()
        for filename in os.listdir(extracted_text_folder):
            if filename.endswith('.txt'):
                text_file_path = os.path.join(extracted_text_folder, filename)
                with open(text_file_path, encoding='utf-8', mode='r') as f:
                    text = f.read()

                words = text.split()
                corrected_text = list()
                for word in words:
                    corrected_word = spell.correction(word)
                    if not corrected_word is not None and isinstance(corrected_word, str):
                        corrected_text.append(corrected_word)
                    else:
                        corrected_text.append(word)

                # filter out None and non string values
                corrected_text = [word for word in corrected_text if word is not None and isinstance(word, str)]

                # Join the corrected words back into text
                corrected_text = ' '.join(corrected_text)

                with open(text_file_path, mode='w', encoding='utf-8') as f:
                    f.write(corrected_text)

    def extract_text_using_recognizer(self):
        # Define header and footer regions as bounding boxes [left, top, width, height]
        header_region = (0, 0, 800, 100)  # Example header region
        footer_region = (0, 974, 800, 100)  # Example footer region

        for magazine_folder in os.listdir(self.extracted_magazine_image_dir):
            print('Processing magazine ::', magazine_folder)
            for image in os.listdir(os.path.join(self.extracted_magazine_image_dir, magazine_folder)):
                if image.endswith('.jpg'):
                    extracted_text = ""
                    image_path = os.path.join(self.extracted_magazine_image_dir, magazine_folder, image)
                    credential = AzureKeyCredential(self.__credentials["FormRecognizer"]["API-KEY"])
                    client = FormRecognizerClient(endpoint=self.__credentials["FormRecognizer"]["ENDPOINT"], credential=credential)

                    with open(image_path, 'rb') as image_file:
                        poller = client.begin_recognize_content(image_file)
                        result = poller.result()
                        for page in result:
                            for line in page.lines:
                                # check if the line is outside the header and footer regions
                                if not is_within_region(line, header_region) and not is_within_region(line, footer_region):
                                    extracted_text += line.text + '\n'

                    recognized_output_dir = os.path.join(os.getcwd(), "filtered_text_versions", magazine_folder)
                    os.makedirs(recognized_output_dir, exist_ok=True)
                    with open(os.path.join(recognized_output_dir, f'{os.path.basename(image_path).split(".")[0]}.txt'), mode='w', encoding='utf-8') as image_output_text_file:
                        image_output_text_file.write(extracted_text)

                    # this below portion checks for grammar issues in the text file and corrects all sentences wherever necessary
                    time.sleep(1)
                    print(f"checking for corrections in {image_output_text_file.name}..")
                    self.ensure_spellcheck_and_sentence_correction(recognized_output_dir)
            print(f'Processed magazine :: {magazine_folder}')

test = MagazineExtractorTextContentFilter()
test.extract_pipeline_for_instance_magazine(os.path.join(os.getcwd(), "All Original Magazines"))
# async_test = MagazineExtractorTextExtractorConcurrent()
# async_test.process_magazines_concurrently()