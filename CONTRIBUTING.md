# Contributing

Thank you for helping. 欢迎用中文或英文提交问题和建议。

## Reporting a problem
Open an issue with the *Bug report* template and include:
- the DeskTrace version (Settings → About) and Windows version;
- what you did, what you expected, what happened;
- if you can, Settings → *Diagnostics* → *Copy* (it lists no file contents).

## Changing the code
- DeskTrace runs on the **Python 3.12 standard library**; please keep it that way (the only extra is the optional `pypdf`).
- Try changes on a separate history folder so your own history stays untouched:
  `python desktop_watch\server.py --data %TEMP%\dt-try --port 8899`
- Every user-visible text is in `desktop_watch/static/i18n.js` in **English and 简体中文** — add both.
- Never delete a user's file without the Recycle Bin or an explicit, clearly worded confirmation.
- Keep data written by older versions readable.
- Describe the change for the changelog with a level (1 Fix … 5 New) in English and Chinese.
