import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from kelip import app
from kelip import local_caption as ai


class LocalCaptionTests(unittest.TestCase):
    def test_grounded_summary_and_rejections(self):
        transcript='Menabung sedikit setiap hari membantu membangun dana darurat.'
        result=ai.parse_summary(json.dumps(dict(caption='Kebiasaan menabung kecil membantu menyiapkan dana darurat.',evidence='membangun dana darurat',unclear=False)),transcript)
        self.assertEqual(result['caption_source'],'ai_local')
        self.assertNotEqual(result['caption'],transcript)
        for invalid in [dict(caption='Elephants have long ears',evidence="And that's pretty much all there is to say.",unclear=False), dict(caption='Klaim baru.',evidence='beli bitcoin',unclear=False),dict(caption='',evidence='',unclear=True)]:
            with self.assertRaises(ai.UnclearTranscript): ai.parse_summary(json.dumps(invalid),transcript)
        with self.assertRaises(ai.CaptionUnavailable): ai.parse_summary('not json',transcript)
        with self.assertRaises(ai.CaptionUnavailable): ai.parse_summary(json.dumps(dict(caption='kata '*40,evidence='dana darurat',unclear=False)),transcript)

    def test_local_request_configuration_and_language(self):
        response={'message':{'content':json.dumps(dict(caption='Small savings can build your emergency fund.',evidence='an emergency fund',unclear=False))}}
        with patch.object(ai,'ensure_runtime',return_value={'models':[{'name':ai.MODEL}]}), patch.object(ai,'request',return_value=response) as request:
            result=ai.summarize('Small daily savings help build an emergency fund.','global_en')
            self.assertEqual(result['caption_status'],'ready')
            payload=request.call_args.args[1]
            self.assertFalse(payload['stream']);self.assertFalse(payload['think'])
            self.assertEqual(payload['keep_alive'],0)
            self.assertIn('English',payload['messages'][0]['content'])
            self.assertEqual(ai.BASE,'http://127.0.0.1:11434')
        with patch.object(ai,'ensure_runtime',return_value={'models':[]}):
            with self.assertRaises(ai.CaptionUnavailable): ai.summarize('This is a long enough transcript.')

    def test_regenerate_persists_without_touching_video_and_handles_errors(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(app,'DATA',Path(directory)),patch.object(app,'jobs',{}):
            jid='c'*32;folder=app.DATA/jid;folder.mkdir();video=folder/'clip-1.mp4';video.write_bytes(b'keep this video')
            (folder/'job.json').write_text(json.dumps(dict(done=True,audience='local',clips=[dict(text='Menabung rutin membantu menyiapkan dana darurat.',caption='old')])) )
            client=app.app.test_client();url=f'/api/jobs/{jid}/clips/0/caption'
            result=dict(caption='Tabungan rutin membantu membangun dana darurat.',caption_source='ai_local',caption_status='ready')
            with patch.object(app,'summarize',return_value=result):
                self.assertEqual(client.post(url).json['caption'],result['caption'])
            self.assertEqual(json.loads((folder/'job.json').read_text())['clips'][0]['caption'],result['caption'])
            self.assertEqual(video.read_bytes(),b'keep this video')
            self.assertEqual(client.post(f'/api/jobs/{jid}/clips/9/caption').status_code,404)
            for exception,code in [(ai.UnclearTranscript('unclear'),422),(ai.CaptionUnavailable('offline'),503)]:
                with patch.object(app,'summarize',side_effect=exception):
                    self.assertEqual(client.post(url).status_code,code)
                self.assertEqual(app.read_job(jid)['clips'][0]['caption'],result['caption'])
            app.jobs['d'*32]=dict(done=False)
            self.assertEqual(client.post(url).status_code,409)

    def test_caption_failure_does_not_fail_video_job(self):
        from types import SimpleNamespace
        class Model:
            def transcribe(self,*args,**kwargs):
                return iter([SimpleNamespace(start=0,end=15,text='Menabung rutin membantu membangun dana darurat.')]),None
        for exception,status in [(ai.CaptionUnavailable('offline'),'unavailable'),(ai.UnclearTranscript('unclear'),'needs_review')]:
            with self.subTest(status=status), tempfile.TemporaryDirectory() as directory, patch.object(app,'DATA',Path(directory)), patch.object(app,'jobs',{}), patch.object(app,'model',Model()), patch.object(app,'run'), patch.object(app,'render_clip',return_value={'mode':'center'}), patch.object(app,'summarize',side_effect=exception):
                jid='f'*32;folder=app.DATA/jid;folder.mkdir();source=folder/'source.mp4';source.write_bytes(b'fixture')
                app.jobs[jid]=dict(id=jid,title='Test',done=False,clips=[])
                app.process(jid,None,source,15,1,'id')
                job=app.read_job(jid)
                self.assertTrue(job['done']);self.assertNotIn('error',job)
                self.assertEqual(job['clips'][0]['caption_status'],status)
                self.assertEqual(job['clips'][0]['caption'],'')

    def test_severe_repetition_is_rejected_before_model_call(self):
        with patch.object(ai,'ensure_runtime') as runtime:
            with self.assertRaises(ai.UnclearTranscript):
                ai.summarize('Tapi diso no tapi diso no tapi diso no yang kamping cabawah di airpot belan gitu gitu benar benar benar.')
            runtime.assert_not_called()

    def test_local_rejects_english_and_retries_once_in_indonesian(self):
        transcript='Pembahasan kesehatan mental selama pandemi membutuhkan perhatian dan dukungan keluarga.'
        wrong=json.dumps(dict(caption='Explore mental health through pandemic stress and self-reflection.',evidence='kesehatan mental selama pandemi',unclear=False))
        correct=json.dumps(dict(caption='Menjaga kesehatan mental selama pandemi membutuhkan dukungan keluarga.',evidence='kesehatan mental selama pandemi',unclear=False))
        with patch.object(ai,'ensure_runtime',return_value={'models':[{'name':ai.MODEL}]}),patch.object(ai,'request',side_effect=[{'message':{'content':wrong}},{'message':{'content':correct}}]) as request:
            result=ai.summarize(transcript,'local')
            self.assertEqual(request.call_count,2)
            self.assertEqual(result['caption_language'],'id')
            self.assertEqual(result['caption'],json.loads(correct)['caption'])
            self.assertIn('BAHASA INDONESIA',request.call_args.args[1]['messages'][0]['content'])
        with patch.object(ai,'ensure_runtime',return_value={'models':[{'name':ai.MODEL}]}),patch.object(ai,'request',return_value={'message':{'content':wrong}}) as request:
            with self.assertRaises(ai.CaptionLanguageError):ai.summarize(transcript,'local')
            self.assertEqual(request.call_count,2)

    def test_global_rejects_indonesian_and_local_can_summarize_english_in_indonesian(self):
        transcript='Small daily steps help build consistent habits over time.'
        translated=dict(caption='Langkah kecil membantu membangun kebiasaan yang konsisten.',evidence='Small daily steps help build consistent habits over time.',unclear=False)
        result=ai.parse_summary(json.dumps(translated),transcript,'local')
        self.assertEqual(result['caption_language'],'id')
        with self.assertRaises(ai.CaptionLanguageError):ai.parse_summary(json.dumps(translated),transcript,'global_en')

    def test_evidence_index_selects_original_sentence_and_rejects_invalid_indices(self):
        transcript='Pembahasan ini penting. Dukungan keluarga membantu menjaga kesehatan mental selama pandemi.'
        raw=dict(unclear=False,evidence_id=1,caption='Dukungan keluarga membantu menjaga kesehatan mental selama pandemi.')
        result=ai.parse_summary(json.dumps(raw),transcript,'local')
        self.assertEqual(result['caption_evidence'],'Dukungan keluarga membantu menjaga kesehatan mental selama pandemi.')
        for index in [99,-1,True,'1']:
            raw['evidence_id']=index
            with self.assertRaises(ai.UnclearTranscript):ai.parse_summary(json.dumps(raw),transcript,'local')
