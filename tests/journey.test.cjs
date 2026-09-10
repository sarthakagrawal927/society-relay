const {test} = require('node:test');
const assert = require('node:assert/strict');
const {repairJourney} = require('../relay/static/journey.js');

test('guide follows consent, delay, fresh authorization and separate confirmations', () => {
  const i = {id:'repair',status:'reported',reporters:['A-304','A-502'],confirmed:[]};
  const state = {journey:'difficult-repair',incidents:[i],events:[]};
  const event = title => state.events.push({incident_id:i.id,title});
  assert.equal(repairJourney(state).action,'agent');
  i.status='awaiting_approval';
  i.proposal={quote:1800,vendor:'ClearFlow',window:{label:'15:00–16:00'},visit_date:'2026-09-11'};
  assert.equal(repairJourney(state).action,'conflict');
  event('Visit replanned'); i.proposal.window=null;
  i.negotiation={status:'waiting',required:['A-502'],answers:{},label:'15:00–16:00'};
  assert.equal(repairJourney(state).action,'decline');
  event('Resident declined the exception');
  i.negotiation={status:'waiting',required:['A-304'],answers:{},label:'17:00–18:00'};
  assert.equal(repairJourney(state).unit,'A-304');
  assert.equal(repairJourney(state).action,'accept');
  i.negotiation.status='agreed';i.proposal.window={label:'17:00–18:00'};
  assert.equal(repairJourney(state).action,'approve');
  i.status='scheduled';i.proposal.approved=true;
  assert.equal(repairJourney(state).action,'delay');
  event('Vendor reported a delay');i.status='delayed';
  assert.equal(repairJourney(state).action,'agent');
  i.status='needs_attention';assert.equal(repairJourney(state).action,'replan');
  i.status='awaiting_approval';i.proposal.window=null;i.negotiation=null;
  assert.equal(repairJourney(state).action,'agent');
  i.negotiation={status:'waiting',required:['A-502'],answers:{},label:'15:00–16:00'};
  assert.equal(repairJourney(state).action,'accept');
  i.negotiation.status='agreed';i.proposal.window={label:'15:00–16:00'};
  assert.equal(repairJourney(state).action,'approve');
  i.status='scheduled';assert.equal(repairJourney(state).action,'complete');
  i.status='verifying';assert.equal(repairJourney(state).unit,'A-304');
  i.confirmed=['A-304'];assert.equal(repairJourney(state).unit,'A-502');
  assert.equal(repairJourney(state).chapter,5);
  i.confirmed.push('A-502');i.status='resolved';
  assert.equal(repairJourney(state).action,'evidence');
  assert.equal(repairJourney(state).chapter,6);
});

test('running agent never exposes a premature human action; failed idle run permits retry', () => {
  const state={journey:'difficult-repair',incidents:[{id:'a',status:'reported',reporters:['A-304'],confirmed:[]}],events:[],running:true};
  assert.equal(repairJourney(state).action,'waiting');
  state.running=false;state.runs=[{error:'provider unavailable'}];
  assert.equal(repairJourney(state).action,'agent');
});

test('guide stays out of custom workspaces and never promises consent after exhaustion', () => {
  assert.equal(repairJourney({incidents:[]}).action,'start');
  assert.equal(repairJourney({incidents:[{id:'custom'}]}),null);
  const state={journey:'difficult-repair',events:[],incidents:[{id:'a',status:'awaiting_approval',reporters:['A-304','A-502'],proposal:{window:null},negotiation:{status:'exhausted'}}]};
  assert.equal(repairJourney(state).action,'availability');
});
