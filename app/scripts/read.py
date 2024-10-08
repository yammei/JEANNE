from PIL import Image
import pytesseract

def extract_text_from_image(image_path):
    # Open the image file
    img = Image.open(image_path)

    # Use pytesseract to do OCR on the image
    text = pytesseract.image_to_string(img)

    return text

# Example usage
image_path = 'example_image.png'
text = extract_text_from_image(image_path)
print("Extracted Text:")
print(text)
