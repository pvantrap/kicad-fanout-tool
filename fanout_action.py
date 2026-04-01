#!/usr/bin/env python3
# Fanout Tool - IPC API version
# Entry point for the KiCad IPC plugin

import wx
from kipy import KiCad
from kipy.errors import ConnectionError

from onekiwi.controller.controller import Controller

def main():
    try:
        kicad = KiCad()
        board = kicad.get_board()
    except ConnectionError as e:
        wx.MessageBox(f"Could not connect to KiCad: {e}", "Fanout Tool Error")
        return
    except Exception as e:
        wx.MessageBox(f"Error: {e}", "Fanout Tool Error")
        return

    app = wx.App()
    controller = Controller(kicad, board)
    controller.Show()
    app.MainLoop()

if __name__ == "__main__":
    main()
