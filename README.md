# UniversalFastDownloader

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

UniversalFastDownloader is a blazingly fast, multi-threaded file downloader written in Python. This tool is designed to maximize download speeds by leveraging multiple threads and can seamlessly inherit authentication details (like cookies and User-Agent) from a `curl` command, making it perfect for downloading files from sites that require login sessions.

UniversalFastDownloader 是一个使用 Python 编写的超高速多线程文件下载器。该工具通过利用多线程来最大化下载速度，并能无缝地从 `curl` 命令中继承认证信息（如 cookies 和 User-Agent），非常适合下载需要登录会话的网站上的文件。

## 🚀 Getting Started / 开始使用

### Prerequisites / 先决条件

- Python 3.6 或更高版本
- `pip` (Python 包安装器)

### Installation / 安装

1.  Clone this repository (克隆此仓库):
    ```bash
    git clone https://github.com/ryanzhaorx/UniversalFastDownloader.git
    cd UniversalFastDownloader
    ```

2.  Install the required dependencies (安装所需依赖):
    ```bash
    pip install -r requirements.txt
    ```

### Usage / 使用方法

Run the script and follow the interactive prompts (运行脚本并按照交互式提示操作):

```bash
python UniversalFastDownloader.py
