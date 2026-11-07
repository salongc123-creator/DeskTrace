"""Notification-area (tray) icon with a menu and Windows notifications — pure ctypes, Windows only.

The icon lives on its own thread with a hidden window and a message loop. Menu choices arrive
as WM_COMMAND messages and are passed to ``on_command(name)``; ``menu()`` is asked for the
current items every time the menu opens, so labels and check marks are always up to date.
"""
import ctypes
import os
import threading
import time

available = os.name == 'nt'

if available:
    from ctypes import wintypes

    _user32 = ctypes.WinDLL('user32', use_last_error=True)
    _shell32 = ctypes.WinDLL('shell32', use_last_error=True)
    _kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

    LRESULT = wintypes.LPARAM
    WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

    class WNDCLASSEXW(ctypes.Structure):
        _fields_ = [('cbSize', wintypes.UINT), ('style', wintypes.UINT), ('lpfnWndProc', WNDPROC),
                    ('cbClsExtra', ctypes.c_int), ('cbWndExtra', ctypes.c_int), ('hInstance', wintypes.HINSTANCE),
                    ('hIcon', wintypes.HICON), ('hCursor', wintypes.HANDLE), ('hbrBackground', wintypes.HBRUSH),
                    ('lpszMenuName', wintypes.LPCWSTR), ('lpszClassName', wintypes.LPCWSTR), ('hIconSm', wintypes.HICON)]

    class GUID(ctypes.Structure):
        _fields_ = [('Data1', wintypes.DWORD), ('Data2', wintypes.WORD), ('Data3', wintypes.WORD),
                    ('Data4', ctypes.c_ubyte * 8)]

    class NOTIFYICONDATAW(ctypes.Structure):
        _fields_ = [('cbSize', wintypes.DWORD), ('hWnd', wintypes.HWND), ('uID', wintypes.UINT),
                    ('uFlags', wintypes.UINT), ('uCallbackMessage', wintypes.UINT), ('hIcon', wintypes.HICON),
                    ('szTip', wintypes.WCHAR * 128), ('dwState', wintypes.DWORD), ('dwStateMask', wintypes.DWORD),
                    ('szInfo', wintypes.WCHAR * 256), ('uVersion', wintypes.UINT), ('szInfoTitle', wintypes.WCHAR * 64),
                    ('dwInfoFlags', wintypes.DWORD), ('guidItem', GUID), ('hBalloonIcon', wintypes.HICON)]

    def _fn(dll, name, res, *args):
        f = getattr(dll, name)
        f.restype, f.argtypes = res, args
        return f

    RegisterClassExW = _fn(_user32, 'RegisterClassExW', wintypes.ATOM, ctypes.POINTER(WNDCLASSEXW))
    CreateWindowExW = _fn(_user32, 'CreateWindowExW', wintypes.HWND, wintypes.DWORD, wintypes.LPCWSTR,
                          wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                          wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID)
    DefWindowProcW = _fn(_user32, 'DefWindowProcW', LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
    DestroyWindow = _fn(_user32, 'DestroyWindow', wintypes.BOOL, wintypes.HWND)
    GetMessageW = _fn(_user32, 'GetMessageW', wintypes.BOOL, ctypes.POINTER(wintypes.MSG), wintypes.HWND,
                      wintypes.UINT, wintypes.UINT)
    TranslateMessage = _fn(_user32, 'TranslateMessage', wintypes.BOOL, ctypes.POINTER(wintypes.MSG))
    DispatchMessageW = _fn(_user32, 'DispatchMessageW', LRESULT, ctypes.POINTER(wintypes.MSG))
    PostMessageW = _fn(_user32, 'PostMessageW', wintypes.BOOL, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
    PostQuitMessage = _fn(_user32, 'PostQuitMessage', None, ctypes.c_int)
    RegisterWindowMessageW = _fn(_user32, 'RegisterWindowMessageW', wintypes.UINT, wintypes.LPCWSTR)
    LoadImageW = _fn(_user32, 'LoadImageW', wintypes.HANDLE, wintypes.HINSTANCE, wintypes.LPCWSTR, wintypes.UINT,
                     ctypes.c_int, ctypes.c_int, wintypes.UINT)
    DestroyIcon = _fn(_user32, 'DestroyIcon', wintypes.BOOL, wintypes.HICON)
    GetSystemMetrics = _fn(_user32, 'GetSystemMetrics', ctypes.c_int, ctypes.c_int)
    CreatePopupMenu = _fn(_user32, 'CreatePopupMenu', wintypes.HMENU)
    AppendMenuW = _fn(_user32, 'AppendMenuW', wintypes.BOOL, wintypes.HMENU, wintypes.UINT, ctypes.c_size_t, wintypes.LPCWSTR)
    SetMenuDefaultItem = _fn(_user32, 'SetMenuDefaultItem', wintypes.BOOL, wintypes.HMENU, wintypes.UINT, wintypes.UINT)
    TrackPopupMenu = _fn(_user32, 'TrackPopupMenu', wintypes.BOOL, wintypes.HMENU, wintypes.UINT, ctypes.c_int,
                         ctypes.c_int, ctypes.c_int, wintypes.HWND, wintypes.LPVOID)
    DestroyMenu = _fn(_user32, 'DestroyMenu', wintypes.BOOL, wintypes.HMENU)
    SetForegroundWindow = _fn(_user32, 'SetForegroundWindow', wintypes.BOOL, wintypes.HWND)
    GetCursorPos = _fn(_user32, 'GetCursorPos', wintypes.BOOL, ctypes.POINTER(wintypes.POINT))
    Shell_NotifyIconW = _fn(_shell32, 'Shell_NotifyIconW', wintypes.BOOL, wintypes.DWORD, ctypes.POINTER(NOTIFYICONDATAW))
    GetModuleHandleW = _fn(_kernel32, 'GetModuleHandleW', wintypes.HMODULE, wintypes.LPCWSTR)

WM_NULL, WM_DESTROY, WM_CLOSE, WM_COMMAND = 0x0000, 0x0002, 0x0010, 0x0111
WM_LBUTTONUP, WM_RBUTTONUP, WM_CONTEXTMENU, WM_USER, WM_APP = 0x0202, 0x0205, 0x007B, 0x0400, 0x8000
NIN_BALLOONUSERCLICK = WM_USER + 5
CALLBACK_MSG = WM_APP + 1
NIM_ADD, NIM_MODIFY, NIM_DELETE = 0, 1, 2
NIF_MESSAGE, NIF_ICON, NIF_TIP, NIF_INFO, NIF_SHOWTIP = 0x1, 0x2, 0x4, 0x10, 0x80
NIIF_USER, NIIF_NOSOUND, NIIF_LARGE_ICON = 0x4, 0x10, 0x20
WM_HOTKEY, HOTKEY_ID = 0x0312, 0xD7  # 2.6.0 #14
MF_STRING, MF_GRAYED, MF_CHECKED, MF_POPUP, MF_SEPARATOR = 0x0, 0x1, 0x8, 0x10, 0x800
TPM_RIGHTBUTTON, TPM_BOTTOMALIGN = 0x2, 0x20
IMAGE_ICON, LR_LOADFROMFILE = 1, 0x10
SM_CXICON, SM_CXSMICON = 11, 49
CLASS_NAME = 'DesktopWatchTray'


class Tray:
    """``menu()`` returns a list of items: ('-',) for a separator, (cmd, label, checked) for an
    entry, or ('>', label, [items]) for a submenu. The first entry is shown in bold (default)."""

    def __init__(self, icon, paused_icon, on_command, menu, commands=(), tooltip='DeskTrace'):
        self.icon_path, self.paused_icon_path = str(icon), str(paused_icon)
        self.on_command, self.menu = on_command, menu
        self.tooltip, self.paused = tooltip, False
        self.hwnd = None
        self.ready = threading.Event()
        self.added = False
        self._taskbar_created = None  # set after the window exists; Windows sends messages before that
        self._icon = self._icon_paused = self._icon_large = None
        self.state, self.state_icons, self._state_icon = None, {}, {}  # 2.6.0 #45: 'busy' / 'alert' -> .ico path
        # Stable menu ids (100, 101, … in ``commands`` order), so WM_COMMAND can be posted by tests too.
        self._ids = {100 + i: name for i, name in enumerate(commands)}
        self._last_click = 0.0
        self.thread = threading.Thread(target=self._run, daemon=True, name='tray')

    def start(self):
        if available:
            self.thread.start()
            self.ready.wait(5)
        return self.added

    # -- GUI thread ---------------------------------------------------------------------------
    def _run(self):
        try:
            hinst = GetModuleHandleW(None)
            self._proc = WNDPROC(self._wndproc)       # keep a reference: Windows calls back into it
            wc = WNDCLASSEXW()
            wc.cbSize = ctypes.sizeof(WNDCLASSEXW)
            wc.lpfnWndProc = self._proc
            wc.hInstance = hinst
            wc.lpszClassName = CLASS_NAME
            RegisterClassExW(ctypes.byref(wc))        # fails harmlessly if already registered
            self.hwnd = CreateWindowExW(0, CLASS_NAME, 'DeskTrace', 0, 0, 0, 0, 0, None, None, hinst, None)
            self._taskbar_created = RegisterWindowMessageW('TaskbarCreated')
            small, large = GetSystemMetrics(SM_CXSMICON), GetSystemMetrics(SM_CXICON)
            self._icon = LoadImageW(None, self.icon_path, IMAGE_ICON, small, small, LR_LOADFROMFILE)
            self._icon_paused = LoadImageW(None, self.paused_icon_path, IMAGE_ICON, small, small, LR_LOADFROMFILE) or self._icon
            self._icon_large = LoadImageW(None, self.icon_path, IMAGE_ICON, large, large, LR_LOADFROMFILE)
            for k, p in self.state_icons.items():
                self._state_icon[k] = LoadImageW(None, str(p), IMAGE_ICON, small, small, LR_LOADFROMFILE)
            self.added = self._notify(NIM_ADD)
            # 2.6.0 #14: Ctrl+Alt+Z anywhere -> the files just deleted or overwritten (if no other program took it)
            self.hotkey = bool(ctypes.windll.user32.RegisterHotKey(self.hwnd, HOTKEY_ID, 0x0002 | 0x0001 | 0x4000, ord('Z')))
        finally:
            self.ready.set()
        msg = wintypes.MSG()
        while GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            TranslateMessage(ctypes.byref(msg))
            DispatchMessageW(ctypes.byref(msg))
        for h in {self._icon, self._icon_paused, self._icon_large}:
            if h:
                DestroyIcon(h)

    def _data(self, flags):
        d = NOTIFYICONDATAW()
        d.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        d.hWnd, d.uID, d.uFlags = self.hwnd, 1, flags
        d.uCallbackMessage = CALLBACK_MSG
        d.hIcon = self._icon_paused if self.paused else (self._state_icon.get(self.state) or self._icon)
        d.szTip = self.tooltip[:127]
        return d

    def _notify(self, op):
        return bool(Shell_NotifyIconW(op, ctypes.byref(self._data(NIF_MESSAGE | NIF_ICON | NIF_TIP | NIF_SHOWTIP))))

    def _wndproc(self, hwnd, msg, wparam, lparam):
        try:
            if msg == CALLBACK_MSG:
                event = lparam & 0xFFFF
                if event == WM_LBUTTONUP:
                    if time.time() - self._last_click > 1.0:   # a double click shouldn't open two tabs
                        self._last_click = time.time()
                        self.on_command('open')
                elif event in (WM_RBUTTONUP, WM_CONTEXTMENU):
                    self._show_menu()
                elif event == NIN_BALLOONUSERCLICK:
                    self.on_command('open-notification')
                return 0
            if msg == WM_HOTKEY and wparam == HOTKEY_ID:
                self.on_command('quick-restore')
                return 0
            if msg == WM_COMMAND:
                name = self._ids.get(wparam & 0xFFFF)
                if name:
                    self.on_command(name)
                return 0
            if self._taskbar_created and msg == self._taskbar_created:  # Explorer restarted: add the icon again
                self.added = self._notify(NIM_ADD)
                return 0
            if msg == WM_CLOSE:
                DestroyWindow(hwnd)
                return 0
            if msg == WM_DESTROY:
                Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self._data(0)))
                PostQuitMessage(0)
                return 0
        except Exception as e:  # never let an exception escape into Windows
            print('tray error:', repr(e))
        return DefWindowProcW(hwnd, msg, wparam, lparam)

    def _build(self, items):
        hmenu = CreatePopupMenu()
        for it in items:
            if it[0] == '-':
                AppendMenuW(hmenu, MF_SEPARATOR, 0, None)
            elif it[0] == '>':
                AppendMenuW(hmenu, MF_POPUP, self._build(it[2]), it[1])
            else:
                cmd_id = self.command_id(it[0])
                if cmd_id is None:
                    cmd_id = 100 + len(self._ids)
                    self._ids[cmd_id] = it[0]
                AppendMenuW(hmenu, MF_STRING | (MF_CHECKED if len(it) > 2 and it[2] else 0), cmd_id, it[1])
        return hmenu

    def _show_menu(self):
        hmenu = self._build(self.menu())
        SetMenuDefaultItem(hmenu, 0, 1)
        pt = wintypes.POINT()
        GetCursorPos(ctypes.byref(pt))
        SetForegroundWindow(self.hwnd)                          # so the menu closes when clicking elsewhere
        TrackPopupMenu(hmenu, TPM_RIGHTBUTTON | TPM_BOTTOMALIGN, pt.x, pt.y, 0, self.hwnd, None)
        PostMessageW(self.hwnd, WM_NULL, 0, 0)
        DestroyMenu(hmenu)

    # -- any thread ----------------------------------------------------------------------------
    def command_id(self, name):
        """The menu id bound to ``name``."""
        return next((i for i, n in self._ids.items() if n == name), None)

    def update(self, tooltip=None, paused=None, state=False):
        changed = False
        if state is not False and state != self.state:  # None = still, 'busy' = green, 'alert' = red (2.6.0 #45)
            self.state, changed = state, True
        if tooltip is not None and tooltip != self.tooltip:
            self.tooltip, changed = tooltip, True
        if paused is not None and paused != self.paused:
            self.paused, changed = paused, True
        if changed and self.added:
            self._notify(NIM_MODIFY)

    def notify(self, title, text, sound=False):
        """Show a Windows notification from the tray icon."""
        if not self.added:
            return False
        d = self._data(NIF_INFO)
        d.szInfoTitle = title[:63]
        d.szInfo = text[:255]
        d.dwInfoFlags = NIIF_USER | NIIF_LARGE_ICON | (0 if sound else NIIF_NOSOUND)
        d.hBalloonIcon = self._icon_large
        return bool(Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(d)))

    def stop(self):
        if self.hwnd:
            PostMessageW(self.hwnd, WM_CLOSE, 0, 0)
            self.thread.join(3)
