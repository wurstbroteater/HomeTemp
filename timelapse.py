import cv2
import os
from datetime import datetime

image_folder = './pictures'
output_video = 'timelapse.mp4'
fps = 2
# List to store the image file paths
image_files = []

for filename in os.listdir(image_folder):
    if filename.endswith(".png"):
        # Parse the date from the filename and add to the list
        try:
            datetime.strptime(str(filename).replace(".png",""), '%Y-%m-%d-%H:%M:%S') 
            image_files.append(os.path.join(image_folder, filename))
        except ValueError:
            print(f"Skipping file: {filename}, invalid date format")
    

# Sort the images based on the timestamp in the filename
image_files.sort()

# Read the first image to get the dimensions
if len(image_files) > 0:
    frame = cv2.imread(image_files[0])
    height, width, layers = frame.shape

    # Define codec and create VideoWriter 
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video = cv2.VideoWriter(output_video, fourcc, fps, (width, height))

    # Write each image frame to the video
    for image_file in image_files:
        img = cv2.imread(image_file)
        video.write(img)

    video.release()

    print(f"Timelapse video saved as {output_video}")
else:
    print("No valid images found.")
