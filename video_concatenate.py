# coding: utf-8
#
# 起動方法
# python video_concatenate [head, tail, in_dir, out_dir]
# 
# head: 結合始め
# tail: 結合終わり
# in_dir: 結合ファイルのパス
# out_dir: 結合したファイルの出力先
#
import subprocess
from sys import argv, exit
from datetime import datetime


def remove_files(head, tail, in_dir, out_dir):
    args = ["rm"]
    for i in range(head, tail+1):
        args.append("{}/{}.h264".format(in_dir, i))
    # 削除実行
    subprocess.call(args)


def concat(head, tail, in_dir, out_dir):

    print("動画を結合しています......")
    date_time = datetime.now().strftime("%Y%m%d%H%M%S")
    out_file_name = "{}/video-{}.mp4".format(out_dir, date_time)

    args = ["MP4Box", "-add", "{}/{}.h264".format(in_dir, head)]
    for i in range(head+1, tail+1):
        args.append("-cat")
        args.append("{}/{}.h264".format(in_dir, i))
    args.append("-new")
    args.append(out_file_name)
    subprocess.call(args)
    # print(args)

    # 結合し終えたファイルの削除
    remove_files(head, tail, in_dir, out_dir)

    print("-------- 結合が完了しました --------")
    



if __name__ == "__main__":

    if len(argv) == 5:
        head = int(argv[1])
        tail = int(argv[2])
        in_dir = argv[3]
        out_dir = argv[4]
    else:
        print("引数が違います。")
        exit(1)

    concat(head, tail, in_dir, out_dir)
