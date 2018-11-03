"""
Game auto-playing bot.
"""

import logging
from functools import partial
from typing import Dict, Any, Callable
from .tm import TM
from .device import Device
import json
from pathlib import Path
from time import sleep
from typing import Tuple, List, Union
from random import randint

logger = logging.getLogger('bot')

INTERVAL_SHORT = 1
INTERVAL_MID = 2
INTERVAL_LONG = 10


class BattleBot:
    """
    A class of the bot that automatically play battles.
    """

    def __init__(self,
                 quest: str = 'quest.png',
                 friend: Union[str, List[str]] = 'friend.png',
                 ap: List[str] = None,
                 quest_threshold: float = 0.97,
                 friend_threshold: float = 0.97
                 ):
        """

        :param quest: path to image of the quest to play
        :param friend: path to image(s) of the preferred friend servant
        :param ap: the preferred AP regeneration item.
                   Options are 'silver_apple', 'gold_apple', 'quartz'.
                   i.e. ['silver_apple', 'gold_apple'] means: to use silver apple first
                   and to use gold apple if silver ones run out.
                   If not given, the bot will stop when AP runs out.
        :param quest_threshold: threshold of quest matching
        :param friend_threshold: threshold of friend matching
        """

        # A dict of the handler functions that are called repeatedly at each stage.
        # Use `at_stage` to register functions.
        self.stage_handlers = {}

        # A dict of configurations.
        self.config = {}

        self.stage_count = 3
        logger.info('Stage count set to {}.'.format(self.stage_count))

        # Device
        self.device = Device()

        # Template matcher
        self.tm = TM(feed=partial(self.device.capture, method=Device.FROM_SHELL))

        # Target quest
        path = Path(quest).absolute()
        self.tm.load_image(path, name='quest')

        if isinstance(friend, str):
            friend = [friend]

        # Count of expected friend servants
        self.friend_count = len(friend)
        logger.info('Friend count is {}.'.format(self.friend_count))

        for fid in range(self.friend_count):
            path = Path(friend[fid]).absolute()
            self.tm.load_image(path, name='f_{}'.format(fid))

        # AP strategy
        self.ap = ap
        logger.info('AP strategy is {}.'.format(self.ap))

        self.quest_threshold = quest_threshold
        self.friend_threshold = friend_threshold

        # Load button coords from config
        btn_path = Path(__file__).absolute().parent / 'config' / 'buttons.json'
        with open(btn_path) as f:
            self.buttons = json.load(f)

        logger.debug('Bot initialized.')

    def __add_stage_handler(self, stage: int, f: Callable):
        """
        Register a handler function to a given stage of the battle.

        :param stage: the stage number
        :param f: the handler function
        """
        assert not self.stage_handlers.get(stage), 'Cannot register multiple function to a single stage.'
        logger.debug('Function {} registered to stage {}'.format(f.__name__, stage))
        self.stage_handlers[stage] = f

    def __button(self, btn):
        """
        Return the __button coords and size.

        :param btn: the name of __button
        :return: (x, y, w, h)
        """
        btn = self.buttons[btn]
        return btn['x'], btn['y'], btn['w'], btn['h']

    def __swipe(self, track):
        """
        Swipe in given track.

        :param track:
        :return:
        """
        x1, y1, x2, y2 = map(lambda x: x + randint(-5, 5), self.buttons['swipe'][track])
        self.device.swipe((x1, y1), (x2, y2))

    def __find_and_tap(self, im: str, threshold: float = None) -> bool:
        """
        Find the given image on screen and tap.

        :param im: the name of image
        :param threshold: the matching threshold
        :return: whether successful
        """
        x, y = self.tm.find(im, threshold=threshold)
        if (x, y) == (-1, -1):
            logger.warning('Failed to find image {} on screen.'.format(im))
            return False
        w, h = self.tm.getsize(im)
        return self.device.tap_rand(x, y, w, h)

    def __exists(self, im: str, threshold: float = None) -> bool:
        """
        Check if a given image exists on screen.

        :param im: the name of the image
        :param threshold: threshold of matching
        """
        return self.tm.exists(im, threshold=threshold)

    def __wait(self, sec):
        """
        Wait some seconds and update the screen feed.

        :param sec: the seconds to wait
        """
        logger.debug('Sleep {} seconds.'.format(sec))
        sleep(sec)
        self.tm.update_screen()

    def __wait_until(self, im: str):
        """
        Wait until the given image appears. Useful when try to use skills, etc.
        """
        logger.debug("Wait until image '{}' appears.".format(im))
        self.tm.update_screen()
        while not self.__exists(im):
            self.__wait(INTERVAL_MID)

    def __get_current_stage(self) -> int:
        """
        Get the current stage in battle.

        :return: current stage. Return -1 if error occurs.
        """
        self.__wait_until('attack')
        max_prob, max_stage = 0.8, -1
        for stage in range(1, self.stage_count + 1):
            im = '{}_{}'.format(stage, self.stage_count)
            prob = self.tm.probability(im)
            if prob > max_prob:
                max_prob, max_stage = prob, stage

        if max_stage == -1:
            logger.error('Failed to get current stage.')
        else:
            logger.debug('Got current stage: {}'.format(max_stage))

        return max_stage

    def __find_friend(self) -> str:
        self.__wait_until('refresh_friends')
        for _ in range(6):
            for fid in range(self.friend_count):
                im = 'f_{}'.format(fid)
                if self.__exists(im, threshold=self.friend_threshold):
                    return im
            self.__swipe('friend')
            self.__wait(INTERVAL_SHORT)
        return ''

    def __enter_battle(self) -> bool:
        """
        Enter the battle.

        :return: whether successful.
        """
        self.__wait_until('menu')
        while not self.__find_and_tap('quest', threshold=self.quest_threshold):
            self.__swipe('quest')
            self.__wait(INTERVAL_SHORT)
        self.__wait(INTERVAL_MID)

        # no enough AP
        if self.__exists('ap_regen'):
            if not self.ap:
                return False
            else:
                ok = False
                for ap_item in self.ap:
                    if self.__find_and_tap(ap_item):
                        self.__wait(1)
                        if self.__find_and_tap('decide'):
                            self.__wait_until('refresh_friends')
                            ok = True
                            break
                if not ok:
                    return False

        # look for friend servant
        friend = self.__find_friend()
        while not friend:
            self.__find_and_tap('refresh_friends')
            self.__wait(INTERVAL_SHORT)
            self.__find_and_tap('yes')
            self.__wait(INTERVAL_LONG)
            friend = self.__find_friend()
        self.__find_and_tap(friend)
        self.__wait(INTERVAL_SHORT)
        self.__wait_until('start_quest')
        self.__find_and_tap('start_quest')
        self.__wait(INTERVAL_SHORT)
        self.__wait_until('attack')
        return True

    def __play_battle(self) -> int:
        """
        Play the battle.

        :return: count of rounds.
        """
        rounds = 0
        while True:
            stage = self.__get_current_stage()
            if stage == -1:
                logger.error("Failed to get current stage. Leaving battle...")
                return rounds

            rounds += 1
            logger.info('At stage {}/{}, round {}, calling handler function...'
                        .format(stage, rounds, self.stage_count))
            self.stage_handlers[stage]()

            while True:
                self.__wait(INTERVAL_MID)
                if self.__exists('bond') or self.__exists('bond_up'):
                    logger.info("'与从者的羁绊' detected. Leaving battle...")
                    return rounds
                elif self.__exists('attack'):
                    logger.info("'Attack' detected. Continuing loop...")
                    break

    def __end_battle(self):
        # self.__find_and_tap('bond')
        # self.__wait(INTERVAL_SHORT)
        # self.__wait_until('gain_exp')
        # self.__find_and_tap('gain_exp')
        # self.__wait(INTERVAL_SHORT)
        self.__wait(INTERVAL_MID)
        while not self.__exists('next_step'):
            self.device.tap_rand(640, 360, 50, 50)
            self.__wait(INTERVAL_MID)

        self.__find_and_tap('next_step')
        self.__wait(INTERVAL_MID)

        # quest first-complete reward
        if self.__exists('please_tap'):
            self.__find_and_tap('please_tap')
            self.__wait(INTERVAL_SHORT)

        # not send friend application
        if self.__exists('not_apply'):
            self.__find_and_tap('not_apply')

        self.__wait_until('menu')

    def at_stage(self, stage: int):
        """
        A decorator that is used to register a handler function to a given stage of the battle.

        :param stage: the stage number
        """

        def decorator(f):
            self.__add_stage_handler(stage, f)
            return f

        return decorator

    def use_skill(self, servant: int, skill: int, obj=None):
        """
        Use a skill.

        :param servant: the servant id.
        :param skill: the skill id.
        :param obj: the object of skill, if required.
        """
        self.__wait_until('attack')

        x, y, w, h = self.__button('skill')
        x += self.buttons['servant_distance'] * (servant - 1)
        x += self.buttons['skill_distance'] * (skill - 1)
        self.device.tap_rand(x, y, w, h)
        logger.debug('Used skill ({}, {})'.format(servant, skill))
        self.__wait(INTERVAL_SHORT)

        if self.__exists('choose_object'):
            if obj is None:
                logger.error('Must choose a skill object.')
            else:
                x, y, w, h = self.__button('choose_object')
                x += self.buttons['choose_object_distance'] * (obj - 1)
                self.device.tap_rand(x, y, w, h)
                logger.debug('Chose skill object {}.'.format(obj))

        self.__wait(INTERVAL_SHORT * 2)

    def use_master_skill(self, skill: int, obj=None, obj2=None):
        """
        Use a master skill.
        Param `obj` is needed if the skill requires a object.
        Param `obj2` is needed if the skill requires another object (Order Change).

        :param skill: the skill id.
        :param obj: the object of skill, if required.
        :param obj2: the second object of skill, if required.
        """
        self.__wait_until('attack')

        x, y, w, h = self.__button('master_skill_menu')
        self.device.tap_rand(x, y, w, h)
        self.__wait(INTERVAL_SHORT)

        x, y, w, h = self.__button('master_skill')
        x += self.buttons['master_skill_distance'] * (skill - 1)
        self.device.tap_rand(x, y, w, h)
        logger.debug('Used master skill {}'.format(skill))
        self.__wait(INTERVAL_SHORT)

        if self.__exists('choose_object'):
            if obj is None:
                logger.error('Must choose a master skill object.')
            elif 1 <= obj <= 3:
                x, y, w, h = self.__button('choose_object')
                x += self.buttons['choose_object_distance'] * (obj - 1)
                self.device.tap_rand(x, y, w, h)
                logger.debug('Chose master skill object {}.'.format(obj))
            else:
                logger.error('Invalid master skill object.')
        elif self.__exists('change_disabled'):
            if obj is None or obj2 is None:
                logger.error('Must choose two objects for Order Change.')
            elif 1 <= obj <= 3 and 4 <= obj2 <= 6:
                x, y, w, h = self.__button('change')
                x += self.buttons['change_distance'] * (obj - 1)
                self.device.tap_rand(x, y, w, h)

                x += self.buttons['change_distance'] * (obj2 - obj)
                self.device.tap_rand(x, y, w, h)
                logger.debug('Chose master skill object ({}, {}).'.format(obj, obj2))

                self.__wait(INTERVAL_SHORT)
                self.__find_and_tap('change')
                logger.debug('Order Change')
            else:
                logger.error('Invalid master skill object.')

        self.__wait(INTERVAL_SHORT)

    def attack(self, cards: list):
        """
        Tap attack __button and choose three cards.

        1 ~ 5 stands for normal cards, 6 ~ 8 stands for noble phantasm cards.

        :param cards: the cards id, as a list

        """
        assert len(cards) == 3, 'Number of cards must be 3.'
        assert len(set(cards)) == 3, 'Cards must be distinct.'
        self.__wait_until('attack')

        self.__find_and_tap('attack')
        self.__wait(INTERVAL_SHORT * 2)
        for card in cards:
            if 1 <= card <= 5:
                x, y, w, h = self.__button('card')
                x += self.buttons['card_distance'] * (card - 1)
                self.device.tap_rand(x, y, w, h)
            elif 6 <= card <= 8:
                x, y, w, h = self.__button('noble_card')
                x += self.buttons['card_distance'] * (card - 6)
                self.device.tap_rand(x, y, w, h)
            else:
                logger.error('Card number must be in range [1, 8]')

    def run(self, max_loops: int = 10):
        """
        Start the bot.

        :param max_loops: the max number of loops.
        """
        count = 0
        for n_loop in range(max_loops):
            logger.info('Entering battle...')
            if not self.__enter_battle():
                logger.info('AP runs out. Quiting...')
                break
            rounds = self.__play_battle()
            self.__end_battle()
            count += 1
            logger.info('{}-th Battle complete. {} rounds played.'.format(count, rounds))

        logger.info('{} Battles played in total. Good bye!'.format(count))
