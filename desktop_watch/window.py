"""DeskTrace's own app window.

The interface runs in a native window through Microsoft Edge WebView2 (part of Windows 11 and of
current Windows 10), driven directly through ctypes, so nothing extra has to be installed. The
background service (server.py) does the monitoring and starts this window; closing the window leaves
the service running in the notification area.

    pythonw window.py --url http://127.0.0.1:8765/app?k=... --data <data dir> [--hash #event=12] [--pid N]

Only one window per data folder: starting a second one brings the first to the front (and passes it
the --hash to open) instead.
"""
import argparse
import ctypes
import json
import os
import sys
import threading
import urllib.parse
import winreg
import zlib
from ctypes import wintypes as W
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
ICON = APP_DIR / 'static' / 'icon.ico'
AUMID = 'DeskTrace.App'
APP_NAME = 'DeskTrace'

u32, k32, ole32, gdi32 = ctypes.windll.user32, ctypes.windll.kernel32, ctypes.windll.ole32, ctypes.windll.gdi32
dwmapi = ctypes.windll.dwmapi
HRESULT = ctypes.c_long
LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, W.HWND, W.UINT, W.WPARAM, W.LPARAM)
PV = ctypes.c_void_p

WM_DESTROY, WM_SIZE, WM_SETFOCUS, WM_CLOSE, WM_MOVE = 0x0002, 0x0005, 0x0007, 0x0010, 0x0003
WM_GETMINMAXINFO, WM_COPYDATA, WM_DPICHANGED, WM_APP = 0x0024, 0x004A, 0x02E0, 0x8000
WM_SHOW_ERROR = WM_APP + 1
WS_OVERLAPPEDWINDOW, CW_USEDEFAULT = 0x00CF0000, -0x80000000
SW_SHOWNORMAL, SW_SHOWMAXIMIZED, SW_RESTORE, SW_MINIMIZE = 1, 3, 9, 6
SIZE_MINIMIZED = 1
E_NOINTERFACE = 0x80004002 - (1 << 32)
IID_IUNKNOWN = '{00000000-0000-0000-C000-000000000046}'
IID_SETTINGS3 = '{fdb5ab74-af33-4854-84f0-0a631deb5eba}'
IID_CONTROLLER2 = '{c979903e-d4ca-4228-92eb-47ee3fa96eab}'


class GUID(ctypes.Structure):
    _fields_ = [('a', W.DWORD), ('b', W.WORD), ('c', W.WORD), ('d', ctypes.c_ubyte * 8)]

    @classmethod
    def parse(cls, s):
        g = cls()
        ole32.CLSIDFromString(ctypes.c_wchar_p(s), ctypes.byref(g))
        return g

    def __eq__(self, other):
        return bytes(self) == bytes(other)


class RECT(ctypes.Structure):
    _fields_ = [('left', W.LONG), ('top', W.LONG), ('right', W.LONG), ('bottom', W.LONG)]


class MINMAXINFO(ctypes.Structure):
    _fields_ = [('reserved', W.POINT), ('maxSize', W.POINT), ('maxPos', W.POINT), ('minTrack', W.POINT), ('maxTrack', W.POINT)]


class COPYDATASTRUCT(ctypes.Structure):
    _fields_ = [('dwData', ctypes.c_size_t), ('cbData', W.DWORD), ('lpData', PV)]


class WINDOWPLACEMENT(ctypes.Structure):
    _fields_ = [('length', W.UINT), ('flags', W.UINT), ('showCmd', W.UINT), ('ptMin', W.POINT),
                ('ptMax', W.POINT), ('rcNormal', RECT)]


class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [('cbSize', W.UINT), ('style', W.UINT), ('lpfnWndProc', WNDPROC), ('cbClsExtra', ctypes.c_int),
                ('cbWndExtra', ctypes.c_int), ('hInstance', W.HINSTANCE), ('hIcon', W.HICON), ('hCursor', W.HANDLE),
                ('hbrBackground', W.HBRUSH), ('lpszMenuName', W.LPCWSTR), ('lpszClassName', W.LPCWSTR), ('hIconSm', W.HICON)]


for fn, res, args in [
    (u32.DefWindowProcW, LRESULT, [W.HWND, W.UINT, W.WPARAM, W.LPARAM]),
    (u32.CreateWindowExW, W.HWND, [W.DWORD, W.LPCWSTR, W.LPCWSTR, W.DWORD, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                   ctypes.c_int, W.HWND, W.HMENU, W.HINSTANCE, PV]),
    (u32.RegisterClassExW, W.ATOM, [ctypes.POINTER(WNDCLASSEXW)]),
    (u32.FindWindowW, W.HWND, [W.LPCWSTR, W.LPCWSTR]),
    (u32.SendMessageW, LRESULT, [W.HWND, W.UINT, W.WPARAM, W.LPARAM]),
    (u32.PostMessageW, W.BOOL, [W.HWND, W.UINT, W.WPARAM, W.LPARAM]),
    (u32.LoadImageW, W.HANDLE, [W.HINSTANCE, W.LPCWSTR, W.UINT, ctypes.c_int, ctypes.c_int, W.UINT]),
    (u32.LoadCursorW, W.HANDLE, [W.HINSTANCE, PV]),
    (u32.GetClientRect, W.BOOL, [W.HWND, ctypes.POINTER(RECT)]),
    (u32.SetWindowPos, W.BOOL, [W.HWND, W.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, W.UINT]),
    (u32.GetWindowPlacement, W.BOOL, [W.HWND, ctypes.POINTER(WINDOWPLACEMENT)]),
    (u32.SetWindowPlacement, W.BOOL, [W.HWND, ctypes.POINTER(WINDOWPLACEMENT)]),
    (u32.MonitorFromRect, W.HANDLE, [ctypes.POINTER(RECT), W.DWORD]),
    (u32.GetDpiForWindow, W.UINT, [W.HWND]),
    (u32.SetWindowTextW, W.BOOL, [W.HWND, W.LPCWSTR]),
    (u32.MessageBoxW, ctypes.c_int, [W.HWND, W.LPCWSTR, W.LPCWSTR, W.UINT]),
    (u32.IsIconic, W.BOOL, [W.HWND]),
    (u32.ShowWindow, W.BOOL, [W.HWND, ctypes.c_int]),
    (u32.SetForegroundWindow, W.BOOL, [W.HWND]),
    (u32.GetMessageW, W.BOOL, [ctypes.POINTER(W.MSG), W.HWND, W.UINT, W.UINT]),
    (u32.TranslateMessage, W.BOOL, [ctypes.POINTER(W.MSG)]),
    (u32.DispatchMessageW, LRESULT, [ctypes.POINTER(W.MSG)]),
    (u32.DestroyWindow, W.BOOL, [W.HWND]),
    (gdi32.CreateSolidBrush, W.HBRUSH, [W.COLORREF]),
    (k32.GetModuleHandleW, W.HMODULE, [W.LPCWSTR]),
    (k32.OpenProcess, W.HANDLE, [W.DWORD, W.BOOL, W.DWORD]),
    (k32.WaitForSingleObject, W.DWORD, [W.HANDLE, W.DWORD]),
    (ole32.CoTaskMemFree, None, [PV]),
    (ole32.CoInitializeEx, HRESULT, [PV, W.DWORD]),
    (dwmapi.DwmSetWindowAttribute, HRESULT, [W.HWND, W.DWORD, PV, W.DWORD]),
]:
    fn.restype, fn.argtypes = res, args


# -- minimal COM plumbing -------------------------------------------------------------------------------
def vcall(obj, index, argtypes, *args):
    """Call method ``index`` of the COM interface pointer ``obj``; raise OSError on a failed HRESULT."""
    vtbl = ctypes.cast(obj, ctypes.POINTER(ctypes.POINTER(PV)))[0]
    hr = ctypes.WINFUNCTYPE(HRESULT, PV, *argtypes)(vtbl[index])(obj, *args)
    if hr < 0:
        raise OSError(f'COM call {index} failed: 0x{hr & 0xFFFFFFFF:08X}')
    return hr


def get_ptr(obj, index):
    out = PV()
    vcall(obj, index, [ctypes.POINTER(PV)], ctypes.byref(out))
    return out.value


def get_str(obj, index):
    out = ctypes.c_void_p()
    vcall(obj, index, [ctypes.POINTER(PV)], ctypes.byref(out))
    try:
        return ctypes.wstring_at(out.value) if out.value else ''
    finally:
        ole32.CoTaskMemFree(out)


def get_bool(obj, index):
    out = W.BOOL()
    vcall(obj, index, [ctypes.POINTER(W.BOOL)], ctypes.byref(out))
    return bool(out.value)


def query(obj, iid):
    out = PV()
    try:
        vcall(obj, 0, [ctypes.POINTER(GUID), ctypes.POINTER(PV)], ctypes.byref(GUID.parse(iid)), ctypes.byref(out))
        return out.value
    except OSError:
        return None


class Callback:
    """A COM object with one Invoke method: what WebView2 calls back when something completes or happens.
    Instances are kept alive for the life of the process (WebView2 may call them at any time)."""
    _alive = []
    _QI = ctypes.WINFUNCTYPE(HRESULT, PV, ctypes.POINTER(GUID), ctypes.POINTER(PV))
    _REF = ctypes.WINFUNCTYPE(W.ULONG, PV)
    _unknown = None

    def __init__(self, iid, fn, *argtypes):
        if Callback._unknown is None:
            Callback._unknown = GUID.parse(IID_IUNKNOWN)
        mine = GUID.parse(iid)

        def qi(this, riid, ppv):
            if riid[0] == Callback._unknown or riid[0] == mine:
                ppv[0] = this
                return 0
            if os.environ.get('DW_QI_LOG'):
                log(f'QI refused {bytes(riid[0]).hex()} (callback {iid})')
            ppv[0] = None
            return E_NOINTERFACE

        def invoke(this, *a):
            try:
                fn(*a)
            except Exception as e:  # never let a Python error unwind into WebView2
                log(f'callback error: {e!r}')
            return 0

        self.funcs = [self._QI(qi), self._REF(lambda this: 1), self._REF(lambda this: 1),
                      ctypes.WINFUNCTYPE(HRESULT, PV, *argtypes)(invoke)]
        self.vtbl = (PV * 4)(*[ctypes.cast(f, PV) for f in self.funcs])
        self.obj = PV(ctypes.addressof(self.vtbl))
        self.ptr = ctypes.addressof(self.obj)
        Callback._alive.append(self)


def log(msg):
    try:
        print(msg, flush=True)
    except Exception:
        pass


# -- WebView2 runtime -------------------------------------------------------------------------------------
RUNTIME_GUID = '{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}'


def find_runtime():
    """Folder of the installed WebView2 runtime (machine-wide or per-user), or None."""
    keys = [(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\\' + RUNTIME_GUID),
            (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\EdgeUpdate\Clients\\' + RUNTIME_GUID),
            (winreg.HKEY_CURRENT_USER, r'Software\Microsoft\EdgeUpdate\Clients\\' + RUNTIME_GUID)]
    for root, key in keys:
        try:
            with winreg.OpenKey(root, key.replace('\\\\', '\\')) as k:
                ver = winreg.QueryValueEx(k, 'pv')[0]
                try:
                    loc = winreg.QueryValueEx(k, 'location')[0]
                except OSError:
                    loc = os.path.join(os.environ['ProgramFiles(x86)'] if root == winreg.HKEY_LOCAL_MACHINE
                                       else os.environ['LOCALAPPDATA'], 'Microsoft', 'EdgeWebView', 'Application')
        except OSError:
            continue
        dll = Path(loc) / ver / 'EBWebView' / 'x64' / 'EmbeddedBrowserWebView.dll'
        if ver and ver != '0.0.0.0' and dll.exists():
            return dll
    return None


def bool_arg(v):
    return W.BOOL(1 if v else 0)


# -- the window ----------------------------------------------------------------------------------------------
class AppWindow:
    def __init__(self, url, data_dir, hash_='', server_pid=None):
        self.url, self.data = url, Path(data_dir)
        self.hash = hash_
        self.server_pid = server_pid
        self.hwnd = None
        self.controller = self.webview = None
        self.state_file = self.data / 'window.json'
        self.class_name = 'DesktopWatchWindow-%08x' % zlib.crc32(str(self.data.resolve()).lower().encode())
        self.dark = self.load_state().get('dark', system_dark())
        self.origin = '{0.scheme}://{0.netloc}'.format(urllib.parse.urlparse(url))

    # window state -----------------------------------------------------------------------------------------
    def load_state(self):
        try:
            return json.loads(self.state_file.read_text('utf-8'))
        except (OSError, ValueError):
            return {}

    def save_state(self):
        wp = WINDOWPLACEMENT(length=ctypes.sizeof(WINDOWPLACEMENT))
        if not u32.GetWindowPlacement(self.hwnd, ctypes.byref(wp)):
            return
        r = wp.rcNormal
        state = {**self.load_state(), 'rect': [r.left, r.top, r.right, r.bottom],
                 'max': wp.showCmd == SW_SHOWMAXIMIZED, 'dark': self.dark}
        try:
            self.state_file.write_text(json.dumps(state), 'utf-8')
        except OSError:
            pass

    # creation --------------------------------------------------------------------------------------------
    def create(self):
        hinst = k32.GetModuleHandleW(None)
        big = u32.LoadImageW(None, str(ICON), 1, 0, 0, 0x10 | 0x40)    # IMAGE_ICON, LR_LOADFROMFILE|LR_DEFAULTSIZE
        small = u32.LoadImageW(None, str(ICON), 1, 16, 16, 0x10)
        self._proc = WNDPROC(self.wndproc)
        wc = WNDCLASSEXW(cbSize=ctypes.sizeof(WNDCLASSEXW), style=0x3, lpfnWndProc=self._proc, hInstance=hinst,
                         hIcon=big, hIconSm=small, hCursor=u32.LoadCursorW(None, PV(32512)),
                         hbrBackground=gdi32.CreateSolidBrush(0x1A1310 if self.dark else 0xFAF7F5),
                         lpszClassName=self.class_name)
        if not u32.RegisterClassExW(ctypes.byref(wc)):
            raise OSError('RegisterClassEx failed')
        self.hwnd = u32.CreateWindowExW(0, self.class_name, APP_NAME, WS_OVERLAPPEDWINDOW,
                                        CW_USEDEFAULT, CW_USEDEFAULT, 1280, 820, None, None, hinst, None)
        if not self.hwnd:
            raise OSError('CreateWindowEx failed')
        self.set_dark_titlebar(self.dark)
        state = self.load_state()
        show = SW_SHOWNORMAL
        if state.get('rect'):
            r = RECT(*state['rect'])
            if u32.MonitorFromRect(ctypes.byref(r), 0) and r.right - r.left > 300 and r.bottom - r.top > 200:
                wp = WINDOWPLACEMENT(length=ctypes.sizeof(WINDOWPLACEMENT), showCmd=SW_SHOWNORMAL, rcNormal=r)
                u32.SetWindowPlacement(self.hwnd, ctypes.byref(wp))
            if state.get('max'):
                show = SW_SHOWMAXIMIZED
        else:  # first start: a comfortable size for the screen it opens on
            scale = u32.GetDpiForWindow(self.hwnd) / 96
            u32.SetWindowPos(self.hwnd, None, 0, 0, int(1280 * scale), int(820 * scale), 0x0002 | 0x0004)  # NOMOVE|NOZORDER
        u32.ShowWindow(self.hwnd, show)
        u32.SetForegroundWindow(self.hwnd)

    def set_dark_titlebar(self, dark):
        v = ctypes.c_int(1 if dark else 0)
        for attr in (20, 19):  # DWMWA_USE_IMMERSIVE_DARK_MODE (newer / older Windows 10 builds)
            if dwmapi.DwmSetWindowAttribute(self.hwnd, attr, ctypes.byref(v), 4) == 0:
                break
        mica = ctypes.c_int(2)  # DWMWA_SYSTEMBACKDROP_TYPE = 38, DWMSBT_MAINWINDOW (Mica): Windows 11 22H2+, ignored before (2.6.0 #42)
        dwmapi.DwmSetWindowAttribute(self.hwnd, 38, ctypes.byref(mica), 4)

    def start_webview(self):
        dll_path = find_runtime()
        if not dll_path:
            raise RuntimeError('webview2-missing')
        dll = ctypes.WinDLL(str(dll_path))
        create_env = dll.CreateWebViewEnvironmentWithOptionsInternal
        create_env.restype = HRESULT
        create_env.argtypes = [W.BOOL, ctypes.c_int, W.LPCWSTR, PV, PV]
        profile = self.data / 'webview'
        profile.mkdir(parents=True, exist_ok=True)
        self._env_cb = Callback('{4e8a3389-c9d8-4bd2-b6b5-124fee6cc14d}', self.on_environment, HRESULT, PV)
        hr = create_env(1, 0, str(profile), None, self._env_cb.ptr)
        if hr < 0:
            raise OSError(f'WebView2 environment: 0x{hr & 0xFFFFFFFF:08X}')

    def on_environment(self, hr, env):
        if hr < 0 or not env:
            return self.fail(f'WebView2 environment failed: 0x{hr & 0xFFFFFFFF:08X}')
        vcall(env, 1, [])  # AddRef: keep it
        self.env = env
        self._ctl_cb = Callback('{6c4819f3-c9b7-4260-8127-c9f5bde7f68c}', self.on_controller, HRESULT, PV)
        vcall(env, 3, [W.HWND, PV], self.hwnd, self._ctl_cb.ptr)  # CreateCoreWebView2Controller

    def on_controller(self, hr, controller):
        if hr < 0 or not controller:
            return self.fail(f'WebView2 controller failed: 0x{hr & 0xFFFFFFFF:08X}')
        vcall(controller, 1, [])
        self.controller = controller
        c2 = query(controller, IID_CONTROLLER2)
        if c2:  # no white flash in dark mode while the page loads
            color = (ctypes.c_ubyte * 4)(255, *((0x10, 0x13, 0x1A) if self.dark else (0xF5, 0xF7, 0xFA)))
            try:
                vcall(c2, 27, [ctypes.c_uint32], int.from_bytes(bytes(color), 'little'))
            except OSError:
                pass
        self.webview = get_ptr(controller, 25)  # get_CoreWebView2
        self.configure()
        self.resize()
        vcall(controller, 4, [W.BOOL], bool_arg(True))  # put_IsVisible
        self.navigate(self.url + self.hash)
        self.focus()

    def configure(self):
        wv = self.webview
        s = get_ptr(wv, 3)  # get_Settings
        vcall(s, 10, [W.BOOL], bool_arg(False))  # put_IsStatusBarEnabled
        vcall(s, 12, [W.BOOL], bool_arg(bool(os.environ.get('DW_DEVTOOLS'))))  # put_AreDevToolsEnabled
        vcall(s, 16, [W.BOOL], bool_arg(False))  # put_AreHostObjectsAllowed
        s3 = query(s, IID_SETTINGS3)
        if s3:
            try:
                vcall(s3, 24, [W.BOOL], bool_arg(False))  # put_AreBrowserAcceleratorKeysEnabled: no F5, Ctrl+P, ...
            except OSError:
                pass
        token = ctypes.c_int64()
        tok = ctypes.byref(token)
        self._title_cb = Callback('{f5f2b923-953e-4042-9f95-f3a118e1afd4}', self.on_title, PV, PV)
        vcall(wv, 46, [PV, PV], self._title_cb.ptr, tok)      # add_DocumentTitleChanged
        self._msg_cb = Callback('{57213f19-00e6-49fa-8e07-898ea01ecbd2}', self.on_message, PV, PV)
        vcall(wv, 34, [PV, PV], self._msg_cb.ptr, tok)        # add_WebMessageReceived
        self._nav_cb = Callback('{9adbe429-f36d-432b-9ddc-f8881fbd76e3}', self.on_navigation_starting, PV, PV)
        vcall(wv, 7, [PV, PV], self._nav_cb.ptr, tok)         # add_NavigationStarting
        self._done_cb = Callback('{d33a35bf-1c49-4f98-93ab-006e0533fe1c}', self.on_navigation_completed, PV, PV)
        vcall(wv, 15, [PV, PV], self._done_cb.ptr, tok)       # add_NavigationCompleted
        self._new_cb = Callback('{d4c185fe-c81c-4989-97af-2d3fa7ab5651}', self.on_new_window, PV, PV)
        vcall(wv, 44, [PV, PV], self._new_cb.ptr, tok)        # add_NewWindowRequested
        self._fail_cb = Callback('{79e0aea4-990b-42d9-aa1d-0fcc2e5bc7f1}', self.on_process_failed, PV, PV)
        vcall(wv, 25, [PV, PV], self._fail_cb.ptr, tok)       # add_ProcessFailed
        self._script_cb = Callback('{49511172-cc67-4bca-9923-137112f4c4cc}', lambda hr, res: None, HRESULT, W.LPCWSTR)

    # webview helpers ------------------------------------------------------------------------------------------
    def navigate(self, url):
        vcall(self.webview, 5, [W.LPCWSTR], url)

    def run_js(self, code):
        if self.webview:
            vcall(self.webview, 29, [W.LPCWSTR, PV], code, self._script_cb.ptr)  # ExecuteScript

    def resize(self):
        if self.controller:
            r = RECT()
            u32.GetClientRect(self.hwnd, ctypes.byref(r))
            vcall(self.controller, 6, [RECT], r)  # put_Bounds

    def focus(self):
        if self.controller:
            try:
                vcall(self.controller, 12, [ctypes.c_int], 0)  # MoveFocus(PROGRAMMATIC)
            except OSError:
                pass

    def internal(self, uri):
        return uri.startswith(self.origin + '/') or uri == self.origin or uri.startswith(('about:', 'data:', 'blob:'))

    # events -------------------------------------------------------------------------------------------------
    def on_title(self, sender, args):
        u32.SetWindowTextW(self.hwnd, get_str(self.webview, 48) or APP_NAME)

    def on_message(self, sender, args):
        msg = json.loads(get_str(args, 4) or 'null')  # get_WebMessageAsJson
        if not isinstance(msg, dict):
            return
        if 'theme' in msg:
            self.dark = msg['theme'] == 'dark'
            self.set_dark_titlebar(self.dark)
        if msg.get('cmd') == 'close':
            u32.PostMessageW(self.hwnd, WM_CLOSE, 0, 0)
        if msg.get('cmd') == 'external' and str(msg.get('url', '')).startswith(('http://', 'https://', 'mailto:')):
            os.startfile(msg['url'])

    def on_navigation_starting(self, sender, args):
        uri = get_str(args, 3)
        if not self.internal(uri):  # links to the web open in the normal browser, never inside the app
            vcall(args, 8, [W.BOOL], bool_arg(True))  # put_Cancel
            if uri.startswith(('http://', 'https://', 'mailto:')):
                os.startfile(uri)

    def on_new_window(self, sender, args):
        uri = get_str(args, 3)
        if not self.internal(uri):
            vcall(args, 6, [W.BOOL], bool_arg(True))  # put_Handled: no popup
            if uri.startswith(('http://', 'https://', 'mailto:')):
                os.startfile(uri)

    def on_navigation_completed(self, sender, args):
        if not get_bool(args, 3):  # get_IsSuccess
            status = ctypes.c_int()
            vcall(args, 4, [ctypes.POINTER(ctypes.c_int)], ctypes.byref(status))
            log(f'navigation failed (web error {status.value})')

    def on_process_failed(self, sender, args):
        log('WebView2 process failed; reloading')
        try:
            vcall(self.webview, 31, [])  # Reload
        except OSError:
            pass

    def fail(self, text):
        log(text)
        u32.PostMessageW(self.hwnd, WM_SHOW_ERROR, 0, 0)

    def wndproc(self, hwnd, msg, wp, lp):
        try:
            if msg == WM_SIZE:
                if self.controller:
                    vcall(self.controller, 4, [W.BOOL], bool_arg(wp != SIZE_MINIMIZED))  # idle while minimized
                    self.resize()
                return 0
            if msg == WM_MOVE and self.controller:
                vcall(self.controller, 23, [])  # NotifyParentWindowPositionChanged
            elif msg == WM_SETFOCUS:
                self.focus()
            elif msg == WM_GETMINMAXINFO:
                scale = (u32.GetDpiForWindow(hwnd) or 96) / 96
                mmi = ctypes.cast(lp, ctypes.POINTER(MINMAXINFO))[0]
                mmi.minTrack.x, mmi.minTrack.y = int(720 * scale), int(480 * scale)
                return 0
            elif msg == WM_DPICHANGED:
                r = ctypes.cast(lp, ctypes.POINTER(RECT))[0]
                u32.SetWindowPos(hwnd, None, r.left, r.top, r.right - r.left, r.bottom - r.top, 0x0004 | 0x0010)
                return 0
            elif msg == WM_COPYDATA:  # another start asked us to show something (e.g. #event=12)
                cds = ctypes.cast(lp, ctypes.POINTER(COPYDATASTRUCT))[0]
                if cds.dwData == 0xD3 and cds.lpData:
                    h = ctypes.wstring_at(cds.lpData, cds.cbData // 2)
                    if h:
                        self.run_js(f'location.hash = {json.dumps(h)}')
                self.bring_to_front()
                return 1
            elif msg == WM_SHOW_ERROR:
                u32.MessageBoxW(hwnd, 'The DeskTrace window could not be started (Microsoft Edge WebView2 '
                                'did not respond). The log has details.', APP_NAME, 0x10)
                u32.DestroyWindow(hwnd)
                return 0
            elif msg == WM_CLOSE:
                self.save_state()
                if self.controller:
                    try:
                        vcall(self.controller, 24, [])  # Close: ends the browser processes cleanly
                    except OSError:
                        pass
                    self.controller = None
                u32.DestroyWindow(hwnd)
                return 0
            elif msg == WM_DESTROY:
                u32.PostQuitMessage(0)
                return 0
        except Exception as e:
            log(f'wndproc error: {e!r}')
        return u32.DefWindowProcW(hwnd, msg, wp, lp)

    def bring_to_front(self):
        if u32.IsIconic(self.hwnd):
            u32.ShowWindow(self.hwnd, SW_RESTORE)
        u32.SetForegroundWindow(self.hwnd)

    def watch_server(self):
        """Close the window when the background service exits (tray → Quit, uninstall, update)."""
        h = k32.OpenProcess(0x00100000, False, self.server_pid)  # SYNCHRONIZE
        if h:
            k32.WaitForSingleObject(h, 0xFFFFFFFF)
            u32.PostMessageW(self.hwnd, WM_CLOSE, 0, 0)

    def run(self):
        self.create()
        self.start_webview()
        if self.server_pid:
            threading.Thread(target=self.watch_server, daemon=True).start()
        msg = W.MSG()
        while u32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            u32.TranslateMessage(ctypes.byref(msg))
            u32.DispatchMessageW(ctypes.byref(msg))


def system_dark():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize') as k:
            return winreg.QueryValueEx(k, 'AppsUseLightTheme')[0] == 0
    except OSError:
        return False


def pass_to_existing(class_name, hash_):
    """If a window for this data folder is already open, show it (with ``hash_``) and return True."""
    hwnd = u32.FindWindowW(class_name, None)
    if not hwnd:
        return False
    buf = ctypes.create_unicode_buffer(hash_ or '')
    cds = COPYDATASTRUCT(0xD3, len(hash_ or '') * 2, ctypes.cast(buf, PV))
    u32.SetForegroundWindow(hwnd)  # allowed: whoever started us passed on the right to take the foreground
    u32.SendMessageW(hwnd, WM_COPYDATA, 0, ctypes.addressof(cds))
    return True


def available():
    return find_runtime() is not None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--url', required=True)
    ap.add_argument('--data', required=True)
    ap.add_argument('--hash', default='')
    ap.add_argument('--pid', type=int)
    args = ap.parse_args()
    if sys.stdout is None:  # pythonw: log next to the service's log
        try:
            sys.stdout = sys.stderr = open(Path(args.data) / 'window.log', 'a', encoding='utf-8', buffering=1)
        except OSError:
            pass
    try:
        u32.SetProcessDpiAwarenessContext(PV(-4))  # per-monitor v2: crisp text on every screen
    except Exception:
        pass
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(ctypes.c_wchar_p(AUMID))
    except Exception:
        pass
    win = AppWindow(args.url, args.data, args.hash, args.pid)
    if pass_to_existing(win.class_name, args.hash):
        return
    ole32.CoInitializeEx(None, 0x2)  # STA, as WebView2 requires
    win.run()


if __name__ == '__main__':
    main()
