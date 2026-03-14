import cv2
import numpy as np

cap = cv2.VideoCapture(1)

# Calibration: How many centimeters is 1 pixel at this distance?
# You need to measure this once: (Real Height / Pixel Height)
CM_PER_PIXEL = 0.15  # Example: 1 pixel = 0.15cm

# Define where the 'surface' is in the image (Y-coordinate)
surface_y = 400 

while True:
    ret, frame = cap.read()
    if not ret: break

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    
    # Red mask (same as your code)
    mask = cv2.inRange(hsv, np.array([0, 120, 70]), np.array([10, 255, 255])) + \
           cv2.inRange(hsv, np.array([170, 120, 70]), np.array([180, 255, 255]))
    
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Draw Surface Line
    cv2.line(frame, (0, surface_y), (frame.shape[1], surface_y), (255, 255, 0), 2)
    cv2.putText(frame, "SURFACE", (10, surface_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)

    if contours:
        largest_cnt = max(contours, key=cv2.contourArea)
        if cv2.contourArea(largest_cnt) > 500:
            M = cv2.moments(largest_cnt)
            if M["m00"] != 0:
                cX = int(M["m10"] / M["m00"])
                cY = int(M["m01"] / M["m00"])

                # Calculate height above surface line
                # Note: In OpenCV, Y increases downwards, so (Surface - Object) = Height
                pixel_height = surface_y - cY
                real_height = pixel_height * CM_PER_PIXEL

                # UI Feedback
                color = (0, 255, 0) if pixel_height > 0 else (0, 0, 255)
                cv2.circle(frame, (cX, cY), 10, color, -1)
                cv2.line(frame, (cX, cY), (cX, surface_y), (255, 255, 255), 1)
                
                label = f"Height: {real_height:.1f} cm"
                cv2.putText(frame, label, (cX + 15, cY), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

    cv2.imshow("Height Tracker", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()