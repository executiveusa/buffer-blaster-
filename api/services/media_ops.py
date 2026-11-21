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


    def _dimensions(self, source: Path) -> tuple[int, int] | None:
        result = self._run(
            [
                self.ffprobe,
                "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height",
                "-of", "csv=p=0:s=x",
                str(source),
            ],
            capture_stdout=True,
        )
        if result.returncode != 0:
            return None
        try:
            width, height = (int(part) for part in result.stdout.decode("utf-8").strip().split("x")[:2])
        except ValueError:
            return None
        return (width, height) if width > 0 and height > 0 else None

    def append_end_card(
        self,
        source: Path,
        destination: Path,
        lines: list[str] | tuple[str, ...],
        *,
        seconds: float = 2.0,
        background_image: Path | None = None,
    ) -> dict[str, Any]:
        """Append a local text end card (no paid generation) matching the source size.

        Text is passed through files, never interpolated into the filter graph,
        so price strings like "$70" and quotes need no escaping.
        """
        clean = [" ".join(str(line).split()) for line in lines if str(line).strip()][:4]
        if not clean:
            return {"ok": False, "error": "end_card_lines_required"}
        size = self._dimensions(source)
        if size is None:
            return {"ok": False, "error": "invalid_source_video"}
        width, height = size
        seconds = max(0.5, min(5.0, float(seconds)))
        destination.parent.mkdir(parents=True, exist_ok=True)
        font = _font_option()
        audio = self.has_audio(source)

        text_files: list[Path] = []
        draws: list[str] = []
        def fit(line: str, cap: int) -> int:
            # Bold sans glyphs average ~0.66em wide; keep each line inside 88% of the frame.
            return max(16, min(cap, int(width * 0.88 / (0.66 * max(1, len(line))))))

        sizes = [fit(line, width // 9 if index == 0 else width // 15) for index, line in enumerate(clean)]
        gap = int(width * 0.04)
        block = sum(sizes) + gap * (len(clean) - 1)
        y = (height - block) // 2 if background_image is None else int(height * 0.68)
        for index, line in enumerate(clean):
            text_file = destination.parent / f"{destination.stem}-endcard-{index}.txt"
            text_file.write_text(line, encoding="utf-8")
            text_files.append(text_file)
            font_size = sizes[index]
            draws.append(
                f"drawtext={font}textfile='{text_file}':fontcolor=white:fontsize={font_size}"
                f":x=(w-text_w)/2:y={y}:borderw=3:bordercolor=black@0.6"
            )
            y += font_size + gap

        inputs = [self.ffmpeg, "-y", "-i", str(source)]
        if background_image is not None:
            inputs += ["-loop", "1", "-t", f"{seconds:.2f}", "-i", str(background_image)]
            card = (
                f"[1:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
                f"crop={width}:{height},setsar=1,fps=30,format=yuv420p,"
                f"drawbox=x=0:y=ih*0.62:w=iw:h=ih*0.38:color=black@0.55:t=fill,{','.join(draws)}[card]"
            )
        else:
            inputs += ["-f", "lavfi", "-t", f"{seconds:.2f}", "-i", f"color=c=0x0b1f3a:s={width}x{height}:r=30"]
            card = f"[1:v]setsar=1,format=yuv420p,{','.join(draws)}[card]"
        main = "[0:v:0]fps=30,setsar=1,format=yuv420p[main]"
        if audio:
            inputs += ["-f", "lavfi", "-t", f"{seconds:.2f}", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"]
            graph = (
                f"{main};{card};[0:a:0]aresample=48000,aformat=channel_layouts=stereo[a0];"
                "[main][a0][card][2:a]concat=n=2:v=1:a=1[v][a]"
            )
            maps = ["-map", "[v]", "-map", "[a]", "-c:a", "aac"]
        else:
            graph = f"{main};{card};[main][card]concat=n=2:v=1:a=0[v]"
            maps = ["-map", "[v]", "-an"]
        args = inputs + [
            "-filter_complex", graph, *maps,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-movflags", "+faststart", str(destination),
        ]
        try:
            result = self._run(args)
        finally:
            for text_file in text_files:
                text_file.unlink(missing_ok=True)
        if result.returncode != 0:
            return {"ok": False, "error": "ffmpeg_end_card_failed", "detail": result.stderr.decode("utf-8", errors="ignore")[-800:]}
        return {"ok": True, "path": str(destination), "audio": audio, "end_card_seconds": seconds}


_FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "/usr/share/fonts/opentype/inter/Inter-Bold.otf",
)


def _font_option() -> str:
    for candidate in _FONT_CANDIDATES:
        if Path(candidate).is_file():
            return f"fontfile='{candidate}':"
    return "font='Sans':"


def get_media_ops() -> MediaOps:
    return MediaOps()
