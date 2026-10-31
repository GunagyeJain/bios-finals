"""H.264 MP4 writer (browser-playable; OpenCV's pip wheels can't encode H.264). Uses the ffmpeg
binary bundled with imageio-ffmpeg. Owner: Gunagye."""
from __future__ import annotations

from pathlib import Path

import numpy as np


class H264Writer:
    """`with H264Writer(path, fps, (w, h)) as vw: vw.write(bgr_img)`. Width and height must be even."""

    def __init__(self, path: Path, fps: float, size: tuple[int, int], crf: int = 26):
        import imageio_ffmpeg

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.size = size
        self._gen = imageio_ffmpeg.write_frames(
            str(path), size, fps=fps, codec="libx264", pix_fmt_in="bgr24", pix_fmt_out="yuv420p",
            macro_block_size=2, ffmpeg_log_level="error",
            output_params=["-crf", str(crf), "-preset", "veryfast", "-movflags", "+faststart"])
        self._gen.send(None)

    def write(self, img: np.ndarray) -> None:
        h, w = img.shape[:2]
        assert (w, h) == self.size, f"frame {w}x{h} != writer {self.size}"
        self._gen.send(np.ascontiguousarray(img).tobytes())

    def close(self) -> None:
        self._gen.close()

    def __enter__(self) -> "H264Writer":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
