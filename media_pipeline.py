import os
from typing import List, Union, Dict
import json
from extract_only_content_text import MagazineExtractorTextContentFilter
from extract_only_content_image import MagazineImageExtractorAPI
from audio_processing import process_extraction_of_transcripts()


class AsynchronousMultimediaModelPipeline:
    def __init__(self) -> None:
        self.text_extractor = MagazineExtractorTextContentFilter()
        self.image_extractor = MagazineImageExtractorAPI()
        self.credentials = json.load(open(os.path.join(os.getcwd(), "azure_credentials.json")))
        # self.azure_vision_creds: Dict[str, Union[str, List[str]]] = {"API-KEY": self.credentials["ComputerVisionService"]["API-KEY"], "ENDPOINT": self.credentials["ComputerVisionService"]["ENDPOINT"]}
        # self.form_recognizer_creds: Dict[str, Union[str, List[str]]] = {"API-KEY": self.credentials["FormRecognizer"]["API-KEY"], "ENDPOINT": self.credentials["FormRecognizer"]["ENDPOINT"]}

    def process_media_pipeline(self):
        # image pipeline
        extracted_image_dir = os.path.join(os.getcwd(), "Extracted Magazine Images")    # this directory will be auto created after calling the below function to extract all images from magazines
        self.image_extractor.extract_all_images_from_magazines()
        self.image_extractor.filter_and_process_standard_image(extracted_image_dir)

        # text pipeline
        self.text_extractor.extract_text_using_recognizer()

        # video pipeline
        process_extraction_of_transcripts()


med_pipe = AsynchronousMultimediaModelPipeline()
med_pipe.process_media_pipeline()