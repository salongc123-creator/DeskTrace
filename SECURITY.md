# Security policy

DeskTrace keeps copies of your files, so security reports matter. Please **do not open a public issue** for a
vulnerability. Report it privately through GitHub: *Security → Report a vulnerability* on this repository.
Include the version (Settings → About), what you did and what happened. You will get an answer within a week.

## Design notes
- The local service listens only on `127.0.0.1` and requires a random per-start token; it serves only DeskTrace's own window.
- Kept versions live in `%LOCALAPPDATA%\DeskTrace`, readable only by your Windows account.
- Version licenses (`.dtlicense`) are verified against a public key built into the app before anything is installed.
  The private signing key is not in this repository.
- DeskTrace never elevates itself; actions that need administrator rights are handed to Windows, which asks you.
