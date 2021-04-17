"""
An example of custom battle bot.
:author: @will7101
"""

from fgobot import BattleBot
import logging

# 指定日志的输出等级（DEBUG / INFO / WARNING / ERROR）
logging.basicConfig(level=logging.DEBUG)

# 实例化一个bot
bot = BattleBot(

    # 要打的关卡截图为'qp.png'，放在这个文件的同一级目录下
    quest='free.png',

    # 需要的助战截图为'friend_qp.png'，放在这个文件的同一级目录下
    # 如果可以接受的助战有多个，可以传入一个list，例如：friend=['friend1.png', 'friend2.png]
    friend='friend_sikaha2.png',

    # AP策略为：当体力耗尽时，优先吃银苹果，再吃金苹果
    # 如果不指定ap参数，则当体力耗尽时停止运行
    ap=['silver_apple'],

    # 要打的关卡有3面
    stage_count=3,

    # 关卡图像识别的阈值为0.97
    # 如果设的过低会导致进错本，太高会导致无法进本，请根据实际情况调整
    quest_threshold=0.97,

    # 助战图像识别的阈值为0.95
    # 如果设的过低会导致选择错误的助战，太高会导致选不到助战，请根据实际情况调整
    friend_threshold=0.95
)

# 为了方便，使用了简写
s = bot.use_skill
m = bot.use_master_skill
a = bot.attack

"""
1. 斯卡哈
2. 女武神
3. 斯卡哈
"""


# 第一面的打法
@bot.at_stage(1)
def stage_1():
    # s(1, 1)表示使用1号从者的技能1
    s(1, 1, obj=2)  # 斯卡哈绿魔放
    s(3, 1, obj=2)  # 斯卡哈绿魔放
    s(2, 1)  # 女武神绿魔放
    s(2, 3)  # 女武神缓充能
    # m(2, 1)表示使用御主技能2，对象为1号从者
    m(2, 2)  # 冲能服
    # (a[6, 1, 2])表示出卡顺序为：6号卡（1号从者宝具卡），1号卡，2号卡
    a([7, 1, 2])  # 女武神宝具卡


# 第二面的打法
@bot.at_stage(2)
def stage_2():
    s(1, 3, obj=2)  # 斯卡哈充能
    a([7, 1, 2])  # 女武神宝具卡


# 第三面的打法
@bot.at_stage(3)
def stage_3():
    s(1, 2)  # 斯卡哈减防
    s(3, 2)  # 斯卡哈减防
    s(3, 3, obj=2)  # 斯卡哈充能
    a([7, 1, 2])  # 女武神宝具卡


# 程序的入口点（不加这行也可以）
# 使用时，可以直接在命令行运行'python my_bot.py'
if __name__ == '__main__':
    # 检查设备是否连接
    if not bot.device.connected():
        # 如果没有连接，则尝试通过本地端口62001连接（具体参数请参考自己的设备/模拟器）
        bot.device.connect('127.0.0.1:59865')

    # 启动bot，最多打5次
    bot.run(max_loops=100)
