#-*- coding: utf-8 -*-

from aqt.qt import QSplashScreen, QPixmap, QTimer
from aqt import mw
from aqt.qt import QSvgRenderer

from random import random
from os import system

#from anki.sound import play as play_sound

schemas = []


class Schema(object):

    piece_per_reinf = None

    def __init__(self):
        raise NotImplementedError()

    def card_rev(self, prob):
        """Handles a card review."""
        # Returns (number of pieces of food rewarded, variance in distribution of number of pieces)
        # For intermediate mints, if there's eg 4 pieces / 9 popups, then consider a popup to be 4/9 pieces of food
        raise NotImplementedError()

    def rollback(self):
        """Goes back one step, in case of accidental reinforcement."""
        # For now, this returns nothing, doesn't affect luck calculations
        # TODO figure out how to make it work with luck estimate
        raise NotImplementedError()

    def status_output(self):
        """Gives a short summary of what's going on in the schema."""
        raise NotImplementedError()

flashPosition = (1000, 500)

def show_reinforcement(picture, sound, duration):
    system("mplayer " + sound + " >/dev/null 2>/dev/null &")
    #play_sound(sound) # this doesn't seem to work for some reason
    #svg = QSVGRenderer
    mw.splash = QSplashScreen(QPixmap(picture))
    mw.splash.move(*flashPosition)
    mw.splash.show()
    mw.splash.move(*flashPosition)
    QTimer.singleShot(duration, mw.splash.close)


# define some reinforcement messages (rm), ie tuples of (image, sound, duration) for the various degrees of reinforcement
rm0 =  (
        "/home/j/Anki2/addons21/Udarnik/media/circle.png",
        "/home/j/Anki2/addons21/Udarnik/media/ding.mp3",
        250,
        )
rm1 = (
        "/home/j/Anki2/addons21/Udarnik/media/earth.png",
        "/home/j/Anki2/addons21/Udarnik/media/ChatIncoming.wav",
        500,
        )
rm1_longer = (
        "/home/j/Anki2/addons21/Udarnik/media/earth.png",
        "/home/j/Anki2/addons21/Udarnik/media/ChatIncoming.wav",
        1000,
        )
rm2 = (
        "/home/j/Anki2/addons21/Udarnik/media/star.png",
        "/home/j/Anki2/addons21/Udarnik/media/CallResume.wav",
        750,
        )
rm2_longer = (
        "/home/j/Anki2/addons21/Udarnik/media/star.png",
        "/home/j/Anki2/addons21/Udarnik/media/CallResume.wav",
        1250,
        )
rm3 = (
        "/home/j/Anki2/addons21/Udarnik/media/unicursal_hexagram.png",
        "/home/j/Anki2/addons21/Udarnik/media/VoicemailReceived.wav",
        1100,
        )
rm4 = (
        "/home/j/Anki2/addons21/Udarnik/media/unicursal_hexagram.png",
        "/home/j/Anki2/addons21/Udarnik/media/ding.mp3", # TODO get a better file?
        1600,
        )


class _1For1(Schema):

    name = '1 for 1'
    piece_per_reinf = 1

    def __init__(self):
        pass

    def card_rev(self, prob):
        reinforcing = random() < prob
        if reinforcing:
            print(">> reinforcing! prob %s" % prob)
            show_reinforcement(*rm1)
            return (1, prob * (1 - prob))
        else:
            print(">> not reinforcing; prob %s" % prob)
            return (0, prob * (1 - prob))

    def rollback(self):
        pass

    def status_output(self):
        return "(1 for 1; no state)"
schemas.append(_1For1())


class NForN(Schema):
    """Abstract base class for schemas that give pieces in a certain regular pattern wrt reinforcements."""
    name = None
    piece_per_reinf = None
    reinf_sequence = None

    def __init__(self):
        self.idx = 0

    def card_rev(self, prob):
        prob /= self.piece_per_reinf
        reinforcing = random() < prob
        if reinforcing:
            show_reinforcement(*self.reinf_sequence[self.idx])
            self.idx += 1
            if self.idx == len(self.reinf_sequence):
                self.idx = 0
            print(">> reinforcing! prob %s, new state %s" % (prob, self.status_output()))
            return (self.piece_per_reinf, (self.piece_per_reinf ** 2) * prob * (1 - prob))
            # Remember Variance(aX) = a^2 Variance(X), henc the **2 above
        else:
            print(">> not reinforcing; prob %s, state %s" % (prob, self.status_output()))
            return (0, (self.piece_per_reinf ** 2) * prob * (1 - prob))

    def rollback(self):
        self.idx -= 1
        if self.idx == -1:
            self.idx = len(self.reinf_sequence) - 1
        print("Rolled back, new state idx %d" % self.idx)

    def status_output(self):
        return "idx %d" % self.idx

class _4For3(NForN):
    name = "4 for 3"
    piece_per_reinf = 4. / 3.
    reinf_sequence = [rm1, rm1, rm2]
schemas.append(_4For3())

class _4For9(NForN):
    name = "4 for 9"
    piece_per_reinf = 4. / 9.
    reinf_sequence = [
            rm0, rm0, rm1,
            rm0, rm0, rm1,
            rm0, rm0, rm2,
            ]
schemas.append(_4For9())

class _13For9(NForN):
    name = "13 for 9"
    piece_per_reinf = 13. / 9.
    reinf_sequence = [
            rm1, rm1, rm2,
            rm1, rm1, rm2,
            rm1, rm1, rm3,
            ]
schemas.append(_13For9())

class _4For27(NForN):
    name = "4 for 27"
    piece_per_reinf = 4. / 27.
    reinf_sequence = [
            rm0, rm0, rm0,
            rm0, rm0, rm0,
            rm0, rm0, rm1_longer,

            rm0, rm0, rm0,
            rm0, rm0, rm0,
            rm0, rm0, rm1_longer,

            rm0, rm0, rm0,
            rm0, rm0, rm0,
            rm0, rm0, rm2_longer,
            ]
schemas.append(_4For27())


class _42For27(NForN):
    name = "42 for 27"
    piece_per_reinf = 42. / 27.
    reinf_sequence = [
            rm1, rm1, rm2, # sums to 4
            rm1, rm1, rm2,
            rm1, rm1, rm3, # cumulative 13

            rm1, rm1, rm2,
            rm1, rm1, rm2,
            rm1, rm1, rm3, # cumulative 26

            rm1, rm1, rm3,
            rm1, rm1, rm3,
            rm1, rm1, rm4, # cumulative 42
            ]
schemas.append(_42For27())


class _1For9(NForN):
    name = "1 for 9"
    piece_per_reinf = 1. / 9.
    reinf_sequence = [
            rm0, rm0, rm0,
            rm0, rm0, rm0,
            rm0, rm0, rm1_longer,
            ]
schemas.append(_1For9())


class Categorical(Schema):
    """Abstract base class for schemas that given a number of pieces determined by a geometric distribution."""
    name = None
    piece_probs = None
        # list of tuples (probability, number reinforcements, rm tuple)

    def __init__(self):
        print("Initializing %s" % self.name)
        # normalize self.piece_probs
        assert self.piece_probs
        total_prob = 0.
        for prob, num, rmx in self.piece_probs:
            total_prob += prob
        for i, (prob, num, rmx) in enumerate(self.piece_probs):
            self.piece_probs[i] = (prob / total_prob, num, rmx)
        print("Normalized piece_probs: %s" % [(prob, num) for (prob, num, rmx) in self.piece_probs])

        # compute expected pieces per reinforcement
        # ie expected number of pieces given, given that there's at least 1 piece given
        self.expected_piece_per_reinf = 0.
        for prob, num, rmx in self.piece_probs:
            self.expected_piece_per_reinf += prob * num
        print("Expected pieces per reinforcement: %s" % self.expected_piece_per_reinf)

        # Compute variance, as Variance(X) = E[X^2] - E[X]^2
        # compute E[X^2] first
        #self.expectation_of_square = 0.
        #for prob, num, rmx in self.piece_probs:
        #    self.expectation_of_square += prob * (num**2)
        #self.variance = self.expectation_of_square - (self.expected_piece_per_reinf ** 2)

    def sample_piece_probs(self):
        r = random()
        for (prob, num, rmx) in self.piece_probs:
            if prob >= r:
                return (prob, num, rmx)
            r -= prob
        assert False

    def card_rev(self, prob):
        print ("adjusted probability: %s / %s = %s" % (prob, self.expected_piece_per_reinf, prob / self.expected_piece_per_reinf))
        prob /= self.expected_piece_per_reinf
        reinforcing = random() < prob

        # Compute variance
        expected_pieces = prob * self.expected_piece_per_reinf
        variance = 0.
        for prob2, num, rmx in self.piece_probs: # sum up expected squared deviations from times we do reinforce
            variance += prob2 * ((num - expected_pieces) ** 2)
        # add squared deviation from when we don't reinforce
        variance += (1 - prob) * (expected_pieces ** 2)

        if reinforcing:
            (prob, num, rmx) = self.sample_piece_probs()
            print(">> reinforcing! number %s" % num)
            show_reinforcement(*rmx)
            return (num, variance)
        else:
            print(">> not reinforcing; prob %s, state %s" % (prob, self.status_output()))
            return (0, variance)

    def rollback(self):
        pass

    def status_output(self):
        return "(categorical, no state)"

class _2For1(Categorical):
    name = "2 for 1"
    piece_probs = [(1., 2., rm2)]
schemas.append(_2For1())

class ApproximateGeometric12(Categorical):
    name = "Approximate-geometric, factor 1/2"
    piece_probs = [(8, 1, rm1), (4, 2, rm2), (2, 3, rm3), (1, 4, rm4)]
schemas.append(ApproximateGeometric12())

class ApproximateGeometric13(Categorical):
    name = "Approximate-geometric, factor 1/3"
    piece_probs = [(27, 1, rm1), (9, 2, rm2), (3, 3, rm3), (1, 4, rm4)]
schemas.append(ApproximateGeometric13())

class Uniform1234(Categorical):
    name = "Uniform 1-4"
    piece_probs = [(1, 1, rm1), (1, 2, rm2), (1, 3, rm3), (1, 4, rm4)]
schemas.append(Uniform1234())


# TODO implement more schemas
# for instance, exponential-distribution schemas
# for instance, geometric-like categorical distribution schemas
