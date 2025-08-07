import os
import sys
import requests
import threading
import time
import signal
import re
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import socket

class UltraFastDownloader:
    def __init__(self, url, filename=None, num_threads=32, chunk_size=8*1024*1024, 
                 user_agent=None, cookies=None, headers=None):
        self.url = url
        self.num_threads = num_threads
        self.chunk_size = chunk_size
        self.filename = filename or self._get_filename()
        self.file_size = 0
        self.downloaded_size = 0
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.start_time = time.time()
        self.last_progress_line = ""
        
        # 构建请求头
        self.headers = {}
        
        # 设置User-Agent
        if user_agent:
            self.headers['User-Agent'] = user_agent
        else:
            self.headers['User-Agent'] = 'netdisk;6.0.0.12;PC;PC-Windows;10.0.16299;WindowsBaiduYunGuanJia'
        
        # 设置Cookie
        if cookies:
            self.headers['Cookie'] = cookies
        
        # 设置其他自定义头
        default_headers = {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
        }
        
        self.headers.update(default_headers)
        if headers:
            self.headers.update(headers)
        
        # 系统级优化
        self._optimize_system()
    
    def _optimize_system(self):
        """系统级优化"""
        try:
            socket.setdefaulttimeout(30)
        except:
            pass
    
    def _get_filename(self):
        """从URL获取文件名"""
        parsed_url = urlparse(self.url)
        filename = os.path.basename(parsed_url.path)
        if not filename or '.' not in filename:
            filename = "downloaded_file.bin"
        return filename
    
    def _get_file_size(self):
        """获取文件大小（多种方法）"""
        methods = [
            self._get_size_with_head,
            self._get_size_with_range,
            self._get_size_with_get
        ]
        
        for method in methods:
            try:
                size = method()
                if size > 0:
                    return size
            except:
                continue
        return 0
    
    def _get_size_with_head(self):
        """HEAD请求获取大小"""
        response = requests.head(self.url, headers=self.headers, allow_redirects=True, timeout=15)
        if response.status_code == 200:
            return int(response.headers.get('content-length', 0))
        return 0
    
    def _get_size_with_range(self):
        """Range请求获取大小"""
        headers = self.headers.copy()
        headers['Range'] = 'bytes=0-0'
        response = requests.get(self.url, headers=headers, timeout=15)
        if response.status_code == 206:
            content_range = response.headers.get('content-range', '')
            if content_range:
                size = int(content_range.split('/')[-1])
                return size
        return 0
    
    def _get_size_with_get(self):
        """GET请求获取大小"""
        response = requests.get(self.url, headers=self.headers, stream=True, timeout=15)
        if response.status_code == 200:
            return int(response.headers.get('content-length', 0))
        return 0
    
    def _download_chunk_requests(self, start, end, thread_id):
        """优化的requests下载"""
        if self.stop_event.is_set():
            return
            
        headers = self.headers.copy()
        headers['Range'] = f'bytes={start}-{end}'
        
        # 创建专用会话
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=100,
            pool_maxsize=100,
            max_retries=1
        )
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        
        try:
            response = session.get(
                self.url,
                headers=headers,
                stream=True,
                timeout=(5, 30)
            )
            
            if response.status_code in [200, 206]:
                with open(self.filename, 'r+b') as f:
                    f.seek(start)
                    for chunk in response.iter_content(chunk_size=131072):  # 128KB块
                        if self.stop_event.is_set():
                            break
                        if chunk:
                            f.write(chunk)
                            with self.lock:
                                self.downloaded_size += len(chunk)
            
            session.close()
            
        except Exception:
            pass
    
    def _format_size(self, size):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"
    
    def _format_speed(self, speed):
        """格式化下载速度"""
        return self._format_size(speed) + '/s'
    
    def _show_progress(self):
        """优化的进度显示（避免刷屏）"""
        last_update_time = 0
        update_interval = 0.1
        
        while not self.stop_event.is_set():
            current_time = time.time()
            
            if current_time - last_update_time >= update_interval and self.file_size > 0:
                current_downloaded = self.downloaded_size
                elapsed_time = current_time - self.start_time
                total_speed = current_downloaded / elapsed_time if elapsed_time > 0 else 0
                
                percent = (current_downloaded / self.file_size) * 100
                
                # 使用固定长度的进度条
                bar_length = 40
                filled_length = int(bar_length * percent // 100)
                progress_bar = '█' * filled_length + '░' * (bar_length - filled_length)
                
                progress_line = f"\r[{progress_bar}] {percent:5.1f}% ({self._format_size(current_downloaded)}/{self._format_size(self.file_size)}) {self._format_speed(total_speed)}"
                
                if progress_line != self.last_progress_line:
                    print(progress_line, end='', flush=True)
                    self.last_progress_line = progress_line
                
                last_update_time = current_time
            
            time.sleep(0.05)
    
    def _preallocate_file(self):
        """预分配文件空间"""
        try:
            with open(self.filename, 'wb') as f:
                f.seek(self.file_size - 1)
                f.write(b'\0')
            return True
        except Exception:
            return False
    
    def download(self):
        """高速下载主函数"""
        print(f"开始高速下载: {self.filename}")
        print("正在获取文件信息...")
        
        # 获取文件大小
        self.file_size = self._get_file_size()
        if self.file_size == 0:
            print("无法获取文件大小，使用单线程下载")
            self._single_thread_download()
            return
        
        print(f"文件大小: {self._format_size(self.file_size)}")
        print(f"使用 {self.num_threads} 个线程进行下载，块大小: {self._format_size(self.chunk_size)}")
        
        # 预分配文件空间
        if not self._preallocate_file():
            print("警告: 无法预分配文件空间")
        
        # 计算每个线程的下载范围
        ranges = []
        chunk_size = max(self.chunk_size, self.file_size // self.num_threads)
        
        start = 0
        while start < self.file_size:
            end = min(start + chunk_size - 1, self.file_size - 1)
            ranges.append((start, end))
            start = end + 1
        
        actual_threads = len(ranges)
        print(f"实际使用 {actual_threads} 个下载任务")
        
        # 启动进度显示线程
        progress_thread = threading.Thread(target=self._show_progress)
        progress_thread.daemon = True
        progress_thread.start()
        
        try:
            # 使用线程池执行下载
            with ThreadPoolExecutor(max_workers=actual_threads) as executor:
                future_to_range = {
                    executor.submit(self._download_chunk_requests, start, end, i): i 
                    for i, (start, end) in enumerate(ranges)
                }
                
                for future in as_completed(future_to_range):
                    thread_id = future_to_range[future]
                    try:
                        future.result()
                    except Exception:
                        pass
            
            # 停止进度显示
            self.stop_event.set()
            progress_thread.join()
            
            print()
            
            elapsed_time = time.time() - self.start_time
            avg_speed = self.file_size / elapsed_time if elapsed_time > 0 else 0
            print(f"下载完成! 用时: {elapsed_time:.2f}秒, 平均速度: {self._format_speed(avg_speed)}")
                
        except KeyboardInterrupt:
            print("\n\n下载被用户中断")
            self.stop_event.set()
            if os.path.exists(self.filename):
                os.remove(self.filename)
    
    def _single_thread_download(self):
        """优化的单线程下载"""
        print("使用单线程模式下载...")
        
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=100,
            pool_maxsize=100,
            max_retries=3
        )
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        
        try:
            response = session.get(self.url, headers=self.headers, stream=True, timeout=60)
            if response.status_code == 200:
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                start_time = time.time()
                
                with open(self.filename, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=131072):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            if total_size > 0:
                                percent = (downloaded / total_size) * 100
                                elapsed_time = time.time() - start_time
                                speed = downloaded / elapsed_time if elapsed_time > 0 else 0
                                
                                bar_length = 40
                                filled_length = int(bar_length * percent // 100)
                                progress_bar = '█' * filled_length + '░' * (bar_length - filled_length)
                                
                                progress_line = f"\r[{progress_bar}] {percent:5.1f}% ({self._format_size(downloaded)}/{self._format_size(total_size)}) {self._format_speed(speed)}"
                                print(progress_line, end='', flush=True)
                
                print()
                print(f"下载完成!")
            else:
                print(f"下载失败，状态码: {response.status_code}")
        except Exception as e:
            print(f"下载出错: {e}")
        finally:
            session.close()

def parse_curl_command(curl_command):
    """解析curl命令，提取URL、文件名、User-Agent和Cookie"""
    url = None
    filename = None
    user_agent = None
    cookies = None
    headers = {}
    
    # 提取URL
    url_patterns = [
        r'["\']?(https?://[^\s"\'>]+)["\']?',
        r'(https?://[^\s>]+)'
    ]
    
    for pattern in url_patterns:
        url_match = re.search(pattern, curl_command)
        if url_match:
            url = url_match.group(1)
            break
    
    # 提取输出文件名
    output_match = re.search(r'-o\s+["\']?([^"\'>\s]+)["\']?', curl_command)
    if output_match:
        filename = output_match.group(1)
    
    # 提取User-Agent
    ua_match = re.search(r'-A\s+["\']?([^"\'>\s]+)["\']?', curl_command)
    if ua_match:
        user_agent = ua_match.group(1)
    
    # 提取Cookie
    cookie_match = re.search(r'-b\s+["\']?([^"\'>]+)["\']?', curl_command)
    if cookie_match:
        cookies = cookie_match.group(1)
    
    # 提取其他头部
    header_matches = re.findall(r'-H\s+["\']?([^"\'>]+)["\']?', curl_command)
    for header in header_matches:
        if ':' in header:
            key, value = header.split(':', 1)
            headers[key.strip()] = value.strip()
    
    return {
        'url': url,
        'filename': filename,
        'user_agent': user_agent,
        'cookies': cookies,
        'headers': headers
    }

def signal_handler(sig, frame):
    print('\n\n程序被中断')
    sys.exit(0)

def get_user_input():
    """获取用户输入"""
    print("=== 高速下载工具 ===")
    print()
    
    # 获取Curl命令
    print("请输入curl命令 (若不知道则回车跳过) *(强烈推荐使用)*:")
    curl_command = input().strip()
    
    if curl_command:
        # 从curl命令解析参数
        curl_info = parse_curl_command(curl_command)
        url = curl_info['url']
        filename = curl_info['filename']
        user_agent = curl_info['user_agent']
        cookies = curl_info['cookies']
        headers = curl_info['headers']
    else:
        # 手动输入参数
        url = None
        while not url:
            print("请输入下载URL:")
            url = input().strip()
            if not url.startswith(('http://', 'https://')):
                print("URL格式错误，请重新输入")
                url = None
        
        print("请输入输出文件名 (若不知道则回车使用默认名称):")
        filename = input().strip() or None
        
        print("请输入User-Agent (若不知道则回车使用默认值):")
        user_agent = input().strip() or None
        
        print("请输入Cookie (若不知道则回车跳过):")
        cookies = input().strip() or None
        
        headers = {}
    
    # 获取线程数
    print("请输入线程数 (默认32):")
    threads_input = input().strip()
    num_threads = int(threads_input) if threads_input.isdigit() else 32
    
    # 获取块大小
    print("请输入块大小(MB) (默认8):")
    chunk_input = input().strip()
    chunk_size = int(chunk_input) * 1024 * 1024 if chunk_input.isdigit() else 8 * 1024 * 1024
    
    return {
        'url': url,
        'filename': filename,
        'num_threads': num_threads,
        'chunk_size': chunk_size,
        'user_agent': user_agent,
        'cookies': cookies,
        'headers': headers
    }

def main():
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    
    # 获取用户输入
    try:
        config = get_user_input()
    except KeyboardInterrupt:
        print("\n\n程序被中断")
        sys.exit(0)
    except Exception as e:
        print(f"输入错误: {e}")
        sys.exit(1)
    
    # 验证URL
    if not config['url']:
        print("错误: 必须提供URL")
        sys.exit(1)
    
    # 创建下载器实例
    downloader = UltraFastDownloader(
        url=config['url'],
        filename=config['filename'],
        num_threads=config['num_threads'],
        chunk_size=config['chunk_size'],
        user_agent=config['user_agent'],
        cookies=config['cookies'],
        headers=config['headers']
    )
    
    print("\n" + "="*50)
    print("开始下载配置:")
    print(f"URL: {config['url']}")
    print(f"文件名: {downloader.filename}")
    print(f"线程数: {config['num_threads']}")
    print(f"块大小: {downloader._format_size(config['chunk_size'])}")
    print("="*50)
    print()
    
    # 开始下载
    downloader.download()

if __name__ == "__main__":
    main()