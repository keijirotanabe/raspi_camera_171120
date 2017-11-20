# coding: utf-8
import sys
import threading
import subprocess
import RPi.GPIO as GPIO
from time import sleep
from datetime import datetime
import picamera


# 定数宣言
RECORDING_UNIT = 3
RECORDING_BEFORE = 3  # 3の倍数で設定
RECORDING_AFTER = 0   # 3の倍数で設定
VIDEOS_DIR = '/home/pi/workspace/camera_171114/videos'
VIDEOS_TEMPORARY_DIR = '/home/pi/workspace/camera_171114/videos/videos_temporary'
CAMERA_RESOLUTION = (1280, 720)  # カメラ解像度: (横, 縦)
BEFORE_FILE_SIZE = RECORDING_BEFORE / RECORDING_UNIT
AFTER_FILE_SIZE = RECORDING_AFTER / RECORDING_UNIT

# ピン設定
SLIDE0_PIN = 26
SLIDE1_PIN = 19

# グローバル変数宣言
time_stamp = datetime.now().strftime("%Y%m%d%H%M%S")
videos_temporary_dir = VIDEOS_TEMPORARY_DIR + "/" + time_stamp
slide0_state = None
slide1_state = None
camera = picamera.PiCamera()
camera.resolution = CAMERA_RESOLUTION
is_first_start = True # 最初の起動か？
is_running = False  # 作動中か？
is_running_previous = False # 前回、作動中だったか？
is_restorating = False  # 復旧中か？
is_restorated = False # 復旧したか？
is_recording = False  # 録画中か？
video_temporary_index = 0
head_concat_video = 2
tail_concat_video = 2
video_temporary_index_previous = 0

print(videos_temporary_dir)

# ビデオ保存用ディレクトリの削除処理
def remove_videos_dir():
    subprocess.call('rm -rf {}'.format(videos_temporary_dir).split(" "))


# ビデオ保存用ディレクトリの作成処理
def create_videos_dir():
    subprocess.call('mkdir -p {}'.format(videos_temporary_dir).split(" "))
    subprocess.call('mkdir -p {}'.format(VIDEOS_DIR).split(" "))


def remove_head_video():
    cmd = ["rm", "{}/1.h264".format(videos_temporary_dir)]
    subprocess.call(cmd)


def is_install_mp4box():
    try:
        subprocess.check_call("MP4Box -version".split(" "))
    except:
        print("「MP4Box」をインストールしてください")
        sys.exit(1)


def get_head():
    i = video_temporary_index - BEFORE_FILE_SIZE
    if i < 2:
        print("{}秒以上前のファイルは存在しません".format(RECORDING_BEFORE))
        return 2
    else:
        return i


def get_tail():
    return video_temporary_index + AFTER_FILE_SIZE


# 次の一時ビデオファイル名を返す処理
def get_next_temporary_name():
    global video_temporary_index
    video_temporary_index += 1
    return "{}/{}.h264".format(videos_temporary_dir, video_temporary_index)


def remove_video_temporary():
    global video_temporary_index_previous

    # 新しい一時ビデオが作られたか？
    if video_temporary_index <= video_temporary_index_previous:
        return
    video_temporary_index_previous = video_temporary_index

    # 削除するファイルの添字を取得
    rm_video_index = video_temporary_index - BEFORE_FILE_SIZE - 1

    # 結合ファイルと重複していないか？
    if rm_video_index <= tail_concat_video:
        return

    # ファイルの削除実行
    cmd = ["rm", "{}/{}.h264".format(videos_temporary_dir, rm_video_index)]
    subprocess.call(cmd)


def camera_start():
    global is_recording
    if is_recording == True:
        return
    is_recording = True
    
    video_name = get_next_temporary_name()
    camera.start_recording(video_name)
    print("録画を開始しました")
    
    # 古い一時ビデオを削除
    # remove_video_temporary()


def camera_stop():
    global is_recording
    if is_recording == False:
        return
    is_recording = False

    camera.stop_recording()
    print("録画を停止しました")


# ビデオの分割
def camera_split():
    video_name = get_next_temporary_name()
    camera.split_recording(video_name)
    print("分割しました: {}".format(video_temporary_index))



# ビデオの結合処理
def video_concatenate():
    # ビデオの一時ファイル時間 ＋ 3秒待機
    sleep(RECORDING_UNIT+3)

    # ビデオ結合スクリプトの実行
    subprocess.call("python video_concatenate.py {} {} {} {}".format(
            head_concat_video,
            tail_concat_video,
            videos_temporary_dir,
            VIDEOS_DIR
        ).split(" "))


# GPIO 読み取り処理
def read_gpio_pins():
    # 再帰処理
    read_gpio_timer = threading.Timer(0.2, read_gpio_pins)
    read_gpio_timer.daemon = True
    read_gpio_timer.start()

    # GPIO 読み取り
    global slide0_state
    global slide1_state
    slide0_state = GPIO.input(SLIDE0_PIN)
    slide1_state = GPIO.input(SLIDE1_PIN)

    #############
    global is_running
    global is_restorating
    is_running = slide0_state
    is_restorating = slide1_state
    #############


# カメラ撮影処理
def camera_split_sec():
    # 再帰処理
    camera_timer = threading.Timer(RECORDING_UNIT, camera_split_sec)
    camera_timer.daemon = True
    camera_timer.start()


    if is_recording == False:
        # まだ録画が回っていないならビデオの分割をスキップする
        print("分割されませんでした。")
        return
    
    camera_split()  # ビデオの分割


def main_func():
    global is_first_start
    global is_restorated
    global is_running_previous
    global head_concat_video
    global tail_concat_video

    if is_running == True: # 作動中 〇
        if is_restorating == True: # 復旧 〇
            print("作動中　かつ　復旧中　（おかしい）")
        else:  # 復旧 ×
            if is_recording == True: # 録画 〇
                if is_restorated == True: # 復旧後 〇
                    # 作動中 〇 | 復旧 × | 録画 〇 | 復旧後 〇
                    is_restorated = False
                    tail_concat_video = get_tail()
                    print("動画の結合処理")
                    video_concatenate()
                else: # 復旧後 ×
                    # 作動中 〇 | 復旧 × | 録画 〇 | 復旧後 〇
                    remove_video_temporary()  # 古いビデオの削除
                    print("録画中")
            else: # 録画 ×
                if is_restorated == True: # 復旧後 〇
                    # 作動中 〇 | 復旧 × | 録画 × | 復旧後 〇
                    is_restorated = False
                    print("復旧したのに録画していない（おかしい）")
                else: # 復旧後 ×
                    # 作動中 〇 | 復旧 × | 録画 〇 | 復旧後 ×
                    camera_start()  # 録画開始
                    print("録画開始")
                    if is_first_start == True:
                        is_first_start = False
                        remove_head_video()
    else: # 作動中 ×
        if is_restorating == True: # 復旧 〇
            if is_recording == True: # 録画 〇
                # 作動中 × | 復旧 〇 | 録画 〇
                print("復旧完了まで待機")
            else: # 録画 ×
                # 作動中 × | 復旧 〇 | 録画 ×
                camera_start()  # 録画開始
        else:  # 復旧 ×
            if is_recording == True: # 録画 〇
                # 作動中 × | 復旧 × | 録画 〇
                if is_running_previous == True: # 停止後 〇
                    camera_stop()  # 録画停止
                    head_concat_video = get_head()
                else:
                    is_restorated = True
                    print("復旧作業が完了しました")
            else: # 録画 ×
                # 作動中 × | 復旧 × | 録画 ×
                print("作動中 × かつ 復旧 × （何もしない）")
    
    is_running_previous = is_running
    print(is_first_start)
        

    print("--------ループおわり--------")


# メイン処理
if __name__ == "__main__":
    
    # MP4Boxがインストールされているか確認
    is_install_mp4box()

    print("--------------------------")
    print("--------  起 動  ---------")
    print("--------------------------")

    # ビデオ保存用ディレクトリの作成&削除
    # remove_videos_dir()
    create_videos_dir()

    # GPIO番号指定をBCM(GPIO番号)に設定
    GPIO.setmode(GPIO.BCM)

    # SLIDE
    GPIO.setup(SLIDE0_PIN, GPIO.IN)
    GPIO.setup(SLIDE1_PIN, GPIO.IN)

    # GPIO 読み取り開始
    read_gpio_thread = threading.Thread(target=read_gpio_pins)
    read_gpio_thread.daemon = True
    read_gpio_thread.start()

    # カメラ 録画開始
    camera_thread = threading.Thread(target=camera_split_sec)
    camera_thread.daemon = True
    camera_thread.start()

    
    
    try:
        while True:
            main_func()
            sleep(0.5)
            print("作動中: {} | 復旧中: {} | head: {} | tail: {}".format(slide0_state, slide1_state, head_concat_video, tail_concat_video))
  
    except:
      pass

    finally:
        camera.close()
        GPIO.cleanup()
        remove_videos_dir()
        
