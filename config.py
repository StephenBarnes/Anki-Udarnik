#-*- coding: utf-8 -*-

"""
Configuration code for the Udarnik add-on for Anki.
"""

from aqt.qt import *
from aqt import mw

import csv
import os
from collections import OrderedDict
from subprocess import call

from .schemas import *




# location of this file
__location__ = os.path.realpath(
            os.path.join(os.getcwd(), os.path.dirname(__file__)))
reinforcers_fname = os.path.join(__location__, "reinforcers.csv")
reinforcers_backup_fname = os.path.join(__location__, "reinforcers.csv~")



def load_reinforcers():
    """Load reinforcers from reinforcers.csv file."""
    result = [] # list of OrderedDicts, each describing one reinforcer
    expected_field_names = ['name', 'kcal / serving', 'protein / serving', 'pieces / serving']
    with open(reinforcers_fname, "r") as reinforcers_file:
        reader = csv.DictReader(reinforcers_file)
        assert reader.fieldnames == expected_field_names, ("Unexpected fieldnames in reinforcers.csv. " + \
                ("Expected: %s. Actual: %s." % (expected_field_names, reader.fieldnames)))
        for reinforcer in reader:
            for k, v in reinforcer.items():
                if k != 'name':
                    reinforcer[k] = float(v)
            result.append(reinforcer)
    return [None] + result

def none_to_empty(x):
    if x is None:
        return ''
    return str(x)


class UdarnikOptions(QDialog):
    """Main Options dialog"""
    def __init__(self, mw, config):
        QDialog.__init__(self, parent=mw)
        self.original_config = config # stores reference to original config
        self.config = dict(config) # new modified config
        self.reinforcers = load_reinforcers()
        self.setup_ui()
        self.setup_values()
        self.reinforcers_csv_change = False

    def setup_values(self):
        """Set up widget data based on provided config dict"""

        schema_idx = self.config["schema"]
        self.schema_sel.setCurrentIndex(schema_idx)
        self.ekcal_rev_input.setText(str(self.config["effective calories per review"]))
        self.protein_free_input.setText(str(self.config["protein free calories"]))
        self.difficult_mult_input.setText(str(self.config["difficult multiplier"]))
        self.easy_mult_input.setText(str(self.config["easy multiplier"]))
        self.fail_mult_input.setText(str(self.config["fail multiplier"]))

        reinforcer_idx = self.config["reinforcer"]
        reinforcer_names = [(reinforcer['name'] if reinforcer is not None else "(select saved reinforcer to load)")
                for reinforcer in self.reinforcers]
        self.reinforcer_sel.addItems(reinforcer_names)
        self.reinforcer_sel.setCurrentIndex(reinforcer_idx)
        self.name_input.setText(none_to_empty(self.config['reinforcer_name']))
        self.kcal_serving_input.setText(none_to_empty(self.config['reinforcer_kcal_serving']))
        self.protein_serving_input.setText(none_to_empty(self.config['reinforcer_protein_serving']))
        self.pieces_serving_input.setText(none_to_empty(self.config['reinforcer_pieces_serving']))

        self.recalculate()

    def line_edit_updated(self, widget, confname, string=False, reinforcer=False):
        def update_config(newval):
            if string:
                self.config[confname] = newval
            else:
                if newval is None or newval == '':
                    self.config[confname] = 0.
                else:
                    self.config[confname] = float(newval)
        widget.textChanged.connect(update_config)
        if reinforcer:
            def update_reinforcer_sel(newval):
                self.reinforcer_sel.setCurrentIndex(0)
                self.config['reinforcer'] = 0
                self.recalculate()
            widget.textEdited.connect(update_reinforcer_sel)


    def recalculate(self):
        schema = schemas[self.config['schema']]
        try:
            ekcal_per_serving = self.config['reinforcer_kcal_serving'] - self.config['protein free calories'] * self.config['reinforcer_protein_serving']
            ekcal_per_piece = ekcal_per_serving / self.config['reinforcer_pieces_serving']
            piece_per_rev = self.config['effective calories per review'] / ekcal_per_piece 
            self.config['ekcal_per_piece'] = ekcal_per_piece
            self.calories_item_readout.setText('%.3f' % ekcal_per_piece)
            self.piece_prob_readout.setText('%.3f' % piece_per_rev)
            self.piece_cards_readout.setText('%.3f' % (1. / piece_per_rev))
            self.config['piece_prob'] = piece_per_rev
        except ZeroDivisionError:
            self.config['ekcal_per_piece'] = 0.
            self.calories_item_readout.setText('(error)')
            self.piece_prob_readout.setText('(error)')
            self.piece_cards_readout.setText('(error)')
            self.config['piece_prob'] = 0.

    def setup_ui(self):
        """Set up widgets."""

        layout = QFormLayout()

        layout.addRow(QLabel("<b>For all reinforcers:</b>"))

        self.schema_sel = QComboBox()
        self.schema_sel.addItems([schema.name for schema in schemas])
        def update_config_schema(i):
            self.config["schema"] = i
            self.recalculate()
        self.schema_sel.activated.connect(update_config_schema)
        layout.addRow(QLabel("Schema"), self.schema_sel)

        self.ekcal_rev_input = QLineEdit()
        self.ekcal_rev_input.setValidator(QDoubleValidator())
        self.line_edit_updated(self.ekcal_rev_input, "effective calories per review")
        layout.addRow(QLabel("Effective kcal / rev"), self.ekcal_rev_input)

        self.protein_free_input = QLineEdit()
        self.protein_free_input.setValidator(QDoubleValidator())
        self.line_edit_updated(self.protein_free_input, "protein free calories")
        layout.addRow(QLabel("Free kcal / g protein"), self.protein_free_input)

        difficult_mult_l = QLabel("\"Difficult\" multiplier")
        self.difficult_mult_input = QLineEdit()
        self.difficult_mult_input.setValidator(QDoubleValidator())
        self.line_edit_updated(self.difficult_mult_input, "difficult multiplier")
        layout.addRow(QLabel("\"Difficult\" multiplier"), self.difficult_mult_input)

        fail_mult_l = QLabel("\"Easy\" multiplier")
        self.easy_mult_input = QLineEdit()
        self.easy_mult_input.setValidator(QDoubleValidator())
        self.line_edit_updated(self.easy_mult_input, "easy multiplier")
        layout.addRow(QLabel("\"Easy\" multiplier"), self.easy_mult_input)

        fail_mult_l = QLabel("\"Fail\" multiplier")
        self.fail_mult_input = QLineEdit()
        self.fail_mult_input.setValidator(QDoubleValidator())
        self.line_edit_updated(self.fail_mult_input, "fail multiplier")
        layout.addRow(QLabel("\"Fail\" multiplier"), self.fail_mult_input)

        self.restore_defaults_button = QPushButton("&Restore defaults")
        self.restore_defaults_button.clicked.connect(self.restore_defaults)
        layout.addRow(self.restore_defaults_button)

        layout.addItem(QSpacerItem(
            20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        ########################################################################

        layout.addRow(QLabel("<b>Reinforcer details:</b>"))
        
        self.reinforcer_sel = QComboBox()
        self.reinforcer_sel.activated.connect(self.reinforcer_selected)
        layout.addRow(QLabel("Load:"), self.reinforcer_sel)

        self.kcal_serving_input = QLineEdit()
        self.kcal_serving_input.setValidator(QDoubleValidator())
        self.line_edit_updated(self.kcal_serving_input, "reinforcer_kcal_serving", reinforcer=True)
        layout.addRow(QLabel("Kcal / serving"), self.kcal_serving_input)

        self.protein_serving_input = QLineEdit()
        self.protein_serving_input.setValidator(QDoubleValidator())
        self.line_edit_updated(self.protein_serving_input, "reinforcer_protein_serving", reinforcer=True)
        layout.addRow(QLabel("Protein / serving"), self.protein_serving_input)

        self.pieces_serving_input = QLineEdit()
        self.pieces_serving_input.setValidator(QDoubleValidator())
        self.line_edit_updated(self.pieces_serving_input, "reinforcer_pieces_serving", reinforcer=True)
        layout.addRow(QLabel("Pieces / serving"), self.pieces_serving_input)

        self.name_input = QLineEdit()
        self.name_input.setValidator(QDoubleValidator())
        self.line_edit_updated(self.name_input, "reinforcer_name", string=True, reinforcer=True)
        layout.addRow(QLabel("Name"), self.name_input)


        save_delete_layout = QHBoxLayout()
        self.delete_reinforcer_button = QPushButton("&Delete reinforcer")
        self.delete_reinforcer_button.clicked.connect(self.delete_reinforcer)
        save_delete_layout.addWidget(self.delete_reinforcer_button)
        self.save_reinforcer_button = QPushButton("&Save reinforcer")
        self.save_reinforcer_button.clicked.connect(self.save_reinforcer)
        save_delete_layout.addWidget(self.save_reinforcer_button)
        layout.addRow(save_delete_layout)

        layout.addItem(QSpacerItem(
            20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        ########################################################################

        layout.addRow(QLabel("<b>Computed values:</b>"))

        self.calories_item_readout = QLineEdit()
        self.calories_item_readout.setReadOnly(True)
        self.calories_item_readout.setStyleSheet("background-color: rgb(200,200,200);")
        layout.addRow(QLabel("Effective calories per piece"), self.calories_item_readout)

        self.piece_prob_readout = QLineEdit()
        self.piece_prob_readout.setReadOnly(True)
        self.piece_prob_readout.setStyleSheet("background-color: rgb(200,200,200);")
        layout.addRow(QLabel("Standard piece probability"), self.piece_prob_readout)

        self.piece_cards_readout = QLineEdit()
        self.piece_cards_readout.setReadOnly(True)
        self.piece_cards_readout.setStyleSheet("background-color: rgb(200,200,200);")
        layout.addRow(QLabel("Standard cards per piece"), self.piece_cards_readout)


        layout.addItem(QSpacerItem(
            20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        ########################################################################

        ok_cancel_layout = QHBoxLayout()
        self.okay_options_button = QPushButton("&Okay")
        self.okay_options_button.clicked.connect(self.save_options)
        ok_cancel_layout.addWidget(self.okay_options_button)
        self.cancel_button = QPushButton("&Cancel")
        self.cancel_button.clicked.connect(self.cancel)
        ok_cancel_layout.addWidget(self.cancel_button)
        layout.addRow(ok_cancel_layout)

        # TODO add tooltips, item.setToolTip("")

        self.accepted.connect(self.save_options)
        self.rejected.connect(self.cancel)
        self.setLayout(layout)
        self.setMinimumWidth(360)
        self.setWindowTitle('Udarnik Options')
    
    def restore_defaults(self):
        # TODO
        self.recalculate()

    def cancel(self):
        self.close()

    def reinforcer_selected(self, idx):
        self.config['reinforcer'] = idx
        reinforcer = self.reinforcers[idx]
        if reinforcer is not None:
            self.kcal_serving_input.setText(str(reinforcer['kcal / serving']))
            self.protein_serving_input.setText(str(reinforcer['protein / serving']))
            self.pieces_serving_input.setText(str(reinforcer['pieces / serving']))
            self.name_input.setText(reinforcer['name'])
            self.config["reinforcer_kcal_serving"] = reinforcer['kcal / serving']
            self.config["reinforcer_protein_serving"] = reinforcer['protein / serving']
            self.config["reinforcer_pieces_serving"] = reinforcer['pieces / serving']
            self.config["reinforcer_name"] = reinforcer['name']
        self.recalculate()

    def delete_reinforcer(self):
        name = self.name_input.text()
        idx = None
        for i, reinforcer in enumerate(self.reinforcers[1:], 1):
            if reinforcer['name'] == name:
                idx = i
                break
        else:
            raise Exception("no reinforcer by that name found")
        del self.reinforcers[idx]
        self.reinforcer_sel.clear()
        reinforcer_names = [(reinforcer['name'] if reinforcer is not None else "(select saved reinforcer to load)")
                for reinforcer in self.reinforcers]
        self.reinforcer_sel.addItems(reinforcer_names)
        self.reinforcer_sel.setCurrentIndex(0)
        self.config['reinforcer'] = 0
        self.reinforcers_csv_change = True

    def save_reinforcer(self):
        new_reinforcer = OrderedDict()
        new_reinforcer['name'] = self.name_input.text()
        # TODO wrap these float() calls in a try-except block
        new_reinforcer['kcal / serving'] = float(self.kcal_serving_input.text())
        new_reinforcer['protein / serving'] = float(self.protein_serving_input.text())
        new_reinforcer['pieces / serving'] = float(self.pieces_serving_input.text())
        if None in new_reinforcer.values():
            raise Exception("form not filled out")
        modified_index = None
        for i, reinforcer in enumerate(self.reinforcers[1:], 1): # try to overwrite existing reinforcer with that name
            if reinforcer['name'] == new_reinforcer['name']:
                self.reinforcers[i] = new_reinforcer
                modified_index = i
                break
        else: # if it's not overwriting an already-existing reinforcer, add it to the end
            self.reinforcers.append(new_reinforcer)
            modified_index = len(self.reinforcers) - 1
        self.reinforcer_sel.clear()
        reinforcer_names = [(reinforcer['name'] if reinforcer is not None else "(select saved reinforcer to load)")
                for reinforcer in self.reinforcers]
        self.reinforcer_sel.addItems(reinforcer_names)
        self.config['reinforcer'] = modified_index
        self.reinforcer_sel.setCurrentIndex(modified_index)
        self.reinforcers_csv_change = True

    def save_options(self):
        """Apply changes on OK button press"""
        # Write out reinforcers to CSV file
        if self.reinforcers_csv_change:
            call(['cp', reinforcers_fname, reinforcers_backup_fname])
            with open(reinforcers_fname, "w") as reinforcers_file:
                expected_field_names = ['name', 'kcal / serving', 'protein / serving', 'pieces / serving']
                writer = csv.DictWriter(reinforcers_file, expected_field_names)
                writer.writeheader()
                writer.writerows(self.reinforcers[1:]) # the [1:] is to not write out the None

        # Apply it to global `config`
        self.original_config.update(self.config)

        # Apply it to the database
        db_config = mw.col.conf['udarnik']
        for k, v in self.config.items():
            db_config[k] = v
        mw.col.setMod()
        mw.reset()
        self.close()

def on_udarnik_options(mw, config):
    """Call options dialog"""
    dialog = UdarnikOptions(mw, config)
    dialog.exec_()
