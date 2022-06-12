import os
import socket
from contextlib import closing
import subprocess
from wakeonlan import send_magic_packet as wake_on_lan
import json

from common import wait_for


class ServerManager:
    class UnknownApplicationIDError(Exception):
        def _init__(self, msg):
            super().__init__(msg)

    def __init__(self, mac_address, ip_address, user):
        self.mac_address = mac_address
        self.ip_address = ip_address
        self.user = user

    def run_remote(self, *command, capture_output=True, stdin=None):
        cmd = ["ssh", f"{self.user}@{self.ip_address}", *command]

        stdin = stdin.encode() if stdin is not None else None

        return subprocess.run(cmd, capture_output=capture_output, input=stdin)

    def run_local_script_on_remote(self, local_script_path, capture_output=True):
        with open(local_script_path, "r") as f:
            script = f.read()
        return self.run_remote("bash", capture_output=capture_output, stdin=script)

    def is_port_open(self, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        with closing(sock):
            result = sock.connect_ex((self.ip_address, port))
            return result == 0

    def is_server_on(self):
        cmd = ["ping", "-c", "1", self.ip_address]

        res = subprocess.run(cmd, capture_output=True)
        return res.returncode == 0

    def is_server_in_use(self):
        res = self.run_local_script_on_remote("in_use.sh")
        return res.returncode == 0

    def turn_server_on(self, verify=False):
        if self.is_server_on():
            return

        wake_on_lan(self.mac_address)

        if verify:
            wait_for(lambda: self.is_server_on(), timeout=300)

        print("Server boot complete")

    # N.B requires password-less shutdown
    def turn_server_off(self):
        if self.is_server_in_use():
            print("Not shutting down - server in use")
            return

        result = self.run_remote("sudo", "shutdown", "now")

        if result.returncode != 0:
            raise RuntimeError(f"Remote call returned code: {result.returncode}")

        print("Server shutdown complete")

    def _run_application_script(
        self,
        start,
        script_prefix,
        verify_ports=None,
        verify=False,
    ):
        if verify and verify_ports is not None and len(verify_ports) > 0:
            if all(self.is_port_open(p) == start for p in verify_ports):
                print("skipping")
                return

        script = f"applications/{script_prefix}.{'on' if start else 'off'}.sh"
        assert os.path.exists(script)
        result = self.run_local_script_on_remote(script)

        if result.returncode != 0:
            raise RuntimeError(f"Remote call returned code: {result.returncode}")

        if verify and verify_ports is not None and len(verify_ports) > 0:
            for p in verify_ports:
                wait_for(lambda: self.is_port_open(p) == start, timeout=300)

    def _change_application_state(self, start, application_id, verify=False):
        with open("applications/applications.json", "r") as f:
            cfg = json.load(f)
            if application_id not in cfg:
                raise ServerManager.UnknownApplicationIDError(
                    f"Unkown application_id: {application_id}"
                )

            app_cfg = cfg[application_id]
            match app_cfg:
                case {"script_prefix": script_prefix, "verify_ports": [*verify_ports]}:
                    self._run_application_script(
                        start,
                        script_prefix,
                        verify_ports=verify_ports,
                        verify=verify,
                    )
                case {"script_prefix": script_prefix}:
                    self._run_application_script(start, script_prefix)
                case _:
                    raise AssertionError("Malformed applications config")

    def start_application(self, application_id, verify=False):
        self.turn_server_on(verify=True)  # idempotent
        return self._change_application_state(True, application_id, verify=verify)

    def stop_application(self, application_id, verify=False):
        return self._change_application_state(False, application_id, verify=verify)
