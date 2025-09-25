import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import serial
import serial.tools.list_ports
import json
import os
from datetime import datetime

class SDR101Controller:
    def __init__(self):
        self.com_port = None
        self.ser = None
        self.current_preset = -1
        self.config_file = "sdr_presets.json"
        self.presets = [self._default_preset_settings() for _ in range(30)]
        self.log_window = None
        self.log_text = None
        self.is_connected = False
        
        self.root = tk.Tk()
        self.root.title("SDR101 control")
        # keep original size used in PureBasic
        self.root.geometry("550x640")
        self.setup_ui()
        self.load_settings()
        self.update_ui_state()
        
    def _default_preset_settings(self):
        return {
            "station_name": "",
            "frequency": "104400K",
            "modulation": "FM",
            "agc": "Средн",
            "speaker_volume": 50,
            "headphone_volume": 50,
            "speaker_mute": False,
            "headphone_mute": False
        }
    
    def setup_ui(self):
        # Увеличиваем размер окна
        self.root.geometry("580x660")  # +30 вправо, +20 вниз
        
        # COM Port section
        self.Text_COM_Port = ttk.Label(self.root, text="COM Порт:")
        self.Text_COM_Port.place(x=60, y=10)
        
        self.Combo_COM_Port = ttk.Combobox(self.root, width=12)
        self.Combo_COM_Port.place(x=140, y=10, width=100, height=25)
        self.create_tooltip(self.Combo_COM_Port, "Выберите COM порт радиоприемника")
        
        self.Button_Connect = ttk.Button(self.root, text="Подключить", command=self.toggle_connection)
        self.Button_Connect.place(x=260, y=10, width=90, height=25)
        self.create_tooltip(self.Button_Connect, "Подключение или отключение порта")
        
        # Frequency display
        self.Text_Frequency_Display = ttk.Label(self.root, text="000.000.000", 
                                              font=("Arial Narrow", 72), anchor="center")
        self.Text_Frequency_Display.place(x=40, y=40, width=450, height=100)
        self.create_tooltip(self.Text_Frequency_Display, "Текущая частота настройки, Гц")
    
        # Frequency unit
        self.Text_Frequency_Unit = ttk.Label(self.root, text="ГЦ", font=("Arial Narrow", 12, "bold"))
        self.Text_Frequency_Unit.place(x=500, y=110, width=25, height=25)
    
        # Presets frame
        self.Frame_Presets = ttk.LabelFrame(self.root, text="Пресеты")
        self.Frame_Presets.place(x=20, y=345, width=540, height=260)  # +30 вправо
    
        # Preset buttons
        self.preset_buttons = []
        frame_x = 0
        frame_y = 355
        for i in range(30):
            orig_x = 40 + (i % 15) * 30
            orig_y = 360 if i < 15 else 390
            x_inside = orig_x - frame_x
            y_inside = orig_y - frame_y
            btn = ttk.Button(self.Frame_Presets, text=f"{i+1:02d}", 
                           command=lambda idx=i: self.preset_button_handler(idx))
            btn.place(x=x_inside, y=y_inside, width=30, height=25)
            self.preset_buttons.append(btn)
    
        # Preset info
        self.Text_Preset_Info = ttk.Label(self.root, text="Выберите настройку", 
                                        font=("Arial Narrow", 11), anchor="center")
        self.Text_Preset_Info.place(x=20, y=140, width=540, height=25)  # +30 вправо
        self.create_tooltip(self.Text_Preset_Info, "Данные о пресете")
    
        # Control frame - расширяем и перемещаем
        self.Frame_Control = ttk.LabelFrame(self.root, text="Управление")
        self.Frame_Control.place(x=20, y=170, width=540, height=175)  # +30 вправо, +20 вниз
        
        # Modulation control
        self.Text_Modulation_Label = ttk.Label(self.Frame_Control, text="Модуляция:")
        self.Text_Modulation_Label.place(x=10, y=5, width=70, height=30)
        
        self.Combo_Modulation = ttk.Combobox(self.Frame_Control, 
                                           values=["AM", "LSB", "USB", "CW", "FM", "Stereo"])
        self.Combo_Modulation.place(x=90, y=5, width=110, height=25)
        self.create_tooltip(self.Combo_Modulation, "Выбор типа модуляции")
        
        # AGC control
        self.Text_AGC_Label = ttk.Label(self.Frame_Control, text="АРУ:")
        self.Text_AGC_Label.place(x=50, y=35, width=30, height=20)
        
        self.Combo_AGC = ttk.Combobox(self.Frame_Control, 
                                    values=["Выкл", "Медл", "Средн", "Быстр"])
        self.Combo_AGC.place(x=90, y=35, width=110, height=25)
        self.create_tooltip(self.Combo_AGC, "Регулировка усиления")
        
        # Speaker control
        self.Text_Speaker_Label = ttk.Label(self.Frame_Control, text="Динамик")
        self.Text_Speaker_Label.place(x=220, y=5, width=60, height=25)
        
        self.TrackBar_Speaker_Volume = ttk.Scale(self.Frame_Control, from_=0, to=100, 
                                               orient="horizontal")
        self.TrackBar_Speaker_Volume.place(x=290, y=5, width=180, height=30)  # +30 вправо
        self.create_tooltip(self.TrackBar_Speaker_Volume, "Громкость динамика")
        
        self.Checkbox_Speaker_Mute = ttk.Checkbutton(self.Frame_Control, text="Выкл")
        self.Checkbox_Speaker_Mute.place(x=480, y=5, width=55, height=25)  # +30 вправо
        self.create_tooltip(self.Checkbox_Speaker_Mute, "Выключить звук динамика")
        
        # Headphone control
        self.Text_Headphone_Label = ttk.Label(self.Frame_Control, text="Наушники")
        self.Text_Headphone_Label.place(x=210, y=35, width=70, height=25)
        
        self.TrackBar_Headphone_Volume = ttk.Scale(self.Frame_Control, from_=0, to=100, 
                                                 orient="horizontal")
        self.TrackBar_Headphone_Volume.place(x=290, y=35, width=180, height=30)  # +30 вправо
        self.create_tooltip(self.TrackBar_Headphone_Volume, "Громкость наушника")
        
        self.Checkbox_Headphone_Mute = ttk.Checkbutton(self.Frame_Control, text="Выкл")
        self.Checkbox_Headphone_Mute.place(x=480, y=35, width=55, height=25)  # +30 вправо
        self.create_tooltip(self.Checkbox_Headphone_Mute, "Выключить звук наушника")
        
        # Frequency control
        self.Text_Frequency_Label = ttk.Label(self.Frame_Control, text="Частота")
        self.Text_Frequency_Label.place(x=10, y=85, width=50, height=25)
        
        self.TrackBar_Frequency = ttk.Scale(self.Frame_Control, from_=100000, to=149000000, 
                                          orient="horizontal")
        self.TrackBar_Frequency.place(x=70, y=65, width=460, height=25)  # +30 вправо
        
        self.String_Frequency_Input_Current = ttk.Entry(self.Frame_Control)
        self.String_Frequency_Input_Current.place(x=70, y=95, width=460, height=25)  # +30 вправо
        self.create_tooltip(self.String_Frequency_Input_Current, "Частота настройки")
        
        self.Button_Send_To_Radio = ttk.Button(self.Frame_Control, text="Отправить", 
                                             command=self.send_to_radio)
        self.Button_Send_To_Radio.place(x=10, y=125, width=520, height=25)  # +30 вправо
        self.create_tooltip(self.Button_Send_To_Radio, "Сохранить значения в радио")
        
        # Preset settings frame - сдвигаем вниз на 20 пикселов
        self.Frame_Preset_Settings = ttk.LabelFrame(self.root, text="Настройка пресета")
        self.Frame_Preset_Settings.place(x=20, y=430, width=540, height=180)  # +30 вправо, +20 вниз
    
        # Speaker volume
        self.Text_Preset_Speaker_Volume_Label = ttk.Label(self.Frame_Preset_Settings, text="Громкость динамика:")
        self.Text_Preset_Speaker_Volume_Label.place(x=10, y=5, width=130, height=25)
        
        self.TrackBar_Preset_Speaker_Volume = ttk.Scale(self.Frame_Preset_Settings, from_=0, to=100, 
                                                      orient="horizontal")
        self.TrackBar_Preset_Speaker_Volume.place(x=150, y=5, width=300, height=25)  # +30 вправо
        self.create_tooltip(self.TrackBar_Preset_Speaker_Volume, "Пресет: Громкость динамика")
        
        self.Checkbox_Preset_Speaker_Mute = ttk.Checkbutton(self.Frame_Preset_Settings, text="Выкл")
        self.Checkbox_Preset_Speaker_Mute.place(x=460, y=5, width=70, height=25)  # +30 вправо
        self.create_tooltip(self.Checkbox_Preset_Speaker_Mute, "Пресет: Выключить динамик")
        
        # Headphone volume
        self.Text_Preset_Headphone_Volume_Label = ttk.Label(self.Frame_Preset_Settings, text="Громкость наушника:")
        self.Text_Preset_Headphone_Volume_Label.place(x=10, y=35, width=130, height=25)
        
        self.TrackBar_Preset_Headphone_Volume = ttk.Scale(self.Frame_Preset_Settings, from_=0, to=100, 
                                                        orient="horizontal")
        self.TrackBar_Preset_Headphone_Volume.place(x=150, y=35, width=300, height=25)  # +30 вправо
        self.create_tooltip(self.TrackBar_Preset_Headphone_Volume, "Пресет: Громкость наушника")
        
        self.Checkbox_Preset_Headphone_Mute = ttk.Checkbutton(self.Frame_Preset_Settings, text="Выкл")
        self.Checkbox_Preset_Headphone_Mute.place(x=460, y=35, width=70, height=25)  # +30 вправо
        self.create_tooltip(self.Checkbox_Preset_Headphone_Mute, "Пресет: Выключить наушник")
        
        # Frequency input
        self.Text_Preset_Frequency_Label = ttk.Label(self.Frame_Preset_Settings, text="Частота:")
        self.Text_Preset_Frequency_Label.place(x=40, y=65, width=80, height=25)
        
        self.String_Preset_Frequency_Input = ttk.Entry(self.Frame_Preset_Settings)
        self.String_Preset_Frequency_Input.place(x=120, y=65, width=280, height=25)  # +30 вправо
        self.create_tooltip(self.String_Preset_Frequency_Input, "Пресет: Частота настройки")
        
        # Modulation
        self.Text_Preset_Modulation_Label = ttk.Label(self.Frame_Preset_Settings, text="Модуляция:")
        self.Text_Preset_Modulation_Label.place(x=40, y=95, width=70, height=30)
        
        self.Combo_Preset_Modulation = ttk.Combobox(self.Frame_Preset_Settings, 
                                                  values=["AM", "LSB", "USB", "CW", "FM", "Stereo"])
        self.Combo_Preset_Modulation.place(x=120, y=95, width=100, height=25)
        self.create_tooltip(self.Combo_Preset_Modulation, "Пресет: Тип модуляции")
        
        # AGC
        self.Text_Preset_AGC_Label = ttk.Label(self.Frame_Preset_Settings, text="АРУ:")
        self.Text_Preset_AGC_Label.place(x=230, y=95, width=30, height=20)
        
        self.Combo_Preset_AGC = ttk.Combobox(self.Frame_Preset_Settings, 
                                           values=["Выкл", "Медл", "Средн", "Быстр"])
        self.Combo_Preset_AGC.place(x=270, y=95, width=100, height=25)
        self.create_tooltip(self.Combo_Preset_AGC, "Пресет: Тип АРУ")
        
        # Station name
        self.Text_Preset_Station_Name_Label = ttk.Label(self.Frame_Preset_Settings, text="Название:")
        self.Text_Preset_Station_Name_Label.place(x=40, y=125, width=70, height=25)
        
        self.String_Preset_Station_Name = ttk.Entry(self.Frame_Preset_Settings)
        self.String_Preset_Station_Name.place(x=120, y=125, width=280, height=25)  # +30 вправо
        self.create_tooltip(self.String_Preset_Station_Name, "Пресет: Название станции")
        
        # Additional settings and Save button
        self.Button_Additional_Settings = ttk.Button(self.Frame_Preset_Settings, text="Дополнительно", state="disabled")
        self.Button_Additional_Settings.place(x=420, y=65, width=100, height=25)  # +20 вправо
        self.create_tooltip(self.Button_Additional_Settings, "Пока не реализовано")
        
        self.Button_Save_Preset = ttk.Button(self.Frame_Preset_Settings, text="Сохранить", 
                                           command=self.save_preset_settings)
        self.Button_Save_Preset.place(x=420, y=95, width=100, height=55)  # +20 вправо
        self.create_tooltip(self.Button_Save_Preset, "Сохранить настройки в пресет")
        
        # Connection status
        self.Text_Connection_Status = ttk.Label(self.root, text="Порт не подключен")
        self.Text_Connection_Status.place(x=400, y=10, width=130, height=25)  # +30 вправо
        
        # Bottom buttons - сдвигаем вниз
        self.Button_About = ttk.Button(self.root, text="О программе", command=self.show_about)
        self.Button_About.place(x=20, y=620, width=100, height=25)  # +20 вниз
        
        self.Button_Terminal = ttk.Button(self.root, text="Терминал", command=self.show_terminal)
        self.Button_Terminal.place(x=130, y=620, width=100, height=25)  # +20 вниз
        
        self.Button_Exit = ttk.Button(self.root, text="Выход", command=self.root.quit)
        self.Button_Exit.place(x=460, y=620, width=100, height=25)  # +30 вправо, +20 вниз
        
        # Bind events
        self.TrackBar_Frequency.bind("<Motion>", self.frequency_trackbar_changed)
        self.String_Frequency_Input_Current.bind("<Return>", self.frequency_input_changed)
        
        self.scan_ports()
    
    def create_tooltip(self, widget, text):
        def enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            label = ttk.Label(tooltip, text=text, background="yellow", relief="solid", borderwidth=1)
            label.pack()
            widget.tooltip = tooltip
        
        def leave(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                delattr(widget, 'tooltip')
        
        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)
    
    def update_ui_state(self):
        """Update UI element states based on connection and preset selection"""
        # keep preset buttons always visible and enabled (like PureBasic layout)
        # Enable/disable control elements based on connection
        connected_state = "normal" if self.is_connected else "disabled"
        control_widgets = [
            self.TrackBar_Speaker_Volume, self.Checkbox_Speaker_Mute,
            self.TrackBar_Headphone_Volume, self.Checkbox_Headphone_Mute,
            self.Combo_AGC, self.Combo_Modulation,
            self.TrackBar_Frequency, self.String_Frequency_Input_Current,
            self.Button_Send_To_Radio
        ]
        for widget in control_widgets:
            widget.config(state=connected_state)
        
        # Preset settings enabled only when a preset is selected
        preset_selected_state = "normal" if self.current_preset != -1 else "disabled"
        preset_widgets = [
            self.TrackBar_Preset_Speaker_Volume, self.Checkbox_Preset_Speaker_Mute,
            self.TrackBar_Preset_Headphone_Volume, self.Checkbox_Preset_Headphone_Mute,
            self.String_Preset_Frequency_Input, self.Combo_Preset_Modulation,
            self.Combo_Preset_AGC, self.String_Preset_Station_Name,
            self.Button_Save_Preset
        ]
        for widget in preset_widgets:
            widget.config(state=preset_selected_state)
        
        # Update connection status
        status_text = "Порт подключен" if self.is_connected else "Порт не подключен"
        self.Text_Connection_Status.config(text=status_text)
        
        # Update connect button text
        self.Button_Connect.config(text="Отключить" if self.is_connected else "Подключить")
    
    def scan_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.Combo_COM_Port['values'] = ports
        if ports:
            self.Combo_COM_Port.set(ports[0])
    
    def load_settings(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for i in range(30):
                        preset_key = f"preset{i+1:02d}"
                        if preset_key in data:
                            self.presets[i].update(data[preset_key])
            except Exception as e:
                print(f"Error loading settings: {e}")
                self.initialize_config()
        else:
            self.initialize_config()
    
    def initialize_config(self):
        data = {}
        for i in range(30):
            data[f"preset{i+1:02d}"] = self._default_preset_settings()
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error initializing config: {e}")
    
    def save_preset_settings(self):
        if self.current_preset == -1:
            messagebox.showerror("Ошибка", "Сначала выберите пресет!")
            return
        
        try:
            frequency = self.String_Preset_Frequency_Input.get()
            # Validate frequency
            freq_hz = self.convert_frequency_to_hz(frequency)
            if not (100000 <= freq_hz <= 149000000):
                raise ValueError("Частота должна быть от 100000 Гц до 149000000 Гц")
            
            self.presets[self.current_preset] = {
                "station_name": self.String_Preset_Station_Name.get(),
                "frequency": frequency,
                "modulation": self.Combo_Preset_Modulation.get(),
                "agc": self.Combo_Preset_AGC.get(),
                "speaker_volume": int(self.TrackBar_Preset_Speaker_Volume.get()),
                "headphone_volume": int(self.TrackBar_Preset_Headphone_Volume.get()),
                "speaker_mute": self.Checkbox_Preset_Speaker_Mute.instate(['selected']),
                "headphone_mute": self.Checkbox_Preset_Headphone_Mute.instate(['selected'])
            }
            
            # Update tooltip for the preset button
            preset = self.presets[self.current_preset]
            tooltip_text = f"{preset['station_name']}\n{preset['frequency']}/{preset['modulation']}"
            self.create_tooltip(self.preset_buttons[self.current_preset], tooltip_text)
            
            data = {}
            for i in range(30):
                data[f"preset{i+1:02d}"] = self.presets[i]
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            messagebox.showinfo("Сохранено", f"Настройки пресета {self.current_preset + 1} сохранены!")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить настройки: {str(e)}")
    
    def preset_button_handler(self, preset_index):
        if self.current_preset == preset_index:
            # Deselect if clicking the same preset
            try:
                self.preset_buttons[self.current_preset].state(['!pressed'])
            except Exception:
                pass
            self.current_preset = -1
            self.Text_Preset_Info.config(text="Выберите настройку")
            self.Text_Frequency_Display.config(text="000.000.000")
        else:
            # Deselect previous preset
            if self.current_preset != -1:
                try:
                    self.preset_buttons[self.current_preset].state(['!pressed'])
                except Exception:
                    pass
            
            # Select new preset
            self.current_preset = preset_index
            try:
                self.preset_buttons[preset_index].state(['pressed'])
            except Exception:
                pass
            self.update_preset_display(preset_index)
            self.apply_preset_settings(preset_index)
        
        self.update_ui_state()
    
    def update_preset_display(self, preset_index):
        preset = self.presets[preset_index]
        
        # Convert frequency to Hz and format with dots
        freq_hz = self.convert_frequency_to_hz(preset["frequency"])
        formatted_freq = self.format_frequency_with_dots(freq_hz)
        self.Text_Frequency_Display.config(text=formatted_freq)
        
        # Update preset info
        info_text = f"{preset['modulation']}, {preset['agc']}, Громкость: {preset['speaker_volume']}"
        self.Text_Preset_Info.config(text=info_text)
        
        # Update preset settings controls
        self.String_Preset_Station_Name.delete(0, tk.END)
        self.String_Preset_Station_Name.insert(0, preset["station_name"])
        
        self.String_Preset_Frequency_Input.delete(0, tk.END)
        self.String_Preset_Frequency_INPUT_val = preset["frequency"]
        self.String_Preset_Frequency_Input.insert(0, preset["frequency"])
        
        self.Combo_Preset_Modulation.set(preset["modulation"])
        self.Combo_Preset_AGC.set(preset["agc"])
        
        self.TrackBar_Preset_Speaker_Volume.set(preset["speaker_volume"])
        self.TrackBar_Preset_Headphone_Volume.set(preset["headphone_volume"])
        
        if preset["speaker_mute"]:
            self.Checkbox_Preset_Speaker_Mute.state(['selected'])
        else:
            self.Checkbox_Preset_Speaker_Mute.state(['!selected'])
        
        if preset["headphone_mute"]:
            self.Checkbox_Preset_Headphone_Mute.state(['selected'])
        else:
            self.Checkbox_Preset_Headphone_Mute.state(['!selected'])
    
    def apply_preset_settings(self, preset_index):
        if not self.is_connected:
            # do not send commands when not connected, but still update UI
            return
        
        preset = self.presets[preset_index]
        
        try:
            # Apply frequency
            freq_hz = self.convert_frequency_to_hz(preset["frequency"])
            self.send_command(f"tune {freq_hz}")
            
            # Apply modulation
            mod_cmd = self.convert_modulation_to_command(preset["modulation"])
            self.send_command(f"mode {mod_cmd}")
            
            # Apply AGC
            agc_cmd = self.convert_agc_to_command(preset["agc"])
            self.send_command(f"agc {agc_cmd}")
            
            # Apply volumes
            self.send_command(f"volume {preset['speaker_volume']}")
            
            # Apply mute states
            spk_cmd = "spk 0" if preset["speaker_mute"] else "spk 1"
            self.send_command(spk_cmd)
            
            # Update current controls to match preset
            self.TrackBar_Frequency.set(freq_hz)
            self.String_Frequency_Input_Current.delete(0, tk.END)
            self.String_Frequency_Input_Current.insert(0, preset["frequency"])
            
            self.Combo_Modulation.set(preset["modulation"])
            self.Combo_AGC.set(preset["agc"])
            
            self.TrackBar_Speaker_Volume.set(preset["speaker_volume"])
            self.TrackBar_Headphone_Volume.set(preset["headphone_volume"])
            
            if preset["speaker_mute"]:
                self.Checkbox_Speaker_Mute.state(['selected'])
            else:
                self.Checkbox_Speaker_Mute.state(['!selected'])
            
            if preset["headphone_mute"]:
                self.Checkbox_Headphone_Mute.state(['selected'])
            else:
                self.Checkbox_Headphone_Mute.state(['!selected'])
            
        except Exception as e:
            self.log_message(f"Error applying preset: {str(e)}")
    
    def convert_frequency_to_hz(self, frequency):
        # Accept both comma and dot as decimal separator
        freq = frequency.upper().strip().replace(',', '.')
        multiplier = 1
        
        if freq.endswith('K'):
            multiplier = 1000
            freq = freq[:-1]
        elif freq.endswith('M'):
            multiplier = 1000000
            freq = freq[:-1]
        
        # protect against empty or invalid strings
        try:
            return int(float(freq) * multiplier)
        except Exception:
            raise ValueError(f"Неверный формат частоты: '{frequency}'")
    
    def format_frequency_with_dots(self, freq_hz):
        """Format frequency with dots every 3 digits"""
        freq_str = str(freq_hz)
        parts = []
        while freq_str:
            parts.append(freq_str[-3:])
            freq_str = freq_str[:-3]
        return '.'.join(reversed(parts))
    
    def convert_modulation_to_command(self, modulation):
        mod_map = {
            "AM": "am", "LSB": "lsb", "USB": "usb",
            "CW": "cw", "FM": "wfm", "STEREO": "ste"
        }
        return mod_map.get(modulation.upper(), "am")
    
    def convert_agc_to_command(self, agc):
        agc_map = {
            "Выкл": "disable", "Медл": "slow", 
            "Средн": "mid", "Быстр": "fast"
        }
        return agc_map.get(agc, "mid")
    
    def frequency_trackbar_changed(self, event):
        """Handle frequency trackbar changes"""
        freq_hz = int(self.TrackBar_Frequency.get())
        formatted_freq = self.format_frequency_with_dots(freq_hz)
        self.Text_Frequency_Display.config(text=formatted_freq)
        
        # Convert to appropriate unit for display (use dot as decimal separator internally)
        if freq_hz >= 1000000:
            display_freq = f"{freq_hz/1000000:.3f}M"
        else:
            display_freq = f"{freq_hz/1000:.0f}K"
        
        self.String_Frequency_Input_Current.delete(0, tk.END)
        self.String_Frequency_Input_CURRENT_val = display_freq
        self.String_Frequency_Input_Current.insert(0, display_freq)
    
    def frequency_input_changed(self, event):
        """Handle frequency input changes"""
        try:
            frequency = self.String_Frequency_Input_Current.get()
            freq_hz = self.convert_frequency_to_hz(frequency)
            
            if not (100000 <= freq_hz <= 149000000):
                raise ValueError("Частота должна быть от 100000 Гц до 149000000 Гц")
            
            self.TrackBar_Frequency.set(freq_hz)
            formatted_freq = self.format_frequency_with_dots(freq_hz)
            self.Text_Frequency_Display.config(text=formatted_freq)
            
        except ValueError as e:
            messagebox.showerror("Ошибка", str(e))
    
    def send_to_radio(self):
        """Send current control values to radio"""
        if not self.is_connected:
            messagebox.showerror("Ошибка", "Порт не подключен!")
            return
        
        try:
            frequency = self.String_Frequency_Input_Current.get()
            freq_hz = self.convert_frequency_to_hz(frequency)
            
            if not (100000 <= freq_hz <= 149000000):
                raise ValueError("Частота должна быть от 100000 Гц до 149000000 Гц")
            
            # Send frequency
            self.send_command(f"tune {freq_hz}")
            
            # Send modulation
            mod_cmd = self.convert_modulation_to_command(self.Combo_Modulation.get())
            self.send_command(f"mode {mod_cmd}")
            
            # Send AGC
            agc_cmd = self.convert_agc_to_command(self.Combo_AGC.get())
            self.send_command(f"agc {agc_cmd}")
            
            # Send volumes
            self.send_command(f"volume {int(self.TrackBar_Speaker_Volume.get())}")
            
            # Send mute states
            spk_mute = self.Checkbox_Speaker_Mute.instate(['selected'])
            self.send_command("spk 0" if spk_mute else "spk 1")
            
            messagebox.showinfo("Успех", "Параметры отправлены на радио")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка отправки: {str(e)}")
    
    def send_command(self, command):
        """Send command to serial port and log it"""
        if not self.ser or not self.ser.is_open:
            return False
        
        try:
            # Log command
            self.log_message(f">>> {command}")
            
            # Clear buffer
            self.ser.reset_input_buffer()
            
            # Send command
            full_command = command + '\r\n'
            self.ser.write(full_command.encode())
            
            # Read response
            self.root.after(300)
            if self.ser.in_waiting > 0:
                response = self.ser.read(self.ser.in_waiting).decode(errors='ignore')
                self.log_message(f"<<< {response.strip()}")
            
            return True
        except Exception as e:
            self.log_message(f"ERROR: {str(e)}")
            return False

    
    def log_message(self, message):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)
        
        # Check if terminal window and text widget still exist
        if (self.log_text and 
            self.log_window and 
            self.log_window.winfo_exists() and 
            tk.Toplevel.winfo_exists(self.log_window)):
            try:
                self.log_text.insert(tk.END, log_entry + "\n")
                self.log_text.see(tk.END)
            except tk.TclError:
                # Widget was destroyed, clean up references
                self.log_text = None
                self.log_window = None
        else:
            # Clean up references if window doesn't exist
            self.log_text = None
            self.log_window = None

    def wake_up_device(self):
        """Wake up the SDR device"""
        if not self.ser:
            return False
        
        for _ in range(5):
            try:
                self.ser.write(b'\r')
                self.root.after(200)
                
                if self.ser.in_waiting > 0:
                    response = self.ser.read(self.ser.in_waiting).decode(errors='ignore')
                    if "ch>" in response:
                        return True
            except:
                pass
        
        return False
    
    def toggle_connection(self):
        """Toggle COM port connection"""
        if self.is_connected:
            self.disconnect_comport()
        else:
            self.connect_comport()
    
    def connect_comport(self):
        port = self.Combo_COM_Port.get()
        if not port:
            messagebox.showerror("Ошибка", "Выберите COM порт!")
            return
        
        try:
            self.ser = serial.Serial(port, 9600, timeout=1)
            self.root.after(2000)  # Wait for device initialization
            
            if not self.wake_up_device():
                messagebox.showwarning("Предупреждение", "Устройство не ответило")
            
            self.is_connected = True
            self.update_ui_state()
            self.log_message(f"Подключен к порту {port}")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось подключиться к порту: {str(e)}")
            self.log_message(f"Ошибка подключения: {str(e)}")
    
    def disconnect_comport(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
        
        self.ser = None
        self.is_connected = False
        self.current_preset = -1
        
        # Reset preset buttons visual state
        for btn in self.preset_buttons:
            try:
                btn.state(['!pressed'])
            except Exception:
                pass
        
        self.update_ui_state()
        self.log_message("Порт отключен")
    
    def show_terminal(self):
        """Show terminal window with communication log"""
        if self.log_window and self.log_window.winfo_exists():
            self.log_window.lift()
            return
        
        self.log_window = tk.Toplevel(self.root)
        self.log_window.title("Терминал SDR101")
        self.log_window.geometry("600x400")
        
        # Handle window close properly
        def on_close():
            self.log_text = None
            self.log_window.destroy()
        
        self.log_window.protocol("WM_DELETE_WINDOW", on_close)
        
        self.log_text = scrolledtext.ScrolledText(self.log_window, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        clear_btn = ttk.Button(self.log_window, text="Очистить", 
                             command=lambda: self.log_text.delete(1.0, tk.END))
        clear_btn.pack(pady=5)
        
        self.log_message("Терминал запущен")
    
    
    def show_about(self):
        """Show about dialog"""
        messagebox.showinfo("О программе", 
                          "SDR101 Controller v1.0\n\n"
                          "Программа для управления SDR приемником SDR101")
    
    def run(self):
        self.root.mainloop()
        if self.ser and self.ser.is_open:
            self.ser.close()

if __name__ == "__main__":
    app = SDR101Controller()
    app.run()
