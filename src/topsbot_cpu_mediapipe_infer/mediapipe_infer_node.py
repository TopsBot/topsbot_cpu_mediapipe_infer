#!/usr/bin/env python3
"""ROS 2 MediaPipe inference node (file + pipeline)."""

from __future__ import annotations

import concurrent.futures
import os
import time
from typing import Optional, Tuple

import cv2 as cv
import numpy as np
import rclpy
from builtin_interfaces.msg import Time as TimeMsg
from geometry_msgs.msg import Point32
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CompressedImage, Image
from tb_det_msgs.msg import TbPerceptionTargets, TbPerf, TbPoint, TbRoi, TbTarget
from tb_img_msgs.msg import TbJpegFrame, TbMsg480P, TbMsg540P, TbMsg1080P

from .solutions.base import InferResult, SolutionBase, TargetDraft
from .solutions.face_detection import FaceDetectionSolution
from .solutions.hands import HandsSolution
from .solutions.pose import PoseSolution


def as_bool(value) -> bool:  # noqa: ANN001
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)


def encoding_to_str(raw) -> str:  # noqa: ANN001
    if isinstance(raw, str):
        return raw.split("\0", 1)[0]
    return bytes(raw).split(b"\0", 1)[0].decode("ascii", errors="ignore")


class MediapipeInferNode(Node):
    def __init__(self):
        super().__init__("mediapipe_infer")
        self.declare_parameter("solution", "hands")
        self.declare_parameter("input_msg", "tb_jpeg")
        self.declare_parameter("input_topic", "")
        self.declare_parameter("tb_img_profile", "480p")
        self.declare_parameter("image_file", "")
        self.declare_parameter("output_image", "/tmp/topsbot_mediapipe/out.jpg")
        self.declare_parameter("detections_topic", "/detections")
        self.declare_parameter("publish_detections", True)
        self.declare_parameter("process_every_n", 3)
        self.declare_parameter("inference_width", 256)
        self.declare_parameter("max_num_hands", 2)
        self.declare_parameter("model_complexity", 0)
        self.declare_parameter("model_selection", 0)
        self.declare_parameter("min_detection_confidence", 0.5)
        self.declare_parameter("min_tracking_confidence", 0.5)
        self.declare_parameter("min_visibility", 0.5)
        self.declare_parameter("smooth_landmarks", True)
        self.declare_parameter("bbox_padding", 0.05)
        self.declare_parameter("static_image_mode", False)

        self.solution_name = str(self.get_parameter("solution").value).strip().lower()
        self.input_msg = str(self.get_parameter("input_msg").value).strip().lower()
        self.detections_topic = str(self.get_parameter("detections_topic").value)
        self.publish_detections = as_bool(self.get_parameter("publish_detections").value)
        self.process_every_n = max(1, int(self.get_parameter("process_every_n").value))
        self.inference_width = max(0, int(self.get_parameter("inference_width").value))
        self.frame_count = 0
        self.stats_started_at = time.monotonic()
        self.stats_frames = 0
        self.stats_infers = 0
        self.fps = 0.0

        self.solution: SolutionBase = self._create_solution(self.solution_name)
        self.solution.open(self._solution_params())
        self.last_result: Optional[InferResult] = None
        self.last_targets: list = []
        self.last_scale = (1.0, 1.0)
        self.infer_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.infer_future = None

        self.det_pub = None
        if self.publish_detections:
            # Match webviz SensorDataQoS (BEST_EFFORT) subscription.
            self.det_pub = self.create_publisher(
                TbPerceptionTargets, self.detections_topic, qos_profile_sensor_data
            )

        if self.input_msg == "file":
            self._run_file_once()
            return

        topic = str(self.get_parameter("input_topic").value).strip()
        if not topic:
            topic = self._default_topic(self.input_msg)
        self._start_subscription(self.input_msg, topic)
        self.get_logger().info(
            f"mediapipe_infer ready solution={self.solution_name} input_msg={self.input_msg} topic={topic}"
        )

    def _solution_params(self) -> dict:
        return {
            "max_num_hands": int(self.get_parameter("max_num_hands").value),
            "model_complexity": int(self.get_parameter("model_complexity").value),
            "model_selection": int(self.get_parameter("model_selection").value),
            "min_detection_confidence": float(self.get_parameter("min_detection_confidence").value),
            "min_tracking_confidence": float(self.get_parameter("min_tracking_confidence").value),
            "min_visibility": float(self.get_parameter("min_visibility").value),
            "smooth_landmarks": as_bool(self.get_parameter("smooth_landmarks").value),
            "bbox_padding": float(self.get_parameter("bbox_padding").value),
            "static_image_mode": as_bool(self.get_parameter("static_image_mode").value)
            or self.input_msg == "file",
        }

    @staticmethod
    def _create_solution(name: str) -> SolutionBase:
        if name == "hands":
            return HandsSolution()
        if name == "pose":
            return PoseSolution()
        if name in ("face_detection", "face"):
            return FaceDetectionSolution()
        raise ValueError(f"unsupported solution: {name}")

    @staticmethod
    def _default_topic(input_msg: str) -> str:
        return {
            "tb_jpeg": "/tbmem_jpeg",
            "tb_img": "/tbmem_img",
            "sensor_image": "/image_raw",
            "sensor_compressed": "/image_raw/compressed",
        }.get(input_msg, "/image_raw")

    def _start_subscription(self, input_msg: str, topic: str) -> None:
        # usb_cam / webviz publish & subscribe with SensorDataQoS (BEST_EFFORT).
        qos = qos_profile_sensor_data
        if input_msg == "sensor_image":
            self.create_subscription(Image, topic, self._on_sensor_image, qos)
        elif input_msg == "sensor_compressed":
            self.create_subscription(CompressedImage, topic, self._on_compressed, qos)
        elif input_msg == "tb_jpeg":
            self.create_subscription(TbJpegFrame, topic, self._on_tb_jpeg, qos)
        elif input_msg == "tb_img":
            profile = str(self.get_parameter("tb_img_profile").value).strip().lower()
            msg_type = {"480p": TbMsg480P, "540p": TbMsg540P, "1080p": TbMsg1080P}.get(profile)
            if msg_type is None:
                raise ValueError(f"unsupported tb_img_profile: {profile}")
            self.create_subscription(msg_type, topic, self._on_tb_img, qos)
        else:
            raise ValueError(f"unsupported input_msg: {input_msg}")

    def _run_file_once(self) -> None:
        path = str(self.get_parameter("image_file").value).strip()
        out = str(self.get_parameter("output_image").value).strip()
        if not path or not os.path.isfile(path):
            self.get_logger().error(f"image_file not found: {path}")
            return
        bgr = cv.imread(path, cv.IMREAD_COLOR)
        if bgr is None:
            self.get_logger().error(f"failed to read image: {path}")
            return
        stamp = self.get_clock().now().to_msg()
        self._process_bgr(bgr, stamp, sync=True)
        if self.last_result is not None:
            self.solution.draw(bgr, self.last_result, *self.last_scale)
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        ok = cv.imwrite(out, bgr)
        self.get_logger().info(f"file mode wrote {out} ok={ok} targets={len(self.last_targets)}")

    def _on_sensor_image(self, msg: Image) -> None:
        bgr = self._image_msg_to_bgr(msg)
        if bgr is not None:
            self._process_bgr(bgr, msg.header.stamp)

    def _on_compressed(self, msg: CompressedImage) -> None:
        data = np.frombuffer(msg.data, dtype=np.uint8)
        bgr = cv.imdecode(data, cv.IMREAD_COLOR)
        if bgr is not None:
            self._process_bgr(bgr, msg.header.stamp)

    def _on_tb_jpeg(self, msg: TbJpegFrame) -> None:
        data = np.frombuffer(bytes(msg.data[: msg.data_size]), dtype=np.uint8)
        bgr = cv.imdecode(data, cv.IMREAD_COLOR)
        if bgr is not None:
            self._process_bgr(bgr, msg.time_stamp)

    def _on_tb_img(self, msg) -> None:  # noqa: ANN001
        enc = encoding_to_str(msg.encoding).lower()
        if enc not in ("rgb8", "bgr8"):
            self.get_logger().warn(f"tb_img encoding '{enc}' not supported (rgb8/bgr8 only; no nv12)")
            return
        h, w = int(msg.height), int(msg.width)
        step = int(msg.step) if msg.step else w * 3
        buf = np.frombuffer(bytes(msg.data[: msg.data_size]), dtype=np.uint8)
        try:
            rows = buf.reshape((h, step))
            frame = rows[:, : w * 3].reshape((h, w, 3)).copy()
        except Exception as exc:  # noqa: BLE001
            self.get_logger().warn(f"failed to parse tb_img: {exc}")
            return
        bgr = frame if enc == "bgr8" else cv.cvtColor(frame, cv.COLOR_RGB2BGR)
        self._process_bgr(bgr, msg.time_stamp)

    def _image_msg_to_bgr(self, msg: Image) -> Optional[np.ndarray]:
        try:
            data = np.frombuffer(msg.data, dtype=np.uint8)
            if msg.encoding in ("bgr8", "rgb8"):
                rows = data.reshape((msg.height, msg.step))
                frame = rows[:, : msg.width * 3].reshape((msg.height, msg.width, 3))
                if msg.encoding == "rgb8":
                    frame = cv.cvtColor(frame, cv.COLOR_RGB2BGR)
                return frame.copy()
            if msg.encoding == "mono8":
                rows = data.reshape((msg.height, msg.step))
                frame = rows[:, : msg.width].reshape((msg.height, msg.width))
                return cv.cvtColor(frame, cv.COLOR_GRAY2BGR)
            if msg.encoding in ("bgra8", "rgba8"):
                rows = data.reshape((msg.height, msg.step))
                frame = rows[:, : msg.width * 4].reshape((msg.height, msg.width, 4))
                code = cv.COLOR_BGRA2BGR if msg.encoding == "bgra8" else cv.COLOR_RGBA2BGR
                return cv.cvtColor(frame, code)
        except Exception as exc:  # noqa: BLE001
            self.get_logger().warn(f"failed to convert image: {exc}")
            return None
        self.get_logger().warn(f"unsupported image encoding: {msg.encoding}")
        return None

    def _make_infer_rgb(self, bgr: np.ndarray) -> Tuple[np.ndarray, float, float]:
        full_h, full_w = bgr.shape[:2]
        if self.inference_width and full_w > self.inference_width:
            scale = self.inference_width / float(full_w)
            infer_w = self.inference_width
            infer_h = max(1, int(full_h * scale))
            resized = cv.resize(bgr, (infer_w, infer_h), interpolation=cv.INTER_AREA)
            scale_x = full_w / float(infer_w)
            scale_y = full_h / float(infer_h)
        else:
            resized = bgr
            scale_x = scale_y = 1.0
        rgb = cv.cvtColor(resized, cv.COLOR_BGR2RGB)
        return rgb, scale_x, scale_y

    def _collect_inference(self) -> None:
        if self.infer_future is None or not self.infer_future.done():
            return
        try:
            self.last_result = self.infer_future.result()
        except Exception as exc:  # noqa: BLE001
            self.get_logger().warn(f"MediaPipe inference failed: {exc}")
            self.last_result = InferResult()
        self.infer_future = None
        self.stats_infers += 1

    def _submit_inference(self, rgb: np.ndarray, scale: Tuple[float, float]) -> None:
        if self.infer_future is not None:
            return
        if self.frame_count % self.process_every_n != 0:
            return
        self.last_scale = scale
        self.infer_future = self.infer_executor.submit(self.solution.infer, rgb)

    def _process_bgr(self, bgr: np.ndarray, stamp: TimeMsg, sync: bool = False) -> None:
        self.frame_count += 1
        full_h, full_w = bgr.shape[:2]
        rgb, scale_x, scale_y = self._make_infer_rgb(bgr)
        if sync:
            t0 = time.monotonic()
            self.last_result = self.solution.infer(rgb)
            self.last_scale = (scale_x, scale_y)
            infer_ms = (time.monotonic() - t0) * 1000.0
            self.stats_infers += 1
        else:
            self._collect_inference()
            self._submit_inference(rgb, (scale_x, scale_y))
            infer_ms = 0.0

        if self.last_result is not None:
            sx, sy = self.last_scale
            self.last_targets = self.solution.to_targets(
                self.last_result, full_w, full_h, sx, sy
            )
        else:
            self.last_targets = []

        self._update_rates()
        if self.det_pub is not None:
            self._publish_detections(stamp, infer_ms)

    def _update_rates(self) -> None:
        self.stats_frames += 1
        now = time.monotonic()
        elapsed = now - self.stats_started_at
        if elapsed < 1.0:
            return
        self.fps = self.stats_frames / elapsed
        self.stats_started_at = now
        self.stats_frames = 0
        self.stats_infers = 0

    def _publish_detections(self, stamp: TimeMsg, infer_ms: float) -> None:
        msg = TbPerceptionTargets()
        msg.header.stamp = stamp
        msg.header.frame_id = "camera"
        msg.fps = int(self.fps)
        if infer_ms > 0:
            perf = TbPerf()
            perf.type = "mediapipe_infer"
            perf.time_ms_duration = float(infer_ms)
            msg.perfs.append(perf)
        for draft in self.last_targets:
            target = TbTarget()
            target.type = draft.type
            target.track_id = 0
            roi = TbRoi()
            roi.type = draft.roi_type
            x, y, w, h = draft.rect
            roi.rect.x_offset = int(x)
            roi.rect.y_offset = int(y)
            roi.rect.width = int(w)
            roi.rect.height = int(h)
            roi.confidence = float(draft.confidence)
            target.rois.append(roi)
            for ls in draft.landmark_sets:
                pts = TbPoint()
                pts.type = ls.type
                for (px, py, pz), c in zip(ls.points_xy, ls.confidences):
                    p = Point32()
                    p.x = float(px)
                    p.y = float(py)
                    p.z = float(pz)
                    pts.point.append(p)
                    pts.confidence.append(float(c))
                target.points.append(pts)
            msg.targets.append(target)
        self.det_pub.publish(msg)

    def destroy_node(self):
        try:
            self.infer_executor.shutdown(wait=False, cancel_futures=True)
        except Exception:  # noqa: BLE001
            pass
        try:
            self.solution.close()
        except Exception:  # noqa: BLE001
            pass
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = MediapipeInferNode()
    try:
        if node.input_msg == "file":
            # one-shot already done in ctor
            pass
        else:
            rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
