#!/usr/bin/env python3
"""文件工具箱 Web 服务 — 静态文件 + API + SSE，默认监听 Unix Socket，--port 切换 TCP"""

import os
import sys
import json
import socket
import socketserver
import subprocess
import threading
import uuid
import queue
import re
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# ==================== 路径配置 ====================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WWW_DIR = os.path.join(SCRIPT_DIR, "www")
SCRIPTS_DIR = os.path.join(SCRIPT_DIR, "..", "scripts")

GATEWAY_PREFIX = "/app/file-tools"
SOCKET_PATH = os.environ.get("SOCKET_PATH") or os.path.join(
    os.environ.get("TRIM_APPDEST", SCRIPT_DIR), "app.sock"
)
LOG_FILE = os.environ.get("LOG_FILE") or os.path.join(
    os.environ.get("TRIM_PKGVAR", "/tmp"), "app.log"
)

# 任务日志目录
_share_paths = os.environ.get("TRIM_DATA_SHARE_PATHS", "")
TASK_LOGS_DIR = _share_paths.split(":")[0] if _share_paths else os.path.join(
    os.environ.get("TRIM_APPDEST", SCRIPT_DIR), "logs"
)

# ==================== 任务管理 ====================
tasks = {}  # taskId -> {"process": Popen, "listeners": set, "events": list, "meta": dict}

# 调试模式（CORS）
DEBUG = False


def log(msg):
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}\n")
    except Exception:
        pass


def _parse_result(lines, tool):
    """从输出行中解析脚本标记的 RESULT: 标签"""
    for line in reversed(lines):
        t = line.get("line", line) if isinstance(line, dict) else line
        m = re.search(r"RESULT:(\S+)", t)
        if m:
            return m.group(1)
    return None

def _save_task_log(task_id, exit_code, status="done"):
    """将已完成的任务输出保存到 @appshare 日志目录"""
    entry = tasks.get(task_id)
    if not entry:
        return
    meta = entry.get("meta", {})
    tool = meta.get("tool", "unknown")
    log_dir = os.path.join(TASK_LOGS_DIR, tool)
    try:
        os.makedirs(log_dir, exist_ok=True)
    except Exception:
        return
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"{ts}.log"
    counter = 1
    while os.path.exists(os.path.join(log_dir, filename)):
        filename = f"{ts}-{counter}.log"
        counter += 1
    stdout_lines = [ev[1] for ev in entry["events"] if ev[0] == "stdout"]
    log_data = {
        "id": task_id,
        "tool": tool,
        "args": meta.get("args", {}),
        "timestamp": datetime.now().isoformat(),
        "exitCode": exit_code,
        "status": status,
        "result": _parse_result(stdout_lines, tool),
        "lines": stdout_lines,
    }
    try:
        filepath = os.path.join(log_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log(f"保存任务日志失败: {e}")


def run_script(task_id, script_name, args):
    """在后台线程中执行脚本，捕获输出并分发给监听器"""
    script_path = os.path.join(SCRIPTS_DIR, script_name)
    cmd = ["bash", script_path] + args

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=SCRIPTS_DIR,
            text=True,
            bufsize=1,
            preexec_fn=os.setsid,
        )
        tasks[task_id]["process"] = proc

        _ansi_re = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]|\x1b\].*?\x07|\r")

        def _clean(line):
            return _ansi_re.sub("", line)

        def _read_stdout():
            for line in proc.stdout:
                line = _clean(line.rstrip("\n"))
                if line:
                    _emit(task_id, "stdout", {"line": line})

        def _read_stderr():
            buf = ""
            while True:
                chunk = proc.stderr.read(1)
                if not chunk:
                    break
                if chunk in ("\r", "\n"):
                    line = _clean(buf.strip())
                    if line:
                        m = re.search(r"进度 \[(\d+)%\] (\d+)/(\d+)\s+(.*)", line)
                        if m:
                            _emit(task_id, "progress", {
                                "percent": int(m.group(1)),
                                "current": int(m.group(2)),
                                "total": int(m.group(3)),
                                "name": m.group(4).strip(),
                            })
                        _emit(task_id, "stderr", {"line": line})
                    buf = ""
                else:
                    buf += chunk
            if buf.strip():
                line = _clean(buf.strip())
                if line:
                    _emit(task_id, "stderr", {"line": line})

        t_out = threading.Thread(target=_read_stdout, daemon=True)
        t_err = threading.Thread(target=_read_stderr, daemon=True)
        t_out.start()
        t_err.start()
        t_out.join()
        t_err.join()

        proc.wait()
        entry = tasks.get(task_id, {})
        stopped = entry.get("stopped_by_user", False) if entry else False
        if stopped:
            status = "stopped"
            code = 143
        elif proc.returncode < 0:
            status = "stopped"
            code = abs(proc.returncode)
        else:
            status = "done"
            code = proc.returncode
        _emit(task_id, "exit", {"code": code, "status": status})
        _save_task_log(task_id, code, status)

    except Exception as e:
        _emit(task_id, "error", {"message": str(e)})
        _save_task_log(task_id, -1, "stopped")
    finally:
        if task_id in tasks:
            del tasks[task_id]


def _emit(task_id, event, data):
    entry = tasks.get(task_id)
    if not entry:
        return
    entry["events"].append((event, data))
    for q in list(entry["listeners"]):
        try:
            q.put((event, data))
        except Exception:
            pass


# ==================== HTTP Handler ====================
class FileCheckHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WWW_DIR, **kwargs)

    def _cors(self):
        if DEBUG:
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _strip_prefix(self):
        parsed = urlparse(self.path)
        p = parsed.path
        if p == GATEWAY_PREFIX:
            location = GATEWAY_PREFIX + "/"
            if parsed.query:
                location += "?" + parsed.query
            self.send_response(301)
            self.send_header("Location", location)
            self.end_headers()
            return True
        if p.startswith(GATEWAY_PREFIX + "/"):
            rest = p[len(GATEWAY_PREFIX):] or "/"
            self.path = rest + (("?" + parsed.query) if parsed.query else "")
        return False

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self._strip_prefix():
            return
        parsed = urlparse(self.path)
        if parsed.path == "/api/events":
            self._handle_sse(parsed)
        elif parsed.path == "/api/task-status":
            self._handle_task_status(parsed)
        elif parsed.path == "/api/logs":
            self._handle_list_logs()
        elif parsed.path.startswith("/api/logs/"):
            self._handle_get_log(parsed.path)
        elif parsed.path == "/api/tasks":
            self._handle_list_tasks()
        elif parsed.path == "/api/health":
            self._json({"status": "ok"})
        else:
            super().do_GET()

    def do_DELETE(self):
        if self._strip_prefix():
            return
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/logs/"):
            self._handle_delete_log(parsed.path)
        else:
            self._json({"error": "未知接口"}, 404)

    def do_POST(self):
        if self._strip_prefix():
            return
        parsed = urlparse(self.path)
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len) if content_len > 0 else b""
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            return self._json({"error": "无效 JSON"}, 400)

        if parsed.path == "/api/compare":
            self._handle_compare(data)
        elif parsed.path == "/api/duplicate":
            self._handle_duplicate(data)
        elif parsed.path == "/api/export":
            self._handle_export(data)
        elif parsed.path == "/api/stop":
            self._handle_stop(data)
        else:
            self._json({"error": "未知接口"}, 404)

    def _handle_compare(self, data):
        mode = data.get("mode")
        dir_a = data.get("dirA", "").strip()
        dir_b = data.get("dirB", "").strip()
        block_size = data.get("blockSize")

        if mode is None or not dir_a or not dir_b:
            return self._json({"error": "缺少必填参数：mode, dirA, dirB"}, 400)
        if int(mode) not in (0, 1, 2):
            return self._json({"error": "mode 仅允许 0、1、2"}, 400)
        for d in (dir_a, dir_b):
            if not os.path.isabs(d):
                return self._json({"error": f"目录路径必须为绝对路径：{d}"}, 400)
            if ".." in d:
                return self._json({"error": "路径不允许包含 .."}, 400)
            if not os.path.exists(d):
                return self._json({"error": f"目录不存在：{d}"}, 400)
            if not os.path.isdir(d):
                return self._json({"error": f"路径不是目录：{d}"}, 400)
            if not os.access(d, os.R_OK):
                return self._json({"error": f"应用无目录读取权限，请到系统设置 - 应用 - file-tools - 添加目录只读权限：{d}"}, 403)

        task_id = str(uuid.uuid4())
        args = [str(mode), dir_a, dir_b]
        if block_size is not None:
            args.append(str(block_size))
        tasks[task_id] = {
            "process": None,
            "listeners": set(),
            "events": [],
            "meta": {
                "tool": "compare",
                "args": {"mode": mode, "dirA": dir_a, "dirB": dir_b, "blockSize": block_size},
            },
        }
        threading.Thread(
            target=run_script,
            args=(task_id, "dir_compare_check.sh", args),
            daemon=True,
        ).start()
        self._json({"taskId": task_id, "sseUrl": f"{GATEWAY_PREFIX}/api/events?taskId={task_id}"})

    def _handle_duplicate(self, data):
        mode = data.get("mode")
        scan_dir = data.get("scanDir", "").strip()
        filter_kb = data.get("filterKB")
        block_size = data.get("blockSize")

        if mode is None or not scan_dir:
            return self._json({"error": "缺少必填参数：mode, scanDir"}, 400)
        if int(mode) not in (0, 1, 2):
            return self._json({"error": "mode 仅允许 0、1、2"}, 400)
        if not os.path.isabs(scan_dir):
            return self._json({"error": "目录路径必须为绝对路径"}, 400)
        if ".." in scan_dir:
            return self._json({"error": "路径不允许包含 .."}, 400)
        if not os.path.exists(scan_dir):
            return self._json({"error": f"目录不存在：{scan_dir}"}, 400)
        if not os.path.isdir(scan_dir):
            return self._json({"error": f"路径不是目录：{scan_dir}"}, 400)
        if not os.access(scan_dir, os.R_OK):
            return self._json({"error": f"应用无目录读取权限，请到系统设置 - 应用 - file-tools - 添加目录只读权限：{scan_dir}"}, 403)

        args = [str(mode), scan_dir, str(filter_kb) if filter_kb is not None else ""]
        if block_size is not None:
            args.append(str(block_size))

        task_id = str(uuid.uuid4())
        tasks[task_id] = {
            "process": None,
            "listeners": set(),
            "events": [],
            "meta": {
                "tool": "duplicate",
                "args": {"mode": mode, "scanDir": scan_dir, "filterKB": filter_kb, "blockSize": block_size},
            },
        }
        threading.Thread(
            target=run_script,
            args=(task_id, "dir_duplicate_check.sh", args),
            daemon=True,
        ).start()
        self._json({"taskId": task_id, "sseUrl": f"{GATEWAY_PREFIX}/api/events?taskId={task_id}"})

    def _handle_export(self, data):
        content = data.get("content", "")
        filename = data.get("filename", "result.txt")
        if not content:
            return self._json({"error": "无内容可导出"}, 400)
        filename = re.sub(r'[^\w\-.]', '_', filename)
        share_paths = os.environ.get("TRIM_DATA_SHARE_PATHS", "")
        if DEBUG and not share_paths:
            share_paths = os.path.join(SCRIPT_DIR, "export")
        if not share_paths:
            return self._json({"error": "未配置数据共享目录，请在应用设置中启用"}, 500)
        export_dir = share_paths.split(":")[0]
        os.makedirs(export_dir, exist_ok=True)
        filepath = os.path.join(export_dir, filename)
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            self._json({"path": filepath})
        except Exception as e:
            self._json({"error": f"写入失败: {e}"}, 500)

    def _handle_list_tasks(self):
        """返回所有活跃任务的状态摘要"""
        result = []
        for tid, entry in tasks.items():
            meta = entry.get("meta", {})
            proc = entry.get("process")
            status = "running"
            if proc and proc.poll() is not None:
                status = "done"
            result.append({
                "taskId": tid,
                "tool": meta.get("tool", "unknown"),
                "args": meta.get("args", {}),
                "status": status,
                "lineCount": len([ev for ev in entry.get("events", []) if ev[0] == "stdout"]),
            })
        self._json({"tasks": result})

    def _handle_task_status(self, parsed):
        qs = parse_qs(parsed.query)
        task_id = (qs.get("taskId") or [None])[0]
        if not task_id:
            return self._json({"error": "缺少 taskId"}, 400)
        if task_id in tasks:
            self._json({"status": "running"})
        else:
            self._json({"status": "done"})

    def _handle_list_logs(self):
        logs = []
        for tool in ("compare", "duplicate"):
            tool_dir = os.path.join(TASK_LOGS_DIR, tool)
            if not os.path.isdir(tool_dir):
                continue
            for fname in sorted(os.listdir(tool_dir), reverse=True):
                if not fname.endswith(".log"):
                    continue
                fpath = os.path.join(tool_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    logs.append({
                        "tool": tool,
                        "filename": fname,
                        "id": data.get("id"),
                        "args": data.get("args", {}),
                        "timestamp": data.get("timestamp"),
                        "exitCode": data.get("exitCode"),
                        "status": data.get("status", "done"),
                        "result": data.get("result"),
                        "lineCount": len(data.get("lines", [])),
                    })
                except Exception:
                    pass
        logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        self._json({"logs": logs})

    def _handle_get_log(self, path):
        parts = path.replace("/api/logs/", "").split("/", 1)
        if len(parts) != 2:
            return self._json({"error": "路径格式错误"}, 400)
        tool, filename = parts
        if tool not in ("compare", "duplicate"):
            return self._json({"error": "无效工具名"}, 400)
        if "/" in filename or ".." in filename:
            return self._json({"error": "非法文件名"}, 400)
        fpath = os.path.join(TASK_LOGS_DIR, tool, filename)
        if not os.path.isfile(fpath):
            return self._json({"error": "日志不存在"}, 404)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._json(data)
        except Exception as e:
            self._json({"error": f"读取失败: {e}"}, 500)

    def _handle_delete_log(self, path):
        parts = path.replace("/api/logs/", "").split("/", 1)
        if len(parts) != 2:
            return self._json({"error": "路径格式错误"}, 400)
        tool, filename = parts
        if tool not in ("compare", "duplicate"):
            return self._json({"error": "无效工具名"}, 400)
        if "/" in filename or ".." in filename:
            return self._json({"error": "非法文件名"}, 400)
        fpath = os.path.join(TASK_LOGS_DIR, tool, filename)
        if not os.path.isfile(fpath):
            return self._json({"error": "日志不存在"}, 404)
        try:
            os.remove(fpath)
            self._json({"message": "已删除"})
        except Exception as e:
            self._json({"error": f"删除失败: {e}"}, 500)

    def _handle_stop(self, data):
        task_id = data.get("taskId")
        if not task_id:
            return self._json({"error": "缺少 taskId"}, 400)
        entry = tasks.get(task_id)
        if not entry:
            return self._json({"message": "任务不存在或已完成"})
        proc = entry.get("process")
        if proc and proc.poll() is None:
            try:
                import signal
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
        # 标记任务被用户终止，实际的退出处理和日志保存由 run_script 线程完成
        entry["stopped_by_user"] = True
        return self._json({"message": "已终止"})

    def _handle_sse(self, parsed):
        qs = parse_qs(parsed.query)
        task_id = (qs.get("taskId") or [None])[0]
        if not task_id:
            return self._json({"error": "缺少 taskId"}, 400)

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self._cors()
        self.end_headers()

        q = queue.Queue()
        entry = tasks.get(task_id)

        if entry:
            entry["listeners"].add(q)
            self._sse_send("connected", {"taskId": task_id})
            for ev in entry["events"]:
                q.put(ev)
        else:
            self._sse_send("error", {"message": "任务不存在或已完成"})
            return

        try:
            while True:
                try:
                    event, data = q.get(timeout=30)
                    self._sse_send(event, data)
                    if event in ("exit", "error"):
                        break
                except queue.Empty:
                    self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            if task_id in tasks:
                tasks[task_id]["listeners"].discard(q)

    def _sse_send(self, event, data):
        try:
            msg = f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
            self.wfile.write(msg.encode("utf-8"))
            self.wfile.flush()
        except Exception:
            pass

    def _json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._cors()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass


# ==================== 服务器 ====================
class ThreadedUnixHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    address_family = socket.AF_UNIX
    daemon_threads = True

    def server_bind(self):
        try:
            os.unlink(self.server_address)
        except OSError:
            pass
        socketserver.TCPServer.server_bind(self)
        self.server_name = "localhost"
        self.server_port = 0
        try:
            os.chmod(self.server_address, 0o666)
        except OSError:
            pass


def _create_tcp_server(port):
    """创建 TCP 模式服务器（本地测试用）"""
    class ThreadedTCPServer(socketserver.ThreadingMixIn, HTTPServer):
        daemon_threads = True
        allow_reuse_address = True

    return ThreadedTCPServer(("0.0.0.0", port), FileCheckHandler)


if __name__ == "__main__":
    args = sys.argv[1:]

    tcp_port = None
    for a in args:
        if a.startswith("--port="):
            tcp_port = int(a.split("=", 1)[1])
        elif a == "--debug":
            DEBUG = True

    if not os.path.isdir(WWW_DIR):
        print(f"前端目录不存在: {WWW_DIR}", file=sys.stderr)
        sys.exit(1)

    if tcp_port:
        DEBUG = True
        server = _create_tcp_server(tcp_port)
        print(f"🔧 本地测试模式: http://localhost:{tcp_port}{GATEWAY_PREFIX}/", flush=True)
    else:
        socket_dir = os.path.dirname(SOCKET_PATH)
        if socket_dir:
            os.makedirs(socket_dir, exist_ok=True)
        server = ThreadedUnixHTTPServer(SOCKET_PATH, FileCheckHandler)
        log(f"文件工具箱服务已启动，Socket: {SOCKET_PATH}")
        print(f"文件工具箱服务已启动，Socket: {SOCKET_PATH}", flush=True)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        if not tcp_port:
            try:
                os.unlink(SOCKET_PATH)
            except OSError:
                pass
