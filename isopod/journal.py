from subprocess import DEVNULL, PIPE, Popen


def namespaced_stream(namespace: str):
    args = [
        "systemd-run",
        "--pipe",
        "--quiet",
        "--collect",
        "--slice-inherit",
        f"--property=LogNamespace={namespace}",
        "systemd-cat",
        "-t",
        "isopod",
    ]
    proc = Popen(args, stdin=PIPE, stdout=DEVNULL, stderr=DEVNULL)
    assert proc.stdin is not None
    return proc.stdin
