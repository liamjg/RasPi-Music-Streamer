import vlc

class musicPlayer():
    def __init__(self):
        self.vlc_instance = vlc.Instance()
        self.player = self.vlc_instance.media_player_new()
        self.volume = 50
        self.player.audio_set_volume(self.volume)
        self.events = self.player.event_manager()
        self.now_playing = None

    def get_status(self):
        status = (self.player.get_time(),self.player.get_length())
        return status

    def song_finished(self,event):
        self.now_playing = None

    def play_url(self,url,now_playing):
        self.player.set_media(self.vlc_instance.media_new(url))
        self.events.event_attach(vlc.EventType.MediaPlayerEndReached, self.song_finished)
        self.player.play()
        self.now_playing = now_playing

    def play_pause(self):
        if self.player.get_state() == vlc.State.Playing:
            self.player.pause()
        else:
            self.player.play()

    def stop(self):
        self.player.stop()

    def volume_up(self):
        self.volume += 1
        if self.volume >= 100:
            self.volume = 100
        self.player.audio_set_volume(self.volume)

    def volume_down(self):
        self.volume -= 1
        if self.volume <= 0:
            self.volume = 0
        self.player.audio_set_volume(self.volume)
