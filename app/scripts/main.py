from optimizer import Log
from PIL import Image, ImageOps
import numpy as np
import pyautogui
import time
import cv2
import csv
import os
import shutil  # For copying files

Log = Log()

def multi_scaling(screenshot_gray, target_image, scales=np.linspace(0.5, 2.0, 20), threshold=.75):
    best_match = None
    best_scale = None
    best_val = 0

    for scale in scales:
        # Resize the target image for the current scale
        resized_template = cv2.resize(target_image, (0, 0), fx=scale, fy=scale)

        # Perform template matching with the resized template
        result = cv2.matchTemplate(screenshot_gray, resized_template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        # Check if the match is above the threshold and if it's the best match so far
        if max_val >= threshold and max_val > best_val:
            best_match = (min_loc, resized_template.shape[1], resized_template.shape[0])
            best_val = max_val
            best_scale = scale

    if best_match:
        top_left = best_match[0]
        width, height = best_match[1], best_match[2]
        bottom_right = (top_left[0] + width, top_left[1] + height)
        return top_left, bottom_right, best_scale, best_val
    else:
        return None, None, None, None

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

def analyze(target_img_path,
            coord_logs_path,
            screenshot_path="latest_screenshot.png",
            optimize_region=None,
            mouse_following=True,
            limit_optimizer=20,
            match_threshold=0.75,
            use_img_scaling=True,
            debugger=False
            ):

    # Take Screenshot
    screenshot = pyautogui.screenshot()

    # Crop screenshot if optimize_region is provided
    if optimize_region:
        x, y, width, height = optimize_region
        screenshot = screenshot.crop((x, y, x + width, y + height))

    if debugger:
        # Save the full screenshot for debugging (before matching)
        debug_screenshot_path = screenshot_path.replace(".png", "_debug.png")
        screenshot.save(debug_screenshot_path)
        print(f"    Debug screenshot saved to {debug_screenshot_path}")

        # Save a copy of the target image being used
        target_img_copy_path = screenshot_path.replace(".png", "_target_copy.png")
        shutil.copy(target_img_path, target_img_copy_path)
        print(f"    Target image copy saved to {target_img_copy_path}")

    # Convert screenshot to grayscale for matching
    screenshot_np = np.array(screenshot)
    screenshot_gray = cv2.cvtColor(screenshot_np, cv2.COLOR_BGR2GRAY)

    # Load Target Image
    target_image = cv2.imread(target_img_path, 0)
    if target_image is None:
        print(f"Target image {target_img_path} not found!")
        return None

    # Use either multi-scale or single-scale template matching based on parameter
    if use_img_scaling:
        top_left, bottom_right, best_scale, best_val = multi_scaling(screenshot_gray, target_image, threshold=match_threshold)
    else:
        top_left, bottom_right, best_scale, best_val = single_scaling(screenshot_gray, target_image, threshold=match_threshold)

    # If a match is found, crop the screenshot to the matched region
    if top_left is not None:
        cropped_screenshot = screenshot.crop((top_left[0], top_left[1], bottom_right[0], bottom_right[1]))

        # Save the cropped screenshot
        mode = "multi_scale" if use_img_scaling else "single_scale"
        cropped_screenshot_path = f"cropped_screenshot_{mode}.png"
        cropped_screenshot.save(cropped_screenshot_path)
        print(f"    Cropped screenshot saved to {cropped_screenshot_path}")

        h, w = bottom_right[1] - top_left[1], bottom_right[0] - top_left[0]

        # Adjust to Screen Size
        if optimize_region:
            top_left = (top_left[0] + optimize_region[0], top_left[1] + optimize_region[1])
            bottom_right = (bottom_right[0] + optimize_region[0], bottom_right[1] + optimize_region[1])

        # Log Coordinates
        with open(coord_logs_path, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([top_left, bottom_right])

        # Move Mouse
        if mouse_following:
            center_x = top_left[0] + w // 2
            center_y = top_left[1] + h // 2
            pyautogui.moveTo(center_x, center_y)

        print(f"    Match found at scale {best_scale} with confidence {best_val}. Coordinates logged to {coord_logs_path}.")

        # Log Limiter
        Log.limit(max_entries=limit_optimizer)

        return [top_left, bottom_right]
    else:
        # If no match is found, still save the screenshot with a "no_match" suffix
        no_match_screenshot_path = screenshot_path.replace(".png", "_no_match.png")
        screenshot.save(no_match_screenshot_path)
        print(f"    No match found. Screenshot saved to {no_match_screenshot_path}")

        return None

def click(top_left, bottom_right):
    # Calculate Center
    center_x = top_left[0] + (bottom_right[0] - top_left[0]) // 2
    center_y = top_left[1] + (bottom_right[1] - top_left[1]) // 2

    # Click
    pyautogui.moveTo(center_x, center_y)
    pyautogui.click()

def main():
    current_time: str = time.strftime("%H:%M:%S")
    i: int = 0
    print(f"[ Locator Starting @ {time.strftime("%Y-%m-%d")} ]")
    while True:
        i += 1
        # Get the current time and format it
        print(f"\n[ {i} | {current_time} ]")

        # Analyze Match and save a screenshot each time
        coordinates: list = analyze(
            target_img_path='../images/EasyApply.png',
            coord_logs_path='../config/coordinate_log.csv',
            screenshot_path='latest_screenshot.png',
            optimize_region=None,  # (x, y, width, height)
            mouse_following=False, # Boolean
            limit_optimizer=50,    # Integer
            match_threshold=0.8,   # Integer: (0-1)
            use_img_scaling=False,  # Set to False to disable scale matching
            debugger=False
        )

        # Optional: Screening Optimization
        Log.optimize()

        # click(coordinates[0], coordinates[1]) if coordinates else None

        # Iteration Interval
        time.sleep(5)

if __name__ == "__main__":
    main()
