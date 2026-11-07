'use strict';
/* UI translations. Each value is a string, or {one, other} for count-dependent text.
   Placeholders look like {name}. Missing keys fall back to English. */

const LANGS = {
  en: { name: 'English', short: 'EN', locale: 'en-US', html: 'en' },
  zh: { name: '简体中文', short: '中', locale: 'zh-CN', html: 'zh-CN' },
};

const I18N = {
  en: {
    'status.connecting': 'Connecting…', 'status.reconnecting': 'Reconnecting…', 'status.starting': 'Starting…',
    'status.paused': 'Paused', 'status.live': 'Live · {files} files · every {s}s', 'status.lastScan': 'Last scan took {ms} ms',
    'btn.pause': 'Pause', 'btn.resume': 'Resume', 'btn.cancel': 'Cancel', 'btn.close': 'Close',
    'search.placeholder': 'Search name or path',
    'title.theme': 'Toggle theme', 'title.settings': 'Settings', 'title.overview': 'Overview', 'title.language': 'Language',
    'side.today': 'Today', 'side.clickFilter': 'click to filter', 'side.activity': 'Activity', 'side.last2h': 'last 2 hours',
    'side.types': 'File types', 'side.typesHint': 'events · tracked', 'side.monitoring': 'Monitoring', 'list.title': 'Changes',
    'kind.created': 'Created', 'kind.modified': 'Modified', 'kind.deleted': 'Deleted', 'kind.renamed': 'Renamed',
    'cat.word': 'Word', 'cat.excel': 'Excel', 'cat.ppt': 'PowerPoint', 'cat.pdf': 'PDF', 'cat.markdown': 'Markdown',
    'cat.text': 'Text', 'cat.code': 'Code & data', 'cat.image': 'Images', 'cat.archive': 'Archives', 'cat.media': 'Audio & video', 'cat.other': 'Other',
    'u.paragraph': { one: 'paragraph', other: 'paragraphs', cap: 'Paragraph' },
    'u.cell': { one: 'cell', other: 'cells', cap: 'Cell' },
    'u.line': { one: 'line', other: 'lines', cap: 'Line' },
    'kpi.allTime': '{n} all time',
    'chart.aria': 'Changes per 5 minutes over the last 2 hours',
    'chart.total': { one: '<b>{n}</b> change in the last 2 hours', other: '<b>{n}</b> changes in the last 2 hours' },
    'chart.peak': ' · peak <b>{p}</b> / 5 min', 'chart.m2h': '−2h', 'chart.m1h': '−1h', 'chart.now': 'now',
    'chart.tip': { one: '{a}–{b} · {n} change', other: '{a}–{b} · {n} changes' },
    'cats.empty': 'No files tracked yet.', 'cats.trackedTitle': 'Files currently tracked',
    'scope.indexing': 'Indexing existing documents', 'scope.files': 'Files tracked', 'scope.scanEvery': 'Scan every',
    'scope.storage': 'History storage', 'scope.ignoring': 'Ignoring shortcuts ({lnk}), Office lock files ({lock}) and temp files.',
    'scope.change': 'Change…', 'scope.folders': '{n} folders',
    'time.justNow': 'just now', 'time.s': '{n}s ago', 'time.m': '{n}m ago', 'time.h': '{n}h ago', 'time.d': '{n}d ago',
    'day.today': 'Today', 'day.yesterday': 'Yesterday',
    'list.emptyTitle': 'Watching for changes',
    'list.emptyText': 'Create, edit, rename or delete a file in a monitored folder and it shows up here within seconds.',
    'list.noMatchTitle': 'No changes match', 'list.noMatchText': 'Try removing a filter or changing the search.',
    'list.more': 'Load older changes', 'filter.clearAll': 'Clear all',
    'tag.away': 'while away', 'tag.awayTitle': 'Detected at startup — happened while DeskTrace was not running',
    'analyzing': 'Analyzing…',
    'sum.new': 'New file', 'sum.newN': 'New file · {n} {unit}', 'sum.del': 'Deleted', 'sum.delN': 'Deleted · had {n} {unit}',
    'sum.renamed': 'Renamed', 'sum.moved': 'Moved', 'sum.big': 'Too large to snapshot ({size})', 'sum.locked': 'File locked — no snapshot', 'sum.lowdisk': 'Disk almost full — no snapshot kept',
    'sum.same': 'Saved — content unchanged', 'sum.fmt': 'Formatting / binary change', 'sum.size': 'Size {d}',
    'tab.changes': 'Changes', 'tab.this': 'This version', 'tab.before': 'Before', 'tab.current': 'Current file',
    'tab.history': 'History', 'tab.details': 'Details', 'tab.content': 'Content', 'tab.last': 'Last version',
    'path.from': 'From', 'path.gone': 'Not on disk now', 'path.copy': 'Copy path',
    'welcome.title': 'Select a change to preview it',
    'welcome.text': 'Every version is snapshotted, so you can see exactly what changed in Word, Excel, PowerPoint, PDF, Markdown and text files — even after they\'re deleted.',
    'keys.move': 'move', 'keys.search': 'search', 'keys.clear': 'clear',
    'act.open': 'Open file', 'act.openGone': 'The file is no longer at this path', 'act.reveal': 'Show in folder',
    'act.restoreFile': 'Restore file', 'act.restoreThis': 'Restore this version', 'act.download': 'Download this version',
    'v.notCaptured': 'This version was not captured.',
    'v.prevNotCaptured': 'The previous version wasn\'t captured — the file existed before monitoring started and is not a document type indexed at startup (or it was larger than the indexing limit).',
    'v.viewCurrent': 'View current file', 'v.blobGone': 'The stored copy of this version is no longer available.',
    'v.textOnly': 'Showing the text indexed when monitoring started — the original file was larger than the copy limit, so only its content was kept.',
    'v.beforeHint': 'The file as it was before this change.', 'v.restoreEarlier': 'Restore this earlier version',
    'cur.live': 'Live from disk · {size} · saved {time}',
    'hist.count': { one: '1 recorded change for this file', other: '{n} recorded changes for this file' }, 'hist.snapshot': 'snapshot',
    'p.change': 'Change', 'p.docProps': 'Document properties', 'p.event': 'Event', 'p.startup': ' (detected at startup)',
    'p.recorded': 'Recorded', 'p.path': 'Path', 'p.prevPath': 'Previous path', 'p.type': 'Type', 'p.noExt': 'no extension',
    'p.sizeBefore': 'Size before', 'p.sizeAfter': 'Size after', 'p.timestamp': 'File timestamp', 'p.thisVer': 'This version',
    'p.prevVer': 'Previous version', 'p.onDisk': 'Currently on disk', 'p.yes': 'Yes', 'p.no': 'No',
    'snap.full': 'Full copy kept', 'snap.text': 'Text index only', 'snap.none': 'Not captured',
    'meta.Title': 'Title', 'meta.Author': 'Author', 'meta.Last modified by': 'Last modified by', 'meta.Created': 'Created',
    'meta.Saved': 'Saved', 'meta.Revision': 'Revision', 'meta.Pages': 'Pages', 'meta.Words': 'Words', 'meta.Slides': 'Slides',
    'meta.Application': 'Application', 'meta.Paragraphs': 'Paragraphs', 'meta.Sheets': 'Sheets', 'meta.Non-empty cells': 'Non-empty cells',
    'meta.Lines': 'Lines', 'meta.Characters': 'Characters', 'meta.Rows': 'Rows', 'meta.Dimensions': 'Dimensions', 'meta.Mode': 'Mode',
    'meta.Format': 'Format', 'meta.Entries': 'Entries', 'meta.Text cells': 'Text cells', 'meta.Creator': 'Creator',
    'meta.Producer': 'Producer', 'meta.Moddate': 'Modified',
    'diff.before': 'Before', 'diff.after': 'After', 'diff.notCaptured': 'Not captured',
    'diff.missing': 'There\'s no earlier snapshot to compare with — this file existed before monitoring started and wasn\'t indexed (unsupported type or above the size limit). The next change will be comparable.',
    'diff.viewThis': 'View this version',
    'diff.same': 'The file was saved, but its content is byte-for-byte identical to the previous version.',
    'diff.binary': 'Content changed, but this file type can\'t be compared as text. Size {a} → {b}.',
    'diff.noText': 'No text differences — the change is in formatting, layout, images or other non-text content.',
    'diff.headDel': 'Deleted · {n} {unit} removed', 'diff.headMod': '{a} → {b} {unit}',
    'diff.wrap': 'Wrap', 'diff.nowrap': 'No wrap', 'diff.truncated': 'This diff is very large; only the first part is shown.',
    'diff.hunk': '{U} {a} → {b}', 'diff.changedN': '{n} changed',
    'mark.slide': '[Slide {n}]', 'mark.notes': '[Notes]', 'mark.page': '──── Page {n} ────',
    'c.legacy': 'Legacy {fmt} file — showing the extracted text. Open the file for full formatting.',
    'c.imgNotCaptured': 'The image itself was not captured.', 'c.entries': '{n} entries',
    'c.error': 'Couldn\'t read this file\'s content:', 'c.noPreview': 'No preview for this file type.',
    'c.useOpen': 'Use <b>Open file</b> to view it in its own app.', 'c.image': 'image', 'c.docEmpty': 'This document is empty.',
    'c.noSlides': 'This presentation has no slides.',
    'c.textBlocks': { one: '1 text block', other: '{n} text blocks' }, 'c.images': { one: '1 image', other: '{n} images' },
    'c.notes': 'Speaker notes', 'c.noSheets': 'This workbook has no sheets.', 'c.sheetEmpty': 'This sheet is empty.',
    'c.clickCell': 'Click a cell to inspect it', 'c.cells': '{n} cells',
    'c.pdfDoc': 'Document', 'c.pdfText': 'Extracted text', 'c.pages': '{n} pages', 'c.page': 'Page {n}',
    'c.noPageText': 'No text on this page (scanned image?)', 'c.noPdfText': 'No text found in this PDF.',
    'c.rendered': 'Rendered', 'c.source': 'Source', 'c.lines': '{n} lines', 'c.empty': 'This file is empty.',
    'c.firstN': 'Showing the first {a} of {b} lines.',
    'toast.more': { one: '+1 more change', other: '+{n} more changes' }, 'toast.seeAll': 'See the timeline for all of them',
    'set.title': 'Settings', 'set.lang': 'Language', 'set.langHint': 'Applies to this window right away.',
    'set.folders': 'Monitored folders', 'set.foldersHint': 'Everything inside these folders is watched, including subfolders.',
    'set.pastePh': 'Paste a folder path, e.g. D:\\Projects', 'set.add': 'Add', 'set.browse': 'Browse…', 'set.stop': 'Stop monitoring',
    'set.interval': 'Scan interval',
    'set.intervalHint': 'How often folders are checked. A change is recorded once the file has stopped changing for one interval, so half-written files are skipped.',
    'set.snap': 'Snapshot limit (MB)', 'set.snapHint': 'Files up to this size get a full copy of every version.',
    'set.baseText': 'Startup index (MB)', 'set.baseTextHint': 'Existing documents up to this size have their text indexed.',
    'set.baseCopy': 'Startup copy (MB)', 'set.baseCopyHint': 'Existing documents up to this size are copied in full.',
    'set.exExt': 'Ignored extensions', 'set.exExtHint': 'Shortcuts and temporary files are ignored by default. Separate entries with commas.',
    'set.exNames': 'Ignored file names', 'set.exNamesHint': 'Wildcards allowed — {lock} skips Office lock files.',
    'set.exDirs': 'Ignored folders',
    'set.clearTitle': 'Clear change history', 'set.clearText': 'Removes all recorded changes and their snapshots. Stored in {dir}',
    'set.clearBtn': 'Clear…', 'set.reset': 'Reset to defaults', 'set.save': 'Save changes', 'set.saved': 'Settings saved.',
    'clear.title': 'Clear all history?',
    'clear.text': 'Every recorded change and stored snapshot will be removed. Your actual files are not touched.',
    'clear.ok': 'Clear history', 'clear.done': 'History cleared.',
    'restore.copyNote': 'A copy will be saved next to the original, named “… (restored <time>)”. The current file is not overwritten.',
    'restore.origNote': 'The file will be restored to its original location:',
    'restore.titleEarlier': 'Restore the earlier version?', 'restore.title': 'Restore this version?', 'restore.ok': 'Restore',
    'restore.done': 'Restored to {path}',
    'err.gone': 'The file no longer exists at this path.', 'err.tooLarge': 'File is too large to preview ({size}).',
    'err.notAllowed': 'Not allowed.', 'err.noSnapshot': 'No full snapshot of this version was kept.',
    'err.noRoots': 'Add at least one existing folder to monitor.', 'err.generic': 'Something went wrong.',
  },

  zh: {
    'status.connecting': '正在连接…', 'status.reconnecting': '正在重新连接…', 'status.starting': '正在启动…',
    'status.paused': '已暂停', 'status.live': '实时 · {files} 个文件 · 每 {s} 秒', 'status.lastScan': '上次扫描耗时 {ms} 毫秒',
    'btn.pause': '暂停', 'btn.resume': '继续', 'btn.cancel': '取消', 'btn.close': '关闭',
    'search.placeholder': '搜索文件名或路径',
    'title.theme': '切换主题', 'title.settings': '设置', 'title.overview': '概览', 'title.language': '语言',
    'side.today': '今天', 'side.clickFilter': '点击筛选', 'side.activity': '活动', 'side.last2h': '最近 2 小时',
    'side.types': '文件类型', 'side.typesHint': '变更 · 已跟踪', 'side.monitoring': '监控范围', 'list.title': '变更记录',
    'kind.created': '新建', 'kind.modified': '修改', 'kind.deleted': '删除', 'kind.renamed': '重命名',
    'cat.word': 'Word', 'cat.excel': 'Excel', 'cat.ppt': 'PowerPoint', 'cat.pdf': 'PDF', 'cat.markdown': 'Markdown',
    'cat.text': '文本', 'cat.code': '代码与数据', 'cat.image': '图片', 'cat.archive': '压缩包', 'cat.media': '音视频', 'cat.other': '其他',
    'u.paragraph': { one: '段', other: '段', cap: '段落' },
    'u.cell': { one: '个单元格', other: '个单元格', cap: '单元格' },
    'u.line': { one: '行', other: '行', cap: '行' },
    'kpi.allTime': '累计 {n}',
    'chart.aria': '最近 2 小时每 5 分钟的变更数',
    'chart.total': '最近 2 小时共 <b>{n}</b> 次变更',
    'chart.peak': ' · 峰值 <b>{p}</b> 次/5 分钟', 'chart.m2h': '−2 小时', 'chart.m1h': '−1 小时', 'chart.now': '现在',
    'chart.tip': '{a}–{b} · {n} 次变更',
    'cats.empty': '尚未跟踪任何文件。', 'cats.trackedTitle': '当前跟踪的文件数',
    'scope.indexing': '正在索引现有文档', 'scope.files': '跟踪的文件', 'scope.scanEvery': '扫描间隔',
    'scope.storage': '历史占用空间', 'scope.ignoring': '已忽略快捷方式（{lnk}）、Office 锁定文件（{lock}）和临时文件。',
    'scope.change': '修改…', 'scope.folders': '{n} 个文件夹',
    'time.justNow': '刚刚', 'time.s': '{n} 秒前', 'time.m': '{n} 分钟前', 'time.h': '{n} 小时前', 'time.d': '{n} 天前',
    'day.today': '今天', 'day.yesterday': '昨天',
    'list.emptyTitle': '正在监控变更',
    'list.emptyText': '在受监控的文件夹中新建、编辑、重命名或删除文件，几秒内就会显示在这里。',
    'list.noMatchTitle': '没有匹配的变更', 'list.noMatchText': '请尝试移除筛选条件或修改搜索内容。',
    'list.more': '加载更早的变更', 'filter.clearAll': '全部清除',
    'tag.away': '离线期间', 'tag.awayTitle': '启动时检测到——发生在 桌迹 未运行期间',
    'analyzing': '正在分析…',
    'sum.new': '新文件', 'sum.newN': '新文件 · {n} {unit}', 'sum.del': '已删除', 'sum.delN': '已删除 · 原有 {n} {unit}',
    'sum.renamed': '已重命名', 'sum.moved': '已移动', 'sum.big': '文件过大，未保存快照（{size}）', 'sum.locked': '文件被占用，未保存快照', 'sum.lowdisk': '磁盘空间不足，未保存快照',
    'sum.same': '已保存，内容未变化', 'sum.fmt': '格式或二进制内容变化', 'sum.size': '大小 {d}',
    'tab.changes': '变更', 'tab.this': '此版本', 'tab.before': '修改前', 'tab.current': '当前文件',
    'tab.history': '历史', 'tab.details': '详情', 'tab.content': '内容', 'tab.last': '最后版本',
    'path.from': '原位置', 'path.gone': '磁盘上已不存在', 'path.copy': '复制路径',
    'welcome.title': '选择一条变更进行预览',
    'welcome.text': '每个版本都会保存快照，你可以准确查看 Word、Excel、PowerPoint、PDF、Markdown 和文本文件中的改动——即使文件已被删除。',
    'keys.move': '切换', 'keys.search': '搜索', 'keys.clear': '清除',
    'act.open': '打开文件', 'act.openGone': '文件已不在此路径', 'act.reveal': '在文件夹中显示',
    'act.restoreFile': '恢复文件', 'act.restoreThis': '恢复此版本', 'act.download': '下载此版本',
    'v.notCaptured': '此版本未被捕获。',
    'v.prevNotCaptured': '未捕获之前的版本——该文件在开始监控前就已存在，且不属于启动时索引的文档类型（或超过了索引大小限制）。',
    'v.viewCurrent': '查看当前文件', 'v.blobGone': '此版本的存储副本已不可用。',
    'v.textOnly': '显示的是开始监控时索引的文本——原文件超过复制大小限制，因此只保留了其内容。',
    'v.beforeHint': '此次修改之前的文件。', 'v.restoreEarlier': '恢复此早期版本',
    'cur.live': '实时读取 · {size} · 保存于 {time}',
    'hist.count': '此文件共有 {n} 条变更记录', 'hist.snapshot': '快照',
    'p.change': '变更', 'p.docProps': '文档属性', 'p.event': '事件', 'p.startup': '（启动时检测到）',
    'p.recorded': '记录时间', 'p.path': '路径', 'p.prevPath': '原路径', 'p.type': '类型', 'p.noExt': '无扩展名',
    'p.sizeBefore': '修改前大小', 'p.sizeAfter': '修改后大小', 'p.timestamp': '文件时间戳', 'p.thisVer': '此版本',
    'p.prevVer': '上一版本', 'p.onDisk': '当前是否存在', 'p.yes': '是', 'p.no': '否',
    'snap.full': '已保存完整副本', 'snap.text': '仅文本索引', 'snap.none': '未捕获',
    'meta.Title': '标题', 'meta.Author': '作者', 'meta.Last modified by': '最后修改者', 'meta.Created': '创建时间',
    'meta.Saved': '保存时间', 'meta.Revision': '修订号', 'meta.Pages': '页数', 'meta.Words': '字数', 'meta.Slides': '幻灯片数',
    'meta.Application': '应用程序', 'meta.Paragraphs': '段落数', 'meta.Sheets': '工作表数', 'meta.Non-empty cells': '非空单元格',
    'meta.Lines': '行数', 'meta.Characters': '字符数', 'meta.Rows': '行数', 'meta.Dimensions': '尺寸', 'meta.Mode': '颜色模式',
    'meta.Format': '格式', 'meta.Entries': '条目数', 'meta.Text cells': '文本单元格', 'meta.Creator': '创建工具',
    'meta.Producer': '生成工具', 'meta.Moddate': '修改日期',
    'diff.before': '修改前', 'diff.after': '修改后', 'diff.notCaptured': '未捕获',
    'diff.missing': '没有可供比较的早期快照——该文件在开始监控前就已存在且未被索引（类型不支持或超过大小限制）。下一次修改将可以比较。',
    'diff.viewThis': '查看此版本',
    'diff.same': '文件已保存，但内容与上一版本完全相同。',
    'diff.binary': '内容已变化，但此类文件无法按文本比较。大小 {a} → {b}。',
    'diff.noText': '没有文字差异——变化在于格式、版式、图片或其他非文本内容。',
    'diff.headDel': '已删除 · 移除 {n} {unit}', 'diff.headMod': '{a} → {b} {unit}',
    'diff.wrap': '自动换行', 'diff.nowrap': '不换行', 'diff.truncated': '差异内容过大，仅显示前一部分。',
    'diff.hunk': '{U} {a} → {b}', 'diff.changedN': '{n} 处变更',
    'mark.slide': '[幻灯片 {n}]', 'mark.notes': '[备注]', 'mark.page': '──── 第 {n} 页 ────',
    'c.legacy': '旧版 {fmt} 文件——仅显示提取的文本。打开文件可查看完整格式。',
    'c.imgNotCaptured': '图片本身未被捕获。', 'c.entries': '{n} 个条目',
    'c.error': '无法读取此文件的内容：', 'c.noPreview': '此文件类型无法预览。',
    'c.useOpen': '请使用<b>打开文件</b>在对应程序中查看。', 'c.image': '图片', 'c.docEmpty': '此文档为空。',
    'c.noSlides': '此演示文稿没有幻灯片。',
    'c.textBlocks': '{n} 个文本块', 'c.images': '{n} 张图片',
    'c.notes': '演讲者备注', 'c.noSheets': '此工作簿没有工作表。', 'c.sheetEmpty': '此工作表为空。',
    'c.clickCell': '点击单元格查看内容', 'c.cells': '{n} 个单元格',
    'c.pdfDoc': '文档', 'c.pdfText': '提取的文本', 'c.pages': '共 {n} 页', 'c.page': '第 {n} 页',
    'c.noPageText': '此页没有文字（可能是扫描图片）', 'c.noPdfText': '此 PDF 中未找到文字。',
    'c.rendered': '渲染', 'c.source': '源码', 'c.lines': '{n} 行', 'c.empty': '此文件为空。',
    'c.firstN': '仅显示前 {a} 行（共 {b} 行）。',
    'toast.more': '还有 {n} 条变更', 'toast.seeAll': '请在变更记录中查看全部',
    'set.title': '设置', 'set.lang': '语言', 'set.langHint': '立即应用到此窗口。',
    'set.folders': '监控的文件夹', 'set.foldersHint': '这些文件夹中的所有内容（包括子文件夹）都会被监控。',
    'set.pastePh': '粘贴文件夹路径，例如 D:\\Projects', 'set.add': '添加', 'set.browse': '浏览…', 'set.stop': '停止监控',
    'set.interval': '扫描间隔',
    'set.intervalHint': '检查文件夹的频率。文件在一个间隔内不再变化后才会记录变更，因此写入到一半的文件会被跳过。',
    'set.snap': '快照上限 (MB)', 'set.snapHint': '不超过此大小的文件会保存每个版本的完整副本。',
    'set.baseText': '启动索引上限 (MB)', 'set.baseTextHint': '不超过此大小的现有文档会索引其文本。',
    'set.baseCopy': '启动复制上限 (MB)', 'set.baseCopyHint': '不超过此大小的现有文档会被完整复制。',
    'set.exExt': '忽略的扩展名', 'set.exExtHint': '默认忽略快捷方式和临时文件。多个条目用逗号分隔。',
    'set.exNames': '忽略的文件名', 'set.exNamesHint': '支持通配符——{lock} 可跳过 Office 锁定文件。',
    'set.exDirs': '忽略的文件夹',
    'set.clearTitle': '清除变更历史', 'set.clearText': '删除所有变更记录及其快照。存储位置：{dir}',
    'set.clearBtn': '清除…', 'set.reset': '恢复默认设置', 'set.save': '保存更改', 'set.saved': '设置已保存。',
    'clear.title': '清除全部历史？',
    'clear.text': '所有变更记录和已存储的快照都将被删除，你的实际文件不受影响。',
    'clear.ok': '清除历史', 'clear.done': '历史已清除。',
    'restore.copyNote': '副本将保存在原文件旁边，名称为“…（已恢复 <时间>）”，不会覆盖当前文件。',
    'restore.origNote': '文件将恢复到原位置：',
    'restore.titleEarlier': '恢复早期版本？', 'restore.title': '恢复此版本？', 'restore.ok': '恢复',
    'restore.done': '已恢复到 {path}',
    'err.gone': '该路径下的文件已不存在。', 'err.tooLarge': '文件过大，无法预览（{size}）。',
    'err.notAllowed': '不允许访问。', 'err.noSnapshot': '此版本没有保存完整快照。',
    'err.noRoots': '请至少添加一个存在的文件夹进行监控。', 'err.generic': '出现错误。',
  },

};

/* Files browser */
Object.assign(I18N.en, {
  'mode.changes': 'Changes', 'mode.files': 'Files', 'files.sortRecent': 'Recently modified', 'files.sortName': 'Name', 'files.sortSize': 'Size',
  'files.changes': { one: '1 change', other: '{n} changes' }, 'files.empty': 'No files match.', 'files.more': 'Load more files',
  'files.shown': '{shown} of {total}', 'fd.noChanges': 'No recorded changes yet', 'fd.modified': 'modified {time}',
  'p.modified': 'Last modified', 'p.size': 'Size', 'p.indexed': 'Startup index',
  'fd.indexedYes': 'Indexed — its first change will be comparable', 'fd.indexedNo': 'Not indexed (type or size not covered)',
  'act.downloadFile': 'Download', 'c.imgAlt': 'Embedded image',
});
Object.assign(I18N.zh, {
  'mode.changes': '变更', 'mode.files': '文件', 'files.sortRecent': '最近修改', 'files.sortName': '名称', 'files.sortSize': '大小',
  'files.changes': '{n} 次变更', 'files.empty': '没有匹配的文件。', 'files.more': '加载更多文件',
  'files.shown': '{shown} / {total}', 'fd.noChanges': '暂无变更记录', 'fd.modified': '修改于 {time}',
  'p.modified': '最后修改', 'p.size': '大小', 'p.indexed': '启动索引',
  'fd.indexedYes': '已索引——首次修改即可对比', 'fd.indexedNo': '未索引（类型或大小不在范围内）',
  'act.downloadFile': '下载', 'c.imgAlt': '嵌入的图片',
});
/* Background running & startup */
Object.assign(I18N.en, {
  'set.bg': 'Background & startup', 'set.autostart': 'Start automatically with Windows',
  'set.autostartHint': 'Runs silently in the background after you sign in — no window, no browser tab.',
  'set.quit': 'Quit DeskTrace', 'set.quitHint': 'Stops background monitoring until you start it again from the Desktop shortcut.',
  'quit.title': 'Quit DeskTrace?', 'quit.text': 'Monitoring stops. Changes made while it is off are still detected the next time it starts.',
  'quit.ok': 'Quit', 'stopped.title': 'DeskTrace has stopped',
  'stopped.text': 'Double-click the DeskTrace shortcut on your Desktop to start it again. ',
  'autostart.on': 'DeskTrace will start automatically with Windows.', 'autostart.off': 'Automatic start turned off.',
});
Object.assign(I18N.zh, {
  'set.bg': '后台运行与开机启动', 'set.autostart': '开机时自动启动',
  'set.autostartHint': '登录 Windows 后在后台静默运行——不弹出窗口，也不打开浏览器。',
  'set.quit': '退出 桌迹', 'set.quitHint': '停止后台监控，直到你再次通过桌面快捷方式启动。',
  'quit.title': '退出 桌迹？', 'quit.text': '监控将停止。停止期间发生的变更会在下次启动时被检测到。',
  'quit.ok': '退出', 'stopped.title': '桌迹 已停止',
  'stopped.text': '双击桌面上的 桌迹 快捷方式即可重新启动。',
  'autostart.on': '已设置为开机自动启动。', 'autostart.off': '已关闭开机自动启动。',
});
/* Batch: views, filters, stars, export, shortcuts */
Object.assign(I18N.en, {
  'range.all': 'All', 'range.today': 'Today', 'range.7': '7 days', 'range.30': '30 days',
  'export.btn': 'Excel', 'export.title': 'Export these changes to Excel',
  'star.filter': 'Show starred files only', 'star.add': 'Star', 'star.remove': 'Starred', 'star.chip': 'Starred',
  'star.title': 'Starred files always send a desktop notification when they change',
  'files.sortChanges': 'Most changed',
  'diff.unified': 'One column', 'diff.side': 'Side by side', 'diff.sheet': 'In sheet', 'diff.full': 'Whole document',
  'diff.sheetHint': 'Changed cells are coloured: green = new, amber = changed, red = cleared.',
  'keys.open': 'open file', 'keys.help': 'all shortcuts',
  'help.title': 'Keyboard shortcuts', 'help.move': 'Move through the list', 'help.search': 'Search',
  'help.open': 'Open the selected file', 'help.star': 'Star or unstar the selected file', 'help.mode': 'Switch between Changes and Files',
  'help.esc': 'Clear the search, close panels', 'help.help': 'Show this list', 'help.dbl': 'Tip: double-click a card to open its file.',
  'toast.restore': 'Restore',
  'set.quickAdd': 'Quick add:', 'folder.documents': 'Documents', 'folder.downloads': 'Downloads', 'folder.pictures': 'Pictures',
  'set.openData': 'Open data folder', 'set.openLog': 'Open log',
});
Object.assign(I18N.zh, {
  'range.all': '全部', 'range.today': '今天', 'range.7': '7 天', 'range.30': '30 天',
  'export.btn': '导出', 'export.title': '将这些变更导出到 Excel',
  'star.filter': '只看已加星标的文件', 'star.add': '加星标', 'star.remove': '已加星标', 'star.chip': '已加星标',
  'star.title': '加星标的文件一有变化就会弹出桌面通知',
  'files.sortChanges': '变更最多',
  'diff.unified': '单栏', 'diff.side': '并排', 'diff.sheet': '表格', 'diff.full': '显示全文',
  'diff.sheetHint': '已为变化的单元格着色：绿色为新增，橙色为修改，红色为清空。',
  'keys.open': '打开文件', 'keys.help': '全部快捷键',
  'help.title': '键盘快捷键', 'help.move': '在列表中上下移动', 'help.search': '搜索',
  'help.open': '打开选中的文件', 'help.star': '为选中的文件加星标或取消', 'help.mode': '在“变更”和“文件”之间切换',
  'help.esc': '清除搜索、关闭面板', 'help.help': '显示此列表', 'help.dbl': '提示：双击卡片即可打开对应文件。',
  'toast.restore': '恢复',
  'set.quickAdd': '快速添加：', 'folder.documents': '文档', 'folder.downloads': '下载', 'folder.pictures': '图片',
  'set.openData': '打开数据文件夹', 'set.openLog': '打开日志',
});
/* Redline document view, image swipe */
Object.assign(I18N.en, {
  'diff.doc': 'In document', 'diff.docHint': 'Green = added, red with strikethrough = removed. Gaps (⋯) are long unchanged stretches.',
  'diff.swipe': 'Swipe',
});
Object.assign(I18N.zh, {
  'diff.doc': '文档视图', 'diff.docHint': '绿色为新增，红色删除线为删除。',
  'diff.swipe': '滑动对比',
});
/* Comparing versions */
Object.assign(I18N.en, {
  'cmp.pick': 'Tick two versions to compare', 'cmp.pickTitle': 'Select this version for comparing', 'cmp.btn': 'Compare',
  'cmp.current': 'Current file on disk', 'cmp.withCurrent': 'Compare with current file', 'cmp.back': 'History',
  'cmp.same': 'These two versions have the same text.', 'cmp.unavailable': 'One of these versions wasn’t captured, so they can’t be compared.',
});
Object.assign(I18N.zh, {
  'cmp.pick': '勾选两个版本进行比较', 'cmp.pickTitle': '选择此版本用于比较', 'cmp.btn': '比较',
  'cmp.current': '磁盘上的当前文件', 'cmp.withCurrent': '与当前文件比较', 'cmp.back': '历史',
  'cmp.same': '这两个版本的文字内容相同。', 'cmp.unavailable': '其中一个版本未被捕获，无法比较。',
});
/* Content search */
Object.assign(I18N.en, {
  'files.byName': 'Name', 'files.byContent': 'Content', 'search.contentPh': 'Search inside documents',
  'files.contentEmpty': 'No document contains “{q}”.',
  'files.contentHint': 'Type a word or phrase to search the text of {n} indexed documents — Word, Excel, PowerPoint, PDF, Markdown and text.',
  'hits.count': { one: '1 match for “{q}”', other: '{n} matches for “{q}”' },
  'hits.none': '“{q}” isn’t in the part shown here — it may be on another sheet or further into the file.',
  'hits.prev': 'Previous match', 'hits.next': 'Next match',
});
Object.assign(I18N.zh, {
  'files.byName': '文件名', 'files.byContent': '内容', 'search.contentPh': '搜索文档内容',
  'files.contentEmpty': '没有文档包含“{q}”。',
  'files.contentHint': '输入词语，在 {n} 个已索引文档的正文中搜索——包括 Word、Excel、PowerPoint、PDF、Markdown 和文本文件。',
  'hits.count': '“{q}”共 {n} 处匹配',
  'hits.none': '“{q}”不在当前显示的部分中——可能在其他工作表或文件更靠后的位置。',
  'hits.prev': '上一处', 'hits.next': '下一处',
});
/* Bulk changes */
Object.assign(I18N.en, {
  'g.created': '{n} files created', 'g.modified': '{n} files modified', 'g.deleted': '{n} files deleted',
  'g.renamed': '{n} files renamed or moved', 'g.sep': ', ', 'g.expand': 'Show the files', 'g.collapse': 'Hide the files',
  'g.files': 'Files', 'g.restoreTo': 'Restore into a folder…', 'g.restoredTo': '{n} files copied into the folder.', 'g.restoreAll': 'Restore all {n} files', 'g.restoreTitle': 'Restore {n} files?',
  'g.restoreText': 'Each file goes back to where it was. If a file with that name exists there again, a “(restored …)” copy is saved next to it instead.',
  'g.restored': 'Restored {n} files.', 'g.failed': '{n} could not be restored (no full copy was kept).',
});
Object.assign(I18N.zh, {
  'g.created': '新建了 {n} 个文件', 'g.modified': '修改了 {n} 个文件', 'g.deleted': '删除了 {n} 个文件',
  'g.renamed': '重命名或移动了 {n} 个文件', 'g.sep': '、', 'g.expand': '展开文件列表', 'g.collapse': '收起文件列表',
  'g.files': '文件', 'g.restoreTo': '恢复到其他文件夹…', 'g.restoredTo': '已将 {n} 个文件复制到该文件夹。', 'g.restoreAll': '全部恢复（{n} 个文件）', 'g.restoreTitle': '恢复 {n} 个文件？',
  'g.restoreText': '每个文件都会回到原来的位置；如果该位置又有了同名文件，则在旁边另存为“（已恢复 …）”副本。',
  'g.restored': '已恢复 {n} 个文件。', 'g.failed': '{n} 个文件无法恢复（没有保存完整副本）。',
});
/* Retention */
Object.assign(I18N.en, {
  'set.keepDays': 'Keep history (days)', 'set.keepDaysHint': 'Older changes are forgotten. 0 = keep forever.',
  'set.maxStorage': 'Storage limit (GB)',
  'set.maxStorageHint': 'Above this, full copies of the oldest versions are removed — their text and the change list stay. 0 = no limit.',
});
Object.assign(I18N.zh, {
  'set.keepDays': '历史保留天数', 'set.keepDaysHint': '更早的变更记录会被删除。0 表示永久保留。',
  'set.maxStorage': '存储上限 (GB)',
  'set.maxStorageHint': '超过上限时，会删除最早版本的完整副本，但保留其文本和变更记录。0 表示不限制。',
});
/* Instant detection, notifications */
Object.assign(I18N.en, {
  'status.liveInstant': 'Live · {files} files · instant',
  'scope.detection': 'Detection', 'scope.instant': 'Instant', 'scope.polling': 'Every {s}s', 'scope.rescan': 'Full rescan',
  'set.interval': 'Full rescan interval',
  'set.intervalHint': 'Changes are picked up instantly through Windows change notifications. A full rescan also runs at this interval as a safety net (for example for network drives, where notifications are not available). While notifications work, it runs at most every 5 minutes to save power.',
  'set.notify': 'Desktop notifications', 'set.notifyHint': 'Shown from the tray icon. Bursts of changes are grouped into one notification.',
  'notify.off': 'Off', 'notify.deleted': 'Deleted files', 'notify.all': 'All changes',
  'notify.saved': 'Notification setting saved.',
});
Object.assign(I18N.zh, {
  'status.liveInstant': '实时 · {files} 个文件 · 即时检测',
  'scope.detection': '检测方式', 'scope.instant': '即时', 'scope.polling': '每 {s} 秒', 'scope.rescan': '完整扫描',
  'set.interval': '完整扫描间隔',
  'set.intervalHint': '通过 Windows 的变更通知，改动会被即时发现。另外每隔这段时间进行一次完整扫描作为保障（例如不支持通知的网络驱动器）。在通知正常工作时，为节省电量最多每 5 分钟扫描一次。',
  'set.notify': '桌面通知', 'set.notifyHint': '由托盘图标显示。短时间内的多处变更会合并为一条通知。',
  'notify.off': '关闭', 'notify.deleted': '删除文件时', 'notify.all': '所有变更',
  'notify.saved': '通知设置已保存。',
});
// Version licenses (updates)
Object.assign(I18N.en, {
  'app.name': 'DeskTrace', 'upd.badge': 'Update {v}', 'upd.title': 'A new version is available: {v}',
  'upd.lead': 'DeskTrace found a license for version <b>{v}</b> (you have {cur}).',
  'upd.from': 'Found in', 'upd.released': 'Released {d}', 'upd.notes': 'What is new',
  'upd.keep': 'Your change history, snapshots and settings are kept. Updating takes a few seconds; the window reopens by itself.',
  'upd.now': 'Update now', 'upd.later': 'Later',
  'upd.laterHint': 'You will be asked again the next time you open DeskTrace.',
  'upd.cannot': 'This copy is not an installed one (it runs from a source folder), so it cannot update itself. Use the installer instead.',
  'upd.working': 'Updating to version {v}…', 'upd.workingText': 'DeskTrace closes, installs the new version and reopens in a few seconds.',
  'upd.done': 'DeskTrace was updated from version {from} to <b>{to}</b>.',
  'upd.failed': 'The update to version {to} did not succeed ({err}). Version {from} is still installed.',
  'upd.none': 'Up to date. To update later, put a DeskTrace version license (<span class="mono">.dtlicense</span>) into a monitored folder, e.g. the Desktop.',
  'upd.section': 'Updates', 'upd.check': 'Choose license file…',
  'upd.rejected': 'A license file was found but cannot be used: {path} ({why})',
  'upd.why.signature': 'not a genuine DeskTrace license', 'upd.why.damaged': 'the file is damaged',
  'upd.why.contents': 'its contents were changed', 'upd.why.product': 'not for DeskTrace',
  'upd.why.too-old': 'this version is too old for it — use the installer', 'upd.why.not-newer': 'not newer than this version',
  'err.not-installed': 'Only an installed copy can update itself.', 'err.none': 'No update is waiting.',
});
Object.assign(I18N.zh, {
  'app.name': '桌迹', 'upd.badge': '更新 {v}', 'upd.title': '有新版本可用：{v}',
  'upd.lead': '桌迹 发现了 <b>{v}</b> 版的版本许可（当前为 {cur}）。',
  'upd.from': '文件位置', 'upd.released': '发布于 {d}', 'upd.notes': '新内容',
  'upd.keep': '变更历史、快照和设置都会保留。更新只需几秒钟，窗口会自动重新打开。',
  'upd.now': '立即更新', 'upd.later': '稍后',
  'upd.laterHint': '下次打开 桌迹 时会再次提示。',
  'upd.cannot': '当前副本不是安装版（从源代码文件夹运行），无法自行更新。请使用安装程序。',
  'upd.working': '正在更新到 {v} 版…', 'upd.workingText': '桌迹 会关闭、安装新版本，并在几秒钟后重新打开。',
  'upd.done': '桌迹 已从 {from} 版更新到 <b>{to}</b> 版。',
  'upd.failed': '更新到 {to} 版未成功（{err}）。仍在使用 {from} 版。',
  'upd.none': '已是最新版本。以后更新时，只需把 桌迹 版本许可文件（<span class="mono">.dtlicense</span>）放进被监控的文件夹（例如桌面）。',
  'upd.section': '更新', 'upd.check': '选择许可文件…',
  'upd.rejected': '发现了许可文件，但无法使用：{path}（{why}）',
  'upd.why.signature': '不是正版 桌迹 许可', 'upd.why.damaged': '文件已损坏',
  'upd.why.contents': '内容被改动过', 'upd.why.product': '不是 桌迹 的许可',
  'upd.why.too-old': '当前版本太旧，请使用安装程序', 'upd.why.not-newer': '不比当前版本新',
  'err.not-installed': '只有安装版才能自行更新。', 'err.none': '没有待安装的更新。',
});
// Notes, pause / do-not-disturb, Explorer menu, ignored folders, diagnostics, shortcuts
Object.assign(I18N.en, {
  'note.add': 'Add note', 'note.edit': 'Edit note', 'note.ph': 'What is this version? e.g. "sent to the client", "before restructuring"',
  'note.save': 'Save note', 'note.remove': 'Remove', 'note.saved': 'Note saved.', 'note.removed': 'Note removed.',
  'note.label': 'Note', 'note.keep': 'Versions with a note are never cleaned up automatically.',
  'search.withNotes': 'Search name, path or note', 'ins.total': { one: '{nf} change in the last 30 days', other: '{nf} changes in the last 30 days' },
  
  'pause.30': 'For 30 minutes', 'pause.120': 'For 2 hours', 'pause.indef': 'Until I resume',
  'status.pausedUntil': 'Paused until {t}',
  'set.shell': 'Explorer right-click menu', 'set.shellHint': 'Adds "DeskTrace: show history" to the right-click menu of every file.',
  'shell.on': 'Added to the Explorer right-click menu.', 'shell.off': 'Removed from the Explorer right-click menu.',
  'set.mute': 'Do not disturb', 'set.muteHint': 'Silences desktop notifications for a while; changes are still recorded.',
  'mute.off': 'Off', 'mute.60': '1 hour', 'mute.tomorrow': 'Until 8:00 tomorrow', 'mute.until': 'Silent until {t}',
  'set.exPaths': 'Ignored folders', 'set.exPathsHint': 'Changes inside these folders are not recorded.', 'set.exPathsNone': 'None — use "Ignore folder" on a change to add one.',
  'ign.btn': 'Ignore folder', 'ign.title': 'Ignore this folder?',
  'ign.text': 'Changes inside {dir} will no longer be recorded. Its earlier history stays. You can undo this in Settings.',
  'ign.ok': 'Ignore folder', 'ign.done': 'Folder ignored.',
  'diag.title': 'Diagnostics', 'diag.version': 'Version', 'diag.uptime': 'Running for', 'diag.detect': 'Instant detection',
  'diag.files': 'Files watched', 'diag.scans': 'Scans', 'diag.scanMs': 'Last full / quick scan', 'diag.events': 'Recorded changes',
  'diag.indexed': 'Documents in the search index', 'diag.db': 'Database size', 'diag.snapshots': 'Snapshots',
  'diag.errors': 'Recent problems in the log', 'diag.noErrors': 'None.', 'diag.yes': 'On', 'diag.no': 'Off', 'diag.copy': 'Copy report',
  'diag.copied': 'Diagnostics copied to the clipboard.',
  'diag.use': 'Background use', 'diag.useV': '{cpu} of CPU time since start · {mem} MB of memory · {io} MB read and written',
  'diag.nextFull': 'Next safety rescan', 'diag.saver': 'Power saver',
  'diag.saverBattery': 'On battery: indexing and comparing large files wait until the PC is plugged in',
  'diag.saverBusy': 'A full-screen game, video or presentation is on: indexing and comparing large files wait',
  'diag.saverOff': 'Not needed right now',
  'hide.dup': 'Not duplicates', 'hide.dupHint': 'Hide this set from Duplicates, for copies you keep on purpose',
  'hide.dupDone': 'Hidden from Duplicates.', 'hide.dupBack': 'Shown in Duplicates again.',
  'hide.dupCount': { one: '1 set marked as not duplicates.', other: '{nf} sets marked as not duplicates.' }, 'hide.dupShown': 'All hidden sets are shown again.',
  'hide.wrCount': { one: '1 document hidden from Writing.', other: '{nf} documents hidden from Writing.' }, 
  'hide.showAgain': 'Show them again', 'hide.undo': 'Undo',
  'folder.only': 'Changes in this folder', 'notes.filter': 'Only versions with a note', 'day.pick': 'Go to a day',
  'diag.disk': 'Free space for the history', 'diag.diskLow': 'below 1 GB: changes are still recorded, but no new copies are kept',
  'page.changes': 'File changes', 'page.files': 'All files',
  'help.find': 'Search (also Ctrl+F)', 'help.refresh': 'Refresh', 'help.settings': 'Settings', 'help.close': 'Close the window (keeps watching)',
});
Object.assign(I18N.zh, {
  'note.add': '添加备注', 'note.edit': '编辑备注', 'note.ph': '这个版本是什么？例如“已发给客户”“重构之前”',
  'note.save': '保存备注', 'note.remove': '删除', 'note.saved': '备注已保存。', 'note.removed': '备注已删除。',
  'note.label': '备注', 'note.keep': '带备注的版本不会被自动清理。',
  'search.withNotes': '搜索文件名、路径或备注', 
  
  'pause.30': '30 分钟', 'pause.120': '2 小时', 'pause.indef': '直到手动继续',
  'status.pausedUntil': '已暂停，{t} 自动继续',
  'set.shell': '资源管理器右键菜单', 'set.shellHint': '在每个文件的右键菜单中添加“桌迹：查看历史版本”。',
  'shell.on': '已添加到资源管理器右键菜单。', 'shell.off': '已从资源管理器右键菜单移除。',
  'set.mute': '勿扰', 'set.muteHint': '暂时不显示桌面通知；变更仍会被记录。',
  'mute.off': '关闭', 'mute.60': '1 小时', 'mute.tomorrow': '到明早 8:00', 'mute.until': '静音到 {t}',
  'set.exPaths': '已忽略的文件夹', 'set.exPathsHint': '这些文件夹中的变更不会被记录。', 'set.exPathsNone': '无——在某条变更上点“忽略文件夹”即可添加。',
  'ign.btn': '忽略文件夹', 'ign.title': '忽略这个文件夹？',
  'ign.text': '{dir} 中的变更将不再被记录，已有的历史会保留。可以在设置中撤销。',
  'ign.ok': '忽略文件夹', 'ign.done': '已忽略该文件夹。',
  'diag.title': '诊断信息', 'diag.version': '版本', 'diag.uptime': '已运行', 'diag.detect': '即时检测',
  'diag.files': '监控的文件', 'diag.scans': '扫描次数', 'diag.scanMs': '上次完整 / 快速扫描', 'diag.events': '已记录的变更',
  'diag.indexed': '搜索索引中的文档', 'diag.db': '数据库大小', 'diag.snapshots': '快照',
  'diag.errors': '日志中最近的问题', 'diag.noErrors': '无。', 'diag.yes': '开', 'diag.no': '关', 'diag.copy': '复制报告',
  'diag.copied': '诊断信息已复制到剪贴板。',
  'diag.use': '后台占用', 'diag.useV': '启动以来 CPU 时间 {cpu} · 内存 {mem} MB · 磁盘读写 {io} MB',
  'diag.nextFull': '下次保底重扫', 'diag.saver': '省电模式',
  'diag.saverBattery': '正在使用电池：建立索引和比较大文件会等到接通电源后再进行',
  'diag.saverBusy': '正在运行全屏游戏、视频或演示：建立索引和比较大文件会稍后进行',
  'diag.saverOff': '当前无需启用',
  'hide.dup': '不是重复', 'hide.dupHint': '在“重复文件”中隐藏这一组，适用于有意保留的副本',
  'hide.dupDone': '已从“重复文件”中隐藏。', 'hide.dupBack': '已重新显示在“重复文件”中。',
  'hide.dupCount': '已有 {nf} 组被标记为不是重复。', 'hide.dupShown': '所有隐藏的组已重新显示。',
  'hide.showAgain': '重新显示', 'hide.undo': '撤销',
  'folder.only': '此文件夹中的变更', 'notes.filter': '只看带备注的版本', 'day.pick': '跳到某一天',
  'diag.disk': '历史记录可用空间', 'diag.diskLow': '不足 1 GB：变更仍会记录，但不再保存新的副本',
  'page.changes': '文件变更', 'page.files': '所有文件',
  'help.find': '搜索（也可按 Ctrl+F）', 'help.refresh': '刷新', 'help.settings': '设置', 'help.close': '关闭窗口（继续监控）',
});
// 1.6.1: filters, keys, versions
Object.assign(I18N.en, {
  'notes.emptyTitle': 'No notes yet',
  'notes.emptyText': 'Select a change and press N (or Add note) to label that version, e.g. "sent to the client". Noted versions are kept for good.',
  'notes.chip': 'With notes', 'range.yesterday': 'Yesterday',
  'day.count': { one: '{nf} change', other: '{nf} changes' }, 'btn.undo': 'Undo', 'ign.undone': 'The folder is watched again.',
  'key.copied': 'Path copied: {path}', 'pause.tomorrow': 'Until 8:00 tomorrow',
  'help.kinds': 'Show only created / modified / deleted / renamed', 'help.copy': 'Copy the path', 'help.reveal': 'Show in Explorer',
  'help.note': 'Add or edit the note', 'help.tabs': 'Previous / next tab', 'help.ends': 'First / last in the list',
  'help.export': 'Export to Excel', 'help.views': 'Changes / Files / Duplicates / Space / Writing',
  
  
  
  'ver.open': 'Open this version', 'ver.openTitle': 'Opens a read-only copy of this version in its program',
  'ver.save': 'Save as…', 'ver.saveTitle': 'Save this version under a name and place you choose',
  'ver.opened': 'Opened a read-only copy of this version.',
  'clean.title': 'Clean up now', 'clean.hint': 'Applies "Keep history" and "Storage limit" right away instead of waiting.',
  'clean.btn': 'Clean up', 'clean.done': 'Cleaned up: {n} old changes forgotten, {size} freed.',
});
Object.assign(I18N.zh, {
  'notes.emptyTitle': '还没有备注',
  'notes.emptyText': '选中一条变更后按 N（或点“添加备注”）给这个版本加上说明，例如“已发给客户”。带备注的版本会一直保留。',
  'notes.chip': '有备注的', 'range.yesterday': '昨天',
  'day.count': '{nf} 处变更', 'btn.undo': '撤销', 'ign.undone': '已恢复监控该文件夹。',
  'key.copied': '已复制路径：{path}', 'pause.tomorrow': '到明早 8:00',
  'help.kinds': '只看新建 / 修改 / 删除 / 重命名', 'help.copy': '复制路径', 'help.reveal': '在资源管理器中显示',
  'help.note': '添加或编辑备注', 'help.tabs': '上一个 / 下一个标签', 'help.ends': '列表的第一项 / 最后一项',
  'help.export': '导出到 Excel', 'help.views': '变更 / 文件 / 重复文件 / 空间占用 / 写作进度',
  
  
  
  'ver.open': '打开此版本', 'ver.openTitle': '用对应程序打开此版本的只读副本',
  'ver.save': '另存为…', 'ver.saveTitle': '把此版本保存到你选择的位置和文件名',
  'ver.opened': '已打开此版本的只读副本。',
  'clean.title': '立即清理', 'clean.hint': '立即按“保留历史”和“存储上限”清理，而不必等待。',
  'clean.btn': '清理', 'clean.done': '清理完成：忘记了 {n} 条旧变更，释放了 {size}。',
});
// Choosing among several versions; the five change levels
Object.assign(I18N.en, {
  'upd.badgeMany': '{n} updates', 'act.more': 'More', 'ver.replace': 'Replace current file with this version', 'ver.replaceTitle': 'Replace the current file?', 'ver.replaceText': 'The file gets this version\'s content. Its current content stays in DeskTrace, so you can switch back the same way.', 'ver.replaceOk': 'Replace', 'ver.replaced': 'The file now has this version\'s content.', 'err.noBackup': 'The current content has no snapshot, so the file was not replaced. Use Save as instead.', 'upd.whatsNewBtn': "What's new", 'upd.whatsNewTitle': "What's new in {v}", 'restoreAll.text': '{n} deleted files shown can be brought back', 'restoreAll.btn': 'Restore all {n}', 'files.changedOnly': 'Changed only', 'help.right': 'Right-click a change or file for its actions.', 'set.advanced': 'Advanced: snapshot and indexing size limits', 'upd.titleMany': '{n} new versions are available',
  'upd.leadMany': 'Licenses for several newer versions were found (you have {cur}). Choose the one to install — each includes everything before it.',
  'upd.latest': 'Latest', 'upd.nChanges': { one: '{n} change', other: '{n} changes' }, 'upd.install': 'Install version {v}',
  'upd.whatsNew': 'What this version brings',
  'lvl.5': 'New feature', 'lvl.4': 'Major improvement', 'lvl.3': 'Improvement', 'lvl.2': 'Polish', 'lvl.1': 'Fix',
  'lvl.hint5': 'Level 5: an entirely new feature', 'lvl.hint4': 'Level 4: a major improvement', 'lvl.hint3': 'Level 3: an improvement',
  'lvl.hint2': 'Level 2: polish', 'lvl.hint1': 'Level 1: a fix',
});
Object.assign(I18N.zh, {
  'upd.badgeMany': '{n} 个更新', 'act.more': '更多', 'ver.replace': '用此版本替换当前文件', 'ver.replaceTitle': '替换当前文件？',
  'ver.replaceText': '文件内容将变为此版本。当前内容仍保存在桌迹中，可以用同样的方法换回来。', 'ver.replaceOk': '替换', 'ver.replaced': '文件已恢复为此版本的内容。',
  'err.noBackup': '当前内容没有快照，因此未替换文件。请改用“另存为…”。', 'upd.whatsNewBtn': '新内容', 'upd.whatsNewTitle': '{v} 版的新内容', 'restoreAll.text': '列出的 {n} 个已删除文件可以恢复', 'restoreAll.btn': '全部恢复（{n} 个）', 'files.changedOnly': '只看有改动的', 'help.right': '右键单击变更或文件可使用其操作。', 'set.advanced': '高级：快照与索引的大小限制', 'upd.titleMany': '有 {n} 个新版本可用',
  'upd.leadMany': '发现了多个新版本的许可（当前为 {cur}）。请选择要安装的版本——每个版本都包含之前所有版本的内容。',
  'upd.latest': '最新', 'upd.nChanges': '{n} 项变化', 'upd.install': '安装 {v} 版',
  'upd.whatsNew': '此版本带来的内容',
  'lvl.5': '新功能', 'lvl.4': '重要改进', 'lvl.3': '改进', 'lvl.2': '体验优化', 'lvl.1': '修复',
  'lvl.hint5': '第 5 级：全新功能', 'lvl.hint4': '第 4 级：重要改进', 'lvl.hint3': '第 3 级：改进',
  'lvl.hint2': '第 2 级：体验优化', 'lvl.hint1': '第 1 级：修复',
});
// 1.7: Duplicates
Object.assign(I18N.en, {
  'dup.nav': 'Duplicates', 'page.dups': 'Duplicate files',
  'dup.sum': { one: '{nf} set of identical files · {size} could be freed', other: '{nf} sets of identical files · {size} could be freed' },
  'dup.emptyTitle': 'No duplicate files', 'dup.emptyText': 'Checked {n} files in the monitored folders by their content: none has an identical copy.',
  'dup.copies': { one: '{n} copy', other: '{n} copies' }, 'dup.each': '{size} each', 'dup.wasted': '{size} extra',
  'dup.title': '{n} identical copies', 'dup.free': '{size} could be freed', 'dup.newest': 'Newest',
  'dup.how': 'These files have exactly the same content. Keep the one you need and move the others to the Recycle Bin — you can put them back from there, and DeskTrace keeps their snapshots.',
  'dup.limit': 'Files are compared by their content; large files are checked in the background.', 'dup.checking': 'checking {n} large files…',
  'dup.recycle': 'Move to Recycle Bin', 'dup.recycleTitle': 'Move this copy to the Recycle Bin?',
  'dup.recycleText': 'The other identical copies stay where they are. You can restore this one from the Recycle Bin.',
  'dup.recycled': 'Moved to the Recycle Bin.', 'err.lastCopy': 'This is the last copy, so it was not removed.',
});
Object.assign(I18N.zh, {
  'dup.nav': '重复文件', 'page.dups': '重复文件',
  'dup.sum': '{nf} 组内容相同的文件 · 可释放 {size}',
  'dup.emptyTitle': '没有重复文件', 'dup.emptyText': '已按内容检查了监控文件夹中的 {n} 个文件：没有内容完全相同的副本。',
  'dup.copies': '{n} 份', 'dup.each': '每份 {size}', 'dup.wasted': '多占 {size}',
  'dup.title': '{n} 份相同的副本', 'dup.free': '可释放 {size}', 'dup.newest': '最新',
  'dup.how': '这些文件的内容完全相同。保留需要的一份，其余的可以移到回收站——之后可以从回收站还原，桌迹也会保留它们的快照。',
  'dup.limit': '按文件内容比较；大文件会在后台检查。', 'dup.checking': '正在检查 {n} 个大文件…',
  'dup.recycle': '移到回收站', 'dup.recycleTitle': '把这份副本移到回收站？',
  'dup.recycleText': '其他内容相同的副本保持不变。这一份可以从回收站还原。',
  'dup.recycled': '已移到回收站。', 'err.lastCopy': '这是最后一份，因此没有删除。',
});
// 1.7.1
Object.assign(I18N.en, {
  'dup.sortWasted': 'Most space', 'dup.sortCount': 'Most copies', 'dup.sortName': 'Name',
  'dup.keepNewest': { one: 'Keep the newest, recycle {n} other', other: 'Keep the newest, recycle {n} others' },
  'dup.keepTitle': { one: 'Recycle {n} copy?', other: 'Recycle {n} copies?' },
  'dup.keepText': 'All copies except the newest one go to the Recycle Bin. This one stays:',
  'dup.keptDone': { one: '{n} copy moved to the Recycle Bin.', other: '{n} copies moved to the Recycle Bin.' },
});
Object.assign(I18N.zh, {
  'dup.sortWasted': '占用最多', 'dup.sortCount': '副本最多', 'dup.sortName': '名称',
  'dup.keepNewest': '保留最新的，其余 {n} 份移到回收站', 'dup.keepTitle': '把 {n} 份副本移到回收站？',
  'dup.keepText': '除最新的一份外，其他副本都会移到回收站。保留的是：', 'dup.keptDone': '已将 {n} 份副本移到回收站。',
});
// 1.8: Space
Object.assign(I18N.en, {
  'sp.nav': 'Space', 'page.space': 'Space usage', 'sp.overview': 'Overview', 'sp.sum': '{size} in {n} files',
  'sp.biggest': 'Biggest files', 'sp.inFiles': 'in {n} files', 'sp.grew': 'grew by {size} in 30 days', 'sp.shrank': 'shrank by {size} in 30 days',
  'sp.roots': 'Monitored folders', 'sp.all': 'All folders', 'sp.staleTitle': '{size} not changed for over a year', 'sp.staleText': '{n} files — click to list the biggest; often good to archive or clean up', 'sp.staleChip': 'Not changed for a year', 'sp.foldersIn': 'Biggest folders (click to look inside)', 'sp.drill': 'Show what is inside', 'sp.noSub': 'No subfolders.', 'sp.byType': 'By file type', 'sp.typeHint': 'click a type to list its biggest files', 'sp.folders': 'Biggest folders (click to open)',
});
Object.assign(I18N.zh, {
  'sp.nav': '空间占用', 'page.space': '空间占用', 'sp.overview': '概览', 'sp.sum': '{n} 个文件共 {size}',
  'sp.biggest': '最大的文件', 'sp.inFiles': '共 {n} 个文件', 'sp.grew': '30 天内增加了 {size}', 'sp.shrank': '30 天内减少了 {size}',
  'sp.roots': '监控的文件夹', 'sp.all': '全部文件夹', 'sp.staleTitle': '{size} 超过一年未改动', 'sp.staleText': '{n} 个文件——点击列出其中最大的；通常适合归档或清理', 'sp.staleChip': '一年未改动', 'sp.foldersIn': '最大的文件夹（点击查看内部）', 'sp.drill': '查看里面的内容', 'sp.noSub': '没有子文件夹。', 'sp.byType': '按文件类型', 'sp.typeHint': '点击某个类型，列出该类型最大的文件', 'sp.folders': '最大的文件夹（点击打开）',
});
// 1.9: Alert rules
Object.assign(I18N.en, {
  
  
  'rule.hits': { one: 'Triggered once · last {t}', other: 'Triggered {nf} times · last {t}' }, 
  
  
  
  'rule.preview': { one: 'In the last 30 days this rule would have triggered once.', other: 'In the last 30 days this rule would have triggered {nf} times.' },
  
});
Object.assign(I18N.zh, {
  
  
  
  
  
  
  
  
  
  
  
  
});

// 2.0: Writing progress
Object.assign(I18N.en, {
  
  
  
  
  
  
  
});
Object.assign(I18N.zh, {
  
  
  
  
  
  
  
});

// 2.1: Folder time travel
Object.assign(I18N.en, {
  'st.btn': 'What uses the space', 'st.title': 'What uses the history space', 'st.lead': 'Kept versions take {size}. These files have the biggest share. Forgetting old versions keeps the newest one and any with a note.', 'st.versions': { one: '{n} kept version', other: '{n} kept versions' }, 'st.forget': 'Forget old versions', 'st.forgetTitle': 'Forget the old versions of this file?', 'st.forgetText': 'Its newest version and any version with a note are kept. This cannot be undone.', 'st.forgotten': 'Forgot {n} old versions, {size} freed.', 'st.none': 'No kept versions yet.',
  
  'tt.missing': { one: '{n} file cannot be rebuilt (that version was not kept).', other: '{n} files cannot be rebuilt (those versions were not kept).' },
  
  
  'err.nothingThen': 'Nothing could be rebuilt for that moment.',
});
Object.assign(I18N.zh, {
  'st.btn': '查看空间用途', 'st.title': '历史记录的空间用途', 'st.lead': '保留的版本共占用 {size}。以下文件占用最多。忘记旧版本时会保留最新的版本以及带备注的版本。', 'st.versions': '保留了 {n} 个版本', 'st.forget': '忘记旧版本', 'st.forgetTitle': '忘记此文件的旧版本？', 'st.forgetText': '最新的版本和带备注的版本会保留。此操作无法撤销。', 'st.forgotten': '已忘记 {n} 个旧版本，释放了 {size}。', 'st.none': '还没有保留的版本。',
  
  
  
  
  
  
  'err.nothingThen': '那个时刻没有可以重建的内容。',
});

/* drive space cleaner (2.2.0) */
Object.assign(I18N.en, {
  'cl.nav': 'Clean up', 'cl.sub': 'All drives of this PC — scanning only reads; nothing is deleted until you click', 'page.clean': 'Clean up a drive', 'cl.localDisk': 'Local disk', 'cl.removable': 'Removable drive',
  'cl.free': '{free} free of {total}', 'cl.freeBig': '{size} free', 'cl.ofTotal': 'of {total}', 'cl.inFiles': 'in {n} files',
  'cl.scanning': 'Reading the drive… {n} files ({size}) so far', 'cl.scanned': 'Read {n} files ({size}) in {s} s.', 'cl.rescan': 'Scan again',
  'cl.safe': 'Can be cleaned', 'cl.safeSum': '{size} in total', 'cl.looking': 'Looking for things to clean…', 'cl.nothing': 'Nothing to clean on this drive.',
  'cl.big': 'Biggest files', 'cl.readingBig': 'The biggest files appear when the drive has been read.',
  'cl.folders': 'What takes up the space (estimated)', 'cl.drillHint': 'click a folder to look inside', 'cl.types': 'By file type (estimated)', 'cl.here': 'Biggest files in this folder',
  'cl.up': 'Up', 'cl.other': 'Other types', 'cl.used': 'Used', 'cl.freeL': 'Free', 'cl.cleanable': 'Can be cleaned',
  'cl.gain': 'Cleaning the items on the left frees about {size}.', 'cl.count': { one: '1 file', other: '{n} files' },
  'cl.clean': 'Clean', 'cl.empty': 'Empty', 'cl.cleaning': 'Cleaning…', 'cl.cleaned': 'Freed {size}.',
  'cl.cleanedSome': 'Freed {size}. {n} files were in use or protected and were left alone.',
  'cl.recycleFile': 'Move to Recycle Bin', 'cl.recycled': '{name} moved to the Recycle Bin. Empty the Recycle Bin (under “Can be cleaned”) to get its {size} back.',
  'cl.how.delete': 'Deleted for good', 'cl.how.recycle': 'Goes to the Recycle Bin', 'cl.how.empty': 'Cannot be undone', 'cl.how.admin': 'Needs administrator rights',
  'cl.openWin': 'Open Windows Disk Cleanup', 'cl.openApps': 'Uninstall a program…', 'cl.ifDelete': 'If you delete it:',
  'cl.note': 'Sizes are what the files hold; Windows folders that share files (e.g. WinSxS) can look bigger than they are. Links and junctions are not followed.',
  'cl.level.system': 'Never delete', 'cl.level.program': 'Uninstall instead', 'cl.level.caution': 'Careful', 'cl.level.personal': 'Your file', 'cl.level.safe': 'Safe to delete',
  'cl.item.temp': 'Temporary files', 'cl.item.wintemp': 'Windows temporary files', 'cl.item.edge': 'Microsoft Edge cache', 'cl.item.chrome': 'Google Chrome cache',
  'cl.item.firefox': 'Firefox cache', 'cl.item.crash': 'Crash reports', 'cl.item.thumbs': 'Picture thumbnails', 'cl.item.devcache': 'Developer tool caches (pip, npm, Yarn)',
  'cl.item.installers': 'Old installers in Downloads', 'cl.item.winupdate': 'Windows Update downloads', 'cl.item.recycle': 'Recycle Bin',
  'cl.why.temp': 'Files programs left behind while working. Safe to delete; files changed in the last hour and files in use are skipped.',
  'cl.why.wintemp': 'Temporary files of Windows and installers. Safe to delete; files in use and files that need administrator rights are skipped.',
  'cl.why.edge': 'Copies of websites kept so they load faster. Pages load a little slower the first time; you stay signed in, and history, passwords and bookmarks are not touched. Close the browser first to free everything.',
  'cl.why.chrome': 'Copies of websites kept so they load faster. Pages load a little slower the first time; you stay signed in, and history, passwords and bookmarks are not touched. Close the browser first to free everything.',
  'cl.why.firefox': 'Copies of websites kept so they load faster. Pages load a little slower the first time; you stay signed in, and history, passwords and bookmarks are not touched.',
  'cl.why.crash': 'Reports saved after a program crashed. Nothing needs them later; safe to delete.',
  'cl.why.thumbs': 'Small previews Explorer keeps for pictures and videos. Explorer makes them again when needed, so folders full of pictures open a little slower once.',
  'cl.why.devcache': 'Packages pip, npm or Yarn downloaded earlier. They are downloaded again the next time a project needs them.',
  'cl.why.installers': 'Setup programs (.exe, .msi) in Downloads, untouched for 30 days. They go to the Recycle Bin; you can download them again if you need them.',
  'cl.why.winupdate': 'Update files Windows already installed. Only Windows Disk Cleanup, with administrator rights, removes them safely.',
  'cl.why.recycle': 'Files you deleted earlier. Emptying the Recycle Bin removes them for good — they can no longer be restored.',
  'cl.file.pagefile': 'Windows’ paging file, used as extra memory. Never delete it; change its size in System settings › Advanced system settings if needed.',
  'cl.file.hiberfil': 'Used for hibernation and fast startup. To remove it, turn hibernation off (powercfg /h off) instead of deleting it.',
  'cl.file.windows': 'Part of Windows. Deleting it can stop Windows or programs from working.',
  'cl.file.program': 'Part of an installed program. Uninstall the program instead (Settings › Apps), or it may stop working.',
  'cl.file.programdata': 'Shared data of installed programs. Remove it from within the program or by uninstalling it.',
  'cl.file.appdata': 'A program’s own data (settings, caches, saved games, chats). Deleting it may reset or break that program — only if you know what it is.',
  'cl.file.installer': 'A setup program you downloaded. You can download it again if needed.',
  'cl.file.archive': 'An archive or disk image. Keep it if you still need what is inside.',
  'cl.file.vm': 'A virtual machine’s disk. Deleting it destroys that virtual machine and everything in it.',
  'cl.file.media': 'One of your pictures, videos or songs. It goes to the Recycle Bin, where you can restore it until the bin is emptied.',
  'cl.file.document': 'One of your documents. It goes to the Recycle Bin, where you can restore it until the bin is emptied.',
  'cl.file.program_file': 'A program file outside the Programs folders (often a portable app or a download). It goes to the Recycle Bin.',
  'cl.file.other': 'It goes to the Recycle Bin, where you can restore it until the bin is emptied; the space comes back once the bin is emptied.',
});
Object.assign(I18N.zh, {
  'cl.nav': '空间清理', 'cl.sub': '这台电脑的所有磁盘——扫描只读取，点击之前不会删除任何东西', 'page.clean': '清理磁盘空间', 'cl.localDisk': '本地磁盘', 'cl.removable': '可移动磁盘',
  'cl.free': '可用 {free}，共 {total}', 'cl.freeBig': '可用 {size}', 'cl.ofTotal': '共 {total}', 'cl.inFiles': '共 {n} 个文件',
  'cl.scanning': '正在读取磁盘…已读取 {n} 个文件（{size}）', 'cl.scanned': '已读取 {n} 个文件（{size}），用时 {s} 秒。', 'cl.rescan': '重新扫描',
  'cl.safe': '可以清理', 'cl.safeSum': '共 {size}', 'cl.looking': '正在查找可清理的内容…', 'cl.nothing': '这个磁盘上没有需要清理的内容。',
  'cl.big': '最大的文件', 'cl.readingBig': '磁盘读取完成后会显示最大的文件。',
  'cl.folders': '空间都用在了哪里（估算）', 'cl.drillHint': '点击文件夹查看里面', 'cl.types': '按文件类型（估算）', 'cl.here': '此文件夹中最大的文件',
  'cl.up': '上一级', 'cl.other': '其他类型', 'cl.used': '已用', 'cl.freeL': '可用', 'cl.cleanable': '可清理',
  'cl.gain': '清理左侧的项目约可释放 {size}。', 'cl.count': '{n} 个文件',
  'cl.clean': '清理', 'cl.empty': '清空', 'cl.cleaning': '正在清理…', 'cl.cleaned': '已释放 {size}。',
  'cl.cleanedSome': '已释放 {size}。有 {n} 个文件正在使用或受保护，已跳过。',
  'cl.recycleFile': '移到回收站', 'cl.recycled': '{name} 已移到回收站。清空回收站（在“可以清理”中）后才能收回 {size} 空间。',
  'cl.how.delete': '永久删除', 'cl.how.recycle': '移到回收站', 'cl.how.empty': '无法撤销', 'cl.how.admin': '需要管理员权限',
  'cl.openWin': '打开 Windows 磁盘清理', 'cl.openApps': '卸载程序…', 'cl.ifDelete': '删除后：',
  'cl.note': '大小按文件内容计算；共享文件的 Windows 文件夹（如 WinSxS）看起来会比实际更大。不会跟随链接和联接点。',
  'cl.level.system': '切勿删除', 'cl.level.program': '请改为卸载', 'cl.level.caution': '谨慎', 'cl.level.personal': '你的文件', 'cl.level.safe': '可安全删除',
  'cl.item.temp': '临时文件', 'cl.item.wintemp': 'Windows 临时文件', 'cl.item.edge': 'Microsoft Edge 缓存', 'cl.item.chrome': 'Google Chrome 缓存',
  'cl.item.firefox': 'Firefox 缓存', 'cl.item.crash': '崩溃报告', 'cl.item.thumbs': '图片缩略图', 'cl.item.devcache': '开发工具缓存（pip、npm、Yarn）',
  'cl.item.installers': '下载文件夹中的旧安装程序', 'cl.item.winupdate': 'Windows 更新下载文件', 'cl.item.recycle': '回收站',
  'cl.why.temp': '程序工作时留下的文件。可以安全删除；最近一小时内修改过的文件和正在使用的文件会被跳过。',
  'cl.why.wintemp': 'Windows 和安装程序的临时文件。可以安全删除；正在使用或需要管理员权限的文件会被跳过。',
  'cl.why.edge': '为加快打开速度而保存的网页副本。网页第一次打开会稍慢；不会退出登录，历史记录、密码和收藏夹都不受影响。先关闭浏览器可释放全部空间。',
  'cl.why.chrome': '为加快打开速度而保存的网页副本。网页第一次打开会稍慢；不会退出登录，历史记录、密码和书签都不受影响。先关闭浏览器可释放全部空间。',
  'cl.why.firefox': '为加快打开速度而保存的网页副本。网页第一次打开会稍慢；不会退出登录，历史记录、密码和书签都不受影响。',
  'cl.why.crash': '程序崩溃后保存的报告。之后不再需要，可以安全删除。',
  'cl.why.thumbs': '资源管理器为图片和视频保存的小预览图。需要时会重新生成，图片很多的文件夹第一次打开会稍慢。',
  'cl.why.devcache': 'pip、npm 或 Yarn 之前下载的软件包。项目下次需要时会重新下载。',
  'cl.why.installers': '下载文件夹中 30 天未动过的安装程序（.exe、.msi）。会移到回收站；需要时可以重新下载。',
  'cl.why.winupdate': 'Windows 已经安装过的更新文件。只有使用管理员权限的 Windows 磁盘清理才能安全删除。',
  'cl.why.recycle': '你之前删除的文件。清空回收站会永久删除它们，之后无法再恢复。',
  'cl.file.pagefile': 'Windows 的分页文件，用作额外内存。切勿删除；如有需要，可在“高级系统设置”中调整大小。',
  'cl.file.hiberfil': '用于休眠和快速启动。要去掉它，请关闭休眠（powercfg /h off），不要直接删除。',
  'cl.file.windows': 'Windows 的组成部分。删除后 Windows 或程序可能无法正常工作。',
  'cl.file.program': '已安装程序的一部分。请改为卸载该程序（设置 › 应用），否则程序可能无法运行。',
  'cl.file.programdata': '已安装程序的共享数据。请在程序中删除，或卸载该程序。',
  'cl.file.appdata': '某个程序自己的数据（设置、缓存、存档、聊天记录）。删除后该程序可能被重置或出错——只在你清楚它是什么时删除。',
  'cl.file.installer': '你下载的安装程序。需要时可以重新下载。',
  'cl.file.archive': '压缩包或磁盘映像。如果还需要里面的内容，请保留。',
  'cl.file.vm': '虚拟机的磁盘。删除后该虚拟机及其中的一切都会丢失。',
  'cl.file.media': '你自己的图片、视频或音乐。会移到回收站，清空回收站之前都可以恢复。',
  'cl.file.document': '你自己的文档。会移到回收站，清空回收站之前都可以恢复。',
  'cl.file.program_file': '“程序”文件夹之外的程序文件（通常是便携软件或下载的文件）。会移到回收站。',
  'cl.file.other': '会移到回收站，清空回收站之前都可以恢复；清空回收站后才会收回空间。',
});

/* after DeepSeek's reviews of 2.1.0 / 2.2.0 (2.3.0): tabs, tick-and-confirm cleaning, honest wording */
Object.assign(I18N.en, {
  'tab.changes': 'Changes', 'cl.tabDrive': 'Drive', 'sp.tab': 'Watched folders',
  'cl.stop': 'Stop', 'cl.stopped': 'Stopped after {n} files ({size}); the lists show what was read so far.',
  'cl.skipped': '{n} folders could not be read · {m} online-only files take no space here',
  'cl.skippedWhy': 'Folders without permission or reserved by Windows are left out; online-only cloud files are counted as 0 because nothing of them is on this disk.',
  'cl.count': { one: '1 file', other: '{nf} files' },
  'cl.picked': { one: '1 item ticked', other: '{n} items ticked' }, 'cl.freeNow': 'frees {size} right away', 'cl.freeLater': '{size} more once the Recycle Bin is emptied',
  'cl.cleanPicked': 'Clean ticked items', 'cl.gain2': 'Can be freed: {now} right away, {later} more via the Recycle Bin.',
  'cl.online': 'Free up space (keep online only)', 'cl.onlineDone': 'Asked the cloud service to free {size} on this disk; the file stays in the cloud.',
  'cl.hist.none': 'Not in a folder DeskTrace watches: DeskTrace has no copy of it.',
  'cl.hist.kept': 'DeskTrace keeps a copy ({n} versions): after deleting you can still restore it from Changes for {days} days, even once the Recycle Bin is emptied.',
  'cl.hist.big': 'DeskTrace watches this file but keeps no copy (it is over the snapshot size limit): once deleted and the Recycle Bin emptied, it is gone.',
  'cl.hist.noCopy': 'DeskTrace watches this file but has no copy of it yet.',
  'cl.confirmTitle': 'Clean these items?', 'cl.irreversible': 'Deleted for good — cannot be undone', 'cl.start': 'Start cleaning',
  'cl.confirmHint': 'Files that are in use or changed within the last hour are skipped; the result lists what was skipped.',
  'cl.resultTitle': 'Done — {size} freed', 'cl.r.freed': 'Freed', 'cl.r.done': 'Files', 'cl.r.skipped': 'Skipped',
  'cl.skippedHint': 'Skipped files were in use, changed within the hour or protected; close the program using them and clean again.',
  'cl.inBinHint': 'Items moved to the Recycle Bin can be restored from there; their space comes back once the Recycle Bin is emptied.',
  'cl.openBin': 'Open Recycle Bin', 'cl.emptyTitle': 'Empty the Recycle Bin?',
  'cl.emptyText': 'The Recycle Bin holds {n} files ({size}) — files you deleted earlier. Look inside first if you are not sure. Emptying deletes them for good: they can no longer be restored.',
  'cl.sure': 'I understand this cannot be undone', 'cl.permTitle': 'This would be deleted for good',
  'cl.noBinText': 'This drive has no Recycle Bin (or it is switched off), so {name} ({size}) cannot be moved there. Deleting it now removes it for good.',
  'cl.tooBigText': '{name} ({size}) is bigger than this drive’s Recycle Bin can hold, so Windows would delete it for good instead of moving it there.',
  'cl.deletePerm': 'Delete for good', 'cl.deletedPerm': '{name} deleted for good ({size} freed).',
  'cl.recycled': '{name} moved to the Recycle Bin — restore it from there if needed. Its {size} come back once the Recycle Bin is emptied.',
  'cl.level.cloud': 'Synced to the cloud', 'cl.level.inapp': 'Clean up in the app',
  'cl.file.cloud': 'In a folder a cloud service keeps in sync (e.g. OneDrive): deleting it here also deletes it in the cloud. Use “Free up space” to keep it online only instead.',
  'cl.file.game': 'Part of an installed game. Uninstall or move it in its launcher (Steam, Epic, …); deleting files breaks the game and it has to be downloaded again.',
  'cl.file.chat': 'Chat history or files received in WeChat / QQ / other messengers. They cannot be downloaded again — use the app’s own storage cleanup.',
  'cl.file.pst': 'An Outlook data file holding your mail. Deleting it loses those emails; archive or clean it up in Outlook.',
  'cl.file.ost': 'Outlook’s offline copy of a mailbox. Outlook rebuilds it by downloading all mail again, which can take hours.',
  'cl.file.git': 'Part of a Git repository. Deleting it damages the repository and its history.',
  'cl.file.winold': 'Your previous Windows, kept to go back after an upgrade. Windows removes it by itself after 10 days; to remove it earlier, use Windows Disk Cleanup.',
  'cl.item.memdump': 'System memory dumps', 'cl.item.winold': 'Previous Windows installation (Windows.old)',
  'cl.why.memdump': 'Crash dumps Windows writes after a blue screen. Safe to delete unless someone is analysing the crash. Needs administrator rights.',
  'cl.why.winold': 'Your previous Windows, kept so you can go back for 10 days after an upgrade; removing it ends that option.',
  'cl.why.temp': 'Files programs left behind while working. Usually safe to delete; files changed in the last hour and files in use are skipped and listed.',
  'cl.why.wintemp': 'Temporary files of Windows and installers. Usually safe; files in use and files that need administrator rights are skipped and listed.',
  'cl.why.edge': 'Copies of websites kept so they load faster. Bookmarks, passwords and history are not deleted; a few websites may ask you to sign in again. Files the open browser is using are skipped — close it first to free everything.',
  'cl.why.chrome': 'Copies of websites kept so they load faster. Bookmarks, passwords and history are not deleted; a few websites may ask you to sign in again. Files the open browser is using are skipped — close it first to free everything.',
  'cl.why.firefox': 'Copies of websites kept so they load faster. Bookmarks, passwords and history are not deleted; a few websites may ask you to sign in again.',
  'cl.why.devcache': 'Global download caches of pip, npm and Yarn (not your projects). The next install or build has to fetch the packages again, which needs the internet — offline or private-registry setups may fail.',
  'cl.why.installers': 'Setup programs (.exe, .msi) in Downloads, untouched for 30 days. Only for installers you no longer need: portable tools and dead download links cannot be got back. They go to the Recycle Bin, so you can restore them.',
  'cl.why.recycle': 'Files you deleted earlier. Emptying the Recycle Bin removes them for good — look inside first; they can no longer be restored.',
  'err.noBin': 'This drive has no Recycle Bin, so nothing was deleted.', 'err.tooBigForBin': 'Too big for the Recycle Bin ({size}), so nothing was deleted.',
  'err.inUse': 'The file is in use or protected; nothing was deleted.',
  'sum.cloud': 'Online-only cloud file — recorded, not downloaded, no snapshot',
});
Object.assign(I18N.zh, {
  'tab.changes': '变更记录', 'cl.tabDrive': '磁盘', 'sp.tab': '监控的文件夹',
  'cl.stop': '停止', 'cl.stopped': '已在读取 {n} 个文件（{size}）后停止；列表显示已读取的部分。',
  'cl.skipped': '{n} 个文件夹无法读取 · {m} 个仅在线文件不占本机空间',
  'cl.skippedWhy': '没有权限或被 Windows 保留的文件夹不计入；仅在线的云文件按 0 计算，因为它们的内容不在这块磁盘上。',
  'cl.count': '{nf} 个文件',
  'cl.picked': '已勾选 {n} 项', 'cl.freeNow': '可立即释放 {size}', 'cl.freeLater': '清空回收站后再释放 {size}',
  'cl.cleanPicked': '清理勾选的项目', 'cl.gain2': '可释放：立即 {now}，清空回收站后再释放 {later}。',
  'cl.online': '释放空间（仅保留在线）', 'cl.onlineDone': '已请求云服务释放本机上的 {size}；文件仍保留在云端。',
  'cl.hist.none': '不在桌迹监控的文件夹中：桌迹没有它的副本。',
  'cl.hist.kept': '桌迹保存了它的副本（{n} 个版本）：删除后，即使清空回收站，{days} 天内仍可在“文件变更”中恢复。',
  'cl.hist.big': '桌迹在监控这个文件，但没有保存副本（超过快照大小上限）：删除并清空回收站后就无法找回。',
  'cl.hist.noCopy': '桌迹在监控这个文件，但还没有它的副本。',
  'cl.confirmTitle': '清理这些项目？', 'cl.irreversible': '永久删除——无法撤销', 'cl.start': '开始清理',
  'cl.confirmHint': '正在使用或一小时内修改过的文件会被跳过；结果中会列出跳过的数量。',
  'cl.resultTitle': '完成——已释放 {size}', 'cl.r.freed': '已释放', 'cl.r.done': '文件数', 'cl.r.skipped': '已跳过',
  'cl.skippedHint': '跳过的文件正在使用、一小时内修改过或受保护；关闭使用它们的程序后可再清理一次。',
  'cl.inBinHint': '移到回收站的项目可以从回收站恢复；清空回收站后才会收回空间。',
  'cl.openBin': '打开回收站', 'cl.emptyTitle': '清空回收站？',
  'cl.emptyText': '回收站中有 {n} 个文件（{size}），都是你之前删除的文件。如不确定，请先打开查看。清空会永久删除它们，之后无法恢复。',
  'cl.sure': '我明白这无法撤销', 'cl.permTitle': '这将被永久删除',
  'cl.noBinText': '这个磁盘没有回收站（或回收站已关闭），{name}（{size}）无法移到回收站。现在删除会永久删除它。',
  'cl.tooBigText': '{name}（{size}）超过了这个磁盘回收站的容量，Windows 会直接永久删除它，而不是移到回收站。',
  'cl.deletePerm': '永久删除', 'cl.deletedPerm': '已永久删除 {name}（释放 {size}）。',
  'cl.recycled': '{name} 已移到回收站，需要时可从回收站恢复。清空回收站后才会收回 {size} 空间。',
  'cl.level.cloud': '云端同步', 'cl.level.inapp': '请在应用内清理',
  'cl.file.cloud': '位于云服务同步的文件夹（如 OneDrive）中：在这里删除也会删除云端的文件。请改用“释放空间”，只保留在线副本。',
  'cl.file.game': '已安装游戏的一部分。请在游戏平台（Steam、Epic 等）中卸载或移动；直接删除会损坏游戏，需要重新下载。',
  'cl.file.chat': '微信 / QQ 等聊天软件的聊天记录或收到的文件，无法重新下载。请使用应用自带的存储空间清理。',
  'cl.file.pst': 'Outlook 数据文件，保存着你的邮件。删除会丢失这些邮件；请在 Outlook 中归档或清理。',
  'cl.file.ost': 'Outlook 邮箱的脱机副本。删除后 Outlook 会重新下载全部邮件来重建，可能需要数小时。',
  'cl.file.git': 'Git 仓库的一部分。删除会损坏仓库及其历史。',
  'cl.file.winold': '上一个版本的 Windows，用于升级后回退。Windows 会在 10 天后自动删除；如需提前删除，请使用 Windows 磁盘清理。',
  'cl.item.memdump': '系统内存转储', 'cl.item.winold': '旧版 Windows（Windows.old）',
  'cl.why.memdump': '蓝屏后 Windows 写入的内存转储。除非有人在分析这次崩溃，否则可以安全删除。需要管理员权限。',
  'cl.why.winold': '上一个版本的 Windows，升级后 10 天内可以回退；删除后就不能回退了。',
  'cl.why.temp': '程序工作时留下的文件。通常可以安全删除；一小时内修改过的和正在使用的文件会被跳过并列出。',
  'cl.why.wintemp': 'Windows 和安装程序的临时文件。通常安全；正在使用和需要管理员权限的文件会被跳过并列出。',
  'cl.why.edge': '为加快打开速度而保存的网页副本。不会删除书签、密码和历史记录；少数网站可能需要重新登录。浏览器正在使用的文件会被跳过——先关闭浏览器可释放全部空间。',
  'cl.why.chrome': '为加快打开速度而保存的网页副本。不会删除书签、密码和历史记录；少数网站可能需要重新登录。浏览器正在使用的文件会被跳过——先关闭浏览器可释放全部空间。',
  'cl.why.firefox': '为加快打开速度而保存的网页副本。不会删除书签、密码和历史记录；少数网站可能需要重新登录。',
  'cl.why.devcache': 'pip、npm、Yarn 的全局下载缓存（不涉及你的项目）。下次安装或构建需要联网重新获取；离线或私有源环境可能会失败。',
  'cl.why.installers': '下载文件夹中 30 天未动过的安装程序（.exe、.msi）。仅适用于确认不再需要的安装包：便携软件和已失效的下载链接无法重新获取。会移到回收站，可以恢复。',
  'cl.why.recycle': '你之前删除的文件。清空回收站会永久删除它们——请先打开看看，之后无法再恢复。',
  'err.noBin': '这个磁盘没有回收站，未删除任何文件。', 'err.tooBigForBin': '超过回收站容量（{size}），未删除任何文件。',
  'err.inUse': '文件正在使用或受保护，未删除任何文件。',
  'sum.cloud': '仅在线的云文件——已记录，未下载，无快照',
});

/* trust (2.3.0): warnings, protection status, restore plan, backup */
Object.assign(I18N.en, {
  'warn.lowdisk': 'Less than 1 GB free:', 'warn.lowdiskWhy': 'changes are still recorded, but no new copies of versions are kept until there is room again.',
  'warn.overflow': 'Some change details were missed:', 'warn.overflowWhy': 'Windows reported too many changes at once. DeskTrace looked at everything again right away, but versions saved in between may be missing.',
  'warn.noinstant': 'Instant detection is off:', 'warn.noinstantWhy': 'changes are found by regular rescans, so quick successive saves may be recorded as one.',
  'warn.integrity': 'The history database reported a problem:', 'warn.integrityWhy': 'back up the history now; details are in Settings › Diagnostics.',
  'warn.goClean': 'Clean up', 'warn.goBackup': 'Back up…',
  'prot.kept': 'Versions kept', 'prot.keptWhy': 'DeskTrace has a copy of the current version and keeps a copy of every change.',
  'prot.big': 'Too big for versions', 'prot.bigWhy': 'Larger than the snapshot limit (Settings): its changes are recorded, but no copies are kept — it cannot be restored.',
  'prot.cloud': 'Online only', 'prot.cloudWhy': 'A cloud placeholder: DeskTrace records its changes but does not download it, so no copy is kept.',
  'prot.text': 'Copy at next change', 'prot.textWhy': 'Its text is indexed; DeskTrace keeps the first full copy the next time it changes.',
  'prot.pending': 'No copy yet', 'prot.pendingWhy': 'DeskTrace has not kept a copy of this file yet; it will at its next change.',
  'rp.title': 'Restore this version?', 'rp.version': 'Version', 'rp.to': 'Restore to', 'rp.exists': 'If the file is there',
  'rp.saved': 'Saved {time}', 'rp.before': 'As it was before the change at {time}', 'rp.free': 'Nothing is there now — the file comes back at this place.',
  'rp.copy': 'Restore as a new file (recommended)', 'rp.copyWhy': 'The current file stays exactly as it is.',
  'rp.replace': 'Replace the current file', 'rp.replaceWhy': 'Its current content stays in the history, so this can be undone the same way.',
  'rp.replaceNo': 'Not possible: DeskTrace has no copy of the current content, so replacing it could not be undone.',
  'rp.doneCopy': 'Restored as {path} — the original file was left as it was.', 'rp.doneReplaced': '{path} now holds the restored version; its previous content is in the history.',
  'bk.title': 'Back up the history', 'bk.btn': 'Back up to another drive…',
  'bk.hint': 'DeskTrace keeps its history on the same disk as your files — it is not a backup: if that disk fails, both are lost. Copy the history (all versions and notes) to another drive, e.g. a USB disk; later backups only add what is new.',
  'bk.running': 'Backing up… {n} of {total} versions', 'bk.done': 'History backed up to {path}', 'bk.failed': 'The backup failed: {why}',
  'diag.integrity': 'History database', 'diag.dbOk': 'Checked, no problems', 'diag.dbBad': 'Problem: {why}',
  'diag.warn': 'History complete?', 'diag.noWarn': 'Yes — nothing was missed',
});
Object.assign(I18N.zh, {
  'warn.lowdisk': '可用空间不足 1 GB：', 'warn.lowdiskWhy': '变更仍会记录，但在空间恢复之前不再保存新的版本副本。',
  'warn.overflow': '漏掉了一些变更细节：', 'warn.overflowWhy': 'Windows 一次报告了太多变更。桌迹已立即重新检查全部文件，但这期间保存的版本可能缺失。',
  'warn.noinstant': '即时检测已关闭：', 'warn.noinstantWhy': '变更靠定期重扫发现，快速连续的几次保存可能只记录为一次。',
  'warn.integrity': '历史数据库报告了问题：', 'warn.integrityWhy': '请立即备份历史记录；详情见 设置 › 诊断信息。',
  'warn.goClean': '去清理', 'warn.goBackup': '备份…',
  'prot.kept': '已保存版本', 'prot.keptWhy': '桌迹有当前版本的副本，并会为每次变更保存副本。',
  'prot.big': '太大，不保存版本', 'prot.bigWhy': '超过快照大小上限（设置中）：会记录它的变更，但不保存副本——无法恢复。',
  'prot.cloud': '仅在线', 'prot.cloudWhy': '云端占位文件：桌迹记录它的变更但不下载它，因此不保存副本。',
  'prot.text': '下次变更时保存', 'prot.textWhy': '已为它的文字建立索引；下次变化时桌迹会保存第一份完整副本。',
  'prot.pending': '尚无副本', 'prot.pendingWhy': '桌迹还没有保存这个文件的副本；它下次变化时会保存。',
  'rp.title': '恢复这个版本？', 'rp.version': '版本', 'rp.to': '恢复到', 'rp.exists': '如果文件已存在',
  'rp.saved': '保存于 {time}', 'rp.before': '{time} 那次变更之前的样子', 'rp.free': '该位置目前没有文件——文件会恢复到这里。',
  'rp.copy': '恢复为新文件（推荐）', 'rp.copyWhy': '现有文件保持原样。',
  'rp.replace': '替换现有文件', 'rp.replaceWhy': '现有内容会保留在历史记录中，可以用同样方式撤销。',
  'rp.replaceNo': '无法替换：桌迹没有现有内容的副本，替换后将无法撤销。',
  'rp.doneCopy': '已恢复为 {path}——原文件保持不变。', 'rp.doneReplaced': '{path} 已替换为恢复的版本；之前的内容保留在历史记录中。',
  'bk.title': '备份历史记录', 'bk.btn': '备份到其他磁盘…',
  'bk.hint': '桌迹把历史记录保存在与你的文件相同的磁盘上——它不是备份：这块磁盘损坏时两者会一起丢失。请把历史记录（全部版本和备注）复制到其他磁盘，例如 U 盘；之后的备份只会添加新增的内容。',
  'bk.running': '正在备份… {n} / {total} 个版本', 'bk.done': '历史记录已备份到 {path}', 'bk.failed': '备份失败：{why}',
  'diag.integrity': '历史数据库', 'diag.dbOk': '已检查，没有问题', 'diag.dbBad': '有问题：{why}',
  'diag.warn': '历史记录完整吗？', 'diag.noWarn': '是——没有遗漏',
});

/* 2.4.0: kept scans, quick/full, disk usage, chat apps, hibernation, Undo, pre-scan, first-run guide */
Object.assign(I18N.en, {
  'cl.kept': 'Scanned {ago} (kept)', 'cl.quick': 'Quick scan', 'cl.quickWhy': 'A quick scan reads only your user folder and the folders DeskTrace watches; a full scan reads the whole drive.',
  'cl.scanQuick': 'Quick scan', 'cl.scanFull': 'Full scan', 'cl.invalid': 'The kept scan was of another disk — reading this drive again…',
  'cl.quickNote': 'Quick scan: only your user folder and the watched folders were read. Run a full scan to see the whole drive.',
  'cl.note2': 'Sizes are what files take on the disk (whole clusters, less when compressed or sparse); a 1 KB file takes 4 KB. Files Windows keeps hard-linked in WinSxS are counted once. Links and junctions are not followed.',
  'cl.openApp': 'Open the app', 'cl.openData': 'Open data folder', 'cl.how.inapp': 'Clean up in the app', 'cl.how.switch': 'A Windows setting',
  'cl.app.wechat': 'WeChat data', 'cl.app.qq': 'QQ data', 'cl.app.wecom': 'WeCom data', 'cl.app.dingtalk': 'DingTalk data', 'cl.app.telegram': 'Telegram data',
  'cl.why.app': '{app} holds your chat history and the files you received — they cannot be downloaded again, so DeskTrace never deletes them. In the app, open its settings and look for its storage management to clear caches you do not need.',
  'cl.item.hiber': 'Hibernation file (hiberfil.sys)',
  'cl.why.hiber': 'Windows keeps this file for hibernation and fast startup. Switching hibernation off removes it; you lose hibernate and fast startup, and can switch it on again the same way.',
  'cl.why.hiberOff': 'Hibernation is off, so this file takes no space. Switch it on again to use hibernate and fast startup.',
  'cl.hiberOff': 'Switch hibernation off', 'cl.hiberOn': 'Switch hibernation on', 'cl.powerOpts': 'Power Options',
  'cl.hiberOffTitle': 'Switch hibernation off?', 'cl.hiberOnTitle': 'Switch hibernation on?',
  'cl.hiberOffText': 'This frees about {size}: Windows deletes hiberfil.sys. You can no longer hibernate, and fast startup is off. To undo it, switch it on again here (or run "powercfg /h on" as administrator).',
  'cl.hiberOnText': 'Windows creates hiberfil.sys again (about as big as your memory) so you can hibernate and use fast startup.',
  'cl.hiberUac': 'This is a Windows setting that needs administrator rights: Windows asks you for permission. DeskTrace itself never runs as administrator.',
  'cl.hiberAsked': 'If you allowed it in the Windows prompt, the change is made; Clean up shows the new state shortly.',
  'cl.usedWhy': 'What the file takes on the disk', 'cl.usedLabel': '{used} on disk', 'cl.sizeLabel': 'size {size}',
  'cl.sizeVsUsed': 'size {size}, takes {used}', 'cl.shared': 'shared ({n} links): takes its space only once', 'cl.sparse': 'sparse', 'cl.compressed': 'compressed', 'cl.approx': 'about',
  'cl.sharedFolder': 'incl. {size} shared with Windows, counted once',
  'cl.undoBar': { one: '1 item moved to the Recycle Bin.', other: '{n} items moved to the Recycle Bin.' },
  'cl.undone': { one: 'Put back where it was.', other: '{n} items put back where they were.' },
  'cl.undoPartly': '{n} put back, {m} could not be — e.g. {first}: {why}', 'cl.undoWhy.notInBin': 'no longer in the Recycle Bin',
  'cl.undoWhy.occupied': 'another file is at that place now (it stays in the Recycle Bin)', 'cl.undoWhy.inUse': 'in use',
  'set.prescan': 'Prepare Clean up in the background', 'set.prescanOn': 'Clean up will be prepared in the background.', 'set.prescanOff': 'Background preparation is off.',
  'set.prescanHint': 'While the PC is idle, plugged in and not running a full-screen game or presentation, DeskTrace reads your drives at the lowest priority (at most every 12 hours), so Clean up opens on fresh results.',
  'gd.title': 'Welcome to DeskTrace', 'gd.step': 'step {n} of {of}', 'gd.skip': 'Skip', 'gd.next': 'Next', 'gd.start': 'Start protecting', 'gd.done': 'Done',
  'gd.s1': 'DeskTrace keeps a version of every change to the files in these folders — so you can undo edits and bring back deleted files.', 'gd.add': 'Add a folder…',
  'gd.whyTitle': 'Why not Windows’ own tools?',
  'gd.why1': 'File History backs up on a schedule to another drive; DeskTrace keeps every save the moment it happens, with no drive to plug in.',
  'gd.why2': '"Previous versions" only exist where File History or restore points made them, often days apart.',
  'gd.why3': 'OneDrive keeps versions only for files inside OneDrive, in the cloud; DeskTrace works on your local folders and never uploads anything.',
  'gd.why4': 'DeskTrace is not a backup: its history is on the same disk. For safety against a broken disk, use Settings › Back up to another drive.',
  'gd.s2': 'Protection has started. DeskTrace notices changes instantly and keeps a copy of each version.', 'gd.watching': 'Watching {n} files',
  'gd.s2b': 'It runs quietly in the background; the icon near the clock opens this window.',
  'gd.s3': 'Try it once with a test file DeskTrace makes (none of your own files are touched):', 'gd.make': 'Make a test file', 'gd.del': 'Delete it',
  'gd.deleting': 'Deleting…', 'gd.restore': 'Restore it — right here.', 'gd.restoreNow': 'Deleted. Now bring it back:', 'gd.restoreBtn': 'Restore', 'gd.deleted': 'Deleted', 'gd.restored': 'It is back, with its content. Every deleted file in these folders can be restored like this, from Changes.', 'gd.notSeen': 'DeskTrace did not see the deletion in time; you can restore the file from Changes.',
  'gd.s3b': 'Every deleted file in these folders gets the same Restore button, and every change is listed under Changes.',
  'gd.finished': 'All set. The test file was removed again.',
  'cl.sharing': 'Correcting files Windows shares (WinSxS) — the Windows folder gets smaller once done…',
  'cl.tinyNote': '{n} very small files may be stored inside the file table and take no cluster; the totals may be up to {size} too high.',
  'cl.noExt': 'No extension', 'cl.noExtWhy': 'Files without an extension — mostly system, program and cache files.',
  'cl.stale': 'may be out of date — scan again', 'bk.raw': 'Back up for older versions', 'bk.rawWhy': 'Uncompressed, so DeskTrace 2.3.0 and older can read it (takes more room).',
  'diag.snapFormat': 'Version format',
  'gd.why': 'DeskTrace and Windows’ own tools', 'gd.whyShort': 'How DeskTrace differs from File History, "Previous versions" and OneDrive, and the short guide.', 'gd.reopen': 'Open the guide',
});
Object.assign(I18N.zh, {
  'cl.kept': '扫描于 {ago}（已保存）', 'cl.quick': '快速扫描', 'cl.quickWhy': '快速扫描只读取你的用户文件夹和桌迹监控的文件夹；完整扫描读取整个磁盘。',
  'cl.scanQuick': '快速扫描', 'cl.scanFull': '完整扫描', 'cl.invalid': '保存的扫描结果属于另一块磁盘——正在重新读取这个磁盘…',
  'cl.quickNote': '快速扫描：只读取了你的用户文件夹和监控的文件夹。运行完整扫描可查看整个磁盘。',
  'cl.note2': '大小按文件在磁盘上的实际占用计算（按簇对齐，压缩或稀疏文件更小）；1 KB 的文件占 4 KB。WinSxS 中与 Windows 共享的硬链接文件只计一次。不会跟随链接和联接点。',
  'cl.openApp': '打开应用', 'cl.openData': '打开数据文件夹', 'cl.how.inapp': '请在应用内清理', 'cl.how.switch': 'Windows 设置',
  'cl.app.wechat': '微信数据', 'cl.app.qq': 'QQ 数据', 'cl.app.wecom': '企业微信数据', 'cl.app.dingtalk': '钉钉数据', 'cl.app.telegram': 'Telegram 数据',
  'cl.why.app': '{app}中保存着你的聊天记录和收到的文件，无法重新下载，所以桌迹绝不会删除它们。请在应用的设置中找到存储空间管理，清理不需要的缓存。',
  'cl.item.hiber': '休眠文件（hiberfil.sys）',
  'cl.why.hiber': 'Windows 保留这个文件用于休眠和快速启动。关闭休眠会删除它；你将无法休眠，快速启动也会关闭，之后可用同样方式重新打开。',
  'cl.why.hiberOff': '休眠已关闭，这个文件不占空间。重新打开后才能使用休眠和快速启动。',
  'cl.hiberOff': '关闭休眠', 'cl.hiberOn': '打开休眠', 'cl.powerOpts': '电源选项',
  'cl.hiberOffTitle': '关闭休眠？', 'cl.hiberOnTitle': '打开休眠？',
  'cl.hiberOffText': '这会释放约 {size}：Windows 删除 hiberfil.sys。之后无法休眠，快速启动也会关闭。想恢复时，在这里重新打开即可（或以管理员身份运行“powercfg /h on”）。',
  'cl.hiberOnText': 'Windows 会重新创建 hiberfil.sys（大小约等于内存），以便休眠和快速启动。',
  'cl.hiberUac': '这是需要管理员权限的 Windows 设置：Windows 会弹出提示请你同意。桌迹本身从不以管理员身份运行。',
  'cl.hiberAsked': '如果你在 Windows 的提示中同意了，设置就已更改；“空间清理”稍后会显示新状态。',
  'cl.usedWhy': '文件在磁盘上的实际占用', 'cl.usedLabel': '占用 {used}', 'cl.sizeLabel': '大小 {size}',
  'cl.sizeVsUsed': '大小 {size}，占用 {used}', 'cl.shared': '共享（{n} 个链接）：空间只占一次', 'cl.sparse': '稀疏', 'cl.compressed': '已压缩', 'cl.approx': '约',
  'cl.sharedFolder': '含 {size} 与 Windows 共享，只计一次',
  'cl.undoBar': '已将 {n} 项移到回收站。', 'cl.undone': '已将 {n} 项放回原处。',
  'cl.undoPartly': '已放回 {n} 项，{m} 项无法放回——例如 {first}：{why}', 'cl.undoWhy.notInBin': '已不在回收站中',
  'cl.undoWhy.occupied': '原位置现在有另一个文件（它仍留在回收站）', 'cl.undoWhy.inUse': '正在使用',
  'set.prescan': '在后台预先准备“空间清理”', 'set.prescanOn': '“空间清理”将在后台预先准备。', 'set.prescanOff': '已关闭后台预先准备。',
  'set.prescanHint': '电脑空闲、接通电源且没有运行全屏游戏或演示时，桌迹会以最低优先级读取你的磁盘（最多每 12 小时一次），这样打开“空间清理”时结果已经是新的。',
  'gd.title': '欢迎使用桌迹', 'gd.step': '第 {n} 步，共 {of} 步', 'gd.skip': '跳过', 'gd.next': '下一步', 'gd.start': '开始保护', 'gd.done': '完成',
  'gd.s1': '桌迹会为这些文件夹中文件的每一次变化保存一个版本——你可以撤销修改，也能找回被删除的文件。', 'gd.add': '添加文件夹…',
  'gd.whyTitle': '为什么不用 Windows 自带的工具？',
  'gd.why1': '“文件历史记录”按计划备份到另一块磁盘；桌迹在每次保存的瞬间就留下版本，不需要插入其他磁盘。',
  'gd.why2': '“以前的版本”只存在于文件历史记录或还原点创建过的时刻，往往相隔好几天。',
  'gd.why3': 'OneDrive 只为 OneDrive 中的文件在云端保留版本；桌迹作用于你本地的文件夹，从不上传任何东西。',
  'gd.why4': '桌迹不是备份：它的历史记录和文件在同一块磁盘上。要防止磁盘损坏，请使用 设置 › 备份到其他磁盘。',
  'gd.s2': '保护已经开始。桌迹会即时发现变化，并为每个版本保存副本。', 'gd.watching': '正在监控 {n} 个文件',
  'gd.s2b': '它在后台安静运行；点击时钟旁的图标即可打开这个窗口。',
  'gd.s3': '用桌迹创建的测试文件试一次（不会动你自己的任何文件）：', 'gd.make': '创建测试文件', 'gd.del': '删除它',
  'gd.deleting': '正在删除…', 'gd.restore': '就在这里把它恢复。', 'gd.restoreNow': '已删除。现在把它找回来：', 'gd.restoreBtn': '恢复', 'gd.deleted': '已删除', 'gd.restored': '文件回来了，内容完好。这些文件夹中每个被删除的文件都可以在“变更”中这样恢复。', 'gd.notSeen': '桌迹没有及时看到这次删除；你可以在“变更”中恢复这个文件。',
  'gd.s3b': '这些文件夹中每个被删除的文件都会有同样的“恢复”按钮，每次变化都列在“变更”中。',
  'gd.finished': '一切就绪。测试文件已再次删除。',
  'cl.sharing': '正在修正 Windows 共享文件（WinSxS）的占用——完成后 Windows 文件夹会变小…',
  'cl.tinyNote': '有 {n} 个极小文件可能直接存放在文件表中、不占簇；合计最多可能高估约 {size}。',
  'cl.noExt': '无扩展名', 'cl.noExtWhy': '没有扩展名的文件——多为系统、程序和缓存文件。',
  'cl.stale': '可能已过期——请重新扫描', 'bk.raw': '为旧版本备份', 'bk.rawWhy': '不压缩，桌迹 2.3.0 及更早版本也能读取（占用更多空间）。',
  'diag.snapFormat': '版本格式',
  'gd.why': '桌迹与 Windows 自带的工具', 'gd.whyShort': '桌迹与文件历史记录、“以前的版本”和 OneDrive 有什么不同，以及入门向导。', 'gd.reopen': '打开入门向导',
});

// 2.4.2 (Gemini review): plainer words, a view of deleted files, folders that are away, safer cleanup
Object.assign(I18N.en, {
  'mode.changes': 'History & restore', 'tab.changes': 'All changes', 'list.title': 'All changes',
  'help.mode': 'Switch between History & restore and Files', 'help.views': 'History & restore / Files / Duplicates / Space / Clean up',
  'gd.restored': 'It is back, with its content. Every deleted file in these folders can be brought back like this, from History & restore.',
  'gd.notSeen': 'DeskTrace did not see the deletion in time; you can restore the file from History & restore.',
  'gd.s3b': 'Every deleted file in these folders gets the same Restore button, under History & restore → Find deleted files.',
  'cl.hist.kept': 'DeskTrace keeps a copy ({n} versions): after deleting you can still bring it back from History & restore for {days} days, even once the Recycle Bin is emptied.',
  'diff.missing': 'This is the first version DeskTrace has seen of this file — it was already there before DeskTrace started looking after it, so there is nothing earlier to compare with. From its next change on you will see what changed.',
  'prot.text': 'Searchable, no copy yet', 'prot.textWhy': 'DeskTrace knows its words (it can be found by searching) but has not kept a copy of the file itself yet. It keeps one the next time the file changes. Until then a deleted file cannot be brought back.',
  'prot.pending': 'No copy yet', 'prot.pendingWhy': 'DeskTrace has not kept a copy of this file yet; it keeps one the next time the file changes. Until then a deleted file cannot be brought back.',
  'cl.folders': 'What takes up the space', 'cl.types': 'By file type', 'cl.drillHint': 'click a folder to look inside · totals are rounded estimates',
  'cl.why.temp': 'Files programs left behind while working. Usually safe to delete. Left alone: files changed in the last two days, files in use, and recovery copies and unsaved drafts (Office, WPS and other editors), however old.',
  'cl.confirmHint': 'Left alone: files in use, files changed in the last two days, and recovery copies or unsaved drafts. The result lists what was skipped.',
  'cl.how.gone': 'Deleted directly · programs do not need them',
  'del.btn': 'Find deleted files', 'del.chip': 'Deleted, still missing',
  'del.lead': 'Files that were deleted from their place and are still missing — newest first. DeskTrace kept a copy of each one; Restore puts it back.',
  'del.empty': 'No deleted files to bring back', 'del.emptyText': 'Every file DeskTrace saw deleted is back in place, or none was deleted yet.',
  'warn.rootgone': 'A monitored folder is not reachable:', 'warn.rootgoneWhy': '{dirs} — the drive may be unplugged or the network away. Its files are not taken for deleted; DeskTrace carries on when it is back.',
  'warn.rootgoneBtn': 'It was deleted…',
  'rg.title': 'Was this folder deleted?', 'rg.text': 'Only choose this if {dir} was really deleted or moved for good. Its files are then listed as deleted, and each can be restored from its kept copy. If the drive is just unplugged, plug it back in instead — nothing needs doing.',
  'rg.confirm': 'Yes, list its files as deleted', 'rg.done': '{n} files listed as deleted. Find them under Find deleted files.',
  'err.inUse': 'The file is open in another program (for example Word), so it was not replaced — it is unchanged. Close it and try again, or choose “Restore as a new file”.',
  'err.writeFailed': 'The version could not be written (is the disk full?). Nothing was changed.',
  'err.cloud': 'This file is online-only (in the cloud). DeskTrace does not download it just to show it; open it once to bring it to this PC.',
  'cl.lastBar': 'Last cleanup ({when}) moved {n} items ({size}) to the Recycle Bin.', 'cl.lastUndo': 'Put them back',
  'cl.lastDone': '{n} items are back where they were.',
  'cl.inBinHint2': 'They are in the Recycle Bin. As long as it is not emptied you can put them back at any time with “Put them back” in Clean up.',
});
Object.assign(I18N.zh, {
  'mode.changes': '历史与找回', 'tab.changes': '修改记录', 'list.title': '修改记录',
  'help.mode': '在“历史与找回”和“文件”之间切换', 'help.views': '历史与找回 / 文件 / 重复文件 / 空间占用 / 空间清理',
  'gd.restored': '文件回来了，内容完好。这些文件夹中每个被删除的文件，都可以在“历史与找回”中这样找回。',
  'gd.notSeen': '桌迹没有及时看到这次删除；你可以在“历史与找回”中恢复这个文件。',
  'gd.s3b': '这些文件夹中每个被删除的文件都会有同样的“恢复”按钮，在“历史与找回”→“找回已删除的文件”中。',
  'cl.hist.kept': '桌迹保存了它的副本（{n} 个版本）：删除后，即使清空回收站，{days} 天内仍可在“历史与找回”中找回。',
  'diff.missing': '这是桌迹看到的这个文件的第一个版本——桌迹开始照看它之前，它就已经在这里了，所以没有更早的版本可以对比。从它下一次被修改开始，就能看到改了哪里。',
  'prot.text': '可搜索，暂无副本', 'prot.textWhy': '桌迹已经记下了它的文字（可以搜到它），但还没有保存文件本身的副本；它下次被修改时会保存一份。在那之前，删除后无法找回。',
  'prot.pending': '暂无副本', 'prot.pendingWhy': '桌迹还没有保存这个文件的副本；它下次被修改时会保存一份。在那之前，删除后无法找回。',
  'cl.folders': '空间都用在了哪里', 'cl.types': '按文件类型', 'cl.drillHint': '点击文件夹查看里面 · 合计为取整后的近似值',
  'cl.why.temp': '程序工作时留下的文件，通常可以安全删除。不会动：两天内修改过的文件、正在使用的文件，以及 Office、WPS 等编辑软件的恢复副本和未保存的草稿（无论多旧）。',
  'cl.confirmHint': '不会动：正在使用的文件、两天内修改过的文件，以及恢复副本和未保存的草稿。结果中会列出跳过的数量。',
  'cl.how.gone': '直接删除 · 程序已不再需要',
  'del.btn': '找回已删除的文件', 'del.chip': '已删除、仍未找回',
  'del.lead': '从原位置被删除、至今仍不在原处的文件，最近删除的在前。桌迹为每一个都保存了副本，点“恢复”即可放回原处。',
  'del.empty': '没有需要找回的文件', 'del.emptyText': '桌迹看到被删除的文件都已回到原处，或者还没有文件被删除过。',
  'warn.rootgone': '有监控的文件夹现在无法访问：', 'warn.rootgoneWhy': '{dirs}——可能是移动硬盘被拔出或网络断开。里面的文件不会被当作已删除；它回来后桌迹会自动继续。',
  'warn.rootgoneBtn': '它已被删除…',
  'rg.title': '这个文件夹被删除了吗？', 'rg.text': '只有在 {dir} 确实已被删除或永久移走时才选这一项。之后它的文件会列为“已删除”，每个都可以用保存的副本找回。如果只是拔掉了移动硬盘，插回去即可，什么都不用做。',
  'rg.confirm': '是的，把它的文件列为已删除', 'rg.done': '已把 {n} 个文件列为已删除，可在“找回已删除的文件”中找到。',
  'err.inUse': '这个文件正在被其他程序打开（例如 Word），所以没有替换——它没有任何改动。请关闭它后再试，或选择“恢复为新文件”。',
  'err.writeFailed': '无法写入这个版本（磁盘是否已满？）。没有做任何改动。',
  'err.cloud': '这个文件只存在于云端（仅联机）。桌迹不会为了显示它而下载；打开一次即可把它下载到本机。',
  'cl.lastBar': '上次清理（{when}）把 {n} 项（{size}）移到了回收站。', 'cl.lastUndo': '放回原处',
  'cl.lastDone': '{n} 项已放回原处。',
  'cl.inBinHint2': '它们在回收站中。只要没有清空回收站，随时都可以在“空间清理”中点“放回原处”。',
});

// 2.4.2 everyday words: 变更 -> 变化 everywhere in the Chinese UI
Object.assign(I18N.zh, {
  'side.typesHint': '变化 · 已跟踪',
  'chart.aria': '最近 2 小时每 5 分钟的变化数',
  'list.emptyTitle': '正在监控变化',
  'list.noMatchTitle': '没有匹配的变化',
  'list.more': '加载更早的变化',
  'welcome.title': '选择一条变化进行预览',
  'p.change': '变化',
  'diff.changedN': '{n} 处变化',
  'toast.seeAll': '请在变化记录中查看全部',
  'set.intervalHint': '通过 Windows 的变化通知，改动会被即时发现。另外每隔这段时间进行一次完整扫描作为保障（例如不支持通知的网络驱动器）。在通知正常工作时，为节省电量最多每 5 分钟扫描一次。',
  'set.clearTitle': '清除变化历史',
  'set.clearText': '删除所有变化记录及其快照。存储位置：{dir}',
  'clear.text': '所有变化记录和已存储的快照都将被删除，你的实际文件不受影响。',
  'chart.total': '最近 2 小时共 <b>{n}</b> 次变化',
  'chart.tip': '{a}–{b} · {n} 次变化',
  'hist.count': '此文件共有 {n} 条变化记录',
  'toast.more': '还有 {n} 条变化',
  'files.changes': '{n} 次变化',
  'fd.noChanges': '暂无变化记录',
  'quit.text': '监控将停止。停止期间发生的变化会在下次启动时被检测到。',
  'export.title': '将这些变化导出到 Excel',
  'files.sortChanges': '变化最多',
  'set.keepDaysHint': '更早的变化记录会被删除。0 表示永久保留。',
  'set.maxStorageHint': '超过上限时，会删除最早版本的完整副本，但保留其文本和变化记录。0 表示不限制。',
  'set.notifyHint': '由托盘图标显示。短时间内的多处变化会合并为一条通知。',
  'notify.all': '所有变化',
  'upd.keep': '变化历史、快照和设置都会保留。更新只需几秒钟，窗口会自动重新打开。',
  'set.muteHint': '暂时不显示桌面通知；变化仍会被记录。',
  'set.exPathsHint': '这些文件夹中的变化不会被记录。',
  'set.exPathsNone': '无——在某条变化上点“忽略文件夹”即可添加。',
  'ign.text': '{dir} 中的变化将不再被记录，已有的历史会保留。可以在设置中撤销。',
  'diag.events': '已记录的变化',
  'folder.only': '此文件夹中的变化',
  'diag.diskLow': '不足 1 GB：变化仍会记录，但不再保存新的副本',
  'page.changes': '历史与找回',
  'notes.emptyText': '选中一条变化后按 N（或点“添加备注”）给这个版本加上说明，例如“已发给客户”。带备注的版本会一直保留。',
  'day.count': '{nf} 处变化',
  'clean.done': '清理完成：忘记了 {n} 条旧变化，释放了 {size}。',
  'help.right': '右键单击变化或文件可使用其操作。',
  'warn.lowdiskWhy': '变化仍会记录，但在空间恢复之前不再保存新的版本副本。',
  'warn.overflow': '漏掉了一些变化细节：',
  'warn.overflowWhy': 'Windows 一次报告了太多变化。桌迹已立即重新检查全部文件，但这期间保存的版本可能缺失。',
  'warn.noinstantWhy': '变化靠定期重扫发现，快速连续的几次保存可能只记录为一次。',
  'prot.keptWhy': '桌迹有当前版本的副本，并会为每次变化保存副本。',
  'prot.bigWhy': '超过快照大小上限（设置中）：会记录它的变化，但不保存副本——无法恢复。',
  'prot.cloudWhy': '云端占位文件：桌迹记录它的变化但不下载它，因此不保存副本。',
  'rp.before': '{time} 那次变化之前的样子',
  'del.btn': '找回已删除',
  'cl.how.gone': '直接删除 · 无需保留',
});
Object.assign(I18N.en, {
  'del.btn': 'Find deleted', 'cl.how.gone': 'Deleted directly · not needed', 'page.changes': 'History & restore',
});

Object.assign(I18N.zh, { 'gd.s3b': '这些文件夹中每个被删除的文件都会有同样的“恢复”按钮——点“历史与找回”里的“找回已删除”即可列出。' });
Object.assign(I18N.en, { 'gd.s3b': 'Every deleted file in these folders gets the same Restore button — click Find deleted in History & restore to list them.' });

// 2.5.0 plain labels: what the file is, what deleting it does, what is better (Clean up)
Object.assign(I18N.en, {
  'cl.level.program': 'Program file', 'cl.level.cloud': 'Synced to the cloud', 'cl.level.inapp': 'App data',
  'cl.level.caution': 'App settings or cache', 'cl.level.personal': 'Your file', 'cl.level.safe': 'Safe to delete', 'cl.level.system': 'Windows',
  'cl.ifDelete': 'If you delete it:',
  'cl.file.cloud': 'It is also deleted in the cloud and on every device that syncs this folder. If you only want the space back, choose "Keep online only" — it stays in the cloud.',
  'cl.file.winold': 'Part of your previous Windows, kept for going back after an upgrade. Deleting single files breaks going back; Windows Disk Cleanup removes it whole.',
  'cl.file.game': 'The game may no longer start or may want to download this again. To free the space properly, uninstall the game in its launcher (Steam, Epic, …).',
  'cl.file.program': 'The program it belongs to may stop working or not start. To free the space properly, uninstall the program in Windows Settings.',
  'cl.file.programdata': 'Data a program shares for all users (settings, licences, downloads). The program may stop working or need to be set up or activated again.',
  'cl.file.chat': 'Chat history or a received file of this app is lost — it cannot be downloaded again. The app\'s own storage cleanup is the safer way.',
  'cl.file.pst': 'An Outlook data file: e-mails, contacts and calendar kept only on this PC are lost. Archive or remove it inside Outlook instead.',
  'cl.file.git': 'Part of a Git repository\'s history; the repository can break. Clean it with Git itself.',
  'cl.file.ost': 'Outlook\'s offline copy of a mailbox. Outlook downloads it again (which can take long).',
  'cl.file.appdata': 'Settings, cache or data of an app. Most apps rebuild a cache; settings or saved data may be lost.',
  'cl.file.installer': 'A setup program you downloaded. Only needed to install that program again.',
  'cl.file.vm': 'A virtual machine disk: everything inside that virtual machine is lost.',
  'cl.file.archive': 'An archive you saved. Check that you do not need what is inside.',
  'cl.file.media': 'Your video, music or picture. Check that you have another copy if you want to keep it.',
  'cl.file.document': 'Your document. Check that you have another copy if you want to keep it.',
  'cl.file.program_file': 'A program file you saved (not installed). Only needed to run or install it again.',
  'cl.file.other': 'A file of yours. Check that you no longer need it.',
  'cl.better.cloud': 'Better: "Keep online only" frees the space here and keeps the file in the cloud.',
  'cl.better.game': 'Better: uninstall the game in its launcher — that removes all of it cleanly.',
  'cl.better.program': 'Better: uninstall the program in Windows Settings → Apps — that removes all of it cleanly.',
  'cl.better.winold': 'Better: Windows Disk Cleanup → Previous Windows installation(s).',
  'cl.better.chat': 'Better: open the app and use its own storage cleanup.',
  'cl.askTitle': 'Delete {name}?', 'cl.iKnow': 'I understand what happens and still want to delete it',
});
Object.assign(I18N.zh, {
  'cl.level.program': '程序文件', 'cl.level.cloud': '云同步文件', 'cl.level.inapp': '应用数据',
  'cl.level.caution': '软件设置或缓存', 'cl.level.personal': '你的文件', 'cl.level.safe': '可以删除', 'cl.level.system': 'Windows',
  'cl.ifDelete': '删除后：',
  'cl.file.cloud': '云端和所有同步这个文件夹的设备上也会一起删除。如果只是想腾出空间，请选“仅保留在线”——文件仍在云端。',
  'cl.file.winold': '这是旧版 Windows 的一部分，用于升级后退回。删除单个文件会导致无法退回；用 Windows 的“磁盘清理”可以整个删除。',
  'cl.file.game': '游戏可能无法启动，或需要重新下载这个文件。想彻底腾出空间，请在游戏平台（Steam、Epic 等）中卸载游戏。',
  'cl.file.program': '它所属的程序可能无法正常工作或无法启动。想彻底腾出空间，请在 Windows 设置中卸载这个程序。',
  'cl.file.programdata': '程序为所有用户共用的数据（设置、授权、下载内容）。程序可能无法工作，或需要重新设置、重新激活。',
  'cl.file.chat': '这个应用的聊天记录或收到的文件会丢失，而且无法重新下载。用应用自带的存储清理更安全。',
  'cl.file.pst': 'Outlook 数据文件：只保存在本机的邮件、联系人和日历会丢失。请在 Outlook 中归档或删除。',
  'cl.file.git': 'Git 仓库历史的一部分，仓库可能损坏。请用 Git 自己清理。',
  'cl.file.ost': 'Outlook 邮箱的离线副本。Outlook 会重新下载（可能需要很久）。',
  'cl.file.appdata': '某个软件的设置、缓存或数据。缓存大多会自动重建；设置或保存的数据可能丢失。',
  'cl.file.installer': '你下载的安装程序。只有重新安装那个软件时才需要。',
  'cl.file.vm': '虚拟机磁盘：这台虚拟机里的所有内容都会丢失。',
  'cl.file.archive': '你保存的压缩包。请确认里面的内容已不需要。',
  'cl.file.media': '你的视频、音乐或图片。如果还想保留，请确认别处有备份。',
  'cl.file.document': '你的文档。如果还想保留，请确认别处有备份。',
  'cl.file.program_file': '你保存的程序文件（未安装）。只有再次运行或安装时才需要。',
  'cl.file.other': '你的文件。请确认已经不需要它。',
  'cl.better.cloud': '更好的做法：“仅保留在线”能腾出本机空间，文件仍保留在云端。',
  'cl.better.game': '更好的做法：在游戏平台中卸载游戏，能干净地全部删除。',
  'cl.better.program': '更好的做法：在“Windows 设置 → 应用”中卸载程序，能干净地全部删除。',
  'cl.better.winold': '更好的做法：Windows “磁盘清理” → “以前的 Windows 安装”。',
  'cl.better.chat': '更好的做法：打开这个应用，使用它自带的存储清理。',
  'cl.askTitle': '删除 {name}？', 'cl.iKnow': '我了解删除后的结果，仍要删除',
});

Object.assign(I18N.en, { 'cl.grid': 'Space map', 'cl.gridHint': 'each block is a folder, sized by its space — click one to find it in the list below', 'cl.gridRest': 'Smaller folders and files' });
Object.assign(I18N.zh, { 'cl.grid': '空间分布图', 'cl.gridHint': '每个方块是一个文件夹，面积代表占用空间——点击即可跳到下方列表中的对应项', 'cl.gridRest': '较小的文件夹和文件' });

// 2.5.0 finer kinds of file
Object.assign(I18N.en, {
  'cl.gridHint': 'blocks are folders sized by their space, split into their biggest subfolders — click one to find it in the list below', 'cl.gridFiles': 'Files and small folders',
  'cl.level.safe': 'Can be deleted',
  'cl.file.wsl': 'The virtual disk of a Linux system in WSL: the whole Linux installation and every file in it is lost.',
  'cl.file.docker': 'Docker\'s virtual disk: all images, containers and their data are lost.',
  'cl.file.phonebackup': 'An iPhone or iPad backup made with iTunes or Apple Devices. Without it the phone cannot be restored from this PC.',
  'cl.file.gamesave': 'A game save: your progress in that game can be lost unless the game keeps it in the cloud.',
  'cl.file.browser': 'Part of a browser profile — bookmarks, saved passwords, history, extensions or open tabs can be lost or the profile damaged.',
  'cl.file.browsercache': 'A browser\'s cache: copies of websites kept so they load faster. The browser downloads them again; nothing of yours is lost.',
  'cl.file.dump': 'A crash dump saved after a program or Windows crashed. Only needed to investigate that crash.',
  'cl.file.log': 'A log file a program wrote. Only needed to look into a problem.',
  'cl.file.pkgcache': 'A downloaded package in a developer tool\'s cache (npm, pip, Maven, NuGet, …). It is downloaded again when needed.',
  'cl.file.appcache': 'A cache or temporary file of an app. The app makes it again when needed.',
  'cl.file.database': 'An app\'s database — its saved data, not a cache. The app may lose data or stop working.',
  'cl.better.wsl': 'Better: remove the Linux distribution with "wsl --unregister" or in Settings → Apps, after backing up what you need.',
  'cl.better.docker': 'Better: clean up inside Docker Desktop (Troubleshoot → Clean / Purge data), or remove unused images there.',
  'cl.better.phonebackup': 'Better: delete old backups in iTunes / Apple Devices → Manage backups.',
  'cl.better.browser': 'Better: clear browsing data inside the browser — it only removes what you choose.',
});
Object.assign(I18N.zh, {
  'cl.gridHint': '每个方块是一个文件夹，面积代表占用空间，并细分为它最大的子文件夹——点击即可跳到下方列表中的对应项', 'cl.gridFiles': '文件和较小的文件夹',
  'cl.level.safe': '可以删除',
  'cl.file.wsl': 'WSL 中 Linux 系统的虚拟磁盘：整个 Linux 系统及其中的所有文件都会丢失。',
  'cl.file.docker': 'Docker 的虚拟磁盘：所有镜像、容器及其数据都会丢失。',
  'cl.file.phonebackup': '用 iTunes 或“Apple 设备”做的 iPhone / iPad 备份。删除后无法再用本机恢复手机。',
  'cl.file.gamesave': '游戏存档：除非游戏有云存档，否则这个游戏的进度可能丢失。',
  'cl.file.browser': '浏览器配置文件的一部分——书签、保存的密码、历史记录、扩展或打开的标签页可能丢失，配置文件可能损坏。',
  'cl.file.browsercache': '浏览器缓存：为加快打开网页保存的副本。浏览器会重新下载，你的东西不会丢失。',
  'cl.file.dump': '程序或 Windows 崩溃后保存的转储文件。只在分析那次崩溃时需要。',
  'cl.file.log': '程序写的日志文件。只在排查问题时需要。',
  'cl.file.pkgcache': '开发工具缓存中下载的软件包（npm、pip、Maven、NuGet 等）。需要时会重新下载。',
  'cl.file.appcache': '某个软件的缓存或临时文件。软件需要时会重新生成。',
  'cl.file.database': '某个软件的数据库——它保存的数据，不是缓存。软件可能丢失数据或无法工作。',
  'cl.better.wsl': '更好的做法：先备份需要的内容，再用“wsl --unregister”或在“设置 → 应用”中删除这个 Linux 发行版。',
  'cl.better.docker': '更好的做法：在 Docker Desktop 中清理（Troubleshoot → Clean / Purge data），或删除不用的镜像。',
  'cl.better.phonebackup': '更好的做法：在 iTunes /“Apple 设备”→“管理备份”中删除旧备份。',
  'cl.better.browser': '更好的做法：在浏览器中“清除浏览数据”——只删除你选择的内容。',
});

// 2.5.0, Gemini's 2.5.0 review
Object.assign(I18N.en, {
  'cl.file.draft': 'A recovery copy or unsaved draft (Office, WPS or another editor). After a crash it may be the only copy of unsaved work.',
  'cl.better.draft': 'Better: open the program it belongs to first — it usually offers to recover the document.',
  'cl.file.database': 'A database — saved data of a program, not a cache (its -wal / -shm / -journal files are part of it). Records can be lost or the database damaged.',
  'cl.recent': 'Changed in the last 24 hours: a program may be using it right now.',
  'cl.toBin': 'It goes to the Recycle Bin, so you can restore it.',
  'cl.tipTop': 'Click to find it in the list below', 'cl.tipSub': 'Click to open {dir} and find it there',
});
Object.assign(I18N.zh, {
  'cl.file.draft': '恢复副本或未保存的草稿（Office、WPS 等编辑软件）。程序崩溃后，它可能是未保存内容的唯一副本。',
  'cl.better.draft': '更好的做法：先打开它所属的程序，通常会提示恢复文档。',
  'cl.file.database': '数据库——程序保存的数据，不是缓存（同名的 -wal / -shm / -journal 文件是它的一部分）。记录可能丢失，数据库可能损坏。',
  'cl.recent': '最近 24 小时内修改过：可能正被某个程序使用。',
  'cl.toBin': '它会移到回收站，可以恢复。',
  'cl.tipTop': '点击在下方列表中定位', 'cl.tipSub': '点击进入 {dir} 并定位',
});

// 2.6.0 #1 Space Spikes Radar
Object.assign(I18N.en, {
  'gr.title': 'What grew recently', 'gr.days1': '24 hours', 'gr.days7': '7 days',
  'gr.lead': 'Between the full scans of {span} the drive grew by {total}. The folders that grew most:',
  'gr.leadShrunk': 'Between the full scans of {span} the drive shrank by {total}. Folders that still grew:',
  'gr.none': 'No folder grew by 100 MB or more.', 'gr.newFolder': 'new folder', 'gr.was': 'was {size}',
  'gr.notReady': 'Needs two full scans of this drive to compare ({n} so far). DeskTrace reads the drive again in the background every 12 hours while the PC is idle — or run a full scan now and another later.',
});
Object.assign(I18N.zh, {
  'gr.title': '最近哪里变大了', 'gr.days1': '24 小时', 'gr.days7': '7 天',
  'gr.lead': '在 {span} 的两次完整扫描之间，这个磁盘多用了 {total}。增长最多的文件夹：',
  'gr.leadShrunk': '在 {span} 的两次完整扫描之间，这个磁盘少用了 {total}。仍在增长的文件夹：',
  'gr.none': '没有文件夹增长 100 MB 以上。', 'gr.newFolder': '新文件夹', 'gr.was': '原为 {size}',
  'gr.notReady': '需要这个磁盘的两次完整扫描才能比较（目前 {n} 次）。电脑空闲时桌迹每 12 小时会在后台重新读取一次——也可以现在完整扫描一次，稍后再扫描一次。',
});

// 2.6.0 #18, #36
Object.assign(I18N.en, {
  'cl.item.otherbrowsers': 'Other browsers\' caches (Brave, Opera, Vivaldi, 360, QQ)',
  'cl.why.otherbrowsers': 'Copies of websites these browsers keep so pages load faster. Bookmarks, passwords and history are not deleted; files an open browser is using are skipped.',
  'cl.item.shaders': 'Graphics shader caches (NVIDIA, AMD, Intel, DirectX)',
  'cl.why.shaders': 'Compiled shaders the graphics driver keeps for games and apps. They are made again when needed — the first start of a game may take a little longer. Files changed in the last two days are left alone.',
});
Object.assign(I18N.zh, {
  'cl.item.otherbrowsers': '其他浏览器缓存（Brave、Opera、Vivaldi、360、QQ）',
  'cl.why.otherbrowsers': '这些浏览器为加快打开网页保存的副本。不会删除书签、密码和历史记录；正在运行的浏览器占用的文件会被跳过。',
  'cl.item.shaders': '显卡着色器缓存（NVIDIA、AMD、Intel、DirectX）',
  'cl.why.shaders': '显卡驱动为游戏和软件编译好的着色器。需要时会重新生成——游戏第一次启动可能稍慢。两天内修改过的文件不会动。',
});

// 2.6.0 #16 restorability
Object.assign(I18N.en, { 'rs.ok': 'Full copy kept', 'rs.okWhy': 'DeskTrace kept the whole file: Restore brings it back exactly as it was.',
  'rs.no': 'No copy — check the Recycle Bin', 'rs.noWhy': 'DeskTrace recorded the deletion but has no copy (too large, online-only, or removed to save space). It may still be in the Recycle Bin.' });
Object.assign(I18N.zh, { 'rs.ok': '有完整副本', 'rs.okWhy': '桌迹保存了整个文件：点“恢复”即可原样找回。',
  'rs.no': '无副本——请查看回收站', 'rs.noWhy': '桌迹记录了这次删除，但没有副本（文件过大、仅联机，或为节省空间已清除）。它可能仍在回收站中。' });

// 2.6.0 #17, #25, #49: Windows' own tools
Object.assign(I18N.en, {
  'wt.title': 'Windows tools', 'wt.cleanmgr': 'Disk Cleanup', 'wt.cleanmgrWhy': 'Windows\' own cleanup: update leftovers, previous Windows installation, system files (asks for administrator rights).',
  'wt.optimize': 'Optimize drives', 'wt.optimizeWhy': 'Windows\' "Optimize Drives": TRIM for SSDs, defragmentation for hard disks.',
  'wt.index': 'Search index', 'wt.indexWhy': 'Indexing Options: choose what Windows Search indexes, or rebuild an index that has grown very large (Advanced → Rebuild).',
  'cl.hiberReduced': 'Make it smaller', 'cl.hiberReducedWhy': 'A reduced hibernation file keeps fast startup but not hibernate; it takes about half the space. Windows asks for administrator rights.',
  'cl.hiberAsked': 'Windows asks for permission; the space changes once it is done.',
});
Object.assign(I18N.zh, {
  'wt.title': 'Windows 工具', 'wt.cleanmgr': '磁盘清理', 'wt.cleanmgrWhy': 'Windows 自带的清理：更新残留、以前的 Windows 安装、系统文件（需要管理员权限）。',
  'wt.optimize': '优化驱动器', 'wt.optimizeWhy': 'Windows 的“优化驱动器”：固态硬盘执行 TRIM，机械硬盘进行碎片整理。',
  'wt.index': '搜索索引', 'wt.indexWhy': '索引选项：选择 Windows 搜索要索引的位置，或重建体积过大的索引（高级 → 重建）。',
  'cl.hiberReduced': '缩小休眠文件', 'cl.hiberReducedWhy': '精简的休眠文件保留快速启动、但不能休眠，约占一半空间。Windows 会请求管理员权限。',
  'cl.hiberAsked': 'Windows 会请求许可；完成后空间才会变化。',
});

// 2.6.0 #8
Object.assign(I18N.en, {
  'cl.item.devprojects': 'Dependencies of old projects (node_modules, Rust target, Python venv)',
  'cl.why.devprojects': 'Folders a build tool fills again — node_modules next to package.json, Rust target next to Cargo.toml, Python virtual environments — in projects you have not changed for 30 days. Your source code is not touched; run npm install, cargo build or recreate the venv to get them back.',
});
Object.assign(I18N.zh, {
  'cl.item.devprojects': '旧项目的依赖（node_modules、Rust target、Python 虚拟环境）',
  'cl.why.devprojects': '构建工具会重新生成的文件夹——package.json 旁的 node_modules、Cargo.toml 旁的 Rust target、Python 虚拟环境——只限 30 天未改动的项目。不会动你的源代码；需要时运行 npm install、cargo build 或重建虚拟环境即可。',
});

// 2.6.0 #40
Object.assign(I18N.en, { 'rb.btn': 'Undo these {n} renames', 'rb.title': 'Give {n} files their old names back?',
  'rb.text': 'Each file gets the name (and folder) it had before. A file whose old name is in use again, or that is gone or open in another program, is left as it is — nothing is overwritten.',
  'rb.go': 'Rename back', 'rb.done': '{n} files have their old names again.', 'rb.partly': '{n} files renamed back; {m} left as they are (old name in use, gone or open elsewhere).' });
Object.assign(I18N.zh, { 'rb.btn': '撤销这 {n} 次重命名', 'rb.title': '把 {n} 个文件改回原来的名字？',
  'rb.text': '每个文件都会改回之前的名字（和文件夹）。原名字已被占用、文件已不存在或正被其他程序打开时，该文件保持不变——不会覆盖任何文件。',
  'rb.go': '改回原名', 'rb.done': '已有 {n} 个文件改回原名。', 'rb.partly': '已改回 {n} 个；{m} 个保持不变（原名已被占用、文件不存在或正被打开）。' });

// 2.6.0 #6 mass change guard
Object.assign(I18N.en, {
  'warn.mass': 'Many files changed at once:', 'warn.massWhy': 'within seconds, many files in your folders were changed, deleted or renamed — a script gone wrong, a sync conflict or ransomware can do this. DeskTrace kept their earlier versions.',
  'mass.restore': 'Put them all back', 'mass.dismiss': 'That was me',
  'mass.title': 'Put {n} changes back?', 'mass.text': 'Every file changed, deleted or renamed between {from} and {to} gets back the version it had just before. A changed file is replaced (its current content stays in the history, so this can be undone too); deleted files come back; renamed files get their old names. New files are left alone. If this is ransomware, first disconnect the PC from the network.',
  'mass.go': 'Put them all back', 'mass.done': '{n} files put back as they were. {m} could not be (no earlier copy, in use, or the name is taken).',
});
Object.assign(I18N.zh, {
  'warn.mass': '大量文件同时发生变化：', 'warn.massWhy': '几秒钟内，你的文件夹中有大量文件被修改、删除或重命名——出错的脚本、同步冲突或勒索病毒都可能造成这种情况。桌迹保存了它们之前的版本。',
  'mass.restore': '全部恢复', 'mass.dismiss': '是我自己做的',
  'mass.title': '恢复这 {n} 处变化？', 'mass.text': '{from} 到 {to} 之间被修改、删除或重命名的每个文件，都会恢复为变化之前的版本：被修改的文件会被替换（当前内容仍保留在历史中，所以这一步也可以撤销）；被删除的文件会找回；被重命名的文件改回原名。新建的文件不会动。如果怀疑是勒索病毒，请先断开网络。',
  'mass.go': '全部恢复', 'mass.done': '已将 {n} 个文件恢复原样。{m} 个无法恢复（没有更早的副本、正被使用，或原名已被占用）。',
});

// 2.6.0 #34
Object.assign(I18N.en, { 'dk.ok': 'healthy', 'dk.bad': 'Windows reports "{s}" — back up your files now',
  'dk.why': 'The disk\'s own health as Windows reports it. Detailed wear and error counters need administrator rights and are not shown.' });
Object.assign(I18N.zh, { 'dk.ok': '健康', 'dk.bad': 'Windows 报告“{s}”——请立即备份文件',
  'dk.why': 'Windows 报告的磁盘自身健康状态。详细的磨损和错误计数需要管理员权限，这里不显示。' });

// 2.6.0 #33
Object.assign(I18N.en, { 'cl.item.oldinstallers': 'Older versions of installers in Downloads',
  'cl.why.oldinstallers': 'Setup files that have a newer version of the same program next to them in Downloads. The newest one stays; the older ones go to the Recycle Bin.' });
Object.assign(I18N.zh, { 'cl.item.oldinstallers': '下载文件夹中安装包的旧版本',
  'cl.why.oldinstallers': '下载文件夹中同一软件已有更新版本的安装包。保留最新的一个，旧的移到回收站。' });

// 2.6.0 #12
Object.assign(I18N.en, { 'cl.item.brokenlinks': 'Broken shortcuts and empty folders',
  'cl.why.brokenlinks': 'Shortcuts on the Desktop and in the Start menu whose program or file no longer exists (left by uninstalled programs), and folders in Downloads with nothing inside. They go to the Recycle Bin.' });
Object.assign(I18N.zh, { 'cl.item.brokenlinks': '失效的快捷方式和空文件夹',
  'cl.why.brokenlinks': '桌面和开始菜单中指向的程序或文件已不存在的快捷方式（多为已卸载软件留下的），以及下载文件夹中完全为空的文件夹。它们会移到回收站。' });

// 2.6.0 #2
Object.assign(I18N.en, { 'lo.title': 'Possibly left by uninstalled programs', 'lo.hint': 'folders in AppData / ProgramData whose name matches no installed program — check before deleting',
  'lo.del': 'Delete', 'lo.askTitle': 'Delete the folder {name}?',
  'lo.askText': '{path} ({size}) matches no installed program, so it was probably left behind when a program was uninstalled. A program that is still in use may keep its data here under a different name — then its settings or data are lost. The folder goes to the Recycle Bin and can be restored from there.',
  'lo.done': '{name} moved to the Recycle Bin ({size}).' });
Object.assign(I18N.zh, { 'lo.title': '可能是已卸载软件的残留', 'lo.hint': 'AppData / ProgramData 中名字与任何已安装软件都对不上的文件夹——删除前请确认',
  'lo.del': '删除', 'lo.askTitle': '删除文件夹 {name}？',
  'lo.askText': '{path}（{size}）与任何已安装的软件都对不上，很可能是卸载软件时留下的。但仍在使用的软件也可能用别的名字把数据放在这里——那样它的设置或数据会丢失。文件夹会移到回收站，可以从回收站恢复。',
  'lo.done': '已将 {name} 移到回收站（{size}）。' });

// 2.6.0 #19
Object.assign(I18N.en, { 'err.lockedBy': 'It is open in: {apps}.' });
Object.assign(I18N.zh, { 'err.lockedBy': '正在使用它的程序：{apps}。' });

// 2.6.0 #20
Object.assign(I18N.en, { 'pin.add': 'Keep forever', 'pin.remove': 'Kept forever', 'pin.why': 'Every version of this file is kept, whatever the history limits say, and Clean up never deletes it.',
  'pin.done': 'Every version of {name} is kept forever now.', 'pin.undone': '{name} follows the normal history limits again.',
  'err.pinned': 'This file is set to "Keep forever". Switch that off first if you really want to remove it.' });
Object.assign(I18N.zh, { 'pin.add': '永久保留', 'pin.remove': '已永久保留', 'pin.why': '这个文件的每个版本都会保留，不受历史记录期限和空间上限影响；空间清理也绝不会删除它。',
  'pin.done': '{name} 的每个版本现在都会永久保留。', 'pin.undone': '{name} 恢复按普通的历史记录期限保留。',
  'err.pinned': '这个文件已设为“永久保留”。如确实要删除，请先取消永久保留。' });

// 2.6.0 #9
Object.assign(I18N.en, { 'cl.item.winupgrade': 'Windows upgrade leftovers ($Windows.~BT, $Windows.~WS, $SysReset)',
  'cl.why.winupgrade': 'Files Windows kept from an upgrade or a reset. Once the upgrade is finished they are not needed; Windows Disk Cleanup (Clean up system files → Temporary Windows installation files / Windows upgrade log files) removes them with administrator rights.' });
Object.assign(I18N.zh, { 'cl.item.winupgrade': 'Windows 升级残留（$Windows.~BT、$Windows.~WS、$SysReset）',
  'cl.why.winupgrade': 'Windows 升级或重置时保留的文件。升级完成后就不再需要；用 Windows“磁盘清理”（清理系统文件 → 临时 Windows 安装文件 / Windows 升级日志文件）可以用管理员权限删除。' });

// 2.6.0 #15
Object.assign(I18N.en, { 'cl.item.compress': 'Compress large old files (nothing is deleted)', 'cl.how.compress': 'Compressed · stays usable',
  'cl.why.compress': 'Logs, text, CSV, SQL, uncompressed pictures and sound of 20 MB or more in your folders, unchanged for 90 days. Windows\' own NTFS compression makes them take less space — often about half — while they open and work exactly as before. Nothing is deleted; "Uncompress" in the file\'s Properties undoes it.' });
Object.assign(I18N.zh, { 'cl.item.compress': '压缩体积大的旧文件（不删除任何文件）', 'cl.how.compress': '压缩 · 照常使用',
  'cl.why.compress': '你文件夹中 20 MB 以上、90 天未修改的日志、文本、CSV、SQL、未压缩的图片和音频。用 Windows 自带的 NTFS 压缩减少占用空间——通常约一半——打开和使用完全照旧。不删除任何文件；在文件“属性”中取消压缩即可还原。' });

// 2.6.0 #29
Object.assign(I18N.en, { 'git.title': 'Large Git repositories', 'git.hint': 'their history (.git) takes a lot of space',
  'git.gc': 'Tidy up', 'git.gcWhy': 'Runs Git\'s own clean-up (git gc --prune=now): packs the history and removes what nothing refers to. Your files and commits stay.',
  'git.running': 'Tidying…', 'git.done': 'Git tidied the repository: {size} freed.', 'git.failed': 'Git could not tidy this repository (is another Git program using it?).',
  'git.noGit': 'Git is not installed, so DeskTrace cannot tidy them; the sizes are shown for information.' });
Object.assign(I18N.zh, { 'git.title': '体积很大的 Git 仓库', 'git.hint': '它们的历史（.git）占用了大量空间',
  'git.gc': '整理', 'git.gcWhy': '运行 Git 自带的整理（git gc --prune=now）：打包历史，删除不再被引用的内容。你的文件和提交都会保留。',
  'git.running': '正在整理…', 'git.done': 'Git 已整理这个仓库，释放 {size}。', 'git.failed': 'Git 无法整理这个仓库（是否有其他 Git 程序正在使用它？）。',
  'git.noGit': '未安装 Git，桌迹无法整理它们；这里只显示大小供参考。' });

// 2.6.0 #22 Outlook data files
Object.assign(I18N.en, {
  'cl.better.pst': 'Better: in Outlook use File → Tools → Mailbox Cleanup (or Clean Up Old Items to archive), empty Deleted Items, then File → Account Settings → Data Files → Settings → Compact Now.',
  'cl.better.ost': 'Better: in Outlook, Account Settings → change "Mail to keep offline" to a shorter period (for example 1 year); Outlook shrinks the file itself. Deleting it makes Outlook download the whole mailbox again.' });
Object.assign(I18N.zh, {
  'cl.better.pst': '更好的做法：在 Outlook 中使用“文件 → 工具 → 邮箱清理”（或“清理旧项目”进行归档），清空“已删除邮件”，然后“文件 → 账户设置 → 数据文件 → 设置 → 立即压缩”。',
  'cl.better.ost': '更好的做法：在 Outlook“账户设置”中把“脱机保留的邮件”改为较短的时间（例如 1 年），Outlook 会自行缩小这个文件。删除它会让 Outlook 重新下载整个邮箱。' });

// 2.6.0 #44
Object.assign(I18N.en, { 'mv.export': 'Export for another PC…', 'mv.exportWhy': 'The whole history — every kept version, changes, notes and settings — as one .dtbackup file.',
  'mv.import': 'Import from another PC…', 'mv.importWhy': 'Use a .dtbackup file made on another PC. It takes effect the next time DeskTrace starts; the history on this PC is kept aside, not deleted.',
  'mv.staged': 'The imported history is ready. Quit DeskTrace and open it again to use it; the history that was here is kept in a folder next to it.',
  'err.notBackup': 'This is not a DeskTrace history file.', 'err.damaged': 'This history file is damaged; nothing was changed.', 'err.busy': 'A backup is already running.' });
Object.assign(I18N.zh, { 'mv.export': '导出到新电脑…', 'mv.exportWhy': '把整个历史记录——所有保存的版本、变化记录、备注和设置——打包成一个 .dtbackup 文件。',
  'mv.import': '从旧电脑导入…', 'mv.importWhy': '使用在另一台电脑上导出的 .dtbackup 文件。下次启动桌迹时生效；本机原有的历史记录会另存一份，不会删除。',
  'mv.staged': '导入的历史记录已准备好。退出桌迹并重新打开即可使用；本机原来的历史记录会保存在旁边的文件夹中。',
  'err.notBackup': '这不是桌迹的历史记录文件。', 'err.damaged': '这个历史记录文件已损坏，没有做任何改动。', 'err.busy': '已有一个备份正在进行。' });

// 2.6.0 #31
Object.assign(I18N.en, { 'fa.lead': 'Need this whole folder as it was at an earlier time?', 'fa.btn': 'Folder as of a time',
  'fa.title': '{name} as it was at…', 'fa.text': 'DeskTrace writes the folder as it was at that moment — every file that existed then, in the version it had then — into a new folder next to it. Nothing in the folder itself is changed.',
  'fa.go': 'Write the copy', 'fa.done': '{n} files written to {path}. {m} had no kept copy from that time.' });
Object.assign(I18N.zh, { 'fa.lead': '需要把整个文件夹恢复到之前某个时刻的样子？', 'fa.btn': '文件夹某一时刻的样子',
  'fa.title': '{name} 在某一时刻的样子', 'fa.text': '桌迹会把文件夹在那一时刻的样子——当时存在的每个文件、当时的版本——写入旁边的一个新文件夹。原文件夹不会有任何改动。',
  'fa.go': '写出副本', 'fa.done': '已将 {n} 个文件写入 {path}。{m} 个文件没有那个时刻的副本。' });

// 2.6.0 #26
Object.assign(I18N.en, { 'rep.btn': 'Export comparison', 'rep.why': 'Save this change as a web page: removed lines red, added lines green, changed words marked — to send or print.',
  'rep.done': 'Comparison saved: {path}', 'err.noDiff': 'There is no text comparison for this change.' });
Object.assign(I18N.zh, { 'rep.btn': '导出对比报告', 'rep.why': '把这次修改保存为网页：删除的行为红色、新增的行为绿色、改动的词会标出——方便发送或打印。',
  'rep.done': '对比报告已保存：{path}', 'err.noDiff': '这次修改没有可对比的文字内容。' });

// 2.6.0 #13
Object.assign(I18N.en, { 'hl.btn': 'Keep all, store once', 'hl.why': 'Every copy stays where it is under its name, but the disk holds the content only once (NTFS hard links).',
  'hl.title': 'Store these {n} copies once?', 'hl.text': 'Every copy keeps its name and place, and programs find them as before — but they become one file on the disk. From then on, editing any of them changes all of them. Copies on another drive, changed meanwhile or open in a program are left as they are.',
  'hl.go': 'Store once', 'hl.done': '{n} copies now share one file: {size} freed. {m} left as they were.',
  'err.notNtfs': 'This drive does not support hard links (it is not NTFS).' });
Object.assign(I18N.zh, { 'hl.btn': '全部保留，只占一份空间', 'hl.why': '每个副本都留在原处、名字不变，但磁盘上只保存一份内容（NTFS 硬链接）。',
  'hl.title': '让这 {n} 个副本只占一份空间？', 'hl.text': '每个副本的名字和位置都不变，程序照常能找到它们——但它们在磁盘上会变成同一个文件。从此修改其中任何一个，其他的也会一起改变。位于其他磁盘、期间被修改过或正被程序打开的副本保持不变。',
  'hl.go': '只占一份空间', 'hl.done': '已有 {n} 个副本共用一个文件，释放 {size}。{m} 个保持不变。',
  'err.notNtfs': '这个磁盘不支持硬链接（不是 NTFS）。' });

// 2.6.0 #3
Object.assign(I18N.en, { 'mvf.btn': 'Move to another drive', 'mvf.why': 'Moves the folder to another drive and leaves a link in its place, so programs find it as before.',
  'mvf.title': 'Move {name} to another drive?', 'mvf.text': 'The folder ({size}) is copied to the drive you choose, every file is checked against the original, and a link (NTFS junction) is put in its place — programs keep using the same path. Only then is the original deleted. Close the programs using it first; if a file is open, nothing happens. You can move it back any time.',
  'mvf.noDrive': 'No other fixed NTFS drive has enough free space.', 'mvf.sure': 'Close programs using this folder; I understand it is moved', 'mvf.go': 'Move',
  'mvf.step.start': 'Starting…', 'mvf.step.copy': 'Copying {total} files…', 'mvf.step.verify': 'Checking {n} of {total} files…',
  'mvf.done': 'Folder moved; its old place now links to the new one.', 'mvf.failed': 'The folder was not moved and is as it was ({why}).',
  'mvf.listTitle': 'Folders moved to another drive', 'mvf.back': 'Move back', 'mvf.backTitle': 'Move this folder back?', 'mvf.backText': 'The folder is copied back, checked, and the copy on the other drive is removed.',
  'err.noSpace': 'Not enough free space on that drive.', 'err.moveFailed': 'The move did not work; nothing was changed.' });
Object.assign(I18N.zh, { 'mvf.btn': '搬到其他磁盘', 'mvf.why': '把文件夹移到其他磁盘，并在原位置留一个链接，程序照常能找到它。',
  'mvf.title': '把 {name} 搬到其他磁盘？', 'mvf.text': '文件夹（{size}）会复制到你选择的磁盘，逐个文件与原文件比对，然后在原位置放一个链接（NTFS 目录联接）——程序继续使用原来的路径。之后才删除原文件夹。请先关闭使用它的程序；如有文件正被打开，什么都不会发生。随时可以搬回来。',
  'mvf.noDrive': '没有其他空间足够的 NTFS 固定磁盘。', 'mvf.sure': '已关闭使用这个文件夹的程序，我知道它会被搬走', 'mvf.go': '搬家',
  'mvf.step.start': '正在开始…', 'mvf.step.copy': '正在复制 {total} 个文件…', 'mvf.step.verify': '正在核对第 {n} / {total} 个文件…',
  'mvf.done': '文件夹已搬走；原位置现在链接到新位置。', 'mvf.failed': '文件夹没有搬走，保持原样（{why}）。',
  'mvf.listTitle': '已搬到其他磁盘的文件夹', 'mvf.back': '搬回来', 'mvf.backTitle': '把这个文件夹搬回来？', 'mvf.backText': '文件夹会复制回来并核对，然后删除其他磁盘上的那份。',
  'err.noSpace': '那个磁盘的可用空间不够。', 'err.moveFailed': '搬家没有成功，没有做任何改动。' });

// 2.6.0 #24
Object.assign(I18N.en, { 'dr.title': 'Unsaved drafts from the last 7 days', 'dr.lead': 'Recovery copies Office and WPS kept after a crash or when a document was closed without saving. Save a copy to open it safely.',
  'dr.save': 'Save a copy', 'dr.saved': 'Copy saved: {path}' });
Object.assign(I18N.zh, { 'dr.title': '最近 7 天未保存的草稿', 'dr.lead': 'Office 和 WPS 在程序崩溃或未保存就关闭文档时留下的恢复副本。先保存一份副本再打开，更安全。',
  'dr.save': '保存一份副本', 'dr.saved': '副本已保存：{path}' });

// 2.6.0 #50
Object.assign(I18N.en, { 'ms.restored': 'DeskTrace has now brought back {n} files for you.', 'ms.freed': 'Clean up has now freed {n} on your drives.' });
Object.assign(I18N.zh, { 'ms.restored': '桌迹已经帮你找回了 {n} 个文件。', 'ms.freed': '空间清理已经为你的磁盘腾出了 {n}。' });

Object.assign(I18N.en, { 'set.milestones': 'Milestone cards', 'set.milestonesHint': 'A short note when DeskTrace has brought back 10, 100 or 1000 files, or Clean up has freed 10 GB, 100 GB or 1 TB.' });
Object.assign(I18N.zh, { 'set.milestones': '里程碑提示', 'set.milestonesHint': '桌迹找回 10、100、1000 个文件，或空间清理腾出 10 GB、100 GB、1 TB 时，显示一条简短提示。' });

// 2.6.0 #7
Object.assign(I18N.en, { 'ch.btn': 'Old received pictures and videos', 'ch.title': '{app}: old received media',
  'ch.text': 'Pictures, videos and files you received in chats, and the app\'s caches — only those older than the period below. They go to the Recycle Bin. In the chats they show as expired or need downloading again, and some may no longer be available.',
  'ch.older': 'Older than', 'ch.days': '{n} days', 'ch.k.picture': 'Pictures', 'ch.k.video': 'Videos', 'ch.k.file': 'Received files', 'ch.k.cache': 'Caches (moments, thumbnails, temporary files)',
  'ch.never': 'Chat history (the databases), settings and backups are never touched.', 'ch.done': '{n} files moved to the Recycle Bin, {size} freed once it is emptied.' });
Object.assign(I18N.zh, { 'ch.btn': '清理收到的旧图片和视频', 'ch.title': '{app}：收到的旧媒体文件',
  'ch.text': '聊天中收到的图片、视频、文件，以及应用的缓存——只限下面所选时间以前的。它们会移到回收站。聊天中这些内容会显示为过期或需要重新下载，有些可能已无法再下载。',
  'ch.older': '早于', 'ch.days': '{n} 天', 'ch.k.picture': '图片', 'ch.k.video': '视频', 'ch.k.file': '收到的文件', 'ch.k.cache': '缓存（朋友圈、缩略图、临时文件）',
  'ch.never': '聊天记录（数据库）、设置和备份绝不会动。', 'ch.done': '已将 {n} 个文件移到回收站，清空回收站后释放 {size}。' });

// 2.6.0 #27, #28
Object.assign(I18N.en, { 'lp.title': 'Language packs of programs ({size})', 'lp.hint': 'languages other than English and Chinese that programs carry — shown for information: removing them breaks updates of some programs, so DeskTrace does not offer it',
  'cl.better.wsl': 'Better: to make the disk smaller without losing anything, run "wsl --manage <distribution> --set-sparse true" (WSL 2.0 or later) or, with WSL shut down, Optimize-VHD in an administrator PowerShell. To remove the distribution, back up first, then "wsl --unregister".',
  'cl.better.docker': 'Better: in Docker Desktop use Troubleshoot → Clean / Purge data, or remove unused images; Docker Desktop also compacts its disk itself (Settings → Resources).' });
Object.assign(I18N.zh, { 'lp.title': '软件语言包（{size}）', 'lp.hint': '各软件自带的英文和中文以外的语言——仅供参考：删除会导致部分软件更新出错，所以桌迹不提供删除',
  'cl.better.wsl': '更好的做法：想在不丢失任何内容的情况下缩小磁盘，可运行“wsl --manage <发行版> --set-sparse true”（WSL 2.0 及以上），或在关闭 WSL 后用管理员 PowerShell 运行 Optimize-VHD。要删除发行版，请先备份，再运行“wsl --unregister”。',
  'cl.better.docker': '更好的做法：在 Docker Desktop 中使用 Troubleshoot → Clean / Purge data，或删除不用的镜像；Docker Desktop 也会自行压缩它的磁盘（设置 → Resources）。' });

// 2.6.0 #35
Object.assign(I18N.en, { 'bn.title': 'Names Windows cannot handle', 'bn.hint': 'Explorer cannot open, rename or delete these',
  'bn.trailing': 'name ends with a space or a dot', 'bn.long': 'path longer than 260 characters', 'bn.fix': 'Fix the name',
  'bn.done': 'Renamed: {path}' });
Object.assign(I18N.zh, { 'bn.title': 'Windows 无法处理的文件名', 'bn.hint': '资源管理器无法打开、重命名或删除它们',
  'bn.trailing': '名字以空格或句点结尾', 'bn.long': '路径超过 260 个字符', 'bn.fix': '修正名字',
  'bn.done': '已重命名：{path}' });

// 2.6.0 #30
Object.assign(I18N.en, { 'cd.title': 'Cloud-synced folders', 'cd.hint': 'size = what is stored on this PC', 'cd.counts': '{n} on this PC, {m} online only',
  'cd.free': 'Keep all online only', 'cd.why': 'Frees the copies on this PC; every file stays in the cloud and in the folder, and downloads again when you open it.',
  'cd.askTitle': 'Keep every file of this folder online only?', 'cd.askText': 'The cloud service removes the copies from this PC. Every file stays in the cloud and shows in the folder as before; opening one downloads it (internet needed). Files you marked "Always keep on this device" are included.',
  'cd.done': 'Asked the cloud service to free the copies; the space comes back as it works through them.' });
Object.assign(I18N.zh, { 'cd.title': '云同步文件夹', 'cd.hint': '大小 = 存在本机上的部分', 'cd.counts': '本机 {n} 个，仅联机 {m} 个',
  'cd.free': '全部仅保留在线', 'cd.why': '释放本机上的副本；每个文件仍保留在云端和文件夹中，打开时会重新下载。',
  'cd.askTitle': '让这个文件夹的所有文件仅保留在线？', 'cd.askText': '云服务会删除本机上的副本。每个文件仍保留在云端，并照常显示在文件夹中；打开时会下载（需要联网）。标记为“始终保留在此设备上”的文件也包括在内。',
  'cd.done': '已请云服务释放副本；它处理完后空间会逐渐回来。' });

// 2.6.0 #14
Object.assign(I18N.en, { 'help.hotkey': 'Anywhere in Windows: today\'s deleted and overwritten files' });
Object.assign(I18N.zh, { 'help.hotkey': '在 Windows 任何地方：今天删除和被覆盖的文件' });

// 2.6.0 #21
Object.assign(I18N.en, { 'usb.text': '{d} {label} plugged in: {free} free of {total}. To keep versions of files on it, add one of its folders in Settings → Folders.', 'usb.look': 'See what is on it' });
Object.assign(I18N.zh, { 'usb.text': '已插入 {d} {label}：可用 {free}，共 {total}。如要为它上面的文件保留历史版本，请在“设置 → 文件夹”中添加它的文件夹。', 'usb.look': '查看空间' });

// 2.6.0 #11
Object.assign(I18N.en, { 'sc.btn': 'Time slider', 'sc.noText': 'No text preview for this version.' });
Object.assign(I18N.zh, { 'sc.btn': '时间轴', 'sc.noText': '这个版本没有文字预览。' });

// 2.6.0 #38
Object.assign(I18N.en, { 'lt.btn': 'Evolution', 'lt.lead': '{n} versions of this file (dots, oldest on the left) and {m} other files that started as a copy of one of them (branches).' });
Object.assign(I18N.zh, { 'lt.btn': '演变图', 'lt.lead': '这个文件的 {n} 个版本（圆点，最早的在左），以及 {m} 个由其中某个版本复制而来的其他文件（分支）。' });

// 2.6.0 #32
Object.assign(I18N.en, { 'sim.btn': 'Similar photos', 'sim.title': 'Similar photos', 'sim.reading': 'Looking at {n} of {total} pictures…',
  'sim.lead': '{n} groups of pictures that look alike (burst shots, edits, resized copies). The biggest one of each group is marked; the others can go to the Recycle Bin.',
  'sim.best': 'Biggest', 'sim.none': 'No similar pictures among {n} pictures in your folders.' });
Object.assign(I18N.zh, { 'sim.btn': '相似照片', 'sim.title': '相似照片', 'sim.reading': '正在查看第 {n} / {total} 张图片…',
  'sim.lead': '{n} 组看起来相似的图片（连拍、修图、缩放后的副本）。每组中分辨率最高的一张已标出；其余的可以移到回收站。',
  'sim.best': '最清晰', 'sim.none': '你文件夹中的 {n} 张图片里没有相似的。' });

// Gemini 2.6.0 review
Object.assign(I18N.en, {
  'dw.title': 'More checks and findings', 'dw.count': '{n} found', 'dw.more': '· up to {size} could be freed',
  'lo.title': 'Program folders unused for a long time (possibly left by uninstalled programs)', 'lo.open': 'Open to check',
  'lo.hint': 'their name matches no installed program and nothing in them changed for 90 days — open and check before deleting',
  'lo.askText': 'DeskTrace cannot be 100 % sure that the program of {path} ({size}) was uninstalled. If it is still in use, it may need to be set up again or download its data again. The folder goes to the Recycle Bin — if a program misbehaves afterwards, put it back from there.',
  'mvf.busy': 'Not moved: {apps} has files in this folder open. Quit it and try again.',
  'mvf.leftover': 'Folder moved, but its old copy could not be fully deleted (a program still had a file open): {path}. Delete it once that program is closed.',
  'mvf.step.check': 'Checking whether a program uses the folder…' });
Object.assign(I18N.zh, {
  'dw.title': '专项体检与扩展发现', 'dw.count': '发现 {n} 项', 'dw.more': '· 最多可腾出 {size}',
  'lo.title': '长期未使用的软件文件夹（可能是已卸载软件的残留）', 'lo.open': '打开查看',
  'lo.hint': '名字与任何已安装的软件都对不上，且 90 天内没有改动——请先打开确认再删除',
  'lo.askText': '桌迹无法 100% 确认 {path}（{size}）所属的软件已被卸载。如果它仍在使用，删除后该软件可能需要重新设置或重新下载数据。文件夹会放入回收站——若之后发现软件异常，可随时从回收站放回原处。',
  'mvf.busy': '没有搬家：{apps} 正在使用这个文件夹中的文件。请先退出它再试。',
  'mvf.leftover': '文件夹已搬走，但原来的副本没能完全删除（有程序仍打开着其中的文件）：{path}。请在关闭那个程序后删除它。',
  'mvf.step.check': '正在检查是否有程序在使用这个文件夹…' });

let LANG = 'en';

function t(key, vars = {}) {
  let s = I18N[LANG][key] ?? I18N.en[key] ?? key;
  if (typeof s === 'object') s = (vars.n === 1 ? s.one : s.other) ?? s.other;
  return s.replace(/\{(\w+)\}/g, (m, k) => (k in vars ? vars[k] : m));
}

/* Unit word for a count ("3 paragraphs"), or the capitalised form for headings. */
function unitWord(u, n) { return t('u.' + u, { n }); }
function unitCap(u) { return (I18N[LANG]['u.' + u] || I18N.en['u.' + u]).cap; }

function detectLang() {
  const n = (navigator.language || 'en').toLowerCase();
  return n.startsWith('zh') ? 'zh' : 'en';
}
