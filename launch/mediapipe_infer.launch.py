#!/usr/bin/env python3
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

    overrides = {}
    for key in (
        "solution",
        "input_msg",
        "input_topic",
        "tb_img_profile",
        "image_file",
        "output_image",
        "detections_topic",
        "publish_detections",
        "process_every_n",
        "inference_width",
    ):
        val = LaunchConfiguration(key).perform(context)
        if val != "":
            if key in ("publish_detections",):
                overrides[key] = val.strip().lower() in ("1", "true", "yes", "on")
            elif key in ("process_every_n", "inference_width"):
                overrides[key] = int(val)
            else:
                overrides[key] = val
    params.update(overrides)

    node = Node(
        package="topsbot_cpu_mediapipe_infer",
        executable="mediapipe_infer",
        name="mediapipe_infer",
        output="screen",
        parameters=[params],
    )
    return [node]


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument("params_file", default_value="hands.yaml"),
            DeclareLaunchArgument("solution", default_value=""),
            DeclareLaunchArgument("input_msg", default_value=""),
            DeclareLaunchArgument("input_topic", default_value=""),
            DeclareLaunchArgument("tb_img_profile", default_value=""),
            DeclareLaunchArgument("image_file", default_value=""),
            DeclareLaunchArgument("output_image", default_value=""),
            DeclareLaunchArgument("detections_topic", default_value=""),
            DeclareLaunchArgument("publish_detections", default_value=""),
            DeclareLaunchArgument("process_every_n", default_value=""),
            DeclareLaunchArgument("inference_width", default_value=""),
            OpaqueFunction(function=_launch_setup),
        ]
    )
