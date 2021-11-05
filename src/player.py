from PIL import ImageFont, ImageDraw
from luma.core.interface.serial import spi
from luma.core.render import canvas
from luma.oled.device import ssd1351
from gmusicapi import Mobileclient
from tree_nodes import TreeNode, TrackNode
from vlc_playback import musicPlayer
from threading import Thread, Lock

import time
import pigpio
import rotary_encoder
import vlc

#gpio pins
ENC_A = 12
ENC_B = 16
ENC_SW = 6
SW_A = 5

PAGE_SIZE = 11
MENU_COLOR = 'blue'
DEVICE_ID = ''

global device, library, gpm_client, player
global curr_menu, counter, page_start, page_next

in_play_menu = False

run = True

lock = Lock()

def do_gp_auth():
    global gpm_client

    wait_screen('Connecting ...')
    gpm_client = Mobileclient()

    wait_screen('Logging in ...')
    gpm_client.oauth_login(DEVICE_ID,oauth_credentials="gp_auth")

def update_library():
    global library, curr_menu

    wait_screen('Fetching Library ...')
    library = gpm_client.get_all_songs()

    wait_screen('Building Tree ...')
    menu_tree = build_menu_trees()

    curr_menu = menu_tree.children

    reset_menu_counters()
    draw_screen()

def build_menu_trees():
    root = TreeNode(0, 'root')

    TreeNode(1, 'Now Playing', root)
    artists = TreeNode(1,'Library', root)
    TreeNode(1,'Update Library', root)
    TreeNode(1,'Exit', root)

    for i in range(len(library)):
        artist_name = library[i]['artist']
        artist = artists.search_by_name(artist_name)
        if not artist:
            artist = TreeNode(2,artist_name,artists)

        album_name = library[i]['album']
        album = artist.search_by_name(album_name)
        if not album:
            album = TreeNode(3,album_name,artist)

        track_num = library[i]['trackNumber']
        track = TrackNode(4,i,track_num,album)

    artists.sort_children()

    for i in range(len(library)):
        artist_name = library[i]['artist']
        artist = artists.search_by_name(artist_name)

        artist.sort_children()

        album_name = library[i]['album']
        album = artist.search_by_name(album_name)
        
        album.sort_tracks()

    return root

def reset_menu_counters():
    global counter, page_start, page_next
    counter = 0
    page_start = 0
    page_next = PAGE_SIZE

def draw_tool_bar(draw):
    draw.rectangle((0, 0, 128, 10), outline="white", fill="white")
    draw.text((112, 0),str(player.volume), font=ImageFont.load_default(), outline="black", fill="black")
    if player.now_playing is not None:
        draw.text((5, 0), player.now_playing['title'][0:17], font=ImageFont.load_default(), outline="black", fill="black")

def draw_menu(draw, menu_window):
    for i in range(len(menu_window)):
        index = page_start + i

        if curr_menu[index].level == 4:
            text = library[curr_menu[index].libindex]['title']
        else:
            text = menu_window[i].name
        if index == counter:
            y = (i%PAGE_SIZE*10)+10
            draw.rectangle((0, y+1, 128, y+10), outline=MENU_COLOR, fill=MENU_COLOR)
            draw.text((4, y), text, font=ImageFont.load_default(), outline="white",fill="white")
        else:
            draw.text((0, (i*10)+10), text, font=ImageFont.load_default(), fill=MENU_COLOR)

def draw_info(draw, track_dict):
    draw.text((5, 26), track_dict['title'], fill="white")
    draw.text((5, 36), track_dict['album'], fill="green")
    draw.text((5, 46), track_dict['artist'], fill="yellow")

def ms_to_str(ms):
    minutes = (ms / 1000) / 60
    seconds = int(ms / 1000) % 60
    return str(int(minutes)) + ":" + str(int(seconds)).zfill(2)

def draw_progress_bar(draw, t_x, t_f):
    Y_POSITION = 98
    draw.text((0, Y_POSITION), ms_to_str(t_x), fill="white")
    draw.text((104, Y_POSITION), ms_to_str(t_f-t_x), fill="white")

    draw.rectangle((10, (Y_POSITION+10), 118, (Y_POSITION+20)), outline="white", fill="black")

    if t_f is not 0:
        progress = (t_x / t_f) * 108
        draw.rectangle((10, (Y_POSITION+10), (10 + int(progress)), (Y_POSITION+20)), outline="white", fill="white")

def draw_screen():
    with canvas(device) as draw:
        draw_menu(draw, curr_menu[page_start:page_next])
        draw_tool_bar(draw)

def draw_player():
    t_x, t_f = player.get_status()
    with canvas(device) as draw:
        draw_info(draw, player.now_playing)
        draw_progress_bar(draw, t_x, t_f)
        draw_tool_bar(draw)

def wait_screen(message):
    with canvas(device) as draw:
        draw.text((5, 64), message, fill="yellow")

def select_track():
    track_dict = library[curr_menu[counter].libindex]
    
    if player.now_playing is not None and player.now_playing['title'] is not track_dict['title']:
        player.stop()
        player.now_playing = None

    if player.now_playing is None:
        wait_screen("Fetching Stream ...")
        stream_URL = gpm_client.get_stream_url(track_dict['storeId'],DEVICE_ID)
        player.play_url(stream_URL,track_dict)

def rotary_sw_callback(gpio,level,tick):
    global curr_menu, in_play_menu, run
    with lock:
        if player.now_playing and in_play_menu:
            player.play_pause()
        elif curr_menu[counter].name == 'Now Playing': 
            if player.now_playing:
                in_play_menu = True
        elif curr_menu[counter].level == 4:
            select_track()
            in_play_menu = True
        elif curr_menu[counter].name == 'Update Library': 
            update_library()
        elif curr_menu[counter].name == 'Exit': 
            run = False
        else:
            curr_menu = curr_menu[counter].children
            reset_menu_counters()
            draw_screen()

def sw_callback(gpio,level,tick):
    global curr_menu, in_play_menu
    with lock:
        if in_play_menu:
            in_play_menu = False
        elif curr_menu[counter].parent.level is not 0:
            curr_menu = curr_menu[counter].parent.parent.children #forgive me
            reset_menu_counters()

        draw_screen()

def rotary_callback(way):
    global counter, page_start, page_next
    with lock:
        if in_play_menu:
            if way < 0:
                player.volume_up()
            else:
                player.volume_down()
        else:
            counter -= way

            if(counter < 0):
                counter = 0
            elif(counter == len(curr_menu)):
                counter = len(curr_menu)-1

            if(counter == page_next):
                page_start = page_next
                page_next += PAGE_SIZE
            elif(counter == page_start-1):
                page_next = page_start
                page_start -= PAGE_SIZE

            draw_screen()

def start_player_clk():
    while run:
        time.sleep(0.1)
        if in_play_menu and player.now_playing is not None:
            with lock:
                draw_player()

def main():
    global player

    do_gp_auth()

    player = musicPlayer()

    update_library()

    pi = pigpio.pi()
    pi.set_glitch_filter(SW_A, 300)

    rot = rotary_encoder.decoder(pi, ENC_A, ENC_B, rotary_callback)
    rot_sw = pi.callback(ENC_SW,pigpio.RISING_EDGE, rotary_sw_callback)
    button = pi.callback(SW_A,pigpio.RISING_EDGE, sw_callback)

    t = Thread(target=start_player_clk)
    t.start()
    t.join()

    button.cancel()
    rot_sw.cancel()
    rot.cancel()
    pi.stop()


if __name__ == "__main__":
    try:
        device = ssd1351(spi(port=0), rotate=0, bgr=True)
        main()
