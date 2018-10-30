"""
Template matching.
"""

from typing import Callable, Union, Tuple
from pathlib import Path
import cv2 as cv
import numpy as np
import logging
from matplotlib import pyplot as plt

logger = logging.getLogger('tm')

# the template matching method
TM_METHOD = cv.TM_CCOEFF_NORMED


class TM:
    def __init__(self, feed: Callable, threshold: float = 0.85):
        """

        :param feed: the screencap feed function
        :param threshold: the default threshold of matching.
        """

        self.feed = feed

        self.threshold = threshold

        # template image set
        self.images = {}
        self.load_images()

        # the screencap image. Needs to be updated before matching.
        self.screen = None

    def load_images(self):
        """
        Load template images from directory.
        """
        im_dir = Path(__file__).absolute().parent / 'images'
        for im in im_dir.glob('*.png'):
            name = im.name[:-4]
            self.images[name] = cv.imread(str(im), cv.IMREAD_COLOR)
            # self.images[name] = cv.cvtColor(self.images[name], cv.COLOR_BGR2RGB)
            # plt.figure(name)
            # plt.imshow(self.images[name])
            # plt.show()
            logger.debug('Loaded image {}'.format(name))

        logger.info('Images loaded successfully.')

    def getsize(self, im: str) -> Tuple[int, int]:
        """
        Return the size of given image.

        :param im: the name of image
        :return: the size in (width, height)
        """
        h, w, _ = self.images[im].shape
        return w, h

    def update_screen(self):
        """
        Update the screencap image from feed.
        """
        self.screen = self.feed()
        logger.debug('Screen updated.')

    def probability(self, im: str) -> float:
        """
        Return the probability of the existence of given image.

        :param im: the name of the image.
        :return: the probability (confidence).
        """
        assert self.screen is not None
        try:
            template = self.images[im]
        except KeyError:
            logger.error('Unexpected image name {}'.format(im))
            return 0.0

        res = cv.matchTemplate(self.screen, template, TM_METHOD)
        _, max_val, _, max_loc = cv.minMaxLoc(res)
        logger.debug('max_val = {}, max_loc = {}'.format(max_val, max_loc))
        return max_val

    def find(self, im: str, threshold: float = None) -> Tuple[int, int]:
        """
        Find the template image on screen and return its top-left coords.

        Return None if the matching value is less than `threshold`.

        :param im: the name of the image
        :param threshold: the threshold of matching. If not given, will be set to the default threshold.
        :return: the top-left coords of the result. Return (-1, -1) if not found.
        """
        threshold = threshold or self.threshold

        assert self.screen is not None
        try:
            template = self.images[im]
        except KeyError:
            logger.error('Unexpected image name {}'.format(im))
            return -1, -1

        res = cv.matchTemplate(self.screen, template, TM_METHOD)
        _, max_val, _, max_loc = cv.minMaxLoc(res)
        logger.debug('max_val = {}, max_loc = {}'.format(max_val, max_loc))
        return max_loc if max_val >= threshold else (-1, -1)

    def exists(self, im: str, threshold: float = None) -> bool:
        """
        Check if a given image exists on screen.

        :param im: the name of the image
        :param threshold: the threshold of matching. If not given, will be set to the default threshold.
        """
        return self.probability(im) >= threshold
