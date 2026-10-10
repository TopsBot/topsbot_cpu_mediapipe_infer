# Changelog

## 0.2.0 (2026-09-21)

- 独立 Hands 场景：新增模型下载脚本与 `models_manifest.yaml`，首次 launch 自动将 NPU `.nb` 装到 `~/topsbot/models/`。
- Hands launch 增加 `models_dir` / `auto_download_models`，并设置 `MEDIAPIPE_NB_DIR`；Pose / Face 仍用 wheel 内 TFLite，不下载。
- 修复 `setup.py` 安装 `scripts/` 时误收录 `__pycache__` 导致 colcon 失败。
- Hands 默认 `process_every_n` 改为 1（`hands.yaml` 与 `cam_mediapipe_webviz_demo` 可逐帧推理）；Pose / Face Detection 仍为 3 / 2。
- `cam_mediapipe_webviz_demo` 将 usb_cam 固定为 30fps，并暴露 `process_every_n` launch 参数。

## 0.1.1 (2026-09-14)

- 修复 `cam_mediapipe_webviz_demo.launch.py`：跟随 topsbot_webviz 类型化配置改名，将 `tbmem_jpeg_zc.yaml` 更新为 `tb_jpeg.yaml`。

## 0.1.0 (2026-07-27)

- 初始包：MediaPipe Hands / Pose / Face Detection 推理节点
- 接入 release2github：GitLab → GitHub 白名单同步（追加历史，禁止 force-push）
