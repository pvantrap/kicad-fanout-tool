import wx
import pcbnew
from onekiwi.controller.controller import Controller

filename = '/tmp/test.kicad_pcb'

class SimplePluginApp(wx.App):
    def OnInit(self):
        board = pcbnew.LoadBoard(filename)
        if board is None:
            print(f"Error: Unable to open file '{filename}' for reading.")
            return False
        controller = Controller(board)
        controller.Show()
        return True

def main():
    app = SimplePluginApp()
    app.MainLoop()

    print("Done")

if __name__ == "__main__":
    main()