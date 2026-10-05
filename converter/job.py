"""The Job data model: one video file to convert.

Pure data, no Qt. The runner (M2) updates `status`/`progress`; the queue (M5)
walks a list of Jobs; the UI table (M4) renders them.
"""

from dataclasses import dataclass, field
from enum import Enum

from converter.ffmpeg_cmd import default_output_path


class JobStatus(str, Enum):
    PENDING = "Pending"
    ENCODING = "Encoding"
    DONE = "Done"
    FAILED = "Failed"
    CANCELLED = "Cancelled"  # used in M7


@dataclass
class Job:
    input_path: str
    status: JobStatus = JobStatus.PENDING
    progress: int = 0  # 0-100
    output_path: str = field(default="")

    def __post_init__(self) -> None:
        """Default the output path to `<name>_h264.mp4` when none was given."""
        if not self.output_path:
            self.output_path = default_output_path(self.input_path)
