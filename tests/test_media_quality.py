import io
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import threading
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import av
import cv2
import numpy as np
from yt_dlp import YoutubeDL
import app
from media_quality import download_options, downloaded_path, output_quality
from speaker_crop import smooth_crop_points, crop_plan


class MediaQualityTests(unittest.TestCase):
    def test_split_hd_stream_preferred_over_combined_360p_offline(self):
        for cap in ('1080','1440','2160'):
            options = download_options(Path('/tmp/fixture'), app.FFMPEG, '/tmp/node', cap)
            formats = [{'format_id':'18','url':'https://example.invalid/360.mp4','ext':'mp4','height':360,'width':640,'vcodec':'avc1','acodec':'mp4a'},
                       {'format_id':'137','url':'https://example.invalid/1080.mp4','ext':'mp4','height':1080,'width':1920,'vcodec':'avc1','acodec':'none'},
                       {'format_id':'140','url':'https://example.invalid/audio.m4a','ext':'m4a','vcodec':'none','acodec':'mp4a'}]
            # Run the real yt-dlp format selector; no network or extractor used.
            with YoutubeDL(options) as ydl:
                selector = ydl.build_format_selector(options['format'])
                selected = list(selector({'formats':formats, 'has_merged_format':True, 'incomplete_formats':False}))[0]
                self.assertEqual(selected['format_id'], '137+140')
                self.assertEqual(selected['height'],1080)
            self.assertEqual(options['ffmpeg_location'],app.FFMPEG)

    def test_real_split_download_and_merge_with_bundled_ffmpeg(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); assets=root/'assets'; assets.mkdir(); out=root/'job';out.mkdir()
            app.run(['-f','lavfi','-i','color=c=blue:s=1280x720:r=10','-t','0.3','-an','-c:v','libx264',assets/'hd.mp4'])
            app.run(['-f','lavfi','-i','sine=frequency=440:sample_rate=16000','-t','0.3','-vn','-c:a','aac',assets/'audio.m4a'])
            class Handler(SimpleHTTPRequestHandler):
                def log_message(self,*a): pass
            server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(assets)))
            worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
            base=f'http://127.0.0.1:{server.server_port}'
            info={'id':'fixture','title':'Fixture split HD','extractor':'generic',
                  'formats':[{'format_id':'hd','url':base+'/hd.mp4','ext':'mp4','width':1280,'height':720,'vcodec':'avc1','acodec':'none'},
                             {'format_id':'audio','url':base+'/audio.m4a','ext':'m4a','vcodec':'none','acodec':'mp4a'}]}
            opts=download_options(out,app.FFMPEG,'/tmp/node');opts['noprogress']=True
            try:
                with YoutubeDL(opts) as ydl:
                    result=ydl.process_ie_result(info,download=True)
                    merged=downloaded_path(ydl,result,out)
                with av.open(str(merged)) as container:
                    self.assertEqual(container.streams.video[0].width,1280)
                    self.assertTrue(container.streams.audio)
            finally:
                server.shutdown();server.server_close();worker.join(timeout=2)

    def test_post_merge_path_and_effective_detail_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); merged=root/'source.mp4';merged.write_bytes(b'fixture')
            ydl=type('YDL',(),{'prepare_filename':lambda s,i:str(root/'source.webm')})()
            self.assertEqual(downloaded_path(ydl,{},root),merged)
        info=output_quality({'width':640,'height':360},1080,1920)
        self.assertAlmostEqual(info['upscale_factor'],5.333,places=3)
        self.assertEqual(info['effective_crop_width'],202)
        self.assertIn('640 × 360',info['warning'])
        self.assertEqual(output_quality({'width':3840,'height':2160},1080,1920)['warning'],'')

    def test_source_quality_validated_persisted_and_dispatched(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(app,'DATA',Path(tmp)),patch.object(app,'jobs',{}),patch.object(app.threading,'Thread') as worker:
            client=app.app.test_client()
            self.assertIn('source_quality', client.get('/api/health').json['capabilities'])
            self.assertEqual(client.post('/api/jobs',data={'url':'https://youtu.be/test','source_quality':'999'}).status_code,400)
            response=client.post('/api/jobs',data={'url':'https://youtu.be/test','source_quality':'2160'})
            self.assertEqual(response.status_code,202)
            self.assertEqual(worker.call_args.kwargs['kwargs']['source_quality'],'2160')
            self.assertEqual(app.jobs[response.json['id']]['source_quality'],'2160')

    def test_per_frame_velocity_limit_vfr_and_scene_reset(self):
        frames=[i/30 for i in range(150)]
        samples=[(0,0),(.267,0),(.533,700),(1.0,900),(2.9,900)]
        points=smooth_crop_points(samples,frames,1040,480)
        steps=np.diff([p[1] for p in points])
        self.assertEqual(len(points),150)
        self.assertLessEqual(max(abs(np.diff(steps))),4)
        self.assertLessEqual(max(abs(steps)),12) # <=312px/s plus integer quantization
        self.assertGreater(sum(steps>0),50)
        self.assertGreater(points[-1][1],880)
        vfr=[0,.017,.055,.13,.267,.4,.7,1.0]
        points=smooth_crop_points(samples,vfr,1040,480)
        self.assertEqual([p[0] for p in points],vfr)
        for a,b in zip(points,points[1:]):
            self.assertLessEqual(abs(b[1]-a[1]),312*(b[0]-a[0])+1.1)
        cut=smooth_crop_points([(0,0),(1,900)],frames,1040,480,cuts=[1])
        self.assertEqual(cut[29][1],0)
        self.assertEqual(cut[30][1],900)

    def test_real_crop_plan_uses_all_frame_pts_without_more_face_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source.mp4';audio=root/'audio.wav'
            app.run(['-f','lavfi','-i','color=c=gray:s=640x360:r=30','-t','2','-c:v','libx264',source])
            app.run(['-f','lavfi','-i','sine=frequency=300:sample_rate=16000','-t','2','-ac','1',audio])
            calls=[]
            class Detector:
                def empty(self): return False
                def detectMultiScale(self,*a,**kw):
                    calls.append(1); return [(50+min(len(calls),6)*50,80,100,100)]
            with patch('cv2.CascadeClassifier',return_value=Detector()):
                points,detected=crop_plan(source,audio,0,2,480,854)
            self.assertEqual(len(points),60)
            self.assertEqual(detected,len(calls))
            self.assertLessEqual(len(calls),9)
            self.assertLessEqual(max(abs(b[1]-a[1]) for a,b in zip(points,points[1:])),12)

    def test_actual_exported_motion_has_intermediate_frames(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); source=root/'source.mp4'; ass=root/'captions.ass';out=root/'out.mp4'
            # Static texture makes camera motion observable independently of moving subjects.
            texture=np.random.default_rng(4).integers(0,256,(360,640,3),dtype=np.uint8)
            cv2.imwrite(str(root/'texture.png'),cv2.GaussianBlur(texture,(5,5),0))
            app.run(['-loop','1','-i',root/'texture.png','-r','30','-t','2','-c:v','libx264','-pix_fmt','yuv420p',source])
            (root/'audio.wav').write_bytes(b'plan mocked, audio not read')
            app.write_subs(ass,[],0,2)
            points=smooth_crop_points([(0,0),(.267,0),(.533,600),(1.9,900)],[i/30 for i in range(60)],1040,480)
            with patch('speaker_crop.crop_plan',return_value=(points,8)):
                framing=app.render_clip(source,ass,out,0,2,'480')
            self.assertEqual(framing['camera_motion'],'per_frame_damped')
            self.assertEqual(framing['encoder']['crf'],18)
            shifts=[];previous=None
            with av.open(str(out)) as video:
                self.assertEqual(video.streams.video[0].average_rate,30)
                for frame in video.decode(video=0):
                    gray=cv2.cvtColor(frame.to_ndarray(format='bgr24'),cv2.COLOR_BGR2GRAY).astype('float32')
                    if previous is not None:
                        (dx,dy),confidence=cv2.phaseCorrelate(previous,gray)
                        if confidence>.4: shifts.append(abs(dx))
                    previous=gray
            self.assertGreater(len(shifts),40)
            self.assertLess(max(shifts),15)
            self.assertGreater(sum(v>1 for v in shifts),30)
