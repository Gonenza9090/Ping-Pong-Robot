# Usage and controls

## Pixel inspection and distance measurement

```powershell
python -m pingpong_robot pixels
python -m pingpong_robot measure
```

The default backend is **GrabCut**, which needs no model download. To use the MobileSAM backend from the original distance script:

```powershell
python -m pip install -r requirements-sam.txt
python -m pingpong_robot measure --backend sam
```

MobileSAM loads on the first requested measurement, not when importing the package. Ultralytics may download `mobile_sam.pt` on first use. For GPU execution, install a compatible PyTorch build using the [official instructions](https://pytorch.org/get-started/locally/).

| Key / action | Effect |
| --- | --- |
| `1`, `2`, `3` | Select a known object; required before distance measurement |
| Left click | Freeze the currently displayed frame |
| `+` / `-` | Enlarge / reduce the prompt box |
| Enter | Segment and measure |
| Escape | Cancel the box or return from a result |
| `R` | Retry the same frozen frame |
| `S` | Save the result to `outputs/measurements.jsonl` |
| Space | Return from the result to live video |
| `Z` / `X` | Change display zoom; raw measurement pixels stay unchanged |
| `Q` | Quit; an in-flight segmentation finishes before shutdown |

Both segmentation backends use the displayed box. The chosen foreground component must contain the clicked point. Multiple jittered prompts sample the **same frozen image**; their spread describes repeatability, not independent real-world trials or certified accuracy.

## Camera setup

### Environment and connection

Requires **Python 3.11 or newer** and a desktop display. Start in the repository directory.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item config.example.toml config.local.toml
```

If PowerShell does not permit activation, use `.venv\Scripts\python.exe` in place of `python`; no policy change is necessary. On macOS/Linux, activate with `source .venv/bin/activate` and copy the config with `cp`.

1. Start the IP Webcam server on the phone and connect the phone and laptop to the same local network.
2. Edit `camera.source` in `config.local.toml`, for example `http://YOUR_PHONE_IP:8080/video`.
3. If the phone requires a login, set credentials in the current terminal, not in a committed file:

   ```powershell
   $env:PINGPONG_CAMERA_USERNAME = "your-camera-username"
   $env:PINGPONG_CAMERA_PASSWORD = "your-camera-password"
   ```

4. First check the video:

   ```powershell
   python -m pingpong_robot view
   ```

The example's loopback address is a placeholder. The original camera address and login are intentionally not published. `config.local.toml`, calibration files, model weights and experiment logs are ignored by Git.

## Current limits

Manually selected known objects, assumed upright dimensions, interactive rather than continuous ball tracking, and sensitivity to camera geometry and segmentation edges limit the current prototype. Phone-camera and MobileSAM checks on the refactored application are still pending; see [testing](testing.md).

## References

- [OpenCV GrabCut](https://docs.opencv.org/4.x/d8/d83/tutorial_py_grabcut.html)
- [Ultralytics MobileSAM](https://docs.ultralytics.com/models/mobile-sam/)
- [Ultralytics SAM prompts](https://docs.ultralytics.com/models/sam/)
