import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import app as module


class GlobalStudioTests(unittest.TestCase):
    def test_pages_ideas_and_validation(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(module, "DATA", Path(directory)), patch.object(module, "jobs", {}), patch.object(module.threading, "Thread") as worker:
            client = module.app.test_client()
            page = client.get('/global')
            self.assertEqual(page.status_code, 200)
            self.assertIn(b'global_en', page.data)
            self.assertIn(b'use-idea', page.data)
            self.assertIn(b'global_en', client.get('/api/health').data)
            self.assertEqual(client.get('/api/global/ideas').json['kind'], 'editorial')
            self.assertEqual(client.post('/api/jobs', data={'url':'https://youtu.be/test','audience':'unknown'}).status_code,400)
            self.assertEqual(client.post('/api/jobs', data={'url':'https://youtu.be/test','topic':'unknown'}).status_code,400)
            response = client.post('/api/jobs', data={'video':(io.BytesIO(b'fixture'),'test.mp4'),'audience':'global_en','topic':'career'})
            self.assertEqual(response.status_code,202)
            jid = response.json['id']
            self.assertEqual(worker.call_args.kwargs['args'][-2:],('global_en','career'))
            job = json.loads((module.DATA/jid/'job.json').read_text())
            self.assertEqual(job['audience'],'global_en')
            self.assertEqual(job['topic'],'career')

    def test_translation_task_and_english_caption_with_original_audio(self):
        class Model:
            def transcribe(self, path, **kwargs):
                self.options = kwargs
                return iter([SimpleNamespace(start=0,end=15,text='A small habit can change your daily routine.')]), None
        for audience, task in [('local','transcribe'),('global_en','translate')]:
            with self.subTest(audience=audience), tempfile.TemporaryDirectory() as directory, patch.object(module,'DATA',Path(directory)), patch.object(module,'jobs',{}), patch.object(module,'model',Model()), patch.object(module,'run'), patch.object(module,'summarize',return_value={'caption':'A small habit can change your daily routine.','caption_source':'ai_local'}), patch.object(module,'render_clip',return_value={'mode':'center'}) as render:
                jid='a'*32; folder=module.DATA/jid;folder.mkdir()
                source=folder/'source.mp4';source.write_bytes(b'original audio video')
                module.jobs[jid]=dict(id=jid,title='Test',audience=audience,done=False,clips=[])
                module.process(jid,None,source,15,1,'id','720',audience,'general')
                job=module.jobs[jid]
                self.assertFalse(job.get('error'),job)
                self.assertEqual(module.model.options['task'],task)
                self.assertEqual(module.model.options['language'],'id')
                self.assertEqual(render.call_args.args[0],source)
                self.assertIn('A small habit', (folder/'clip-1.ass').read_text())
                caption=job['clips'][0]['caption']
                self.assertLessEqual(len(caption),121)
                self.assertNotIn('\n',caption)
                self.assertEqual(job['clips'][0]['audience'],audience)

    def test_topic_bias_preserves_nonoverlapping_candidate_selection(self):
        segments=[dict(start=0,end=15,text='A story from daily life.'),dict(start=20,end=35,text='A habit routine for focus and productivity.')]
        chosen=module.candidates(segments,15,1,'habits')
        self.assertGreater(chosen[0]['start'],15)
        self.assertNotIn('Apa pendapatmu',module.make_caption('English text','global_en'))


if __name__=='__main__':unittest.main()
