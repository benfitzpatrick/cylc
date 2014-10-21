#!/usr/bin/env python
#C: THIS FILE IS PART OF THE CYLC SUITE ENGINE.
#C: Copyright (C) 2008-2014 Hilary Oliver, NIWA
#C:
#C: This program is free software: you can redistribute it and/or modify
#C: it under the terms of the GNU General Public License as published by
#C: the Free Software Foundation, either version 3 of the License, or
#C: (at your option) any later version.
#C:
#C: This program is distributed in the hope that it will be useful,
#C: but WITHOUT ANY WARRANTY; without even the implied warranty of
#C: MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#C: GNU General Public License for more details.
#C:
#C: You should have received a copy of the GNU General Public License
#C: along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""Cylc gui log viewer, with a combo box for log file selection."""

import gobject
import gtk
import os

from cylc.gui.logviewer import logviewer
from cylc.gui.tailer import tailer


class ComboLogViewer(logviewer):

    """Implement a log viewer for the "cylc gui".
    
    It has a a combo box for log file selection.

    """

    LABEL_TEXT = "Choose Log File: "
    MAX_FILE_RADIO_NUM = 2
    MAX_FILE_RADIO_CHAR_LENGTH = 10

    def __init__(self, name, file_list):
        self.common_dir = os.path.dirname(os.path.commonprefix(file_list))
        self.subdirs_files = []
        self._subdir = None
        for file_ in file_list:
            rel_file = os.path.relpath(file_, self.common_dir)
            subdir = os.path.dirname(rel_file)
            if subdir:
                subdir += os.path.sep
            subfile = os.path.basename(rel_file)
            self.subdirs_files.append((subdir, subfile))
        logviewer.__init__(self, name, None, file_list[0])

    def create_gui_panel(self):
        """Create the panel."""
        logviewer.create_gui_panel(self)
        label = gtk.Label(self.LABEL_TEXT)

        subdir_combobox = gtk.combo_box_new_text()

        self._subfile_hbox = gtk.HBox()
        self.hbox.pack_end(self._subfile_hbox, False)

        subdirs_done = []
        for subdir, subfile in self.subdirs_files:
            if subdir and subdir not in subdirs_done:
                subdir_combobox.append_text(subdir)
                subdirs_done.append(subdir)

        if subdirs_done:
            subdir_combobox.connect("changed", self._switch_subdir_combobox)
            subdir_combobox.set_active(0)
            self.hbox.pack_end(subdir_combobox, False)
        else:
            self.set_subdir("")
        self.hbox.pack_end(label, False)

    def set_subdir(self, subdir):
        """Switch to another subdirectory, if necessary."""
        self._subdir = subdir
        subfiles = []
        for subdir, subfile in self.subdirs_files:
            if subdir == self._subdir:
                subfiles.append(subfile)
        for child in self._subfile_hbox:
            self._subfile_hbox.remove(child)
        if not subfiles:
            return
        max_len_chars_subfiles = max([len(_) for _ in subfiles])
        if (len(subfiles) > self.MAX_FILE_RADIO_NUM or
                max_len_chars_subfiles > self.MAX_FILE_RADIO_CHAR_LENGTH):
            # Use a combo box to represent the list of files.
            subfile_combobox = gtk.combo_box_new_text()
            
            for file_ in subfiles:
                subfile_combobox.append_text(file_)

            subfile_combobox.connect("changed", self._switch_file_combobox)
            subfile_combobox.set_active(0)
            subfile_combobox.show()
            self._subfile_hbox.pack_start(subfile_combobox)
            return
        # Otherwise, use some radio buttons to represent the list of files.
        radiobutton = None
        for file_ in subfiles:
            radiobutton = gtk.RadioButton(
                group=radiobutton, label=file_, use_underline=False)
            radiobutton.connect("toggled", self._switch_file_radiobutton)
            radiobutton.show()
            self._subfile_hbox.pack_start(radiobutton)
        radiobutton.get_group()[-1].set_active(True)
        radiobutton.get_group()[-1].toggled()

    def set_file(self, file_, file_desc):
        """Switch to another file, if necessary."""
        if file_ == self.file:
            return
        self.file = file_
        self.t.quit = True
        logbuffer = self.logview.get_buffer()
        pos_start, pos_end = logbuffer.get_bounds()
        self.reset_logbuffer()
        logbuffer.delete(pos_start, pos_end)
        self.log_label.set_text(file_desc)
        self.t = tailer(self.logview, file_)
        self.t.start()

    def _switch_file_combobox(self, combobox):
        """Handle a switch to another file within a combo box."""
        model = combobox.get_model()
        index = combobox.get_active()
        rel_path = os.path.join(self._subdir, model[index][0])
        file_ = os.path.join(self.common_dir, rel_path)
        self.set_file(file_, rel_path)

    def _switch_file_radiobutton(self, radiobutton):
        """Handle a switch to another file within a radio button."""
        if not radiobutton.get_active():
            # Both the inactive and active radio buttons report 'toggled'.
            return
        rel_path = os.path.join(self._subdir, radiobutton.get_label())
        file_ = os.path.join(self.common_dir, rel_path)
        self.set_file(file_, rel_path)

    def _switch_subdir_combobox(self, combobox):
        """Switch to another subdirectory, if necessary."""
        model = combobox.get_model()
        index = combobox.get_active()
        self.set_subdir( model[index][0])
