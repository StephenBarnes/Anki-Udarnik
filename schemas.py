#-*- coding: utf-8 -*-

from aqt.qt import QSplashScreen, QPixmap, QTimer
from aqt import mw

from random import random
from os import system

#from anki.sound import play as play_sound

all_schemas = []


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
    mw.splash = QSplashScreen(QPixmap(picture))
    mw.splash.move(*flashPosition)
    mw.splash.show()
    mw.splash.move(*flashPosition)
    QTimer.singleShot(duration, mw.splash.close)

def show_multiple_reinforcements(*reinf_tuples):
    sounds = [tup[1] for tup in reinf_tuples]
    mplayer_commands = ["(mplayer " + sound + " >/dev/null 2>/dev/null)" for sound in sounds]
    command = "( " + " && ".join(mplayer_commands)  + " ) &"
    system(command)
    # For now, only show the first picture
    picture = reinf_tuples[0][0]
    mw.splash = QSplashScreen(QPixmap(picture))
    mw.splash.move(*flashPosition)
    mw.splash.show()
    mw.splash.move(*flashPosition)
    QTimer.singleShot(reinf_tuples[0][2], mw.splash.close)


# define some reinforcement messages (rm), ie tuples of (image, sound, duration) for the various degrees of reinforcement
def mario_ding_name(n):
    R = ".mp3"
    if n % 3:
        R = f"{n % 3}ding" + R
    if n >= 3:
        R = f"{n // 3}mario" + R
    return R
prm = [ # Piece-reinforcement tuples using mario sounds and ding sounds
    (   f"/home/j/Anki2/addons21/Udarnik/media/PNG_dice/{num}b.png",
        f"/home/j/Anki2/addons21/Udarnik/media/audio/{mario_ding_name(num)}",
        num * 250)
    for num in range(1, 9+1)
]
prm_long = [
    (a, b, c*2) for (a, b, c) in prm
]
irm = [ # Intermediate-reinforcement tuples using chip sounds
    (   f"/home/j/Anki2/addons21/Udarnik/media/PNG_dice/{num}.png",
        f"/home/j/Anki2/addons21/Udarnik/media/audio/{num}chip.mp3",
        num * 50)
    for num in range(1, 9+1)
]


class _1For1(Schema):

    name = '1 for 1'
    piece_per_reinf = 1

    def __init__(self):
        self.num_given = 0

    def card_rev(self, prob):
        reinforcing = random() < prob
        if reinforcing:
            print(">> reinforcing! %d given, prob %.4f" % (1, prob))
            self.num_given += 1
            print(self.status_output())
            show_reinforcement(*prm[0])
            return (1, prob * (1 - prob))
        else:
            print(">> not reinforcing; %d given, prob %.4f" % (0, prob))
            print(self.status_output())
            return (0, prob * (1 - prob))

    def rollback(self):
        self.num_given -= 1
        print(self.status_output())

    def reset(self):
        self.num_given = 0
        print(self.status_output())

    def status_output(self):
        return "(1 for 1; no state; %s given)" % self.num_given
all_schemas.append(_1For1())


class NForNSingles(Schema):
    """Abstract base class for schemas that give pieces in a certain regular pattern wrt reinforcements."""
    name = None
    piece_per_reinf = None
    reinf_sequence = None

    def __init__(self):
        self.idx = 0
        self.num_given = 0

    def card_rev(self, prob):
        prob /= self.piece_per_reinf
        if prob > 1:
            print("Probability would be greater than 1! Effective reinforcement rate is lower than specified")
            prob = 1
        reinforcing = random() < prob
        if reinforcing:
            if self.reinf_sequence[self.idx] is not None:
                show_reinforcement(*self.reinf_sequence[self.idx])
            self.idx += 1
            if self.idx == len(self.reinf_sequence):
                self.idx = 0
                self.num_given += 1
            print(">> reinforcing! prob %.4f, new state %s" % (prob, self.status_output()))
            return (self.piece_per_reinf, (self.piece_per_reinf ** 2) * prob * (1 - prob))
            # Remember Variance(aX) = a^2 Variance(X), henc the **2 above
        else:
            print(">> not reinforcing; prob %.4f, state %s" % (prob, self.status_output()))
            return (0, (self.piece_per_reinf ** 2) * prob * (1 - prob))

    def rollback(self):
        self.idx -= 1
        if self.idx == -1:
            self.idx = len(self.reinf_sequence) - 1
        print("Rolled back, new state idx %d" % self.idx)

    def reset(self):
        self.idx = 0
        self.num_given = 0
        print("Reset, new state idx %d" % self.idx)

    def status_output(self):
        return "idx %d; have given %d" % (self.idx, self.num_given)

class _4For3Singles(NForNSingles):
    name = "4 for 3 singles"
    piece_per_reinf = 4. / 3.
    reinf_sequence = [prm[0], prm[0], prm[1]]
all_schemas.append(_4For3Singles())

class _4For9Singles(NForNSingles):
    name = "4 for 9 singles"
    piece_per_reinf = 4. / 9.
    reinf_sequence = [
            irm[0], irm[0], prm[0],
            irm[0], irm[0], prm[0],
            irm[0], irm[0], prm[1],
            ]
all_schemas.append(_4For9Singles())

class _13For9Singles(NForNSingles):
    name = "13 for 9 singles"
    piece_per_reinf = 13. / 9.
    reinf_sequence = [
            prm[0], prm[0], prm[1],
            prm[0], prm[0], prm[1],
            prm[0], prm[0], prm[2],
            ]
all_schemas.append(_13For9Singles())

class _4For27Singles(NForNSingles):
    name = "4 for 27 singles"
    piece_per_reinf = 4. / 27.
    reinf_sequence = [
            irm[0], irm[0], irm[0],
            irm[0], irm[0], irm[0],
            irm[0], irm[0], prm_long[0],

            irm[0], irm[0], irm[0],
            irm[0], irm[0], irm[0],
            irm[0], irm[0], prm_long[0],

            irm[0], irm[0], irm[0],
            irm[0], irm[0], irm[0],
            irm[0], irm[0], prm_long[1],
            ]
all_schemas.append(_4For27Singles())


class _42For27Singles(NForNSingles):
    name = "42 for 27 singles"
    piece_per_reinf = 42. / 27.
    reinf_sequence = [
            prm[0], prm[0], prm[1], # sums to 4
            prm[0], prm[0], prm[1],
            prm[0], prm[0], prm[2], # cumulative 13

            prm[0], prm[0], prm[1],
            prm[0], prm[0], prm[1],
            prm[0], prm[0], prm[2], # cumulative 26

            prm[0], prm[0], prm[2],
            prm[0], prm[0], prm[2],
            prm[0], prm[0], prm[3], # cumulative 42
            ]
all_schemas.append(_42For27Singles())

for n in (3, 5, 8, 10, 12, 15, 20, 25, 30):
    class _1ForNSingles(NForNSingles):
        name = "1 for %d singles" % n
        piece_per_reinf = 1. / n
        reinf_sequence = [irm[0]] * (n-1) + [prm_long[0]]
    all_schemas.append(_1ForNSingles())

ordinal = lambda n: "%d%s" % (n,"tsnrhtdd"[(n//10%10!=1)*(n%10<4)*n%10::4])

for minorgroups in (2, 3, 5, 10, 15, 20, 30):
    for minorsevery in (1, 2, 3, 5, 7, 10, 15, 20):
        total = minorgroups * minorsevery
        class _1ForNMSinglesMthsMinor(NForNSingles): # useful for eg storing up 100EKcal, with 10 vapes while doing that
            name = "1 for %d singles, every %s is a minor, %d minors total" % (total, ordinal(minorsevery), minorgroups)
            piece_per_reinf = 1. / total
            reinf_sequence = ([irm[0]] * (minorsevery - 1) + [prm[0]]) * (minorgroups - 1) + [irm[0]] * (minorsevery - 1) + [prm_long[8]]
        all_schemas.append(_1ForNMSinglesMthsMinor())

class _1For60Singles10MinorSilent(NForNSingles):
    name = "1 for 60 singles, every 6th is a minor, partials silent"
    piece_per_reinf = 1. / 60
    reinf_sequence = ([None] * 5 + [prm[0]]) * 9 + ([None] * 5 + [prm_long[8]])
all_schemas.append(_1For60Singles10MinorSilent())


class SpecialVapeSturSchema10(Schema):
    """Used to reinforce with vapes and sturs (flavored water) in 1:10 ratio.
    Similar to '1 for 10 singles', except using different reinforcer tuples."""
    name = "10 vapes : 1 stur"
    piece_per_reinf = 1/3.
    modified_prm_8 = (
            prm[8][0],
            prm[8][1],
            1000)
    reinf_sequence = [irm[0], irm[0], prm[0]] * 9 + [irm[0], irm[0], modified_prm_8]

    def __init__(self):
        self.idx = 0

    def card_rev(self, prob):
        prob /= self.piece_per_reinf
        if prob > 1:
            print("Probability would be greater than 1! Effective reinforcement rate is lower than specified")
            prob = 1
        reinforcing = random() < prob
        if reinforcing:
            show_reinforcement(*self.reinf_sequence[self.idx])
            self.idx += 1
            if self.idx == len(self.reinf_sequence):
                self.idx = 0
            print(">> reinforcing! prob %.4f, new state %s" % (prob, self.status_output()))
            return (self.piece_per_reinf, (self.piece_per_reinf ** 2) * prob * (1 - prob))
            # Remember Variance(aX) = a^2 Variance(X), henc the **2 above
        else:
            print(">> not reinforcing; prob %.4f, state %s" % (prob, self.status_output()))
            return (0, (self.piece_per_reinf ** 2) * prob * (1 - prob))

    def rollback(self):
        self.idx -= 1
        if self.idx == -1:
            self.idx = len(self.reinf_sequence) - 1
        print("Rolled back, new state idx %d" % self.idx)

    def reset(self):
        self.idx = 0
        print("Reset, new state idx %d" % self.idx)

    def status_output(self):
        return "idx %d" % self.idx
all_schemas.append(SpecialVapeSturSchema10())

class SpecialVapeSturSchema15(Schema):
    """Used to reinforce with vapes and sturs (flavored water) in 1:15 ratio.
    Similar to '1 for 15 singles', except using different reinforcer tuples."""
    name = "15 vapes : 1 stur"
    piece_per_reinf = 1/3.
    modified_prm_8 = (
            prm[8][0],
            prm[8][1],
            1000)
    reinf_sequence = [irm[0], irm[0], prm[0]] * 14 + [irm[0], irm[0], modified_prm_8]

    def __init__(self):
        self.idx = 0

    def card_rev(self, prob):
        prob /= self.piece_per_reinf
        if prob > 1:
            print("Probability would be greater than 1! Effective reinforcement rate is lower than specified")
            prob = 1
        reinforcing = random() < prob
        if reinforcing:
            show_reinforcement(*self.reinf_sequence[self.idx])
            self.idx += 1
            if self.idx == len(self.reinf_sequence):
                self.idx = 0
            print(">> reinforcing! prob %.4f, new state %s" % (prob, self.status_output()))
            return (self.piece_per_reinf, (self.piece_per_reinf ** 2) * prob * (1 - prob))
            # Remember Variance(aX) = a^2 Variance(X), henc the **2 above
        else:
            print(">> not reinforcing; prob %.4f, state %s" % (prob, self.status_output()))
            return (0, (self.piece_per_reinf ** 2) * prob * (1 - prob))

    def rollback(self):
        self.idx -= 1
        if self.idx == -1:
            self.idx = len(self.reinf_sequence) - 1
        print("Rolled back, new state idx %d" % self.idx)

    def reset(self):
        self.idx = 0
        print("Reset, new state idx %d" % self.idx)

    def status_output(self):
        return "idx %d" % self.idx
all_schemas.append(SpecialVapeSturSchema15())


class CategoricalPieces(Schema):
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
        print("Expected pieces per reinforcement: %.4f" % self.expected_piece_per_reinf)

        self.num_given = 0
        self.prev_num_given = None

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
        print ("adjusted probability: %.4f / %.4f = %.4f" % (prob,
            self.expected_piece_per_reinf, prob / self.expected_piece_per_reinf))
        prob /= self.expected_piece_per_reinf
        reinforcing = random() < prob

        # Compute variance
        expected_pieces = prob * self.expected_piece_per_reinf
        variance = 0.
        for prob2, num, rmx in self.piece_probs: # sum up expected squared deviations from times we do reinforce
            variance += prob2 * ((num - expected_pieces) ** 2)
        # add squared deviation from when we don't reinforce
        variance += (1 - prob) * (expected_pieces ** 2)

        self.prev_num_given = self.num_given

        if reinforcing:
            (prob, num, rmx) = self.sample_piece_probs()
            print(">> reinforcing! number %s" % num)
            self.num_given += num
            show_reinforcement(*rmx)
            print(self.status_output())
            return (num, variance)
        else:
            print(">> not reinforcing; prob %.4f, state %s" % (prob, self.status_output()))
            print(self.status_output())
            return (0, variance)

    def rollback(self):
        if self.prev_num_given is None:
            print("Sorry, can't roll back more than once; state: %s" % self.status_output())
        else:
            self.num_given -= prev_num_given
            print("Rollback subtracts %d; state: %s" % (self.prev_num_given, self.status_output()))

    def reset(self):
        self.num_given = 0
        self.prev_num_given = None
        print("Reset; state: %s" %  self.status_output())

    def status_output(self):
        return "(categoricalPieces, num given %d, previous num given %d)" % (self.num_given, (self.prev_num_given or 0))

for n in range(2, 9+1):
    class _NFor1(CategoricalPieces):
        name = "%d for 1" % n
        piece_probs = [(1., n, prm[n-1])]
    all_schemas.append(_NFor1())

class Geometric12(CategoricalPieces):
    name = "Geometric, factor 1/2"
    piece_probs = [(2**(8 - i), i+1, prm[i]) for i in range(0, 8+1)]
all_schemas.append(Geometric12())

class Geometric13(CategoricalPieces):
    name = "Geometric, factor 1/3"
    piece_probs = [(3**(8 - i), i+1, prm[i]) for i in range(0, 8+1)]
all_schemas.append(Geometric13())

class Geometric14(CategoricalPieces):
    name = "Geometric, factor 1/4"
    piece_probs = [(4**(8 - i), i+1, prm[i]) for i in range(0, 8+1)]
all_schemas.append(Geometric14())

class Geometric23(CategoricalPieces):
    name = "Geometric, factor 2/3"
    piece_probs = [((1.5)**(8 - i), i+1, prm[i]) for i in range(0, 8+1)]
all_schemas.append(Geometric23())

class Uniform1to4(CategoricalPieces):
    name = "Uniform 1-4"
    piece_probs = [(1, i, prm[i-1]) for i in range(1, 4+1)]
all_schemas.append(Uniform1to4())

class Uniform1to9(CategoricalPieces):
    name = "Uniform 1-9"
    piece_probs = [(1, i, prm[i-1]) for i in range(1, 9+1)]
all_schemas.append(Uniform1to9())

class CategoricalPartials(Schema):
    """Abstract base class for schemas that give a number of partial pieces
    determined by a categorical distribution."""
    name = None
    partials_probs = None
        # list of tuples (probability, number of partials)
    partials_per_piece = None
        # how many partials constitutes one piece

    def __init__(self):
        print("Initializing %s" % self.name)

        self.partials_curr = 0
        self.prev_partials_given = 0
        self.num_given = 0
        self.partials_given = 0

        # normalize self.partials_probs
        assert self.partials_probs
        total_prob = 0.
        for prob, num in self.partials_probs:
            total_prob += prob
        for i, (prob, num) in enumerate(self.partials_probs):
            self.partials_probs[i] = (prob / total_prob, num)
        print("Normalized partials_probs: %s" % [(prob, num) for (prob, num) in self.partials_probs])

        # compute expected pieces per reinforcement
        # ie expected number of pieces given, given that there's at least 1 piece given
        self.expected_piece_per_reinf = 0.
        for prob, num in self.partials_probs:
            self.expected_piece_per_reinf += prob * num / self.partials_per_piece
        print("Expected pieces per reinforcement: %.4f" % self.expected_piece_per_reinf)

        # Compute variance, as Variance(X) = E[X^2] - E[X]^2
        # compute E[X^2] first
        #self.expectation_of_square = 0.
        #for prob, num in self.partials_probs:
        #    self.expectation_of_square += prob * (num**2)
        #self.variance = self.expectation_of_square - (self.expected_piece_per_reinf ** 2)

    def sample_partials_probs(self):
        r = random()
        for (prob, num) in self.partials_probs:
            if prob >= r:
                return (prob, num)
            r -= prob
        assert False

    def card_rev(self, prob):
        print ("adjusted probability: %.4f / %.4f = %.4f" % (prob,
            self.expected_piece_per_reinf, prob / self.expected_piece_per_reinf))
        prob /= self.expected_piece_per_reinf
        reinforcing = random() < prob

        # Compute variance
        expected_pieces = prob * self.expected_piece_per_reinf
        variance = 0.
        for prob2, num in self.partials_probs: # sum up expected squared deviations from times we do reinforce
            variance += prob2 * (((num / self.partials_per_piece) - expected_pieces) ** 2)
        # add squared deviation from when we don't reinforce
        variance += (1 - prob) * (expected_pieces ** 2)

        if reinforcing:
            (prob2, num) = self.sample_partials_probs()
            self.prev_partials_given = num
            self.partials_curr += num
            self.partials_given += partials_curr
            if self.partials_curr >= self.partials_per_piece:
                num_pieces = self.partials_curr // self.partials_per_piece
                self.partials_curr %= self.partials_per_piece
                print(">> piece reinforcements given! prob %.4f, %d pieces now, %d partials given, %d partials left" % (prob2, num_pieces, num, self.partials_curr))
                self.num_given += num_pieces
                print("state: %s" % self.status_output())
                show_reinforcement(*prm[num_pieces-1])
            else:
                print(">> partial reinforcements given; prob %.4f, %d partials given, %d partials in total" % (prob2, num, self.partials_curr))
                print("state: %s" % self.status_output())
                show_reinforcement(*irm[num-1])
            return (num / self.partials_per_piece, variance)
        else:
            self.prev_partials_given = 0
            print(">> not reinforcing; prob %.4f, %d partials in total" % (prob, self.partials_curr))
            return (0, variance)

    def rollback(self):
        if self.prev_partials_given is None:
            print("CategoricalPieces can't roll back more than once; state: %s" % self.status_output())
                #TODO let it roll back more than once
        else:
            self.partials_curr -= self.prev_partials_given
            self.partials_given -= self.prev_partials_given
            self.prev_partials_given = None
            print("CategoricalPieces rolled back, %d partials now; state: %s" % (self.partials_curr, self.status_output()))

    def reset(self):
        self.partials_curr = 0
        self.prev_partials_given = None
        self.num_given = 0
        self.partials_given = 0
        print("Rollback; state: %s" % self.status_output())

    def status_output(self):
        return "(categorical partials, %d partials currently, given %d full and %d partials)" % \
                (self.partials_curr, self.num_given, self.partials_given)

class Geometric2Partials9(CategoricalPartials):
    name = "2-Geometric partials, 1 for 9"
    partials_probs = [(2**(8 - i), i+1) for i in range(0, 8+1)]
    partials_per_piece = 9
all_schemas.append(Geometric2Partials9())

class Geometric2Partials3(CategoricalPartials):
    name = "2-Geometric partials, 1 for 3"
    partials_probs = [(2**(8 - i), i+1) for i in range(0, 8+1)]
    partials_per_piece = 3
all_schemas.append(Geometric2Partials3())


class CategoricalPartialsNForN(Schema):
    """Abstract base class for schemas that give a number of partial pieces
    determined by a categorical distribution, with pieces given for varying
    amounts of partials; e.g.: 9 partials for 1, then 9 partials for 1, then
    another 9 partials for 2."""
    name = None
    partials_probs = None
        # list of tuples (probability, number of partials)
    partials_per_reinf = None
        # how many partials constitutes one reinf
    reinf_sequence = None
        # sequence of pieces given when we have more than `partials_per_piece` partials

    def __init__(self):
        print("Initializing %s" % self.name)

        self.state = 0 # index of next reward in the reinf_sequence
        self.partials_curr = 0
        self.prev_partials_given = 0
        self.piece_per_reinf = sum(self.reinf_sequence) / len(self.reinf_sequence)
            # mean number of pieces given per reinf
        self.partials_per_piece = self.partials_per_reinf / self.piece_per_reinf

        # normalize self.partials_probs
        assert self.partials_probs
        total_prob = 0.
        for prob, num in self.partials_probs:
            total_prob += prob
        for i, (prob, num) in enumerate(self.partials_probs):
            self.partials_probs[i] = (prob / total_prob, num)
        print("Normalized partials_probs: %s" % [(prob, num) for (prob, num) in self.partials_probs])

        # compute expected pieces per reinforcement
        # ie expected number of pieces given, given that there's at least 1 piece given
        self.expected_piece_per_reinf = 0.
        for prob, num in self.partials_probs:
            self.expected_piece_per_reinf += prob * num / self.partials_per_piece
        print("Expected pieces per reinforcement: %.4f" % self.expected_piece_per_reinf)

        # Compute variance, as Variance(X) = E[X^2] - E[X]^2
        # compute E[X^2] first
        #self.expectation_of_square = 0.
        #for prob, num in self.partials_probs:
        #    self.expectation_of_square += prob * (num**2)
        #self.variance = self.expectation_of_square - (self.expected_piece_per_reinf ** 2)

    def sample_partials_probs(self):
        r = random()
        for (prob, num) in self.partials_probs:
            if prob >= r:
                return (prob, num)
            r -= prob
        assert False

    def card_rev(self, prob):
        print ("adjusted probability: %.4f / %.4f = %.4f" % (prob,
            self.expected_piece_per_reinf, prob / self.expected_piece_per_reinf))
        prob /= self.expected_piece_per_reinf
        reinforcing = random() < prob

        # Compute variance
        expected_pieces = prob * self.expected_piece_per_reinf
        variance = 0.
        for prob2, num in self.partials_probs: # sum up expected squared deviations from times we do reinforce
            variance += prob2 * (((num / self.partials_per_piece) - expected_pieces) ** 2)
        # add squared deviation from when we don't reinforce
        variance += (1 - prob) * (expected_pieces ** 2)

        if reinforcing:
            # Give a number of partials, as per reinf_sequence
            (prob2, num) = self.sample_partials_probs()
            self.prev_partials_given = num
            self.partials_curr += num
            # If we've gotten a reinf...
            if self.partials_curr >= self.partials_per_reinf:
                num_reinfs = self.partials_curr // self.partials_per_reinf
                self.partials_curr %= self.partials_per_reinf

                #TODO add code to make it loop around the sequence properly
                num_pieces = sum(self.reinf_sequence[self.state : self.state + num_reinfs])
                    # E.g., if reinfs are [1, 1, 2], we're state 1, we give 2 reinfs, that means we give sum(reinf_sequence[1 : 3] == [1, 2]) pieces
                self.state += num_reinfs
                if self.state >= len(self.reinf_sequence):
                    self.state %= len(self.reinf_sequence)
                print(">> reinforcements given! state %d, prob %.4f, %d pieces given, %d reinfs given, %d partials given, %d partials left" % (self.state, prob, num_pieces, num_reinfs, num, self.partials_curr))
                # Show pieces given, and also extra partials remaining after that
                if not self.partials_curr:
                    show_reinforcement(*prm[num_pieces-1])
                else:
                    show_multiple_reinforcements(prm[num_pieces - 1], irm[self.partials_curr - 1])
            else:
                print(">> partial reinforcements given; state %d, prob %.4f, %d partials given, %d partials in total" % (self.state, prob, num, self.partials_curr))
                show_reinforcement(*irm[num-1])
            return (num / self.partials_per_piece, variance)
        else:
            self.prev_partials_given = 0
            print(">> not reinforcing; state %d, prob %.4f, %d partials in total" % (self.state, prob, self.partials_curr))
            return (0, variance)

    def rollback(self):
        if self.partials_curr == 0:
            self.partials_curr = self.partials_per_reinf - 1
            if self.state == 0:
                self.state = len(self.reinf_sequence) - 1
            else:
                self.state -= 1
        else:
            self.partials_curr -= 1
        print("%s rolled back, state %d, partials %d" % (self.name, self.state, self.partials_curr))

    def reset(self):
        # TODO haven't fully implemented state-tracking and reset etc. for this schema, because I never use it
        self.state = 0
        self.partials_curr = 0
        self.prev_partials_given = 0

    def status_output(self):
        return "(categorical partials, %d partials currently, state %d)" % (self.partials_curr, self.state)

def make_geometricApartialsBforC(geom_factor, partials_per_reinf_2, reinf_sequence_2):
    class ManufacturedGeometric(CategoricalPartialsNForN):
        name = "%.2f-Geometric partials, %d pieces for %d partials" % (geom_factor, sum(reinf_sequence_2), len(reinf_sequence_2) * partials_per_reinf_2)
        partials_probs = [(geom_factor**(8 - i), i+1) for i in range(0, 8+1)]
        partials_per_reinf = partials_per_reinf_2
        reinf_sequence = reinf_sequence_2
    all_schemas.append(ManufacturedGeometric())

make_geometricApartialsBforC(2, 9, [1, 1, 2])
make_geometricApartialsBforC(2, 3, [1, 1, 2, 1, 1, 2, 1, 1, 3])
make_geometricApartialsBforC(2, 27, [1])

make_geometricApartialsBforC(1.5, 9, [1, 1, 2])
make_geometricApartialsBforC(1.5, 3, [1, 1, 2, 1, 1, 2, 1, 1, 3])
make_geometricApartialsBforC(1.5, 27, [1])

make_geometricApartialsBforC(3, 9, [1, 1, 2])
make_geometricApartialsBforC(3, 3, [1, 1, 2, 1, 1, 2, 1, 1, 3])
make_geometricApartialsBforC(3, 27, [1])

make_geometricApartialsBforC(4, 9, [1, 1, 2])
make_geometricApartialsBforC(4, 3, [1, 1, 2, 1, 1, 2, 1, 1, 3])
make_geometricApartialsBforC(4, 27, [1])



#TODO refactor code above
# TODO implement more schemas
