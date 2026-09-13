from PIL import Image

from glorydial.formats import writer
from glorydial.formats.errors import ValidationError
from glorydial.model.block import Block, Frame, Project


def _project_with_block(w=4, h=4, frame_count=1, type_id=17):
    project = Project(screen_width=100, screen_height=100)
    block = project.add_block(type_id)
    for _ in range(frame_count):
        block.frames.append(Frame(Image.new("RGBA", (w, h), (10, 20, 30, 255))))
    return project


def test_mismatched_frame_sizes_rejected():
    project = _project_with_block(frame_count=1)
    project.blocks[17].frames.append(Frame(Image.new("RGBA", (5, 5))))
    report = writer.validate_project(project, version=3)
    assert any("different sizes" in e for e in report.errors)


def test_odd_width_rejected_only_for_v3():
    project = _project_with_block(w=5, h=4)
    report_v3 = writer.validate_project(project, version=3)
    report_v1 = writer.validate_project(project, version=1)
    assert any("even" in e for e in report_v3.errors)
    assert not any("even" in e for e in report_v1.errors)


def test_too_many_frames_rejected():
    project = _project_with_block(frame_count=1)
    # Directly corrupt the frame list length representation by adding
    # 256 frames total.
    for _ in range(256):
        project.blocks[17].frames.append(Frame(Image.new("RGBA", (4, 4))))
    report = writer.validate_project(project, version=1)
    assert any("maximum supported is 255" in e for e in report.errors)


def test_hand_arrow_fields_out_of_range_rejected():
    project = Project()
    hand = project.add_block(1)
    hand.frames.append(Frame(Image.new("RGBA", (4, 4))))
    hand.arrow_width = 300
    report = writer.validate_project(project, version=1)
    assert any("ArrowWidth" in e for e in report.errors)


def test_compile_raises_validation_error_with_readable_message():
    project = _project_with_block(w=5, h=4)
    try:
        writer.compile_bin(project, version=3)
        assert False, "expected ValidationError"
    except ValidationError as e:
        assert "even" in str(e)


def test_unsupported_version_rejected():
    project = _project_with_block()
    report = writer.validate_project(project, version=7)
    assert report.errors


def test_max_file_size_enforced(monkeypatch):
    project = _project_with_block()
    monkeypatch.setattr(writer, "MAX_FILE_SIZE", 10)  # force a tiny cap
    try:
        writer.compile_bin(project, version=1)
        assert False, "expected ValidationError"
    except ValidationError as e:
        assert "1024 KB" in str(e) or "exceeds" in str(e)
