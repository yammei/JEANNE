import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
import json
import os
import csv

class Log:
    def __init__(self) -> None:
        self.CSV_PATH: str = "../config/coordinate_log.csv"

    def remove_outliers(self, values):
        """Removes outliers based on the IQR method."""
        mult = 3.0 # Default: 1.5 | NOTE: Keep it within .5 - 3.0
        q1 = np.percentile(values, 25)
        q3 = np.percentile(values, 75)
        iqr = q3 - q1
        lower_bound = q1 - mult * iqr
        upper_bound = q3 + mult * iqr
        return [v for v in values if lower_bound <= v <= upper_bound]

    def optimize(self) -> None:
        if not os.path.exists(self.CSV_PATH):
            print(f"{self.CSV_PATH} not found. No averaging needed.")
            return None, None

        sum_x1, sum_y1, sum_x2, sum_y2 = 0, 0, 0, 0
        num_entries = 0
        coord_pair = []
        x1_vals, y1_vals, x2_vals, y2_vals = [], [], [], []

        # Read Log
        with open(self.CSV_PATH, mode='r') as file:
            reader = csv.reader(file)
            for row in reader:
                if len(row) < 2:
                    continue

                # Analyze Coordinates
                x1, y1 = eval(row[0])
                x2, y2 = eval(row[1])
                center_x = (x1 + x2) / 2
                center_y = (y1 + y2) / 2

                # Append both the center point and the bounding box to the list
                coord_pair.append(((center_x, center_y), ((x1, y1), (x2, y2))))

                # Store values for variance and outlier removal
                x1_vals.append(x1)
                y1_vals.append(y1)
                x2_vals.append(x2)
                y2_vals.append(y2)

                sum_x1 += x1
                sum_y1 += y1
                sum_x2 += x2
                sum_y2 += y2
                num_entries += 1

        if num_entries == 0:
            print("No valid entries found in the CSV.")
            return None, None

        # Remove outliers using the IQR method
        x1_vals_filtered = self.remove_outliers(x1_vals)
        y1_vals_filtered = self.remove_outliers(y1_vals)
        x2_vals_filtered = self.remove_outliers(x2_vals)
        y2_vals_filtered = self.remove_outliers(y2_vals)

        # Calculate the averages of filtered values
        avg_x1 = np.mean(x1_vals_filtered)
        avg_y1 = np.mean(y1_vals_filtered)
        avg_x2 = np.mean(x2_vals_filtered)
        avg_y2 = np.mean(y2_vals_filtered)

        # Calculate variance of the filtered coordinates
        var_x1 = np.var(x1_vals_filtered)
        var_y1 = np.var(y1_vals_filtered)
        var_x2 = np.var(x2_vals_filtered)
        var_y2 = np.var(y2_vals_filtered)

        # Adjust width and height based on variance
        variance_factor = 2  # You can tune this factor to control how much variance affects the box size
        width = (avg_x2 - avg_x1) + variance_factor * np.sqrt(var_x2)
        height = (avg_y2 - avg_y1) + variance_factor * np.sqrt(var_y2)

        # Adjust top-left coordinates by variance for more coverage
        adjusted_x1 = avg_x1 - variance_factor * np.sqrt(var_x1)
        adjusted_y1 = avg_y1 - variance_factor * np.sqrt(var_y1)

        # Save Optimized Coordinates as optimize_region (x, y, width, height)
        optimized_coordinates = {
            "analyze": {
                "optimize_region": [adjusted_x1, adjusted_y1, width, height]
            }
        }

        with open('automation_config.json', mode='w') as json_file:
            json.dump(optimized_coordinates, json_file, indent=4)

        print(f"    Optimized coordinates saved to 'automation_config.json': {optimized_coordinates}")

        return optimized_coordinates, coord_pair

    def encapsulate(self, match_coords):
        x_min = min([coord[0][0] for coord in match_coords])  # Minimum x1 (top-left)
        y_min = min([coord[0][1] for coord in match_coords])  # Minimum y1 (top-left)
        x_max = max([coord[1][0] for coord in match_coords])  # Maximum x2 (bottom-right)
        y_max = max([coord[1][1] for coord in match_coords])  # Maximum y2 (bottom-right)
        return (x_min, y_min), (x_max, y_max)


    def visualize(self, coord_pair, avg_coords, screen_width: int=1920, screen_height: int=1080):
        fig, ax = plt.subplots(figsize=(10, 6))

        for (center_x, center_y), (top_left, bottom_right) in coord_pair:
            if 0 <= center_x < screen_width and 0 <= center_y < screen_height:
                x1, y1 = top_left
                x2, y2 = bottom_right

                width = x2 - x1
                height = y2 - y1

                rect = patches.Rectangle((x1, y1), width, height, linewidth=1, edgecolor='blue', facecolor='none')
                ax.add_patch(rect)

        avg_x1, avg_y1 = avg_coords["top_left"]
        avg_x2, avg_y2 = avg_coords["bottom_right"]

        avg_width = avg_x2 - avg_x1
        avg_height = avg_y2 - avg_y1

        avg_rect = patches.Rectangle((avg_x1, avg_y1), avg_width, avg_height, linewidth=2, edgecolor='red', facecolor='none')
        ax.add_patch(avg_rect)

        plt.title("Coordinates with Bounding Boxes and Average Hit Area")
        plt.xlabel("Screen Width")
        plt.ylabel("Screen Height")

        handles = [
            patches.Patch(edgecolor='blue', facecolor='none', label='Hit Areas'),
            patches.Patch(edgecolor='red', facecolor='none', label='Average Hit Area')
        ]
        plt.legend(handles=handles, loc="upper right")

        ax.set_xlim(0, screen_width)
        ax.set_ylim(screen_height, 0)

        plt.show()

    def limit(self, max_entries: int):
        if os.path.exists(self.CSV_PATH):
            with open(self.CSV_PATH, mode='r') as file:
                lines = list(csv.reader(file))

            if len(lines) > max_entries:
                lines = lines[-max_entries:]

            with open(self.CSV_PATH, mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerows(lines)
