#-*- coding: utf-8 -*-

"""
Anki add-on: Udarnik

System for operant conditioning of anki use, by providing
food at a rate determined by card difficulty and the calorie
content of the food. See blog post: [Forthcoming.]
"""

### Main module ###

import re
import math
import datetime

import aqt
from aqt.qt import *
from aqt import mw, reviewer

from anki.hooks import wrap, addHook

from .config_dialog import on_udarnik_options
from .schemas import all_schemas

def normal_cdf(value):
    "Cdf for standard normal; don't want to import all of scipy just for this."
    q = math.erf(value / math.sqrt(2.0))
    return (1.0 + q) / 2.0


# using only synced conf, not local preferences
DEFAULT_STORE = {
    "schema": 0,
    "version": 0.46,
    "effective calories per review": 1.0,
    "difficult multiplier": 1.,
    "easy multiplier": 1.3,
    "fail multiplier": 1.,

    "protein cost": -1.,
    "carbs cost": 4 * 1.5,
    "fat cost": 9 * 0.9,
    "vape cost": 6.,

    "reinforcer": 0,
    "reinforcer_name": "apricots, dried",
    "reinforcer_real_kcal_serving": 100.,
    "reinforcer_phantom_kcal_serving": 0.,
    "reinforcer_vapes_serving": 0.,
    "reinforcer_carbs_serving": 29.,
    "reinforcer_fat_serving": 2.,
    "reinforcer_protein_serving": 1.,
    "reinforcer_pieces_serving": 5.,

    "ekcal_per_piece": 0.,
    "real_kcal_per_piece": 0.,
    "phantom_kcal_per_piece": 0.,
    "vapes_per_piece": 0.,
    "carbs_per_piece": 0.,
    "fat_per_piece": 0.,
    "protein_per_piece": 0.,

    "piece_prob": 0.,

    "day": 0.0,
    "daily: ekcal given": 0.0,
    "daily: expected ekcal given": 0.0,
    "daily: variance ekcal given": 0.0,
    "daily: real kcal given": 0.0,
    "daily: phantom kcal given": 0.0,
    "daily: vapes given": 0.0,
    "daily: carbs given": 0.0,
    "daily: fat given": 0.0,
    "daily: protein given": 0.0,
}

def load_or_create_store():
    """Load and/or create stored add-on preferences annd values"""
    conf = mw.col.conf
    default = DEFAULT_STORE

    if not 'udarnik' in conf:
        # create initial configuration
        conf['udarnik'] = default
        mw.col.setMod()

    elif conf['udarnik']['version'] < default['version']:
        print("Updating synced config DB from earlier add-on release")
        for key in list(default.keys()):
            if key not in conf['udarnik']:
                conf['udarnik'][key] = default[key]
        conf['udarnik']['version'] = DEFAULT_STORE['version']
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
real_kcal_given = 0.
phantom_kcal_given = 0.
vapes_given = 0.
carbs_given = 0.
fat_given = 0.
protein_given = 0.


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
    stored_day = config['day']
    if stored_day is None:
        same_date = False
    else:
        stored_day = datetime.datetime.fromtimestamp(float(stored_day))

        adjust_val = datetime.datetime.fromtimestamp(mw.col.crt)
        now_adjusted = now - datetime.timedelta(hours = adjust_val.hour)
        
        same_date = now_adjusted.date() == stored_day.date()
    if not same_date:
        new_day()

def new_day():
    now = datetime.datetime.now()
    stored_day = config['day']

    print(">>> Logging Udarnik daily tallies in Traxis DB...")
    import sys
    sys.path.append("home/j/Traxis")
    sys.path.append("/usr/lib/python3/dist-packages/")
    import util
    with util.WithDBCursor() as cursor:
        cursor.execute("""INSERT INTO UdarnikDayRollovers (
                stored_date, new_date,
                ekcal_given, expected_ekcal_given, variance_ekcal_given,
                real_kcal_given, phantom_kcal_given,
                vapes_given, carbs_given, fat_given, protein_given)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);""",
                (util.given_time_str(datetime.datetime.fromtimestamp(stored_day)),
                util.curr_time_str(),
                config["daily: ekcal given"],
                config["daily: expected ekcal given"],
                config["daily: variance ekcal given"],
                config["daily: real kcal given"],
                config["daily: phantom kcal given"],
                config["daily: vapes given"],
                config["daily: carbs given"],
                config["daily: fat given"],
                config["daily: protein given"],
                ))

    print(">>> Resetting stored Udarnik daily tallies...")
    for k, v in DEFAULT_STORE.items():
        if k.startswith('daily: '):
            config[k] = v
    config['day'] = now.timestamp()
    # client responsible for calling mw.col.setMod()


def update_stored_dailies(
        new_ekcal_given, new_expected_ekcal_given, new_variance_ekcal_given,
        new_real_kcal_given, new_phantom_kcal_given, new_vapes_given, new_carbs_given, new_fat_given, new_protein_given
        ):
    """Updates stored values of the daily tallies, to include one new
    reinforcement given."""
    # First, check whether day has changed, maybe zero out values
    day_changed_check()

    # Increment stored values
    config["daily: ekcal given"] += new_ekcal_given
    config["daily: expected ekcal given"] += new_expected_ekcal_given
    config["daily: variance ekcal given"] += new_variance_ekcal_given
    config["daily: real kcal given"] += new_real_kcal_given
    config["daily: phantom kcal given"] += new_phantom_kcal_given
    config["daily: vapes given"] += new_vapes_given
    config["daily: carbs given"] += new_carbs_given
    config["daily: fat given"] += new_fat_given
    config["daily: protein given"] += new_protein_given

    # Set database modified
    mw.col.setMod()

def compute_percentile(given, expected, variance):
    if variance == 0:
        return -1 # TODO handle this case better, after you've added the NormalVariate class
    z = (given - expected) / (variance ** .5)
    return normal_cdf(z)

previous_cid = None

# Function to probabilistically reinforce card ratings
def reinforce_card_rating(self, ease):
    card = self.card

    # Don't reinforce if you've just reinforced for this card
    # (this usually only happens when you undo a review, in which case we don't want to reinforce both)
    global previous_cid
    if (previous_cid is not None) and (previous_cid == card.id):
        print("Just had a reinforcement-try on this card, not gonna try again; probably due to a rev+undo+rev")
        return
    previous_cid = card.id

    # Find deck multiplier
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
        ease_names = ["fail", "normal"]
    elif cnt == 3:
        ease_names = ["fail", "normal", "easy"]
    else: # cnt == 4
        ease_names = ["fail", "difficult", "normal", "easy"]
    if ease > len(ease_names):
        # seems to happen because user just randomly pressed like button 4 when learning a new card
        print("!!! Udarnik: Assuming that keypress wasn't an actual card-rating but rather just a mistake, since it doesn't seem to make sense")
        return
    else:
        ease = ease_names[ease-1]

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
        raise Exception("unknown ease name %s" % ease)

    # Tell the schema to reinforce, using this probability
    schema = all_schemas[config['schema']]
    piece_probability = config['piece_prob'] * deck_multiplier * ease_multiplier
    print(("Piece probability %.3f = base piece probability %.3f x deck "
           "multiplier %.3f x ease multiplier %.3f")
           % (piece_probability, config['piece_prob'], deck_multiplier, ease_multiplier))
    #print("> piece_probability %s" % piece_probability)
    #print("> config's piece_prob %s" % config['piece_prob'])
    #print("> deck multiplier %s" % deck_multiplier)
    #print("> ease multiplier %s" % ease_multiplier)
    pieces_given_now, pieces_variance_now = schema.card_rev(piece_probability)
    if pieces_variance_now < 0:
        print("WARNING: pieces variance would be <0; setting it to 0; this is caused by e.g. 1-for-1 schema with expected pieces >1")
        pieces_variance_now = 0

    ekcal_per_piece = config['ekcal_per_piece']
    real_kcal_per_piece = config['real_kcal_per_piece']
    phantom_kcal_per_piece = config['phantom_kcal_per_piece']
    vapes_per_piece = config['vapes_per_piece']
    carbs_per_piece = config['carbs_per_piece']
    fat_per_piece = config['fat_per_piece']
    protein_per_piece = config['protein_per_piece']

    ekcal_given_now = pieces_given_now * ekcal_per_piece
    expected_ekcal_given_now = piece_probability * ekcal_per_piece
    ekcal_variance_now = (ekcal_per_piece ** 2) * pieces_variance_now

    real_kcal_now = pieces_given_now * real_kcal_per_piece
    phantom_kcal_now = pieces_given_now * phantom_kcal_per_piece
    vapes_now = pieces_given_now * vapes_per_piece
    carbs_now = pieces_given_now * carbs_per_piece
    fat_now = pieces_given_now * fat_per_piece
    protein_now = pieces_given_now * protein_per_piece

    # Update and report statistics and luck
    print("Card ID %s, Date %s" % (card.id, datetime.datetime.now().strftime("%d-%H:%M:%S.%f")))
    print("This rev     :              %7.2f ekcal, %7.2f expectation, %8.2f standard deviation" \
            % (ekcal_given_now, expected_ekcal_given_now, ekcal_variance_now**.5))
    print("             : %1.1f real kcal, %1.1f phantom kcal, %1.1f vapes, %1.1fg carbs, %1.1fg fat, %1.1fg protein" \
            % (real_kcal_now, phantom_kcal_now, vapes_now, carbs_now, fat_now, protein_now))

    global ekcal_given, expected_ekcal_given, variance_ekcal_given
    ekcal_given += ekcal_given_now
    expected_ekcal_given += piece_probability * ekcal_per_piece
    variance_ekcal_given += ekcal_variance_now
    global real_kcal_given, phantom_kcal_given, phantom_kcal_given, vapes_given, fat_given, carbs_given, protein_given
    real_kcal_given += real_kcal_now
    phantom_kcal_given += phantom_kcal_now
    vapes_given += vapes_now
    fat_given += fat_now
    carbs_given += carbs_now
    protein_given += protein_now
    percentile = compute_percentile(ekcal_given, expected_ekcal_given, variance_ekcal_given)
    # Assumes that true distribution is normal, which will become true as we review more cards, by central limit theorem
    print("This session : luck %6.2f%%, %7.2f ekcal, %7.2f expectation, %8.2f standard deviation, %7.2f equivalent revs" \
            % (percentile * 100, ekcal_given, expected_ekcal_given, variance_ekcal_given**.5, expected_ekcal_given / config["effective calories per review"]))
    print("             : %1.1f real kcal, %1.1f phantom kcal, %1.1f vapes, %1.1fg carbs, %1.1fg fat, %1.1fg protein" \
            % (real_kcal_given, phantom_kcal_given, vapes_given, carbs_given, fat_given, protein_given))

    # Update daily totals
    #TODO no more returning  values
    update_stored_dailies(ekcal_given_now, expected_ekcal_given_now, ekcal_variance_now,
            real_kcal_now, phantom_kcal_now, vapes_now, carbs_now, fat_now, protein_now)
    given_daily = config["daily: ekcal given"]
    expected_daily = config["daily: expected ekcal given"]
    variance_daily = config["daily: variance ekcal given"]

    real_kcal_daily = config["daily: real kcal given"]
    phantom_kcal_daily = config["daily: phantom kcal given"]
    vapes_daily = config["daily: vapes given"]
    carbs_daily = config["daily: carbs given"]
    fat_daily = config["daily: fat given"]
    protein_daily = config["daily: protein given"]

    percentile = compute_percentile(given_daily, expected_daily, variance_daily)
    # Assumes that true distribution is normal, which will become true as we review more cards, by central limit theorem
    print("Today        : luck %6.2f%%, %7.2f ekcal, %7.2f expectation, %8.2f standard deviation, %7.2f equivalent revs" \
            % (percentile *  100, given_daily, expected_daily, variance_daily**.5, expected_daily / config["effective calories per review"]))
    print("             : %1.1f real kcal, %1.1f phantom kcal, %1.1f vapes, %1.1fg carbs, %1.1fg fat, %1.1fg protein" \
            % (real_kcal_daily, phantom_kcal_daily, vapes_daily, carbs_daily, fat_daily, protein_daily))

    print("")

#TODO refactor this to use "normal variate" objects
    # ie, objects with a (value, expected, variance)
    # and give them a .update(other_variate) method, for daily += this_rev and session += this_rev
    # and make an inherited class with the methods needed for storing updated daily values in the database
    # and give them a .luck() function
    # and give them a .print(show_luck=True) function; it uses a .name that's assigned on init
    #     show their name as something like '%12s : ' % self.name, so they're right-aligned to the colons
    # and if, say, number of samples is less than 25 for any distribution, we can print out its luck as "--%", ie refuse to show it
    #     because the distribution will not be approximately normal
#TODO add a NormalVariate for a mean of recent revs, to show luck during the past 20 or so revs
#TODO on clearing daily tallies, log them in a CSV or in Traxis


def on_rollback():
    schema = all_schemas[config['schema']]
    schema.rollback()
def on_reset():
    schema = all_schemas[config['schema']]
    schema.reset()


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
rollback_action = QAction("&Udarnik schema rollback", mw)
rollback_action.setShortcut(QKeySequence("Ctrl+Shift+U"))
rollback_action.triggered.connect(lambda _, o=mw: on_rollback())
    # note that this modifies both our `config` and the one stored in the mw.col.conf['udarnik']
mw.form.menuTools.addAction(rollback_action)

# Add reset button
reset_action = QAction("&Udarnik schema reset", mw)
reset_action.setShortcut(QKeySequence("Ctrl+Shift+R"))
reset_action.triggered.connect(lambda _, o=mw: on_reset())
    # note that this modifies both our `config` and the one stored in the mw.col.conf['udarnik']
mw.form.menuTools.addAction(reset_action)
