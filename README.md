# topsbot_cpu_mediapipe_infer

[简体中文](README.zh-CN.md)

ROS 2 MediaPipe CPU inference: `mediapipe_infer` with configurable **Hands / Pose / Face Detection**.

- **file**: local image → annotated JPG
- **pipeline**: subscribe camera topics → publish `/detections` only (rois + points) → `topsbot_webviz` overlays

Does not capture V4L2 or ship a built-in WebUI.

## Dependencies

- `tb_det_msgs` (includes `TbPoint` / `TbTarget.points`)
- `tb_img_msgs`, `sensor_msgs`, `python3-mediapipe`, OpenCV

On the board:

```bash
export PKG_SHARE="$(ros2 pkg prefix topsbot_cpu_mediapipe_infer)/share/topsbot_cpu_mediapipe_infer"
source "$PKG_SHARE/scripts/env_mediapipe.sh" --ros
python3 "$PKG_SHARE/scripts/verify_mediapipe.py"
```

## Input (`input_msg`)

| Value | Default topic | Notes |
| ----- | ------------- | ----- |
| `tb_jpeg` | `/tbmem_jpeg` | JPEG zero-copy |
| `tb_img` | `/tbmem_img` | RGB zero-copy (`encoding=rgb8` only; nv12 rejected) |
| `sensor_image` | `/image_raw` | `Image` |
| `sensor_compressed` | `/image_raw/compressed` | `CompressedImage` |
| `file` | — | Local file |

## Launch

```bash
# Offline JPG
ros2 launch topsbot_cpu_mediapipe_infer file_cli.launch.py \
  solution:=pose \
  image_file:=/path/to.jpg \
  output_image:=/tmp/out.jpg

# Pipeline (JPEG ZC by default)
ros2 launch topsbot_cpu_mediapipe_infer mediapipe_infer.launch.py \
  params_file:=hands.yaml

# One-shot: usb_cam + infer + webviz
ros2 launch topsbot_cpu_mediapipe_infer cam_mediapipe_webviz_demo.launch.py \
  solution:=hands
```

Browser: `http://<board-ip>:8000/` (**http** only, not https). webviz WebSocket is at `ws://<board-ip>:8080`.

> **QoS**: Subscribe to `/tbmem_jpeg` / `/tbmem_img` with `SensorDataQoS` (BEST_EFFORT).

## `/detections` convention

| solution | Target.type | Roi.type | Point.type |
| -------- | ----------- | -------- | ---------- |
| hands | hand | hand | hand_kps (21) |
| pose | person | body | body_kps (33) |
| face_detection | face | face | face_kps (≤6) |
