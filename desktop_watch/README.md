# DeskTrace · 桌迹

(formerly *Desktop Watch*)

Real-time monitor for file creations, modifications, renames/moves and deletions, with a snapshot of
every version so you can open any file, see its content, and see exactly what changed.

**A desktop app with its own window.** The interface opens in a native window (Microsoft Edge WebView2,
built into Windows 11), not in a browser tab; the local service behind it only answers that window.
- **Runs quietly in the background** (windowless, below-normal priority) and can **start with Windows**.
  Closing the window keeps monitoring; the tray icon (a document with a trace) reopens it.
- **Tray menu:** open, recent changes, pause (30 min / 2 h / until resumed), notifications and
  do-not-disturb, start with Windows, quit. It turns grey while paused.
- **Log:** `desktop_watch.log` in the data folder (Settings → *Open log*).

## What it does
- **Instant detection:** Windows change notifications wake the scanner the moment a file changes, so
  changes appear about 1–2 seconds later; a full rescan every *N* seconds is the safety net. A change is
  recorded once the file stops changing, so half-written files and Office's temp-file shuffle on save
  don't create noise.
- **Languages:** English and 简体中文 (bottom of the sidebar, or Settings).
- **Changes:** a live timeline of every create / modify / rename / delete in the monitored folders (your
  Desktop by default). Bursts are grouped into one expandable card, with **Restore all** for deleted files.
  Shortcuts, Office lock files and temp files are ignored.
- **Files:** every file in the monitored folders; search by name, or by **content** (Word, Excel,
  PowerPoint, PDF, Markdown, text — Chinese included).
- **Previews** of Word, Excel, PowerPoint, PDF, Markdown, text & code, images and zip archives;
  line-, paragraph- or cell-level **diffs**; **History** of every version with **Compare** and **Restore**
  (never overwrites). Excel export of the change list.
- From 1.6.1: **notes** on versions, **statistics** (30 days), timed pause, do-not-disturb, the Explorer
  right-click entry, **ignored folders**, **diagnostics**.
- Keyboard: ↑ ↓ move, `/` or Ctrl+F search, Enter open, S star, M switch view, F5 refresh,
  Ctrl+, settings, Ctrl+W close the window, ? all shortcuts.

## Data
Kept in `%LOCALAPPDATA%\DeskTrace\data` (an older `%LOCALAPPDATA%\Desktop Watch` is moved there on first
start): `watch.db` (events, extracted text, search index), `blobs/` (content-addressed snapshots),
`settings.json`, `webview/` (the window's browser profile). Storage is kept in check automatically
(Settings → *Keep history* / *Storage limit*). Versions with a note are never cleaned up.

## Installing (Windows 10/11, 64-bit)
Run `DeskTrace-Setup-<version>.exe`: choose the language and the install folder, watch the progress, done.
No admin rights and no Python needed (it brings its own). Running a newer installer over an older one
(also over *Desktop Watch*) keeps all history and settings. Uninstalling asks whether to keep the history.

## Updates without an installer: version licenses
A version license `DeskTrace <version>.dtlicense` is one signed file that carries a newer version of the
program. **Put it into a monitored folder (e.g. the Desktop).** DeskTrace notices it, checks the
signature and offers the update — every time the window opens, until it is installed; it is never
forced. *Update now* closes the app, swaps the program files (history, settings and notes stay), and
reopens it. Settings → *Updates* can also pick a license file by hand. Licenses that are not genuine,
damaged, or not newer are ignored.

## Versions and change levels
Every change has a level: **5 New feature** (an entirely new capability), **4 Major improvement**,
**3 Improvement**, **2 Polish**, **1 Fix**. A release with a level-5 change raises the second digit and
resets the third (after x.9 the first digit goes up: 1.9.x → 2.0.0); otherwise only the third digit goes
up. `installer\changelog.json` holds every release with its levelled changes (English and 简体中文);
`installer\release.py` checks the numbers and builds the license, which carries the changelog so the app
can show what each version brings.

When licenses for several newer versions are found, the update prompt lists them all (newest first) and
you choose which one to install; each includes everything before it. A version already found is skipped.

| Version | Highlights |
|---|---|
| 1.6.1 | Notes, statistics, timed pause, do-not-disturb, Explorer menu, ignored folders, diagnostics |
| 1.6.2 | Remembers view and filters; small fixes |
| 1.7.0 | **Duplicates** — identical files, move extra copies to the Recycle Bin |
| 1.7.1 | Keep newest / recycle the rest; sorting |
| 1.8.0 | **Space** — biggest files and folders, size by type, 30-day growth; German removed |
| 1.8.1 | Space by file type; folder shares |
| 1.9.0 | **Alert rules** — notifications for changes matching your rules |
| 1.9.1 | Rule templates; preview of past matches |
| 2.0.0 | **Writing progress** — word count over versions, Writing view |
| 2.0.1 | Review release: grouped alerts, large-file duplicates, folder drill-down and old files in Space, tidier detail panel and right-click menus, daily writing goal, What's new after updates, Excel exports, many small fixes |
| 2.1.0 | **Folder time travel** — rebuild any folder as it was at any moment; speed and background release: safety rescan every 5 min instead of every second, Windows background mode, battery / presentation / low-disk savers, batched database writes, much faster Duplicates, Space, Writing, statistics and start-up; folder filter, go to a day, restore a group into a folder, forget old versions, Not duplicates / hide from Writing |
| 2.2.0 | **Clean up** — any drive: charts of what takes the space, safe one-click cleaning of temp files, caches and the Recycle Bin, and for every big file what deleting it would mean (Windows and program files are never offered). Removed: folder time travel, Writing progress, alert rules; Notes moved into the Changes toolbar |
| 2.3.0 | Review release (DeepSeek): **history backup to another drive**; Recycle Bin never silently "for good"; Clean up with tick-boxes, one summary and a result; cloud-synced folders, games, chat data, Outlook, Git and Windows.old protected; restore shows version, destination and conflict handling first; visible warnings when history may be incomplete; per-file protection status; database check; sidebar down to Changes and Clean up with tabs |
| 2.4.0 | **Background preparation of Clean up** and a **first-run guide**; drive reads ~50 s instead of 80–130 s (worker processes); kept scans open at once (quick or full); compressed versions (text ~90% smaller, old ones still readable); real disk usage incl. WinSxS hard links counted once; 10-second Undo from the Recycle Bin; chat-app data and hibernation in Clean up; Statistics removed |
| 2.4.1 | Review release (DeepSeek 2.4.0): guide restores inside itself; at most 4 scan workers with stop and fallback; backups state their format, "back up for older versions"; Clean up numbers marked as estimates; tidier restored-copy names |
| 2.4.2 | Review release (Gemini 2.4.1): unplugged drives and unreadable folders never count as deleted; Find deleted files; restores are written in one step and leave files open elsewhere untouched, long paths work; SHA-256 version names (SHA-1 ones stay readable); drafts and recovery copies are never cleaned; Put them back stays available; plainer words |

## Releasing a new version
1. Raise `APP_VERSION` in `server.py`. If stored data changes shape, raise `SCHEMA_VERSION` and add a
   step to `migrate()`.
2. Installer: `python installer\build_installer.py` → `dist\DeskTrace-Setup-<version>.exe` (needs Inno
   Setup 6). Never change the `AppId`s in `installer\DesktopWatch.iss`.
3. License: describe the changes in a file like `installer\releases\2.0.0.json` (each with a level and
   en / zh text) and run `python installer\add_release.py <that file>` → the version number is worked out
   from the levels and `dist\licenses\DeskTrace <version>.dtlicense` is built from the program as it is now.
   It is signed with `installer\keys\release-key.json` — **keep that file private and backed up**; only
   licenses signed with it are accepted. A license can only replace the program files (not the bundled
   Python); changes to the runtime need the installer.

For testing: `python server.py --data <folder> --port <n> --no-tray` runs a separate instance.
`make_icon.py` redraws the icons; `installer\make_wizard_images.py` the installer pictures.
