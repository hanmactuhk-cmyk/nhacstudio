
import sys, os, json, time
import numpy as np
import sounddevice as sd
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QSlider, QDialog, QFormLayout, QDoubleSpinBox,
    QSpinBox, QCheckBox, QMessageBox, QFileDialog, QGroupBox
)

APP_NAME = "HNStudio Musik AI"

class EffectDialog(QDialog):
    def __init__(self, title, fields, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(380)
        lay = QFormLayout(self)
        self.controls = {}
        for name, kind, value, lo, hi in fields:
            if kind == "double":
                w = QDoubleSpinBox(); w.setRange(lo, hi); w.setValue(value); w.setSingleStep((hi-lo)/100)
            elif kind == "int":
                w = QSpinBox(); w.setRange(int(lo), int(hi)); w.setValue(int(value))
            else:
                w = QSlider(Qt.Horizontal); w.setRange(int(lo), int(hi)); w.setValue(int(value))
            self.controls[name] = w
            lay.addRow(name, w)
        b = QPushButton("APPLY")
        b.clicked.connect(self.accept)
        lay.addRow(b)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1180, 760)
        self.audio_stream = None
        self.recording = False
        self.frames = []
        self.project = {
            "name": "Untitled",
            "audio": {"input": "", "output": "", "sample_rate": 48000, "block_size": 256},
            "effects": {
                "Auto-Tune": {"key": "AUTO", "scale": "AUTO", "retune_ms": 20, "humanize": 30},
                "EQ": {"bands": []},
                "Compressor": {"threshold": -18, "ratio": 3},
                "De-Esser": {"frequency": 6500, "amount": 35},
                "Reverb": {"type": "Hall", "mix": 22, "decay": 1.8},
                "Delay": {"time": 280, "feedback": 18, "mix": 10},
                "Noise Reduction": {"amount": 55},
                "Limiter": {"ceiling": -1.0},
            }
        }
        self.build_ui()
        self.refresh_devices()

    def build_ui(self):
        central = QWidget(); self.setCentralWidget(central)
        root = QVBoxLayout(central); root.setSpacing(12)

        title = QLabel("✦ H N S T U D I O   M U S I K   A I ✦")
        title.setAlignment(Qt.AlignCenter); title.setObjectName("title")
        root.addWidget(title)

        top = QHBoxLayout()
        self.input_box = QComboBox(); self.output_box = QComboBox()
        self.rate_box = QComboBox(); self.rate_box.addItems(["44100","48000","96000"])
        self.buffer_box = QComboBox(); self.buffer_box.addItems(["64","128","256","512","1024"])
        for lab, w in [("INPUT",self.input_box),("OUTPUT",self.output_box),("RATE",self.rate_box),("BUFFER",self.buffer_box)]:
            top.addWidget(QLabel(lab)); top.addWidget(w)
        refresh = QPushButton("↻")
        refresh.clicked.connect(self.refresh_devices); top.addWidget(refresh)
        root.addLayout(top)

        self.wave = QLabel("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        self.wave.setObjectName("wave")
        self.wave.setAlignment(Qt.AlignCenter)
        root.addWidget(self.wave)

        status = QHBoxLayout()
        self.note = QLabel("NOTE: —"); self.key = QLabel("KEY: AUTO / AUTO")
        self.level = QLabel("INPUT: —"); self.latency = QLabel("LATENCY: —")
        for x in (self.note,self.key,self.level,self.latency): status.addWidget(x)
        root.addLayout(status)

        grid = QHBoxLayout()
        effects = [
            ("🎵 AUTO-TUNE","Auto-Tune"),
            ("〽 EQ","EQ"),
            ("⚡ COMPRESSOR","Compressor"),
            ("S DE-ESSER","De-Esser"),
            ("🌊 REVERB","Reverb"),
            ("↻ DELAY","Delay"),
            ("🔇 NOISE","Noise Reduction"),
            ("▣ LIMITER","Limiter"),
        ]
        for label, key in effects:
            b=QPushButton(label); b.setMinimumHeight(58)
            b.clicked.connect(lambda _, k=key: self.open_effect(k))
            grid.addWidget(b)
        root.addLayout(grid)

        controls = QHBoxLayout()
        self.live = QPushButton("🔴 LIVE OFF"); self.live.setCheckable(True); self.live.clicked.connect(self.toggle_live)
        self.rec = QPushButton("● REC"); self.rec.setCheckable(True); self.rec.clicked.connect(self.toggle_record)
        play = QPushButton("▶ PLAY"); play.clicked.connect(self.play_last)
        new = QPushButton("NEW PROJECT"); new.clicked.connect(self.new_project)
        save = QPushButton("SAVE PROJECT"); save.clicked.connect(self.save_project)
        op = QPushButton("OPEN PROJECT"); op.clicked.connect(self.open_project)
        for b in (self.live,self.rec,play,new,save,op): controls.addWidget(b)
        root.addLayout(controls)

        io = QGroupBox("AUDIO SETUP")
        form = QHBoxLayout(io)
        form.addWidget(QLabel("Device routing: chọn INPUT/OUTPUT ở phía trên • ASIO có thể thêm ở bản nâng cấp"))
        root.addWidget(io)

        self.setStyleSheet("""
        QWidget { background:#080812; color:#e9e9ff; font-family:Segoe UI; }
        #title { color:#a970ff; font-size:28px; font-weight:700; padding:12px; }
        #wave { color:#35e7ff; font-size:22px; background:#0d0d1c; border:1px solid #5d2cff; padding:18px; }
        QPushButton { background:#101024; border:1px solid #6b35ff; border-radius:8px; padding:10px; color:#eee; }
        QPushButton:hover { border:1px solid #31e8ff; color:#31e8ff; }
        QPushButton:checked { background:#27104a; border:2px solid #ff35d6; color:#ff7be9; }
        QComboBox, QSpinBox, QDoubleSpinBox { background:#101024; border:1px solid #4930a8; padding:7px; }
        QGroupBox { border:1px solid #4930a8; border-radius:8px; padding:12px; }
        """)

    def refresh_devices(self):
        try:
            devs = sd.query_devices()
            self.input_box.clear(); self.output_box.clear()
            for i,d in enumerate(devs):
                name = f"{i}: {d['name']}"
                if d['max_input_channels'] > 0: self.input_box.addItem(name, i)
                if d['max_output_channels'] > 0: self.output_box.addItem(name, i)
        except Exception as e:
            QMessageBox.warning(self, APP_NAME, f"Không đọc được audio device:\n{e}")

    def open_effect(self, name):
        e = self.project["effects"][name]
        if name == "Auto-Tune":
            d=EffectDialog(name,[("Key (A-Z)", "int", 0, 0, 11),("Retune ms","int",e["retune_ms"],1,100),("Humanize %","int",e["humanize"],0,100)],self)
        elif name == "EQ":
            d=EffectDialog(name,[("Center Frequency Hz","double",1000,20,20000),("Gain dB","double",0,-24,24),("Q","double",1,0.1,20)],self)
        elif name == "Compressor":
            d=EffectDialog(name,[("Threshold dB","double",e["threshold"],-60,0),("Ratio","double",e["ratio"],1,20)],self)
        elif name == "De-Esser":
            d=EffectDialog(name,[("Frequency Hz","double",e["frequency"],2000,12000),("Amount %","double",e["amount"],0,100)],self)
        elif name == "Reverb":
            d=EffectDialog(name,[("Mix %","double",e["mix"],0,100),("Decay sec","double",e["decay"],0.1,10)],self)
        elif name == "Delay":
            d=EffectDialog(name,[("Time ms","double",e["time"],1,2000),("Feedback %","double",e["feedback"],0,95),("Mix %","double",e["mix"],0,100)],self)
        elif name == "Noise Reduction":
            d=EffectDialog(name,[("Reduction %","double",e["amount"],0,100)],self)
        else:
            d=EffectDialog(name,[("Ceiling dB","double",e["ceiling"],-12,0)],self)
        d.exec()

    def toggle_live(self, checked):
        self.live.setText("🔴 LIVE ON" if checked else "🔴 LIVE OFF")
        if checked: self.start_audio()
        else: self.stop_audio()

    def start_audio(self):
        if self.audio_stream: return
        try:
            inp = self.input_box.currentData(); out = self.output_box.currentData()
            rate = int(self.rate_box.currentText()); block = int(self.buffer_box.currentText())
            self.frames=[] if self.recording else self.frames
            self.audio_stream = sd.Stream(device=(inp,out), samplerate=rate, blocksize=block,
                                         channels=1, dtype="float32", callback=self.audio_cb)
            self.audio_stream.start()
            self.latency.setText(f"LATENCY: ~{1000*block/rate:.1f} ms/block")
        except Exception as e:
            self.live.setChecked(False); self.live.setText("🔴 LIVE OFF")
            QMessageBox.critical(self, APP_NAME, f"Không mở được audio:\n{e}")

    def stop_audio(self):
        if self.audio_stream:
            try: self.audio_stream.stop(); self.audio_stream.close()
            except: pass
            self.audio_stream=None

    def audio_cb(self, indata, outdata, frames, t, status):
        x = indata[:,0].copy()
        outdata[:,0] = x  # prototype: direct monitoring; effects engine is modularized for next build
        rms = float(np.sqrt(np.mean(x*x))+1e-12)
        if self.recording: self.frames.append(x)
        self.last_rms=rms

    def toggle_record(self, checked):
        if checked:
            if not self.live.isChecked(): self.live.setChecked(True); self.toggle_live(True)
            self.frames=[]; self.recording=True; self.rec.setText("■ STOP REC")
        else:
            self.recording=False; self.rec.setText("● REC")
            self.save_recording()

    def save_recording(self):
        if not self.frames: return
        path,_=QFileDialog.getSaveFileName(self,"Save recording","","WAV (*.wav)")
        if not path: return
        import wave
        x=np.concatenate(self.frames)
        x=np.clip(x,-1,1)
        pcm=(x*32767).astype(np.int16)
        with wave.open(path,"wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(int(self.rate_box.currentText()))
            w.writeframes(pcm.tobytes())
        QMessageBox.information(self,APP_NAME,"Đã lưu bản thu WAV.")

    def play_last(self):
        QMessageBox.information(self,APP_NAME,"Bản prototype ghi WAV. Hãy mở file WAV bằng trình phát của Windows để nghe lại.")

    def new_project(self):
        self.project["name"]="Untitled"; self.project["effects"]["Auto-Tune"]["key"]="AUTO"
        QMessageBox.information(self,APP_NAME,"Đã tạo project mới.")

    def save_project(self):
        path,_=QFileDialog.getSaveFileName(self,"Save project","","HNStudio Project (*.hnstudio.json)")
        if not path: return
        with open(path,"w",encoding="utf-8") as f: json.dump(self.project,f,ensure_ascii=False,indent=2)
        QMessageBox.information(self,APP_NAME,"Đã lưu project.")

    def open_project(self):
        path,_=QFileDialog.getOpenFileName(self,"Open project","","HNStudio Project (*.hnstudio.json)")
        if not path:return
        with open(path,"r",encoding="utf-8") as f:self.project=json.load(f)
        QMessageBox.information(self,APP_NAME,"Đã mở project.")

    def closeEvent(self,e):
        self.stop_audio(); e.accept()

if __name__=="__main__":
    app=QApplication(sys.argv)
    w=MainWindow(); w.show()
    sys.exit(app.exec())
