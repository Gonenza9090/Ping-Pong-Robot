# Experiment records

## Historical prototype results supplied by the author

| Trial | Actual distance | Estimate | Signed error |
| --- | --- | --- | --- |
| Different calibrated object A | 450 cm | 450.7 cm | +0.7 cm |
| Different calibrated object B | 450 cm | 449.8 cm | -0.2 cm |

The author supplied these values during development. They were not independently reproduced while refactoring this repository. The underlying full trial protocol, calibration record and raw 450 cm frames are not included. These two examples do not establish an overall accuracy percentage or guaranteed operating range for this code.

## New measurements

Use `--actual-distance-cm` and press `S` to collect records in `outputs/measurements.jsonl`. Logs include object dimensions, raw frame size, segmentation backend, focal length, raw/used pixel heights, sample count and measured error. They omit camera credentials and the source URL.

Keep calibration observations separate from evaluation observations. Record the camera/lens and phone zoom settings alongside a trial series. Share only deliberately selected, reviewed experiment files; the outputs directory is ignored by Git by default.
