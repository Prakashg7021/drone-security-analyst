"""Optional OpenCV frame sampling; extracted pixels are not classified."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


def extract_video_frames(
    video_path: str | Path,
    interval_seconds: float = 5.0,
    max_frames: int = 200,
    output_dir: str | Path | None = None,
) -> list[dict[str, Any]]:
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError("OpenCV is required for video extraction; install opencv-python-headless.") from exc

    if interval_seconds <= 0 or max_frames <= 0:
        raise ValueError("interval_seconds and max_frames must be positive")
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        capture.release()
        raise ValueError(f"Unable to open video file: {video_path}")
    fps = capture.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        capture.release()
        raise ValueError("Video does not provide a usable frame rate")
    interval = max(1, int(fps * interval_seconds))
    captured: list[dict[str, Any]] = []
    frame_index = 0
    base_time = datetime.now().replace(microsecond=0)
    destination = Path(output_dir) if output_dir else Path(video_path).parent / "extracted_frames"
    destination.mkdir(parents=True, exist_ok=True)
    try:
        while len(captured) < max_frames:
            ok, image = capture.read()
            if not ok:
                break
            if frame_index % interval == 0:
                timestamp = base_time + timedelta(seconds=frame_index / fps)
                frame_id = f"VIDEO-{Path(video_path).stem}-{frame_index:08d}"
                image_path = destination / f"{frame_id}.jpg"
                if not cv2.imwrite(str(image_path), image):
                    raise OSError(f"Could not write extracted video frame: {image_path}")
                captured.append(
                    {
                        "frame_id": frame_id,
                        "timestamp": timestamp.isoformat(timespec="seconds"),
                        "description": (
                            "Uploaded video frame sampled by OpenCV; visual content "
                            "was not analyzed."
                        ),
                        "telemetry": {
                            "timestamp": timestamp.isoformat(timespec="seconds"),
                            "status": "unavailable",
                            "zone": "unknown",
                            "simulated": False,
                            "image_path": str(image_path.resolve()),
                        },
                        "source": "video",
                    }
                )
            frame_index += 1
    finally:
        capture.release()
    return captured
