import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import av
from kelip import app as module
from kelip.subtitle_styles import SUBTITLE_STYLES


class SubtitleStyleTests(unittest.TestCase):
    def test_choice_validated_persisted_and_forwarded(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(module,'DATA',Path(directory)), patch.object(module,'jobs',{}), patch.object(module.threading,'Thread') as worker:
            client=module.app.test_client()
            self.assertEqual(client.post('/api/jobs',data={'url':'https://youtu.be/test','subtitle_style':'arbitrary ASS'}).status_code,400)
            for choice in SUBTITLE_STYLES:
                response=client.post('/api/jobs',data={'video':(io.BytesIO(b'fixture'),'video.mp4'),'subtitle_style':choice})
                self.assertEqual(response.status_code,202)
                jid=response.json['id']
                self.assertEqual(worker.call_args.kwargs['kwargs']['subtitle_style'],choice)
                self.assertEqual(json.loads((module.DATA/jid/'job.json').read_text())['subtitle_style'],choice)
                module.update(jid,done=True)
                module.jobs.clear()
                self.assertEqual(client.get('/api/jobs/'+jid).json['subtitle_style'],choice)
            response=client.post('/api/jobs',data={'video':(io.BytesIO(b'fixture'),'default.mp4')})
            self.assertEqual(module.jobs[response.json['id']]['subtitle_style'],'classic')

    def test_legacy_jobs_keep_classic(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(module,'DATA',Path(directory)), patch.object(module,'jobs',{}):
            folder=module.DATA/('e'*32);folder.mkdir()
            (folder/'job.json').write_text(json.dumps(dict(done=True,clips=[dict(text='Test')])) )
            job=module.read_job(folder.name)
            self.assertEqual(job['subtitle_style'],'classic')
            self.assertEqual(job['clips'][0]['subtitle_style'],'classic')

    def test_styles_really_render_differently_and_scale(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'source.mp4'
            module.run(['-f','lavfi','-i','color=c=blue:size=320x180:rate=10','-t','0.5','-c:v','libx264',source])
            for resolution in ['480','720']:
                fingerprints=[]
                for choice,config in SUBTITLE_STYLES.items():
                    ass=root/(choice+'.ass');out=root/(choice+resolution+'.mp4')
                    module.write_subs(ass,[dict(start=0,end=.5,text='Subtitle pilihan saya')],0,.5,choice)
                    self.assertIn('Style: Default,'+config['ass'],ass.read_text())
                    module.render_clip(source,ass,out,0,.5,resolution)
                    with av.open(str(out)) as stream:
                        frame=next(stream.decode(video=0)).to_ndarray(format='rgb24')
                        fingerprints.append(hashlib.sha256(frame.tobytes()).hexdigest())
                        if choice=='bold_yellow':
                            self.assertTrue(((frame[:,:,0]>180)&(frame[:,:,1]>180)&(frame[:,:,2]<100)).any())
                self.assertEqual(len(set(fingerprints)),len(SUBTITLE_STYLES))
