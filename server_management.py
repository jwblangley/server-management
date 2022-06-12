import os
import socket
from contextlib import closing
import subprocess
from wakeonlan import send_magic_packet as wake_on_lan
import json

from common import wait_for


class UnknownApplicationIDError(Exception):
    def _init__(self, msg):
        super().__init__(msg)


def run_remote(ip_address, user, *command, capture_output=True, stdin=None):
    cmd = ["ssh", f"{user}@{ip_address}", *command]

    stdin = stdin.encode() if stdin is not None else None

    return subprocess.run(cmd, capture_output=capture_output, input=stdin)


def run_local_script_on_remote(
    ip_address, user, local_script_path, capture_output=True
):
    with open(local_script_path, "r") as f:
        script = f.read()
    return run_remote(
        ip_address, user, "bash", capture_output=capture_output, stdin=script
    )


def is_port_open(ip_address, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    with closing(sock):
        result = sock.connect_ex((ip_address, port))
        return result == 0


def is_server_on(ip_address):
    cmd = ["ping", "-c", "1", ip_address]

    res = subprocess.run(cmd, capture_output=True)
    return res.returncode == 0


def is_server_in_use(ip_address, user):
    res = run_local_script_on_remote(ip_address, user, "in_use.sh")
    return res.returncode == 0


def turn_server_on(mac_address, ip_address, verify=False):
    if is_server_on(ip_address):
        return

    wake_on_lan(mac_address)

    if verify:
        wait_for(lambda: is_server_on(ip_address), interval=5, timeout=300)

    print("Server boot complete")


# N.B requires password-less shutdown
def turn_server_off(ip_address, user):
    if is_server_in_use(ip_address, user):
        print("Not shutting down - server in use")
        return

    result = run_remote(ip_address, user, "sudo", "shutdown", "now")

    if result.returncode != 0:
        raise RuntimeError(f"Remote call returned code: {result.returncode}")

    print("Server shutdown complete")


def _run_application_script(
    start,
    ip_address,
    user,
    script_prefix,
    verify_ports=None,
    verify=False,
):
    if verify and verify_ports is not None and len(verify_ports) > 0:
        if all(is_port_open(ip_address, p) == start for p in verify_ports):
            print("skipping")
            return

    script = f"applications/{script_prefix}.{'on' if start else 'off'}.sh"
    assert os.path.exists(script)
    result = run_local_script_on_remote(ip_address, user, script)

    if result.returncode != 0:
        raise RuntimeError(f"Remote call returned code: {result.returncode}")

    if verify and verify_ports is not None and len(verify_ports) > 0:
        for p in verify_ports:
            wait_for(lambda: is_port_open(ip_address, p) == start)


def _change_application_state(start, ip_address, user, application_id, verify=False):
    # TODO: turn_server_on()

    with open("applications/applications.json", "r") as f:
        cfg = json.load(f)
        if application_id not in cfg:
            raise UnknownApplicationIDError(f"Unkown application_id: {application_id}")

        app_cfg = cfg[application_id]
        match app_cfg:
            case {"script_prefix": script_prefix, "verify_ports": [*verify_ports]}:
                _run_application_script(
                    start,
                    ip_address,
                    user,
                    script_prefix,
                    verify_ports=verify_ports,
                    verify=verify,
                )
            case {"script_prefix": script_prefix}:
                _run_application_script(start, ip_address, user, script_prefix)
            case _:
                raise AssertionError("Malformed applications config")


def start_application(ip_address, user, application_id, verify=False):
    return _change_application_state(
        True, ip_address, user, application_id, verify=verify
    )


def stop_application(ip_address, user, application_id, verify=False):
    return _change_application_state(
        False, ip_address, user, application_id, verify=verify
    )
