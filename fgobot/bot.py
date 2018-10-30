import logging
from functools import partial
from typing import Dict, Any, Callable
from .tm import TM
from .device import Device
import json
from pathlib import Path
from time import sleep

logger = logging.getLogger('bot')


class BattleBot:
    """
    A class of the bot that automatically play battles.
    """

    def __init__(self):
        # A dict of the handler functions that are called repeatedly at each stage.
        # Use `at_stage` to register functions.
        self.stage_handlers = {}

        # A dict of configurations.
        self.config = {}

        self.stage_count = 3

        # Device
        self.device = Device()

        # Template matcher
        self.tm = TM(feed=partial(self.device.capture, method=Device.FROM_SHELL))

        # Load button coords from config
        config_path = Path(__file__).absolute().parent / 'config' / 'buttons.json'
        with open(config_path) as f:
            self.buttons = json.load(f)
        print(self.buttons)

        logger.debug('Bot initialized.')

    def add_stage_handler(self, stage: int, f: Callable):
        """
        Register a handler function to a given stage of the battle.

        :param stage: the stage number
        :param f: the handler function
        """
        assert not self.stage_handlers.get(stage), 'Cannot register multiple function to a single stage.'
        logger.debug('Function {} registered to stage {}'.format(f.__name__, stage))
        self.stage_handlers[stage] = f

    def at_stage(self, stage: int):
        """
        A decorator that is used to register a handler function to a given stage of the battle.

        :param stage: the stage number
        """

        def decorator(f):
            self.add_stage_handler(stage, f)
            return f

        return decorator

    def button(self, btn):
        """
        Return the button coords and size.

        :param btn: the name of button
        :return: (x, y, w, h)
        """
        btn = self.buttons[btn]
        return btn['x'], btn['y'], btn['w'], btn['h']

    def find_and_tap(self, im: str) -> bool:
        """
        Find the given image on screen and tap.

        :param im: the name of image
        :return: whether successful
        """
        x, y = self.tm.find(im)
        if (x, y) == (-1, -1):
            logger.error('Failed to find image {} on screen.'.format(im))
        w, h = self.tm.getsize(im)
        return self.device.tap_rand(x, y, w, h)

    def exists(self, im: str) -> bool:
        """
        Check if a given image exists on screen.

        :param im: the name of the image
        """
        return self.tm.exists(im)

    def wait(self, sec):
        """
        Wait some seconds and update the screen feed.

        :param sec: the seconds to wait
        """
        sleep(sec)
        self.tm.update_screen()

    def wait_until(self, im: str):
        """
        Wait until the given image appears. Useful when try to use skills, etc.
        """
        self.tm.update_screen()
        while not self.exists(im):
            self.wait(3)

    def use_skill(self, servant: int, skill: int, obj=None):
        """
        Use a skill.

        :param servant: the servant id.
        :param skill: the skill id.
        :param obj: the object of skill, if required.
        """
        self.wait_until('attack')

        x, y, w, h = self.button('skill')
        x += self.buttons['servant_distance'] * (servant - 1)
        x += self.buttons['skill_distance'] * (skill - 1)
        self.device.tap_rand(x, y, w, h)
        logger.debug('Used skill ({}, {})'.format(servant, skill))
        self.wait(3)

        if self.exists('choose_object'):
            if obj is None:
                logger.error('Must choose a skill object.')
            else:
                x, y, w, h = self.button('choose_object')
                x += self.buttons['choose_object_distance'] * (obj - 1)
                self.device.tap_rand(x, y, w, h)
                logger.debug('Chose skill object {}.'.format(obj))

    def use_master_skill(self, skill: int, obj=None):
        """
        Use a master skill.

        :param skill: the skill id.
        :param obj: the object of skill, if required.
        """
        self.wait_until('attack')

        x, y, w, h = self.button('master_skill_menu')
        self.device.tap_rand(x, y, w, h)
        self.wait(2)

        x, y, w, h = self.button('master_skill')
        x += self.buttons['master_skill_distance'] * (skill - 1)
        self.device.tap_rand(x, y, w, h)
        logger.debug('Used master skill {}'.format(skill))
        self.wait(2)

        if self.exists('choose_object'):
            if obj is None:
                logger.error('Must choose a master skill object.')
            else:
                x, y, w, h = self.button('choose_object')
                x += self.buttons['choose_object_distance'] * (obj - 1)
                self.device.tap_rand(x, y, w, h)
                logger.debug('Chose master skill object {}.'.format(obj))

    def attack(self, cards: list):
        """
        Tap attack button and choose three cards.

        1 ~ 5 stands for normal cards, 6 ~ 8 stands for noble phantasm cards.

        :param cards: the cards id, as a list

        """
        assert len(cards) == 3, 'Number of cards must be 3.'
        assert len(set(cards)) == 3, 'Cards must be distinct.'
        self.wait_until('attack')

        self.find_and_tap('attack')
        self.wait(3)
        for card in cards:
            if 1 <= card <= 5:
                x, y, w, h = self.button('card')
                x += self.buttons['card_distance'] * (card - 1)
                self.device.tap_rand(x, y, w, h)
            elif 6 <= card <= 8:
                x, y, w, h = self.button('noble_card')
                x += self.buttons['card_distance'] * (card - 6)
                self.device.tap_rand(x, y, w, h)
            else:
                logger.error('Card number must be in range [1, 8]')

    def get_current_stage(self) -> int:
        """
        Get the current stage in battle.

        :return: current stage. Return -1 if error occurs.
        """
        self.wait_until('attack')
        max_prob, max_stage = 0.8, -1
        for stage in (1, self.stage_count + 1):
            im = '{}_{}'.format(stage, self.stage_count)
            prob = self.tm.probability(im)
            if prob > max_prob:
                max_prob, max_stage = prob, stage

        if max_stage == -1:
            logger.error('Failed to get current stage.')
        else:
            logger.debug('Got current stage: {}'.format(max_stage))

        return stage

    def enter_battle(self):
        self.wait_until('menu')
        self.find_and_tap('default_battle')
        self.wait_until('refresh_friends')
        self.find_and_tap('friend_caster')
        self.wait(1)
        self.find_and_tap('km_petal')
        self.wait_until('start_quest')
        self.find_and_tap('start_quest')
        self.wait_until('attack')

    def play_battle(self) -> int:
        """
        Play the battle.

        :return: count of rounds.
        """
        rounds = 0
        while True:
            stage = self.get_current_stage()
            if stage == -1:
                logger.error("Failed to get current stage. Leaving battle...")
                return rounds

            rounds += 1
            logger.info('At stage {}/{}, round {}, calling handler function...'
                        .format(stage, rounds, self.stage_count))
            self.stage_handlers[stage]()

            while True:
                self.wait(5)
                if self.exists('bond'):
                    logger.info("'与从者的羁绊' detected. Leaving battle...")
                    return rounds
                elif self.exists('attack'):
                    logger.info("'Attack' detected. Continuing loop...")
                    break

    def end_battle(self):
        self.find_and_tap('bond')
        self.wait_until('gain_exp')
        self.find_and_tap('gain_exp')
        self.wait_until('next_step')
        self.find_and_tap('next_step')
        self.wait(5)
        if self.exists('please_tap'):
            self.find_and_tap('please_tap')
        self.wait_until('menu')

    def run(self, max_loops: int = 10):
        """
        Start the bot.

        :param max_loops: the max number of loops.
        """
        for n_loop in range(max_loops):
            logger.info('Entering battle...')
            self.enter_battle()
            rounds = self.play_battle()
            logger.info('Battle complete. {} rounds played.'.format(rounds))
            self.end_battle()

        logger.info('{} Battles played. Good bye!'.format(max_loops))
