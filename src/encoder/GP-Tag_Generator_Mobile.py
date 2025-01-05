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

import io
import os
import math
import random

from kivy.app import App
from kivy.core.window import Window
from kivy.core.image import Image as CoreImage
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.utils import platform

# Replace with your real import:
from tag_encoder import create_fiducial_marker

# For Android GPS and sensors
if platform == 'android':
    from plyer import gps, accelerometer, gyroscope, gravity


def euler_to_quaternion(roll, pitch, yaw):
    """
    Convert Euler angles to quaternion using NED (North-East-Down) convention.
    
    NED coordinate system:
    - X axis points North
    - Y axis points East
    - Z axis points Down (into the ground)
    
    At 0,0,0:
    - The tag is flat (like lying on a table)
    - The tag's right side points North (+X)
    - The tag's bottom side points East (+Y)
    - The Z axis points downward, so the tag face is up
    """
    roll = math.radians(roll)
    pitch = math.radians(pitch)
    yaw = math.radians(yaw)
    
    cy = math.cos(yaw * 0.5)
    sy = math.sin(yaw * 0.5)
    cp = math.cos(pitch * 0.5)
    sp = math.sin(pitch * 0.5)
    cr = math.cos(roll * 0.5)
    sr = math.sin(roll * 0.5)
    
    qw = cr * cp * cy + sr * sp * sy
    qx = sr * cp * cy - cr * sp * sy
    qy = cr * sp * cy + sr * cp * sy
    qz = cr * cp * sy - sr * sp * cy
    
    return [qx, qy, qz, qw]


class GPTagGeneratorApp(App):
    """
    A mobile application for generating GP-Tag fiducial markers using the NED convention.
    
    Features:
    - Manual or automatic (sensor) input for position & orientation
    - Tag preview & saving (no share)
    - NED coordinate system, default (roll=0, pitch=0, yaw=0) means:
      Tag is flat on a table, right side = North(+X), bottom side = East(+Y), face up
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sensors_enabled = False
        self.sensor_update_event = None
        self.tag_image = None
        self.current_tag_path = None
        self.current_yaw = 0.0  # internal yaw for sensor updates

    def build(self):
        # Outer layout
        root_layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(5))

        # ScrollView that contains everything: reference text + fields
        scroll = ScrollView(size_hint=(1, 1))
        scroll_content = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(10))
        scroll_content.bind(minimum_height=scroll_content.setter('height'))

        # Orientation explanation text at the top
        info_label = Label(
            text=(
                "[b]NED (North-East-Down) Reference[/b]\n\n"
                "In the NED frame:\n"
                "- X axis points North\n"
                "- Y axis points East\n"
                "- Z axis points Down\n\n"
                "Default Orientation (0,0,0):\n"
                "- Tag lies flat on a surface\n"
                "- Right side = North (+X)\n"
                "- Bottom side = East (+Y)\n"
                "- Tag face is up (Z axis down)\n\n"
                "Altitude with Use Sensor is disabled for now.\n"
                "(GPS often doesn't provide valid altitude.)"
            ),
            markup=True,
            halign='left',
            valign='top',
            size_hint_y=None
        )
        # Let the label expand as needed
        info_label.bind(texture_size=info_label.setter('size'))
        info_label.text_size = (Window.width - dp(20), None)

        scroll_content.add_widget(info_label)

        # The input fields in a 2-column GridLayout
        field_grid = GridLayout(cols=2, spacing=dp(5), size_hint_y=None, padding=dp(5))
        field_grid.bind(minimum_height=field_grid.setter('height'))

        # Including resolution "U" below
        fields = [
            ("Latitude",   "-90..+90",      "63.8203894", "Latitude in degrees\nRange: -90 to +90"),
            ("Longitude",  "-180..+180",    "20.3058847", "Longitude in degrees\nRange: -180 to +180"),
            ("Altitude",   "-10000..10000", "45.16",      "Altitude in meters (manual)"),
            ("Roll",       "X rotation",    "0",          "Rotation around X (North) axis"),
            ("Pitch",      "Y rotation",    "0",          "Rotation around Y (East) axis"),
            ("Yaw",        "Z rotation",    "0",          "Rotation around Z (Down) axis"),
            ("Tag Size",   "mm",            "100",        "Physical size of the tag in mm"),
            ("Accuracy",   "0..3",          "2",          "0=Low,1=Med,2=High,3=Ultra"),
            ("Tag ID",     "0..4095",       "123",        "Unique tag identifier"),
            ("Version",    "0..15",         "3",          "Tag format version"),
            ("Resolution", "U value",       "40",         "Pixels per cell (36U×36U)")
        ]

        for label_text, hint_text, default_text, help_text in fields:
            field_layout = self.add_input_field(label_text, hint_text, default_text, help_text)
            field_grid.add_widget(field_layout)

        scroll_content.add_widget(field_grid)
        scroll.add_widget(scroll_content)
        root_layout.add_widget(scroll)

        # Button row
        btn_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), spacing=dp(5))

        self.use_sensors_btn = Button(text='Use Sensors', on_press=self.toggle_sensors)
        self.generate_btn = Button(text='Generate', on_press=self.generate_tag)
        self.save_btn = Button(text='Save', on_press=self.save_tag)
        # No share button

        btn_box.add_widget(self.use_sensors_btn)
        btn_box.add_widget(self.generate_btn)
        btn_box.add_widget(self.save_btn)
        root_layout.add_widget(btn_box)

        # Tag preview
        self.preview = Image(size_hint_y=None, height=dp(200))
        root_layout.add_widget(self.preview)

        # Status label at bottom
        self.status_label = Label(text='Ready', size_hint_y=None, height=dp(30))
        root_layout.add_widget(self.status_label)

        # Initialize sensors, but do not actually start them
        if platform == 'android':
            self.init_sensors()

        return root_layout

    def add_input_field(self, label_text, hint_text, default_text, help_text):
        """
        Return a horizontal BoxLayout containing a Label and TextInput with a tooltip on press.
        """
        input_layout = BoxLayout(orientation='horizontal', spacing=dp(5), size_hint_y=None, height=dp(50))

        label = Label(
            text=label_text,
            size_hint_x=0.4,
            halign='right',
            valign='middle'
        )
        label.bind(size=label.setter('text_size'))

        text_input = TextInput(
            text=default_text,
            hint_text=hint_text,
            multiline=False,
            size_hint_x=0.6,
            height=dp(40),
            padding=[dp(5), dp(5)]
        )

        def on_touch_down(instance, touch):
            if text_input.collide_point(*touch.pos):
                self.show_tooltip(text_input, help_text)
        text_input.bind(on_touch_down=on_touch_down)

        input_layout.add_widget(label)
        input_layout.add_widget(text_input)

        # Store the text input as an attribute
        attr_name = label_text.lower().replace(" ", "_") + "_input"
        setattr(self, attr_name, text_input)

        return input_layout

    def show_tooltip(self, widget, text):
        """
        Show a popup with help text.
        """
        popup = Popup(
            title='Help',
            content=Label(text=text),
            size_hint=(0.8, None),
            height=dp(200)
        )
        popup.open()

    def init_sensors(self):
        """
        Prepares GPS and motion sensors. Must request location permissions externally if needed.
        """
        gps.configure(on_location=self.on_gps_location)
        accelerometer.enable()
        gyroscope.enable()
        gravity.enable()

    def toggle_sensors(self, instance):
        """
        Turn sensor usage ON/OFF. If ON, we schedule updates for orientation & GPS.
        """
        self.sensors_enabled = not self.sensors_enabled
        if self.sensors_enabled:
            self.use_sensors_btn.background_color = (0, 1, 0, 1)  # green
            self.use_sensors_btn.text = "Sensors ON"
            self.status_label.text = "Sensors enabled"
            try:
                gps.start()  # Might fail if no permission
            except Exception as e:
                self.status_label.text = f"GPS start error: {e}"

            # Update orientation 2x/sec
            self.sensor_update_event = Clock.schedule_interval(self.update_orientation, 0.5)
        else:
            self.use_sensors_btn.background_color = (1, 1, 1, 1)
            self.use_sensors_btn.text = "Use Sensors"
            self.status_label.text = "Sensors disabled"
            try:
                gps.stop()
            except:
                pass

            if self.sensor_update_event:
                self.sensor_update_event.cancel()
                self.sensor_update_event = None

    def on_gps_location(self, **kwargs):
        """
        Called when GPS location changes. Updates lat/lon fields if sensors are ON.
        Ignores altitude (since it's usually inaccurate).
        """
        if not self.sensors_enabled:
            return

        def update_fields(dt):
            if 'lat' in kwargs and 'lon' in kwargs:
                self.latitude_input.text = str(kwargs['lat'])
                self.longitude_input.text = str(kwargs['lon'])
            # Not setting altitude, because it's typically inaccurate

        Clock.schedule_once(update_fields)

    def update_orientation(self, dt):
        """
        Poll gravity and gyroscope for orientation.  
        pitch is negated; yaw is displayed as negative of the integrated z_gyro.
        """
        if not self.sensors_enabled:
            return

        try:
            # Gravity => roll/pitch
            g_data = gravity.gravity
            # Gyro => approximate yaw changes
            gyro_data = gyroscope.rotation

            if g_data:
                xg, yg, zg = g_data
                roll = math.degrees(math.atan2(yg, zg))
                pitch = math.degrees(math.atan2(-xg, math.sqrt(yg*yg + zg*zg)))
                pitch = -pitch
                self.roll_input.text = f"{roll:.3f}"
                self.pitch_input.text = f"{pitch:.3f}"

            if gyro_data:
                x_gyro, y_gyro, z_gyro = gyro_data
                # Integrate Z rotation
                self.current_yaw += (z_gyro * dt * 180 / math.pi)
                # Keep yaw in [-180..180]
                self.current_yaw = ((self.current_yaw + 180) % 360) - 180
                # Display negative
                display_yaw = -self.current_yaw
                self.yaw_input.text = f"{display_yaw:.3f}"

            self.status_label.text = 'Sensors updating...'
        except Exception as e:
            self.status_label.text = f'Sensor error: {e}'

    def create_tag_image(self):
        """
        Build the fiducial marker from input fields. Returns a Pillow Image or None on error.
        """
        try:
            latitude = float(self.latitude_input.text)
            longitude = float(self.longitude_input.text)
            altitude = float(self.altitude_input.text)
            roll = float(self.roll_input.text)
            pitch = float(self.pitch_input.text)
            yaw = float(self.yaw_input.text)
            tag_size = float(self.tag_size_input.text)
            accuracy = int(self.accuracy_input.text)
            tag_id = int(self.tag_id_input.text)
            version = int(self.version_input.text)
            resolution = int(self.resolution_input.text)

            quaternion = euler_to_quaternion(roll, pitch, yaw)
            scale = 36 / tag_size  # 36 cells = tag_size mm

            return create_fiducial_marker(
                latitude, longitude, altitude,
                quaternion, scale, accuracy,
                tag_id, version, U=resolution
            )
        except Exception as e:
            self.status_label.text = f"Error: {str(e)}"
            return None

    def generate_tag(self, instance):
        """
        Generate the tag & show a preview (does not save to disk).
        """
        tag_img = self.create_tag_image()
        if not tag_img:
            return

        self.tag_image = tag_img
        buf = io.BytesIO()
        tag_img.save(buf, format='PNG')
        buf.seek(0)
        core_img = CoreImage(buf, ext='png')
        self.preview.texture = core_img.texture
        self.status_label.text = "Tag generated (preview)"

    def save_tag(self, instance):
        """
        Saves the PNG to the local script directory.
        """
        if not self.tag_image:
            self.tag_image = self.create_tag_image()
            if not self.tag_image:
                return

        filename = f"gptag_{self.tag_id_input.text}.png"
        try:
            self.tag_image.save(filename)
            self.current_tag_path = os.path.abspath(filename)
            self.status_label.text = f"Saved as {self.current_tag_path}"
        except Exception as e:
            self.status_label.text = f"Error saving: {e}"

    def on_stop(self):
        """
        Clean up sensors if on Android.
        """
        if platform == 'android':
            if self.sensors_enabled:
                try:
                    gps.stop()
                except:
                    pass
            accelerometer.disable()
            gyroscope.disable()
            gravity.disable()


if __name__ == '__main__':
    GPTagGeneratorApp().run()
