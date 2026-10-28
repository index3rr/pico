"""Local control bridge. All Thonny calls run on Tk's main thread."""
import json
import os
from pathlib import Path
import socket
import time
import uuid

from thonny import get_runner, get_workbench
from thonny.common import ToplevelCommand


def load_plugin():
    path = os.environ.get("PICO_BRIDGE_SOCKET")
    if not path:
        return
    # Thonny 5's UI compares the configured name with ttyACM names literally.
    # Keep the stable by-id path for opening the port, resolve it for UI lookup.
    from thonny.plugins.micropython import mp_front
    original_get_port_info = mp_front.get_port_info
    mp_front.get_port_info = lambda name: original_get_port_info(os.path.realpath(name))
    Bridge(path)


class Bridge:
    def __init__(self, path):
        self.path = Path(path)
        self.path.unlink(missing_ok=True)
        self.server = socket.socket(socket.AF_UNIX)
        self.server.bind(str(self.path))
        os.chmod(self.path, 0o600)
        self.server.listen(4)
        self.server.setblocking(False)
        self.clients = {}
        self.pending = None
        bench = get_workbench()
        bench.bind("ProgramOutput", self.output, True)
        bench.bind("ToplevelResponse", self.done, True)
        bench.bind("BackendTerminated", self.terminated, True)
        bench.after(100, self.poll)

    def reply(self, client, **data):
        try:
            client.settimeout(0.2)
            client.sendall(json.dumps(data).encode() + b"\n")
        except OSError:
            pass
        finally:
            self.clients.pop(client, None)
            client.close()

    def output(self, event):
        if self.pending:
            self.pending["output"].append((event.stream_name, event.data))

    def done(self, event):
        if self.pending and event.get("command_id") == self.pending["id"]:
            pending, self.pending = self.pending, None
            stderr = "".join(data for stream, data in pending["output"] if stream == "stderr")
            self.reply(pending["client"], ok=not stderr and not event.get("error"),
                       stdout="".join(data for stream, data in pending["output"] if stream == "stdout"),
                       stderr=stderr, error=event.get("error"))

    def terminated(self, event):
        if self.pending:
            pending, self.pending = self.pending, None
            self.reply(pending["client"], ok=False, error="Pico backend disconnected; command was not retried")

    def dispatch(self, client, request):
        runner = get_runner()
        action = request.get("action")
        if action == "status":
            self.reply(client, ok=True, state=runner.get_state(),
                       ready=runner.get_backend_proxy() is not None and runner.is_waiting_toplevel_command(),
                       port=get_workbench().get_option("RPiPico.port"))
        elif action == "interrupt":
            proxy = runner.get_backend_proxy()
            if proxy is None:
                raise RuntimeError("Backend is disconnected; use reconnect")
            proxy.interrupt()
            self.reply(client, ok=True)
        elif action == "reconnect":
            if self.pending:
                raise RuntimeError("A bridge command is still active; interrupt it first")
            runner.restart_backend(clean=False)
            self.reply(client, ok=True)
        elif action == "exec":
            if self.pending or runner.get_backend_proxy() is None or not runner.is_waiting_toplevel_command():
                raise RuntimeError("Pico is busy or disconnected; interrupt or reconnect explicitly")
            command_id = "pico_" + uuid.uuid4().hex
            self.pending = dict(client=client, id=command_id, output=[],
                                deadline=time.monotonic() + request.get("timeout", 30))
            self.clients.pop(client, None)
            runner.send_command(ToplevelCommand("execute_source", source=request["source"], id=command_id))
        else:
            raise ValueError("Unknown action")

    def poll(self):
        try:
            while True:
                client, _ = self.server.accept()
                client.setblocking(False)
                self.clients[client] = (b"", time.monotonic())
        except BlockingIOError:
            pass
        for client, (buffer, started) in list(self.clients.items()):
            try:
                try:
                    chunk = client.recv(65536)
                except BlockingIOError:
                    chunk = None
                if chunk == b"":
                    self.clients.pop(client, None)
                    client.close()
                    continue
                buffer += chunk or b""
                if len(buffer) > 2_000_000 or time.monotonic() - started > 10:
                    raise ValueError("Request too large or incomplete")
                if b"\n" in buffer:
                    self.dispatch(client, json.loads(buffer.split(b"\n", 1)[0]))
                else:
                    self.clients[client] = (buffer, started)
            except Exception as exc:
                self.reply(client, ok=False, error=str(exc))
        if self.pending and time.monotonic() > self.pending["deadline"]:
            pending, self.pending = self.pending, None
            self.reply(pending["client"], ok=False,
                       error="Timed out; code may still be running. Use interrupt before retrying.")
        get_workbench().after(50, self.poll)
