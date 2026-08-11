# topsbot_cpu_mediapipe_infer

[English](README.md)

ROS 2 MediaPipe CPU 推理包：`mediapipe_infer` 节点，配置切换 **Hands / Pose / Face Detection**。

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

# 一键：usb_cam + infer + webviz
ros2 launch topsbot_cpu_mediapipe_infer cam_mediapipe_webviz_demo.launch.py \
  solution:=hands
```

浏览器：`http://<板卡IP>:8000/`（必须是 **http**，不要 https）。webviz WebSocket 在 `ws://<板卡IP>:8080`。

> **QoS**：订 `/tbmem_jpeg` / `/tbmem_img` 使用 `SensorDataQoS`（BEST_EFFORT）。

## `/detections` 约定

| solution | Target.type | Roi.type | Point.type |
| -------- | ----------- | -------- | ---------- |
| hands | hand | hand | hand_kps (21) |
| pose | person | body | body_kps (33) |
| face_detection | face | face | face_kps (≤6) |
