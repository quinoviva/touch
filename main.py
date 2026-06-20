import sys
import os

from calibration import run_calibration
from tracking import run_tracking


def get_camera_source():
    import argparse
    parser = argparse.ArgumentParser(description="Touch TV — Interactive Touch Screen")
    parser.add_argument("--camera", type=str, default="0",
                        help="Camera index (0) or IP Webcam URL (e.g. http://192.168.1.100:8080/video)")
    args = parser.parse_args()
    src = args.camera
    try:
        return int(src)
    except ValueError:
        return src


def main():
    camera_source = get_camera_source()

    print("=" * 60)
    print("  Touch TV — Interactive Touch Screen via Webcam")
    print("=" * 60)
    print()
    print("This app turns your TV into an interactive touch screen")
    print("using your laptop's front-facing webcam.")
    print()
    print("Make sure your laptop display is MIRRORED/DUPLICATED to your TV.")
    print()
    print(f"Camera source: {camera_source}")
    print()

    if not os.path.exists("calibration.json"):
        print("No calibration found. Starting calibration wizard...")
        print("Press ESC at any time to exit.")
        print()
        calibrated = run_calibration(camera_source)
        if not calibrated:
            print("\nCalibration was cancelled. Exiting.")
            sys.exit(0)
        print("\nCalibration saved to calibration.json")
    else:
        print("Using existing calibration.json.")
        print("Re-run and delete calibration.json to recalibrate.")
        print()

    print("Starting tracking engine. Press ESC in the debug window to exit.")
    print()
    try:
        run_tracking(camera_source)
    except KeyboardInterrupt:
        pass
    finally:
        print("\nTouch TV stopped.")


if __name__ == "__main__":
    main()
