# Copyright 2026 TOPSBOT
# SPDX-License-Identifier: Apache-2.0

"""Hands NPU .nb lookup / download for topsbot_cpu_mediapipe_infer launch files."""

import os
import subprocess
import sys

from ament_index_python.packages import get_package_share_directory
from launch.substitutions import LaunchConfiguration

PACKAGE_NAME = "topsbot_cpu_mediapipe_infer"
DEFAULT_MODELS_DIR = "~/topsbot/models"
HANDS_NB_FILES = (
    "palm_detection_lite_int8.nb",
    "hand_landmark_lite_int8.nb",
)


def is_hands_solution(solution):
    name = (solution or "hands").strip().lower()
    return name in ("hands", "hand")


def _launch_arg(context, name, default=""):
    try:
        value = LaunchConfiguration(name).perform(context)
    except Exception:
        return default
    return value if value not in (None, "") else default


def ensure_hands_models(context, solution):
    """Download Hands NPU .nb files when missing.

    Pose / Face Detection use TFLite inside the MediaPipe wheel and skip this.
    Returns the directory to export as MEDIAPIPE_NB_DIR, or None.
    """
    if not is_hands_solution(solution):
        return None

    models_dir = os.path.normpath(os.path.expanduser(
        _launch_arg(context, "models_dir", DEFAULT_MODELS_DIR) or DEFAULT_MODELS_DIR))
    missing = [
        os.path.join(models_dir, name)
        for name in HANDS_NB_FILES
        if not os.path.isfile(os.path.join(models_dir, name))
    ]
    if not missing:
        return models_dir

    auto_download = _launch_arg(context, "auto_download_models", "true")
    if auto_download.lower() not in ("true", "1", "yes"):
        raise RuntimeError(
            "Hands NPU models are missing: " + ", ".join(missing)
            + "; run scripts/download_models.sh or launch with auto_download_models:=true")

    package_share = get_package_share_directory(PACKAGE_NAME)
    manifest_path = os.path.join(package_share, "config", "models_manifest.yaml")
    if not os.path.isfile(manifest_path):
        raise RuntimeError(f"models_manifest.yaml not found: {manifest_path}")
    model_manager = os.path.join(package_share, "scripts", "model_manager.py")
    if not os.path.isfile(model_manager):
        raise RuntimeError(f"model_manager.py not found: {model_manager}")

    print(f"[mediapipe_infer] Missing models: {missing}; downloading to {models_dir}",
          file=sys.stderr)
    try:
        subprocess.run([
            sys.executable, model_manager, "download",
            "--manifest", manifest_path,
            "--install-dir", models_dir,
        ], check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"failed to download Hands NPU models: {e}") from None

    still_missing = [
        os.path.join(models_dir, name)
        for name in HANDS_NB_FILES
        if not os.path.isfile(os.path.join(models_dir, name))
    ]
    if still_missing:
        raise RuntimeError(
            "Hands NPU models still missing after download: "
            + ", ".join(still_missing))
    print("[mediapipe_infer] Models ready", file=sys.stderr)
    return models_dir
