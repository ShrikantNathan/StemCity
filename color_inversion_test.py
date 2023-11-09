import os
from PIL import Image as PILImage, ImageOps, ImageEnhance
import pickle
from typing import Union, Optional, List, AnyStr
import time

processed_images = list()
# folder_tracker = os.path.join(os.getcwd(), "Processed Images Record Tracker")

def load_processed_images(magazine_pdf_path):
    global processed_images
    try:
        with open(f'processed_images_{os.path.basename(magazine_pdf_path)}.pkl', 'rb') as file:
            processed_images = pickle.load(file)
    except FileNotFoundError as err:
        processed_images = list()
        print(err)

def save_processed_images(magazine_pdf_path):
    global processed_images
    with open(f'processed_images_{os.path.basename(magazine_pdf_path)}.pkl', 'wb') as file:
        pickle.dump(processed_images, file)

def is_image_negative(image):
  """Checks if an image is negative.

  Args:
    image: A numpy array representing the image.

  Returns:
    True if the image is negative, False otherwise.
  """

  # Calculate the average pixel value of the image.
  #   average_pixel_value = cv2.mean(image)[0]
  average_pixel_value = image.getextrema()[0][0]

  # If the average pixel value is less than 128, then the image is negative.
  return average_pixel_value < 128


def convert_cmyk_to_rgb(image):
    # Check if the image is in CMYK color mode
    # Invert the colors of the image.
    # if image.mode == 'CMYK':
    inverted_image = ImageOps.invert(image)

    # Convert the image to RGB mode.
    rgb_image = inverted_image.convert('RGB')

    # Apply enhancement filters
    contrasted = ImageEnhance.Contrast(rgb_image).enhance(1.0)
    brightness = ImageEnhance.Brightness(contrasted).enhance(1.0)

    return brightness

def process_and_save_image(image_path: str, processed_output_folder: Optional[Union[str, List[AnyStr]]] = os.path.join(os.getcwd(), "Extracted Magazine Images", "Processed Images")):
    global processed_images
    os.makedirs(processed_output_folder, exist_ok=True)
    try:
        if image_path in processed_images:
            print(f'Skipping already processed image: {image_path}')
            return True

        with PILImage.open(image_path) as image:
            # Eliminate all broken images with size issues
            if (image.height < 100 and image.width < 100) or (image.height > 100 and image.width < 300) or (image.width > 100 and image.height < 300):
                os.remove(image_path)
                image.close()
                images_removed += 1

            else:
                if is_image_negative(image):
                    # Convert CMYK to RGB if necessary
                    image = convert_cmyk_to_rgb(image)
                elif image.mode == 'CMYK':
                    image = convert_cmyk_to_rgb(image)
                else:
                    pass

                # Save the image as PNG
                image.save(image_path, "JPEG")

                # Record the processed image
                processed_images.append(image_path)
                return True

    except Exception as e:
        print(f"Error processing {image_path}: {str(e)}")
        return False

def convert_to_rgb(image: PILImage.Image):
    if image.mode == 'RGB':
        return image
    else:
        return image.convert('RGB')

# load_processed_images()
def convert_png_to_jpeg(input_folder: str):
    """function to first convert png to jpeg and then do the preprocessing."""
    output_dir = os.path.join(os.getcwd(), "PNG_TO_JPG", "Processed Images")
    os.makedirs(output_dir, exist_ok=True)

    for nested_magazine_image_dir in os.listdir(input_folder):
        load_processed_images(os.path.join(input_folder, nested_magazine_image_dir))
        for image in os.listdir(os.path.join(input_folder, nested_magazine_image_dir)):
            image_path = os.path.join(input_folder, nested_magazine_image_dir, image)
            if image_path.endswith('.png'):
                current_image = PILImage.open(image_path)
                if (current_image.height < 100 and current_image.width < 100) or (current_image.height > 100 and current_image.width < 300) or (current_image.width > 100 and current_image.height < 300):
                    current_image.close()
                    os.remove(image_path)
                    # images_removed += 1
                    # time.sleep(1)
                    continue

                else:
                    current_image = convert_to_rgb(current_image)
                    new_imagext = os.path.join(output_dir, os.path.splitext(image)[0] + ".jpg")
                    current_image.save(new_imagext, format="JPEG")
                    current_image.close()
                    # time.sleep(1)
        save_processed_images(output_dir)

# Usage example:
magazine_dir = os.path.join(os.getcwd(), "Random Inverted Magazine")
magazine_dir_full = os.path.join(os.getcwd(), "Extracted Magazine Images")

# for magazine_folders in os.listdir(magazine_dir_full):
#     load_processed_images(os.path.join(magazine_dir_full, magazine_folders))

#     for image in os.listdir(os.path.join(magazine_dir_full, magazine_folders)):
#         image_path = os.path.join(magazine_dir_full, magazine_folders, image)
#         # output_path = "output_image.png"
        
#         if process_and_save_image(image_path):
#             print(f"Image processed and saved to {image_path}")
#             continue
#         else:
#             print(f"Image processing failed for {image_path}")

#     save_processed_images(os.path.join(magazine_dir_full, magazine_folders))

# convert_png_to_jpeg(magazine_dir_full)