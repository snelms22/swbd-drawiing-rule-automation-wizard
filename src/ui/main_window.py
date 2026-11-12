"""Main window: section list | section editor | page preview, with warnings below, and a
File menu for projects.

Every edit re-runs the layout engine and redraws the preview, so what you see is always
the current result of the layout rules.

Projects (decisions 2026-10-15): File > New / Open / Open from Library / Save / Save As.
Projects are .swbd files, saved only when the engineer saves; the title bar shows the file
and a * when there are unsaved changes, and anything that would lose them asks first.
A switchboard opened from the library is an untitled copy, so saving never changes the
library. The project's name is its file name.

Updates (decision 2026-10-15): the released app checks SharePoint for a newer version when
it starts and every 30 minutes, and offers a restart, which goes through the launcher.

One person edits a project at a time (project_lock.py): opening a project someone else has
open gives a read-only copy, where Save works as Save As. Drawings go to the folder the
person picked (File > Drawing Folder), remembered on their PC (preferences.py).
"""
import html
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QFileDialog, QHBoxLayout, QListWidget, QMainWindow, QMessageBox,
    QPushButton, QScrollArea, QSplitter, QStackedWidget, QVBoxLayout, QWidget,
)

from src.layout.page_fitter import fit_pages
from src.layout.settings import LayoutSettings
from src.model.devices import device_problems
from src.model.drawing_info import job_number_problem
from src.model.project_file import (
    EXTENSION, ProjectFileError, attributes_no_longer_on_blocks, open_project, save_project,
)
from src.model.project_lock import held_by_someone_else, release_lock, take_lock
from src.preferences import (
    DRAWING_FOLDER, LAST_SEEN_VERSION, drawing_folder, load_preferences, save_preference,
)
from src.release_notes import notes_since
from src.updates import INSTALLED_LAUNCHER, RELEASE_FOLDER, newer_version_available
from src.model.switchboard import Section, Switchboard, new_switchboard
from src.ui.drawing_info_editor import DrawingInfoEditor
from src.ui.page_preview import PagePreview
from src.ui.section_editor import SectionEditor
from src.version import VERSION

APP_NAME = "Switchboard Configurator"
DRAWING_INFO_ROW_TEXT = "Drawing Information"
FIRST_SECTION_ROW = 1          # row 0 of the section list is Drawing Information
UPDATE_CHECK_MINUTES = 30
FILE_FILTER = f"Switchboard projects (*{EXTENSION})"


class MainWindow(QMainWindow):
    def __init__(self, settings: LayoutSettings, switchboard: Switchboard,
                 autocad_settings=None, autocad_settings_problem: str = "", catalog=None,
                 drawing_info_settings=None, device_settings=None):
        super().__init__()
        self._drawing_info_settings = drawing_info_settings
        self._device_settings = device_settings   # meters, fuses (device pages); None = none
        self._catalog = catalog     # library block sizes/terminals; None = placeholders only
        self._settings = settings
        self._switchboard = switchboard
        self._autocad_settings = autocad_settings
        self._file_path: Path | None = None   # the .swbd this project is saved in, if any
        self._unsaved = False
        self._read_only = False                # someone else has this project open
        self.resize(1500, 900)
        self._build_file_menu()
        self._build_help_menu()

        # Left: the lineup. Sections have no names; the list shows "Section n".
        self.section_list = QListWidget()
        self.section_list.currentRowChanged.connect(self._section_selected)
        self.push_check = QCheckBox("Push to next page")
        self.link_check = QCheckBox("Link with next section")
        self.push_check.toggled.connect(self._page_controls_changed)
        self.link_check.toggled.connect(self._page_controls_changed)

        list_buttons = QHBoxLayout()
        for text, action in (("+ Add", self._add_section), ("Remove", self._remove_section),
                             ("▲", self._move_up), ("▼", self._move_down)):
            button = QPushButton(text)
            button.clicked.connect(action)
            list_buttons.addWidget(button)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(self.section_list)
        left_layout.addLayout(list_buttons)
        left_layout.addWidget(self.push_check)
        left_layout.addWidget(self.link_check)

        self.generate_button = QPushButton("Generate drawing")
        self.generate_button.clicked.connect(self._generate_drawing)
        if autocad_settings is None:
            self.generate_button.setEnabled(False)
            self.generate_button.setToolTip(autocad_settings_problem or "AutoCAD settings not loaded.")
        left_layout.addWidget(self.generate_button)


        # Middle: the Drawing Information page or the editor for the selected section.
        comms_modules = device_settings.comms_modules if device_settings else {}
        meter_models = device_settings.power_meter_models if device_settings else []
        self.editor = SectionEditor(settings, catalog, comms_modules, meter_models,
                                    switchboard_provider=lambda: self._switchboard,
                                    fuse=device_settings.fuse if device_settings else None,
                                    power_supply=device_settings.power_supply if device_settings else None)
        self.editor.changed.connect(self._edited)
        self.drawing_info_editor = DrawingInfoEditor(drawing_info_settings)
        self.drawing_info_editor.changed.connect(self._edited)
        self.editor_pages = QStackedWidget()
        self.editor_pages.addWidget(self.drawing_info_editor)
        self.editor_pages.addWidget(self.editor)
        editor_scroll = QScrollArea()
        editor_scroll.setWidgetResizable(True)
        editor_scroll.setWidget(self.editor_pages)

        # Right: page preview (scrolls when there are many pages).
        self.preview = PagePreview(settings)
        preview_scroll = QScrollArea()
        preview_scroll.setWidgetResizable(True)
        preview_scroll.setWidget(self.preview)

        top_splitter = QSplitter(Qt.Horizontal)
        top_splitter.addWidget(left)
        top_splitter.addWidget(editor_scroll)
        top_splitter.addWidget(preview_scroll)
        editor_scroll.setMinimumWidth(460)   # room for the editor's buttons and slot fields
        top_splitter.setSizes([160, 480, 860])

        # Bottom: warnings
        self.warning_list = QListWidget()

        main_splitter = QSplitter(Qt.Vertical)
        main_splitter.addWidget(top_splitter)
        main_splitter.addWidget(self.warning_list)
        main_splitter.setSizes([750, 150])
        self.setCentralWidget(main_splitter)

        self._rebuild_list(select_index=0)
        self.refresh()
        self._update_title()

        # Only the released app updates itself (not when run from the development folder).
        self._update_offered = None
        if getattr(sys, "frozen", False):
            self._update_timer = QTimer(self)
            self._update_timer.timeout.connect(self._check_for_update)
            self._update_timer.start(UPDATE_CHECK_MINUTES * 60 * 1000)
            QTimer.singleShot(5000, self._check_for_update)

    # --- Updates ------------------------------------------------------------------------

    def show_updates_since_last_session(self, changelog: Path):
        """If this is a newer version than the person last opened, list what changed in
        each version since then (decision 2026-10-19). Shown once per version."""
        last_seen = load_preferences().get(LAST_SEEN_VERSION)
        if last_seen == VERSION:
            return
        try:
            text = changelog.read_text(encoding="utf-8")
        except OSError:
            text = ""
        releases = notes_since(text, last_seen, VERSION)
        save_preference(LAST_SEEN_VERSION, VERSION)
        if releases:
            QTimer.singleShot(300, lambda: self._show_release_notes(releases))

    def _show_release_notes(self, releases):
        parts = []
        for version, notes in releases:
            items = "".join(f"<li>{html.escape(note)}</li>" for note in notes)
            parts.append(f"<p><b>Version {version}</b></p><ul>{items}</ul>")
        box = QMessageBox(self)
        box.setWindowTitle("Updates since your last session")
        box.setTextFormat(Qt.RichText)
        box.setText("<h3>Updates since your last session</h3>" + "".join(parts)
                    + "<p>&nbsp;</p><p>Go try it out :)</p>")
        box.exec()

    def _check_for_update(self):
        newer = newer_version_available(VERSION)
        if newer is None or newer == self._update_offered:
            return                      # nothing new, or already offered (asked once each)
        self._update_offered = newer
        answer = QMessageBox.question(
            self, APP_NAME, f"Version {newer} of the {APP_NAME} is available (you have "
            f"{VERSION}).\n\nRestart now to update? Your project will be closed first.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if answer == QMessageBox.Yes and self._may_discard_changes():
            self._let_go_of_project()
            self._unsaved = False
            subprocess.Popen([str(INSTALLED_LAUNCHER)], cwd=str(INSTALLED_LAUNCHER.parent))
            self.close()

    # --- Projects -----------------------------------------------------------------------

    def _build_file_menu(self):
        menu = self.menuBar().addMenu("&File")
        for text, shortcut, action in (
            ("&New", QKeySequence.New, self._new_project),
            ("&Open...", QKeySequence.Open, self._open_project),
            ("Open from &Library...", None, self._open_from_library),
            ("&Save", QKeySequence.Save, self._save),
            ("Save &As...", QKeySequence.SaveAs, self._save_as),
            (None, None, None),
            ("&Drawing Folder...", None, self._choose_drawing_folder),
        ):
            if text is None:
                menu.addSeparator()
                continue
            item = QAction(text, self)
            if shortcut is not None:
                item.setShortcut(shortcut)
            item.triggered.connect(action)
            menu.addAction(item)

    def _build_help_menu(self):
        menu = self.menuBar().addMenu("&Help")
        about = QAction(f"&About {APP_NAME}", self)
        about.triggered.connect(self._show_about)
        menu.addAction(about)

    def _show_about(self):
        drawings = drawing_folder()
        QMessageBox.about(self, f"About {APP_NAME}", (
            f"{APP_NAME} {VERSION}\nHyper Solutions\n\n"
            f"Drawings are saved in: {drawings or '(not chosen yet)'}\n"
            f"Releases: {RELEASE_FOLDER}\n"
            f"Installed in: {INSTALLED_LAUNCHER.parent}\n"
            f"(launcher.log there records each start, for troubleshooting)"))

    def _update_title(self):
        name = self._file_path.name if self._file_path else "Untitled"
        star = " *" if self._unsaved else ""
        read_only = " (read-only)" if self._read_only else ""
        self.setWindowTitle(f"{APP_NAME} {VERSION} - {name}{read_only}{star}")

    def _edited(self, *_):
        """Any change to the switchboard: mark it unsaved and redraw."""
        self._unsaved = True
        self._update_title()
        self.refresh()

    def _folder(self, kind: str) -> Path:
        """The jobs folder (created if needed) or the switchboard library; the user's home
        folder if the settings didn't load or the folder can't be made."""
        if self._autocad_settings is None:
            return Path.home()
        folder = (self._autocad_settings.jobs_folder if kind == "jobs"
                  else self._autocad_settings.switchboard_library_folder)
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError:
            return Path.home()
        return folder

    def _may_discard_changes(self) -> bool:
        """True if it's fine to replace or close the project: nothing unsaved, or the
        engineer saved it or chose not to."""
        if not self._unsaved:
            return True
        answer = QMessageBox.question(
            self, APP_NAME, "This project has unsaved changes. Save them first?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Save)
        if answer == QMessageBox.Save:
            return self._save()
        return answer == QMessageBox.Discard

    def _show_project(self, switchboard: Switchboard, file_path: Path | None,
                      read_only: bool = False):
        self._let_go_of_project()
        if file_path is not None and not read_only:
            self._try_to_lock(file_path)
        self._switchboard = switchboard
        self._file_path = file_path
        self._read_only = read_only
        self._unsaved = False
        self._rebuild_list(select_index=0)
        self.refresh()
        self._update_title()
        kept = attributes_no_longer_on_blocks(switchboard, self._settings, self._catalog)
        if kept:
            QMessageBox.information(self, APP_NAME, "Opened. Please note:\n" +
                                    "\n".join(f"- {line}" for line in kept))

    def _new_project(self):
        if self._may_discard_changes():
            self._show_project(new_switchboard(), None)

    def _open_project(self):
        self._open_from(self._folder("jobs"), keep_path=True)

    def _open_from_library(self):
        # A library switchboard opens as an untitled copy: saving it goes to the jobs
        # folder and never changes the library.
        self._open_from(self._folder("library"), keep_path=False)

    def _open_from(self, folder: Path, keep_path: bool):
        if not self._may_discard_changes():
            return
        chosen, _ = QFileDialog.getOpenFileName(self, "Open project", str(folder), FILE_FILTER)
        if not chosen:
            return
        try:
            switchboard = open_project(chosen)
        except ProjectFileError as error:
            QMessageBox.warning(self, "Project not opened", str(error))
            return
        read_only = False
        if keep_path:
            holder = held_by_someone_else(Path(chosen))
            if holder is not None:
                choice = self._ask_about_lock(Path(chosen).name, holder)
                if choice is None:
                    return
                read_only = choice == "read-only"
        self._show_project(switchboard, Path(chosen) if keep_path else None, read_only)

    def _ask_about_lock(self, name: str, holder) -> str | None:
        """Someone else has the project open: "read-only", "take over", or None (cancel)."""
        box = QMessageBox(self)
        box.setWindowTitle(APP_NAME)
        box.setIcon(QMessageBox.Warning)
        box.setText(f"{name} is being edited by {holder.describe()}.\n\n"
                    "Only one person can edit a project at a time. You can open a read-only "
                    "copy (use Save As to keep your changes under another name).")
        read_only = box.addButton("Open read-only", QMessageBox.AcceptRole)
        take_over = box.addButton("Take over editing", QMessageBox.DestructiveRole)
        box.addButton(QMessageBox.Cancel)
        box.setDefaultButton(read_only)
        box.exec()
        if box.clickedButton() is read_only:
            return "read-only"
        if box.clickedButton() is take_over:
            sure = QMessageBox.question(
                self, APP_NAME, f"Only take over if you're sure {holder.user} isn't working on "
                f"it (for example, their app closed unexpectedly). Their unsaved changes would "
                f"be lost if they save after you. Take over?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            return "take over" if sure == QMessageBox.Yes else None
        return None

    def _try_to_lock(self, path: Path):
        try:
            take_lock(path)
        except OSError:
            pass              # can't write next to the project: carry on without a lock

    def _let_go_of_project(self):
        """Remove our lock on the current project (when closing it or opening another)."""
        if self._file_path is not None and not self._read_only:
            release_lock(self._file_path)

    def _save(self) -> bool:
        if self._file_path is None or self._read_only:
            return self._save_as()
        return self._write(self._file_path)

    def _save_as(self) -> bool:
        start = self._file_path or self._folder("jobs") / f"{self._switchboard.name}{EXTENSION}"
        chosen, _ = QFileDialog.getSaveFileName(self, "Save project", str(start), FILE_FILTER)
        if not chosen:
            return False
        return self._write(Path(chosen))

    def _write(self, path: Path) -> bool:
        if path.suffix.lower() != EXTENSION:
            path = path.with_name(path.name + EXTENSION)
        holder = held_by_someone_else(path)
        if holder is not None:
            QMessageBox.warning(self, "Project not saved",
                                f"{path.name} is being edited by {holder.describe()}. "
                                f"Save under another name.")
            return False
        self._switchboard.name = path.stem          # the project's name is its file name
        try:
            saved = save_project(self._switchboard, path)
        except OSError as error:
            QMessageBox.warning(self, "Project not saved", f"Could not save {path}:\n{error}")
            return False
        if saved != self._file_path:                # saved under a new name: move our lock
            self._let_go_of_project()
            self._try_to_lock(saved)
        self._file_path = saved
        self._read_only = False
        self._unsaved = False
        self._update_title()
        return True

    def _choose_drawing_folder(self) -> Path | None:
        """Ask where drawings go and remember it on this PC."""
        start = drawing_folder() or Path.home() / "Documents"
        chosen = QFileDialog.getExistingDirectory(self, "Folder for drawings", str(start))
        if not chosen:
            return None
        save_preference(DRAWING_FOLDER, chosen)
        return Path(chosen)

    def closeEvent(self, event):
        if self._may_discard_changes():
            self._let_go_of_project()
            event.accept()
        else:
            event.ignore()

    # --- Section list -------------------------------------------------------------------

    # The list's first row is "Drawing Information"; the sections follow it, so section
    # index i (0 = Section 1) is list row i + 1.

    def _sections(self) -> list[Section]:
        return self._switchboard.sections

    def _section_index(self) -> int:
        """Index of the selected section, or -1 when Drawing Information is selected."""
        return self.section_list.currentRow() - FIRST_SECTION_ROW

    def _rebuild_list(self, select_index):
        """Refill the list and select section `select_index` (-1 = Drawing Information)."""
        self.section_list.blockSignals(True)
        self.section_list.clear()
        self.section_list.addItem(DRAWING_INFO_ROW_TEXT)
        for number in range(1, len(self._sections()) + 1):
            self.section_list.addItem(f"Section {number}")
        self.section_list.blockSignals(False)
        index = min(select_index, len(self._sections()) - 1)
        self.section_list.setCurrentRow(index + FIRST_SECTION_ROW)
        self._section_selected(self.section_list.currentRow())

    def _selected(self) -> Section | None:
        index = self._section_index()
        return self._sections()[index] if 0 <= index < len(self._sections()) else None

    def _section_selected(self, row):
        if row == 0:                      # Drawing Information
            self.drawing_info_editor.load(self._switchboard)
            self.editor_pages.setCurrentWidget(self.drawing_info_editor)
        else:
            self.editor_pages.setCurrentWidget(self.editor)
        section = self._selected()
        self.editor.load(section, self._section_index() + 1)
        for check, value in ((self.push_check, section.push_to_next_page if section else False),
                             (self.link_check, section.link_with_next if section else False)):
            check.blockSignals(True)
            check.setChecked(value)
            check.setEnabled(section is not None)
            check.blockSignals(False)

    def _page_controls_changed(self, *_):
        section = self._selected()
        if section is not None:
            section.push_to_next_page = self.push_check.isChecked()
            section.link_with_next = self.link_check.isChecked()
            self._edited()

    def _add_section(self):
        # New sections go right after the selected one (Drawing Information selected: first).
        insert_at = self._section_index() + 1
        self._sections().insert(insert_at, Section())
        self._rebuild_list(insert_at)
        self._edited()

    def _remove_section(self):
        index = self._section_index()
        if 0 <= index < len(self._sections()):
            del self._sections()[index]
            self._rebuild_list(index)
            self._edited()

    def _move_up(self):
        self._swap(self._section_index(), -1)

    def _move_down(self):
        self._swap(self._section_index(), +1)

    def _swap(self, index, step):
        sections = self._sections()
        other = index + step
        if 0 <= index < len(sections) and 0 <= other < len(sections):
            sections[index], sections[other] = sections[other], sections[index]
            self._rebuild_list(other)
            self._edited()

    # --- AutoCAD ------------------------------------------------------------------------

    def _generate_drawing(self):
        # Imported here so the app still opens (preview only) where AutoCAD isn't installed.
        from src.autocad.generate import GenerateError, drawing_path, generate_drawing

        missing_job = job_number_problem(self._switchboard)
        if missing_job:
            QMessageBox.warning(self, "Drawing not made", missing_job)
            self.section_list.setCurrentRow(0)                 # show Drawing Information
            return
        folder = drawing_folder()
        if folder is None:
            QMessageBox.information(self, APP_NAME, "Pick the folder your drawings should be saved "
                                    "in. You can change it later with File > Drawing Folder.")
            folder = self._choose_drawing_folder()
            if folder is None:
                return
        # Drawings are named after the job number, so generating again replaces the last one.
        target = drawing_path(self._switchboard, folder, self._drawing_info_settings)
        if target.exists():
            answer = QMessageBox.question(
                self, APP_NAME, f"{target.name} already exists in the drawing folder. Replace it?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if answer != QMessageBox.Yes:
                return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            result = generate_drawing(self._switchboard, self._settings, self._autocad_settings,
                                      self._catalog, output_folder=folder,
                                      drawing_info_settings=self._drawing_info_settings,
                                      device_settings=self._device_settings)
        except GenerateError as error:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self, "Drawing not made", str(error))
            return
        except Exception as error:     # AutoCAD/COM errors: show them rather than crash
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "AutoCAD problem", f"{type(error).__name__}: {error}")
            return
        QApplication.restoreOverrideCursor()
        message = f"Drawing saved:\n{result.drawing_file}"
        if result.project_copy is not None:
            message += f"\n\nA copy of the project was saved next to it:\n{result.project_copy.name}"
        if result.problems:
            message += "\n\nPlease check:\n" + "\n".join(f"- {p}" for p in result.problems)
        QMessageBox.information(self, "Drawing made", message)

    # --- Layout -------------------------------------------------------------------------

    def refresh(self):
        self.drawing_info_editor.refresh_preview()     # line 2 counts the breakers
        result = fit_pages(self._switchboard, self._settings, self._catalog, self._device_settings)
        self.preview.show_layout(result)
        self.warning_list.clear()
        missing_job = job_number_problem(self._switchboard)     # required for a drawing
        if missing_job:
            result.warnings.insert(0, missing_job)
        result.warnings += device_problems(self._switchboard)   # CTs and power meters
        if result.warnings:
            # Plain text on purpose: a warning symbol here made Windows search its fonts
            # the first time a warning appeared (about 0.7 s of lag).
            self.warning_list.addItems(result.warnings)
        else:
            self.warning_list.addItem("No warnings.")
