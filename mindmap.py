import sys
import json
import random
import math
import time
import os
import subprocess

os.environ["QT_QUICK_BACKEND"] = "software"

try:
    # QMessageBox eklendi
    from PyQt6.QtWidgets import (QApplication, QMainWindow, QGraphicsView, QGraphicsScene, 
                                 QGraphicsItem, QGraphicsLineItem, QGraphicsTextItem, 
                                 QGraphicsPathItem, QColorDialog, QDialog, QVBoxLayout, 
                                 QLabel, QTextEdit, QPushButton, QComboBox, QFileDialog, QHBoxLayout, QRubberBand, QMessageBox)
    from PyQt6.QtCore import Qt, QPointF, QRectF, QLineF, QPoint, QRect, QSize, QUrl
    from PyQt6.QtGui import QColor, QPen, QBrush, QPainter, QFont, QPainterPath, QTextOption, QPolygonF, QAction, QKeySequence, QImage, QDesktopServices, QPixmap, QFontMetrics
except ImportError:
    print("PyQt6 is missing! Please run 'pip install PyQt6'.")
    sys.exit(1)

GRID_SIZE = 30

class ConnectionLine(QGraphicsLineItem):
    def __init__(self, block1, block2, color="#aaaaaa", style=Qt.PenStyle.SolidLine, is_directed=False):
        super().__init__()
        self.block1, self.block2 = block1, block2
        self.line_color, self.line_style, self.is_directed = QColor(color), style, is_directed
        self.setZValue(-1)
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.update_appearance()
        self.update_position()

    def update_appearance(self):
        self.setPen(QPen(self.line_color, 4, self.line_style))

    def update_position(self):
        if self.block1 and self.block2 and self.block1.scene() and self.block2.scene():
            p1 = self.block1.scenePos() + self.block1.get_center_offset()
            p2 = self.block2.scenePos() + self.block2.get_center_offset()
            self.setLine(QLineF(p1, p2))
            self.prepareGeometryChange()
            self.update()

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(self.pen())
        line = self.line()
        painter.drawLine(line)
        if self.is_directed and line.length() > 30:
            angle = math.atan2(-line.dy(), line.dx())
            painter.setBrush(QBrush(self.line_color))
            painter.setPen(Qt.PenStyle.NoPen)
            for i in range(1, int(line.length() / 60) + 1):
                pos = line.pointAt((i * 60) / line.length())
                if (i * 60) / line.length() > 0.9: continue
                p1 = pos + QPointF(math.sin(angle - math.pi/3) * 8, math.cos(angle - math.pi/3) * 8)
                p2 = pos + QPointF(math.sin(angle - math.pi + math.pi/3) * 8, math.cos(angle - math.pi + math.pi/3) * 8)
                painter.drawPolygon(QPolygonF([pos, p1, p2]))

    def remove_self(self):
        if self.block1 and self in self.block1.connections: self.block1.connections.remove(self)
        if self.block2 and self in self.block2.connections: self.block2.connections.remove(self)
        if self.scene(): self.scene().removeItem(self)

class MindBlock(QGraphicsPathItem):
    def __init__(self, x, y, scene_mgr, text="New Idea", b_color="#4A90E2", t_color="#FFFFFF", h_align=1, v_align=1, uid=None, width=190, height=40, file_path=""):
        super().__init__()
        self.scene_mgr, self.uid = scene_mgr, uid if uid else str(random.randint(1000000, 9999999))
        self.brush_color, self.text_color = QColor(b_color), QColor(t_color)
        self.h_alignment, self.v_alignment = h_align, v_align
        self.setPos(x, y)
        self.w, self.h = width, height
        self.file_path = file_path
        
        self.is_manually_selected = False
        self._is_moving_group = False
        
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsMovable | 
                      QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
                      QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        
        self.text_item = QGraphicsTextItem(self)
        self.connections = []
        self.press_time = 0
        self.update_content(text)

    def get_center_offset(self): return QPointF(self.w / 2, self.h / 2)

    def update_content(self, text):
        display_text = text
        if self.file_path:
            ext = os.path.splitext(self.file_path)[1].lower()
            icon = "📄"
            if ext in ['.pdf']: icon = "📕"
            elif ext in ['.xls', '.xlsx', '.csv']: icon = "📊"
            elif ext in ['.doc', '.docx', '.rtf']: icon = "📝"
            elif ext in ['.ppt', '.pptx']: icon = "📉"
            elif ext in ['.txt', '.md']: icon = "📃"
            elif ext in ['.map']: icon = "🗺️"
            elif ext in ['.mp3', '.wav', '.ogg', '.flac']: icon = "🎵"
            elif ext in ['.mp4', '.mov', '.avi', '.mkv']: icon = "🎬"
            elif ext in ['.py', '.js', '.html', '.css', '.json', '.xml']: icon = "💻"
            elif ext in ['.zip', '.rar', '.7z']: icon = "📦"
            elif ext in ['.svg', '.psd', '.ai']: icon = "🎨"
            
            if text == "New Idea" or not text:
                display_text = f"{icon} {os.path.basename(self.file_path)}"
            elif not text.startswith(icon):
                display_text = f"{icon} {text}"

        self.text_item.setPlainText(display_text)
        self.text_item.setDefaultTextColor(self.text_color)
        
        # Auto-Resize Logic
        fm = QFontMetrics(self.text_item.font())
        text_width = fm.horizontalAdvance(display_text)
        
        if self.file_path:
            self.w = max(190, text_width + 40)
        else:
            self.w = max(self.w, 40)

        self.text_item.setTextWidth(max(10, self.w - 20))
        
        opt = QTextOption()
        opt.setAlignment([Qt.AlignmentFlag.AlignLeft, Qt.AlignmentFlag.AlignHCenter, Qt.AlignmentFlag.AlignRight][self.h_alignment])
        self.text_item.document().setDefaultTextOption(opt)
        th = self.text_item.boundingRect().height()
        y_pos = (self.h - th) / 2 if self.v_alignment == 1 else (10 if self.v_alignment == 0 else self.h - th - 5)
        self.text_item.setPos(10, max(0, y_pos))
        
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, self.w, self.h), 10, 10)
        self.setPath(path)
        self.setBrush(QBrush(self.brush_color))
        
        for connection in self.connections:
            connection.update_position()

    def paint(self, painter, option, widget):
        pen = QPen(QColor("#FFD700") if self.is_manually_selected else Qt.GlobalColor.black, 3 if self.is_manually_selected else 1)
        self.setPen(pen)
        super().paint(painter, option, widget)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange and self.scene():
            if self.scene_mgr.parent.is_global_resize_mode: return self.pos()
            new_pos = value
            if self.scene_mgr.parent.snap_to_grid:
                new_pos = QPointF(round(new_pos.x()/GRID_SIZE)*GRID_SIZE, round(new_pos.y()/GRID_SIZE)*GRID_SIZE)
            
            offset = new_pos - self.pos()
            if self.is_manually_selected and not self._is_moving_group and offset != QPointF(0,0):
                self._is_moving_group = True
                for item in self.scene().items():
                    if isinstance(item, MindBlock) and item.is_manually_selected and item != self:
                        item._is_moving_group = True
                        item.setPos(item.pos() + offset)
                        item._is_moving_group = False
                self._is_moving_group = False
            for l in self.connections: l.update_position()
            return new_pos
        return super().itemChange(change, value)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.scene_mgr.delete_block(self); return
        self.press_time = time.time()
        if event.button() == Qt.MouseButton.MiddleButton:
            is_dir = not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
            self.scene_mgr.start_connection(self, directed=is_dir)
            event.accept(); return
        if event.button() == Qt.MouseButton.LeftButton and event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
            self.is_manually_selected = not self.is_manually_selected
            self.update(); event.accept(); return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.scene_mgr.parent.is_global_resize_mode and (event.buttons() & Qt.MouseButton.LeftButton):
            new_w = event.pos().x()
            new_h = event.pos().y()
            if self.scene_mgr.parent.snap_to_grid:
                new_w = round(new_w / GRID_SIZE) * GRID_SIZE
                new_h = round(new_h / GRID_SIZE) * GRID_SIZE
            self.w = max(50, new_w)
            self.h = max(30, new_h)
            self.update_content(self.text_item.toPlainText())
            for l in self.connections: l.update_position()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if not self.scene_mgr.parent.is_global_resize_mode and event.button() == Qt.MouseButton.LeftButton:
            if (time.time() - self.press_time) < 0.2 and not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
                self.open_editor()
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if self.file_path and os.path.exists(self.file_path):
            if self.file_path.endswith('.map'):
                self.open_sub_map()
            else:
                QDesktopServices.openUrl(QUrl.fromLocalFile(self.file_path))
        else:
            super().mouseDoubleClickEvent(event)

    def open_sub_map(self):
        try:
            subprocess.Popen([sys.executable, sys.argv[0], self.file_path])
        except Exception as e:
            print(f"Error opening map: {e}")

    def open_editor(self):
        selected_blocks = [i for i in self.scene().items() if isinstance(i, MindBlock) and i.is_manually_selected]
        if self not in selected_blocks: selected_blocks.append(self)
        d = QDialog(); d.setWindowTitle("Edit Block"); d.setMinimumSize(350, 480); layout = QVBoxLayout(d)
        
        edit = QTextEdit(); edit.setPlainText(self.text_item.toPlainText()); layout.addWidget(QLabel("<b>Text / Description:</b>")); layout.addWidget(edit)
        if len(selected_blocks) > 1: edit.setEnabled(False)

        f_lbl = QLabel(f"Linked File: {os.path.basename(self.file_path)}" if self.file_path else "<i>No File</i>")
        f_lbl.setStyleSheet("color: blue; font-style: italic;")
        layout.addWidget(f_lbl)
        btn_file = QPushButton("📁 Select / Change File"); layout.addWidget(btn_file)
        
        temp_path = self.file_path
        def sel_file():
            nonlocal temp_path
            filters = "All Supported (*.pdf *.txt *.docx *.xlsx *.pptx *.map *.mp3 *.wav *.mp4 *.py *.html *.css *.js *.json *.zip *.rar);;All Files (*.*)"
            p, _ = QFileDialog.getOpenFileName(d, "Select File", "", filters)
            if p: temp_path = p; f_lbl.setText(f"Selected: {os.path.basename(p)}")
        btn_file.clicked.connect(sel_file)

        cb_h = QComboBox(); cb_h.addItems(["Left", "Center", "Right"]); cb_h.setCurrentIndex(self.h_alignment)
        cb_v = QComboBox(); cb_v.addItems(["Top", "Center", "Bottom"]); cb_v.setCurrentIndex(self.v_alignment)
        grid = QHBoxLayout(); grid.addWidget(QLabel("Horizontal:")); grid.addWidget(cb_h); grid.addWidget(QLabel("Vertical:")); grid.addWidget(cb_v); layout.addLayout(grid)
        
        row = QHBoxLayout(); b1, b2 = QPushButton("Box Color"), QPushButton("Text Color")
        for b in [b1, b2]: b.setMinimumHeight(40); row.addWidget(b)
        layout.addLayout(row)
        temp_brush, temp_text_c = self.brush_color, self.text_color
        def pick_b(): nonlocal temp_brush; c = QColorDialog.getColor(temp_brush, d); (temp_brush := c) if c.isValid() else None
        def pick_t(): nonlocal temp_text_c; c = QColorDialog.getColor(temp_text_c, d); (temp_text_c := c) if c.isValid() else None
        b1.clicked.connect(pick_b); b2.clicked.connect(pick_t)
        
        del_btn = QPushButton("🗑️ DELETE BLOCK"); del_btn.setStyleSheet("background: #f44336; color: white; font-weight: bold; padding: 10px;")
        del_btn.clicked.connect(lambda: [self.scene_mgr.delete_block(self), d.accept()])
        layout.addWidget(del_btn)
        
        ok_btn = QPushButton("✅ SAVE"); ok_btn.setStyleSheet("background: #2E7D32; color: white; font-weight: bold; padding: 10px;")
        ok_btn.clicked.connect(d.accept); layout.addWidget(ok_btn)
        
        if d.exec():
            for block in selected_blocks:
                block.brush_color, block.text_color = temp_brush, temp_text_c
                block.h_alignment, block.v_alignment = cb_h.currentIndex(), cb_v.currentIndex()
                block.file_path = temp_path
                txt = edit.toPlainText() if len(selected_blocks) == 1 else block.text_item.toPlainText()
                block.update_content(txt)
                block.update()

class CustomView(QGraphicsView):
    def __init__(self, scene):
        super().__init__(scene); self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self._panning = self._selecting = False; self.rubberBand = QRubberBand(QRubberBand.Shape.Rectangle, self); self.origin = QPoint()

    def wheelEvent(self, e):
        f_in, f_out = 1.15, 0.85
        curr = self.transform().m11()
        if e.angleDelta().y() > 0 and curr < 5.0: self.scale(f_in, f_in)
        elif e.angleDelta().y() < 0 and curr > 0.15: self.scale(f_out, f_out)

    def mousePressEvent(self, e):
        it = self.itemAt(e.position().toPoint())
        if e.button() == Qt.MouseButton.LeftButton and e.modifiers() == Qt.KeyboardModifier.ShiftModifier and it is None:
            self._selecting = True; self.origin = e.position().toPoint(); self.rubberBand.setGeometry(QRect(self.origin, QSize())); self.rubberBand.show(); return
        if e.button() == Qt.MouseButton.MiddleButton and not it: self._panning, self._last_pos = True, e.position(); self.setCursor(Qt.CursorShape.ClosedHandCursor); return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._selecting: self.rubberBand.setGeometry(QRect(self.origin, e.position().toPoint()).normalized()); return
        if self._panning:
            d = e.position() - self._last_pos; self._last_pos = e.position()
            self.horizontalScrollBar().setValue(int(self.horizontalScrollBar().value() - d.x())); self.verticalScrollBar().setValue(int(self.verticalScrollBar().value() - d.y())); return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if self._selecting:
            self.rubberBand.hide(); rect = self.mapToScene(self.rubberBand.geometry()).boundingRect()
            for i in self.scene().items(rect): (setattr(i, 'is_manually_selected', True), i.update()) if isinstance(i, MindBlock) else None
            self._selecting = False; return
        if e.button() == Qt.MouseButton.MiddleButton: self._panning = False; self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseReleaseEvent(e)

class MindMapScene(QGraphicsScene):
    def __init__(self, parent):
        super().__init__(); self.parent = parent; self.setSceneRect(0, 0, 10000, 10000); self.src = None

    def drawBackground(self, p, r):
        p.fillRect(r, self.backgroundBrush()); p.setPen(QPen(QColor("#555555"), 1))
        for x in range(int(r.left())-int(r.left()%30), int(r.right()), 30):
            for y in range(int(r.top())-int(r.top()%30), int(r.bottom()), 30): p.drawPoint(x, y)

    def mousePressEvent(self, e):
        it = self.itemAt(e.scenePos(), QGraphicsView().transform())
        
        if e.button() == Qt.MouseButton.RightButton and (e.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            filters = "All Supported (*.pdf *.txt *.docx *.xlsx *.pptx *.map *.mp3 *.wav *.mp4 *.py *.html *.css *.js *.json *.zip *.rar);;All Files (*.*)"
            p, _ = QFileDialog.getOpenFileName(None, "Import File", "", filters)
            if p: self.addItem(MindBlock(e.scenePos().x(), e.scenePos().y(), self, file_path=p))
            return

        if e.button() == Qt.MouseButton.LeftButton and it is None:
            if not (QApplication.keyboardModifiers() & Qt.KeyboardModifier.ShiftModifier):
                for i in self.items(): (setattr(i, 'is_manually_selected', False), i.update()) if isinstance(i, MindBlock) else None
                self.src = None
        
        if e.button() == Qt.MouseButton.RightButton and not (e.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            if isinstance(it, ConnectionLine):
                b1, b2, dr, col, sty = it.block1, it.block2, it.is_directed, it.line_color.name(), it.line_style
                it.remove_self(); nb = MindBlock(e.scenePos().x()-95, e.scenePos().y()-20, self); self.addItem(nb)
                for p_ in [(b1, nb), (nb, b2)]:
                    nl = ConnectionLine(p_[0], p_[1], col, sty, dr); self.addItem(nl); p_[0].connections.append(nl); p_[1].connections.append(nl)
                return
            elif it is None:
                x, y = (round(e.scenePos().x()/30)*30, round(e.scenePos().y()/30)*30) if self.parent.snap_to_grid else (e.scenePos().x(), e.scenePos().y())
                self.addItem(MindBlock(x, y, self)); return
        if e.button() == Qt.MouseButton.LeftButton and isinstance(it, ConnectionLine): self.open_line_editor(it); return
        super().mousePressEvent(e)

    def delete_block(self, b):
        # AUTO-HEAL
        incoming_nodes = []
        outgoing_nodes = []
        for conn in b.connections:
            if conn.block2 == b: incoming_nodes.append(conn.block1)
            elif conn.block1 == b: outgoing_nodes.append(conn.block2)

        for l in list(b.connections): l.remove_self()
        if b.scene(): self.removeItem(b)

        for input_block in incoming_nodes:
            for output_block in outgoing_nodes:
                exists = False
                for existing_conn in input_block.connections:
                    if existing_conn.block1 == input_block and existing_conn.block2 == output_block:
                        exists = True; break
                
                if not exists and input_block != output_block:
                    nl = ConnectionLine(input_block, output_block, is_directed=True)
                    self.addItem(nl)
                    input_block.connections.append(nl); output_block.connections.append(nl)

    def open_line_editor(self, line):
        d = QDialog(); d.setWindowTitle("Connection Settings"); d.setFixedSize(350, 320); layout = QVBoxLayout(d)
        layout.setContentsMargins(20,20,20,20); layout.setSpacing(10)
        layout.addWidget(QLabel("<b>Line Style:</b>"))
        cb = QComboBox(); cb.addItems(["Solid Line", "Dashed Line", "Dotted Line"]); 
        styles = [Qt.PenStyle.SolidLine, Qt.PenStyle.DashLine, Qt.PenStyle.DotLine]
        cb.setCurrentIndex(styles.index(line.line_style)); layout.addWidget(cb)
        btn_c = QPushButton("🎨 Change Color"); btn_c.setMinimumHeight(35)
        btn_c.clicked.connect(lambda: [setattr(line, 'line_color', QColorDialog.getColor(line.line_color, d)), line.update_appearance()]); layout.addWidget(btn_c)
        btn_del = QPushButton("🗑️ DELETE CONNECTION"); btn_del.setMinimumHeight(40)
        btn_del.setStyleSheet("background-color: #d32f2f; color: white; font-weight: bold; border-radius: 5px;")
        btn_del.clicked.connect(lambda: [line.remove_self(), d.accept()]); layout.addWidget(btn_del)
        btn_ok = QPushButton("✅ OK"); btn_ok.setMinimumHeight(40); btn_ok.clicked.connect(d.accept); layout.addWidget(btn_ok)
        if d.exec(): line.line_style = styles[cb.currentIndex()]; line.update_appearance()

    def start_connection(self, b, directed=False):
        if not self.src: self.src = b; b.is_manually_selected = True; b.update()
        elif self.src != b:
            if not any((l.block1 == self.src and l.block2 == b) for l in self.src.connections):
                nl = ConnectionLine(self.src, b, is_directed=directed); self.addItem(nl); self.src.connections.append(nl); b.connections.append(nl)
            self.src = None; [i.update() for i in self.items()]
        else: self.src = None

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle("Pro Mind Map v95 - Final Safe")
        self.snap_to_grid = True; self.is_global_resize_mode = False; self.current_file = None
        self.scene = MindMapScene(self); self.scene.setBackgroundBrush(QBrush(QColor("#2b2b2b")))
        self.view = CustomView(self.scene); self.setCentralWidget(self.view)
        self.init_menu()
        if len(sys.argv) > 1 and os.path.exists(sys.argv[1]): self.load_from_path(sys.argv[1])

    def init_menu(self):
        mb = self.menuBar(); fm = mb.addMenu("File")
        fm.addAction(QAction("New Map", self, shortcut="Ctrl+N", triggered=self.new_map))
        fm.addAction(QAction("Open File", self, shortcut="Ctrl+O", triggered=self.load))
        fm.addAction(QAction("Import...", self, shortcut="Ctrl+I", triggered=self.import_from_menu))
        fm.addAction(QAction("Save", self, shortcut="Ctrl+S", triggered=self.save))
        fm.addAction(QAction("Save As", self, shortcut="Ctrl+Shift+S", triggered=self.save_as))
        fm.addAction(QAction("Export PNG", self, triggered=self.export_png))
        am = mb.addMenu("Settings")
        self.snap_act = QAction("Snap [S]", self, checkable=True, shortcut="S"); self.snap_act.setChecked(True)
        self.snap_act.triggered.connect(lambda: setattr(self, 'snap_to_grid', self.snap_act.isChecked())); am.addAction(self.snap_act)
        self.res_act = QAction("Resize [R]", self, checkable=True, shortcut="R"); self.res_act.triggered.connect(self.toggle_resize); am.addAction(self.res_act)
        tm = am.addMenu("Theme"); tm.addAction("Dark", lambda: self.set_bg("#2b2b2b")); tm.addAction("Light", lambda: self.set_bg("#f0f0f0")); tm.addAction("Custom...", self.pick_bg)

    def new_map(self):
        reply = QMessageBox.question(self, 'New Map', "Are you sure you want to create a new map? Unsaved changes will be lost.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.scene.clear(); self.current_file = None; self.set_bg("#2b2b2b")

    def import_from_menu(self):
        filters = "All Supported (*.pdf *.txt *.docx *.xlsx *.pptx *.map *.mp3 *.wav *.mp4 *.py *.html *.css *.js *.json *.zip *.rar);;All Files (*.*)"
        p, _ = QFileDialog.getOpenFileName(self, "Import File", "", filters)
        if p:
            center_pos = self.view.mapToScene(self.view.viewport().rect().center())
            self.scene.addItem(MindBlock(center_pos.x(), center_pos.y(), self.scene, file_path=p))

    def set_bg(self, c): self.scene.setBackgroundBrush(QBrush(QColor(c)))
    def pick_bg(self):
        c = QColorDialog.getColor(self.scene.backgroundBrush().color(), self)
        if c.isValid(): self.set_bg(c.name())
    def delete_manually_selected(self):
        for item in [i for i in self.scene.items() if isinstance(i, MindBlock) and i.is_manually_selected]: self.scene.delete_block(item)
    def export_png(self):
        r = self.scene.itemsBoundingRect().adjusted(-50,-50,50,50)
        img = QImage(r.size().toSize(), QImage.Format.Format_ARGB32); img.fill(self.scene.backgroundBrush().color())
        p = QPainter(img); p.setRenderHint(QPainter.RenderHint.Antialiasing); self.scene.render(p, QRectF(img.rect()), r); p.end()
        path, _ = QFileDialog.getSaveFileName(self, "Save", "", "PNG Files (*.png)")
        if path: img.save(path)
    def toggle_resize(self):
        self.is_global_resize_mode = self.res_act.isChecked()
        self.view.setCursor(Qt.CursorShape.SizeFDiagCursor if self.is_global_resize_mode else Qt.CursorShape.ArrowCursor); self.scene.update()
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_X: self.delete_manually_selected()
        super().keyPressEvent(event)
    def save(self): self.do_save(self.current_file) if self.current_file else self.save_as()
    def save_as(self):
        p, _ = QFileDialog.getSaveFileName(self, "Save As", "", "Map Files (*.map)")
        if p: self.current_file = p; self.do_save(p)
    def do_save(self, path):
        data = {"bg": self.scene.backgroundBrush().color().name(), "blocks": [], "lines": []}
        for b in [i for i in self.scene.items() if isinstance(i, MindBlock)]:
            data["blocks"].append({
                "x": b.x(), "y": b.y(), "txt": b.text_item.toPlainText(), "bc": b.brush_color.name(), "tc": b.text_color.name(), 
                "ha": b.h_alignment, "va": b.v_alignment, "id": b.uid, "w": b.w, "h": b.h, "f_path": b.file_path
            })
        for l in [i for i in self.scene.items() if isinstance(i, ConnectionLine)]:
            data["lines"].append({"b1": l.block1.uid, "b2": l.block2.uid, "c": l.line_color.name(), "s": int(l.line_style.value), "dir": l.is_directed})
        with open(path, "w") as f: json.dump(data, f)
    def load(self):
        p, _ = QFileDialog.getOpenFileName(self, "Open File", "", "Map Files (*.map)")
        if p: self.load_from_path(p)

    def load_from_path(self, path):
        self.scene.clear(); self.current_file = path
        with open(path, "r") as f: data = json.load(f)
        self.set_bg(data.get("bg", "#2b2b2b"))
        u = {}
        for b in data["blocks"]:
            nb = MindBlock(b["x"], b["y"], self.scene, b["txt"], b["bc"], b.get("tc", "#FFFFFF"), b.get("ha", 1), b.get("va", 1), b["id"], b.get("w", 190), b.get("h", 40), b.get("f_path", ""))
            self.scene.addItem(nb); u[b["id"]] = nb
        for l in data["lines"]:
            b1, b2 = u.get(l["b1"]), u.get(l["b2"])
            if b1 and b2:
                nl = ConnectionLine(b1, b2, l["c"], Qt.PenStyle(l["s"]), l.get("dir", False))
                self.scene.addItem(nl); b1.connections.append(nl); b2.connections.append(nl)

if __name__ == "__main__":
    app = QApplication(sys.argv); win = MainWindow(); win.showMaximized(); sys.exit(app.exec())