from PIL import Image, ImageOps
from optimizer import Log
import numpy as np
import pytesseract
import pyautogui
import time
import cv2
import csv
import os
import shutil

Log = Log()
screen_width = 2560
screen_height = 1440

def single_scaling(screenshot_gray, target_image, threshold=.75):
    result = cv2.matchTemplate(screenshot_gray, target_image, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    if max_val >= threshold:
        h, w = target_image.shape
        top_left = min_loc
        bottom_right = (top_left[0] + w, top_left[1] + h)
        return top_left, bottom_right, 1.0, max_val  # Return scale as 1.0
    else:
        return None, None, None, None

def find_all_matches_color(screenshot_rgb, target_rgb, threshold):
    # Perform template matching on each channel separately and average results
    screenshot_b, screenshot_g, screenshot_r = cv2.split(screenshot_rgb)
    target_b, target_g, target_r = cv2.split(target_rgb)

    result_b = cv2.matchTemplate(screenshot_b, target_b, cv2.TM_CCOEFF_NORMED)
    result_g = cv2.matchTemplate(screenshot_g, target_g, cv2.TM_CCOEFF_NORMED)
    result_r = cv2.matchTemplate(screenshot_r, target_r, cv2.TM_CCOEFF_NORMED)

    # Average the results across channels
    result_combined = (result_b + result_g + result_r) / 3

    # Find all matches above the threshold
    locations = np.where(result_combined >= threshold)
    matches = []
    h, w = target_rgb.shape[:2]
    for pt in zip(*locations[::-1]):
        top_left = (pt[0], pt[1])
        bottom_right = (top_left[0] + w, top_left[1] + h)
        matches.append((top_left, bottom_right))

    return matches

def analyze(target_img_path: str    = '../images/EasyApply.png',
            coord_logs_path: str    = '../config/coordinate_log.csv',
            screenshot_path: str    = '../logs/analyzed_region.png',
            get_all_matches: bool   = False,
            optimize_region: tuple  = None,
            restrict_region: tuple  = None,
            limit_optimizer: int    = 20,
            match_threshold: float  = 0.75,
            visual_debugger: bool   = False
            ):

    # Take Screenshot
    screenshot = pyautogui.screenshot(region=restrict_region) if restrict_region else pyautogui.screenshot()
    screenshot.save(screenshot_path)

    # Crop screenshot if optimize_region is provided
    if optimize_region:
        x, y, width, height = optimize_region
        screenshot = screenshot.crop((x, y, x + width, y + height))

    # Convert screenshot to RGB (discard the alpha channel if present)
    screenshot_rgb = np.array(screenshot.convert("RGB"))

    # Load the target image (in color)
    target_image = cv2.imread(target_img_path)
    if target_image is None:
        print(f"Target image {target_img_path} not found!")
        return None

    # Handle get_all_matches logic
    if get_all_matches:
        matches = find_all_matches_color(screenshot_rgb, target_image, threshold=match_threshold)
        if matches:
            match_centers = []  # Store center coordinates of all matches
            match_coords = []   # Store top-left and bottom-right coordinates of all matches

            for top_left, bottom_right in matches:
                match_coords.append((top_left, bottom_right))

                # Calculate the center of the current match
                center_x = top_left[0] + (bottom_right[0] - top_left[0]) // 2
                center_y = top_left[1] + (bottom_right[1] - top_left[1]) // 2
                match_centers.append([int(center_x), int(center_y)])

            # Calculate the maximum bounding box that encapsulates all matches
            max_top_left, max_bottom_right = Log.encapsulate(match_coords)

            if visual_debugger:
                # Save the cropped screenshot for the entire bounding box
                cropped_screenshot = screenshot.crop((max_top_left[0], max_top_left[1], max_bottom_right[0], max_bottom_right[1]))
                cropped_screenshot.save(f"../logs/all_image_matches.png")
                print(f"Visual debug: Saved all matches as 'all_image_matches.png'.")

            # Adjust to Screen Size
            if optimize_region:
                max_top_left = (max_top_left[0] + optimize_region[0], max_top_left[1] + optimize_region[1])
                max_bottom_right = (max_bottom_right[0] + optimize_region[0], max_bottom_right[1] + optimize_region[1])

            # Log only the encapsulating bounding box
            with open(coord_logs_path, mode='a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([max_top_left, max_bottom_right])

            print(f"Encapsulating bounding box of {len(match_coords)} matches logged to {coord_logs_path}.")

            # Limit the number of log entries in the CSV file
            Log.limit(max_entries=limit_optimizer)

            if restrict_region:
                match_centers = [[coords[0]+restrict_region[0], coords[1]] for coords in match_centers]
            return match_centers  # Return list of center coordinates
        else:
            print("No matches found.")
            return None
    else:
        # Single match: Use the first found match
        top_left, bottom_right, best_scale, best_val = single_scaling(screenshot_rgb, target_image, threshold=match_threshold)

        if top_left is not None:
            cropped_screenshot = screenshot.crop((top_left[0], top_left[1], bottom_right[0], bottom_right[1]))

            # Save the cropped screenshot
            cropped_screenshot.save(f"../logs/single_image_match.png")

            h, w = bottom_right[1] - top_left[1], bottom_right[0] - top_left[0]

            # Adjust to Screen Size
            if optimize_region:
                top_left = (top_left[0] + optimize_region[0], top_left[1] + optimize_region[1])
                bottom_right = (bottom_right[0] + optimize_region[0], bottom_right[1] + optimize_region[1])

            # Log Coordinates
            with open(coord_logs_path, mode='a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([top_left, bottom_right])

            print(f"Match found with confidence {best_val}. Coordinates logged to {coord_logs_path}.")

            # Log Limiter
            Log.limit(max_entries=limit_optimizer)

            # Return the center coordinate of the single match
            center_x = top_left[0] + (bottom_right[0] - top_left[0]) // 2
            center_y = top_left[1] + (bottom_right[1] - top_left[1])
            return center_x, center_y
        else:
            # If no match is found, still save the screenshot with a "no_match" suffix
            no_match_screenshot_path = screenshot_path.replace(".png", "_no_match.png")
            screenshot.save(no_match_screenshot_path)
            print(f"No match found. Screenshot saved to {no_match_screenshot_path}")

            return None


def scroll(y_scroll: int=0) -> None:
    pyautogui.scroll(y_scroll, x=None, y=None)

def main():
    current_time: str = time.strftime("%H:%M:%S")
    i: int = 0
    print(f"[ Starting @ {time.strftime("%Y-%m-%d")} ]")
    while True:
        i += 1
        # Get the current time and format it
        print(f"\n[ {i} | {current_time} ]")

        # Analyze Match and save a screenshot each time
        coordinates: list = analyze(
            target_img_path='../images/EasyApplySmall.png',
            get_all_matches=True,
            visual_debugger=True
        )

        # Optional: Screening Optimization
        Log.optimize()

        # click(coordinates[0], coordinates[1]) if coordinates else None

        # Iteration Interval
        time.sleep(5)

def automation_series() -> None:
    # LOCAL FUNCTIONS _______________________________________________

    def scan():
         pass

    def screenie(region: tuple = None) -> any:
        print(f"    Capturing region: {region}")
        try:
            image = pyautogui.screenshot(region=region) if region else pyautogui.screenshot()
            image.save("../logs/analyzed_region.png")
            return image
        except Exception as e:
            print(f"Error taking screenshot: {e}")
            return None

    def click(clicks: int = 1, x: int = 0, y: int = 0, wait: int = 0) -> None:
        for _ in range(clicks):
            pyautogui.click(x, y)
        time.sleep(wait)

    def apply():
        def img2txt(image) -> any:
            return pytesseract.image_to_string(image)

        def identify(page: str='') -> any:
            page = page.lower()
            page_keywords = {
                'contact': ['contact info', 'email address', 'phone country code', 'mobile phone number'],
                'resume': ['be sure to include an updated resume'],
                'additional': ['how many years of work experience do you have with'],
                'review': ['review your application', 'the employer will also receive a copy of your profile']
            }
            for page_type, keywords in page_keywords.items():
                for keyword in keywords:
                    if keyword in page:
                        print(f"    Found {keyword}. Page is {page_type}.")
                        return page_type

        i: int = 0
        # Scan and fill out each application page.
        while i < 10:
            # Screenshot application.
            bottom_left: list = list(analyze(
                target_img_path='../images/SubApp.png',
                get_all_matches=True,
                visual_debugger=True
            ))[0]
            x1, y1 = bottom_left[0], bottom_left[1]

            top_right: list = list(analyze(
                target_img_path='../images/ExitIconAndZeroPercent.png',
                get_all_matches=True,
                visual_debugger=False
            ))[0]
            x2, y2 = top_right[0], top_right[1]

            # Introduce padding.
            pl, _ = Image.open('../images/SubApp.png').size
            pr, _ = Image.open('../images/ExitIconAndZeroPercent.png').size

            # Ensure positive width and height, and adjust if necessary
            width = abs(x2 - x1 + pr)
            height = abs(y1 - y2)

            # Calculate the region ensuring the coordinates are valid
            region: tuple = (
                x1 - pl,  # Left (x)
                y2,       # Top (y)
                width,    # Width
                height    # Height
            )

            # Screen & scan page.
            page_content: str = img2txt(screenie(region=region))
            page_type: str = identify(page_content)

            # Enter contact info
            if page_type == 'contact':
                print(f"    PAGE TYPE: Contact")
                next_button: list = list(analyze(
                    target_img_path='../images/Next.png',
                    get_all_matches=True,
                    restrict_region=(screen_width//2, 0, (screen_width//2)-1, screen_height),
                    visual_debugger=True,
                    match_threshold=.99
                ))[0]
                time.sleep(2)
                print(f"COORDS: {next_button}")
                click(clicks=1, x=next_button[0], y=next_button[1], wait=2)
                print(f"CLICKED: {next_button}")

            # Choose resume
            elif page_type == 'resume':
                print(f"    PAGE TYPE: Resume")
                next_button: list = list(analyze(
                    target_img_path='../images/Next.png',
                    get_all_matches=True,
                    restrict_region=(screen_width//2, 0, (screen_width//2)-1, screen_height),
                    visual_debugger=True,
                    match_threshold=.99
                ))[0]
                time.sleep(2)
                click(clicks=1, x=next_button[0], y=next_button[1], wait=2)

            # Logic for answering additional information
            elif page_type == 'additional':
                print(f"    PAGE TYPE: Additional")

                next_button: list = list(analyze(
                    target_img_path='../images/Next.png',
                    get_all_matches=True,
                    restrict_region=(screen_width//2, 0, (screen_width//2)-1, screen_height),
                    visual_debugger=True,
                    match_threshold=.99
                ))[0]
                if next_button:
                    click(clicks=1, x=next_button[0], y=next_button[1], wait=2)
                else:
                    review_button: list = list(analyze(
                        target_img_path='../images/Review.png',
                        get_all_matches=True,
                        restrict_region=(screen_width//2, 0, (screen_width//2)-1, screen_height),
                        visual_debugger=True,
                        match_threshold=.99
                    ))[0]
                    click(clicks=1, x=review_button[0], y=review_button[1], wait=2)

            # Unsubscribe to newletter & submit
            elif page_type == 'review':
                print(f"    PAGE TYPE: Review")
                submit_button: list = list(analyze(
                    target_img_path='../images/SubmitApplication.png',
                    restrict_region=(screen_width//2, 0, (screen_width//2)-1, screen_height),
                    get_all_matches=True,
                    visual_debugger=True,
                    match_threshold=.99
                ))[0]
                click(clicks=1, x=submit_button[0], y=submit_button[1], wait=2)
                print(f"    Application submitted.")
                return

            # Increment to eventually hit the fail-safe stop
            i += 1
            time.sleep(5)


    def change_page() -> None:
        pass

    # START _________________________________________________________
    i: int = 0
    current_time: str = time.strftime("%H:%M:%S")
    print(f"[ Starting @ {time.strftime('%Y-%m-%d')} ]")
    time.sleep(5)

    # Automation Loop
    while True:

        # Scan for all available 'Easy Apply' listings in page.
        all_job_listings: list = list(analyze(
            target_img_path='../images/EasyApplySmall.png',
            get_all_matches=True,
            visual_debugger=True
        ))

        # Apply to all 'Easy Apply' listings.
        for job_listing in all_job_listings:

            # Track number of attempted applications.
            i += 1
            print(f"\n[ Job Listing {i} | {current_time} ]")

            # Check job listing description.
            click(clicks=2, x=job_listing[0], y=job_listing[1], wait=2)

            # Start job application.
            application_start: list = list(analyze(
                target_img_path='../images/EasyApply.png',
                get_all_matches=True,
                visual_debugger=True,
            ))[0]
            click(clicks=1, x=application_start[0], y=application_start[1], wait=2)

            # Fill out all application fields.
            apply()

            # Complete.
            print(f"Applied.")
            time.sleep(5)

        # TEST: Return after 1
        return

        change_page()


if __name__ == "__main__":
    # main()
    automation_series()
