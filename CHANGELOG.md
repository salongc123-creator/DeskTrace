# Changelog

Every change has a level: **New** (new capability), **Major**, **Improved**, **Polish**, **Fix**. A release with a *New* change raises the second digit of the version; otherwise the third digit goes up.

每项变化都有级别：新功能、重要改进、改进、打磨、修复。含“新功能”的版本第二位数字加一，否则第三位加一。

## 2.7.0 — 2026-11-12

- **New** · Restore from a backup folder: check what a backup holds (versions read back against their checksums), then merge it into the current history or replace the current history — the previous one is always kept aside, a backup DeskTrace cannot read is refused  
  新功能 · 从备份文件夹恢复：先检查备份内容（抽查版本与校验值是否一致），再合并到当前历史或替换当前历史——原来的历史总会另外保留；桌迹读不了的备份会被拒绝
- **New** · Activity record (Settings › Trust and history): every restore, cleanup, backup, settings change and note, by you or by DeskTrace, with time and result — never the text of a note; CSV export, kept 12 months  
  新功能 · 活动记录（设置 › 可信与历史）：你或桌迹做过的每次恢复、清理、备份、设置更改和备注，含时间和结果——绝不记录备注文字；可导出 CSV，保留 12 个月
- **New** · Protection overview: how many watched files have a kept version and why the others have none (too large, online-only, not changed yet), each group one click away; the last 7 days' warnings, last cleanup and last backup  
  新功能 · 保护概览：多少受监控文件有已保存版本、其余的为什么没有（过大、仅在线、尚未改过），每类一点即看；最近 7 天的警告、上次清理和上次备份
- **New** · What will be forgotten: the history limits show in advance which changes the next 7 days will forget and how much space that gives back; noted and "Keep forever" versions are never on it, and the cleanup removes exactly what was shown  
  新功能 · 将被清除的内容：按当前规则提前列出未来 7 天会清除哪些变化、释放多少空间；带备注和“永久保留”的版本绝不在内，实际清理与预览完全一致
- **New** · Limits per folder: each watched folder can keep its history for its own number of days and have its own space cap; empty means the global setting  
  新功能 · 按文件夹设置保留规则：每个受监控文件夹可以有自己的保留天数和空间上限；留空即使用全局设置
- **New** · Replacing a file with an older version keeps its current content first, so every replace can be undone; if that is impossible (too large, disk full) you choose  
  新功能 · 用旧版本替换文件前，会先保存它当前的内容，所以每次替换都能撤回；无法保存时（文件过大、磁盘已满）由你决定
- **New** · Space map through time: see a drive's folders as they were 7, 14 or 30 days ago with what changed outlined, or coloured by growth (grew / shrank / about the same) with the numbers; full scans are now kept one per day for 90 days  
  新功能 · 空间分布图的时间回放：查看磁盘 7、14 或 30 天前的文件夹分布，变化处描边；或按增长着色（变大 / 变小 / 基本不变）并标出数字；完整扫描现在每天保留一份、保留 90 天
- **New** · Search in plain words: "deleted Excel files last week" or "上周删除的表格" becomes filters you can see and take off; if nothing matches by name, search inside documents is offered  
  新功能 · 用自然语言搜索：“上周删除的表格”或 “deleted Excel files last week” 会变成看得见、可去掉的筛选条件；名称没有匹配时，可改为搜索文档内容
- **New** · What changed in the structure of Word, Markdown, PowerPoint and Excel files: headings, slides, table rows, cells and changed numbers, above the comparison  
  新功能 · Word、Markdown、PowerPoint 和 Excel 文件的结构变化：标题、幻灯片、表格行、单元格和变化的数字，显示在对比上方
- **Major** · Export all versions of a file or folder: v1, v2, … plus a manifest.csv with time, note and checksum; size shown first, and a stopped export continues where it was  
  重要改进 · 导出文件或文件夹的全部版本：v1、v2……以及含时间、备注和校验值的 manifest.csv；先显示大小，中断后可从原处继续
- **Major** · Weekly report: the week's versions, restores, freed space and unusual events, as a Markdown file and (if you like) one quiet Monday notification; made on this PC only  
  重要改进 · 保护周报：一周保存的版本、恢复、释放的空间和异常事件，可存为 Markdown，也可以（如果你愿意）每周一一条安静的通知；只在本机生成
- **Major** · Mass-change alert you can tune: how many changes in how many seconds, and how long "that was normal" keeps it quiet (10 min, 1 hour, 24 hours)  
  重要改进 · 可调整的大量变更预警：多少秒内多少处变化，以及“这是正常的”之后保持安静多久（10 分钟、1 小时、24 小时）
- **Major** · Scheduled cleanup of caches and temporary files — off unless you set it up, only the items you tick, never your own files, every run in the activity record  
  重要改进 · 定时清理缓存和临时文件——除非你设置否则不开启，只清理你勾选的项目，绝不碰你自己的文件，每次运行都写入活动记录
- **Major** · Changes: Ctrl/Shift+click several changes to note, save or restore them together; sort by size of change or how often a file changed; only big changes; deleted files still in the Recycle Bin or that only DeskTrace has; saved views  
  重要改进 · 变化列表：按住 Ctrl/Shift 点选多项，一起备注、另存或恢复；按变动幅度或修改频次排序；只看大改动；仍在回收站中 / 只有桌迹有副本的已删除文件；保存的视图
- **Major** · In a folder: what happened between two dates — new, changed, deleted, renamed and net size — each number opens the list  
  重要改进 · 文件夹时间切片：两个日期之间新增、修改、删除、重命名的数量和净增大小，点击数字即可查看列表
- **Major** · Clean up: Downloads by age (older than 6 months, 3–6, 1–3; never ticked for you), kinds of big files, "free me X GB" that only ticks safe items, a copyable check-up, time left while a drive is read, and a much faster start (it no longer reads every place again after each deletion)  
  重要改进 · 空间清理：按时间分批的下载内容（半年以上、3–6 个月、1–3 个月；不会替你勾选）、大文件类型筛选、只勾安全项的“帮我腾出 X GB”、可复制的体检简报、扫描剩余时间，打开也快得多（每删一个文件不再重新读一遍所有位置）
- **Major** · Notes get a colour label (Final, Draft, Important, Sent to client); notifications are three switches: deleted or overwritten files, low disk space, ordinary changes; a deletion's notification opens its Restore  
  重要改进 · 备注可加颜色标签（定稿、草稿、重要、已发客户）；通知改为三个开关：删除或覆盖文件、磁盘空间不足、普通修改；删除通知点开即是恢复
- **Improved** · Previews: Space for a quick look, line numbers with copy-a-line, PDF page jump, long unchanged parts folded, step from change to change, the differences shown inside the replace dialog, .patch export, the real checksum (SHA-1 / SHA-256) of each version  
  改进 · 预览：按空格快速查看、带行号可复制单行、PDF 跳页、长段未改动内容折叠、在改动之间跳转、替换对话框里直接看差异、导出 .patch、每个版本的真实校验值（SHA-1 / SHA-256）
- **Improved** · Preferences: name of restored copies, time format, text size (also Ctrl + wheel), window on top and compact width, double-click action, side-by-side direction, the global shortcut (or off), sound when done, recent searches, a copied path offered (off by default), Desktop shortcut  
  改进 · 偏好设置：恢复副本的命名、时间格式、文字大小（也可 Ctrl+滚轮）、窗口置顶和紧凑宽度、双击行为、并排对比方向、全局快捷键（可关闭）、完成提示音、最近搜索、识别复制的路径（默认关闭）、桌面快捷方式
- **Improved** · Support bundle: the last 300 log lines, the check-up and the settings with your user name taken out, shown before it is saved  
  改进 · 诊断包：最近 300 行日志、自检结果和设置（已去掉你的用户名），保存前先给你看
- **Polish** · Clearer promises: only versions up to the snapshot limit are kept, and each change says when there is no copy of it; "Keep forever" says it is not protection against ransomware  
  打磨 · 说法更准确：只有不超过快照上限的版本才会保存，没有副本的变化会注明；“永久保留”明确说明它不能防勒索软件
- **Polish** · Quieter in the background: started with Windows it opens nothing; scans and indexing run in Windows' efficiency mode; Explorer's menu changes at once; a removed USB drive no longer leaves an error page  
  打磨 · 后台更安静：随 Windows 启动时不打开任何窗口；扫描和索引在 Windows 能效模式下运行；资源管理器右键菜单即时生效；拔出 U 盘不再留下错误页面
- **Fix** · Faster to open and lighter: translations merged at build time, rarely used parts loaded only when needed, one look at the disk per file in long lists  
  修复 · 打开更快、更轻：翻译在构建时合并，少用的部分用到时才加载，长列表中每个文件只查一次磁盘

## 2.6.0 — 2026-11-07

- **New** · What grew recently: Clean up compares full scans of a drive and shows the folders that grew most in the last 24 hours or 7 days, naming the deepest folder responsible  
  新功能 · 最近哪里变大了：空间清理比较磁盘的两次完整扫描，列出过去 24 小时或 7 天增长最多的文件夹，并指出真正导致增长的最深一层
- **New** · Mass-change guard: when 100 or more files are changed, deleted or renamed within seconds (a script gone wrong, a sync conflict, ransomware), a red banner appears and one click puts every file back as it was before  
  新功能 · 大量变化防护：几秒内有 100 个以上文件被修改、删除或重命名（出错的脚本、同步冲突、勒索病毒）时显示红色横幅，一键把每个文件恢复到之前的样子
- **New** · Move a big folder to another drive: copied, every file checked, a link left in its place so programs find it as before, and it can be moved back  
  新功能 · 大文件夹搬家：复制到其他磁盘并逐个文件核对，在原位置留下链接，程序照常能找到；随时可以搬回来
- **New** · Move to a new PC: export the whole history as one file and import it on another PC; the history that was there is kept aside  
  新功能 · 换电脑：把整个历史记录导出为一个文件，在另一台电脑上导入；那台电脑原有的历史记录会另存一份
- **New** · A folder as it was at any time: written as a copy next to it, with every file in the version it had then  
  新功能 · 文件夹在任意时刻的样子：在旁边写出一份副本，每个文件都是当时的版本
- **New** · Similar photos: burst shots, edits and resized copies grouped together, the sharpest one marked  
  新功能 · 相似照片：把连拍、修图和缩放后的副本归为一组，标出最清晰的一张
- **Major** · Keep forever: a file whose every version is kept whatever the history limits say, and that Clean up never deletes  
  重要改进 · 永久保留：文件的每个版本都会保留，不受历史记录期限影响，空间清理也绝不删除它
- **Major** · Undo a batch rename, find unsaved Office and WPS drafts after a crash, and name the program that has a file open when it cannot be restored or deleted  
  重要改进 · 一键撤销批量重命名；程序崩溃后找回 Office 和 WPS 未保存的草稿；文件因被占用无法恢复或删除时，指出是哪个程序在使用它
- **Major** · New in Clean up: dependencies of old projects, other browsers' and graphics shader caches, older installer versions, broken shortcuts and empty folders, compression of large old files (nothing deleted), large Git repositories, chat apps' old received media (never their chat history), cloud folders on this PC vs online only, and possible leftovers of uninstalled programs  
  重要改进 · 空间清理新增：旧项目的依赖、其他浏览器和显卡着色器缓存、安装包旧版本、失效快捷方式和空文件夹、压缩体积大的旧文件（不删除任何文件）、体积很大的 Git 仓库、聊天软件收到的旧媒体（绝不动聊天记录）、云同步文件夹在本机与仅联机的分布，以及可能是已卸载软件的残留
- **Major** · Duplicates can be kept in every place but stored once (hard links)  
  重要改进 · 重复文件可以全部保留在原处，但在磁盘上只占一份空间（硬链接）
- **Improved** · History: a time slider over every version, an evolution view with the copies made from a file, a comparison report to save as a web page, and badges saying whether a deleted file can be fully restored  
  改进 · 历史记录：可在所有版本间拖动的时间轴、显示由文件复制出的副本的演变图、可保存为网页的对比报告，以及标明被删除文件能否完整找回的标记
- **Improved** · Explorer: right-click a folder for the files deleted there; Ctrl+Alt+Z anywhere shows today's deleted and overwritten files  
  改进 · 资源管理器：右键文件夹即可找回在那里删除的文件；在任何地方按 Ctrl+Alt+Z 显示今天删除和被覆盖的文件
- **Improved** · Windows tools in Clean up (Disk Cleanup, Optimize drives, search index), each disk's health, a smaller hibernation file option, and Windows upgrade leftovers  
  改进 · 空间清理中的 Windows 工具（磁盘清理、优化驱动器、搜索索引）、各磁盘的健康状态、缩小休眠文件，以及 Windows 升级残留
- **Improved** · Names Windows cannot handle (ending in a space or dot, paths over 260 characters) are listed and can be fixed  
  改进 · 列出 Windows 无法处理的文件名（以空格或句点结尾、路径超过 260 个字符），并可一键修正
- **Polish** · Kept versions are checked in idle time; the tray turns green during busy moments and red on a mass change; a removable drive gets a card when plugged in; quieter on low battery and during presentations; Mica title bar on Windows 11; optional milestone cards  
  打磨 · 空闲时校验保存的版本；托盘图标在大量写入时变绿、出现大量变化时变红；插入移动硬盘时显示提示；低电量和演示时更安静；Windows 11 标题栏使用 Mica 效果；可关闭的里程碑提示
- **Polish** · Updating across several versions, the notes show only what you really get: features added and removed again in between are left out, and a removal is only mentioned if you had that feature  
  打磨 · 跨越多个版本更新时，更新说明只显示你实际得到的内容：中间加入又被移除的功能不再列出；只有你用过的功能被移除时才会提到
- **Fix** · Renames are no longer paired with the wrong file when many files share the same size and time  
  修复 · 大量文件大小和时间相同时，不再把重命名配错文件
- **Fix** · Gemini review: a folder is never moved while any program has one of its files open (also programs that allow sharing), "That was me" silences the mass-change alert for 10 minutes, possible leftovers are worded more carefully and skip well-known vendors, and the extra Clean up lists sit in one folding section  
  修复 · Gemini 评审：只要有程序打开着文件夹中的任何文件（包括允许共享的程序），就不会搬家；“是我自己做的”会让大量变化提示静默 10 分钟；可能的残留文件夹用更谨慎的说法，并跳过知名厂商；空间清理的扩展列表收进一个可折叠的区域

## 2.5.0 — 2026-11-07

- **New** · Clean up can delete any file it lists: for each one it says plainly what the file is, what deleting it does and what is better, and files that are risky to delete need a tick on "I understand what happens" first. Core Windows files (the Windows folder, page and hibernation files, System Volume Information, $ folders) are no longer listed at all  
  新功能 · 空间清理现在可以删除列出的任何文件：每个文件都会用大白话说明它是什么、删除后会怎样、有什么更好的做法；删除有风险的文件前需要先勾选“我了解删除后的结果”。Windows 核心文件（Windows 文件夹、页面文件和休眠文件、System Volume Information、以 $ 开头的文件夹）不再列出
- **New** · Space map: every folder is a block sized by its space, split into its biggest subfolders; click a block to jump to it in the list below (a deeper block opens its folder first)  
  新功能 · 空间分布图：每个文件夹是一个方块，面积代表占用空间，并细分为它最大的子文件夹；点击方块即可跳到下方列表中的对应项（更深一层的方块会先打开所在文件夹）
- **Major** · Reading a drive is about twice as fast: folders are handed to whichever worker is free, and a big folder is split among all of them instead of keeping one worker busy alone (on the test PC 71.5 s → 35.5 s for 1.86 million files)  
  重要改进 · 读取磁盘速度约提高一倍：文件夹交给空闲的工作进程处理，大文件夹会分给所有工作进程，不再由一个进程独自读完（测试电脑上 186 万个文件从 71.5 秒降到 35.5 秒）
- **Improved** · Against deleting the wrong thing (Gemini review): every deletion shows what it means first; recovery copies and unsaved drafts, databases anywhere (with their -wal / -shm journals) and files changed in the last 24 hours need the tick; Windows' machine keys, activation, credential vault and Defender data, bootsect.bak, boottel.dat and MSOCache are core and not listed; program files offer Windows' uninstall; tiny space-map slivers are merged and blocks say what a click does  
  改进 · 防止误删（Gemini 评审）：每次删除前都先说明后果；恢复副本和未保存的草稿、任何位置的数据库（含 -wal / -shm 日志）以及 24 小时内修改过的文件需要勾选确认；Windows 的机器密钥、激活凭据、凭据保险库和 Defender 数据，以及 bootsect.bak、boottel.dat、MSOCache 视为核心文件，不再列出；程序文件提供“打开 Windows 卸载”；空间分布图合并过小的碎片方块，并提示点击后的行为
- **Improved** · Finer kinds of file against deleting the wrong thing: browser profiles (passwords, bookmarks) apart from browser caches, WSL and Docker virtual disks, iPhone backups, game saves, app databases, logs, crash dumps and package caches each get their own explanation  
  改进 · 更细的文件分类，避免误删：浏览器配置文件（密码、书签）与浏览器缓存分开，WSL 和 Docker 虚拟磁盘、iPhone 备份、游戏存档、软件数据库、日志、崩溃转储和软件包缓存都有各自的说明
- **Polish** · Plain labels instead of "Uninstall instead": Program file, Synced to the cloud, App data, App settings or cache, Your file, Can be deleted  
  打磨 · 标签改为直白的说法，不再显示“请改为卸载”：程序文件、云同步文件、应用数据、软件设置或缓存、你的文件、可以删除

## 2.4.2 — 2026-11-07

- **Major** · A monitored folder on a drive that is unplugged, a network that is away or a folder that cannot be read is no longer taken for "everything deleted": its files keep their history, a banner names the folder, monitoring carries on when it is back, and "It was deleted…" lists its files as deleted only when you say so  
  重要改进 · 监控的文件夹所在的移动硬盘被拔出、网络断开或文件夹暂时无法读取时，不再被当作“全部删除”：文件的历史保留，横幅会指出是哪个文件夹，它回来后自动继续监控；只有你点“它已被删除…”确认后，里面的文件才会列为已删除
- **Major** · Find deleted files: one button lists every file that was deleted and is still missing, newest first, each with Restore  
  重要改进 · 找回已删除的文件：一个按钮列出所有被删除、至今仍不在原处的文件，最近删除的在前，每个都带“恢复”按钮
- **Major** · Restoring writes the whole version to a temporary file first and then puts it in place in one step; a file open in another program (for example Word) is left untouched with a clear message, and paths over 260 characters work  
  重要改进 · 恢复时先把整个版本写入临时文件，再一步放到位；目标文件被其他程序（例如 Word）打开时保持原样并给出明确提示；超过 260 个字符的路径也能恢复
- **Improved** · New versions are named by SHA-256; versions kept before stay readable under their SHA-1 names, an unchanged file reuses its old copy, and Duplicates and move detection compare old and new names  
  改进 · 新的版本副本以 SHA-256 命名；之前保存的版本仍按 SHA-1 名称读取，未变化的文件沿用旧副本，重复文件和移动检测能对比新旧两种名称
- **Improved** · Temporary-file cleanup leaves alone files changed in the last two days (was one hour) and never removes recovery copies or unsaved drafts of Office, WPS and other editors, however old  
  改进 · 临时文件清理不再动两天内修改过的文件（原为一小时），并且无论多旧都不删除 Office、WPS 等编辑软件的恢复副本和未保存的草稿
- **Improved** · After a cleanup, "Put them back" stays available in Clean up as long as the Recycle Bin is not emptied, instead of a 10-second offer  
  改进 · 清理后，“放回原处”会一直留在“空间清理”中（只要回收站没有清空），不再是 10 秒内的临时按钮
- **Polish** · Plainer words: the history view is called "History & restore", protection labels say "No copy yet" and what that means, the "no earlier version" note is in everyday language, caches are labelled "Deleted directly · programs do not need them" instead of a red warning, and chart titles no longer say "estimated"  
  打磨 · 用词更直白：历史视图改名为“历史与找回”；保护状态写“暂无副本”并说明含义；“没有更早的版本”的说明改为日常用语；缓存标为“直接删除 · 程序已不再需要”，不再用红色警告；图表标题不再写“估算”
- **Polish** · After the PC wakes up, the catch-up rescan and background preparation wait a little, so DeskTrace never competes with you right after opening the lid  
  打磨 · 电脑从睡眠中唤醒后，补充扫描和后台准备会稍等片刻再进行，刚打开笔记本时桌迹不会和你抢资源
- **Polish** · First-run guide: the restored test file shows a short highlight  
  打磨 · 入门向导：找回测试文件后有短暂的高亮提示
- **Fix** · Showing the current content of an online-only cloud file no longer downloads it  
  修复 · 查看“仅联机”云文件的当前内容时不再触发下载
- **Fix** · Changing settings while a drive is unplugged no longer drops its folder from the monitored list  
  修复 · 移动硬盘拔出时修改设置，不再把它的文件夹从监控列表中删掉

## 2.4.1 — 2026-11-07

- **Major** · First-run guide: the test file is restored right inside the guide with its own Restore button — no pop-up or notification is needed, so the guide cannot get stuck  
  重要改进 · 入门向导：测试文件直接在向导里用它自己的“恢复”按钮找回——不需要任何弹出提示或系统通知，向导不会卡住
- **Improved** · Reading a drive while you wait uses at most 4 worker processes (about 100 MB together, gone when done); stopping ends them at once, and if they cannot start the drive is read in DeskTrace itself with the same result  
  改进 · 你等待时读取磁盘最多使用 4 个工作进程（合计约 100 MB，完成后即释放）；停止时立即结束它们；如果无法启动，则由桌迹自己读取，结果相同
- **Improved** · Backups say which DeskTrace can read them (FORMAT.txt), "Back up for older versions" writes every version uncompressed for DeskTrace 2.3.0 and older, and Diagnostics shows the version format  
  改进 · 备份会注明哪些版本的桌迹能读取（FORMAT.txt）；“为旧版本备份”会把每个版本不压缩地写出，供桌迹 2.3.0 及更早版本使用；诊断信息会显示版本格式
- **Improved** · Clean up is clearer about its numbers: folder and type totals are marked as estimates, the possible over-count from tiny files is shown, files without an extension are labelled as such, a scan older than a day says it may be out of date, and the WinSxS correction is shown while it runs  
  改进 · 空间清理的数字说明更清楚：文件夹和类型的合计标为估算，显示极小文件可能造成的高估，无扩展名的文件单独标注，超过一天的扫描会提示可能已过期，修正 WinSxS 时会显示进度
- **Polish** · Restored copies are named like "report (restored 2026-11-07 01-19-05).docx"  
  打磨 · 恢复的副本命名为“报告 (恢复于 2026-11-07 01-19-05).docx”这样的格式
- **Polish** · The background preparation of Clean up no longer keeps its own timer; it is checked when DeskTrace wakes up anyway  
  打磨 · “空间清理”的后台预先准备不再使用单独的定时器，而是在桌迹本来就会唤醒时顺便检查
- **Fix** · Game files no longer offer "Uninstall a program…"; games are uninstalled in their launcher  
  修复 · 游戏文件不再提供“卸载程序…”；游戏请在其平台中卸载
- **Fix** · First-run guide: the delete step shows "Deleted" when it is done instead of staying on "Deleting…"  
  修复 · 入门向导：删除步骤完成后显示“已删除”，不再一直显示“正在删除…”

## 2.4.0 — 2026-11-07

- **New** · New: background preparation of Clean up — while the PC is idle, plugged in and not running a full-screen game or presentation, DeskTrace reads your drives at the lowest priority (at most every 12 hours), so Clean up opens on fresh results; can be switched off in Settings  
  新功能 · 新功能：在后台预先准备“空间清理”——电脑空闲、接通电源且没有运行全屏游戏或演示时，桌迹以最低优先级读取你的磁盘（最多每 12 小时一次），打开“空间清理”时结果已经是新的；可在设置中关闭
- **New** · New: first-run guide — three short, skippable steps: what to watch (and how DeskTrace differs from File History, "Previous versions" and OneDrive), protection starting, and one real undo with a test file DeskTrace makes and deletes itself  
  新功能 · 新功能：入门向导——三个可跳过的简短步骤：选择监控的文件夹（并说明桌迹与文件历史记录、“以前的版本”、OneDrive 的区别）、开始保护，以及用桌迹自己创建并删除的测试文件实际恢复一次
- **Major** · Reading a drive is much faster: a full read of a 1.9-million-file system drive takes about 50 seconds instead of 80–130, using several processes while you wait (spinning disks and background reads stay gentle, one folder at a time)  
  重要改进 · 读取磁盘快了很多：完整读取一个有 190 万个文件的系统盘约需 50 秒，而不是 80–130 秒——你等待时使用多个进程并行读取（机械硬盘和后台读取仍然一次一个文件夹，保持温和）
- **Major** · Clean up opens at once on the last scan, which is kept on disk (checked against the disk's serial number, so a different disk is read again); quick scan (your folders only) or full scan; spinning disks start with a quick scan  
  重要改进 · “空间清理”会立即显示保存在磁盘上的上次扫描结果（会核对磁盘序列号，换了磁盘会重新读取）；可选择快速扫描（只读取你的文件夹）或完整扫描；机械硬盘默认快速扫描
- **Major** · Kept versions are compressed: text, documents in plain formats and code take about 90% less room; Office files, PDFs, pictures and archives are left as they are; versions kept by older versions stay readable and are compressed gradually during upkeep  
  重要改进 · 保存的版本会被压缩：文本、纯文本格式文档和代码占用的空间减少约 90%；Office 文件、PDF、图片和压缩包保持原样；旧版本保存的版本依然可读，并会在定期维护时逐步压缩
- **Major** · Clean up shows what files really take on the disk: whole clusters, less when compressed, much less when sparse; files Windows keeps hard-linked in WinSxS are counted once (9.4 GB less on the test PC), and the size is shown next to it  
  重要改进 · “空间清理”显示文件在磁盘上的实际占用：按簇对齐，压缩文件更小，稀疏文件小得多；WinSxS 中 Windows 硬链接的文件只计一次（测试电脑上少算了 9.4 GB），并同时显示文件大小
- **Improved** · Undo for 10 seconds after anything was moved to the Recycle Bin — one file or a whole cleaning run; an occupied original place is never overwritten  
  改进 · 移到回收站后 10 秒内可以撤销——无论是单个文件还是一次清理；原位置已被占用时绝不覆盖
- **Improved** · Chat apps: WeChat, QQ, WeCom, DingTalk and Telegram data is shown with its size and how to clean it inside the app, with buttons to open the app or its data folder; DeskTrace never deletes chat data  
  改进 · 聊天应用：显示微信、QQ、企业微信、钉钉和 Telegram 数据的大小以及在应用内清理的方法，并提供打开应用或数据文件夹的按钮；桌迹绝不删除聊天数据
- **Improved** · Hibernation: Clean up shows what hiberfil.sys takes and can switch hibernation off (or on again) — Windows asks for permission itself; DeskTrace never runs as administrator  
  改进 · 休眠：“空间清理”显示 hiberfil.sys 的占用，并可关闭（或重新打开）休眠——由 Windows 自己请求许可；桌迹从不以管理员身份运行
- **Improved** · Simpler: Statistics was removed (its tab, the tray entry and the I shortcut)  
  改进 · 更简洁：删除了“统计”（其标签页、托盘菜单项和 I 快捷键）
- **Polish** · Clean up: the scan line says when the shown results were made, and whether they are a quick or a full scan  
  打磨 · 空间清理：扫描行会注明当前结果的扫描时间，以及是快速扫描还是完整扫描

## 2.3.0 — 2026-11-07

- **New** · New: back up the whole history (every kept version, notes and settings) to another drive, e.g. a USB disk, from Settings; later backups only add what is new. Settings now says plainly that the history on the same disk is not a backup  
  新功能 · 新功能：在设置中把全部历史记录（所有保存的版本、备注和设置）备份到其他磁盘，例如 U 盘；之后的备份只添加新增内容。设置中明确说明：与文件在同一块磁盘上的历史记录不是备份
- **Major** · The Recycle Bin is never a silent "for good": a file it cannot take (no Recycle Bin on that drive, switched off, or bigger than the bin) is not deleted; you are asked and must tick "I understand" before it is deleted for good. This also protects Duplicates  
  重要改进 · 回收站绝不会悄悄变成“永久删除”：回收站放不下的文件（该磁盘没有回收站、已关闭或文件超过回收站容量）不会被删除；会先询问你，并需要勾选“我明白”后才会永久删除。“重复文件”同样受此保护
- **Major** · Clean up: tick what may go — only risk-free items are ticked by default, never your files or the Recycle Bin; one summary lists every item, its size and whether it can be undone before anything happens, and a result shows what was freed and what was skipped  
  重要改进 · 空间清理：勾选要清理的项目——默认只勾选无风险的项目，绝不默认勾选你的文件或回收站；执行前用一个汇总列出每一项、大小以及能否撤销，完成后显示释放了多少、跳过了什么
- **Major** · Files in cloud-synced folders (OneDrive, Dropbox, iCloud, WPS and others registered with Windows) are never offered for deletion — deleting there deletes in the cloud too; "Free up space" keeps them online only instead. Online-only files are not counted as using space and are never downloaded by DeskTrace  
  重要改进 · 云同步文件夹（OneDrive、Dropbox、iCloud、WPS 以及其他在 Windows 中注册的云盘）中的文件绝不会被列为可删除——在那里删除会连云端一起删除；改为提供“释放空间（仅保留在线）”。仅在线的文件不计入占用空间，桌迹也绝不会下载它们
- **Major** · Restoring shows which version (time and note), the exact place it goes to and what happens to an existing file before anything happens; "restore as a new file" is the default and "replace" is offered only when it can be undone  
  重要改进 · 恢复前会显示：哪个版本（时间和备注）、恢复到的确切位置、现有文件会怎样；默认“恢复为新文件”，只有在可以撤销时才提供“替换”
- **Major** · When the history may be incomplete — less than 1 GB free, Windows dropping change details, instant detection off, or a database problem — a banner, the tray and Diagnostics say so  
  重要改进 · 当历史记录可能不完整时——可用空间不足 1 GB、Windows 丢失变更细节、即时检测关闭或数据库出现问题——横幅、托盘和诊断信息都会提示
- **Improved** · Every file shows how it is protected: versions kept, too big for versions, online only, or no copy yet  
  改进 · 每个文件都会显示它的保护状态：已保存版本、太大不保存版本、仅在线或尚无副本
- **Improved** · Clean up knows more dangerous places: game libraries (uninstall in the launcher), WeChat/QQ and other chat data (clean up in the app), Outlook mail files, Git repositories and Windows.old are never offered for deletion as ordinary files  
  改进 · 空间清理识别更多危险位置：游戏库（请在平台中卸载）、微信/QQ 等聊天数据（请在应用内清理）、Outlook 邮件文件、Git 仓库和 Windows.old 都不会被当作普通文件提供删除
- **Improved** · Clean up: each big file says whether DeskTrace keeps a copy — and so whether it can still be restored after the Recycle Bin is emptied  
  改进 · 空间清理：每个大文件都会说明桌迹是否保存了副本——也就是清空回收站后能否恢复
- **Improved** · Simpler navigation: the sidebar has two entries — Changes (with All files and Statistics) and Clean up (with Drive, Duplicates and Watched folders) — shown as tabs  
  改进 · 导航更简洁：侧边栏只有两项——“变更”（含所有文件和统计）与“空间清理”（含磁盘、重复文件和监控的文件夹），以标签页切换
- **Improved** · Emptying the Recycle Bin is separate from cleaning and asks first, saying how many files you would lose  
  改进 · 清空回收站与其他清理分开，并会先确认，说明将会失去多少个文件
- **Improved** · The history database is checked at start and during upkeep; a problem is shown instead of silently used  
  改进 · 启动时和定期维护时都会检查历史数据库；出现问题会显示出来，而不是继续默默使用
- **Polish** · Clean up: consequence texts are more precise (sign-in may be needed on some sites, offline builds may fail, skipped files are listed), and "can be freed" is split into right away and after emptying the Recycle Bin  
  打磨 · 空间清理：后果说明更准确（少数网站可能需要重新登录、离线构建可能失败、跳过的文件会列出），“可释放”分为“立即释放”和“清空回收站后释放”
- **Polish** · Clean up: reading a drive can be stopped, and folders that could not be read and online-only files are counted and explained  
  打磨 · 空间清理：读取磁盘时可以停止，无法读取的文件夹和仅在线文件会被统计并说明
- **Polish** · Windows.old and system memory dumps are shown with their size and handed to Windows Disk Cleanup  
  打磨 · Windows.old 和系统内存转储会显示大小，并交给 Windows 磁盘清理处理
- **Fix** · After sleep or hibernation DeskTrace looks at all files once, so nothing changed meanwhile is missed  
  修复 · 睡眠或休眠唤醒后，桌迹会重新检查全部文件一次，不会漏掉这期间的变更

## 2.2.0 — 2026-11-06

- **New** · New: Clean up — pick any drive and see what takes up its space: a ring chart of used, cleanable and free space, the biggest folders as a bar chart you can click into, the size by file type and the biggest files  
  新功能 · 新功能：空间清理——选择任意磁盘，查看空间都用在了哪里：已用 / 可清理 / 可用空间的环形图、可点击进入的最大文件夹条形图、按文件类型的大小以及最大的文件
- **Major** · Clean up says what deleting means before you click: each place to clean and each big file explains the consequence, and whether it is deleted for good or goes to the Recycle Bin; Windows and installed programs are never offered for deletion  
  重要改进 · 空间清理在点击之前就说明删除的后果：每个可清理项目和每个大文件都会说明后果，以及是永久删除还是移到回收站；Windows 和已安装程序的文件绝不会被列为可删除
- **Improved** · One-click cleaning of temporary files, browser caches (Edge, Chrome, Firefox), crash reports, picture thumbnails, developer caches (pip, npm, Yarn), old installers in Downloads and the Recycle Bin; files in use or changed within the hour are skipped, links are never followed  
  改进 · 一键清理临时文件、浏览器缓存（Edge、Chrome、Firefox）、崩溃报告、图片缩略图、开发工具缓存（pip、npm、Yarn）、下载文件夹中的旧安装程序和回收站；正在使用或一小时内修改过的文件会被跳过，绝不跟随链接
- **Improved** · Clean up: Windows Update leftovers, which need administrator rights, open Windows Disk Cleanup; program files offer "Uninstall a program…" instead of deleting  
  改进 · 空间清理：需要管理员权限的 Windows 更新残留会打开 Windows 磁盘清理；程序文件提供“卸载程序…”而不是直接删除
- **Improved** · Simpler: Folder time travel, Writing progress and Alert rules were removed; your notifications for changes and deletions stay as they were  
  改进 · 更简洁：删除了文件夹时光回溯、写作进度和提醒规则；变更与删除通知保持不变
- **Improved** · Notes are part of Changes now: a "Only versions with a note" button with the count sits next to ★ in the toolbar, instead of a separate sidebar entry  
  改进 · 备注并入“文件变更”：工具栏 ★ 旁新增带数量的“只看带备注的版本”按钮，不再单独占用侧边栏
- **Improved** · Space shows a ring chart of the size by file type  
  改进 · “空间占用”以环形图显示各文件类型的大小
- **Polish** · Reading a whole drive runs in Windows background mode and keeps at most about 13 MB in memory (1.9 million files); the result is let go after 10 minutes without use  
  打磨 · 读取整个磁盘时以 Windows 后台模式运行，内存最多约 13 MB（190 万个文件）；闲置 10 分钟后会释放结果
- **Polish** · Statistics: the changes-per-day chart shows every day (quiet days next to a busy one stay visible), its scale and its dates  
  打磨 · 统计：每日变更图显示每一天（繁忙日旁的少量变更也清晰可见），并显示刻度和日期
- **Fix** · Statistics: clicking a day in the chart now opens that day's changes  
  修复 · 统计：点击图表中的某一天现在会打开当天的变更

## 2.1.0 — 2026-11-06

- **New** · New: Folder time travel — see any monitored folder as it was at any moment (files edited, deleted or renamed since included) and rebuild it as a new folder next to it; nothing is overwritten  
  新功能 · 新功能：文件夹时光回溯——查看任意监控文件夹在任意时刻的样子（包括之后被修改、删除或重命名的文件），并把它重建为旁边的新文件夹；不会覆盖任何文件
- **Major** · Time travel shows a preview first: every file it would rebuild, where it comes from, and which ones cannot be rebuilt because that version was not kept  
  重要改进 · 时光回溯会先显示预览：将重建的每个文件、它的来源，以及哪些文件因当时的版本没有保留而无法重建
- **Major** · Forget old versions of one file to free space: its newest version and any version with a note are kept  
  重要改进 · 可忘记某个文件的旧版本以释放空间：最新版本和带备注的版本会保留
- **Major** · Much less background work: while Windows reports changes instantly, the safety rescan of all files runs at most every 5 minutes instead of as often as every second  
  重要改进 · 后台负担大幅降低：在 Windows 即时报告变更时，全部文件的保底重扫最多每 5 分钟一次，而不是每秒一次
- **Improved** · "This folder as it was before this change" in the More and right-click menus jumps straight to the moment before a change  
  改进 · “更多”和右键菜单中的“此文件夹在这次变更之前的样子”可直接回到某次变更之前的时刻
- **Improved** · Settings: What uses the space shows which files' kept versions take the most of DeskTrace's storage  
  改进 · 设置：“查看空间用途”显示哪些文件保留的版本占用了桌迹最多的存储空间
- **Improved** · Scanning, indexing and hashing run in Windows background mode (lowest CPU, disk and memory priority), so they never slow down your other programs; the window stays quick  
  改进 · 扫描、索引和计算哈希改为在 Windows 后台模式下运行（最低的 CPU、磁盘和内存优先级），不会拖慢其他程序；窗口仍保持流畅
- **Improved** · Duplicates, Space and Writing are only worked out again after something changed, so switching to them is instant  
  改进 · 重复文件、空间占用和写作进度只在有变化后才重新计算，切换到这些视图时即时显示
- **Improved** · Comparing large files for Duplicates is gentle on the disk: lowest disk priority with short pauses  
  改进 · 为“重复文件”比较大文件时对磁盘更友好：使用最低磁盘优先级并适当停顿
- **Improved** · A hidden or minimized window does no work at all; it catches up when you come back  
  改进 · 隐藏或最小化的窗口完全不做任何工作；回来时会自动补上更新
- **Improved** · Battery saver: on a laptop running on battery, first-time indexing and comparing large files wait until it is plugged in, and the safety rescan runs only every 15 minutes; change detection goes on as normal  
  改进 · 省电模式：笔记本电脑使用电池时，首次建立索引和比较大文件会等到接通电源后再进行，保底重扫每 15 分钟才运行一次；变更检测照常进行
- **Improved** · Presentation saver: first-time indexing and comparing large files also wait while a full-screen game, video or presentation is on  
  改进 · 演示模式省电：运行全屏游戏、视频或演示时，首次建立索引和比较大文件也会暂缓
- **Improved** · Diagnostics show DeskTrace's own background use (CPU time, memory, data read and written), when the next safety rescan runs and whether a power saver is active  
  改进 · 诊断信息显示桌迹自身的后台占用（CPU 时间、内存、读写数据量）、下次保底重扫的时间以及省电模式是否生效
- **Improved** · Duplicates: "Not duplicates" hides a set you keep on purpose (with Undo); hidden sets can be shown again at the bottom of the list  
  改进 · 重复文件：“不是重复”可隐藏有意保留的一组副本（可撤销）；可在列表底部重新显示隐藏的组
- **Improved** · Writing: hide a document from Writing (right-click or its Progress tab), and show hidden documents again  
  改进 · 写作进度：可将文档从“写作进度”中隐藏（右键或其“进度”标签页），也可重新显示已隐藏的文档
- **Improved** · Recording many changes at once (a folder copied in, unzipped or deleted) writes up to 90% less to disk and uses about a third less CPU  
  改进 · 一次记录大量变更（复制进来、解压或删除整个文件夹）时，磁盘写入最多减少 90%，CPU 占用减少约三分之一
- **Improved** · Duplicates are worked out about 15 times faster (0.05 instead of 0.85 seconds for 12,000 files)  
  改进 · 重复文件的计算速度提高约 15 倍（12,000 个文件只需 0.05 秒，原来需要 0.85 秒）
- **Improved** · Space is worked out twice as fast  
  改进 · 空间占用的计算速度提高一倍
- **Improved** · Finding out how much room DeskTrace's own history takes is about 15 times faster; it runs every 30 seconds while the window is open  
  改进 · 统计桌迹自身历史记录占用的空间快了约 15 倍；窗口打开时它每 30 秒运行一次
- **Improved** · DeskTrace starts about a second faster: it no longer waits for Windows to confirm that no earlier copy is running  
  改进 · 桌迹的启动速度快了约一秒：不再等待 Windows 确认没有已在运行的副本
- **Improved** · The window stays smooth while many files change at once: the list is redrawn a few times instead of once per file (about 50 times less work when 1,000 files are copied in)  
  改进 · 大量文件同时变化时窗口依然流畅：列表只重绘几次，而不是每个文件重绘一次（复制进 1,000 个文件时工作量减少约 50 倍）
- **Improved** · With a long history (e.g. 150,000 recorded changes) the Files list and the statistics update about 10 times faster after each change: only the new changes are counted  
  改进 · 历史记录很长时（例如 15 万条变更），每次变更后“所有文件”列表和统计信息的更新速度提高约 10 倍：只统计新增的变更
- **Improved** · Writing opens about 10 times faster with a long history: each document's word counts are reused until it changes, and this week's documents are looked up by date  
  改进 · 历史记录很长时，“写作进度”的打开速度提高约 10 倍：每个文档的字数在其变化前会被重复使用，本周的文档按日期查找
- **Improved** · Changes in one folder: click a change's folder (or right-click › Changes in this folder) to see only that folder and its subfolders; Statistics' busiest folders now open exactly that folder  
  改进 · 查看单个文件夹的变更：点击某条变更的文件夹（或右键 ›“此文件夹中的变更”）即可只看该文件夹及其子文件夹；“统计”中最活跃的文件夹现在会精确打开该文件夹
- **Improved** · Changes: go straight to any day with the new date button next to All / Today / Yesterday  
  改进 · 文件变更：通过“全部 / 今天 / 昨天”旁的新日期按钮直接跳到任意一天
- **Improved** · DeskTrace never fills up your disk: when the drive with its history has less than 1 GB free, changes are still recorded but no new copies are kept, and the change says so; Diagnostics shows the free space  
  改进 · 桌迹不会占满磁盘：当保存历史记录的磁盘可用空间不足 1 GB 时，变更仍会记录，但不再保存新的副本，并在变更中注明；诊断信息会显示可用空间
- **Improved** · Bulk changes: "Restore into a folder…" copies a group's versions into a folder you choose, keeping their subfolders; nothing at the original place is touched or overwritten  
  改进 · 批量变更：“恢复到其他文件夹…”会把一组文件的版本复制到你选择的文件夹并保留子文件夹结构；原位置的文件不会被改动或覆盖
- **Polish** · Time travel is in the sidebar and in Space's folder view, with quick choices for 1 hour, 1 day and 1 week ago  
  打磨 · 时光回溯位于侧边栏和“空间占用”的文件夹视图中，并提供 1 小时前、1 天前、1 周前等快捷选项
- **Polish** · Writing works out each document's progress once instead of twice  
  打磨 · 写作进度对每个文档只计算一次进度，而不是两次
- **Polish** · First-time indexing writes to the database in batches, which is faster  
  打磨 · 首次建立索引时批量写入数据库，速度更快
- **Polish** · Looking up the history of renamed or moved files uses an index and is faster  
  打磨 · 查询被重命名或移动的文件的历史时使用索引，速度更快
- **Polish** · Regular database upkeep keeps it quick and gives back disk space from its log file  
  打磨 · 定期维护数据库，使其保持快速，并收回日志文件占用的磁盘空间
- **Polish** · The window and tray icon are only updated when something actually changed  
  打磨 · 窗口和托盘图标只在确实有变化时才更新
- **Polish** · After 10 minutes without use DeskTrace drops its caches and gives memory back to Windows  
  打磨 · 闲置 10 分钟后，桌迹会清空缓存并把内存还给 Windows
- **Polish** · Opening the window is quicker: the open view comes first, the sidebar counts follow a moment later  
  打磨 · 打开窗口更快：先显示当前视图，侧边栏的计数稍后再加载
- **Polish** · Housekeeping (every 6 hours) goes through stored versions about 12 times faster, so it holds up change detection for far less time  
  打磨 · 定期清理（每 6 小时）检查已保存版本的速度提高约 12 倍，因而几乎不再耽误变更检测
- **Polish** · What uses the space (Settings) opens about twice as fast when many versions are kept  
  打磨 · 保留了大量版本时，设置中的“查看空间用途”打开速度提高约一倍
- **Polish** · Statistics open about twice as fast with a long history  
  打磨 · 历史记录很长时，“统计”的打开速度提高约一倍
- **Polish** · Alert rules: new quick-add template "Large file appears (500 MB or more)"  
  打磨 · 提醒规则：新增快速添加模板“出现大文件（500 MB 以上）”
- **Polish** · Alert rules: duplicate a rule to make a similar one quickly  
  打磨 · 提醒规则：可复制一条规则，快速创建相似的规则
- **Polish** · The log file stays small (about 1 MB) also while DeskTrace runs for weeks; it was only trimmed at start  
  打磨 · 桌迹连续运行数周时日志文件也保持很小（约 1 MB）；以前只在启动时裁剪
- **Polish** · Bursts of changes prepare their Windows notification with one timer instead of one per file (1,500 deleted files: 2 ms instead of 0.17 s of work during the scan)  
  打磨 · 一批变更只用一个计时器准备 Windows 通知，而不是每个文件一个（删除 1,500 个文件时，扫描中的额外工作从 0.17 秒降到 2 毫秒）
- **Polish** · Compared versions and current-file previews keep at most 64 MB each in memory; they were limited by count, so a few huge documents could hold hundreds of MB  
  打磨 · 版本对比和当前文件预览各自在内存中最多保留 64 MB；以前按数量限制，几个超大文档就可能占用数百 MB
- **Fix** · Writing: when more than 200 documents were edited in a week, it now shows the 200 edited most recently instead of an arbitrary 200  
  修复 · 写作进度：一周内编辑的文档超过 200 个时，现在显示最近编辑的 200 个，而不是随意的 200 个

## 2.0.1 — 2026-11-05

- **Major** · Alert rules no longer flood you: a burst of matching changes (e.g. a deleted folder) becomes one notification per rule  
  重要改进 · 提醒规则不再刷屏：一连串符合规则的变更（例如删除整个文件夹）会合并为每条规则一条通知
- **Major** · Duplicates now also finds large identical files (videos, archives, installers) beyond the snapshot limit; they are checked in the background  
  重要改进 · 重复文件现在也能找出超过快照上限的大文件（视频、压缩包、安装包），它们会在后台检查
- **Major** · Space: click a folder to look inside it — its biggest files, subfolders, types and growth; a separate button opens it in Explorer  
  重要改进 · 空间占用：点击文件夹即可查看其内部——最大的文件、子文件夹、类型和增长；另有按钮可在资源管理器中打开
- **Improved** · Alert rules: Show matches lists every change a rule has caught  
  改进 · 提醒规则：“查看匹配”可列出该规则捕获的所有变更
- **Improved** · Writing: set a daily word goal and see today's progress towards it  
  改进 · 写作进度：可设置每日字数目标，并查看今天的完成进度
- **Improved** · Alert rules: Pause all alerts for a while (e.g. while reorganising files) without changing the rules  
  改进 · 提醒规则：可暂时“暂停所有提醒”（例如整理文件时），而无需修改规则
- **Improved** · After an update, What's new lists the changes you just received, with their levels  
  改进 · 更新后，“新内容”会列出刚刚获得的变化及其级别
- **Improved** · When the list shows only deletions, one button restores all of them — handy after an accidental mass delete  
  改进 · 当列表只显示删除记录时，一个按钮即可全部恢复——误删大量文件后很方便
- **Improved** · Replace current file with this version (under More): roll a document back in place; its current content stays in DeskTrace so you can switch back  
  改进 · 用此版本替换当前文件（在“更多”中）：可直接把文档改回旧版本；当前内容仍保存在桌迹中，可随时换回
- **Improved** · Duplicates: right-click a set to open or show its newest copy, or keep the newest and recycle the rest  
  改进 · 重复文件：右键单击某组可打开或显示最新的一份，或保留最新的并回收其余副本
- **Improved** · Right-click any change or file in a list for its common actions: open, show in folder, restore, star, note, copy path  
  改进 · 在列表中右键单击任何变更或文件即可使用常用操作：打开、在文件夹中显示、恢复、加星标、备注、复制路径
- **Improved** · Alert rules: an optional minimum size, e.g. to be told when a file over 500 MB appears  
  改进 · 提醒规则：可设置最小文件大小，例如出现超过 500 MB 的文件时提醒
- **Improved** · Writing: a chart of the words you wrote on each of the last 7 days, across all documents  
  改进 · 写作进度：图表显示最近 7 天每天在所有文档中写了多少字
- **Improved** · Files: a Changed only switch shows just the files that have a history of changes (remembered)  
  改进 · 文件：“只看有改动的”开关只显示有变更历史的文件（会被记住）
- **Improved** · Duplicates and Space can be exported to Excel, e.g. as a clean-up list  
  改进 · 重复文件和空间占用可以导出为 Excel，例如作为清理清单
- **Improved** · Space: shows how much is taken by files not changed for over a year, and lists the biggest of them as clean-up candidates  
  改进 · 空间占用：显示超过一年未改动的文件占用了多少空间，并列出其中最大的文件作为清理候选
- **Improved** · Space: the biggest folders no longer list a folder and its own subfolder twice  
  改进 · 空间占用：最大的文件夹列表不再重复列出某个文件夹及其子文件夹
- **Improved** · A tidier detail panel: the main actions stay in view, the rest (download, open or save this version, copy path, ignore folder) are under More  
  改进 · 更整洁的详情面板：主要操作保持可见，其余操作（下载、打开或另存此版本、复制路径、忽略文件夹）放在“更多”中
- **Improved** · Duplicates ignores tiny files (under 1 KB) and system files such as desktop.ini and Thumbs.db  
  改进 · 重复文件会忽略很小的文件（小于 1 KB）和 desktop.ini、Thumbs.db 等系统文件
- **Improved** · Pop-ups inside the window only appear for deletions (with Restore); other changes are highlighted in the list  
  改进 · 窗口内的弹出提示只在删除时出现（带“恢复”按钮）；其他变更会在列表中高亮
- **Improved** · Settings: the snapshot and indexing size limits moved into Advanced  
  改进 · 设置：快照与索引的大小限制移到了“高级”中
- **Polish** · Statistics: clicking one of the most changed files opens its history  
  打磨 · 统计：点击改动最多的文件会直接打开其历史记录
- **Polish** · Alert rules: an optional notification sound per rule  
  打磨 · 提醒规则：每条规则可选择是否播放提示音
- **Polish** · New installations notify about deleted files by default (existing settings are kept)  
  打磨 · 新安装默认在文件被删除时通知（已有设置保持不变）
- **Polish** · Files: click a file's "N changes" badge to go straight to its history  
  打磨 · 文件：点击文件的“N 次变更”标签可直接查看其历史
- **Polish** · Writing: shows how many days in a row you reached your daily goal  
  打磨 · 写作进度：显示连续达成每日目标的天数
- **Polish** · Settings shows the size and number of files of each monitored folder  
  打磨 · 设置中会显示每个监控文件夹的大小和文件数量
- **Polish** · Ctrl+3, Ctrl+4 and Ctrl+5 open Duplicates, Space and Writing (Ctrl+1 / Ctrl+2: Changes / Files)  
  打磨 · Ctrl+3、Ctrl+4、Ctrl+5 分别打开重复文件、空间占用和写作进度（Ctrl+1 / Ctrl+2：变更 / 文件）
- **Polish** · On a deleted file, Restore is the highlighted button  
  打磨 · 对已删除的文件，“恢复”是突出显示的主按钮
- **Polish** · While the window is open, changes caught by an alert rule also pop up inside it, with the rule's name  
  打磨 · 窗口打开时，符合提醒规则的变更也会在窗口内弹出提示，并显示规则名称
- **Polish** · Restored versions keep their original date when it is known  
  打磨 · 恢复的版本在已知时会保留原来的修改日期
- **Polish** · A simpler sidebar: the 2-hour activity chart was removed (Statistics shows activity in more detail)  
  打磨 · 更简洁的侧边栏：移除了 2 小时活动图（统计中有更详细的活动信息）
- **Fix** · Esc works again for closing the detail panel, menus and the sidebar (since 1.6.1 the new shortcuts had taken it over)  
  修复 · Esc 键重新可以关闭详情面板、菜单和侧边栏（1.6.1 起被新的快捷键占用）
- **Fix** · Duplicates, Space and Writing only recalculate while their view is open, so DeskTrace does less work in the background  
  修复 · 重复文件、空间占用和写作进度只在打开对应视图时重新计算，后台负担更小
- **Fix** · The message after quitting no longer mentions closing a browser tab  
  修复 · 退出后的提示不再提及关闭浏览器标签页

## 2.0.0 — 2026-11-05

- **New** · New: Writing progress — every document (Word, PowerPoint, PDF, Markdown, text) gets a Progress tab charting its word count across all saved versions, with today's and this week's gain (Chinese is counted by character)  
  新功能 · 新功能：写作进度——每个文档（Word、PowerPoint、PDF、Markdown、文本）都有“进度”标签，用图表显示所有已保存版本的字数变化，以及今天和本周新增的字数（中文按字计算）
- **Major** · The Writing view lists the documents you worked on this week, most words added first, each with a small trend line  
  重要改进 · “写作进度”视图列出本周编辑过的文档，按新增字数排序，每个都带有趋势小图
- **Polish** · Versions with a note stand out as larger dots in the progress chart  
  打磨 · 带备注的版本在进度图中显示为较大的圆点

## 1.9.1 — 2026-11-05

- **Major** · Alert rules: one-click templates — an Office document or PDF deleted, anything deleted or moved, a new program or script  
  重要改进 · 提醒规则：一键模板——Office 文档或 PDF 被删除、任何文件被删除或移走、出现新的程序或脚本
- **Improved** · While you edit a rule, DeskTrace shows how often it would have triggered in the last 30 days, with examples  
  改进 · 编辑规则时，桌迹会显示这条规则在最近 30 天内会触发多少次，并给出示例

## 1.9.0 — 2026-11-05

- **New** · New: Alert rules — get a desktop notification when a change matches your rule (kind of change, file names like *.docx, and an optional folder), even when other notifications are off  
  新功能 · 新功能：提醒规则——当变更符合你的规则（变更类型、*.docx 之类的文件名、可选的文件夹）时弹出桌面通知，即使其他通知已关闭
- **Improved** · Each rule counts how often it was triggered and when it last was; rules can be switched off without deleting them  
  改进 · 每条规则都会统计触发次数和最近一次的时间；规则可以关闭而无需删除
- **Polish** · Changes that matched a rule carry a bell tag with the rule's name  
  打磨 · 符合规则的变更会带上标有规则名称的铃铛标签

## 1.8.1 — 2026-11-05

- **Improved** · Space: click a file type in the overview to list the biggest files of that type  
  改进 · 空间占用：在概览中点击某个文件类型，即可列出该类型最大的文件
- **Polish** · Space: each of the biggest folders shows its share of the total  
  打磨 · 空间占用：每个最大的文件夹都会显示其占总量的百分比

## 1.8.0 — 2026-11-05

- **New** · New: Space — see what takes up room in your monitored folders: biggest files, biggest folders, size by file type, and growth over 30 days  
  新功能 · 新功能：空间占用——查看监控文件夹里什么最占空间：最大的文件、最大的文件夹、按类型的大小，以及 30 天内的增长
- **Improved** · Languages: DeskTrace now speaks English and 简体中文 (German was removed)  
  改进 · 语言：桌迹现在提供英文和简体中文（已移除德语）
- **Polish** · The sidebar shows the total size of the monitored folders next to Space  
  打磨 · 侧边栏“空间占用”旁显示监控文件夹的总大小

## 1.7.1 — 2026-11-05

- **Major** · Duplicates: one click keeps the newest copy and moves all the others to the Recycle Bin  
  重要改进 · 重复文件：一键保留最新的一份，其余副本全部移到回收站
- **Improved** · Duplicates can be sorted by space used, number of copies or name (remembered)  
  改进 · 重复文件可按占用空间、副本数量或名称排序（会被记住）
- **Polish** · Enter opens the newest copy of the selected set of duplicates  
  打磨 · 按 Enter 打开所选重复组中最新的一份

## 1.7.0 — 2026-11-05

- **New** · New: Duplicates — finds files with identical content anywhere in your monitored folders, biggest waste first  
  新功能 · 新功能：重复文件——在所有监控文件夹中找出内容完全相同的文件，按浪费的空间从大到小排列
- **Improved** · Move an extra copy to the Recycle Bin right from DeskTrace; the last copy is always protected  
  改进 · 可直接在桌迹中把多余的副本移到回收站；最后一份始终受保护
- **Polish** · The sidebar shows how many sets of duplicates there are; ↑ ↓ move through them  
  打磨 · 侧边栏显示重复文件的组数；可用 ↑ ↓ 逐个查看

## 1.6.2 — 2026-11-05

- **Improved** · The window opens where you left it: view, date range, sort order and search mode are remembered  
  改进 · 窗口会回到上次离开时的状态：视图、时间范围、排序方式和搜索方式都会被记住
- **Polish** · The Notes view explains how to add a note when there are none yet  
  打磨 · “备注”视图在还没有备注时会说明如何添加
- **Fix** · Esc now also closes the pause menu  
  修复 · 按 Esc 现在也会关闭暂停菜单

## 1.6.1 — 2026-11-05

<details><summary>Release notes / 发布说明</summary>

50 updates in 1.6.1  
  
Notes on versions  
1. Add a note to any version ("sent to the client")  
2. Notes show on the change card  
3. ...and in the detail panel, with Edit  
4. Search finds notes too  
5. Notes appear in the History tab  
6. Excel export gets a Note column  
7. Versions with a note are never cleaned up  
8. "Notes" in the sidebar lists every noted version, with a count  
9. "With notes" filter chip  
  
Statistics (sidebar, tray, or key I)  
10. Changes per day for 30 days  
11. Totals per kind; click one to see those changes  
12. Click a day to see that day's changes  
13. Most changed files (click to open)  
14. Busiest folders; click to see their changes  
15. Ignore a folder right from the statistics  
16. Busiest day  
17. This week against the week before  
18. Activity by hour of day, with the peak hour  
19. Activity by day of the week  
20. Changes by file type (click to filter)  
21. Storage used, saved versions, notes  
22. Statistics entry in the tray menu  
  
Working with versions  
23. Open any version directly (read-only copy in its program)  
24. ...also from each entry in the History tab  
25. Save a version as... (choose name and place)  
  
Pause and quiet  
26. Pause for 30 minutes  
27. ...for 2 hours  
28. ...until 8:00 tomorrow  
29. The status shows when monitoring resumes  
30. Do not disturb for notifications (1 hour / until tomorrow)  
  
Folders and housekeeping  
31. Ignore a folder from any change  
32. Undo right after ignoring  
33. Manage ignored folders in Settings  
34. Explorer right-click entry "DeskTrace: show history" (switch in Settings)  
35. Clean up now (applies Keep history / Storage limit at once)  
36. Diagnostics in Settings  
37. Copy the diagnostics report  
  
List and filters  
38. "Yesterday" range  
39. One day picked in the statistics, shown as a removable chip  
40. Each day header shows its number of changes  
41. Filters also apply to changes arriving live  
42. Excel export follows the day and notes filters  
  
Keyboard  
43. 1-4: show only created / modified / deleted / renamed  
44. C: copy the path  
45. E: show in Explorer  
46. N: add or edit the note  
47. Left / Right: previous / next tab  
48. Home / End: first / last item  
49. Ctrl+E: export to Excel  
50. Ctrl+1 / Ctrl+2: Changes / Files

1.6.1 共 50 项更新  
  
版本备注  
1. 可为任意版本添加备注（如“已发给客户”）  
2. 备注显示在变更卡片上  
3. 详情面板中显示备注并可编辑  
4. 搜索也能找到备注  
5. 历史记录中显示备注  
6. Excel 导出增加“备注”列  
7. 带备注的版本永不自动清理  
8. 侧边栏“备注”列出所有带备注的版本并显示数量  
9. “有备注的”筛选标签  
  
统计（侧边栏、托盘或按 I）  
10. 最近 30 天每日变更  
11. 各类变更合计，点击即查看  
12. 点击某天查看当天的变更  
13. 改动最多的文件（点击打开）  
14. 最活跃的文件夹，点击查看其变更  
15. 在统计中直接忽略文件夹  
16. 最忙的一天  
17. 本周与上周对比  
18. 按时段的活动及高峰时间  
19. 按星期的活动  
20. 按文件类型统计（点击筛选）  
21. 存储占用、已保存版本数、备注数  
22. 托盘菜单中的“统计”  
  
版本操作  
23. 直接打开任意版本（只读副本）  
24. 历史记录每一项都可直接打开  
25. 版本另存为（自选位置和文件名）  
  
暂停与勿扰  
26. 暂停 30 分钟  
27. 暂停 2 小时  
28. 暂停到明早 8:00  
29. 状态栏显示何时自动继续  
30. 通知勿扰（1 小时 / 到明早）  
  
文件夹与整理  
31. 在任意变更上忽略其文件夹  
32. 忽略后可立即撤销  
33. 在设置中管理已忽略的文件夹  
34. 资源管理器右键菜单“桌迹：查看历史版本”（设置中开关）  
35. 立即清理（马上应用“保留历史/存储上限”）  
36. 设置中的诊断信息  
37. 一键复制诊断报告  
  
列表与筛选  
38. “昨天”时间范围  
39. 在统计中选中的某一天显示为可移除的筛选标签  
40. 每个日期标题显示当天变更数  
41. 筛选同样作用于实时到达的变更  
42. Excel 导出遵循日期和备注筛选  
  
快捷键  
43. 1–4：只看新建/修改/删除/重命名  
44. C：复制路径  
45. E：在资源管理器中显示  
46. N：添加或编辑备注  
47. ← / →：切换标签  
48. Home / End：第一项 / 最后一项  
49. Ctrl+E：导出到 Excel  
50. Ctrl+1 / Ctrl+2：变更 / 文件

</details>

## 1.6 — 2026-11-05

- First released version. / 首个发布版本。
