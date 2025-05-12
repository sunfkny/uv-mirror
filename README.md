```bash
uv run --index https://mirrors.aliyun.com/pypi/simple https://raw.githubusercontents.com/sunfkny/uv-index/refs/heads/master/uv-index.py
# or ssh pipe to server
cat uv-index.py | ssh server_name uv run --index https://mirrors.aliyun.com/pypi/simple -
```
