# Ping Pong Robot

Camera-guided ping pong turret: live video, object segmentation and calibrated distance measurement. **Work in progress.**

## Demo

A recorded demonstration of the current application is pending. The implemented workflow is: click to freeze a frame, segment a selected object, and overlay its pixel dimensions or estimated distance.

## Current components

| Component | Current implementation | Planned work |
| --- | --- | --- |
| Vision | Live/recorded video, frozen-frame selection, OpenCV GrabCut and optional MobileSAM segmentation. | Validate the refactored application on the phone-camera setup. |
| Brain | Known-height distance measurement, resolution checks and local measurement logs. | Recalibrate and publish independent validation trials. |
| Controller | Not implemented. | Microcontroller integration; board selection pending. |
| Hardware | Not implemented. | Pan-tilt mechanism and ball launcher. |

The current software measures manually selected known objects. Continuous ball tracking, aiming and launching remain planned. See the [roadmap](ROADMAP.md) and [architecture](docs/architecture.md).

## Results

Camera-validation results for the refactored application are pending. The example uses **1920 × 1080** and an **unverified 1390 px** focal-length starting value; recalibrate before relying on its distances. No camera-accuracy percentage or operating range is established. See the [experiment records](docs/experiments.md) and [calibration guide](docs/calibration.md).

The repository includes offline tests for measurement arithmetic, coordinate mapping, stale frames, MJPEG handling and a synthetic GrabCut pipeline. Run them with `python -m unittest discover -s tests -v`; see [testing](docs/testing.md) for the remaining physical checks.

## Getting started

Requires **Python 3.11+** and a desktop display. These steps use Windows PowerShell.

1. Clone the repository and enter its directory:

   ```powershell
   git clone https://github.com/Gonenza9090/Ping-Pong-Robot.git
   cd Ping-Pong-Robot
   ```

2. Install dependencies, preferably in a virtual environment:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Copy the example configuration, then set `camera.source` to your phone's MJPEG URL, USB camera index or recorded video path. For a phone stream, start IP Webcam and connect both devices to the same local network.

   ```powershell
   Copy-Item config.example.toml config.local.toml
   ```

   The example address is a placeholder. See [camera setup](docs/usage.md#camera-setup) for credentials and environment setup.

4. Run the video viewer:

   ```powershell
   python -m pingpong_robot view
   ```

For pixel inspection, distance measurement, keyboard controls and optional MobileSAM setup, see [usage](docs/usage.md). Distance mode requires a calibration for the actual camera resolution, lens and zoom.

**How this was built:** AI assistance was used to review the documentation and repository structure. The current package is an assisted refactor of the original camera and measurement scripts; see the [migration notes](docs/architecture.md).

Built by **Srijan Kumar Samrat**.

Developed during a self-directed gap year to explore the intersection of Machine Learning and Robotics.
