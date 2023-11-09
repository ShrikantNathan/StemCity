from azure.core.exceptions import ClientAuthenticationError, HttpResponseError
from azure.ai.formrecognizer import DocumentAnalysisClient, FormRecognizerClient
from azure.ai.textanalytics import TextAnalyticsClient
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes, VisualFeatureTypes
from azure.identity import DefaultAzureCredential
from msrest.authentication import CognitiveServicesCredentials
import os
import cv2
from typing import AnyStr, List, Union
import random
import shutil
import numpy as np
import io
import fitz
import time

def main():
  try:
    AZURE_CREDENTIALS = {
        "ENDPOINT": "https://stemcityproject.cognitiveservices.azure.com/",
        "COGKEYS": {
          "OPT-1": "7a80b805e1b1499f91f8f7102ec7df71",
          "OPT-2": "245a252ca0574fd8b394865c0dcf36e0"
          }
    }

    credential = DefaultAzureCredential()
    client = DocumentAnalysisClient(AZURE_CREDENTIALS["ENDPOINT"], credential)
    # source_folder = random.choice([magazine for magazine in os.listdir(os.getcwd()) if "Magazine" in magazine])
    source_folder = os.path.join(os.getcwd(), "All Extracted Magazines")
    output_folder = os.path.join(os.getcwd(), "Extracted_Image_Texts", str(source_folder))
    os.makedirs(output_folder, exist_ok=True)

    for pdf_file in os.listdir(source_folder):
      if pdf_file.endswith(".pdf"):
        pdf_path = os.path.join(source_folder, pdf_file)
        output_filename = f'{os.path.splitext(pdf_file)[0]}.txt'
        output_path = os.path.join(output_folder, output_filename)

        extracted_text = str()
        with fitz.open(pdf_path) as doc:
            for page_num in range(doc.page_count):
                page = doc[page_num]
                extracted_text += page.get_text()

        with open(output_path, mode='w', encoding='utf-8') as output_file:
            output_file.write(extracted_text)

        # Use the Text Analytics client to analyze the extracted text
        documents = [{"id": pdf_file, "text": extracted_text}]
        response = client.analyze_sentiment(documents=documents)
        sentiment_score = response[0].confidence_scores.positive

        print("Text extraction completed successfully.")
        print(f'Text Sentiment score: {sentiment_score}.')

  except Exception as e:
    return (f"An error occurred: {str(e)}")


def extract_text_from_images(image_folder: AnyStr, output_folder: AnyStr):
  AZURE_CREDS = {"Endpoint": "https://magazineextractorinstance.cognitiveservices.azure.com/", "Keys": {"Gen": "0672b24216fb416097243020c719b7a2", "Gen2": "b5d4450af6ed462680ca20fb4d42e595"}}
  credential = DefaultAzureCredential()
  client = DocumentAnalysisClient(AZURE_CREDS.get('Endpoint'), credential)
  os.makedirs(output_folder, exist_ok=True)

  for image_file in os.listdir(image_folder):
    if image_file.lower().endswith(('.png', '.jpg', '.jpeg')):
      image_path = os.path.join(image_folder, image_file)
      output_filename = f'{os.path.splitext(image_file)[0]}.txt'
      output_path = os.path.join(output_folder, output_filename)

      with open(image_path, mode='rb') as image_stream:
        poller = client.begin_analyze_document("prebuilt/receipt", image_stream)
        result = poller.result()

      extracted_text = str()
      for page in result.pages:
        for line in page.lines:
          extracted_text += f'{line.content}\n'

      with open(output_path, mode='w', encoding='utf-8') as output_file:
        output_file.write(extracted_text)

# Testing process start.
# selected_image_folder = random.choice([folder for folder in os.listdir(os.path.join(os.getcwd(), "All Extracted Magazines"))])
# print('Selected Image folder ::', selected_image_folder)
# extract_text_from_images(os.path.join("All Extracted Magazines", selected_image_folder), os.path.join("Extracted Magazine Texts", selected_image_folder))