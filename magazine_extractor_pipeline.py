from azure.core.exceptions import ClientAuthenticationError, HttpResponseError
from azure.ai.formrecognizer import DocumentAnalysisClient, FormRecognizerClient
from azure.ai.textanalytics import TextAnalyticsClient
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes, VisualFeatureTypes, ComputerVisionErrorCodes, ComputerVisionErrorResponseException
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobClient, BlobServiceClient, ContainerClient
from azure.core.credentials import AzureKeyCredential
from msrest.authentication import CognitiveServicesCredentials
import os
import cv2
from typing import AnyStr, List, Union
import random
import shutil
import numpy as np
from PIL import Image as PILImage #, ImageOps, ImageEnhance, ImageFilter
import fitz
import time
import json
from io import BytesIO
import pdfplumber
import tempfile
from wand.image import Image


class MagazineExtractorPipeline:
    def __init__(self) -> None:
        self.all_magazines_main_dir = os.path.join(os.getcwd(), "All Original Magazines")
        self.women_color_magazine_dir = os.path.join(os.getcwd(), "Women of Color Magazine")
        if not os.listdir(self.women_color_magazine_dir) and os.path.exists(self.women_color_magazine_dir):
            print(f'{os.path.basename(self.women_color_magazine_dir)} directory is empty.')
        else:
            self.force_copy_remote_magazines_to_parent_magazine_dir(self.women_color_magazine_dir)

    def force_copy_remote_magazines_to_parent_magazine_dir(self, remote_magazines_dir: AnyStr):
        """This will copy all the remote magazine directory contents to the parent folder i.e Original Magazines
        Note that: this function is not applicable for all test cases."""
        for magazine in os.listdir(os.path.join(remote_magazines_dir)):
            if magazine.endswith('pdf'):
                shutil.move(os.path.join(remote_magazines_dir, magazine), self.all_magazines_main_dir)
                print(f'Magazine {magazine} moved to {os.path.basename(self.all_magazines_main_dir)}.')

    def extract_pages_from_magazine(self, mag_selected, pdf_doc):
        """ This is the copy of the above function, but this will be used for processing extraction in all folders. """
        print(f'Total pages in {str(mag_selected).split(".")[0]}: {pdf_doc.page_count}.')

        for page_number in range(1, pdf_doc.page_count):
            print('in page:', page_number)
            page = pdf_doc.load_page(page_number)
            images = page.get_images(full=True)

            for img_idx, img in enumerate(images):
                xref = img[0]
                base_image = pdf_doc.extract_image(xref)
                image_bytes = base_image["image"]

                selected_mag_folder_dir = os.path.join(os.getcwd(), "All Extracted Magazines", os.path.splitext(mag_selected)[0])
                if not os.path.exists(selected_mag_folder_dir):
                    os.makedirs(selected_mag_folder_dir)

                # Process and save the image bytes
                try:
                    image = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
                    cv2.imwrite(os.path.join(selected_mag_folder_dir, f'Image_{page_number}_{img_idx}.jpg'), image)
                except cv2.error as e:
                    print(f"Error decoding image: {str(e)}")
                    continue  # Skip this image and continue with the next one

    def extract_all_media_from_folders(self, parent_dir_path: Union[AnyStr, List[AnyStr]]):
        """ This will iterate through each magazine and extract media (image) from each page."""
        if isinstance(parent_dir_path, str):
            parent_dir_path = [parent_dir_path]  # Convert a single path to a list

        for dir_path in parent_dir_path:
            print(f'Total files in this folder {os.path.basename(dir_path)} :: {len([file for file in os.listdir(dir_path) if file.endswith(".pdf")])}.')
            all_magazines_folder = os.path.join(os.getcwd(), "All Extracted Magazines")

            # Create the output folder if it doesn't exist
            os.makedirs(all_magazines_folder, exist_ok=True)

            processed_files = set()  # Keep track of processed files

            for filename in os.listdir(dir_path):
                if filename.endswith('.pdf') and filename not in processed_files:
                    if filename.startswith("Hispanic") and filename.__contains__("Volume"):
                        print(f'Selected Magazine: {filename}')
                        pdf_document = fitz.open(os.path.join(dir_path, filename))
                        # Process the PDF document here
                        self.extract_pages_from_magazine(filename, pdf_document)
                        processed_files.add(filename)  # Add the processed file to the set
                        time.sleep(1)  # Sleep as needed

                    if filename.startswith("OCRWomen") and filename.__contains__("Volume"):
                        print(f'Selected Magazine: {filename}')
                        pdf_document = fitz.open(os.path.join(dir_path, filename))
                        # Process the PDF document here
                        self.extract_pages_from_magazine(filename, pdf_document)
                        processed_files.add(filename)  # Add the processed file to the set
                        time.sleep(1)  # Sleep as needed

                else:
                    continue


    def extract_magazines_without_volumes_prefix(self):
        """This will process only those files having color inversion issues with alternate algorithm"""
        non_hispanic_prefix = list(hisp_mag_pdf for hisp_mag_pdf in os.listdir(self.all_magazines_main_dir) if str(hisp_mag_pdf).__contains__("HE"))
        ocrwoc_colormag_prefix = list(color_mag_pdf for color_mag_pdf in os.listdir(self.all_magazines_main_dir) if str(color_mag_pdf).__contains__("OCRWOC"))
        output_dir = os.path.join(os.getcwd(), "Extracted Magazine Texts")
        os.makedirs(output_dir, exist_ok=True)

        credentials = json.load(open(os.path.join(os.getcwd(), "azure_credentials.json")))
        cog_credentials = CognitiveServicesCredentials(credentials.get("ComputerVisionService").get("API-KEY"))
        client = ComputerVisionClient(credentials.get("ComputerVisionService").get("ENDPOINT"), cog_credentials)
        form_recg_client = FormRecognizerClient(credentials.get("FormRecognizer").get("ENDPOINT"), credential=AzureKeyCredential(credentials.get("FormRecognizer").get("API-KEY")))

        for mag_pdf in ocrwoc_colormag_prefix:
            mag_pdf_path = os.path.join(self.all_magazines_main_dir, mag_pdf)
            with pdfplumber.open(mag_pdf_path) as pdf:
                try:
                    for page_num, pdf_page in enumerate(pdf.pages, start=1):
                        pil_image = pdf_page.to_image()
                        # pil_image = pil_image.filter(ImageFilter.GaussianBlur(radius=5))
                        # Save image temporarily in a path
                        women_colmag_img_edit_dir = os.path.join(os.getcwd(), "Women Color Magazine Image Only Edition")
                        os.makedirs(women_colmag_img_edit_dir, exist_ok=True)
                        temp_image_dir = os.path.join(women_colmag_img_edit_dir, os.path.basename(mag_pdf_path).split('.')[0], "PDF Page Images")
                        os.makedirs(temp_image_dir, exist_ok=True)
                        temp_image_path = os.path.join(temp_image_dir, f'temp_page_{page_num}.jpg')
                        pil_image.save(temp_image_path)

                        # Convert image to RGB using wand
                        with Image(filename=os.path.join(temp_image_dir, temp_image_path)) as img:
                            img.format = "JPG"
                            img.save(filename=temp_image_path)
                            # print('image shape:', (img.height, img.width))
                            # Extract the image from the page and save it as a JPEG file
                            img.close()

                        with open(os.path.join(temp_image_dir, temp_image_path), "rb") as page_image:
                            # Perform OCR
                            print(f"Extraction Process for Magazine -> {mag_pdf} ::", os.path.basename(temp_image_path).swapcase())
                            analyze_result = form_recg_client.begin_recognize_content(page_image.read(), content_type="image/jpeg")
                            content_result = analyze_result.result()

                            output_filename = f'{os.path.splitext(mag_pdf)[0]}_page_{page_num}.txt'
                            output_path = os.path.join(output_dir, output_filename)
                            if os.path.exists(output_path):
                                continue

                            with open(output_path, mode='w', encoding='utf-8') as output_file:
                                output_file.write(f'\nPage {page_num}:\n\n')
                                for read_result in content_result:
                                    for line in read_result.lines:
                                        output_file.write(line.text)
                                        output_file.write("\n")

                except ComputerVisionErrorResponseException as cv_exp:
                    print(f"Error occured: {cv_exp}.")
                    if cv_exp.inner_exception:
                        print(cv_exp.inner_exception, "\n", "Message:", cv_exp.message)
                        continue
        print(f"Text extraction completed. Extracted text files are saved in the {os.path.basename(output_dir)} folder.")
        shutil.rmtree(women_colmag_img_edit_dir)

        # Processing for hispanic engineer magazines that does not contain Volume edition
        for i in range(len(non_hispanic_prefix)):
            current_magazine = os.path.join(self.all_magazines_main_dir, non_hispanic_prefix[i])
            os.makedirs(output_dir, exist_ok=True)
            output_text_file = f"{os.path.basename(current_magazine).split('.')[0]}.txt"
            print(f'Magazine: {os.path.basename(current_magazine)}.')

            if os.path.exists(output_text_file) and os.path.isfile(output_text_file):  # Remove pre-existing outputs
                os.remove(output_text_file)

            with open(os.path.join(output_dir, output_text_file), mode='w', encoding='utf-8') as output_file:
                # Open the PDF file using pdfplumber
                with pdfplumber.open(current_magazine) as pdf:
                    with tempfile.TemporaryDirectory() as temp_dir:
                        for page_num, page in enumerate(pdf.pages, start=1):
                            try:
                                page_image = page.to_image()
                                page_image_path = os.path.join(temp_dir, f"page_{page_num}.jpeg")
                                page_image.save(page_image_path, format="PNG")

                                # Convert image to RGB using wand
                                with Image(filename=page_image_path) as img:
                                    img.format = "JPEG"
                                    jpeg_image_path = os.path.join(temp_dir, f"page_{page_num}.jpeg")
                                    img.save(filename=jpeg_image_path)
                                    # Extract the image from the page and save it as a JPEG file

                                    img.close()

                                with open(jpeg_image_path, "rb") as page_image:
                                    # Perform OCR
                                    analyze_result = form_recg_client.begin_recognize_content(page_image.read(), content_type="image/jpeg")
                                    content_result = analyze_result.result()

                                    for read_result in content_result:
                                        output_file.write(f'\nPage {page_num}:\n')
                                        for line in read_result.lines:
                                            output_file.write(line.text)
                                            output_file.write("\n")
                            except Exception as e:
                                print(f'Error processing page {page_num}: {str(e)}.')

    def extract_all_magazines_text_using_computer_vision_algorithm(self):
        credentials = json.load(open(os.path.join(os.getcwd(), "azure_credentials.json")))
        api_endpoint = credentials["ComputerVisionService"]["ENDPOINT"]
        api_key = credentials["ComputerVisionService"]["API-KEY"]
        cv_client = ComputerVisionClient(api_endpoint, CognitiveServicesCredentials(api_key))
        predicted_texts: List[str] = list()
        stored_magazines_folder = os.path.join(os.getcwd(), "All Extracted Magazines")

        # initially remove existing detected outputs from the folder
        for magazine_folder in os.listdir(stored_magazines_folder):
            for image in os.listdir(os.path.join(stored_magazines_folder, magazine_folder)):
                if str(image).endswith('.txt'):
                    os.remove(os.path.join(stored_magazines_folder, magazine_folder, image))

        for magazine_folder in os.listdir(stored_magazines_folder):
            # if magazine_folder.__contains__("OCRWomen"):
            print('Magazine folder:', magazine_folder)
            for image in os.listdir(os.path.join(stored_magazines_folder, magazine_folder)):
                if str(image).endswith('.jpg'):
                    image_path = os.path.join(stored_magazines_folder, magazine_folder, image)

                    with open(image_path, mode='rb') as image_file:
                        try:
                            image_data = image_file.read()
                            response = cv_client.read_in_stream(BytesIO(image_data), language='en', raw=True)
                        except ComputerVisionErrorResponseException as e:
                            print(e.message)
                            if e.inner_exception:
                                print('inner exception:', e.inner_exception)
                            continue
                        operationLocation = response.headers["Operation-Location"]  # To get unique key
                        operationId = str(operationLocation).split('/')[-1]
                        # result = cv_client.get_read_result(operationId)

                        # Wait for the operation to complete
                        while True:
                            try:
                                result = cv_client.get_read_result(operationId)
                                if result.status not in [OperationStatusCodes.succeeded, OperationStatusCodes.failed]:
                                    time.sleep(2)
                                else:
                                    break
                            except ComputerVisionErrorResponseException as err_exp:
                                print(f'Error checking operation status: {err_exp}')
                                break

                        if result.status == OperationStatusCodes.succeeded:
                            read_results = result.analyze_result.read_results
                            for analyzed_result in read_results:
                                for line in analyzed_result.lines:
                                    predicted_texts.append(line.text)

                            extracted_folder_dir = os.path.join(os.getcwd(), "Extracted Magazine Texts", magazine_folder)
                            os.makedirs(extracted_folder_dir, exist_ok=True)
                            output_filename = f'{os.path.splitext(image_path)[0]}.txt'
                            output_path = os.path.join(extracted_folder_dir, output_filename)
                            if os.path.exists(output_path):
                                continue

                            with open(output_path, mode='w', encoding='utf-8') as output_file:
                                output_file.write("\n".join([phrase for phrase in predicted_texts]))
                                predicted_texts.clear()

                        time.sleep(2)

    def extract_only_images(self):
        magazine_images_output_dir = os.path.join(os.getcwd(), "Extracted Magazine Images")
        os.makedirs(magazine_images_output_dir, exist_ok=True)
        valid_page_count: int = 0

        for pdf_path in os.listdir(self.all_magazines_main_dir):
            pdf_document = fitz.open(os.path.join(self.all_magazines_main_dir, pdf_path))
            broken_images_output_dir = os.path.join(magazine_images_output_dir, os.path.basename(pdf_path).split('.')[0])   # same as magazine directory extracted folder, but to store broken images and then remove

            for page_number in range(pdf_document.page_count):
                page = pdf_document.load_page(page_number)
                # Get the XObject (images) dictionary
                xobjects = page.get_images(full=True)

                for xobject_index, xobject in enumerate(xobjects):
                    xobject_index += 1 # start index from 1
                    base_image = pdf_document.extract_image(xobject[0])
                    image_data = base_image["image"]
                    import io

                    try:
                        img = PILImage.open(io.BytesIO(image_data))
                        # Eliminate all broken images with size issues
                        if img.height < 300 and img.width < 300:
                            continue
                        if img.height > 100:
                            if img.width < 400:
                                continue
                        if img.width > 100:
                            if img.height < 100:
                                continue

                        # Save the image
                        nested_mag_path_output_dir = os.path.join(magazine_images_output_dir, os.path.basename(pdf_path).split('.')[0])
                        os.makedirs(nested_mag_path_output_dir, exist_ok=True)
                        image_filename = os.path.join(broken_images_output_dir, f'page_{page_number + 1}_image_{xobject_index}.png')
                        with open(os.path.join(magazine_images_output_dir, image_filename), mode='wb') as image_file:
                            image_file.write(image_data)

                    except Exception as e:
                        # Handle invalid or broken images here (log or ignore)
                        # print('hey you, inside exception.')
                        image_filename = os.path.join(broken_images_output_dir, f'page_{page_number + 1}_image_{xobject_index}.png')
                        os.remove(image_filename)
                        print(f'Removed invalid or broken image on page {page_number + 1}, index {xobject_index}: {str(e)}')
                        continue

        self.validate_extracted_images_and_eliminate(magazine_images_output_dir)
        print(f'Total valid pages in the magazine {os.path.basename(pdf_path)} :: {valid_page_count}.')

    def validate_extracted_images_and_eliminate(self, extracted_magazine_image_path):
        images_removed: int = 0
        for image_folders in os.listdir(extracted_magazine_image_path):
            for image in os.listdir(os.path.join(extracted_magazine_image_path, image_folders)):
                image_path = os.path.join(extracted_magazine_image_path, image_folders, image)
                try:
                    with PILImage.open(image_path) as image:
                        # image.get_child_images()
                        # Eliminate all broken images with size issues
                        if (image.height < 100 and image.width < 100) or (image.height > 100 and image.width < 300) or (image.width > 100 and image.height < 300):
                            os.remove(image_path)
                            images_removed += 1

                except Exception as e:
                    print(f"Error processing {image_path}: {str(e)}")

                    try:
                        # Attempt to remove the file again
                        os.remove(image_path)
                        images_removed += 1
                        print(f"Successfully removed {image_path}")
                        continue
                    except Exception as e:
                        print(f"Failed to remove {image_path}: {str(e)}")

            print(f'Total corrupt images eliminated from the folder {os.path.basename(os.path.join(extracted_magazine_image_path, image_folders))} :: {images_removed}')
        print(f'{images_removed} images cleared from the directory {extracted_magazine_image_path}.')

    def store_all_processed_directories_to_azure_containers(self, processed_folder_path: os.PathLike):
        storage_creds = json.load(open(os.path.join(os.getcwd(), "azure_credentials.json")))
        blob_service_client = BlobServiceClient.from_connection_string(storage_creds["StorageAccounts"]["CONNECTION_STRING"], connection_timeout=500, read_timeout=500, write_timeout=500)

        # Create a container client
        container_client = blob_service_client.get_container_client("stemcitymagazinecontainer")

        for magazine_folders in os.listdir(processed_folder_path):
            blob_folder_path = os.path.join(processed_folder_path, magazine_folders)
            print(f'Processing directory :: {os.path.basename(blob_folder_path)}.')

            if os.path.isdir(blob_folder_path):
                for filename in os.listdir(blob_folder_path):
                    filepath = os.path.join(blob_folder_path, filename)
                    # Create a blob client for uploading files
                    blob_client = container_client.get_blob_client(f"magazinesblob/{magazine_folders}/{filename}")

                    # Upload the file to Azure Blob Storage
                    with open(filepath, "rb") as data:
                        blob_client.upload_blob(data, overwrite=True)

    def process_full_pipeline(self):
        self.extract_all_media_from_folders(self.all_magazines_main_dir)
        self.extract_all_magazines_text_using_computer_vision_algorithm()
        self.extract_magazines_without_volumes_prefix()


pipeline = MagazineExtractorPipeline()
# pipeline.store_all_processed_directories_to_azure_containers(os.path.join(os.getcwd(), "All Extracted Magazines"))