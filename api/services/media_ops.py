"""Dependency-light local media operations for the UGC factory.

All operations are deterministic subprocess calls with argument arrays (no
shell). ffmpeg/ffprobe are installed in the production image by this change.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any


class MediaOps:
    def __init__(self) -> None:
        self.ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
        self.ffprobe = shutil.which("ffprobe") or "ffprobe"

    def _run(self, args: list[str], *, capture_stdout: bool = False) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            args,
            check=False,
            stdout=subprocess.PIPE if capture_stdout else subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=180,
        )

    def available(self) -> bool:
        return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))

    def duration_seconds(self, source: Path) -> float | None:
        result = self._run(
            [
                self.ffprobe,
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(source),
            ],
            capture_stdout=True,
        )
        if result.returncode != 0:
            return None
        try:
            return float(result.stdout.decode("utf-8").strip())
        except ValueError:
            return None

    def has_audio(self, source: Path) -> bool:
        result = self._run(
            [
                self.ffprobe,
                "-v", "error",
                "-select_streams", "a",
                "-show_entries", "stream=index",
                "-of", "csv=p=0",
                str(source),
            ],
            capture_stdout=True,
        )
        return result.returncode == 0 and bool(result.stdout.strip())

    def trim_tail(self, source: Path, destination: Path, seconds: float = 0.35) -> dict[str, Any]:
        duration = self.duration_seconds(source)
        if duration is None or duration <= seconds + 0.1:
            return {"ok": False, "error": "invalid_source_duration", "duration": duration}
        keep = max(0.1, duration - seconds)
        destination.parent.mkdir(parents=True, exist_ok=True)
        result = self._run(
            [
                self.ffmpeg,
                "-y",
                "-i", str(source),
                "-t", f"{keep:.3f}",
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "20",
                "-c:a", "aac",
                "-movflags", "+faststart",
                str(destination),
            ]
        )
        if result.returncode != 0:
            return {"ok": False, "error": "ffmpeg_trim_failed", "detail": result.stderr.decode("utf-8", errors="ignore")[-800:]}
        return {"ok": True, "path": str(destination), "source_duration": duration, "trimmed_duration": keep}

    def extract_last_frame(self, source: Path, destination: Path) -> dict[str, Any]:
        destination.parent.mkdir(parents=True, exist_ok=True)
        result = self._run(
            [self.ffmpeg, "-y", "-sseof", "-0.05", "-i", str(source), "-frames:v", "1", "-q:v", "2", str(destination)]
        )
        if result.returncode != 0:
            return {"ok": False, "error": "seed_frame_extract_failed", "detail": result.stderr.decode("utf-8", errors="ignore")[-800:]}
        return {"ok": True, "path": str(destination)}

    def extract_first_frame(self, source: Path, destination: Path) -> dict[str, Any]:
        destination.parent.mkdir(parents=True, exist_ok=True)
        result = self._run(
            [self.ffmpeg, "-y", "-i", str(source), "-frames:v", "1", "-q:v", "2", str(destination)]
        )
        if result.returncode != 0:
            return {"ok": False, "error": "first_frame_extract_failed", "detail": result.stderr.decode("utf-8", errors="ignore")[-800:]}
        return {"ok": True, "path": str(destination)}

    def _raw_rgb(self, source: Path) -> bytes | None:
        result = self._run(
            [
                self.ffmpeg,
                "-v", "error",
                "-i", str(source),
                "-vf", "scale=64:64",
                "-frames:v", "1",
                "-f", "rawvideo",
                "-pix_fmt", "rgb24",
                "pipe:1",
            ],
            capture_stdout=True,
        )
        return result.stdout if result.returncode == 0 and result.stdout else None

    def seam_diff(self, left: Path, right: Path) -> float:
        a = self._raw_rgb(left)
        b = self._raw_rgb(right)
        if not a or not b or len(a) != len(b):
            return 1.0
        total = sum(abs(x - y) for x, y in zip(a, b))
        return total / (len(a) * 255.0)

    def stitch(self, first: Path, second: Path, destination: Path) -> dict[str, Any]:
        destination.parent.mkdir(parents=True, exist_ok=True)
        audio = self.has_audio(first) and self.has_audio(second)
        if audio:
            filter_complex = "[0:v:0][0:a:0][1:v:0][1:a:0]concat=n=2:v=1:a=1[v][a]"
            args = [
                self.ffmpeg, "-y", "-i", str(first), "-i", str(second),
                "-filter_complex", filter_complex,
                "-map", "[v]", "-map", "[a]",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                "-c:a", "aac", "-movflags", "+faststart", str(destination),
            ]
        else:
            filter_complex = "[0:v:0][1:v:0]concat=n=2:v=1:a=0[v]"
            args = [
                self.ffmpeg, "-y", "-i", str(first), "-i", str(second),
                "-filter_complex", filter_complex,
                "-map", "[v]", "-an",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                "-movflags", "+faststart", str(destination),
            ]
        result = self._run(args)
        if result.returncode != 0:
            return {"ok": False, "error": "ffmpeg_stitch_failed", "detail": result.stderr.decode("utf-8", errors="ignore")[-800:]}
        return {"ok": True, "path": str(destination), "audio": audio}


def get_media_ops() -> MediaOps:
    return MediaOps()
