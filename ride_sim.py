"""Educational PLC-style station simulator. No hardware connectivity; not safety-rated."""
from dataclasses import dataclass, field
import json, argparse

@dataclass
class RideStation:
    train_present: bool = True
    gate_closed: bool = True
    restraints_locked: bool = True
    block_clear: bool = True
    drive_ready: bool = True
    estop_healthy: bool = True
    plc_comms_ok: bool = True
    sensor_consistent: bool = True
    state: str = 'IDLE'
    alarms: list = field(default_factory=list)
    event_log: list = field(default_factory=list)
    tick_count: int = 0

    def faults(self):
        names = {'estop_healthy':'E_STOP_CIRCUIT_OPEN','plc_comms_ok':'PLC_COMMUNICATION_LOSS',
                 'sensor_consistent':'SENSOR_DISAGREEMENT','drive_ready':'DRIVE_NOT_READY'}
        return [name for fieldname,name in names.items() if not getattr(self,fieldname)]

    def permissives(self):
        return all((self.train_present,self.gate_closed,self.restraints_locked,
                    self.block_clear,self.drive_ready,self.estop_healthy,
                    self.plc_comms_ok,self.sensor_consistent))

    def tick(self, dispatch=False, reset=False, arrive=False):
        self.tick_count += 1
        active = self.faults()
        for a in active:
            if a not in self.alarms: self.alarms.append(a)
        if active:
            self.state='FAULT'
        elif self.state=='FAULT':
            if reset and self.permissives():
                self.alarms.clear(); self.state='READY'
        elif self.state=='IDLE':
            if self.permissives(): self.state='READY'
        elif self.state=='READY':
            if not self.permissives(): self.state='IDLE'
            elif dispatch: self.state='DISPATCHED'
        elif self.state=='DISPATCHED':
            self.train_present=False
            self.block_clear=False
            self.state='AWAY'
        elif self.state=='AWAY':
            if arrive and self.block_clear:
                self.train_present=True; self.state='IDLE'
        event={'tick':self.tick_count,'state':self.state,'dispatch_permitted':self.permissives() and self.state=='READY',
               'alarms':list(self.alarms)}
        self.event_log.append(event)
        return event

    def set_input(self, name, value):
        if name not in {'train_present','gate_closed','restraints_locked','block_clear','drive_ready',
                        'estop_healthy','plc_comms_ok','sensor_consistent'}: raise ValueError('Unknown input')
        setattr(self,name,bool(value))


def scenario_report():
    def run(name, actions):
        s=RideStation()
        rows=[]
        for label, changes, command in actions:
            for k,v in changes.items(): s.set_input(k,v)
            rows.append({'step':label,**s.tick(**command)})
        return {'scenario':name,'steps':rows}
    return [
        run('Nominal dispatch', [('Initial scan',{},{}),('Dispatch request',{}, {'dispatch':True}),('Departure scan',{}, {})]),
        run('Open gate blocks dispatch',[('Gate open',{'gate_closed':False},{}),('Dispatch request',{}, {'dispatch':True})]),
        run('PLC communication failure and reset',[('Ready',{},{}),('Comms lost',{'plc_comms_ok':False},{}),('Comms restored without reset',{'plc_comms_ok':True},{}),('Operator reset',{}, {'reset':True})]),
        run('Sensor disagreement latches fault',[('Ready',{},{}),('Sensor mismatch',{'sensor_consistent':False},{}),('Mismatch fixed',{'sensor_consistent':True},{}),('Reset',{}, {'reset':True})]),
        run('Drive fault',[('Ready',{},{}),('Drive fault',{'drive_ready':False},{}),('Dispatch blocked',{}, {'dispatch':True})]),
        run('E-stop circuit opens',[('Ready',{},{}),('E-stop open',{'estop_healthy':False},{}),('Dispatch blocked',{}, {'dispatch':True})]),
    ]

if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Educational PLC-style station simulator')
    parser.add_argument('--scenarios',action='store_true',help='Print deterministic scenario results')
    args=parser.parse_args()
    if args.scenarios: print(json.dumps(scenario_report(),indent=2))
    else:
        s=RideStation(); print('Commands: scan, dispatch, reset, arrive, set <input> <0|1>, status, quit')
        while True:
            try: parts=input('station> ').strip().split()
            except EOFError: break
            if not parts: continue
            if parts[0]=='quit': break
            try:
                if parts[0]=='set' and len(parts)==3: s.set_input(parts[1],parts[2]=='1')
                elif parts[0]=='status': print(json.dumps(s.__dict__,indent=2)); continue
                elif parts[0] not in ('scan','dispatch','reset','arrive','set'): print('Unknown command'); continue
                print(json.dumps(s.tick(dispatch=parts[0]=='dispatch',reset=parts[0]=='reset',arrive=parts[0]=='arrive')))
            except ValueError as e: print(e)
