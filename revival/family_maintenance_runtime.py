"""Partitioned family clock hints; every write uses its existing organization owner."""
import asyncio,time
from family_maintenance import MaintenanceCommand,ClockResumeCommand,FamilyGuildClosureCommand
from family_donation import DonationSweepCommand
from family_guild_history import FamilyGuildHistoryCommand


class FamilyMaintenanceRuntime:
    def __init__(self,family):
        self.family,self.owner,self.rt=family,family.owner,family.rt
        self.rules=family.store.maintenance_rules
        policy=self.owner.policy['family_maintenance']
        if type(policy['scheduler_enabled']) is not bool or type(policy['scan_interval_ms']) is not int or policy['scan_interval_ms']<1:
            raise ValueError('invalid_family_maintenance_scheduler')
        self.interval=policy['scan_interval_ms']/1000
        self.limit=min(self.owner.policy['owner_limit'],self.rules.batch_limit*self.rules.partitions)
        self.jobs={};self.closure_jobs={};self.donation_jobs={};self.history_jobs={};self.closed=False
        self.cursors={};self.closure_cursors={};self.donation_cursors={};self.history_cursors={};self.history_ceilings={}
        self.loops=tuple(asyncio.create_task(self.loop(part),name=f'family-clock-directory:{part}')
            for part in range(self.rules.partitions)) if policy['scheduler_enabled'] else ()

    async def loop(self,partition):
        while not self.closed:
            await asyncio.sleep(self.interval)
            try:
                await self.scan_partition(partition,int(time.time()*1000))
                await self.scan_closures(partition)
                await self.scan_donations(partition)
                await self.scan_history(partition)
            except asyncio.CancelledError:raise
            except Exception as error:
                self.rt.log(event='family_clock_directory_deferred',partition=partition,reason=type(error).__name__)

    async def scan_partition(self,partition,now):
        if self.closed:return
        due=await self.rt.io.run(('family-clock-directory',partition),self.family.store.due_family_maintenance,partition,now,self.cursors.get(partition))
        if due:self.cursors[partition]=(due[-1][1],due[-1][0])
        else:self.cursors.pop(partition,None)
        for identity,stamp in due:self.nudge(identity,stamp,now)

    async def scan_closures(self,partition):
        if self.closed:return
        due=await self.rt.io.run(('family-closure-directory',partition),self.family.store.pending_family_guild_dissolutions,
            partition,self.closure_cursors.get(partition))
        if due:self.closure_cursors[partition]=(due[-1][1],due[-1][0])
        else:self.closure_cursors.pop(partition,None)
        for identity,stamp in due:
            if identity in self.closure_jobs:continue
            if self.job_count()>=self.limit:
                self.rt.log(event='family_closure_jobs_full',family=identity)
                break
            task=asyncio.create_task(self.run_closure(identity,stamp),name=f'family-guild-closure:{identity}:{stamp}')
            self.closure_jobs[identity]=task
            def finished(value,identity=identity):
                if self.closure_jobs.get(identity) is value:self.closure_jobs.pop(identity,None)
                if not value.cancelled():value.exception()
            task.add_done_callback(finished)

    async def run_closure(self,identity,due):
        try:
            event=await self.rt.io.run(('organization',identity),self.family.store.family_dissolution_pending,identity)
            if event.due_ms!=due:raise ValueError('family_dissolution_due_changed')
            now=int(time.time()*1000)
            command=FamilyGuildClosureCommand(event,f'family-guild-closure:{identity}:{due}',now+5000)
            if event.guild is not None:await self.owner.consume_family_guild_dissolution(command,now)
            # No family owner is held while waiting for the guild owner. Ack
            # independently verifies the committed guild receipt in storage.
            await self.owner.ack_family_guild_dissolution(command,int(time.time()*1000))
        except Exception as error:
            self.rt.log(event='family_guild_closure_deferred',family=identity,due_ms=due,reason=str(error))

    def job_count(self):return len(self.jobs)+len(self.closure_jobs)+len(self.donation_jobs)+len(self.history_jobs)

    async def scan_history(self,partition):
        if self.closed:return
        page=await self.rt.io.run(('family-guild-history-directory',partition),self.family.store.family_guild_history_page,
            partition,self.history_cursors.get(partition),self.history_ceilings.get(partition))
        pending=page.entries
        if not pending:
            self.history_cursors.pop(partition,None);self.history_ceilings.pop(partition,None)
        else:self.history_ceilings[partition]=page.ceiling
        for family,sequence in pending:
            if family in self.history_jobs:
                self.history_cursors[partition]=family
                continue
            if self.job_count()>=self.limit:
                self.rt.log(event='family_guild_history_jobs_full',family=family)
                break
            task=asyncio.create_task(self.run_history(family,sequence),name=f'family-guild-history:{family}:{sequence}')
            self.history_jobs[family]=task
            self.history_cursors[partition]=family
            def finished(value,family=family):
                if self.history_jobs.get(family) is value:self.history_jobs.pop(family,None)
                if not value.cancelled():value.exception()
            task.add_done_callback(finished)

    async def run_history(self,family,sequence):
        try:
            event=await self.rt.io.run(('organization',family),self.family.store.family_guild_history_event,sequence)
            if event.family!=family:raise ValueError('family_guild_history_target_changed')
            now=int(time.time()*1000)
            command=FamilyGuildHistoryCommand(event,f'family-guild-history:{family}:{sequence}',now+5000)
            await self.owner.consume_family_guild_history(command,now)
            # The family owner has returned; no entity owner waits while the
            # guild verifies its durable inbox/archive and acknowledges.
            await self.owner.ack_family_guild_history(command,int(time.time()*1000))
        except Exception as error:
            self.rt.log(event='family_guild_history_deferred',family=family,sequence=sequence,reason=str(error))

    async def scan_donations(self,partition):
        if self.closed:return
        pending=await self.rt.io.run(('family-donation-directory',partition),self.family.store.pending_family_donations,
            partition,self.donation_cursors.get(partition))
        if pending:
            identity,stamp,role,reservation=pending[-1]
            self.donation_cursors[partition]=(stamp,identity,role,reservation)
        else:self.donation_cursors.pop(partition,None)
        for identity,stamp,role,reservation in pending:
            if identity in self.donation_jobs:continue
            if self.job_count()>=self.limit:
                self.rt.log(event='family_donation_jobs_full',family=identity)
                break
            task=asyncio.create_task(self.run_donations(identity),name=f'family-donations:{identity}')
            self.donation_jobs[identity]=task
            def finished(value,identity=identity):
                if self.donation_jobs.get(identity) is value:self.donation_jobs.pop(identity,None)
                if not value.cancelled():value.exception()
            task.add_done_callback(finished)

    async def run_donations(self,identity):
        try:
            now=int(time.time()*1000)
            command=DonationSweepCommand(identity,f'family-donations:{identity}:{now}',now+5000)
            await self.owner.sweep_family_donations(command,now)
        except Exception as error:
            self.rt.log(event='family_donation_deferred',family=identity,reason=str(error))

    def nudge(self,identity,due,now):
        if self.closed or identity in self.jobs:return False
        if self.job_count()>=self.limit:
            self.rt.log(event='family_clock_jobs_full',family=identity)
            return False
        task=asyncio.create_task(self.run_family(identity,due,now),name=f'family-maintenance:{identity}:{due}')
        self.jobs[identity]=task
        def finished(value):
            if self.jobs.get(identity) is value:self.jobs.pop(identity,None)
            if not value.cancelled():value.exception()
        task.add_done_callback(finished)
        return True

    async def run_family(self,identity,due,now):
        try:
            request_id=f'family-clock:{identity}:{due}'
            if now-due>self.rules.max_lateness_ms:
                await self.owner.resume_family_maintenance(ClockResumeCommand(identity,due,request_id,now+5000),now)
                return
            audience=await self.rt.io.run(('organization',identity),self.family.store.family_audience,identity)
            if not audience:return
            online=self.rt.online_snapshot()
            observation=tuple((rid,online[rid].login_epoch) for rid,_ in audience.members if rid in online)
            await self.owner.maintain_family(MaintenanceCommand(identity,due,observation,request_id,now+5000),now)
        except Exception as error:
            self.rt.log(event='family_maintenance_deferred',family=identity,due_ms=due,reason=str(error))

    async def idle(self):
        while self.job_count():
            await asyncio.gather(*tuple(self.jobs.values()),*tuple(self.closure_jobs.values()),
                *tuple(self.donation_jobs.values()),*tuple(self.history_jobs.values()),return_exceptions=True)

    async def run_once(self,now):
        await asyncio.gather(*(self.scan_partition(part,now) for part in range(self.rules.partitions)))
        await self.idle()
        await asyncio.gather(*(self.scan_closures(part) for part in range(self.rules.partitions)))
        await self.idle()
        await asyncio.gather(*(self.scan_donations(part) for part in range(self.rules.partitions)))
        await self.idle()
        await asyncio.gather(*(self.scan_history(part) for part in range(self.rules.partitions)))
        await self.idle()

    async def close(self):
        self.closed=True
        for task in self.loops:task.cancel()
        await asyncio.gather(*self.loops,return_exceptions=True)
        await self.idle()
