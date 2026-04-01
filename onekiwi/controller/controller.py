# IPC-based controller for Fanout Tool
# Uses kipy instead of pcbnew SWIG bindings

from ..model.model import Model
from ..view.view import FanoutView
from .logtext import LogText
import sys
import logging
import wx
from .package import get_packages

from kipy import KiCad
from kipy.board import Board
from kipy.board_types import BoardLayer, FootprintInstance, Track, Via, ViaType
from kipy.geometry import Vector2
from kipy.util import from_mm, to_mm


class Controller:
    def __init__(self, kicad: KiCad, board: Board):
        self.view = FanoutView()
        self.kicad = kicad
        self.board = board
        self.reference = None
        self.tracks = []
        self.vias = []
        self.packages = get_packages()
        self.logger = self.init_logger(self.view.textLog)
        self.model = Model(self.kicad, self.board, self.logger)

        # Connect Events
        self.view.buttonFanout.Bind(wx.EVT_BUTTON, self.OnButtonFanout)
        self.view.buttonUndo.Bind(wx.EVT_BUTTON, self.OnButtonUndo)
        self.view.buttonClear.Bind(wx.EVT_BUTTON, self.OnButtonClear)
        self.view.buttonClose.Bind(wx.EVT_BUTTON, self.OnButtonClose)
        self.view.choicePackage.Bind(wx.EVT_CHOICE, self.OnChoicePackage)
        self.view.choiceAlignment.Bind(wx.EVT_CHOICE, self.OnChoiceAlignment)
        self.view.choiceDirection.Bind(wx.EVT_CHOICE, self.OnChoiceDirection)
        self.view.choiceReference.Bind(wx.EVT_CHOICE, self.OnChoiceReference)
        self.view.editFilter.Bind(wx.EVT_TEXT, self.OnFilterChange)
        
        self.add_references()
        self.get_tracks_vias()
        self.set_package()

    def Show(self):
        self.view.Show()
    
    def Close(self):
        self.view.Destroy()

    def OnButtonFanout(self, event):
        reference = self.view.GetReferenceSelected()
        if reference == '':
            self.logger.error('Please chose a Reference')
            return
        else:
            self.logger.info('Selected reference: %s' % reference)
            
        if len(self.tracks) > 0:
            track_index = self.view.GetTrackSelectedIndex()
        else:
            self.logger.error('Please add track width')
            return
        if len(self.vias) > 0:
            via_index = self.view.GetViaSelectedIndex()
        else:
            self.logger.error('Please add via')
            return
        
        package = self.view.GetPackageValue()
        self.logger.info('package: %s' % package)
        alignment = self.view.GetAlignmentValue()
        self.logger.info('alignment: %s' % alignment)
        if package == 'BGA' and alignment == 'Quadrant':
            direction = 'none'
        else:
            direction = self.view.GetDirectionValue()
        self.logger.info('direction: %s' % direction)
        skip_unconnected = self.view.GetSkipUnconnected()
        outer_pad_tracks = self.view.GetOuterPadTracks()
        
        self.model.update_data(reference, self.tracks[track_index], self.vias[via_index])
        self.model.update_package(package, alignment, direction, skip_unconnected, outer_pad_tracks)
        self.model.fanout()

    def OnButtonUndo(self, event):
        self.model.remove_track_via()

    def OnButtonClear(self, event):
        self.view.textLog.SetValue('')

    def OnButtonClose(self, event):
        self.Close()

    def OnChoicePackage(self, event):
        index = event.GetEventObject().GetSelection()
        value = event.GetEventObject().GetString(index)
        package = self.packages[index]
        alignments = []
        directions = []
        for i, ali in enumerate(package.alignments, 0):
            alignments.append(ali.name)
            if i == 0:
                for direc in ali.directions:
                    directions.append(direc.name)
        self.view.ClearAlignment()
        self.view.ClearDirection()
        if value == 'BGA staggered':
            alignments.clear()
        if value == 'BGA':
            directions.clear()
        self.view.AddAlignment(alignments)
        self.view.AddDirection(directions)
        image = self.packages[index].alignments[0].directions[0].image
        self.view.SetImagePreview(image)

    def OnChoiceAlignment(self, event):
        x = self.view.GetPackageIndex()
        y = self.view.GetAlignmentIndex()
        value = self.view.GetAlignmentValue()
        directions = []
        direcs = self.packages[x].alignments[y].directions
        for direc in direcs:
            directions.append(direc.name)
        image = direcs[0].image
        self.view.ClearDirection()
        if value == 'Quadrant':
            directions.clear()
        self.view.AddDirection(directions)
        self.view.SetImagePreview(image)

    def OnChoiceDirection(self, event):
        x = self.view.GetPackageIndex()
        y = self.view.GetAlignmentIndex()
        i = event.GetEventObject().GetSelection()
        image = self.packages[x].alignments[y].directions[i].image
        self.view.SetImagePreview(image)

    def OnChoiceReference(self, event):
        reference = self.view.GetReferenceSelected()
        if reference == '':
            return
        # Find footprint by reference
        footprints = self.board.get_footprints()
        for fp in footprints:
            if fp.reference_field.text.value == reference:
                # Add to selection to focus on it
                self.board.clear_selection()
                self.board.add_to_selection([fp])
                break

    def OnFilterChange(self, event):
        self.logger.info('OnFilterChange')
        value = event.GetEventObject().GetValue()
        self.logger.info('text: %s' % value)
        self.view.ClearReferences()
        for ref in self.model.references:
            if ref.rfind(value) != -1:
                self.view.AddReferences(ref)
        self.view.SetIndexReferences(0)

    def add_references(self):
        self.view.AddReferences(self.model.references)

    def get_tracks_vias(self):
        # Get design rules from project
        project = self.board.get_project()
        design_rules = self.board.get_design_rules()
        
        # For now, use default values - the IPC API exposes design rules differently
        # We'll need to adapt this based on what's available
        tracklist = []
        vialist = []
        
        # Default track widths (in nm)
        default_tracks = [200000, 250000, 300000, 400000, 500000]  # 0.2mm, 0.25mm, etc.
        for track in default_tracks:
            self.tracks.append(track)
            display = f"{to_mm(track):.3f} mm"
            tracklist.append(display)
        
        # Default via sizes (diameter, drill) in nm
        default_vias = [
            (800000, 400000),   # 0.8/0.4 mm
            (600000, 300000),   # 0.6/0.3 mm
            (500000, 250000),   # 0.5/0.25 mm
        ]
        for diam, drill in default_vias:
            self.vias.append({'diameter': diam, 'drill': drill})
            display = f"{to_mm(diam):.2f} / {to_mm(drill):.2f} mm"
            vialist.append(display)
        
        self.view.AddTracksWidth(tracklist)
        self.view.AddViasSize(vialist)
        self.logger.info('get_design_settings')

    def set_package(self):
        default = 2  # bga
        packages = []
        alignments = []
        for package in self.packages:
            packages.append(package.name)
            if package.name == 'BGA':
                for alig in package.alignments:
                    alignments.append(alig.name)
        self.view.AddPackageType(packages, default)
        self.view.AddAlignment(alignments)
        image = self.packages[default].alignments[0].directions[0].image
        self.view.SetImagePreview(image)

    def init_logger(self, texlog):
        root = logging.getLogger()
        root.setLevel(logging.DEBUG)
        # Clear existing handlers to avoid duplicates when plugin is reloaded
        root.handlers.clear()
        # Log to our GUI only
        handler = LogText(texlog)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(funcName)s -  %(message)s",
            datefmt="%Y.%m.%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        root.addHandler(handler)
        return logging.getLogger(__name__)
