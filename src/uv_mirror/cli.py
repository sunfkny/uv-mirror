from dataclasses import dataclass
import difflib
import os
import pathlib
import platform
import time
from typing import Annotated
from urllib.parse import urljoin

import httpx
import tomlkit
import tomlkit.items
import typer
from rich.console import Console
from rich.syntax import Syntax

console = Console()

app = typer.Typer(help="UV镜像源管理工具", no_args_is_help=True)

# PyPI镜像源列表
index_urls = [
    # 官方
    # "https://pypi.org/simple/",
    # 高速
    "https://mirrors.aliyun.com/pypi/simple/",
    "https://mirrors.tencent.com/pypi/simple/",
    "https://mirror.nju.edu.cn/pypi/web/simple/",
    "https://mirrors.sustech.edu.cn/pypi/web/simple/",
    "https://mirrors.ustc.edu.cn/pypi/web/simple/",
    "https://mirrors.jlu.edu.cn/pypi/web/simple/",
    "https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple/",
    "https://mirrors.pku.edu.cn/pypi/web/simple/",
    "https://mirrors.zju.edu.cn/pypi/web/simple/",
    # 内网
    # "http://mirrors.cloud.aliyuncs.com/pypi/simple/",
    # "http://mirrors.tencentyun.com/pypi/simple/",
    # 低速
    # "https://mirrors.bfsu.edu.cn/pypi/web/simple/",
    # "https://mirrors.neusoft.edu.cn/pypi/web/simple/",
    # "https://mirrors.njtech.edu.cn/pypi/web/simple/",
    # "https://mirror.nyist.edu.cn/pypi/web/simple/",
    # "https://mirror.sjtu.edu.cn/pypi/web/simple/",
]

# Python安装镜像列表
official_python_install_url = (
    "https://github.com/astral-sh/python-build-standalone/releases/download"
)
python_install_urls = [
    # 官方
    # official_python_install_url,
    # 高速
    "https://registry.npmmirror.com/-/binary/python-build-standalone",
    "https://mirror.nju.edu.cn/github-release/indygreg/python-build-standalone",
    # 低速
    # f"https://gh-proxy.com/{official_python_install_url.removeprefix('https://')}",
    # f"https://github.akams.cn/{official_python_install_url}",
    # f"https://hub.gitmirror.com/{official_python_install_url}",
    # f"https://gh.jasonzeng.dev/{official_python_install_url}",
]


@dataclass
class DownloadResult:
    total_bytes: int
    duration: float
    value: str
    speed: float


def download(value: str, url: str, timeout: int):
    total_bytes = 0
    with httpx.Client() as client:
        start_at = time.time()
        end_at = -1
        with client.stream(
            "GET",
            url,
            timeout=timeout,
            follow_redirects=True,
        ) as stream:
            for chunk in stream.iter_bytes(chunk_size=1024):
                end_at = time.time()
                if end_at - start_at > timeout:
                    break
                total_bytes += len(chunk)

    duration = end_at - start_at
    speed = total_bytes / duration
    return DownloadResult(
        total_bytes=total_bytes,
        duration=duration,
        value=value,
        speed=speed,
    )


def human_readable_speed(speed: float):
    if speed < 1024:
        return f"{speed:.2f} B/s"
    elif speed < 1024**2:
        return f"{speed / 1024:.2f} KB/s"
    elif speed < 1024**3:
        return f"{speed / 1024**2:.2f} MB/s"
    else:
        return f"{speed / 1024**3:.2f} GB/s"


def display_diff(s1: str, s2: str, fromfile="", tofile=""):
    if s1 != s2:
        diff = "\n".join(
            difflib.unified_diff(
                s1.splitlines(),
                s2.splitlines(),
                fromfile=fromfile,
                tofile=tofile,
                lineterm="",
            )
        )
        syntax = Syntax(diff, "diff", theme="ansi_dark", line_numbers=False)
        console.print(syntax)
        return True
    return False


def get_configuration_file_path():
    p = platform.system()
    if p == "Windows":
        user_config_dir = pathlib.Path(os.environ["APPDATA"])
    elif p == "Darwin":
        user_config_dir = pathlib.Path("~/Library/Preferences").expanduser()
    else:
        user_config_dir = pathlib.Path("~/.config").expanduser()

    config_path = user_config_dir / "uv" / "uv.toml"
    if not config_path.exists():
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.touch()
    return config_path


def set_index_url(index_url: str):
    config_path = get_configuration_file_path()

    old_config_text = config_path.read_text()
    config = tomlkit.parse(old_config_text)

    index_aot = config.get("index", tomlkit.aot())
    assert isinstance(index_aot, tomlkit.items.AoT)

    default_index_found = False

    for item in index_aot:
        if item["default"]:
            item["url"] = index_url
            default_index_found = True

    if not default_index_found:
        new_item = tomlkit.table()
        new_item["url"] = index_url
        new_item["default"] = True
        index_aot.append(new_item)

    config["index"] = index_aot
    config_path.write_text(tomlkit.dumps(config))
    config_text = config_path.read_text()

    return display_diff(
        old_config_text,
        config_text,
        str(config_path),
        str(config_path),
    )


def set_python_install_mirror(python_install_mirror: str):
    config_path = get_configuration_file_path()

    old_config_text = config_path.read_text()
    config = tomlkit.parse(old_config_text)
    config["python-install-mirror"] = python_install_mirror

    config_path.write_text(tomlkit.dumps(config))
    config_text = config_path.read_text()

    return display_diff(
        old_config_text,
        config_text,
        str(config_path),
        str(config_path),
    )


def test_index_urls(timeout: int = 5):
    results = list[DownloadResult]()
    for index_url in index_urls:
        try:
            result = download(
                value=index_url,
                url=urljoin(
                    index_url,
                    "../packages/be/a6/46e250737d46e955e048f6bbc2948fb22f0de3f3ab828d3803070dc1260e/Django-5.0.tar.gz",
                ),
                timeout=timeout,
            )
            if result.speed > 0:
                console.print(f" ● {human_readable_speed(result.speed)} {result.value}")
                results.append(result)
        except Exception as e:
            console.print(f" ● {e} {index_url}", style="red bold")
    return results


def test_python_install_urls(timeout: int = 5):
    results = list[DownloadResult]()
    for python_install_url in python_install_urls:
        try:
            result = download(
                value=python_install_url,
                url=f"{python_install_url}/20250409/cpython-3.13.3%2B20250409-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz",
                timeout=timeout,
            )
            if result.speed > 0:
                console.print(f" ● {human_readable_speed(result.speed)} {result.value}")
                results.append(result)

        except Exception as e:
            console.print(f" ● {e} {python_install_url}", style="red bold")
    return results


@app.command()
def index(
    timeout: int = typer.Option(5, help="测试超时时间（秒）"),
    yes: Annotated[bool, typer.Option("-y", help="自动确认")] = False,
):
    console.print("测试PyPI镜像源速度...")
    results = test_index_urls(timeout)
    result = sorted(results, key=lambda x: x.speed, reverse=True)[0]
    console.print(
        f"最快的PyPI镜像源: {result.value} ({human_readable_speed(result.speed)})"
    )

    if yes or typer.confirm("是否设置为PyPI镜像源?", default=True):
        has_change = set_index_url(result.value)
        if has_change:
            console.print("已设置PyPI镜像源", style="bold green")
        else:
            console.print("PyPI镜像源无需更改")


@app.command()
def python_install(
    timeout: int = typer.Option(5, help="测试超时时间（秒）"),
    yes: Annotated[bool, typer.Option("-y", help="自动确认")] = False,
):
    console.print("测试Python安装镜像源速度...")
    results = test_python_install_urls(timeout)
    result = sorted(results, key=lambda x: x.speed, reverse=True)[0]
    console.print(
        f"最快的Python安装镜像源: {result.value} ({human_readable_speed(result.speed)})"
    )

    if yes or typer.confirm("是否设置为Python安装镜像源?", default=True):
        has_change = set_python_install_mirror(result.value)
        if has_change:
            console.print("已设置Python安装镜像源", style="bold green")
        else:
            console.print("Python安装镜像源无需更改")


@app.command()
def all(
    timeout: int = typer.Option(5, help="测试超时时间（秒）"),
    yes: Annotated[bool, typer.Option("-y", help="自动确认")] = False,
):
    index(timeout=timeout, yes=yes)
    python_install(timeout=timeout, yes=yes)


def main():
    app()


if __name__ == "__main__":
    main()
