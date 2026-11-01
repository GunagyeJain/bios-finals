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


def h264_preview(src: Path, dest: Path, width: int = 960, crf: int = 28) -> Path:
    """Browser-playable copy of a source clip (the camera files are HEVC, which most browsers can't decode).
    Scaled to `width`, no audio track: voices are personal data and never leave the source file."""
    import subprocess

    import imageio_ffmpeg

    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".part.mp4")
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(src), "-an",
                    "-vf", f"scale={width}:-2", "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf),
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(tmp)], check=True)
    tmp.replace(dest)
    return dest
