# IPC-based model for Fanout Tool
# Uses kipy instead of pcbnew SWIG bindings

from kipy import KiCad
from kipy.board import Board
from kipy.board_types import FootprintInstance, Track, Via, ViaType, BoardLayer, Net
from kipy.geometry import Vector2
from kipy.util import from_mm, to_mm

from .bga import BGA


class Model:
    def __init__(self, kicad: KiCad, board: Board, logger):
        self.logger = logger
        self.kicad = kicad
        self.board = board
        self.references = []
        self.reference = None
        self.track = None
        self.via = None
        self.package = None
        self.alignment = None
        self.direction = None
        self.bga = None
        self.update_reference()

    def update_reference(self):
        footprints = self.board.get_footprints()
        for footprint in footprints:
            ref = footprint.reference_field.text.value
            self.references.append(ref)

    def update_data(self, reference, track, via):
        self.reference = reference
        self.track = track
        self.via = via

    def update_package(self, package, alignment, direction, skip_unconnected=True, outer_pad_tracks=False):
        self.package = package
        self.alignment = alignment
        self.direction = direction
        self.skip_unconnected = skip_unconnected
        self.outer_pad_tracks = outer_pad_tracks

    def fanout(self):
        if self.package == 'BGA':
            self.bga = BGA(
                self.kicad, self.board, self.reference, self.track, self.via, 
                self.alignment, self.direction, self.logger,
                skip_unconnected=self.skip_unconnected,
                outer_pad_tracks=self.outer_pad_tracks
            )
            self.bga.fanout()
    
    def remove_track_via(self):
        if self.bga:
            self.bga.remove_track_via()
