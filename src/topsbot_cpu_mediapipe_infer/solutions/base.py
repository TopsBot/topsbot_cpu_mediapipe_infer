"""Solution plugin interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, List, Optional, Sequence, Tuple

import numpy as np


@dataclass
class LandmarkSetDraft:
    type: str
    points_xy: List[Tuple[float, float, float]]  # x, y, z in full-image pixels
    confidences: List[float]


@dataclass
class TargetDraft:
    type: str
    roi_type: str
    rect: Tuple[int, int, int, int]  # x, y, w, h
    confidence: float
    landmark_sets: List[LandmarkSetDraft] = field(default_factory=list)


@dataclass
class InferResult:
    targets: List[TargetDraft] = field(default_factory=list)
    raw: Any = None


class SolutionBase(ABC):
    name: str = "base"

    @abstractmethod
    def open(self, params: dict) -> None:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def infer(self, rgb_infer: np.ndarray) -> InferResult:
        """Run on RGB image (inference resolution)."""
        raise NotImplementedError

    @abstractmethod
    def to_targets(
        self,
        result: InferResult,
        full_w: int,
        full_h: int,
        scale_x: float,
        scale_y: float,
    ) -> List[TargetDraft]:
        """Map inference-space result to full-image TargetDraft list."""
        raise NotImplementedError

    @abstractmethod
    def draw(self, bgr_full: np.ndarray, result: InferResult, scale_x: float, scale_y: float) -> None:
        raise NotImplementedError


def clamp_rect(x: int, y: int, w: int, h: int, full_w: int, full_h: int) -> Tuple[int, int, int, int]:
    x = max(0, min(x, full_w - 1))
    y = max(0, min(y, full_h - 1))
    w = max(1, min(w, full_w - x))
    h = max(1, min(h, full_h - y))
    return x, y, w, h


def landmarks_to_bbox(
    pts: Sequence[Tuple[float, float, float]],
    full_w: int,
    full_h: int,
    padding: float = 0.05,
    min_conf: Optional[Sequence[float]] = None,
    conf_thresh: float = 0.0,
) -> Optional[Tuple[int, int, int, int]]:
    xs: List[float] = []
    ys: List[float] = []
    for i, (x, y, _z) in enumerate(pts):
        if min_conf is not None and i < len(min_conf) and min_conf[i] < conf_thresh:
            continue
        xs.append(x)
        ys.append(y)
    if not xs:
        return None
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    bw, bh = x1 - x0, y1 - y0
    pad_x = bw * padding
    pad_y = bh * padding
    return clamp_rect(
        int(x0 - pad_x),
        int(y0 - pad_y),
        int(bw + 2 * pad_x),
        int(bh + 2 * pad_y),
        full_w,
        full_h,
    )
