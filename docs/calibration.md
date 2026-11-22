# Calibration and assumptions

Distance measurement uses a known object height and a focal length in pixels. It assumes the object's measured vertical dimension is upright and approximately parallel to the camera image plane. This is not arbitrary depth estimation and is not a measurement of a tilted object's true three-dimensional distance.

## Practical workflow

1. Fix the camera lens, phone-camera zoom, stream resolution and mount.
2. Measure the object's actual height with a ruler.
3. Measure a reference distance from the camera consistently. Decide which physical camera reference point you use and record it.
4. In `pixels` mode, segment the complete object and record raw height in pixels.
5. Repeat with several objects/distances. Use `calibrate --sample ...` for the collected observations and inspect their focal-length spread.
6. Save calibration to a `*.local.json` file and pass it with `--calibration`.
7. Evaluate on different observations from those used for calibration. Changing the lens, camera zoom or image crop requires a new calibration even if the pixel resolution stays the same.

The software checks the frame width and height. It cannot automatically prove that the phone lens, optical field of view or physical mount stayed unchanged.

## Object dimensions

The example heights come from the executable values in the uploaded `Dis_measure.py`: Fogg can 17.5 cm, Box 18.8 cm, Can 2 12.0 cm. Earlier comments in that file contained different values; remeasure before relying on the example.

No object widths are prefilled. The original file marked at least one width as a placeholder. To experiment with the original width-derived-height idea, add both fields to a measured object:

```toml
# Replace with your actual measured width, not this illustrative number.
width_cm = 4.0
width_verified = true
```

Also set `measurement.width_correction = true`. When the measured height and width-derived height agree within `ratio_tolerance_pct`, they are averaged; otherwise width becomes the fallback. Both estimates come from one frame and may share errors. A low disagreement is not proof of correct segmentation, and a correct-looking width does not guarantee a correct fallback. Leave this off for ordinary height-only measurements until you have collected validation data.

## Report errors directly

For a known test distance, run:

```powershell
python -m pingpong_robot measure --calibration calibration.local.json --actual-distance-cm 450
```

Press `S` on a result to save its estimate, ground truth and absolute/relative error. More clicks on one frozen frame test segmentation repeatability; independent frames, distances, objects and lighting are needed to evaluate real-world measurement performance.
