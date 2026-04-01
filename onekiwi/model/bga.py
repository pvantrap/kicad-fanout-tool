# IPC-based BGA fanout implementation
# Uses kipy instead of pcbnew SWIG bindings

import math
from typing import List, Optional, Tuple

from kipy import KiCad
from kipy.board import Board
from kipy.board_types import (
    FootprintInstance, Pad, Track, Via, ViaType, BoardLayer, Net,
    PadType, PST_NORMAL
)
from kipy.geometry import Vector2
from kipy.util import from_mm, to_mm
from kipy.proto.common.types import KIID


class BGA:
    def __init__(self, kicad: KiCad, board: Board, reference: str, track_width: int, 
                 via_settings: dict, alignment: str, direction: str, logger,
                 skip_unconnected: bool = True, outer_pad_tracks: bool = False):
        self.logger = logger
        self.kicad = kicad
        self.board = board
        self.reference = reference
        self.track_width = track_width
        self.via_diameter = via_settings['diameter']
        self.via_drill = via_settings['drill']
        self.alignment = alignment
        self.direction = direction
        self.skip_unconnected = skip_unconnected
        self.outer_pad_tracks = outer_pad_tracks
        self.pitchx = 0
        self.pitchy = 0
        self.created_item_ids: List[KIID] = []  # Track created items for undo
        self.minx = 0
        self.maxx = 0
        self.miny = 0
        self.maxy = 0
        self.x0 = 0
        self.y0 = 0
        self.degrees = 0.0
        self.radian = 0.0
        self.radian_pad = 0.0

        self.logger.info(reference)
        
        # Find the footprint by reference
        self.footprint: Optional[FootprintInstance] = None
        self.pads: List[Pad] = []
        footprints = self.board.get_footprints()
        for fp in footprints:
            if fp.reference_field.text.value == reference:
                self.footprint = fp
                break
        
        if self.footprint is None:
            self.logger.error(f'Footprint {reference} not found')
            return
        
        # Get footprint orientation
        self.degrees = self.footprint.orientation.degrees
        self.radian = self.footprint.orientation.to_radians()
        
        # Get footprint position (center)
        self.x0 = self.footprint.position.x
        self.y0 = self.footprint.position.y
        
        # We need pads from board.get_pads() because footprint.definition.pads
        # doesn't have net information. But we use definition.pads positions
        # to establish the footprint boundary and pitch.
        def_pads = self.footprint.definition.pads
        if not def_pads:
            self.logger.error('No pads in footprint definition')
            return
        
        # Calculate pitch from definition pads (which have correct positions)
        x_positions = sorted(set(p.position.x for p in def_pads))
        y_positions = sorted(set(p.position.y for p in def_pads))
        
        if len(x_positions) > 1:
            diffs = [x_positions[i+1] - x_positions[i] for i in range(len(x_positions)-1)]
            self.pitchx = min(diffs)
        else:
            self.pitchx = from_mm(1.0)
            
        if len(y_positions) > 1:
            diffs = [y_positions[i+1] - y_positions[i] for i in range(len(y_positions)-1)]
            self.pitchy = min(diffs)
        else:
            self.pitchy = from_mm(1.0)
        
        # Build a set of definition pad positions for matching
        def_pad_positions = set()
        tolerance = self.pitchx // 10  # Small tolerance for position matching
        for p in def_pads:
            def_pad_positions.add((p.position.x, p.position.y))
        
        # Get pads from board and match by position with definition pads
        all_pads = self.board.get_pads()
        for pad in all_pads:
            # Check if this pad's position matches any definition pad position
            for def_x, def_y in def_pad_positions:
                if (abs(pad.position.x - def_x) <= tolerance and
                    abs(pad.position.y - def_y) <= tolerance):
                    self.pads.append(pad)
                    break
        
        # Set bounds
        if def_pads:
            self.minx = min(p.position.x for p in def_pads)
            self.maxx = max(p.position.x for p in def_pads)
            self.miny = min(p.position.y for p in def_pads)
            self.maxy = max(p.position.y for p in def_pads)
        
        self._log_init_data()

    def is_pad_connected(self, pad: Pad) -> bool:
        """Check if pad has a valid net connection (not unconnected)."""
        if not self.skip_unconnected:
            return True
        net = pad.net
        net_name = net.name
        if not net_name or net_name.strip() == '':
            return False
        net_name_lower = net_name.lower()
        if net_name_lower.startswith('unconnected-') and '-pad' in net_name_lower:
            return False
        return True

    def is_outer_pad(self, pad: Pad) -> bool:
        """Check if pad is on the outer edge of the BGA."""
        if not self.outer_pad_tracks:
            return False
        pos = pad.position
        tolerance = self.pitchx / 4
        on_left = abs(pos.x - self.minx) < tolerance
        on_right = abs(pos.x - self.maxx) < tolerance
        on_top = abs(pos.y - self.miny) < tolerance
        on_bottom = abs(pos.y - self.maxy) < tolerance
        return on_left or on_right or on_top or on_bottom

    def get_outer_pad_direction(self, pad: Pad) -> Tuple[int, int]:
        """Get the outward direction for an outer pad. Returns (dx, dy) normalized."""
        pos = pad.position
        tolerance = self.pitchx / 4
        on_left = abs(pos.x - self.minx) < tolerance
        on_right = abs(pos.x - self.maxx) < tolerance
        on_top = abs(pos.y - self.miny) < tolerance
        on_bottom = abs(pos.y - self.maxy) < tolerance
        
        dx, dy = 0, 0
        if on_left:
            dx = -1
        elif on_right:
            dx = 1
        if on_top:
            dy = -1
        elif on_bottom:
            dy = 1
        
        # Normalize if diagonal
        if dx != 0 and dy != 0:
            length = math.sqrt(dx*dx + dy*dy)
            dx = int(dx / length)
            dy = int(dy / length)
        
        return (dx, dy)

    def _log_init_data(self):
        """Log initialization data."""
        px = to_mm(self.pitchx)
        py = to_mm(self.pitchy)
        self.logger.info(f'pitch x: {px:.6f} mm')
        self.logger.info(f'pitch y: {py:.6f} mm')

    def init_data(self):
        """Initialize BGA data from pad positions - kept for compatibility."""
        pass  # Initialization now done in __init__

    def fanout(self):
        """Execute the fanout operation."""
        if not self.pads:
            self.logger.error('No pads to process')
            return
            
        # Begin a commit for undo support
        commit = self.board.begin_commit()
        
        try:
            if self.alignment == 'Quadrant':
                if self.degrees in [0.0, 90.0, 180.0, -90.0]:
                    self.quadrant_0_90_180()
                elif self.degrees in [45.0, 135.0, -135.0, -45.0]:
                    self.quadrant_45_135()
                else:
                    self.quadrant_other_angle()
            elif self.alignment == 'Diagonal':
                if self.degrees in [0.0, 90.0, 180.0, -90.0]:
                    self.diagonal_0_90_180()
                elif self.degrees in [45.0, 135.0, -135.0, -45.0]:
                    self.diagonal_45_135()
                else:
                    self.diagonal_other_angle()
            elif self.alignment == 'X-pattern':
                if self.degrees in [0.0, 90.0, 180.0, -90.0]:
                    self.xpattern_0_90_180()
                elif self.degrees in [45.0, 135.0, -135.0, -45.0]:
                    self.xpattern_45_135()
                else:
                    self.xpattern_other_angle()
            
            self.board.push_commit(commit, "BGA Fanout")
            self.logger.info('Fanout complete')
        except Exception as e:
            self.board.drop_commit(commit)
            self.logger.error(f'Fanout failed: {e}')
            import traceback
            self.logger.error(traceback.format_exc())

    def add_track(self, net: Net, start: Vector2, end: Vector2):
        """Add a track segment."""
        track = Track()
        track.start = start
        track.end = end
        track.width = self.track_width
        track.layer = BoardLayer.BL_F_Cu
        track.net = net
        
        created = self.board.create_items([track])
        if created:
            self.created_item_ids.append(created[0].id)

    def add_via(self, net: Net, pos: Vector2):
        """Add a via."""
        via = Via()
        via.position = pos
        via.type = ViaType.VT_THROUGH
        via.diameter = self.via_diameter
        via.drill_diameter = self.via_drill
        via.net = net
        
        created = self.board.create_items([via])
        if created:
            self.created_item_ids.append(created[0].id)

    def add_fanout_for_pad(self, pad: Pad, end: Vector2):
        """Add track from pad to end, then via or outer track depending on options."""
        pos = pad.position
        net = pad.net
        
        if self.is_outer_pad(pad):
            self.add_outer_track(net, pos, pad)
        else:
            self.add_track(net, pos, end)
            self.add_via(net, end)

    def add_outer_track(self, net: Net, pos: Vector2, pad: Pad):
        """Add a straight outward track for outer pads."""
        dx, dy = self.get_outer_pad_direction(pad)
        if dx == 0 and dy == 0:
            return
        
        track_length = int(self.pitchx * 3)
        end_x = pos.x + dx * track_length
        end_y = pos.y + dy * track_length
        end = Vector2.from_xy(end_x, end_y)
        self.add_track(net, pos, end)

    def remove_track_via(self):
        """Remove all created tracks and vias."""
        if self.created_item_ids:
            self.board.remove_items_by_id(self.created_item_ids)
            self.created_item_ids.clear()

    # Quadrant patterns
    def quadrant_0_90_180(self):
        """Quadrant fanout for 0, 90, 180, -90 degree orientations."""
        for pad in self.pads:
            if not self.is_pad_connected(pad):
                continue
            pos = pad.position
            
            if pos.y > self.y0:
                if pos.x > self.x0:
                    # bottom-right
                    x = pos.x + self.pitchx // 2
                    y = pos.y + self.pitchy // 2
                else:
                    # bottom-left
                    x = pos.x - self.pitchx // 2
                    y = pos.y + self.pitchy // 2
            else:
                if pos.x > self.x0:
                    # top-right
                    x = pos.x + self.pitchx // 2
                    y = pos.y - self.pitchy // 2
                else:
                    # top-left
                    x = pos.x - self.pitchx // 2
                    y = pos.y - self.pitchy // 2
            
            end = Vector2.from_xy(x, y)
            self.add_fanout_for_pad(pad, end)

    def quadrant_45_135(self):
        """Quadrant fanout for 45, 135, -135, -45 degree orientations."""
        bx = self.y0 + self.x0
        by = self.y0 - self.x0
        pitch = int(math.sqrt(self.pitchx * self.pitchx + self.pitchy * self.pitchy) / 2)
        
        for pad in self.pads:
            if not self.is_pad_connected(pad):
                continue
            pos = pad.position
            y1 = bx - pos.x
            y2 = by + pos.x
            
            if pos.y > y1:
                if pos.y > y2:
                    # bottom
                    x = pos.x
                    y = pos.y + pitch
                else:
                    # left
                    x = pos.x + pitch
                    y = pos.y
            else:
                if pos.y > y2:
                    # right
                    x = pos.x - pitch
                    y = pos.y
                else:
                    # top
                    x = pos.x
                    y = pos.y - pitch
            
            end = Vector2.from_xy(x, y)
            self.add_fanout_for_pad(pad, end)

    def quadrant_other_angle(self):
        """Quadrant fanout for other angles - simplified implementation."""
        # For other angles, use the same logic as 0 degrees as a fallback
        self.quadrant_0_90_180()

    # Diagonal patterns
    def diagonal_0_90_180(self):
        """Diagonal fanout for 0, 90, 180, -90 degree orientations."""
        for pad in self.pads:
            if not self.is_pad_connected(pad):
                continue
            pos = pad.position
            
            if self.direction == 'TopLeft':
                x = pos.x - self.pitchx // 2
                y = pos.y - self.pitchy // 2
            elif self.direction == 'TopRight':
                x = pos.x + self.pitchx // 2
                y = pos.y - self.pitchy // 2
            elif self.direction == 'BottomLeft':
                x = pos.x - self.pitchx // 2
                y = pos.y + self.pitchy // 2
            elif self.direction == 'BottomRight':
                x = pos.x + self.pitchx // 2
                y = pos.y + self.pitchy // 2
            else:
                continue
            
            end = Vector2.from_xy(x, y)
            self.add_fanout_for_pad(pad, end)

    def diagonal_45_135(self):
        """Diagonal fanout for 45, 135, -135, -45 degree orientations."""
        pitch = int(math.sqrt(self.pitchx * self.pitchx + self.pitchy * self.pitchy) / 2)
        
        for pad in self.pads:
            if not self.is_pad_connected(pad):
                continue
            pos = pad.position
            
            if self.direction == 'TopLeft':
                x = pos.x
                y = pos.y - pitch
            elif self.direction == 'TopRight':
                x = pos.x + pitch
                y = pos.y
            elif self.direction == 'BottomLeft':
                x = pos.x - pitch
                y = pos.y
            elif self.direction == 'BottomRight':
                x = pos.x
                y = pos.y + pitch
            else:
                continue
            
            end = Vector2.from_xy(x, y)
            self.add_fanout_for_pad(pad, end)

    def diagonal_other_angle(self):
        """Diagonal fanout for other angles - simplified implementation."""
        self.diagonal_0_90_180()

    # X-pattern
    def xpattern_0_90_180(self):
        """X-pattern fanout for 0, 90, 180, -90 degree orientations."""
        bx = self.y0 + self.x0
        by = self.y0 - self.x0
        
        for pad in self.pads:
            if not self.is_pad_connected(pad):
                continue
            pos = pad.position
            y1 = bx - pos.x
            y2 = by + pos.x
            
            if pos.y > y1:
                if pos.y > y2:
                    # bottom
                    if self.direction == 'Counterclock':
                        x = pos.x - self.pitchx // 2
                        y = pos.y + self.pitchy // 2
                    else:
                        x = pos.x + self.pitchx // 2
                        y = pos.y + self.pitchy // 2
                else:
                    # right
                    if self.direction == 'Counterclock':
                        x = pos.x + self.pitchx // 2
                        y = pos.y + self.pitchy // 2
                    else:
                        x = pos.x + self.pitchx // 2
                        y = pos.y - self.pitchy // 2
            else:
                if pos.y > y2:
                    # left
                    if self.direction == 'Counterclock':
                        x = pos.x - self.pitchx // 2
                        y = pos.y - self.pitchy // 2
                    else:
                        x = pos.x - self.pitchx // 2
                        y = pos.y + self.pitchy // 2
                else:
                    # top
                    if self.direction == 'Counterclock':
                        x = pos.x + self.pitchx // 2
                        y = pos.y - self.pitchy // 2
                    else:
                        x = pos.x - self.pitchx // 2
                        y = pos.y - self.pitchy // 2
            
            end = Vector2.from_xy(x, y)
            self.add_fanout_for_pad(pad, end)

    def xpattern_45_135(self):
        """X-pattern fanout for 45, 135, -135, -45 degree orientations."""
        pitch = int(math.sqrt(self.pitchx * self.pitchx + self.pitchy * self.pitchy) / 2)
        
        for pad in self.pads:
            if not self.is_pad_connected(pad):
                continue
            pos = pad.position
            
            # Simplified implementation
            if self.direction == 'Counterclock':
                x = pos.x - pitch
                y = pos.y
            else:
                x = pos.x + pitch
                y = pos.y
            
            end = Vector2.from_xy(x, y)
            self.add_fanout_for_pad(pad, end)

    def xpattern_other_angle(self):
        """X-pattern fanout for other angles - simplified implementation."""
        self.xpattern_0_90_180()
