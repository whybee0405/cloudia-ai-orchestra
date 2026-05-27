"""All ffmpeg operations as Python functions. Never call ffmpeg directly elsewhere."""
import subprocess
import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def _run(cmd: list[str]) -> None:
    """Run ffmpeg command, raising RuntimeError on non-zero exit with full stderr."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed (exit {result.returncode}):\n{result.stderr}")
    logger.debug("ffmpeg: %s", " ".join(cmd[:6]))


def trim_clip(input_path: str, output_path: str, duration_sec: float) -> None:
    """Trim video to exact duration from the start."""
    _run(["ffmpeg", "-y", "-i", input_path, "-t", str(duration_sec),
          "-c:v", "libx264", "-c:a", "aac", output_path])


def add_audio(video_path: str, audio_path: str, output_path: str) -> None:
    """Mix audio track into video, replacing existing audio."""
    _run(["ffmpeg", "-y", "-i", video_path, "-i", audio_path,
          "-c:v", "copy", "-map", "0:v:0", "-map", "1:a:0",
          "-shortest", output_path])


def add_background_music(video_path: str, music_path: str, output_path: str, music_volume: float = 0.15) -> None:
    """Mix background music at given volume under existing audio."""
    _run(["ffmpeg", "-y", "-i", video_path, "-i", music_path,
          "-filter_complex",
          f"[1:a]volume={music_volume}[bg];[0:a][bg]amix=inputs=2:duration=first[a]",
          "-map", "0:v", "-map", "[a]", "-c:v", "copy", output_path])


def add_text_overlay(
    input_path: str, output_path: str, text: str,
    font_color: str = "white", font_size: int = 48,
    x: str = "(w-text_w)/2", y: str = "h-100",
) -> None:
    """Burn text overlay into video."""
    safe_text = text.replace("'", "\\'").replace(":", "\\:")
    _run([
        "ffmpeg", "-y", "-i", input_path,
        "-vf", f"drawtext=text='{safe_text}':fontcolor={font_color}:fontsize={font_size}:x={x}:y={y}",
        "-c:a", "copy", output_path,
    ])


def concatenate(input_paths: list[str], output_path: str) -> None:
    """Concatenate video files in order."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        for p in input_paths:
            f.write(f"file '{p}'\n")
        concat_file = f.name
    try:
        _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_file,
              "-c", "copy", output_path])
    finally:
        os.unlink(concat_file)


def resize_video(input_path: str, output_path: str, width: int, height: int) -> None:
    """Resize/rescale video to target resolution. Pads with blurred background for aspect ratio mismatch."""
    _run([
        "ffmpeg", "-y", "-i", input_path,
        "-vf", (
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black"
        ),
        "-c:v", "libx264", "-c:a", "aac", "-preset", "fast", output_path,
    ])


def burn_subtitles(input_path: str, srt_path: str, output_path: str) -> None:
    """Burn SRT subtitles into video."""
    safe_srt = srt_path.replace(":", "\\:")
    _run(["ffmpeg", "-y", "-i", input_path,
          "-vf", f"subtitles='{safe_srt}'",
          "-c:a", "copy", output_path])


def apply_colour_grade(input_path: str, output_path: str, lut_path: str) -> None:
    """Apply a .cube LUT colour grade to video."""
    safe_lut = lut_path.replace(":", "\\:")
    _run(["ffmpeg", "-y", "-i", input_path,
          "-vf", f"lut3d='{safe_lut}'",
          "-c:a", "copy", output_path])


def add_silent_audio(input_path: str, output_path: str) -> None:
    """Add a silent audio track to a video that has no audio."""
    _run(["ffmpeg", "-y", "-i", input_path,
          "-f", "lavfi", "-i", "aevalsrc=0",
          "-map", "0:v", "-map", "1:a",
          "-c:v", "copy", "-c:a", "aac", "-shortest", output_path])


def get_duration(path: str) -> float:
    """Return video/audio duration in seconds using ffprobe."""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")
    return float(result.stdout.strip())


def transcode(input_path: str, output_path: str, width: int, height: int, max_mb: float) -> None:
    """
    Transcode video to H.264/AAC at target resolution.
    If file would exceed max_mb, lower bitrate accordingly.
    """
    target_bytes = max_mb * 1024 * 1024
    duration = get_duration(input_path)
    target_bitrate = int((target_bytes * 8) / duration / 1000)  # kbps
    video_bitrate = max(500, min(target_bitrate - 128, 8000))  # reserve 128k for audio
    _run([
        "ffmpeg", "-y", "-i", input_path,
        "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black",
        "-c:v", "libx264", "-b:v", f"{video_bitrate}k",
        "-c:a", "aac", "-b:a", "128k",
        "-preset", "medium", output_path,
    ])
