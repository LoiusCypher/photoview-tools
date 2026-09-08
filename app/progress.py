from datetime import datetime, timezone
from typing import List, Optional

class Progress( object):

    def __init__( self, resolution: int, ranges: List[int], counts: List[int]) -> None:
        self.resolution = resolution
        self.ranges = ranges
        self.active_step = None
        assert len( counts) + 1 == len( self.ranges)
        self.steps = counts

    def start_next( self) -> None:
        if self.active_step is None:
            self.active_step = 0
        else:
            self.active_step += 1
        #print( f"{self.active_step} {len(self.ranges)} {self.steps}")
        assert self.active_step < (len( self.ranges) - 1)
        self.ticks = 0
        self.res_rng = self.resolution * (self.ranges[self.active_step+1] - self.ranges[self.active_step])
        #print( f"{self.res_rng} {self.resolution} {self.ranges[self.active_step+1]} - {self.ranges[self.active_step]}")
        self.started = datetime.now( timezone.utc)

    def tick( self) -> bool:
        assert self.active_step is not None
        self.ticks += 1
        #print( f"{self.ticks = } {self.active_step = } {self.steps = } {self.ranges = } {self.res_rng = } {(self.res_rng * self.ticks) % self.steps[self.active_step] }")
        return (self.res_rng * self.ticks) % self.steps[self.active_step] < self.res_rng

    def status( self):
        percent = self.ranges[self.active_step] + int( self.res_rng * self.ticks / self.steps[self.active_step]) / self.resolution
        span = datetime.now( timezone.utc) - self.started
        return ( percent, self.steps[self.active_step], self.ticks, span, span / percent,)

    def status_msg( self):
        percent = self.ranges[self.active_step] + int( self.res_rng * self.ticks / self.steps[self.active_step]) / self.resolution
        span = datetime.now( timezone.utc) - self.started
        return f"{percent} {self.steps[self.active_step]} {self.ticks} {span} {span / percent}"


