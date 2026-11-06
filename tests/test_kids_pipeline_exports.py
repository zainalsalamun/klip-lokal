import copy
from collections import OrderedDict
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import importlib
import hashlib
import subprocess
import cv2

m = importlib.import_module('app')


class KidsPipelineExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.assets = self.root / 'watermark-assets'; self.assets.mkdir()
        self.briefs = self.root / 'kids-briefs'; self.briefs.mkdir()
        self.patches = [patch.object(m, 'DATA', self.root), patch.object(m, 'KIDS_BRIEFS', self.briefs),
                        patch.object(m, 'WATERMARK_ASSETS', self.assets), patch.object(m, 'jobs', {}),
                        patch.object(m, 'history_cache', OrderedDict()), patch.object(m, 'active_export', None),
                        patch.object(m, 'caption_requests', 0)]
        for p in self.patches: p.start()
        self.client = m.app.test_client()
        self.brief = self.client.post('/api/kids/briefs', json={'title':'Warna merah', 'learning_goal':'Mengenali merah', 'target_duration':15}).json['brief']

    def tearDown(self):
        for p in reversed(self.patches): p.stop()
        self.tmp.cleanup()

    def create_kids(self, **overrides):
        data = {'content_profile':'kids', 'audience':'local', 'language':'id', 'source_kind':'speech',
                'brief_id':self.brief['brief_id'], 'brief_revision':'1', 'duration':'15', 'count':'1',
                'video':(io.BytesIO(b'fixture'), 'test.mp4')}
        data.update(overrides)
        with patch.object(m.threading, 'Thread'):
            return self.client.post('/api/jobs', data=data)

    def test_snapshot_modes_and_general_backwards_compatibility(self):
        for values in ({'audience':'global_en'}, {'language':'en'}, {'language':'auto'}, {'source_kind':'music'}, {'content_profile':'invalid'}):
            self.assertEqual(self.create_kids(**values).status_code, 400)
        self.assertEqual(self.create_kids(brief_revision='2').status_code, 409)
        response = self.create_kids()
        self.assertEqual(response.status_code, 202)
        jid = response.json['id']
        job = self.client.get('/api/jobs/' + jid).json
        self.assertEqual(job['kids_metadata']['brief_snapshot']['title'], 'Warna merah')
        self.client.patch('/api/kids/briefs/' + self.brief['brief_id'], json={'expected_revision':1,'title':'Biru'})
        self.assertEqual(self.client.get('/api/jobs/' + jid).json['kids_metadata']['brief_snapshot']['title'], 'Warna merah')
        m.jobs[jid]['done'] = True
        self.assertEqual(self.client.get('/api/jobs').json['jobs'][0]['content_profile'], 'kids')
        self.assertNotIn('kids_metadata', self.client.get('/api/jobs').json['jobs'][0])
        with patch.object(m.threading, 'Thread'):
            legacy = self.client.post('/api/jobs', data={'video':(io.BytesIO(b'x'),'test.mp4')})
        self.assertEqual(legacy.status_code, 202)
        self.assertEqual(m.jobs[legacy.json['id']]['content_profile'], 'general')
        self.assertEqual(m.jobs[legacy.json['id']]['language'], 'auto')

    def test_goal_words_prefer_relevant_candidates_without_inventing_text(self):
        segments = [{'start':0,'end':10,'text':'Ini contoh kegiatan bermain balok di rumah.'},
                    {'start':12,'end':22,'text':'Ini contoh kegiatan mengenal warna merah di rumah.'}]
        chosen = m.candidates(segments, 15, 1, learning_goal='Mengenal warna merah')
        self.assertIn('merah', chosen[0]['text'])
        self.assertNotIn('pasti pintar', chosen[0]['text'])

    def test_source_route_locks_language_and_selected_brief(self):
        self.assertEqual(self.client.get('/kids/source').status_code, 400)
        html = self.client.get('/kids/source?brief=' + self.brief['brief_id']).text
        self.assertIn('name="content_profile" value="kids"', html)
        self.assertIn('name="brief_revision" value="1"', html)
        self.assertNotIn('<option value="en">', html)
        self.assertIn('Mengenali merah', html)

    def test_empty_transcript_and_caption_policy(self):
        response = self.create_kids(); jid=response.json['id']
        fake = type('Model', (), {'transcribe':lambda *a,**kw:(iter([]), None)})()
        with patch.object(m, 'model', fake), patch.object(m, 'run'):
            m.process(jid, '', self.root/jid/'source.mp4', 15, 1, 'id')
        self.assertTrue(m.jobs[jid]['done'])
        self.assertIn('Lagu/gerak', m.jobs[jid]['error'])
        with self.assertRaises(m.UnclearTranscript): m.kids_caption({'caption':'Tulis jawaban di komentar!'})
        self.assertEqual(m.kids_caption({'caption':'Mengenal warna merah pada benda sekitar.'})['caption'], 'Mengenal warna merah pada benda sekitar.')

    def fixture_clip(self):
        jid = 'b' * 32; folder=self.root/jid; folder.mkdir()
        source=folder/'clip-1.mp4'
        subprocess.run([m.FFMPEG,'-hide_banner','-loglevel','error','-y','-f','lavfi','-i','color=c=blue:s=160x284:r=10:d=1',
                        '-f','lavfi','-i','sine=frequency=440:duration=1','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-shortest',str(source)],check=True)
        job={'id':jid,'done':True,'clips':[{'clip_id':'c'*32,'file':'clip-1.mp4','start':0,'end':1,
             'watermark':dict(m.watermark.DEFAULT_WATERMARK_CONFIG,enabled=True,text='TEST',width_ratio=.3),
             'watermark_revision':1,'caption_revision':1,'metadata_revision':1}]}
        m.jobs[jid]=job; m.write_job_atomic(jid,job)
        return jid, source

    def test_kids_render_survives_caption_model_failure(self):
        jid, source = self.fixture_clip()
        source_copy = source.with_name('source.mp4'); source_copy.write_bytes(source.read_bytes())
        m.jobs[jid]['content_profile'] = 'kids'
        m.jobs[jid]['kids_metadata'] = {'age_band':'3_5','language':'id','brief_snapshot':self.brief}
        segment = type('Segment', (), {'start':0, 'end':.8, 'text':'Ini balok merah untuk mengenal warna.'})()
        seen = {}
        def transcribe(audio, **kwargs):
            seen.update(kwargs)
            return iter([segment]), None
        fake = type('Model', (), {})(); fake.transcribe = transcribe
        selection = [{'start':0,'end':.9,'text':segment.text,'score':1}]
        with patch.object(m, 'model', fake), patch.object(m, 'candidates', return_value=selection), patch.object(m, 'summarize', side_effect=m.CaptionUnavailable('Fixture AI offline')):
            m.process(jid, '', source_copy, 15, 1, 'id', resolution='480')
        job = m.jobs[jid]
        self.assertTrue(job['done']); self.assertNotIn('error', job)
        self.assertEqual(seen['language'], 'id'); self.assertEqual(seen['task'], 'transcribe')
        self.assertTrue((source.parent / job['clips'][0]['file']).is_file())
        self.assertEqual(job['clips'][0]['caption_source'], 'none')
        self.assertEqual(job['clips'][0]['caption_language'], 'id')

    def test_versioned_media_exports_preserve_source_and_snapshot(self):
        jid, source=self.fixture_clip(); original=hashlib.sha256(source.read_bytes()).hexdigest()
        base=f'/api/jobs/{jid}/clips/{"c"*32}/exports'
        payload={'request_id':'d'*32,'kind':'video','expected_watermark_revision':1}
        with patch.object(m.threading,'Thread'):
            response=self.client.post(base,json=payload)
        self.assertEqual(response.status_code,202)
        self.assertEqual(self.client.post(base,json=payload).status_code,200)
        self.assertEqual(self.client.post(base,json={**payload,'kind':'thumbnail'}).status_code,409)
        self.assertEqual(self.client.delete('/api/jobs/'+jid).status_code,409)
        record=response.json['export']
        m.jobs[jid]['clips'][0]['watermark']['text']='CHANGED'
        m.export_worker(jid,'c'*32,record,source)
        status=self.client.get(base+'/'+'d'*32).json['export']
        self.assertEqual(status['status'],'done',status)
        self.assertEqual(status['settings']['watermark']['text'],'TEST')
        video=self.root/jid/'exports'/('d'*32)/'video.mp4'
        cap=cv2.VideoCapture(str(video)); ok,frame=cap.read(); cap.release()
        self.assertTrue(ok); self.assertEqual(frame.shape[:2],(284,160))
        # Burned watermark creates bright pixels on the blue source; audio stream retained.
        self.assertGreater(int(frame[:,:,1].max()),100)
        probe=subprocess.run([m.FFMPEG,'-i',str(video),'-f','null','-'],capture_output=True,text=True)
        self.assertIn('Audio:',probe.stderr)
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),original)
        with patch.object(m.threading,'Thread'):
            response=self.client.post(base,json={'request_id':'e'*32,'kind':'thumbnail','ratio':'landscape','frame_time':.4,'expected_watermark_revision':1})
        self.assertEqual(response.status_code,202)
        m.export_worker(jid,'c'*32,response.json['export'],source)
        thumb=cv2.imread(str(self.root/jid/'exports'/('e'*32)/'thumbnail.png'))
        self.assertEqual(thumb.shape[:2],(720,1280))
        with self.client.get(base+'/'+'e'*32+'/file') as download:
            self.assertEqual(download.status_code,200)
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),original)

    def test_export_failure_conflicts_and_busy_guards(self):
        jid, source=self.fixture_clip(); base=f'/api/jobs/{jid}/clips/{"c"*32}/exports'
        payload={'request_id':'f'*32,'kind':'thumbnail','frame_time':2,'expected_watermark_revision':1}
        self.assertEqual(self.client.post(base,json={**payload,'expected_watermark_revision':2}).status_code,409)
        with patch.object(m,'caption_requests',1):
            self.assertEqual(self.client.post(base,json=payload).status_code,409)
        with patch.object(m.threading,'Thread'):
            response=self.client.post(base,json=payload)
        self.assertEqual(self.client.get('/api/health').json['active_exports'],1)
        m.export_worker(jid,'c'*32,response.json['export'],source)
        status=self.client.get(base+'/'+'f'*32).json['export']
        self.assertEqual(status['status'],'failed')
        self.assertTrue(source.exists()); self.assertIsNone(m.active_export)
        self.assertEqual(self.client.get(base+'/'+'f'*32+'/file').status_code,409)
