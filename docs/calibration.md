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

The author confirmed that the current stream is **1920 x 1080**. The example and configuration defaults now use that resolution. The retained 1390 px focal length is unverified for this setup because the original comments associate it with 1600 x 900. Calculate a new calibration from actual 1920 x 1080 frames; no automatic focal-length scaling is performed.

## Historical calibration conflict

The original `Dis_measure.py` comments describe an 80 cm calibration at 1600 x 900, without zoom, and list focal lengths of 1211.2, 1186.3 and 1180.0 px. Their arithmetic mean is **1192.5 px**. A separate comment mentions 1183.6 px, while the executable setting is 1390 px. The commented object heights (17.8 and 18.5 cm) also differ from the executable heights (17.5 and 18.8 cm).

The original distance script loads MobileSAM, but that does not establish which backend produced the historical calibration observations. The calibration backend, raw pixel heights and independent validation records are still needed. None of these conflicting values is a verified replacement for the current configuration, and no focal length is automatically converted between resolutions.

## Object dimensions

The example heights come from the executable values in the uploaded `Dis_measure.py`: Fogg can 17.5 cm, Box 18.8 cm, Can 2 12.0 cm. Earlier comments in that file contained different values; remeasure before relying on the example.

The widths from lines 84-88 of the uploaded script are preserved in the example:

| Object | Height (cm) | Width (cm) |
| --- | --- | --- |
| Fogg can | 17.5 | 4.4 |
| Box | 18.8 | 10.0 |
| Can 2 | 12.0 | 3.5 |

The original file marked Can 2's width as a placeholder. All three widths therefore remain `width_verified = false` pending confirmation of physical measurements. To experiment with the original width-derived-height idea, measure the relevant width and update that object's fields:

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

## Calibration command

The known-height pinhole approximation is:

```text
distance_cm = real_height_cm * focal_length_px / pixel_height
focal_length_px = pixel_height * reference_distance_cm / real_height_cm
```

Use `pixels` to inspect a known-height object at a tape-measured distance. Then calculate calibration from one or more observations:

```powershell
python -m pingpong_robot calibrate --sample 20 100 200 --sample 10 200 50 --frame-size 1920 1080 --output calibration.local.json
python -m pingpong_robot measure --calibration calibration.local.json
```

Those two samples are **illustrative arithmetic examples**, not results from my camera. Each sample is `REAL_HEIGHT_CM DISTANCE_CM PIXEL_HEIGHT`; the tool stores the median inferred focal length and the supplied reference observations. See [object dimensions](#object-dimensions) for the experimental width fallback.

Record the segmentation backend (`grabcut` or `sam`) beside every calibration series, and validate with that same backend. The calibration command receives manually supplied pixel heights; it does not infer which backend produced them.
