import unittest
from ride_sim import RideStation

class StationTests(unittest.TestCase):
    def test_nominal_dispatch(self):
        s=RideStation(); self.assertEqual(s.tick()['state'],'READY'); self.assertEqual(s.tick(dispatch=True)['state'],'DISPATCHED'); self.assertEqual(s.tick()['state'],'AWAY')
    def test_gate_prevents_dispatch(self):
        s=RideStation(gate_closed=False); s.tick(); self.assertEqual(s.tick(dispatch=True)['state'],'IDLE')
    def test_restraint_prevents_dispatch(self):
        s=RideStation(restraints_locked=False); s.tick(); self.assertEqual(s.tick(dispatch=True)['state'],'IDLE')
    def test_block_occupied_prevents_dispatch(self):
        s=RideStation(block_clear=False); s.tick(); self.assertEqual(s.tick(dispatch=True)['state'],'IDLE')
    def test_fault_latched_until_reset(self):
        s=RideStation(); s.tick(); s.set_input('plc_comms_ok',False); self.assertEqual(s.tick()['state'],'FAULT'); s.set_input('plc_comms_ok',True); self.assertEqual(s.tick()['state'],'FAULT'); self.assertEqual(s.tick(reset=True)['state'],'READY')
    def test_sensor_disagreement(self):
        s=RideStation(sensor_consistent=False); r=s.tick(); self.assertEqual(r['state'],'FAULT'); self.assertIn('SENSOR_DISAGREEMENT',r['alarms'])
    def test_drive_not_ready(self):
        s=RideStation(drive_ready=False); self.assertEqual(s.tick(dispatch=True)['state'],'FAULT')
    def test_estop(self):
        s=RideStation(estop_healthy=False); self.assertEqual(s.tick(dispatch=True)['state'],'FAULT')
    def test_no_reset_with_fault_active(self):
        s=RideStation(plc_comms_ok=False); s.tick(); self.assertEqual(s.tick(reset=True)['state'],'FAULT')
    def test_away_requires_block_clear_to_arrive(self):
        s=RideStation(); s.tick(); s.tick(dispatch=True); s.tick(); self.assertEqual(s.tick(arrive=True)['state'],'AWAY'); s.set_input('block_clear',True); self.assertEqual(s.tick(arrive=True)['state'],'IDLE')
if __name__=='__main__': unittest.main(verbosity=2)
