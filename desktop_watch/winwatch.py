"""Instant change notifications on Windows (ReadDirectoryChangesW via ctypes, no dependencies).

A Watcher reports every change below a folder as soon as Windows sees it, so the monitor
can rescan right away instead of waiting for its next periodic scan. Anywhere this is not
available, ``available`` is False and the monitor simply keeps polling.
"""
import ctypes
import os
import struct
import threading

available = os.name == 'nt'

if available:
    from ctypes import wintypes

    _k32 = ctypes.WinDLL('kernel32', use_last_error=True)

    def _fn(name, res, *args):
        f = getattr(_k32, name)
        f.restype, f.argtypes = res, args
        return f

    _CreateFileW = _fn('CreateFileW', wintypes.HANDLE, wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                       wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
    _ReadDirectoryChangesW = _fn('ReadDirectoryChangesW', wintypes.BOOL, wintypes.HANDLE, wintypes.LPVOID,
                                 wintypes.DWORD, wintypes.BOOL, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD),
                                 wintypes.LPVOID, wintypes.LPVOID)
    _CloseHandle = _fn('CloseHandle', wintypes.BOOL, wintypes.HANDLE)
    _CancelIoEx = _fn('CancelIoEx', wintypes.BOOL, wintypes.HANDLE, wintypes.LPVOID)
    _CancelSynchronousIo = _fn('CancelSynchronousIo', wintypes.BOOL, wintypes.HANDLE)
    _OpenThread = _fn('OpenThread', wintypes.HANDLE, wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)

    _INVALID = wintypes.HANDLE(-1).value
    _FILE_LIST_DIRECTORY = 0x0001
    _SHARE_ALL = 0x1 | 0x2 | 0x4                  # read | write | delete: never block the user's own operations
    _OPEN_EXISTING = 3
    _BACKUP_SEMANTICS = 0x02000000                # required to open a directory handle
    _NOTIFY = 0x1 | 0x2 | 0x8 | 0x10             # file name, dir name, size, last write
    _THREAD_TERMINATE = 0x0001                    # access right CancelSynchronousIo needs

# Actions reported per entry.
ADDED, REMOVED, MODIFIED, RENAMED_OLD, RENAMED_NEW = 1, 2, 3, 4, 5


class Watcher:
    """Watches ``path`` recursively on a background thread and calls ``callback(changes)``.

    ``changes`` is a list of ``(action, relative_path)``, or ``None`` when Windows dropped
    details because too much happened at once (the caller should then rescan everything).
    """

    def __init__(self, path, callback):
        self.path, self.callback = path, callback
        self.handle = None
        self.stopped = False
        self.failed = False
        self.thread = threading.Thread(target=self._run, daemon=True, name=f'watch {path}')
        self.thread.start()

    @property
    def alive(self):
        return self.thread.is_alive() and not self.failed

    def _run(self):
        h = _CreateFileW(self.path, _FILE_LIST_DIRECTORY, _SHARE_ALL, None, _OPEN_EXISTING, _BACKUP_SEMANTICS, None)
        if not h or h == _INVALID:
            self.failed = True
            return
        self.handle = h
        buf = ctypes.create_string_buffer(64 * 1024)
        got = wintypes.DWORD()
        try:
            while not self.stopped:
                if not _ReadDirectoryChangesW(h, buf, len(buf), True, _NOTIFY, ctypes.byref(got), None, None):
                    self.failed = not self.stopped   # cancelled on purpose, or the folder went away
                    break
                if self.stopped:
                    break
                try:
                    self.callback(self._parse(buf.raw[:got.value]) if got.value else None)
                except Exception as e:  # a bad callback must not kill the watcher
                    print('watch callback error:', repr(e))
        finally:
            self.handle = None
            _CloseHandle(h)

    @staticmethod
    def _parse(data):
        out, off = [], 0
        while off + 12 <= len(data):
            nxt, action, ln = struct.unpack_from('<III', data, off)
            out.append((action, data[off + 12:off + 12 + ln].decode('utf-16-le', 'replace')))
            if not nxt:
                break
            off += nxt
        return out

    def stop(self):
        self.stopped = True
        h = self.handle
        if h:
            _CancelIoEx(h, None)
        tid = self.thread.native_id
        if tid and self.thread.is_alive():  # interrupt the blocking call on the watcher thread itself
            th = _OpenThread(_THREAD_TERMINATE, False, tid)
            if th:
                _CancelSynchronousIo(th)
                _CloseHandle(th)
