"""Tests for video-only download command and client functions."""

import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from bili_cli import client
from bili_cli.cli import cli
from bili_cli.exceptions import NetworkError


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_video_info():
    return {
        "title": "Test Video",
        "duration": 120,
        "owner": {"name": "TestUP", "mid": 123},
    }


@pytest.mark.asyncio
async def test_get_video_stream_dash_prefers_video_slot():
    mock_download_data = {"dash": {"video": [{"baseUrl": "https://example.com/video.m4s"}]}}
    mock_stream = MagicMock()
    mock_stream.url = "https://example.com/video.m4s"
    mock_stream.video_quality.name = "_1080P"
    mock_stream.video_quality.value = 80
    mock_stream.video_codecs.value = "avc"

    with patch("bili_cli.client.video.Video") as MockVideo, \
         patch("bili_cli.client.video.VideoDownloadURLDataDetecter") as MockDetector:
        MockVideo.return_value.get_download_url = AsyncMock(return_value=mock_download_data)
        detector_instance = MockDetector.return_value
        detector_instance.check_flv_mp4_stream.return_value = False
        detector_instance.detect_best_streams.return_value = [mock_stream, None]

        stream = await client.get_video_stream("BV1test12345", max_quality="1080p", codec="avc")

    assert stream.url == "https://example.com/video.m4s"
    assert stream.quality == "1080p"
    assert stream.codec == "avc"
    assert stream.extension == "mp4"


@pytest.mark.asyncio
async def test_download_video_uses_stream_downloader():
    with patch("bili_cli.client.download_stream", new_callable=AsyncMock, return_value=123) as mock_download:
        nbytes = await client.download_video("https://example.com/video.m4s", "out.mp4")

    assert nbytes == 123
    mock_download.assert_awaited_once_with("https://example.com/video.m4s", "out.mp4", label="video")


def test_download_command_downloads_video_only(runner, mock_video_info):
    stream = client.VideoStreamInfo(
        url="https://example.com/video.m4s",
        quality="1080p",
        codec="avc",
        extension="mp4",
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("bili_cli.commands.common.get_credential", return_value=None), \
             patch("bili_cli.client.extract_bvid", return_value="BV1test12345"), \
             patch("bili_cli.client.get_video_info", new_callable=AsyncMock, return_value=mock_video_info), \
             patch("bili_cli.client.get_video_stream", new_callable=AsyncMock, return_value=stream) as mock_stream, \
             patch("bili_cli.client.download_video", new_callable=AsyncMock, return_value=1024 * 1024) as mock_download:
            result = runner.invoke(cli, ["download", "BV1test12345", "--quality", "1080p", "-o", tmpdir])

    assert result.exit_code == 0
    assert "Video saved:" in result.output
    mock_stream.assert_awaited_once()
    output_path = mock_download.await_args.args[1]
    assert output_path == os.path.join(tmpdir, "Test Video [BV1test12345] [1080p-avc].mp4")


def test_download_command_invalid_bvid(runner):
    result = runner.invoke(cli, ["download", "invalid"])
    assert result.exit_code != 0


def test_download_command_download_error_returns_nonzero(runner, mock_video_info):
    stream = client.VideoStreamInfo(
        url="https://example.com/video.m4s",
        quality="720p",
        codec="avc",
        extension="mp4",
    )
    with patch("bili_cli.commands.common.get_credential", return_value=None), \
         patch("bili_cli.client.extract_bvid", return_value="BV1test12345"), \
         patch("bili_cli.client.get_video_info", new_callable=AsyncMock, return_value=mock_video_info), \
         patch("bili_cli.client.get_video_stream", new_callable=AsyncMock, return_value=stream), \
         patch("bili_cli.client.download_video", new_callable=AsyncMock, side_effect=NetworkError("timeout")):
        result = runner.invoke(cli, ["download", "BV1test12345"])

    assert result.exit_code != 0
    assert "下载视频" in result.output
