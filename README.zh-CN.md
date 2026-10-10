# topsbot_cpu_mediapipe_infer

[English](README.md)

ROS 2 MediaPipe 推理包：`mediapipe_infer` 节点，配置切换 **Hands（NPU）/ Pose / Face Detection（CPU）**。

- **file**：本地图 → 可视化 JPG  
- **pipeline**：订相机图 → 只发 `/detections`（rois + points）→ `topsbot_webviz` 画框/关节点  

不采 V4L2、不内置 WebUI。

## 依赖

- `tb_det_msgs`（含 `TbPoint` / `TbTarget.points`）
- `tb_img_msgs`、`sensor_msgs`、`python3-mediapipe`、OpenCV

板端：

```bash
export PKG_SHARE="$(ros2 pkg prefix topsbot_cpu_mediapipe_infer)/share/topsbot_cpu_mediapipe_infer"
source "$PKG_SHARE/scripts/env_mediapipe.sh" --ros
python3 "$PKG_SHARE/scripts/verify_mediapipe.py"
```

## 模型文件（Hands NPU）

Hands 在 NPU 上跑时需要一对 `.nb`，**不随源码 / wheel 分发**。Pose / Face Detection 用 wheel 内的 TFLite，不需要下载。

首次 launch Hands 时会检查 `~/topsbot/models/`，缺失则按 `config/models_manifest.yaml` 自动下载。文件名与 `topsbot_gesture` 相同，目录也相同，但本包是独立场景，自带下载脚本。

| 模型文件 | 默认路径 |
| ---- | ---- |
| `palm_detection_lite_int8.nb` | `~/topsbot/models/palm_detection_lite_int8.nb` |
| `hand_landmark_lite_int8.nb` | `~/topsbot/models/hand_landmark_lite_int8.nb` |

MediaPipe 查找顺序：`$MEDIAPIPE_NB_DIR/<文件名>` → `~/topsbot/models/<文件名>`。Hands launch 会把 `models_dir` 写进 `MEDIAPIPE_NB_DIR`。

离线环境或模型已手动放置：

```bash
ros2 launch topsbot_cpu_mediapipe_infer file_cli.launch.py auto_download_models:=false
```

手动下载（源码树）：

```bash
./scripts/download_models.sh
```

## 输入（`input_msg`）

| 值 | 话题默认 | 说明 |
| ---- | -------- | ---- |
| `tb_jpeg` | `/tbmem_jpeg` | JPEG 零拷贝 |
| `tb_img` | `/tbmem_img` | RGB 零拷贝（仅 `encoding=rgb8`；拒绝 nv12） |
| `sensor_image` | `/image_raw` | `Image` |
| `sensor_compressed` | `/image_raw/compressed` | `CompressedImage` |
| `file` | — | 本地文件 |

## 启动

```bash
# 离线 JPG
ros2 launch topsbot_cpu_mediapipe_infer file_cli.launch.py \
  solution:=pose \
  image_file:=/path/to.jpg \
  output_image:=/tmp/out.jpg

# pipeline（JPEG ZC 默认）
ros2 launch topsbot_cpu_mediapipe_infer mediapipe_infer.launch.py \
  params_file:=hands.yaml

# 一键：usb_cam（30 fps）+ infer + webviz
ros2 launch topsbot_cpu_mediapipe_infer cam_mediapipe_webviz_demo.launch.py \
  solution:=hands
```

常用 launch 参数：

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `models_dir` | `~/topsbot/models` | Hands NPU `.nb` 目录，会写入 `MEDIAPIPE_NB_DIR` |
| `auto_download_models` | `true` | 首次 launch 时自动下载缺失的 Hands 模型 |
| `process_every_n` | 见 yaml / demo | 每 N 帧推理一次（`1` = 逐帧） |

`process_every_n` 默认：`hands.yaml` = 1，`pose.yaml` = 3，`face_detection.yaml` = 2。`cam_mediapipe_webviz_demo` 会覆盖为 **1**，并把 usb_cam 设为 `framerate:=30`。

浏览器：`http://<板卡IP>:8000/`（必须是 **http**，不要 https）。webviz WebSocket 在 `ws://<板卡IP>:8080`。

> **QoS**：订 `/tbmem_jpeg` / `/tbmem_img` 使用 `SensorDataQoS`（BEST_EFFORT）。

## `/detections` 约定

| solution | Target.type | Roi.type | Point.type |
| -------- | ----------- | -------- | ---------- |
| hands | hand | hand | hand_kps (21) |
| pose | person | body | body_kps (33) |
| face_detection | face | face | face_kps (≤6) |
