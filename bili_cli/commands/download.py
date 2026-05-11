"""Video-only download command."""

from __future__ import annotations

import os
import re

import click

from .common import console, extract_bvid_or_exit, get_credential, run_or_exit

DEFAULT_OUTPUT_DIR = "downloads"
QUALITY_CHOICES = ["best", "1080p", "1080p-plus", "1080p60", "720p", "480p", "360p", "4k", "8k"]
CODEC_CHOICES = ["avc", "hev", "av1", "auto"]


def _sanitize_filename(title: str) -> str:
    """Remove or replace characters that are unsafe in file paths."""
    title = re.sub(r'[<>:"/\\|?*]', "_", title)
    title = title.strip(". ")
    return title[:120] or "video"


@click.command(name="download")
@click.argument("bv_or_url")
@click.option(
    "--quality",
    "-q",
    default="best",
    type=click.Choice(QUALITY_CHOICES),
    show_default=True,
    help="Maximum video quality to request.",
)
@click.option(
    "--codec",
    default="avc",
    type=click.Choice(CODEC_CHOICES),
    show_default=True,
    help="Video codec to request. avc is the most compatible.",
)
@click.option(
    "--output",
    "-o",
    default=DEFAULT_OUTPUT_DIR,
    type=click.Path(file_okay=False),
    show_default=True,
    help="Output directory.",
)
def download(bv_or_url: str, quality: str, codec: str, output: str):
    """Download the video-only stream for a Bilibili video."""
    from .. import client

    bvid = extract_bvid_or_exit(bv_or_url)
    cred = get_credential(mode="optional")

    info = run_or_exit(client.get_video_info(bvid, credential=cred), "获取视频信息")
    title = info.get("title", bvid)
    safe_title = _sanitize_filename(title)

    console.print(f"[bold]{title}[/bold]")
    console.print("[dim]Selecting video-only stream...[/dim]")
    stream = run_or_exit(
        client.get_video_stream(bvid, credential=cred, max_quality=quality, codec=codec),
        "获取视频流",
    )

    out_dir = os.path.expanduser(output)
    filename = f"{safe_title} [{bvid}] [{stream.quality}-{stream.codec}].{stream.extension}"
    out_file = os.path.join(out_dir, filename)

    console.print(f"[dim]Downloading {stream.quality} {stream.codec} video stream...[/dim]")
    nbytes = run_or_exit(client.download_video(stream.url, out_file), "下载视频")
    size_mb = nbytes / (1024 * 1024)
    console.print(f"[green]Video saved: {out_file} ({size_mb:.1f} MB)[/green]")
