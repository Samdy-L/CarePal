"""单摄像头跌倒检测 Session 管理

简化版：单摄像头，按 track_id 管理 Buffer，stride 可配置。
"""

from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from STGCN import STGCN_Pipeline


@dataclass
class STGCNResult:
    """STGCN 推理结果"""
    is_fall: bool
    conf: float
    track_id: int


@dataclass
class DetectionBuffer:
    """单人检测 Buffer — 滑动窗口"""
    track_id: int
    window_size: int = 30
    stride: int = 15
    buffer: deque = field(default_factory=lambda: deque(maxlen=30))
    triggered: bool = False
    current_streak: int = 0   # 当前连续阳性窗口数

    def append(self, keypoints: np.ndarray) -> None:
        self.buffer.append(keypoints)

    def is_full(self) -> bool:
        return len(self.buffer) >= self.window_size

    def get_window(self) -> Optional[np.ndarray]:
        if len(self.buffer) < self.window_size:
            return None
        return np.array(self.buffer)

    def slide(self) -> None:
        """滑动窗口：删除最早的 stride 帧"""
        for _ in range(self.stride):
            if len(self.buffer) > 0:
                self.buffer.popleft()
        self.triggered = False


class SessionManager:
    """单摄像头检测 Session 管理"""

    def __init__(
        self,
        stgcn_model_path: str,
        stgcn_window_size: int = 30,
        stgcn_stride: int = 15,
        device: str = "cuda",
    ):
        self.pipeline = STGCN_Pipeline(
            model_path=stgcn_model_path,
            num_classes=2,
            device=device,
            window_size=stgcn_window_size,
            stride=stgcn_stride,
        )
        self.window_size = stgcn_window_size
        self.stride = stgcn_stride
        self.buffers: dict[int, DetectionBuffer] = {}
        self._lock = threading.Lock()

    def update(self, detections: list[dict], img_size: tuple = (640, 640)) -> list[STGCNResult]:
        """更新检测结果，返回 STGCN 推理结果

        Args:
            detections: YOLO 检测结果列表，每项包含 keypoints, bbox, track_id
            img_size: 原始图像尺寸 (width, height)，用于关键点归一化

        Returns:
            每人的 STGCN 推理结果
        """
        results = []

        with self._lock:
            for det in detections:
                track_id = det["track_id"]
                keypoints = det["keypoints"]  # [17, 3]

                if track_id not in self.buffers:
                    self.buffers[track_id] = DetectionBuffer(
                        track_id=track_id,
                        window_size=self.window_size,
                        stride=self.stride,
                    )

                buf = self.buffers[track_id]
                buf.append(keypoints)

                if buf.is_full() and not buf.triggered:
                    seq = buf.get_window()
                    if seq is not None:
                        pred, conf = self.pipeline.predict(seq, img_size=img_size)
                        if pred == 1:
                            buf.current_streak += 1
                        else:
                            buf.current_streak = 0
                        is_fall = buf.current_streak >= 5
                        results.append(STGCNResult(is_fall=is_fall, conf=conf, track_id=track_id))
                        buf.triggered = True
                elif buf.triggered:
                    buf.slide()

        return results
