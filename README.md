# fast-project-backup

**Fast ZIP backup tool with GUI progress bar for multi-GB projects**

A Python desktop application that creates timestamped ZIP backups of project directories with real-time progress tracking. Optimized for speed using no-compression storage and ZIP64 support for large codebases.

## Features

- 🚀 **Lightning fast** - Uses ZIP_STORED (no compression) for maximum I/O throughput
- 📊 **Real-time progress** - Responsive GUI with determinate progress bar showing MB/s
- 💾 **Large file support** - ZIP64 enabled for archives > 4GB and 65k+ files
- 🖥️ **Dual interface** - Desktop GUI and headless CLI for automation
- 📁 **Smart excludes** - Skip heavy folders like node_modules, .git, venv automatically
- ⏰ **Timestamped backups** - Archives named with YYYYMMDD-HHMMSS format

## Quick Start

### GUI Mode
