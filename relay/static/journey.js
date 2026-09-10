/* The guide reads real workspace state. It never fabricates agent outcomes. */
function repairJourney(state) {
  const incidents = state.incidents || [];
  if (!incidents.length) return {chapter: 0, title: 'Two homes. No water. Then the plan falls apart.', text: 'Play the people in one difficult repair. Say no to an access request, introduce a missed visit, and see whether Relay earns its way to a verified outcome.', action: 'start', button: 'Start the difficult repair →', actor: 'You set the scene'};
  if (state.journey !== 'difficult-repair') return null;
  const i = incidents.find(x => x.status !== 'linked' && x.reporters.length > 1) || incidents[0];
  if (i.reporters.length < 2 && i.status !== 'reported') return {chapter:1, title:'Relay kept the reports separate.', text:'The live decision differs from the expected shared repair. Inspect the original reports and the activity record before proceeding. The guide will not pretend a merge happened.', action:'inspect', button:'Review the actual decision →', actor:'Human review', incident:i};
  const history = (state.events || []).filter(e => e.incident_id === i.id);
  const happened = title => history.some(e => e.title === title);
  const delayed = happened('Vendor reported a delay');
  const declined = happened('Resident declined the exception');
  const n = i.negotiation;
  let step;
  if (i.status === 'resolved') step = {chapter: 6, title: 'The agent followed through. The neighbours closed it.', text: `Both households confirmed restoration. The fixed quote is ₹${i.proposal.quote.toLocaleString('en-IN')}. Open the record to inspect the refusal, the revised visit, and the two separate confirmations.`, action: 'evidence', button: 'See the decision record →', actor: 'Outcome verified by residents'};
  else if (i.status === 'reported') step = {chapter: 1, title: 'Two descriptions. Is this really one fault?', text: 'Relay must read both reports, connect the shared supply problem, and propose a repair. The original reports remain available for a human correction.', action: 'agent', button: 'Let Relay assess the reports →', actor: 'Relay · understand and propose'};
  else if (i.status === 'awaiting_approval') {
    if (!delayed && !happened('Visit replanned') && i.proposal?.window) step = {chapter: 2, title: 'A plan works—until one calendar changes.', text: 'Both homes can currently make the visit. Introduce the complication: A-502 can now only be home in the evening. The old proposal must lose its authority.', action: 'conflict', button: 'A-502: I can only do evening →', actor: 'You play resident A-502'};
    else if (n?.status === 'waiting') {
      const unit = n.required.find(u => !n.answers[u]);
      step = !declined && !delayed
        ? {chapter: 2, title: 'A useful agent can hear “no”.', text: `Relay is asking ${unit} for access on ${n.visit_date}, ${n.label}. Decline this one-time request. Watch whether it finds a different household instead of asking the same person again.`, action: 'decline', button: `${unit}: not this time →`, actor: `You play resident ${unit}`, unit}
        : {chapter: delayed ? 4 : 3, title: delayed ? 'Yesterday’s yes cannot authorize a new visit.' : 'The refusal changed the plan.', text: `Relay now asks ${unit} for ${n.label} on ${n.visit_date}. ${delayed ? 'This is fresh consent for the revised date.' : 'The household that declined is not being asked again in this round.'} Accepting this visit leaves general availability unchanged.`, action: 'accept', button: `${unit}: yes, for this visit →`, actor: `You play resident ${unit}`, unit};
    } else if (i.proposal?.window) step = {chapter: delayed ? 4 : 3, title: 'An agreement is ready. Spending still needs you.', text: `${i.proposal.vendor} · ₹${i.proposal.quote.toLocaleString('en-IN')} · ${i.proposal.visit_date}, ${i.proposal.window.label}. Review the exact proposal before creating the demo work order.`, action: 'approve', button: `Approve ₹${i.proposal.quote.toLocaleString('en-IN')} for this visit →`, actor: 'You play the committee'};
    else if (n?.status === 'exhausted') step = {chapter: 3, title: 'No agreement is better than invented consent.', text: 'The available alternatives are exhausted. A person must revise availability or coordinate another plan. Relay cannot force a visit.', action: 'availability', button: 'Review household availability →', actor: 'A human decision is needed'};
    else step = {chapter: delayed ? 4 : 2, title: declined && !delayed ? 'The answer is recorded. Find a different way.' : 'No shared window. No invented agreement.', text: 'Relay compares eligible one-time exceptions. It must respect quiet hours, previous refusals in this round, and the fixed quote.', action: 'agent', button: 'Ask Relay to find another way →', actor: 'Relay · compare and request'};
  } else if (i.status === 'scheduled') step = !delayed
    ? {chapter: 4, title: 'Approved. And then the technician cannot make it.', text: 'Introduce a missed visit. Relay must notice the broken promise and return the next decision to the committee without adding to the quote.', action: 'delay', button: 'Facility team: report a missed visit →', actor: 'You play the facility team'}
    : {chapter: 5, title: 'A repair note is a claim. Let the homes test it.', text: 'The revised visit is authorized. Submit a fictional repair note: the common pump was restarted and supply pressure checked. This must not close the issue.', action: 'complete', button: 'Facility team: report repair complete →', actor: 'You play the facility team'};
  else if (i.status === 'delayed') step = {chapter: 4, title: 'A broken promise has reached Relay.', text: 'The delay is saved. Sentinel must inspect the milestone and surface a decision. A timer waking the agent is separate from the model deciding which tool to call.', action: 'agent', button: 'Let Relay catch the missed visit →', actor: 'Relay · follow up'};
  else if (i.status === 'needs_attention') step = {chapter: 4, title: 'The next visit needs a fresh decision.', text: 'The committee can reopen planning. The quote stays fixed, but the date changes and the previous one-time consent cannot be reused.', action: i.proposal?.approved ? 'replan' : 'inspect', button: i.proposal?.approved ? 'Committee: prepare a fresh visit →' : 'Review the issue →', actor: 'You play the committee'};
  else if (i.status === 'verifying') {
    const unit = i.reporters.find(u => !i.confirmed.includes(u));
    step = {chapter: 5, title: i.confirmed.length ? 'One home has water. The other still has a vote.' : '“Work complete” is not the finish line.', text: `${i.confirmed.length} of ${i.reporters.length} households have confirmed. ${unit} must check the outcome independently. Only the final household confirmation can close this shared issue.`, action: 'confirm', button: `${unit}: water is restored →`, actor: `You play resident ${unit}`, unit};
  }
  if (!step) return null;
  if (state.running && !['evidence', 'inspect'].includes(step.action)) step = {...step, action: 'waiting', button: `${state.live?.agent || 'Relay'} is working…`};
  return {...step, incident: i, history};
}
if (typeof module !== 'undefined') module.exports = {repairJourney};
