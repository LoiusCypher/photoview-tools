from datetime import UTC, datetime

import sqlalchemy


class Progress:

    def __init__( self, table: object, column: str, action_id: int, steps: int, resolution: int=1) -> None:
        self.table = table
        self.columns = [ column, ]
        self.action_id = action_id
        self.resolution = [ resolution, ]
        self.steps = [ steps, ]
        self.ranges = [ 0, 100,]
        self.active_step = None
        #print( f"__init__ {self.column = } {self.action_id} {self.resolution} {self.steps} {self.ranges}")

    def add_task( self, column: str, steps: int | None =None, resolution: int | None =None, ranges: list[int] | int | None =None) -> None:
        #print( f"add_task {column = } {steps = } {resolution = } {ranges = }")
        self.columns.append( column)
        #print( f"add_task {self.columns = }")
        if resolution:
            self.resolution.append( resolution)
        else:
            #print( f"add_taski {self.resolution[-1] = }")
            self.resolution.append( self.resolution[-1])
        #print( f"add_task {self.resolution = }")
        if steps:
            self.steps.append( steps)
        else:
            self.steps.append( self.steps[-1])
        #print( f"add_task {self.steps = }")
        if not ranges:
            ranges = int( 100 / len( self.ranges))
        if isinstance( ranges, int):
            self.ranges = [ int(border * (100 - ranges) / 100) for border in self.ranges]
            self.ranges.append( 100)
        else:
            assert len(ranges) == len( self.ranges) + 1
            self.ranges = ranges
        #print( f"add_task {self.ranges = }")

    def start_next( self) -> None:
        #print( f"start_next")
        if self.active_step is None:
            self.active_step = 0
            self.started = datetime.now( tz=UTC)
        else:
            self.active_step += 1
        #print( f"{self.active_step} {len(self.ranges)} {self.steps}")
        assert self.active_step < (len( self.ranges) - 1)
        self.step_ticks = 0
        self.res_rng = self.resolution[self.active_step] * (self.ranges[self.active_step+1] - self.ranges[self.active_step])
        #print( f"{self.res_rng} {self.resolution[self.active_step]} {self.ranges[self.active_step+1]} - {self.ranges[self.active_step]}")
        self.step_started = datetime.now( tz=UTC)
        self.last_tic = self.started

    def tick( self, session: sqlalchemy.orm.session.Session = None) -> bool:
        assert self.active_step is not None
        self.step_ticks += 1
        #print( f"tick   {self.step_ticks = } {self.active_step = } {self.steps = } {self.ranges = } {self.res_rng = }")
        #print( f"    <? {(self.res_rng * self.step_ticks) % self.steps[self.active_step] }")
        steps = self.steps[self.active_step]
        update = ((self.res_rng * self.step_ticks) % steps) < self.res_rng
        if update:
            now = datetime.now( tz=UTC)
            self.step_percent = int( self.res_rng * self.step_ticks / steps) / self.resolution[self.active_step]
            self.percent = self.ranges[self.active_step] + self.step_percent
            self.update_tic_time = now - self.last_tic
            self.step_dur = now - self.step_started
            self.duration = now - self.started
            self.one_perc_duration = self.step_dur / self.step_percent
            self.eta_dur = (100 - self.percent) * self.one_perc_duration
            self.eta = now + self.eta_dur
            self.last_tic = now
            if session and update:
                session.execute( sqlalchemy.update(self.table).values({
                    self.columns[self.active_step]: self.percent,
                    'expected_at': self.eta,
                }).where(self.table.id==self.action_id))
                session.commit()
        return update

    def status_msg( self):
        return f"{self.percent} {self.steps[self.active_step]} {self.step_ticks} spent:{self.duration} tic dur:{self.update_tic_time} perc_dur:{self.one_perc_duration} ETA_dur:{self.eta_dur} ETA:{self.eta.time()}"


