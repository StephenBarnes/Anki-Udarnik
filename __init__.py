#-*- coding: utf-8 -*-

"""
Anki add-on: Udarnik

System for operant conditioning of anki use, by providing
food at a rate determined by card difficulty and the calorie
content of the food. See blog post: [Forthcoming.]
"""

### Main module ###


import aqt
from aqt.qt import *
from aqt import mw

from anki.hooks import wrap, addHook

from .config import *

import re
import math

def normal_cdf(x):
    "Cdf for standard normal; don't want to import all of scipy just for this."
    q = math.erf(x / math.sqrt(2.0))
    return (1.0 + q) / 2.0


# To load global config once the profile is loaded
config = None
def load_config_to_global():
    global config
    config = load_config()
addHook("profileLoaded", load_config_to_global)


# Initialize globals to track luck
ekcal_given = 0
expected_ekcal_given = 0
variance_ekcal_given = 0


# Function to probabilistically reinforce card ratings
def reinforce_card_rating(self, ease):

    # Find deck multiplier
    card = self.card
    deckName = self.mw.col.decks.name(card.did)
    multiplier_if_any = re.findall(r".*\{([0-9.]+)\}.*$", deckName)
    assert len(multiplier_if_any) in (0, 1)
    if not multiplier_if_any:
        deck_multiplier = 1.
    else:
        deck_multiplier = float(multiplier_if_any[0])

    # Compute actual ease it was passed with
    cnt = self.mw.col.sched.answerButtons(self.card)
        # this is the number of answer buttons, either 2 or 3 or 4
    if cnt == 2:
        ease = ["fail", "normal"][ease-1]
    elif cnt == 3:
        ease = ["fail", "normal", "easy"][ease-1]
    else: # cnt == 4
        ease = ["fail", "difficult", "normal", "easy"][ease-1]

    # Compute ease multiplier
    ease_multiplier = None
    if ease == "easy":
        ease_multiplier = config['easy multiplier']
    elif ease == "normal":
        ease_multiplier = 1.
    elif ease == "difficult":
        ease_multiplier = config['difficult multiplier']
    elif ease == "fail":
        ease_multiplier = config['fail multiplier']
    else:
        raise Exception()

    # Tell the schema to reinforce, using this probability
    schema = schemas[config['schema']]
    piece_probability = config['piece_prob'] * deck_multiplier * ease_multiplier
    #print("> piece_probability %s" % piece_probability)
    #print("> config's piece_prob %s" % config['piece_prob'])
    #print("> deck multiplier %s" % deck_multiplier)
    #print("> ease multiplier %s" % ease_multiplier)
    ekcal_per_piece = config['ekcal_per_piece']
    pieces_given_now, pieces_variance_now = schema.card_rev(piece_probability)
    ekcal_given_now = pieces_given_now * ekcal_per_piece
    expected_ekcal_given_now = piece_probability * ekcal_per_piece
    ekcal_variance_now = (ekcal_per_piece ** 2) * pieces_variance_now

    # Update and report luck
    global ekcal_given, expected_ekcal_given, variance_ekcal_given
    ekcal_given += ekcal_given_now
    expected_ekcal_given += piece_probability * ekcal_per_piece
    variance_ekcal_given += ekcal_variance_now
    print("This rev: %.2f ekcal, %.2f expectation, %.2f variance" \
            % (ekcal_given_now, expected_ekcal_given_now, ekcal_variance_now))
    print("In total: %.2f ekcal, %.2f expectation, %.2f variance" \
            % (ekcal_given, expected_ekcal_given, variance_ekcal_given))
    z = (ekcal_given - expected_ekcal_given) / (variance_ekcal_given ** .5)
    print("Standard score: %.2f sigma" % z)
    percentile = normal_cdf(z)
    # Assumes that true distribution is normal, which will become true as we review more cards, by central limit theorem
    print("Luck: %d%%" % (percentile * 100))
    print("")


    # TODO system to compute expected reinforcements, and actual, and luck this session
    #global expected_reinforcements
    #expected_reinforcements += reinforceProbability
    #print("Expected number of reinforcements: %.1f" % expected_reinforcements)


def on_rollback():
    schema = schemas[config['schema']]
    schema.rollback()


### Hooks and wraps ###

# Wrap answer-card function with reinforce_card_rating
reviewer.Reviewer._answerCard = wrap(
        reviewer.Reviewer._answerCard, reinforce_card_rating, "before")

# Add options dialog
options_action = QAction("&Udarnik Options...", mw)
options_action.setShortcut(QKeySequence("Ctrl+U"))
options_action.triggered.connect(lambda _, o=mw: on_udarnik_options(o, config))
    # note that this modifies both our `config` and the one stored in the mw.col.conf['udarnik']
mw.form.menuTools.addAction(options_action)

# Add rollback button
rollback_action = QAction("&Udarnik rollback", mw)
rollback_action.setShortcut(QKeySequence("Ctrl+Shift+U"))
rollback_action.triggered.connect(lambda _, o=mw: on_rollback())
    # note that this modifies both our `config` and the one stored in the mw.col.conf['udarnik']
mw.form.menuTools.addAction(rollback_action)
