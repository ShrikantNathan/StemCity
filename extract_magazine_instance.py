import PyPDF2
from PIL import Image
import os
from pdf2image import convert_from_path
from extract_only_content_text import MagazineExtractorTextContentFilter
import time

# PDF file input path
pdf_file = [file for file in os.listdir(os.getcwd()) if file.endswith('.pdf')][0]
pdf_file_path = os.path.join(os.getcwd(), pdf_file)

def extract_pages_from_magazine():
    # Output folder for JPEG images
    output_folder = os.path.join(os.getcwd(), "All Extracted Magazines")

    # Create the output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Save the image to the output folder
    output_magazine_path = os.path.join(output_folder, os.path.basename(pdf_file_path).split('.')[0])
    os.makedirs(output_magazine_path, exist_ok=True)

    images = convert_from_path(pdf_file_path, dpi=300)

    # Iterate through the images and save them to the output folder
    for page_num, image in enumerate(images):
        # output_magazine_path = os.path.join(output_folder, os.path.basename(pdf_file_path))
        # os.makedirs(output_magazine_path, exist_ok=True)
        image_filename = os.path.join(output_magazine_path, f'page_{page_num + 1}.jpg')
        image.save(image_filename, 'JPEG')

    print(f'{len(images)} pages extracted and saved as JPEG images in the folder: {output_folder}')


def merge_all_text_contents():
    all_text_contents = []

    extracted_folder = os.path.join(os.getcwd(), "filtered_text_versions", "OCRWOC_Vol212_No1_DIGITAL (1)")
    for file in os.listdir(extracted_folder):
        if file.endswith('.txt'):
            file_path = os.path.join(extracted_folder, file)
            with open(file_path, mode='r', encoding='utf-8') as input_file:
                text_contents = input_file.read()
                all_text_contents.append(text_contents)

    master_text_file = f"master file for {os.path.basename(extracted_folder)}.txt"
    master_text = '\n'.join(all_text_contents)
    with open(os.path.join(extracted_folder, master_text_file), mode='w', encoding='utf-8') as master_file:
        master_file.write(master_text)

    # remove all chunked page outputs after making the master file
    for file in os.listdir(extracted_folder):
        if file.endswith('.txt'):
            if file.__contains__('page') or file.startswith("Image"):
                current_path = os.path.join(extracted_folder, file)
                os.remove(current_path)
            else:
                pass

# text_extractor = MagazineExtractorTextContentFilter()
# text_extractor.extract_text_using_recognizer()
merge_all_text_contents()

# Iterate through each page and convert it to a JPEG image
# for page_num in range(len(pdf.pages)):
#     page = pdf.pages[page_num]
#     image = page.extract_text()  # Extract text from the page (optional)

#     # Convert the page to an image
#     img = page.to_image(dpi=300)  # Adjust the DPI as needed

#     # Save the image to the output folder
#     # output_magazine_path = os.path.join(output_folder, os.path.basename(pdf_file_path))
#     # os.makedirs(output_magazine_path, exist_ok=True)
#     image_filename = os.path.join(output_folder, os.path.basename(pdf_file_path), f'page_{page_num + 1}.jpg')
#     img.save(image_filename, 'JPEG')

# print(f'{len(pdf.pages)} pages extracted and saved as JPEG images in the folder: {output_folder}')
