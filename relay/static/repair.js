const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let proof, position = 0;
const stories = [
  ['Residents report', 'Two households describe the same loss of water supply. Their original reports are saved independently before the model assesses them.'],
  ['AI interprets and proposes', 'The evidence specialist groups the shared fault. Relay connects the reports and proposes the approved vendor at the fixed quote. No work is authorized yet.'],
  ['Resident changes a constraint', 'A-502 can only provide evening access. The previous shared window disappears. An attempted approval using the stale proposal was rejected by the application.'],
  ['AI requests; a person decides', 'Relay has compared the allowed alternatives and asked for one exception. It has not edited a calendar or assumed agreement.'],
  ['Resident declines', 'The answer is no. That refusal stays in the record and excludes further requests to this household in the same planning round.'],
  ['AI changes its plan', 'The next request involves a different household. Inspect the required and declined households in the saved state below.'],
  ['Resident grants limited consent', 'A yes makes this one visit possible. The saved general availability remains unchanged, and committee approval is still required.'],
  ['Committee authorizes spending', 'A person approves the exact date, window, vendor and ₹1,800 proposal. Only now is there an authorized demonstration work order.'],
  ['AI follows up on a delay', 'After the technician reports a missed visit, Sentinel checks the saved milestone. The issue returns to the committee for a decision. The quote does not increase.'],
  ['Committee reopens planning', 'A revised date requires a fresh agreement. The previous one-time yes cannot be carried forward and the proposal is no longer approved.'],
  ['AI seeks fresh consent', 'Relay asks for access on the revised date. It must wait for a new human answer before this visit can be authorized.'],
  ['Resident agrees to the new visit', 'Consent has been given for the revised date. This still does not authorize spending: the committee must approve again.'],
  ['Vendor reports a result', 'Following fresh committee approval, the vendor reports the pump repair complete. The saved status is verifying, not resolved.'],
  ['First household verifies', 'A-304 confirms restoration. A-502 has not yet confirmed, so the shared repair remains open.'],
  ['Second household verifies', 'Both reporting households now confirm restoration. The issue closes at the same ₹1,800 quote, with household availability unchanged.']
];
function render() {
  const c = proof.checkpoints[position], i = c.incident, [actor, story] = stories[position];
  $('#position').textContent = `${position + 1} / ${proof.checkpoints.length}`;
  $('#previous').disabled = position === 0; $('#next').disabled = position === proof.checkpoints.length - 1;
  $('#chapters').innerHTML = proof.checkpoints.map((c,n) => `<button data-checkpoint="${n}" ${n === position ? 'aria-current="step"' : ''}><span>${String(n+1).padStart(2,'0')}</span>${esc(c.label)}</button>`).join('');
  $('#actor').textContent = actor; $('#checkpoint-title').textContent = c.label; $('#checkpoint-story').textContent = story;
  $('#checkpoint-stats').innerHTML = [[i.proposal ? '₹'+i.proposal.quote.toLocaleString('en-IN') : '—','Fixed quote'],[`${i.confirmed.length} / ${i.reporters.length}`,'Household confirmations'],[i.status.replaceAll('_',' '),'Saved repair status']].map(([v,k])=>`<div><strong>${esc(v)}</strong><span>${esc(k)}</span></div>`).join('');
  const previousIds = new Set(position ? proof.checkpoints[position-1].events.map(e=>e.id) : []);
  $('#checkpoint-receipts').innerHTML = c.events.filter(e=>!previousIds.has(e.id)).map(e=>`<div class="proof-receipt"><small>${esc(e.actor)} · ${esc(new Date(e.at).toISOString().slice(11,19))} UTC</small><strong>${esc(e.title)}</strong><p>${esc(e.detail)}</p></div>`).join('');
  $('#checkpoint-json').textContent = JSON.stringify({status:i.status,reporters:i.reporters,confirmed:i.confirmed,availability:c.availability,proposal:i.proposal ? {id:i.proposal.id,quote:i.proposal.quote,date:i.proposal.visit_date,window:i.proposal.window?.label || null,approved:i.proposal.approved} : null,access_request:i.negotiation ? {date:i.negotiation.visit_date,window:i.negotiation.label,required:i.negotiation.required,answers:i.negotiation.answers,declined_households:i.negotiation.declined_units}:null},null,2);
}
$('#previous').onclick = () => {if(position>0){position--;render();}};
$('#next').onclick = () => {if(position<proof.checkpoints.length-1){position++;render();}};
$('#chapters').onclick = e => {const button=e.target.closest('[data-checkpoint]');if(button){position=Number(button.dataset.checkpoint);render();}};
async function start() {
  try {
    const response=await fetch('/static/repair-proof.json'); if(!response.ok)throw Error('The recorded evidence is unavailable. You can still try the live repair.');
    proof=await response.json(); if(!proof.passed || proof.checkpoints.length!==stories.length)throw Error('This record has not passed its acceptance checks.');
    $('#proof-date').textContent=`Verified ${new Date(proof.verified_at).toLocaleDateString('en-GB')} on the public AWS deployment. These are measured run times, not a latency guarantee.`;
    $('#model-runs').innerHTML=proof.runs.map((r,n)=>`<div class="model-run"><strong>Run ${n+1} · ${esc(r.model)} · ${r.seconds}s</strong><span>${esc([...new Set(r.calls.filter(c=>c.ok && c.tool!=='inspect_workspace').map(c=>c.tool))].join(' → '))}</span></div>`).join('');
    render(); $('#proof').classList.remove('hidden');
  } catch(error) {$('#proof-error').textContent=error.message;}
}
start();
