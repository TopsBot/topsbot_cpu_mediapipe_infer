# topsbot_cpu_mediapipe_infer

[简体中文](README.zh-CN.md)

ROS 2 MediaPipe inference: `mediapipe_infer` with configurable **Hands (NPU) / Pose / Face Detection (CPU)**.

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

## Models (Hands NPU)

Hands on NPU needs a pair of `.nb` files that are **not** shipped in source or the wheel. Pose / Face Detection use TFLite inside the wheel and need no download.

On first Hands launch, `~/topsbot/models/` is checked; missing files are downloaded per `config/models_manifest.yaml`. Filenames and directory match `topsbot_gesture`, but this package is a standalone scene and ships its own download script.

| Model | Default path |
| ----- | ------------ |
| `palm_detection_lite_int8.nb` | `~/topsbot/models/palm_detection_lite_int8.nb` |
| `hand_landmark_lite_int8.nb` | `~/topsbot/models/hand_landmark_lite_int8.nb` |

MediaPipe lookup: `$MEDIAPIPE_NB_DIR/<name>` then `~/topsbot/models/<name>`. Hands launch sets `MEDIAPIPE_NB_DIR` from `models_dir`.

Offline / already placed:

```bash
ros2 launch topsbot_cpu_mediapipe_infer file_cli.launch.py auto_download_models:=false
```

Manual download (source tree):

```bash
./scripts/download_models.sh
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

# One-shot: usb_cam (30 fps) + infer + webviz
ros2 launch topsbot_cpu_mediapipe_infer cam_mediapipe_webviz_demo.launch.py \
  solution:=hands
```

Common launch arguments:

| Arg | Default | Notes |
| --- | ------- | ----- |
| `models_dir` | `~/topsbot/models` | Hands NPU `.nb` directory; sets `MEDIAPIPE_NB_DIR` |
| `auto_download_models` | `true` | Download missing Hands models on first launch |
| `process_every_n` | see yaml / demo | Infer every N frames (`1` = every frame) |

`process_every_n` defaults: `hands.yaml` = 1, `pose.yaml` = 3, `face_detection.yaml` = 2. `cam_mediapipe_webviz_demo` overrides to **1** and sets usb_cam `framerate:=30`.

Browser: `http://<board-ip>:8000/` (**http** only, not https). webviz WebSocket is at `ws://<board-ip>:8080`.

> **QoS**: Subscribe to `/tbmem_jpeg` / `/tbmem_img` with `SensorDataQoS` (BEST_EFFORT).

## `/detections` convention

| solution | Target.type | Roi.type | Point.type |
| -------- | ----------- | -------- | ---------- |
| hands | hand | hand | hand_kps (21) |
| pose | person | body | body_kps (33) |
| face_detection | face | face | face_kps (≤6) |
