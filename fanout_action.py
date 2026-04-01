#!/usr/bin/env python3
# Fanout Tool - IPC API version
# Entry point for the KiCad IPC plugin

import wx
from kipy import KiCad
from kipy.errors import ConnectionError, ApiError

from onekiwi.controller.controller import Controller


def _ensure_app():
    app = wx.GetApp()
    created = False
    if app is None:
        app = wx.App(False)
        created = True
    return app, created


def main():
    app, created = _ensure_app()

    try:
        kicad = KiCad()
        board = kicad.get_board()
    except (ConnectionError, ApiError) as e:
        wx.MessageBox(f"Could not connect to KiCad: {e}", "Fanout Tool Error")
        return
    except Exception as e:
        wx.MessageBox(f"Error: {e}", "Fanout Tool Error")
        return

    controller = Controller(kicad, board)
    controller.Show()

    if created:
        app.MainLoop()

if __name__ == "__main__":
    main()
