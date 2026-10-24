"""Bounded partition scans; each mutation uses the existing guild owner."""
import asyncio,time
from guild_maintenance import GuildMaintenanceCommand,GuildClockResumeCommand


class GuildMaintenanceRuntime:
    def __init__(self,guild):
        self.guild,self.owner,self.rt=guild,guild.owner,guild.rt
        self.rules=guild.store.guild_maintenance_rules
        self.limit=min(self.owner.policy['owner_limit'],self.rules.batch_limit*self.rules.partitions)
        self.jobs={};self.cursors={};self.ceilings={};self.waiting={};self.closed=False
        self.loops=tuple(asyncio.create_task(self.loop(part),name=f'guild-clock-directory:{part}')
            for part in range(self.rules.partitions)) if self.rules.scheduler_enabled else ()

    async def loop(self,partition):
        while not self.closed:
            await asyncio.sleep(self.rules.scan_interval_ms/1000)
            try:await self.scan(partition,int(time.time()*1000))
            except asyncio.CancelledError:raise
            except Exception as error:
                self.waiting.pop(partition,None)
                self.rt.log(event='guild_clock_directory_deferred',partition=partition,reason=type(error).__name__)

    async def scan(self,partition,now):
        if self.closed:return
        page=await self.rt.io.run(('guild-clock-directory',partition),self.guild.store.guild_maintenance_page,
            partition,now,self.cursors.get(partition),self.ceilings.get(partition))
        if not page.entries:
            self.cursors.pop(partition,None);self.ceilings.pop(partition,None)
            self.waiting.pop(partition,None)
            return
        self.ceilings[partition]=page.ceiling
        for identity,due in page.entries:
            if identity not in self.jobs:
                if len(self.jobs)>=self.limit or (self.waiting and next(iter(self.waiting))!=partition):
                    # At most one admission marker per directory partition.
                    # Failed early partitions cannot repeatedly steal the only
                    # slot before a later partition gets its next scan turn.
                    self.waiting.setdefault(partition,True)
                    self.rt.log(event='guild_clock_jobs_full',organization=identity)
                    break
                self.waiting.pop(partition,None)
                task=asyncio.create_task(self.run(identity,due),name=f'guild-maintenance:{identity}:{due}')
                self.jobs[identity]=task
                def finished(value,identity=identity):
                    if self.jobs.get(identity) is value:self.jobs.pop(identity,None)
                    if not value.cancelled():value.exception()
                task.add_done_callback(finished)
            # Capacity refusal cannot move past an unaccepted guild. A finite
            # round ceiling prevents new due sources from starving old ones.
            self.cursors[partition]=(due,identity)

    async def run(self,identity,due):
        try:
            now=int(time.time()*1000)
            if now-due>self.rules.max_lateness_ms:
                await self.owner.resume_guild_maintenance(GuildClockResumeCommand(identity,due,now+5000),now)
                return
            audience=await self.rt.io.run(('organization',identity),self.guild.store.guild_audience,identity)
            if audience is None:raise ValueError('guild_panel_unknown')
            online=self.rt.online_snapshot()
            observation=tuple((rid,online[rid].login_epoch) for rid,_,_ in audience.members if rid in online)
            await self.owner.maintain_guild(GuildMaintenanceCommand(identity,due,now+5000,observation),now)
        except Exception as error:
            self.rt.log(event='guild_maintenance_deferred',organization=identity,due_ms=due,reason=str(error))

    async def idle(self):
        while self.jobs:await asyncio.gather(*tuple(self.jobs.values()),return_exceptions=True)

    async def close(self):
        self.closed=True
        for task in self.loops:task.cancel()
        await asyncio.gather(*self.loops,return_exceptions=True)
        await self.idle()
