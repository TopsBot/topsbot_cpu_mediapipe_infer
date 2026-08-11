"""MediaPipe Face Detection solution."""

from __future__ import annotations

from typing import List

import cv2 as cv
import mediapipe as mp
import numpy as np

from .base import InferResult, LandmarkSetDraft, SolutionBase, TargetDraft, clamp_rect


class FaceDetectionSolution(SolutionBase):
    name = "face_detection"

    def __init__(self) -> None:
        self._face = None
        self._mp_face = mp.solutions.face_detection

    def open(self, params: dict) -> None:
        self._face = self._mp_face.FaceDetection(
            model_selection=int(params.get("model_selection", 0)),
            min_detection_confidence=float(params.get("min_detection_confidence", 0.5)),
        )

    def close(self) -> None:
        if self._face is not None:
            self._face.close()
            self._face = None

    def infer(self, rgb_infer: np.ndarray) -> InferResult:
        assert self._face is not None
        return InferResult(raw=self._face.process(rgb_infer))

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
        if raw is None or not raw.detections:
            return []
        out: List[TargetDraft] = []
        for det in raw.detections:
            box = det.location_data.relative_bounding_box
            x = int(box.xmin * full_w)
            y = int(box.ymin * full_h)
            w = int(box.width * full_w)
            h = int(box.height * full_h)
            rect = clamp_rect(x, y, w, h, full_w, full_h)
            conf = float(det.score[0]) if det.score else 1.0
            kps: List[tuple] = []
            confs: List[float] = []
            for kp in det.location_data.relative_keypoints:
                kps.append((kp.x * full_w, kp.y * full_h, 0.0))
                confs.append(conf)
            landmark_sets = []
            if kps:
                landmark_sets.append(
                    LandmarkSetDraft(type="face_kps", points_xy=kps, confidences=confs)
                )
            out.append(
                TargetDraft(
                    type="face",
                    roi_type="face",
                    rect=rect,
                    confidence=conf,
                    landmark_sets=landmark_sets,
                )
            )
        return out

    def draw(self, bgr_full: np.ndarray, result: InferResult, scale_x: float, scale_y: float) -> None:
        del scale_x, scale_y
        raw = result.raw
        if raw is None or not raw.detections:
            return
        h, w = bgr_full.shape[:2]
        for det in raw.detections:
            box = det.location_data.relative_bounding_box
            x1 = int(box.xmin * w)
            y1 = int(box.ymin * h)
            x2 = int((box.xmin + box.width) * w)
            y2 = int((box.ymin + box.height) * h)
            cv.rectangle(bgr_full, (x1, y1), (x2, y2), (0, 200, 0), 2)
            for kp in det.location_data.relative_keypoints:
                cv.circle(bgr_full, (int(kp.x * w), int(kp.y * h)), 2, (0, 0, 255), -1)
