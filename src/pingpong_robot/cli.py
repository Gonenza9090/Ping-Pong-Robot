"""Command-line entry point; --help does not open cameras or load ML weights."""

import argparse
from dataclasses import replace
import json
from pathlib import Path
from statistics import median
from .config import Calibration, load_settings, pixel_count, positive
from .brain.geometry import focal_length_px


def parser():
    root = argparse.ArgumentParser(description="Ping pong robot vision/measurement prototype")
    commands = root.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("view", "View live video only (original Video.py)"),
        ("pixels", "Freeze, segment and inspect raw pixel dimensions (original Pixel.py)"),
        ("measure", "Measure a calibrated known object's distance (original Dis_measure.py)"),
    ):
        sub = commands.add_parser(name, help=help_text)
        sub.add_argument("--config", default="config.local.toml")
        sub.add_argument("--source", help="Override with an MJPEG URL, video path or USB index")
        sub.add_argument("--backend", choices=["grabcut", "sam"])
        sub.add_argument("--weights", help="MobileSAM weights path; optional download on first use")
        sub.add_argument("--calibration", help="Override TOML calibration with a calibration JSON file")
        sub.add_argument("--log", default="outputs/measurements.jsonl")
        sub.add_argument("--actual-distance-cm", type=float, help="Optional measured ground truth for saved error records")
    sub = commands.add_parser("calibrate", help="Calculate focal length from one or more manually measured references")
    sub.add_argument("--sample", nargs=3, type=float, action="append", required=True,
                     metavar=("HEIGHT_CM", "DISTANCE_CM", "PIXEL_HEIGHT"))
    sub.add_argument("--frame-size", nargs=2, type=int, required=True, metavar=("WIDTH", "HEIGHT"))
    sub.add_argument("--output", help="Write calibration JSON; otherwise print it")
    return root


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "calibrate":
            width, height = args.frame_size
            positive(width, "frame width"); positive(height, "frame height")
            focal = [focal_length_px(*sample) for sample in args.sample]
            row = {
                "focal_length_px": median(focal), "frame_width": width, "frame_height": height,
                "method": "median_of_known_height_samples", "samples": args.sample,
                "sample_focal_lengths_px": focal,
            }
            text = json.dumps(row, indent=2)
            if args.output:
                target = Path(args.output)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text + "\n", encoding="utf-8")
                print(f"Calibration saved to {target}")
            else:
                print(text)
            return 0
        settings = load_settings(args.config, args.source)
        if args.backend:
            settings = replace(settings, measurement=replace(settings.measurement, backend=args.backend))
        if args.weights:
            settings = replace(settings, measurement=replace(settings.measurement, sam_weights=args.weights))
        if args.calibration:
            c = json.loads(Path(args.calibration).read_text(encoding="utf-8"))
            settings = replace(settings, calibration=Calibration(
                positive(c["focal_length_px"], "focal_length_px"),
                pixel_count(c["frame_width"], "frame_width"),
                pixel_count(c["frame_height"], "frame_height"),
            ))
        actual = None if args.actual_distance_cm is None else positive(args.actual_distance_cm, "actual_distance_cm")
        from .app import RobotApp
        RobotApp(settings, args.command, args.log, actual).run()
        return 0
    except (ValueError, TypeError, KeyError, OSError, RuntimeError) as error:
        print(f"Error: {error}")
        return 2
