import unittest
import app
from speaker_crop import SpeakerTracker


class SpeechCutTests(unittest.TestCase):
    def test_finishes_utterance_past_target_without_truncated_text(self):
        segments = [dict(start=0,end=12,text='Kenapa ini penting'),
                    dict(start=12,end=32,text='karena kalimatnya perlu diselesaikan.'),
                    dict(start=34,end=49,text='Topik berikutnya.')]
        clip = app.candidates(segments,30,1)[0]
        self.assertEqual(clip['start'],0)
        self.assertAlmostEqual(clip['end'],32.15)
        self.assertNotIn('Topik',clip['text'])
        self.assertTrue(clip['text'].endswith('diselesaikan.'))

    def test_no_mid_segment_cut_when_no_sentence_boundary(self):
        segments = [dict(start=0,end=18,text='awal ucapan'),dict(start=18,end=38,text='lanjutan ucapan')]
        clip = app.candidates(segments,30,1)[0]
        self.assertGreaterEqual(clip['end'],18)
        self.assertLessEqual(clip['end'],18.15)
        self.assertEqual(clip['text'],'awal ucapan')
        self.assertEqual(app.candidates([dict(start=0,end=90,text='ucapan sangat panjang')],15,1),[])

    def test_all_selected_text_is_inside_nonoverlapping_cuts(self):
        segments=[dict(start=i*17,end=i*17+15,text=f'Kenapa cerita nomor {i} penting.') for i in range(10)]
        clips=app.candidates(segments,30,5)
        for clip in clips:
            for segment in segments:
                if segment['text'] in clip['text']:
                    self.assertLessEqual(clip['start'],segment['start'])
                    self.assertGreaterEqual(clip['end'],segment['end'])
        for i,clip in enumerate(clips):
            for other in clips[i+1:]:
                self.assertLessEqual(min(clip['end'],other['end'])-max(clip['start'],other['start']),0)

    def test_speaker_switch_needs_voice_and_sustained_mouth_motion(self):
        tracker=SpeakerTracker()
        faces=[dict(center=.25,area=100,activity=0),dict(center=.75,area=90,activity=.2)]
        for i in range(8): tracker.update(faces,False,i*.25)
        self.assertEqual(tracker.speaker,.25)
        tracker.update(faces,True,2)
        self.assertEqual(tracker.speaker,.25)
        for i in range(3): tracker.update(faces,True,2.25+i*.25)
        self.assertEqual(tracker.speaker,.75)
        before=tracker.center
        after=tracker.update([],False,3)
        self.assertLessEqual(abs(after-before),.0350001)
