"""
MIT License

Copyright (c) 2025 S. E. Sundén Byléhn

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.graphics.texture import Texture
import cv2
import numpy as np
from sift_detector import SIFTDetector6DoF

def quaternion_to_euler_NegY(q: np.ndarray) -> np.ndarray:
    """
    Convert quaternion to Euler angles in Y-down frame.
    
    Args:
        q: Quaternion in [x, y, z, w] format
        
    Returns:
        Euler angles [roll, pitch, yaw] in degrees
        Roll: Rotation around X
        Pitch: Negative rotation around Y
        Yaw: Rotation around Z
    """
    sinr_cosp = 2 * (q[3] * q[0] + q[1] * q[2])
    cosr_cosp = 1 - 2 * (q[0] * q[0] + q[1] * q[1])
    roll = np.arctan2(sinr_cosp, cosr_cosp)

    sinp = 2 * (q[3] * q[1] - q[2] * q[0])
    if abs(sinp) >= 1:
        pitch = np.sign(sinp) * np.pi / 2
    else:
        pitch = np.arcsin(sinp)

    siny_cosp = 2 * (q[3] * q[2] + q[0] * q[1])
    cosy_cosp = 1 - 2 * (q[1] * q[1] + q[2] * q[2])
    yaw = np.arctan2(siny_cosp, cosy_cosp)

    return np.array([np.degrees(roll),
                    np.degrees(-pitch),
                    np.degrees(yaw)])

class TagDetectorApp(App):
    """
    Mobile application for real-time tag detection using device camera.
    
    Uses Kivy for UI and OpenCV for camera access and image processing.
    Displays camera feed with detection overlays and tag information.
    """
    
    def build(self):
        """
        Set up the application UI layout.
        
        Creates:
        - Full-screen camera preview
        - Status label showing detection results
        - Camera capture at 1080p resolution
        - SIFT detector with calibrated camera parameters
        
        Returns:
            Root layout widget
        """
        self.layout = BoxLayout(orientation='vertical')
        
        self.img = Image()
        self.layout.add_widget(self.img)
        
        self.status_label = Label(
            text='Starting...',
            size_hint_y=0.4,
            halign='left',
            valign='top',
            text_size=(None, None),
            padding=(10, 10)
        )
        self.layout.add_widget(self.status_label)
        
        self.capture = cv2.VideoCapture(0)
        if self.capture.isOpened():
            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
            
        self.last_process_time = 0
        self.process_interval = 1.0
        
        self.detector = SIFTDetector6DoF()
        self.camera_matrix = np.array([
            [1344, 0, 960],
            [0, 1344, 540],
            [0, 0, 1]
        ])
        self.dist_coeffs = np.zeros(5)
        
        Clock.schedule_interval(self.update, 1.0 / 30.0)
        
        return self.layout
    
    def update(self, dt):
        """
        Process camera frame and update UI.
        
        Performs:
        1. Capture camera frame
        2. Run tag detection (at specified interval)
        3. Draw detection results
        4. Update display and status
        
        Args:
            dt: Time delta from Kivy clock
        """
        ret, frame = self.capture.read()
        if not ret:
            return
            
        current_time = Clock.get_time()
        
        # Convert frame color for display
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_display = frame_bgr.copy()
        
        if current_time - self.last_process_time > self.process_interval:
            detection = self.detector.detect(
                image=frame_bgr,
                camera_matrix=self.camera_matrix,
                dist_coeffs=self.dist_coeffs
            )
            
            if detection:
                corners = np.array(detection['corners'], dtype=np.int32)
                for i in range(4):
                    cv2.line(frame_display, 
                            tuple(corners[i]), 
                            tuple(corners[(i+1)%4]), 
                            (0, 255, 0), 2)
                
                center = np.mean(corners, axis=0).astype(int)
                cv2.circle(frame_display, tuple(center), 5, (255, 0, 0), -1)
                
                euler_angles = quaternion_to_euler_NegY(np.array(detection['rotation']))
                roll, pitch, yaw = euler_angles
                pos_x, pos_y, pos_z = detection['position']
                
                # Corrected data access
                tag_data = detection.get('tag_data', {})
                tag_id = tag_data.get('tag_id', 'N/A')
                version = tag_data.get('version_id', 'N/A')
                scale = tag_data.get('scale', 0)
                lat = tag_data.get('latitude', 0)  # Corrected
                long = tag_data.get('longitude', 0)  # Corrected
                alt = tag_data.get('altitude', 0)  # Added altitude
                
                info_lines = [
                    f"Processing: {detection['detection_time_ms']:.0f}ms",
                    f"Tag ID: {tag_id}, Version: {version}",
                    f"6-DoF Pose:",
                    f"  Roll: {roll:.1f}°",
                    f"  Pitch: {pitch:.1f}°",
                    f"  Yaw: {yaw:.1f}°",
                    f"Position (m):",
                    f"  X: {pos_x:.3f}",
                    f"  Y: {pos_y:.3f}",
                    f"  Z: {pos_z:.3f}",
                    f"Tag Info:",
                    f"  Scale: {scale:.2f}mm",
                    f"  Lat: {lat:.6f}°",
                    f"  Long: {long:.6f}°",
                    f"  Alt: {alt:.1f}m"
                ]
                self.status_label.text = '\n'.join(info_lines)
                self.last_process_time = current_time
            else:
                self.status_label.text = "No tag detected\nSearching..."

        # Update display
        buf = cv2.flip(frame_display, 0).tobytes()
        texture = Texture.create(
            size=(frame_display.shape[1], frame_display.shape[0]), 
            colorfmt='rgb'
        )
        texture.blit_buffer(buf, colorfmt='rgb', bufferfmt='ubyte')
        self.img.texture = texture

    def on_stop(self):
        """Clean up resources when application closes."""
        self.capture.release()

if __name__ == '__main__':
    TagDetectorApp().run()