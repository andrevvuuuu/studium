import json, os, signal, sys, tempfile, time, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import orchestrator as o
from job_progress import compute_overall, phase_plan

class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); o.RUNTIME_DIR=Path(self.tmp.name)
        (o.RUNTIME_DIR/'current-job.json').write_text(json.dumps({'job_id':'j1','operation':'normal','strict_sources':True}))
    def tearDown(self): self.tmp.cleanup()
    def test_normalize(self):
        self.assertEqual(len(o.normalize_sources({'source':{'type':'youtube'},'allow_base_knowledge':False})[0]),1)
        self.assertTrue(o.normalize_sources({'sources':[{'type':'web','label':'w'}],'strict_sources':True})[1])
        self.assertEqual(len(o.normalize_sources({'source':{'type':'multi','value':[{'type':'web'}]}})[0]),1)
    def test_multi_sources_progress(self):
        events=[]; original=o.update_status; o.update_status=lambda *a,**kw: events.append(kw['progress'])
        old=o.process_source_fast; o.process_source_fast=lambda source_info,*a,**kw:{'source_type':source_info['type'],'label':source_info['label'],'content_markdown':'text','raw_source_text':'x'*50,'extracted_files':[],'metadata':{'notebooks':[]}}
        try:
            r=o.process_sources_multi([{'type':'youtube','label':'Y'},{'type':'web','label':'W'},{'type':'local_files','label':'M'},{'type':'notebooklm','label':'N'}],Path(self.tmp.name),Path(self.tmp.name),Path(self.tmp.name),Path(self.tmp.name),{},False)
            self.assertIn('## Fonte 1/4 — Y (youtube)',r['content_markdown']); self.assertEqual([e['done'] for e in events],[0,1,1,2,2,3,3,4])
        finally:o.update_status=original;o.process_source_fast=old
    def test_strict_empty(self):
        old=o.process_source_fast;o.process_source_fast=lambda *a,**kw:{'raw_source_text':'','label':'x'}
        try:
            with self.assertRaisesRegex(RuntimeError,'Fonte «x»'):o.process_sources_multi([{'type':'web','label':'x'}],Path(self.tmp.name),Path(self.tmp.name),Path(self.tmp.name),Path(self.tmp.name),{},True)
        finally:o.process_source_fast=old
    def test_progress_and_monotonic(self):
        self.assertEqual(compute_overall('sources',1,['prep','sources','final']),15)
        o.update_status(Path(self.tmp.name),0,2,status='running',phase='writing',progress={'done':8,'total':10,'unit':'righe'})
        first=json.loads((o.RUNTIME_DIR/'job-status.json').read_text())['overall_percent']
        o.update_status(Path(self.tmp.name),0,1,status='running',phase='prep')
        self.assertEqual(json.loads((o.RUNTIME_DIR/'job-status.json').read_text())['overall_percent'],first)
    def test_cancel_guard(self):
        p=o.RUNTIME_DIR/'job-status.json';p.write_text(json.dumps({'status':'cancelled','job_id':'j1'}));(o.RUNTIME_DIR/'cancel-request.json').write_text(json.dumps({'job_id':'j1'}))
        o.update_status(Path(self.tmp.name),0,2,status='running',phase='sources');self.assertEqual(json.loads(p.read_text())['status'],'cancelled')
    def test_sigterm_converts_to_cancel(self):
        handler=signal.getsignal(signal.SIGTERM)
        try:
            signal.signal(signal.SIGTERM,lambda s,f: (_ for _ in ()).throw(o.JobCancelled()))
            with self.assertRaises(o.JobCancelled):os.kill(os.getpid(),signal.SIGTERM)
        finally:signal.signal(signal.SIGTERM,handler)
    def test_strict_prompt_text(self):
        text=o.strict_source_block([{'type':'web','label':'Pagina'}]);self.assertIn('VINCOLO INDEROGABILE — SOLO FONTI SELEZIONATE',text);self.assertIn('*(Non presente nelle fonti selezionate)*',text)
if __name__=='__main__':unittest.main()
