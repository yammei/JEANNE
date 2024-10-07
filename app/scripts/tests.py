from main import analyze
from optimizer import Log
import time

Log = Log()

def test(location: bool=False, optimize: bool=False, visualize: bool=False, scans: int=30, delay: int=5, limit_coordinate_fit: int=20) -> None:
    # Ensure limit_coordinate_fit is less than or equal to scans
    if limit_coordinate_fit > scans:
        print(f"Number of <scans> must be equal or higher than <limit_coordinate_fit>.")
        return

    print(f"Starting test automation in 5 seconds ...")
    print(f"    ├─ Optimizer Tests = {optimize}")
    print(f"           └─ Visualize Results = {visualize}")
    print(f"    └─ Locator Tests = {location}")
    print(f"           └─ Execution Interval = {delay}")

    time.sleep(5)

    # Optimize coordinates test
    if optimize:
        # Calculate the average coordinates and read all logged coordinates
        print(f"\nInitial Coordinate Optimization...")
        average_data, coordinates_with_boxes = Log.optimize()
        if average_data and coordinates_with_boxes:
            # Extract the average bounding box from the average data
            avg_coords = average_data["analyze"]["optimize_region"]  # This is a list [x, y, width, height]

            # Extract values from the list
            avg_x1, avg_y1 = avg_coords[0], avg_coords[1]  # Top-left corner
            avg_x2, avg_y2 = avg_x1 + avg_coords[2], avg_y1 + avg_coords[3]  # Bottom-right corner

            # Optionally visualize the coordinates if requested
            if visualize:
                Log.visualize(
                    coord_pair=coordinates_with_boxes,
                    avg_coords={"top_left": (avg_x1, avg_y1), "bottom_right": (avg_x2, avg_y2)},
                    screen_width=2560,
                    screen_height=1440
                )

    # Locate test
    if location:
        for i in range(scans):
            print(f"\n[{i} of {scans}]")

            # Locate the image and log the coordinates
            coordinates: any = analyze(
                target_img_path='../images/EasyApply.png',
                coord_logs_path='../config/coordinate_log.csv',
                screenshot_path='latest_screenshot.png',
                optimize_region=None,  # (x, y, width, height)
                mouse_following=False, # Boolean
                limit_optimizer=limit_coordinate_fit,    # Integer
                match_threshold=0.8,   # Integer: (0-1)
                use_img_scaling=False,  # Set to False to disable scale matching
                debugger=False
            )

            # Calculate the average of the existing coordinates in the CSV
            if optimize and coordinates:
                average_data, coordinates_with_boxes = Log.optimize()
                if average_data and coordinates_with_boxes:
                    print(f"    Average coordinates: {average_data}")

            # Sleep for the specified execution interval between scans
            time.sleep(delay)

    # Limit the number of log entries in the CSV file to limit_coordinate_fit
    Log.limit(max_entries=limit_coordinate_fit)

    print("Tests Complete.")

# Example of how to call the test function
if __name__ == "__main__":

    test(location=True,
         optimize=True,
         visualize=True,
         scans=30,
         delay=5,
         limit_coordinate_fit=20)
