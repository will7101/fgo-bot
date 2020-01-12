"""
An example of custom battle bot.
:author: @will7101
"""

from fgobot import BattleBot
import logging

# 指定日志的输出等级（DEBUG / INFO / WARNING / ERROR）
logging.basicConfig(level=logging.INFO)

# 实例化一个bot
bot = BattleBot(

    # 要打的关卡截图为'qp.png'，放在这个文件（my_bot.py)的相同路径的userimages目录下
    quest='userimages/qp.png',

    # 需要的助战截图为'friend_qp.png'，放在这个文件（my_bot.py)的相同路径的userimages目录下
    # 如果可以接受的助战有多个，可以传入一个list，例如：friend=['friend1.png', 'friend2.png]
    friend='userimages/friend_qp.png',

    # AP策略为：当体力耗尽时，优先吃银苹果，再吃金苹果
    # 如果不指定ap参数，则当体力耗尽时停止运行
    ap=['gold_apple', 'silver_apple'],

    # 要打的关卡有3面
    stage_count=3,

    # 关卡图像识别的阈值为0.97
    # 如果设的过低会导致进错本，太高会导致无法进本，请根据实际情况调整
    quest_threshold=0.97,

    # 助战图像识别的阈值为0.95
    # 如果设的过低会导致选择错误的助战，太高会导致选不到助战，请根据实际情况调整
    friend_threshold=0.95,

    # 如果你的分辨率不是720p，将你的屏幕宽度写在这里
    # 目前仅支持1280x720分辨率的等比例缩放，例如1920x1080
    # 1080p和720p以外的分辨率，请自行制作截图并放在fgo-bot/fgo-bot/images/xx(宽度）p目录下
    zoom_width=1080
)

# 为了方便，使用了简写
s = bot.use_skill
m = bot.use_master_skill
a = bot.attack


# 第一面的打法
@bot.at_stage(1)
def stage_1(rounds: int):
    if rounds == 1:
        # s(1, 1)表示使用1号从者的技能1
        s(2, 2)
        s(2, 3)
        # (a[6, 1, 2])表示出卡顺序为：6号卡（1号从者宝具卡），1号卡，2号卡
        a([7])
    # else部分表示如果该面(stage)打了超过一回合(round)，则怎么打，你也可以自己写elif加入第二回合、第三回合等特定打法
    else:
        a([])


# 第二面的打法
@bot.at_stage(2)
def stage_2(rounds: int):
    if rounds == 1:
        # m(2, 1)表示使用御主技能2，对象为1号从者
        m(3, 2, 4)
        s(1, 1)
        s(1, 3)
        s(3, 1)
        s(3, 3)
        a([6])
    else:
        a([])


# 第三面的打法
@bot.at_stage(3)
def stage_3(rounds: int):
    if rounds == 1:
        s(2, 2)
        a([7])
    else:
        a([])


# 程序的入口点（不加这行也可以）
# 使用时，可以直接在命令行运行'python my_bot.py'或'python3 my_bot.py'
if __name__ == '__main__':
    # 检查设备是否连接
    if not bot.device.connected():
        # 如果没有连接，则尝试通过本地端口7555连接（具体参数请参考自己的设备/模拟器）
        bot.device.connect('127.0.0.1:7555')

    # 启动bot，最多打5次
    bot.run(max_loops=5)
