# Architecture and migration

The body/controller layer is intentionally absent until hardware is chosen and tested. This repository is the current desktop vision and measurement prototype.

| Module | Responsibility |
| --- | --- |
| `config.py` | Validate camera settings, known object dimensions and calibration |
| `vision/stream.py` | Acquire the newest frame, reconnect MJPEG streams and reject stale data |
| `vision/viewport.py` | Display-only crop/zoom and exact coordinate mapping back to raw pixels |
| `brain/segmentation.py` | Common GrabCut/MobileSAM prompt and foreground-mask contract |
| `brain/measurement.py` | Jittered segmentation, edge refinement and pixel statistics |
| `brain/geometry.py` | Pure distance/calibration math and optional width heuristic |
| `app.py` | Main-thread GUI, frozen-frame state, background measurement and local result saves |
| `cli.py` | `view`, `pixels`, `measure` and `calibrate` commands |

## What changed from the uploaded scripts

- The three copied camera configurations became one ignored local config.
- Camera credentials are read from environment variables and are not printed in application status messages.
- The HTTP stream uses request authentication separately from its URL.
- A disconnected camera cannot return the last frame indefinitely; packets expire.
- The exact displayed raw frame is frozen at click time.
- Digital zoom only changes the view. Clicks/boxes map back to the unzoomed original image before measurement, so focal length is not multiplied by an approximate zoom factor.
- MobileSAM receives the adjustable box as well as the click prompt.
- The selected connected component contains the click; an unrelated larger object is not selected merely because it has the most pixels.
- Nearest-neighbour mask resizing avoids inventing intermediate mask labels.
- Edge searches are clamped to the image, including objects near its borders.
- Guessed object widths cannot override height measurements. The width policy is explicitly experimental and disabled by default.
- Segmentation is queued on one worker while window events stay on the main thread.
- The app closes camera resources and windows in cleanup paths.

The original files remain in the user's uploaded source collection. They are not copied into this repository because they contain local camera connection details. This refactor was made with coding assistance; the author should test, understand and adapt it before describing its behavior as demonstrated on the physical setup.

## Future controller boundary

A future controller should consume a separately defined, time-stamped target estimate with validity checks. This code does not yet estimate ping pong ball trajectories or send actuator commands, and it does not choose a microcontroller board.
