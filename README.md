```bash
uvx --index https://mirrors.aliyun.com/pypi/simple git+https://github.com/sunfkny/uv-mirror all
# or ssh pipe to server
cat main.py | ssh server_name uv run --index https://mirrors.aliyun.com/pypi/simple -
```
