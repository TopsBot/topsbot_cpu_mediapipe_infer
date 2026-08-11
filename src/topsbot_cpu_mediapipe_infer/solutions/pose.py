"""MediaPipe Pose solution."""

from __future__ import annotations

from typing import List

import mediapipe as mp
import numpy as np

from .base import InferResult, LandmarkSetDraft, SolutionBase, TargetDraft, landmarks_to_bbox


class PoseSolution(SolutionBase):
    name = "pose"

    def __init__(self) -> None:
        self._pose = None
        self._mp_pose = mp.solutions.pose
        self._draw = mp.solutions.drawing_utils
        self._padding = 0.05
        self._min_visibility = 0.5

    def open(self, params: dict) -> None:
        self._padding = float(params.get("bbox_padding", 0.05))
        self._min_visibility = float(params.get("min_visibility", 0.5))
        self._pose = self._mp_pose.Pose(
            static_image_mode=bool(params.get("static_image_mode", False)),
            model_complexity=int(params.get("model_complexity", 0)),
            smooth_landmarks=bool(params.get("smooth_landmarks", True)),
            min_detection_confidence=float(params.get("min_detection_confidence", 0.5)),
            min_tracking_confidence=float(params.get("min_tracking_confidence", 0.5)),
        )

    def close(self) -> None:
        if self._pose is not None:
            self._pose.close()
            self._pose = None

    def infer(self, rgb_infer: np.ndarray) -> InferResult:
        assert self._pose is not None
        return InferResult(raw=self._pose.process(rgb_infer))

    def to_targets(
        self,
        result: InferResult,
        full_w: int,
        full_h: int,
        scale_x: float,
        scale_y: float,
    ) -> List[TargetDraft]:
        del scale_x, scale_y
        raw = result.raw
        if raw is None or raw.pose_landmarks is None:
            return []
        pts = []
        confs = []
        for lm in raw.pose_landmarks.landmark:
            pts.append((lm.x * full_w, lm.y * full_h, lm.z))
            confs.append(float(lm.visibility))
        bbox = landmarks_to_bbox(
            pts,
            full_w,
            full_h,
            padding=self._padding,
            min_conf=confs,
            conf_thresh=self._min_visibility,
        )
        if bbox is None:
            return []
        return [
            TargetDraft(
                type="person",
                roi_type="body",
                rect=bbox,
                confidence=1.0,
                landmark_sets=[
                    LandmarkSetDraft(type="body_kps", points_xy=pts, confidences=confs)
                ],
            )
        ]

    def draw(self, bgr_full: np.ndarray, result: InferResult, scale_x: float, scale_y: float) -> None:
        del scale_x, scale_y
        raw = result.raw
        if raw is None or raw.pose_landmarks is None:
            return
        self._draw.draw_landmarks(bgr_full, raw.pose_landmarks, self._mp_pose.POSE_CONNECTIONS)
