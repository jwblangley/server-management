import os
import socket
from contextlib import closing
import subprocess
from wakeonlan import send_magic_packet as wake_on_lan

from common import wait_for


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

    r = run_remote(ip_address, user, "sudo", "shutdown", "now")

    print("Server shutdown complete")
