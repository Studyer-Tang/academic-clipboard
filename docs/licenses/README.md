# Runtime notices

These notices accompany the bundled runtimes; they do not change this project's MIT license.

- `tcl-license.terms`: https://github.com/tcltk/tcl/blob/core-8-6-branch/license.terms
- `tk-license.terms`: https://github.com/tcltk/tk/blob/core-8-6-branch/license.terms
- `libffi-LICENSE`: https://github.com/libffi/libffi/blob/master/LICENSE

The build copies the installed Python runtime's `LICENSE.txt`, Pillow's license, PyInstaller's bootloader license/exception, and either PyObjC's shared MIT notice (from the Cocoa distribution) or pystray's LGPL/GPL notices plus six's license. Original third-party notices remain intact. Installed dependency versions are determined by the native build's package environment.
