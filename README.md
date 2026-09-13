# GloryDial Studio

<img width="1442" height="1347" alt="Screenshot 2026-09-13 122207" src="https://github.com/user-attachments/assets/849a61dc-bdb6-43f6-ae14-79c4df0e9112" />

Open-source watch face editor for UTE/GloryFit-compatible .bin watch faces, with support for multiple devices and compression versions.

GloryDial Studio is designed to provide a more capable and user-friendly alternative to older watch face editing tools such as ClockFaceEdit, while maintaining compatibility with the watch face formats used by real devices.

> **Status:** Early development / actively evolving
---
> **License:** GNU General Public License v3.0

---

## Features

* Create and edit `.bin` watch faces
* Import existing watch face files
* Edit watch face elements and their properties
* Support for digital and analog watch face components
* Watch hands and digit-based time displays
* Image-based watch face elements
* Live watch face preview
* Export `.bin` watch face files
* Compatible with ClockFaceEdit
* Designed to support multiple watch/firmware formats rather than being locked to a single device
* Modern desktop interface built with Python and PyQt6

---

## Project Goals

GloryDial Studio was created to make working with proprietary smart-watch face formats easier.

The project aims to:

1. Provide a modern replacement for older watch face editors.
2. Make `.bin` watch face creation accessible without manually editing binary data.
3. Preserve compatibility with existing watch face tools where possible.
4. Support multiple watch face formats and device variants.
5. Provide accurate previews before transferring a face to a watch.
6. Eventually provide a complete workflow from importing a watch face to editing, previewing, and exporting it.

---

## The Origin of the Tool
This tool was originally made for my K72 Rugged Smartwatch. After further analysis, more devices have been added.
<img width="380" height="439" alt="Screenshot 2026-09-13 121802" src="https://github.com/user-attachments/assets/2f08341b-15b5-42c7-9ac6-f288353a205c" />

---

## File Format

GloryDial Studio works with watch face `.bin` files.

The project was developed through analysis of existing watch face files and the open-source **ClockFaceEdit** implementation.

A `.bin` watch face contains a header followed by the compressed watch face payload.

The known header structure includes:

| Offset |     Size | Description                         |
| -----: | -------: | ----------------------------------- |
| `0x00` |  4 bytes | Opaque file identifier              |
| `0x04` |  4 bytes | Payload length (`file length - 24`) |
| `0x08` |  4 bytes | CRC32 of the payload                |
| `0x0C` |  2 bytes | Watch face width                    |
| `0x0E` | 10 bytes | Remaining header/reserved data      |
| `0x18` |        — | Compressed payload                  |

The original file identifier is preserved when appropriate rather than assuming that every watch face uses the same value.

GloryDial Studio does **not** assume that every `.bin` file uses the same compression or format revision. Different watch face families may use different structures.

---

## Compatibility

One of the project's primary goals is compatibility with existing watch face software.

### ClockFaceEdit (xplorr's watch face tool)

GloryDial Studio's exported `.bin` files have been tested by loading them into ClockFaceEdit.

A generated watch face successfully:

* loaded in ClockFaceEdit
* parsed correctly
* rendered correctly

This provides an important validation point for the generated binary format.

GloryDial Studio is therefore being developed against **real-world compatibility**, rather than relying solely on an assumed or simplified file specification.

xplorr's XDA thread: https://xdaforums.com/t/watchface-tool-editor-for-gloryfitpro-mk68-015-hello-watch-estg.4704442/

---

## Watch Face Elements

The format can contain different types of watch face components, including elements such as:

* Hours
* Minutes
* Seconds
* Hour digits
* Minute digits
* Second digits
* Images
* Animated image sequences
* Analog hands
* Other format-specific elements

Analog hand objects may contain information such as:

* Position
* Animation speed
* Image index
* Number of images
* Transparency settings
* Full hand length
* Hand length toward the center
* Hand width

The exact available elements depend on the watch face format being edited.

---

## Technology

GloryDial Studio is written in:

* **Python**
* **PyQt6**

The application is designed as a native desktop application rather than a web-based editor.

---

## Development Status

GloryDial Studio is currently under active development. While most functionalities work, some features may not work properly.

## Building / Running

### Requirements

* Python 3.10
* PyQt6
* Required Python dependencies listed by the project

Clone the repository:

```bash
git clone https://github.com/coolsteel712/GloryDial-Studio.git
cd GloryDial-Studio
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the application:

```bash
python main.py
```

> The repository structure and dependencies may change during development.

---

## Important Notes

GloryDial Studio works with proprietary watch face formats.

The format documentation is based on:

* Reverse engineering
* Analysis of real watch face files
* Existing open-source implementations
* Compatibility testing
* Empirical testing with physical hardware

Because these formats are not necessarily publicly documented by the original manufacturers, some portions of the format may remain undocumented or may differ between devices and firmware versions.

**Always keep backups of your original watch face files.**

---

## Contributing

Contributions are welcome.

Useful contributions include:

* Reverse engineering additional watch face formats
* Adding support for new devices
* Improving binary parsing
* Improving rendering accuracy
* Testing exported watch faces
* Fixing bugs
* Improving the editor UI
* Improving documentation

When adding support for a new format, please provide as much information as possible about the source files, device, firmware version, and observed behavior.

---

## License

GloryDial Studio is licensed under the:

**GNU General Public License v3.0 (GPL-3.0)**

You are free to use, study, modify, and redistribute the software under the terms of the GPL-3.0 license.

See [`LICENSE`](LICENSE) for the complete license text.

---

## Disclaimer

GloryDial Studio is an independent open-source project.

It is **not affiliated with, endorsed by, or sponsored by** Shenzhen Ultra Easy Technology Co., Ltd.

Use the software and custom watch faces at your own risk. Improperly constructed watch face files may fail to load or may be rejected by the watch's companion application.

---

## Project

**GloryDial Studio**
Open-source watch face creation and editing for `.bin` smart-watch faces.

Built for experimentation, reverse engineering, compatibility, and customization.
