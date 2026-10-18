"""Network guard for reproduction runs. Put this directory first on PYTHONPATH (the clean-room does it when NBA_BLOCK_NETWORK=1): every Python process, including the stage
subprocesses, then refuses all outbound (non-loopback) connections and name lookups and appends each attempt to $NBA_NONET_LOG. Loopback is allowed because the Windows asyncio
event loop (imported by xlwings) builds a loopback socket pair. A reproduction that finishes with an empty log made no network calls."""
import os, socket, sys, time
_LOG = os.environ.get("NBA_NONET_LOG"); _LOCAL = {"127.0.0.1", "::1", "localhost", "", None}
_connect, _connect_ex, _gai = socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo


def _host(addr):
    return addr[0] if isinstance(addr, tuple) and addr else addr


def _note(kind, what):
    if _LOG:
        with open(_LOG, "a") as fh: fh.write(f"{time.strftime('%H:%M:%S')} {kind} {sys.argv[:2]} {str(what)[:100]}\n")
    raise OSError(f"outbound network access blocked by scripts/nonet ({kind})")


def connect(self, addr):
    if self.family == getattr(socket, "AF_UNIX", -1) or _host(addr) in _LOCAL: return _connect(self, addr)
    _note("connect", addr)


def connect_ex(self, addr):
    if self.family == getattr(socket, "AF_UNIX", -1) or _host(addr) in _LOCAL: return _connect_ex(self, addr)
    _note("connect_ex", addr)


def getaddrinfo(host, *a, **k):
    if host in _LOCAL: return _gai(host, *a, **k)
    _note("getaddrinfo", host)


socket.socket.connect = connect; socket.socket.connect_ex = connect_ex; socket.getaddrinfo = getaddrinfo
