'use strict';
const fsDefault = require('node:fs');
const path = require('node:path');
const child = require('node:child_process');
const RUNTIME_DIR = process.env.ANTIGRAVITY_RUNTIME_DIR || '/tmp/antigravity_runtime';
const PHASE_BANDS = { prep:[0,3], sources:[3,15], context:[15,20], writing:[20,85], verify:[85,97], final:[97,100] };
const terminal = s => ['completed','error','cancelled','idle'].includes(s);
function phasePlanFor(job={}) { const op=job.operation_type||job.operation||'normal', strict=job.strict_sources ?? ((job.source||{}).type==='notebooklm' && !job.allow_base_knowledge); const p=['prep','sources','context','writing']; if(op==='moc'||(op==='normal'&&strict))p.push('verify'); p.push('final'); return p; }
function computeOverallPercent(status={}, plan=phasePlanFor(readJob())) { if(status.status==='completed')return 100; if(Number.isFinite(status.overall_percent))return Math.max(0,Math.min(100,status.overall_percent)); const phase=status.phase||'prep'; let [lo,hi]=PHASE_BANDS[phase]||[0,3]; if(phase==='final'&&!plan.includes('verify'))[lo,hi]=[85,100]; const p=status.progress, f=p&&Number(p.total)>0?Math.max(0,Math.min(1,Number(p.done)/Number(p.total))):0; return Math.round(lo+(hi-lo)*f); }
function readJson(file,fs=fsDefault){try{return JSON.parse(fs.readFileSync(file,'utf8'));}catch{return null;}}
function readStatus(opts={}){return readJson(path.join(opts.runtimeDir||RUNTIME_DIR,'job-status.json'),opts.fs||fsDefault);}
function readJob(opts={}){return readJson(path.join(opts.runtimeDir||RUNTIME_DIR,'current-job.json'),opts.fs||fsDefault)||{};}
function isJobActive(status,opts={}){if(!status||status.status!=='running')return false;const age=(opts.now||Date.now)()-(status.updated_at||0);if(age>600000)return false;const kill=opts.kill||process.kill.bind(process);
 // Il gruppo di run_job.sh resta vivo per tutto il job; il pid nello stato può essere di un processo breve (--set-status)
 try{const pgid=Number((opts.fs||fsDefault).readFileSync(path.join(opts.runtimeDir||RUNTIME_DIR,'job.pgid'),'utf8').trim());if(pgid>0){kill(-pgid,0);return true;}}catch{}
 if(!status.pid)return false;try{kill(status.pid,0);return true;}catch{return false;}}
function resetForNewJob(jobId,opts={}){const fs=opts.fs||fsDefault,dir=opts.runtimeDir||RUNTIME_DIR;fs.mkdirSync(dir,{recursive:true});for(const f of ['cancel-request.json','job.pgid'])try{fs.unlinkSync(path.join(dir,f));}catch{};return jobId;}
function createJobController(opts={}){const fs=opts.fs||fsDefault,dir=opts.runtimeDir||RUNTIME_DIR,kill=opts.kill||process.kill.bind(process),execSync=opts.execSync||child.execSync,now=opts.now||Date.now,delay=opts.setTimeout||setTimeout,jobId=readJob(opts).job_id||null, ac=new AbortController();let aborted=false;
 async function abort(reason){if(aborted)return {ok:true,method:'noop'};aborted=true;ac.abort(reason);fs.mkdirSync(dir,{recursive:true});fs.writeFileSync(path.join(dir,'cancel-request.json'),JSON.stringify({job_id:jobId,at:now()}));let method='signal';try{const pgid=fs.readFileSync(path.join(dir,'job.pgid'),'utf8').trim();if(pgid){kill(-Number(pgid),'SIGTERM');await new Promise(r=>delay(r,3000));try{kill(-Number(pgid),0);kill(-Number(pgid),'SIGKILL');}catch{}}else{method='pkill';execSync("pkill -f 'orchestrator.py|run_job.sh' || true");}}catch(e){method='pkill';try{execSync("pkill -f 'orchestrator.py|run_job.sh' || true");}catch{}}
 const prior=readStatus(opts)||{};const status={...prior,status:'cancelled',job_id:jobId,overall_percent:prior.overall_percent||0,percent:prior.overall_percent||0,pid:null,updated_at:now()};fs.writeFileSync(path.join(dir,'job-status.json'),JSON.stringify(status));try{fs.rmSync(path.join(dir,'job-context'),{recursive:true,force:true});}catch{}return {ok:true,method};}
 return {signal:ac.signal,jobId,abort};}
let singleton;
function getJobController(opts={}){const s=readStatus(opts);if(!singleton||singleton.signal.aborted||terminal(s&&s.status))singleton=createJobController(opts);return singleton;}
function onStatus(cb,{intervalMs=800,signal, ...opts}={}){let timer;const tick=()=>{if(signal&&signal.aborted)return;const s=readStatus(opts);if(s)cb(s);if(!(signal&&signal.aborted))timer=(opts.setTimeout||setTimeout)(tick,intervalMs);};tick();return ()=>{if(timer)(opts.clearTimeout||clearTimeout)(timer);};}
module.exports={phasePlanFor,computeOverallPercent,readStatus,readJob,isJobActive,resetForNewJob,createJobController,getJobController,onStatus};
// Templater carica ogni .js in Scripts/ come user script ed esige che i valori enumerabili siano solo funzioni:
// le costanti restano accessibili ma non enumerabili.
Object.defineProperty(module.exports,"RUNTIME_DIR",{value:RUNTIME_DIR,enumerable:false});
Object.defineProperty(module.exports,"PHASE_BANDS",{value:PHASE_BANDS,enumerable:false});
