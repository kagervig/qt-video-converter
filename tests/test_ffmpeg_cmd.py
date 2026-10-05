"""Tests for the pure-Python command builders (M1)."""

from converter.ffmpeg_cmd import (
    build_encode_args,
    build_probe_args,
    default_output_path,
)


def test_encode_args_sets_input_and_output():
    args = build_encode_args("/videos/clip.mov", "/videos/clip_h264.mp4")
    assert args[args.index("-i") + 1] == "/videos/clip.mov"
    assert args[-1] == "/videos/clip_h264.mp4"


def test_encode_args_use_h264_codec():
    args = build_encode_args("in.mov", "out.mp4")
    assert args[args.index("-c:v") + 1] == "libx264"


def test_encode_args_copy_audio():
    args = build_encode_args("in.mov", "out.mp4")
    assert args[args.index("-c:a") + 1] == "copy"


def test_encode_args_emit_machine_progress():
    args = build_encode_args("in.mov", "out.mp4")
    assert args[args.index("-progress") + 1] == "pipe:1"


def test_probe_args_request_duration():
    args = build_probe_args("/videos/clip.mov")
    assert "format=duration" in args
    assert args[-1] == "/videos/clip.mov"


def test_default_output_path_is_sibling_with_suffix():
    assert default_output_path("/videos/clip.mov") == "/videos/clip_h264.mp4"


def test_default_output_path_never_equals_source():
    source = "/videos/clip.mp4"
    assert default_output_path(source) != source
