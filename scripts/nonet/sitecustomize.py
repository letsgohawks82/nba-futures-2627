"""Network guard for reproduction runs. Put this directory first on PYTHONPATH (the clean-room does it when NBA_BLOCK_NETWORK=1): every Python process, including the stage
subprocesses, then refuses all outbound connections and name lookups and appends each attempt to $NBA_NONET_LOG. A reproduction that finishes with an empty log made no network calls."""
import os, socket, sys, time
_LOG = os.environ.get("NBA_NONET_LOG")


def _deny(kind):
    def f(*a, **k):
        if _LOG:
            with open(_LOG, "a") as fh: fh.write(f"{time.strftime('%H:%M:%S')} {kind} {sys.argv[:3]} {str(a)[:100]}\n")
        raise OSError(f"network access blocked by scripts/nonet ({kind})")
    return f


socket.getaddrinfo = _deny("getaddrinfo"); socket.create_connection = _deny("create_connection"); socket.socket.connect = _deny("connect"); socket.socket.connect_ex = _deny("connect_ex")
