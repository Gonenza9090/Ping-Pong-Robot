# Validation and local testing

## Automated checks

Run `python -m unittest discover -s tests -v` from the repository root after installation. These tests use synthetic frames, masks, JPEG data and arithmetic references. They require no phone, display window, GPU or SAM weights.

The tests establish software behavior under those conditions. They do not validate the author's focal length, physical object measurements, 450 cm experiment results, live camera reliability or real-world SAM segmentation accuracy.

## Physical setup checks still needed

1. Run `view` and confirm a fresh stream at the intended resolution.
2. Interrupt Wi-Fi/IP Webcam. The app should stay responsive, expire the previous frame and reconnect when video returns.
3. Compare a click and prompt box in `pixels` at display zoom 1x and 2x. Measurement must stay in original raw pixels.
4. Test both GrabCut and optional MobileSAM on full-object selections, difficult backgrounds and image borders.
5. Recalibrate using physically measured objects and distances.
6. Collect separate test measurements at multiple distances and save them with ground truth.
7. Test the width fallback only after verifying object widths; compare it against height-only results.

USB capture backend read interruption and desktop window behavior vary by platform. A running segmentation is allowed to finish during shutdown so the worker and model are cleaned up.
