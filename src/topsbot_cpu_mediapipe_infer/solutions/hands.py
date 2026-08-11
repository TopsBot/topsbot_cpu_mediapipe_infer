"""MediaPipe Hands solution."""

from __future__ import annotations

from typing import List

import mediapipe as mp
import numpy as np

from .base import InferResult, LandmarkSetDraft, SolutionBase, TargetDraft, landmarks_to_bbox


class HandsSolution(SolutionBase):
    name = "hands"

    def __init__(self) -> None:
        self._hands = None
        self._mp_hands = mp.solutions.hands
        self._draw = mp.solutions.drawing_utils
        self._padding = 0.05

    def open(self, params: dict) -> None:
        self._padding = float(params.get("bbox_padding", 0.05))
        self._hands = self._mp_hands.Hands(
            static_image_mode=bool(params.get("static_image_mode", False)),
            max_num_hands=int(params.get("max_num_hands", 2)),
            model_complexity=int(params.get("model_complexity", 0)),
            min_detection_confidence=float(params.get("min_detection_confidence", 0.5)),
            min_tracking_confidence=float(params.get("min_tracking_confidence", 0.5)),
        )

    def close(self) -> None:
        if self._hands is not None:
            self._hands.close()
            self._hands = None

    def infer(self, rgb_infer: np.ndarray) -> InferResult:
        assert self._hands is not None
        return InferResult(raw=self._hands.process(rgb_infer))

    def to_targets(
        self,
        result: InferResult,
        full_w: int,
        full_h: int,
        scale_x: float,
        scale_y: float,
    ) -> List[TargetDraft]:
        del scale_x, scale_y  # normalized landmarks map directly when aspect-preserved
        raw = result.raw
        if raw is None or not raw.multi_hand_landmarks:
            return []
        out: List[TargetDraft] = []
        handedness = raw.multi_handedness or []
        for idx, hand_lms in enumerate(raw.multi_hand_landmarks):
            pts = [(lm.x * full_w, lm.y * full_h, lm.z) for lm in hand_lms.landmark]
            confs = [1.0] * len(pts)
            conf = 1.0
            if idx < len(handedness):
                conf = float(handedness[idx].classification[0].score)
            bbox = landmarks_to_bbox(pts, full_w, full_h, padding=self._padding)
            if bbox is None:
                continue
            out.append(
                TargetDraft(
                    type="hand",
                    roi_type="hand",
                    rect=bbox,
                    confidence=conf,
                    landmark_sets=[
                        LandmarkSetDraft(type="hand_kps", points_xy=pts, confidences=confs)
                    ],
                )
            )
        return out

    def draw(self, bgr_full: np.ndarray, result: InferResult, scale_x: float, scale_y: float) -> None:
        del scale_x, scale_y
        raw = result.raw
        if raw is None or not raw.multi_hand_landmarks:
            return
        for hand_lms in raw.multi_hand_landmarks:
            self._draw.draw_landmarks(bgr_full, hand_lms, self._mp_hands.HAND_CONNECTIONS)
