import os
import numpy as np
from typing import List, Union
import fitz
from PIL import Image, ImageChops, ImageEnhance, UnidentifiedImageError
import io


class MagazineImageExtractorAPI:
  def __init__(self) -> None:
    self.magazines_dir = os.path.join(os.getcwd(), "All Original Magazines")  # this directory will soon be replaced by client's link, waiting for client's input, as of now Its processing from local storage
    self.magazine_instance = [magazine for magazine in os.listdir(self.magazines_dir)][1]
    self.magazine_instance_path = os.path.join(self.magazines_dir, self.magazine_instance)
    self.image_output_dir = os.path.join(os.getcwd(), "Extracted Magazine Images")

  def filter_and_process_standard_image(self, image_dir_path: Union[os.PathLike, List[os.PathLike]]):
    for extracted_magazines in os.listdir(image_dir_path):
      for image in os.listdir(os.path.join(image_dir_path, extracted_magazines)):
        if str(image).endswith('.jpg'):
          current_image_path = os.path.join(image_dir_path, extracted_magazines, image)
          current_image = Image.open(current_image_path)

          # Setting up dimensions to filter
          min_width, min_height = 100, 100
          max_width, max_height = 300, 300

          # verify each image with min dimensions and max dimensions criteria fit range, save them on criteria set,
          # discard them in case of breach
          if current_image.width >= min_width and current_image.height >= min_height: # and current_image.width <= max_width and current_image.height <= max_height
              current_image.save(current_image_path, format='JPEG')

          else:
            current_image.close()
            os.remove(current_image_path)

  def extract_all_images_from_magazines(self):
    os.makedirs(self.image_output_dir, exist_ok=True)

    for magazine in os.listdir(self.magazines_dir):
      magazine_pdf_path = os.path.join(self.magazines_dir, magazine)
      print(f'Processing :: {os.path.basename(magazine_pdf_path)}')

      # Open the PDF file using PyMuPDF
      pdf_document = fitz.open(magazine_pdf_path)

      for page_number in range(pdf_document.page_count):
        page = pdf_document[page_number]

        # Get the images on the page
        images = page.get_images(full=True)

        for image_index, image in enumerate(images):
          xref = image[0]
          base_image = pdf_document.extract_image(xref)
          image_bytes = base_image["image"]

          try:
            # Convert the image to a PIL Image
            image_data = Image.open(io.BytesIO(image_bytes))

            if image_data.mode == 'RGBA':
              image_data = image_data.convert('RGB')

            if image_data.mode != 'RGB':
              image_data = ImageChops.invert(image_data)

          except UnidentifiedImageError:
            print(f'Skipping unidentified image at page {page_number}, image {image_index}.')

          # Save the image as JPEG
          nested_image_output_dir = os.path.join(self.image_output_dir, os.path.basename(magazine_pdf_path).split('.')[0])
          os.makedirs(nested_image_output_dir, exist_ok=True)
          image_path = os.path.join(nested_image_output_dir, f"page{page_number}_image{image_index}.jpg")
          image_data.save(image_path, "JPEG")

          print(f"Extracted image: {image_path}")


# mag_api = MagazineImageExtractorAPI()
# mag_api.extract_all_images_from_magazines()
# mag_api.filter_and_process_standard_image(os.path.join(os.getcwd(), "Extracted Magazine Images"))
