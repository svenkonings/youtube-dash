from json import loads
from re import sub
from sys import argv

from bottle import response, route, run
from youtube_dl import YoutubeDL
from youtube_dl.compat import compat_parse_qs, compat_urllib_parse_urlencode
from youtube_dl.extractor import YoutubeIE


class Extractor(YoutubeIE):
    def __init__(self, ydl, *args, **kwargs):
        super(Extractor, self).__init__(*args, **kwargs)
        self.set_downloader(ydl)

    def extract(self, video_id):
        return self._real_extract(video_id)

    def _real_extract(self, video_id):
        url = 'https://www.youtube.com/embed/%s' % video_id
        webpage = self._download_webpage(url, video_id, 'Downloading embed webpage')
        data = compat_urllib_parse_urlencode({
            'video_id': video_id,
            'eurl': 'https://youtube.googleapis.com/v/' + video_id,
            'sts': self._search_regex(r'"sts"\s*:\s*(\d+)', webpage, 'sts', default='')
        })
        video_info_url = 'https://www.youtube.com/get_video_info?' + data
        video_info_webpage = self._download_webpage(video_info_url, video_id, 'Downloading video info webpage')
        video_info = compat_parse_qs(video_info_webpage)
        dash_mpd = video_info.get('dashmpd')[0]
        player_url_json = self._search_regex(r'"assets":.+?"js":\s*("[^"]+")', webpage, 'JS player URL')
        player_url = loads(player_url_json)

        def decrypt_sig(mobj):
            s = mobj.group(1)
            dec_s = self._decrypt_signature(s, video_id, player_url)
            return '/signature/%s' % dec_s

        mpd_url = sub(r'/s/([a-fA-F0-9\.]+)', decrypt_sig, dash_mpd)
        return self._download_webpage_handle(mpd_url, video_id, 'Downloading MPD manifest')[0]


_extractor = Extractor(YoutubeDL())


@route('/youtube/<video_id>')
def extract(video_id):
    response.content_type = "video/vnd.mpeg.dash.mpd"
    return _extractor.extract(video_id)


run(host='0.0.0.0', port=int(argv[1]))
