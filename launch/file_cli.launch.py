#!/usr/bin/env python3
"""Offline file inference -> annotated JPG."""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import yaml


def _load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("/**", {}).get("ros__parameters", data.get("ros__parameters", data))


def _launch_setup(context, *args, **kwargs):
    pkg = get_package_share_directory("topsbot_cpu_mediapipe_infer")
    params_file = LaunchConfiguration("params_file").perform(context)
    if not os.path.isabs(params_file):
        params_file = os.path.join(pkg, "config", params_file)
    params = _load_yaml(params_file)
    params["input_msg"] = "file"
    params["publish_detections"] = False
    params["static_image_mode"] = True

    for key in ("solution", "image_file", "output_image", "inference_width"):
        val = LaunchConfiguration(key).perform(context)
        if val != "":
            params[key] = int(val) if key == "inference_width" else val

    return [
        Node(
            package="topsbot_cpu_mediapipe_infer",
            executable="mediapipe_infer",
            name="mediapipe_infer",
            output="screen",
            parameters=[params],
        )
    ]


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument("params_file", default_value="file_hands.yaml"),
            DeclareLaunchArgument("solution", default_value="hands"),
            DeclareLaunchArgument("image_file", default_value=""),
            DeclareLaunchArgument("output_image", default_value="/tmp/topsbot_mediapipe/out.jpg"),
            DeclareLaunchArgument("inference_width", default_value=""),
            OpaqueFunction(function=_launch_setup),
        ]
    )
