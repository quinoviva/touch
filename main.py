import sys
import os

from calibration import run_calibration
from tracking import run_tracking


def main():
    print("=" * 60)
    print("  Touch TV — Interactive Touch Screen via Webcam")
    print("=" * 60)
    print()
    print("This app turns your TV into an interactive touch screen")
    print("using your laptop's front-facing webcam.")
    print()
    print("Make sure your laptop display is MIRRORED/DUPLICATED to your TV.")
    print()

    if not os.path.exists("calibration.json"):
        print("No calibration found. Starting calibration wizard...")
        print("Press ESC at any time to exit.")
        print()
        calibrated = run_calibration()
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
        run_tracking()
    except KeyboardInterrupt:
        pass
    finally:
        print("\nTouch TV stopped.")


if __name__ == "__main__":
    main()
