import os
import socket
from contextlib import closing
import subprocess
from wakeonlan import send_magic_packet as wake_on_lan

from common import wait_for


def run_remote(ip_address, user, *command, capture_output=True, stdin=None):
    cmd = ["ssh", f"{user}@{ip_address}", *command]

    return subprocess.run(cmd, capture_output=capture_output, input=stdin.encode())


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
    with open("in_use.sh", "r") as f:
        script = f.read()
    res = run_remote(ip_address, user, "bash", stdin=script)
    return res.returncode == 0


def turn_server_on(mac_address, ip_address, verify=False):
    if is_server_on(ip_address):
        return

    wake_on_lan(mac_address)

    if verify:
        wait_for(lambda: is_server_on(ip_address), interval=5, timeout=300)
