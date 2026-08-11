#!/usr/bin/env python3
"""Verify MediaPipe Hands / Pose / FaceDetection can initialize."""

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--solution",
        default="all",
        choices=("all", "hands", "pose", "face_detection"),
    )
    args = parser.parse_args()
    import mediapipe as mp

    solutions = []
    if args.solution in ("all", "hands"):
        solutions.append(("Hands", lambda: mp.solutions.hands.Hands(
            static_image_mode=True, max_num_hands=1, model_complexity=0
        )))
    if args.solution in ("all", "pose"):
        solutions.append(("Pose", lambda: mp.solutions.pose.Pose(
            static_image_mode=True, model_complexity=0
        )))
    if args.solution in ("all", "face_detection"):
        solutions.append(("FaceDetection", lambda: mp.solutions.face_detection.FaceDetection(
            model_selection=0, min_detection_confidence=0.5
        )))

    for name, factory in solutions:
        obj = factory()
        obj.close()
        print(f"{name} OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
