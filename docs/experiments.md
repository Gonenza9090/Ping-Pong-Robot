# Experiment records

## Published validation status

No reproducible camera-validation dataset is committed yet. The earlier 450 cm estimates have been removed from the published results because their frames, calibration record and backend were not recorded in this repository. They should be repeated and logged before being presented as evidence.

For each published trial, include the actual and estimated distance, signed/absolute error, relative error, object dimensions, resolution, focal length, backend and a reviewed frame/log link. Compute absolute relative error as `100 * abs(estimate_cm - actual_cm) / actual_cm`. Report calibration observations separately from held-out validation.

## New measurements

Use `--actual-distance-cm` and press `S` to collect records in `outputs/measurements.jsonl`. Logs include object dimensions, raw frame size, segmentation backend, focal length, raw/used pixel heights, sample count and measured error. They omit camera credentials and the source URL.

Keep calibration observations separate from evaluation observations. Record the camera/lens and phone zoom settings alongside a trial series. Share only deliberately selected, reviewed experiment files; the outputs directory is ignored by Git by default.
