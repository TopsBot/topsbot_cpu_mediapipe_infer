#!/usr/bin/env python3
"""usb_cam (JPEG ZC) + mediapipe_infer + webviz demo."""
import os
import sys

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    OpaqueFunction,
    SetEnvironmentVariable,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import yaml

_launch_dir = os.path.dirname(os.path.abspath(__file__))
if _launch_dir not in sys.path:
    sys.path.insert(0, _launch_dir)
from model_utils import ensure_hands_models  # noqa: E402


def _load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("/**", {}).get("ros__parameters", data.get("ros__parameters", data))


def _launch_setup(context, *args, **kwargs):
    mp_pkg = get_package_share_directory("topsbot_cpu_mediapipe_infer")
    cam_pkg = get_package_share_directory("topsbot_usb_cam")
    viz_pkg = get_package_share_directory("topsbot_webviz")

    solution = LaunchConfiguration("solution").perform(context) or "hands"
    params_name = {
        "hands": "hands.yaml",
        "pose": "pose.yaml",
        "face_detection": "face_detection.yaml",
        "face": "face_detection.yaml",
    }.get(solution, "hands.yaml")
    mp_params = _load_yaml(os.path.join(mp_pkg, "config", params_name))
    mp_params["solution"] = "face_detection" if solution == "face" else solution
    mp_params["input_msg"] = "tb_jpeg"
    mp_params["input_topic"] = "/tbmem_jpeg"
    mp_params["publish_detections"] = True
    mp_params["process_every_n"] = int(
        LaunchConfiguration("process_every_n").perform(context) or "1"
    )

    actions = []
    nb_dir = ensure_hands_models(context, mp_params.get("solution", "hands"))
    if nb_dir:
        actions.append(SetEnvironmentVariable("MEDIAPIPE_NB_DIR", nb_dir))

    cam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(cam_pkg, "launch", "usb_cam.launch.py")),
        launch_arguments={
            "params_file": "mjpeg_640x480_zc.yaml",
            "framerate": "30",
        }.items(),
    )
    infer = Node(
        package="topsbot_cpu_mediapipe_infer",
        executable="mediapipe_infer",
        name="mediapipe_infer",
        output="screen",
        parameters=[mp_params],
    )
    viz = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(viz_pkg, "launch", "webviz.launch.py")),
        launch_arguments={
            "params_file": "tb_jpeg.yaml",
            "detection_enabled": "true",
            "detection_topic": "/detections",
        }.items(),
    )
    actions.extend([cam, infer, viz])
    return actions


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument("solution", default_value="hands"),
            DeclareLaunchArgument(
                "process_every_n",
                default_value="1",
                description="Infer every N camera frames (1 = every frame; 3 was for slow CPU)",
            ),
            DeclareLaunchArgument(
                "models_dir",
                default_value="~/topsbot/models",
                description="Directory containing Hands NPU .nb models",
            ),
            DeclareLaunchArgument(
                "auto_download_models",
                default_value="true",
                description="Auto download Hands NPU models if missing",
            ),
            OpaqueFunction(function=_launch_setup),
        ]
    )
