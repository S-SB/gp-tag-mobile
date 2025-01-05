![GP-Tag Overview](docs/images/social-preview-mobile.png)

# GP-Tag Mobile

GP-Tag Mobile is a mobile implementation of GP-Tag detection and encoding for Android devices.

## Related Repositories
- [GP-Tag](https://github.com/S-SB/gp-tag) - Core GP-Tag implementation and documentation
- [GP-Tag ROS2](https://github.com/S-SB/gp-tag-ros2) - ROS2 implementation for robotics integration
- [GP-Tag Mobile](https://github.com/S-SB/gp-tag-mobile) - This repository

## Author
S. E. Sundén Byléhn

## License
MIT License. See [LICENSE](LICENSE) file for details.

## Installation

### Prerequisites
1. Install Pydroid 3 from the Google Play Store
2. Install required Pydroid plugins:
   - Pydroid Repository Plugin
   - Pydroid Permissions Plugin

### Dependencies
In Pydroid's Terminal or Pip interface, install:

pip install numpy
pip install opencv-python
pip install reedsolo
pip install kivy

## Usage

### Tag Detection
1. Place all decoder files in a single directory:
   - annuli_decoder.py
   - data_decoder.py
   - finder_decoder.py
   - mobile_detector.py
   - sift_detector.py
   - spike_detector.py
   - tag3_blank_360.png

2. Open `mobile_detector.py` in Pydroid
3. Run the script to start the camera feed and tag detection

### Tag Creation
The tag generator provides two methods for creating tags:
1. Manual data input through a GUI interface
2. Optional automatic generation using phone's GPS and IMU sensors (note: altitude sensing is currently disabled due to GPS altitude inaccuracy)

To use the tag generator:
1. Place the tag generator script in your working directory
2. If you plan to use sensor data, ensure you grant location permissions in Android settings
3. Run the script to open the GUI interface
4. Enter tag parameters manually or use the "Use Sensors" button to automatically populate position and orientation
5. Click "Generate" to preview the tag
6. Click "Save" to save the tag as a PNG file

## Components
- `mobile_detector.py`: Main UI and camera handling
- `sift_detector.py`: Core SIFT-based tag detection
- `spike_detector.py`: Corner detection refinement
- `finder_decoder.py`: Pattern validation
- `annuli_decoder.py`: Rotation detection
- `data_decoder.py`: Data extraction
- `tag3_blank_360.png`: SIFT reference template

## Troubleshooting
- Ensure camera permissions are granted in Android settings
- If getting import errors, verify all files are in the same directory
- Check Pydroid's terminal for specific error messages
- For sensor usage in tag generation, ensure location permissions are granted

## Contributing
Please see the main GP-Tag repository for contribution guidelines.

## Citation
If you use GP-Tag in your research, please cite:

@misc{gptag2025,
  author = {Sundén Byléhn, S. E.},
  title = {GP-Tag: A Universal Fiducial Marker Framework},
  year = {2025},
  publisher = {GitHub},
  url = {https://github.com/S-SB/gp-tag}
}