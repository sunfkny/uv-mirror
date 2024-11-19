# /// script
# dependencies = [
#     "httpx",
#     "loguru",
#     "tomlkit",
# ]
# ///
import asyncio
import os
import pathlib
import platform
import time
from urllib.parse import urljoin

import httpx
import tomlkit
import tomlkit.items
from loguru import logger

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


async def download(url: str, timeout: int):
    total_bytes = 0
    async with httpx.AsyncClient() as client:
        start_at = time.time()
        end_at = -1
        try:
            async with client.stream(
                "GET",
                url,
                timeout=timeout,
                follow_redirects=True,
            ) as stream:
                async for chunk in stream.aiter_bytes(chunk_size=1024):
                    end_at = time.time()
                    if end_at - start_at > timeout:
                        break
                    total_bytes += len(chunk)
        except httpx.RequestError as e:
            logger.error(repr(e))
            end_at = time.time()

    duration = end_at - start_at
    return total_bytes, duration


def human_readable_speed(speed: float):
    if speed < 1024:
        return f"{speed:.2f}B/s"
    elif speed < 1024**2:
        return f"{speed / 1024:.2f}KB/s"
    elif speed < 1024**3:
        return f"{speed / 1024 ** 2:.2f}MB/s"
    else:
        return f"{speed / 1024 ** 3:.2f}GB/s"


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
    logger.info(f"Config path: {config_path}")

    config = tomlkit.parse(config_path.read_text())

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
    config_content = config_path.read_text()

    logger.info("Config content: ")
    print(config_content)


async def main():
    BIG_FILE = "../packages/be/a6/46e250737d46e955e048f6bbc2948fb22f0de3f3ab828d3803070dc1260e/Django-5.0.tar.gz"
    data: list[tuple[float, str]] = []
    for index_url in index_urls:
        logger.info(index_url)
        total_bytes, duration = await download(
            url=urljoin(index_url, BIG_FILE),
            timeout=5,
        )
        logger.info(" - " + human_readable_speed(total_bytes / duration))
        data.append((total_bytes / duration, index_url))
    _, fast_index = max(data)
    set_index_url(fast_index)


if __name__ == "__main__":
    asyncio.run(main())
