#!/usr/bin/env python3
"""usb_cam (JPEG ZC) + mediapipe_infer + webviz demo."""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import yaml


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

    cam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(cam_pkg, "launch", "usb_cam.launch.py")),
        launch_arguments={"params_file": "mjpeg_640x480_zc.yaml"}.items(),
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
            "params_file": "tbmem_jpeg_zc.yaml",
            "detection_enabled": "true",
            "detection_topic": "/detections",
        }.items(),
    )
    return [cam, infer, viz]


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument("solution", default_value="hands"),
            OpaqueFunction(function=_launch_setup),
        ]
    )
