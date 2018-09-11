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

import datetime

def normal_cdf(x):
    "Cdf for standard normal; don't want to import all of scipy just for this."
    q = math.erf(x / math.sqrt(2.0))
    return (1.0 + q) / 2.0


# using only synced conf, not local preferences
default_store = {
    "schema": 0,
    "version": 0.3,
    "effective calories per review": 0.8,
    "protein free calories": 5.,
    "difficult multiplier": .75,
    "easy multiplier": 1.3,
    "fail multiplier": 1,

    "reinforcer": 0,
    "reinforcer_name": "M&Ms",
    "reinforcer_kcal_serving": 210,
    "reinforcer_protein_serving": 2,
    "reinforcer_pieces_serving": 49.196,
    "ekcal_per_piece": (210 - 2 * 5) / 49.196,

    "piece_prob": 0.8 / ((210 - 5 * 2) / 49.196),

    "daily: day": 0.0,
    "daily: ekcal given": 0.0,
    "daily: expected ekcal given": 0.0,
    "daily: variance ekcal given": 0.0,
}

def load_or_create_store():
    """Load and/or create stored add-on preferences annd values"""
    conf = mw.col.conf
    default = default_store

    if not 'udarnik' in conf:
        # create initial configuration
        conf['udarnik'] = default
        mw.col.setMod()

    elif conf['udarnik']['version'] < default['version']:
        print("Updating synced config DB from earlier add-on release")
        for key in list(default.keys()):
            if key not in conf['udarnik']:
                conf['udarnik'][key] = default[key]
        conf['udarnik']['version'] = default_store['version']
        # insert other update actions here:
        mw.col.setMod()
    
    # TODO remove
    #conf['udarnik'] = default
    #mw.col.setMod()

    return mw.col.conf['udarnik']


# To load global config once the profile is loaded
config = None
def load_config_to_global():
    global config
    config = load_or_create_store()
    day_changed_check()
    mw.col.setMod()
addHook("profileLoaded", load_config_to_global)




# Tracking for this session:
ekcal_given = 0.
expected_ekcal_given = 0.
variance_ekcal_given = 0.


# What do we need to do for daily tracking?
#   read the values so far today
#   increment the values so far today on every rev
#   check whether it's the next day yet, and if so, reset
#   create database tables if they don't exist
# using only synced conf, not local preferences


def day_changed_check():
    """Check whether the day has changed since the last time this function was
    called, and if so, reset Udarnik's daily counts."""
    now = datetime.datetime.now()
    stored_day = config['daily: day']
    if stored_day is None:
        same_date = False
    else:
        stored_day = datetime.datetime.fromtimestamp(float(stored_day))

        adjust_val = datetime.datetime.fromtimestamp(mw.col.crt)
        now_adjusted = now - datetime.timedelta(hours = adjust_val.hour)
        
        same_date = now_adjusted.date() == stored_day.date()
    if not same_date:
        print(">>> Resetting stored Udarnik daily tallies...")
        config['daily: day'] = now.timestamp()
        config['daily: ekcal given'] = 0
        config['daily: expected ekcal given'] = 0
        config['daily: variance ekcal given'] = 0
        # client responsible for calling mw.col.setMod()

def update_stored_dailies(new_ekcal_given, new_expected_ekcal_given, new_variance_ekcal_given):
    """Updates stored values of the daily tallies, to include one new
    reinforcement given."""
    # First, check whether day has changed, maybe zero out values
    day_changed_check()
    # Increment stored values
    config['daily: ekcal given'] += new_ekcal_given
    config['daily: expected ekcal given'] += new_expected_ekcal_given
    config['daily: variance ekcal given'] += new_variance_ekcal_given
    # Set database modified
    mw.col.setMod()
    return (config['daily: ekcal given'], config['daily: expected ekcal given'], config['daily: variance ekcal given'])

def compute_percentile(given, expected, variance):
    z = (given - expected) / (variance ** .5)
    return normal_cdf(z)

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
    print("This rev     :           %.2f ekcal, %.2f expectation, %.2f variance" \
            % (ekcal_given_now, expected_ekcal_given_now, ekcal_variance_now))
    percentile = compute_percentile(ekcal_given, expected_ekcal_given, variance_ekcal_given)
    # Assumes that true distribution is normal, which will become true as we review more cards, by central limit theorem
    print("This session : luck %d%%, %.2f ekcal, %.2f expectation, %.2f variance" \
            % (percentile * 100, ekcal_given, expected_ekcal_given, variance_ekcal_given))

    # Update daily totals
    given_daily, expected_daily, variance_daily = update_stored_dailies(ekcal_given_now, expected_ekcal_given_now, ekcal_variance_now)
    percentile = compute_percentile(ekcal_given, expected_ekcal_given, variance_ekcal_given)
    # Assumes that true distribution is normal, which will become true as we review more cards, by central limit theorem
    print("Today        : luck %d%%, %.2f ekcal, %.2f expectation, %.2f variance" \
            % (percentile *  100, given_daily, expected_daily, variance_daily))

    print("")

#TODO refactor this to use "normal variate" objects
    # ie, objects with a (value, expected, variance)
    # and give them a .update(other_variate) method, for daily += this_rev and session += this_rev
    # and make an inherited class with the methods needed for storing updated daily values in the database
    # and give them a .luck() function
    # and give them a .print(show_luck=True) function; it uses a .name that's assigned on init


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
