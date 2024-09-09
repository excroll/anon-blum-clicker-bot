import pyautogui
import cv2
import numpy as np
import concurrent.futures
import time
from pynput import keyboard as kb
from pynput.mouse import Button, Controller, Listener
import pygetwindow as gw
import tkinter as tk
from tkinter import simpledialog, messagebox, scrolledtext
from tkinter import ttk
import threading
from PIL import Image, ImageTk
import configparser
import os, sys
from threading import Event
import random
import re
import datetime
import math
from PIL import ImageGrab
from queue import Queue
from pynput import keyboard, mouse
import shutil
import subprocess
import psutil
import atexit

class BotBase:
    def __init__(self, log_widget, window_name, collecting_bounds, star_templates, star_ship):
        self.mouse = Controller()
        self.collecting_resources = True
        self.ship_position = None
        self.ship_template_size = None
        self.mouse_position = (0, 0)
        self.paused = True
        self.running = Event()
        self.log_widget = log_widget
        self.window_name = window_name
        self.collecting_bounds = collecting_bounds
        self.star_templates = star_templates
        self.star_ship = star_ship
        self.listener = None
        self.bot_thread = None

        config = configparser.ConfigParser()
        config.read('file.ini')

        self.width = '1920'
        self.height = '1080'

        self.resolutionemu960 = False
        self.resolutionemu1600 = True

        # Инициализация строки для текущей энергии
        self.log_widget.tag_configure("energy", foreground="green")
        self.log_widget.insert(tk.END, "Current energy: 0\n", "energy")
        self.backup_config_file()

    def log_message(self, message, bot_name=None, tag=None):
        self.log_widget.config(state='normal')

        if bot_name:
            start_index = message.find(bot_name)
            end_index = start_index + len(bot_name)

            # Вставляем текст до bot_name
            self.log_widget.insert(tk.END, message[:start_index])

            # Вставляем bot_name с тегом
            self.log_widget.insert(tk.END, bot_name, "bot_name_tag")

            # Вставляем текст после bot_name
            self.log_widget.insert(tk.END, message[end_index:])

            self.log_widget.insert(tk.END, "\n")
        else:
            self.log_widget.insert(tk.END, message + "\n")

        self.log_widget.see(tk.END)
        self.log_widget.config(state='disabled')

    def log_message_name(self, bot_name):
        self.log_widget.tag_configure("bot_name_tag", foreground="white")
        return f"{bot_name}"

    def backup_config_file(self):
        if os.path.exists('file.ini') and os.path.getsize('file.ini') > 0:
            shutil.copy('file.ini', 'save.ini')

    def restart_bot(self):
        def on_closing():
            self.stop_bot()
            root.destroy()
            # Завершение всех дочерних процессов
            for proc in psutil.process_iter():
                if proc.pid != os.getpid() and proc.ppid() == os.getpid():
                    proc.terminate()
            os._exit(0)  # Принудительно завершить все потоки

        # Привязка обработчика закрытия окна
        root.protocol("WM_DELETE_WINDOW", on_closing)

        # Запуск .bat файла для перезапуска с скрытой консолью
        subprocess.Popen(['restart.bat'], creationflags=subprocess.CREATE_NO_WINDOW)
        # Вызов обработчика закрытия окна
        on_closing()

        # Привязка обработчика закрытия окна
        root.protocol("WM_DELETE_WINDOW", on_closing)

        # Запуск .bat файла для перезапуска
        subprocess.Popen(['restart.bat'])
        # Вызов обработчика закрытия окна
        on_closing()


    def log_full_clicked(self, message, profileIndex, bot_name=None):
        self.log_widget.config(state='normal')

        if bot_name:
            # Найти индексы bot_name и profileIndex в сообщении
            start_index_bot_name = message.find(bot_name)
            end_index_bot_name = start_index_bot_name + len(bot_name)

            start_index_profile = message.find(f"[{profileIndex}]")
            end_index_profile = start_index_profile + len(f"[{profileIndex}]")

            # Вставляем текст до profileIndex
            self.log_widget.insert(tk.END, message[:start_index_profile])

            # Вставляем profileIndex с тегом
            self.log_widget.insert(tk.END, f"[{profileIndex}]", "profile_index_tag")

            # Вставляем текст между profileIndex и bot_name
            self.log_widget.insert(tk.END, message[end_index_profile:start_index_bot_name])

            # Вставляем bot_name с тегом
            self.log_widget.insert(tk.END, bot_name, "bot_name_tag")

            # Вставляем текст после bot_name
            self.log_widget.insert(tk.END, message[end_index_bot_name:])

            self.log_widget.insert(tk.END, "\n")
        else:
            self.log_widget.insert(tk.END, message + "\n")

        self.log_widget.see(tk.END)
        self.log_widget.config(state='disabled')

        # Настройка тегов
        self.log_widget.tag_configure("bot_name_tag", foreground="white")
        self.log_widget.tag_configure("profile_index_tag", foreground="white")

    def update_energy_display(self):
        self.log_widget.config(state='normal')
        # Удаляем предыдущую строку с текущей энергией
        self.log_widget.delete("end-2l", "end-1l")
        # Вставляем новую строку с текущей энергией
        self.log_widget.insert(tk.END, f"Current energy: {self.current_energy[self.profile]}\n", "energy")
        self.log_widget.config(state='disabled')
        self.log_widget.see(tk.END)  # Прокручиваем до конца

    def on_click(self, x, y, button, pressed):
        if button == Button.left:
            self.collecting_resources = not pressed
            if pressed:
                self.running.clear()  # Приостановить сбор ресурсов при нажатии ЛКМ
            else:
                self.running.set()  # Возобновить сбор ресурсов при отпускании ЛКМ
                if self.ship_position:
                    # Переместить курсор на центр корабля при отпускании левой кнопки мыши
                    self.mouse.position = (self.ship_position[0], self.ship_position[1])
                    self.mouse_position = self.mouse.position

    def on_move(self, x, y):
        if self.ship_position:
            # Обновляем только координату X
            self.mouse_position = (x, self.ship_position[1])

    def get_window(self, window):
        windows = pyautogui.getWindowsWithTitle(window)
        if windows:
            window = windows[0]
            region_left = window.left
            region_top = window.top
            region_width = window.width
            region_height = window.height
            return region_left, region_top, region_width, region_height
        else:
            raise Exception(f"Window '{window}' not found.")

    def click(self, xs, ys):
        self.mouse.position = (xs, ys)
        self.mouse.press(Button.left)
        self.mouse.release(Button.left)
        time.sleep(0.4)

    def clickBlum(self, xs, ys):
        self.mouse.position = (xs, ys)
        self.mouse.press(Button.left)
        self.mouse.release(Button.left)
        time.sleep(random.uniform(self.delaymin, self.delaymax))

    def clickerClick(self, xs, ys):
        self.mouse.position = (xs, ys)
        self.mouse.press(Button.left)
        self.mouse.release(Button.left)

    # def clickTwoFingers(self, xs, ys):
    #     # Первый клик
    #     self.mouse.position = (xs, ys)
    #     self.mouse.press(Button.left)
    #     self.mouse.release(Button.left)

    #     # Второй клик на расстоянии 30 пикселей
    #     self.mouse.position = (xs + 30, ys)
    #     self.mouse.press(Button.left)
    #     self.mouse.release(Button.left)

    def click_with_movement(self, start_x, start_y, end_x, end_y, steps=12):
        def generate_control_points(start_x, start_y, end_x, end_y):
            return [
                (start_x, start_y),
                (start_x + random.uniform(-50, 50), start_y + random.uniform(-50, 50)),
                (start_x + random.uniform(-50, 50), start_y + random.uniform(-50, 50)),
                (end_x + random.uniform(-50, 50), end_y + random.uniform(-50, 50)),
                (end_x, end_y)
            ]

        def bezier_curve(t, points):
            n = len(points) - 1
            return sum(
                (math.comb(n, i) * (1 - t) ** (n - i) * t ** i * np.array(point) for i, point in enumerate(points))
            )

        def bezier_curve_reverse(t, points):
            n = len(points) - 1
            return sum(
                (math.comb(n, i) * (1 - t) ** i * t ** (n - i) * np.array(point) for i, point in enumerate(points))
            )

        def move_to_curved(start_x, start_y, end_x, end_y, steps, click_speeds):
            control_points = generate_control_points(start_x, start_y, end_x, end_y)
            for i in range(steps):
                if self.current_energy[self.profile] < self.energy_per_click[self.profile]:
                    return  # Прекращаем выполнение, если недостаточно энергии
                t = i / (steps - 1)
                x, y = bezier_curve(t, control_points)
                x += random.uniform(-2, 2)
                y += random.uniform(-2, 2)
                self.mouse.position = (x, y)
                self.mouse.press(Button.left)
                self.mouse.release(Button.left)
                self.current_energy[self.profile] -= self.energy_per_click[self.profile]
                self.save_profile_settings(self.profile)  # Сохранение текущей энергии в файл после каждого клика
                speed = random.choice(['fast', 'medium', 'slow'])
                min_delay, max_delay = click_speeds[speed]
                time.sleep(random.uniform(min_delay, max_delay))  # Случайная задержка для имитации движения

        last_stop_time = 0

        control_points = generate_control_points(start_x, start_y, end_x, end_y)

        for i in range(steps):
            if self.current_energy[self.profile] < self.energy_per_click[self.profile]:
                return  # Прекращаем выполнение, если недостаточно энергии
            t = i / (steps - 1)
            x, y = bezier_curve(t, control_points)
            x += random.uniform(-2, 2)
            y += random.uniform(-2, 2)
            self.mouse.position = (x, y)
            time.sleep(random.uniform(0.01, 0.03))  # Случайная задержка для имитации движения

        # Клик в конечной точке
        if self.current_energy[self.profile] < self.energy_per_click[self.profile]:
            return  # Прекращаем выполнение, если недостаточно энергии
        self.mouse.press(Button.left)
        self.mouse.release(Button.left)
        self.current_energy[self.profile] -= self.energy_per_click[self.profile]
        self.save_profile_settings(self.profile)
        time.sleep(random.uniform(0.02, 0.05))  # Случайная задержка перед следующим кликом

        # Случайное количество кликов (1, 2 или 3)
        num_clicks = random.choice([1])

        # Случайная скорость кликов (быстрая, средняя, медленная)
        click_speeds = {
            'fast': (0.1, 0.13),
            'medium': (0.13, 0.15),
            'slow': (0.15, 0.2)
        }

        # Время для ускорения и замедления
        acceleration_time = random.uniform(2, 4)  # Время ускорения в секундах
        deceleration_time = random.uniform(1, 3)  # Время замедления в секундах
        start_time = time.time()

        while time.time() - start_time < acceleration_time + deceleration_time:
            if not self.running.is_set() or self.paused or self.current_energy[self.profile] < self.energy_per_click[
                self.profile]:
                return  # Прекращаем выполнение, если бот приостановлен, остановлен или недостаточно энергии

            # Случайная остановка
            if time.time() - last_stop_time > 10 and random.random() < 0.01:  # 1% шанс остановки
                stop_duration = random.uniform(3, 7)
                time.sleep(stop_duration)
                last_stop_time = time.time()

            if time.time() - start_time < acceleration_time:
                # Ускорение
                speed = 'fast'
            else:
                # Замедление
                speed = random.choice(['medium', 'slow'])

            min_delay, max_delay = click_speeds[speed]

            for _ in range(num_clicks):
                if self.current_energy[self.profile] < self.energy_per_click[self.profile]:
                    return  # Прекращаем выполнение, если недостаточно энергии

                # Выбор между кривой Безье, обратной кривой Безье и изогнутой прямой
                movement_type = random.choices(
                    ['bezier', 'reverse_bezier', 'curved'],
                    weights=[0.1, 0.1, 0.1],  # Уменьшаем вероятность движения по изогнутой прямой
                    k=1
                )[0]

                if movement_type == 'reverse_bezier':
                    control_points = generate_control_points(start_x, start_y, end_x, end_y)
                    for i in range(steps):
                        if self.current_energy[self.profile] < self.energy_per_click[self.profile]:
                            return  # Прекращаем выполнение, если недостаточно энергии
                        t = i / (steps - 1)
                        x, y = bezier_curve_reverse(t, control_points)
                        x += random.uniform(-2, 2)
                        y += random.uniform(-2, 2)
                        self.mouse.position = (x, y)
                        self.mouse.press(Button.left)
                        self.mouse.release(Button.left)
                        self.current_energy[self.profile] -= self.energy_per_click[self.profile]
                        self.save_profile_settings(
                            self.profile)  # Сохранение текущей энергии в файл после каждого клика
                        speed = random.choice(['fast', 'medium', 'slow'])
                        min_delay, max_delay = click_speeds[speed]
                        time.sleep(random.uniform(min_delay, max_delay))  # Случайная задержка для имитации движения
                elif movement_type == 'curved':
                    move_to_curved(x, y, end_x, end_y, steps, click_speeds)
                else:
                    rand_x = random.randint(34, 42)
                    rand_y = random.randint(-5, 5)
                    self.mouse.position = (x + rand_x, y + rand_y)
                    self.mouse.press(Button.left)
                    self.mouse.release(Button.left)
                    self.current_energy[self.profile] -= self.energy_per_click[self.profile]
                    self.save_profile_settings(self.profile)
                    time.sleep(random.uniform(min_delay, max_delay))  # Случайная задержка перед следующим кликом

            # Обновление позиции мыши для следующего цикла
            x += random.uniform(-2, 2)
            y += random.uniform(-2, 2)

            # Вычитание энергии с учетом количества кликов
            self.current_energy[self.profile] -= self.energy_per_click[self.profile] * num_clicks
            self.update_energy_display()
            self.save_profile_settings(self.profile)


    def choose_window_gui(self):
        root = tk.Tk()
        root.withdraw()

        windows = gw.getAllTitles()
        if not windows:
            return None

        choice = simpledialog.askstring("Selecting the PLAY window", "Enter the window number:\n" + "\n".join(
            f"{i}: {window}" for i, window in enumerate(windows)))

        if choice is None or not choice.isdigit():
            return None

        choice = int(choice)
        if 0 <= choice < len(windows):
            return windows[choice]
        else:
            return None

    def grab_screen(self, region, scale_factor=0.5):
        screenshot = pyautogui.screenshot(region=region)
        screenshot = np.array(screenshot)
        screenshot = cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)
        new_width = int(screenshot.shape[1] * scale_factor)
        new_height = int(screenshot.shape[0] * scale_factor)
        resized_screenshot = cv2.resize(screenshot, (new_width, new_height))
        return resized_screenshot

    def find_template_on_screen(self, template, screenshot, step=0.7, scale_factor=0.5):
        new_width = int(template.shape[1] * scale_factor)
        new_height = int(template.shape[0] * scale_factor)
        resized_template = cv2.resize(template, (new_width, new_height))

        # Проверка размеров шаблона и изображения
        if resized_template.shape[0] > screenshot.shape[0] or resized_template.shape[1] > screenshot.shape[1]:
            self.log_message(f"No focus in play window!\nChoose {self.window_name} and restart bot")
            return None

        result = cv2.matchTemplate(screenshot, resized_template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        if max_val >= step:
            return (int(max_loc[0] / scale_factor), int(max_loc[1] / scale_factor))
        return None


    def click_on_screen(self, position, template_width, template_height, region_left, region_top):
        center_x = position[0] + template_width // 2
        center_y = position[1] + template_height // 2

        # Проверка, находится ли клик в пределах заданных границ
        if (self.collecting_bounds[0] <= center_x <= self.collecting_bounds[2] and
            self.collecting_bounds[1] <= center_y <= self.collecting_bounds[3]):
            if notebook.index(notebook.select()) == 0:
                self.click(center_x + region_left, center_y + region_top + 4)
            elif notebook.index(notebook.select()) == 1:
                self.clickBlum(center_x + region_left, center_y + region_top + 4)
            elif notebook.index(notebook.select()) == 2:
                self.clickerClick(center_x + region_left, center_y + region_top + 4)
        # else:
        #     self.log_message(f"Click out of bounds: ({center_x}, {center_y})")

    def process_template(self, template_data, screenshot, scale_factor, region_left, region_top, avoid=False):
        template_name, template = template_data
        if template is None:
            self.log_message(f"Error load template {template_name}")
            return template_name, None
        position = self.find_template_on_screen(template, screenshot, scale_factor=scale_factor)
        if position:
            template_height, template_width, _ = template.shape
            if avoid:
                return position
            else:
                self.click_on_screen(position, template_width, template_height, region_left, region_top)
                return template_name, position
        return template_name, None


    def start_bot(self):
        if not self.running.is_set():
            self.running.set()
            self.paused = False
            self.bot_thread = threading.Thread(target=self.bot_loop)
            self.bot_thread.start()
        else:
            self.paused = False
        self.log_message("Bot RUN")

    def pause_bot(self):
        self.paused = True
        self.log_message("Bot PAUSE")

    def stop_bot(self):
        self.paused = True
        self.running.clear()
        self.log_message("Bot STOP")

    def update_window_name(self, window_name_entry):
        self.window_name = window_name_entry.get()
        self.log_message(f"Window name updated to: {self.window_name}")

        if notebook.index(notebook.select()) == 0:
            # Обновление значения в файле ini
            config = configparser.ConfigParser()
            config.read('file.ini')
            config['Window']['name'] = self.window_name
            with open('file.ini', 'w') as configfile:
                config.write(configfile)
        elif notebook.index(notebook.select()) == 1:
            # Обновление значения в файле ini
            config = configparser.ConfigParser()
            config.read('file.ini')
            config['WindowBlum']['name'] = self.window_name
            with open('file.ini', 'w') as configfile:
                config.write(configfile)
        elif notebook.index(notebook.select()) == 3:
            # Обновление значения в файле ini
            config = configparser.ConfigParser()
            config.read('file.ini')
            config['WindowClicker']['name'] = self.window_name
            with open('file.ini', 'w') as configfile:
                config.write(configfile)

    def update_cipher(self, window_name_entry):
        self.window_name = window_name_entry.get()
        self.log_message(f"Cipher name updated to: {self.window_name}")
        # Обновление значения в файле ini
        config = configparser.ConfigParser()
        config.read('file.ini')
        config['CipherBot']['cipher'] = self.window_name
        with open('file.ini', 'w') as configfile:
            config.write(configfile)

    def open_config_window(self):
        config_window = tk.Toplevel(root)
        config_window.title("Config")
        config_window.resizable(False, False)

        bounds_frame = tk.Frame(config_window, bg="dark gray")
        bounds_frame.pack(pady=10, padx=10)

        # Поля ввода для collecting_bounds
        left_label = tk.Label(bounds_frame, text="Left:", bg="white")
        left_label.grid(row=0, column=0, padx=2, pady=2, sticky="w")
        left_entry = tk.Entry(bounds_frame)
        left_entry.insert(0, self.collecting_bounds[0])
        left_entry.grid(row=0, column=1, padx=2, pady=2, sticky="w")

        top_label = tk.Label(bounds_frame, text="Top:", bg="white")
        top_label.grid(row=0, column=2, padx=2, pady=2, sticky="w")
        top_entry = tk.Entry(bounds_frame)
        top_entry.insert(0, self.collecting_bounds[1])
        top_entry.grid(row=0, column=3, padx=2, pady=2, sticky="w")

        right_label = tk.Label(bounds_frame, text="Right:", bg="white")
        right_label.grid(row=1, column=0, padx=2, pady=2, sticky="w")
        right_entry = tk.Entry(bounds_frame)
        right_entry.insert(0, self.collecting_bounds[2])
        right_entry.grid(row=1, column=1, padx=2, pady=2, sticky="w")

        bottom_label = tk.Label(bounds_frame, text="Bottom:", bg="white")
        bottom_label.grid(row=1, column=2, padx=2, pady=2, sticky="w")
        bottom_entry = tk.Entry(bounds_frame)
        bottom_entry.insert(0, self.collecting_bounds[3])
        bottom_entry.grid(row=1, column=3, padx=2, pady=2, sticky="w")

        # Кнопка для применения collecting_bounds
        apply_bounds_button = tk.Button(bounds_frame, text="Save",
                                        command=lambda: self.update_collecting_bounds(left_entry, top_entry,
                                                                                      right_entry, bottom_entry))
        apply_bounds_button.grid(row=2, column=0, columnspan=4, pady=5)

        # Кнопка для автоматического вычисления размеров окна
        auto_bounds_button = tk.Button(bounds_frame, text="Auto Update Bounds")
        auto_bounds_button.grid(row=3, column=0, columnspan=4, pady=5)

        # Добавление кнопки для выделения области
        highlight_button = tk.Button(bounds_frame, text="Show Clicker Frame", command=self.highlight_collecting_bounds)
        highlight_button.grid(row=4, column=0, columnspan=4, pady=5)

        # Новая секция для ввода значений разрешения экрана
        settings_frame5 = tk.Frame(config_window, bg="gray")
        settings_frame5.pack(pady=(10, 0), padx=10)

        resolution_section_label = tk.Label(settings_frame5, text="Display Resolution", bg="dark gray",
                                            font=("Arial", 10, "bold"))
        resolution_section_label.grid(row=0, column=0, columnspan=2, pady=0)

        settings_frame51 = tk.Frame(config_window, bg="gray")
        settings_frame51.pack(pady=2, padx=10)

        height_label = tk.Label(settings_frame51, text="Height:", bg="white")
        height_label.grid(row=2, column=0, padx=2, pady=2, sticky="w")
        height_entry = tk.Entry(settings_frame51, width=10)
        height_entry.insert(0, self.height)
        height_entry.grid(row=2, column=1, padx=2, pady=10, sticky="w")

        width_label = tk.Label(settings_frame51, text="Width:", bg="white")
        width_label.grid(row=1, column=0, padx=2, pady=2, sticky="w")
        width_entry = tk.Entry(settings_frame51, width=10)
        width_entry.insert(0, self.width)
        width_entry.grid(row=1, column=1, padx=2, pady=10, sticky="w")

        settings_frame61 = tk.Frame(config_window, bg="gray")
        settings_frame61.pack(pady=2, padx=10)

        # Кнопки для переключения разрешений
        resolution_frame71 = tk.Frame(config_window, bg="gray")
        resolution_frame71.pack(pady=(5, 2), padx=10)

        resolution_frame_label = tk.Label(resolution_frame71, text="Emulator Resolution", bg="dark gray",
                                          font=("Arial", 10, "bold"))
        resolution_frame_label.grid(row=0, column=0, columnspan=2, pady=0)

        resolution_frame = tk.Frame(config_window, bg="gray")
        resolution_frame.pack(pady=0, padx=10)

        resolution960_button = tk.Button(resolution_frame, text="960x540",
                                         bg="dark gray" if self.resolutionemu960 else "light gray",
                                         command=lambda: self.toggle_resolution('960x540', resolution960_button,
                                                                                resolution1600_button))
        resolution960_button.grid(row=0, column=0, padx=5, pady=5)

        resolution1600_button = tk.Button(resolution_frame, text="1600x900",
                                          bg="dark gray" if self.resolutionemu1600 else "light gray",
                                          command=lambda: self.toggle_resolution('1600x900', resolution960_button,
                                                                                 resolution1600_button))
        resolution1600_button.grid(row=0, column=1, padx=5, pady=5)

        # Кнопка для сохранения значений из SettingsClicker
        save_settings_button = tk.Button(settings_frame61, text="Save",
                                         command=lambda: self.update_settings_values_display(height_entry, width_entry))
        save_settings_button.grid(row=5, column=0, columnspan=2, pady=5, padx=5)

    def copy_to_clipboard(self):
        root.clipboard_clear()
        root.clipboard_append("UQBKm1osfi6A721M_iGjB9sMz-Far0vv4e8i5HXC2HXUFI2n")
        root.update()  # now it stays on the clipboard after the window is closed
        self.log_message("Wallet copied!")

    def update_settings_values_display(self,  height_entry, width_entry):
        self.height = int(height_entry.get())
        self.width = int(width_entry.get())
        self.log_message(f"Settings values updated:  width={self.width}, height={self.height}")
        # Обновление значений в файле ini
        config = configparser.ConfigParser()
        config.read('file.ini')
        config['DisplaySetting'] = {
            'height': str(self.height),
            'width': str(self.width),
            'resolutionemu960': str(self.resolutionemu960),
            'resolutionemu1600': str(self.resolutionemu1600),
        }
        with open('file.ini', 'w') as configfile:
            config.write(configfile)

    def toggle_resolution(self, resolution, button960, button1600):
        if resolution == '960x540':
            self.resolutionemu960 = True
            self.resolutionemu1600 = False
            button960.config(bg="dark gray")
            button1600.config(bg="light gray")
        elif resolution == '1600x900':
            self.resolutionemu960 = False
            self.resolutionemu1600 = True
            button960.config(bg="light gray")
            button1600.config(bg="dark gray")
        self.update_resolution(resolution)

    def update_resolution(self, resolution):
        config = configparser.ConfigParser()
        config.read('file.ini')
        if self.resolutionemu960 == True:
            self.resolutionemu1600 = False
        elif self.resolutionemu1600 == True:
            self.resolutionemu960 = False
        config.set('DisplaySetting', 'resolutionemu960', str(self.resolutionemu960))
        config.set('DisplaySetting', 'resolutionemu1600', str(self.resolutionemu1600))
        with open('file.ini', 'w') as configfile:
            config.write(configfile)

#============================================================SpaceBot
class SpaceBot(BotBase):
    def __init__(self, log_widget):
        config = configparser.ConfigParser()
        config.read('file.ini')
        collecting_bounds = (
            int(config['Bounds']['left']),
            int(config['Bounds']['top']),
            int(config['Bounds']['right']),
            int(config['Bounds']['bottom'])
        )
        window_name1 = config['WindowAnon']['name']

        self.resolutionemu1600 = config.getboolean('SettingsClicker', 'resolutionemu1600', fallback=True)
        self.resolutionemu960 = config.getboolean('SettingsClicker', 'resolutionemu960', fallback=False)

        if self.resolutionemu1600:
            self.image_folder = 'img/1600x900/anon/'
        elif self.resolutionemu960:
            self.image_folder = 'img/960x540/anon/'


        star_templates = [
            ('1', cv2.imread(f'{self.image_folder}/1.png', cv2.IMREAD_COLOR)),
            ('2', cv2.imread(f'{self.image_folder}/2.png', cv2.IMREAD_COLOR))
        ]
        star_ship = [
            ('10', cv2.imread(f'{self.image_folder}/ship.png', cv2.IMREAD_COLOR))
        ]
        super().__init__(log_widget, window_name1, collecting_bounds, star_templates, star_ship)

    def highlight_collecting_bounds(self):
        check = gw.getWindowsWithTitle(self.window_name)

        if not check:
            self.log_message(f"\nWindow {self.window_name} not found!\nPlease, select another window.")
            self.window_name = self.choose_window_gui()

        if not self.window_name or not gw.getWindowsWithTitle(self.window_name):
            self.log_message("\nThe specified window could not be found!\nStart the game, then restart the bot!")
            return

        telegram_window = gw.getWindowsWithTitle(self.window_name)[0]
        window_rect = (
            telegram_window.left, telegram_window.top, telegram_window.width, telegram_window.height
        )

        screenshot = self.grab_screen(window_rect, scale_factor=1.0)
        left, top, right, bottom = self.collecting_bounds
        cv2.rectangle(screenshot, (left, top), (right, bottom), (0, 255, 0), 2)

        # Отображение значений collecting_bounds рядом с границами
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        color = (0, 255, 0)
        thickness = 1

        # Отображение значений рядом с границами
        cv2.putText(screenshot, str(left), (left + 5, (top + bottom) // 2), font, font_scale, color, thickness)
        cv2.putText(screenshot, str(top), ((left + right) // 2, top + 20), font, font_scale, color, thickness)
        cv2.putText(screenshot, str(right), (right - 50, (top + bottom) // 2), font, font_scale, color, thickness)
        cv2.putText(screenshot, str(bottom), ((left + right) // 2, bottom - 15), font, font_scale, color, thickness)

        # Уменьшение размера изображения на 25 пикселей по ширине и высоте
        new_width = max(screenshot.shape[1] - 25, 1)
        new_height = max(screenshot.shape[0] - 25, 1)
        resized_screenshot = cv2.resize(screenshot, (new_width, new_height))

        cv2.imshow("Clicker Area Frame", resized_screenshot)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    # Функция для автоматического вычисления размеров окна
    def auto_update_collecting_bounds(self):
        try:
            window = gw.getWindowsWithTitle(self.window_name)[0]
            left, top, right, bottom = 0, 0, window.width, window.height
            self.update_collecting_bounds(
                tk.StringVar(value=left),
                tk.StringVar(value=top),
                tk.StringVar(value=right),
                tk.StringVar(value=bottom)
            )
        except Exception as e:
            self.log_message(f"Error: {e}")

    def bot_loop(self):
        check = gw.getWindowsWithTitle(self.window_name)

        if not check:
            self.log_message(f"\nWindow {self.window_name} not found!\nPlease, select another window.")
            self.window_name = self.choose_window_gui()

        if not self.window_name or not gw.getWindowsWithTitle(self.window_name):
            self.log_message("\nThe specified window could not be found!\nStart the game, then restart the bot!")
            return
        else:
            self.log_message(f"\nWindow {self.window_name} found\nPress 'D' to start\n'A' to pause\n'S' to stop bot")

        telegram_window = gw.getWindowsWithTitle(self.window_name)[0]

        # Запуск слушателя для отслеживания нажатий и движения мыши
        self.listener = Listener(on_click=self.on_click, on_move=self.on_move)
        self.listener.start()

        while True:
            if not self.running.is_set():
                self.running.wait()  # wait until running is set

            if self.paused:
                time.sleep(0.1)
                continue

            window_rect = (
                telegram_window.left, telegram_window.top, telegram_window.width, telegram_window.height
            )

            if telegram_window != []:
                try:
                    telegram_window.activate()
                except:
                    telegram_window.minimize()
                    telegram_window.restore()

            if self.collecting_resources:
                screenshot = self.grab_screen(window_rect)
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    futures = []
                    current_time = time.time()

                    futures += [executor.submit(self.process_template, template_data, screenshot, 0.5, telegram_window.left, telegram_window.top) for template_data in self.star_templates]

                    # Find the ship position
                    for template_data in self.star_ship:
                        _, position = self.process_template(template_data, screenshot, 0.5, telegram_window.left, telegram_window.top)
                        if position:
                            self.ship_position = (position[0] + telegram_window.left + template_data[1].shape[1] // 2,
                                                 position[1] + telegram_window.top + template_data[1].shape[0] // 2)
                            self.ship_template_size = (template_data[1].shape[1], template_data[1].shape[0])
                            break

                    # Process other templates
                    for future in concurrent.futures.as_completed(futures):
                        template_name, position = future.result()

        self.log_message('STOP')
        self.listener.stop()

class BlumBot(BotBase): #===========================================Blum=========================================================
    def __init__(self, log_widget):
        config = configparser.ConfigParser()
        config.read('file.ini')
        collecting_bounds = (
            int(config['BoundsBlum']['left']),
            int(config['BoundsBlum']['top']),
            int(config['BoundsBlum']['right']),
            int(config['BoundsBlum']['bottom'])
        )
        self.freeze_active = config.getboolean('State', 'freeze_active', fallback=False)
        self.restart_active = config.getboolean('State', 'restart_active', fallback=False)

        self.resolutionemu1600 = config.getboolean('SettingsClicker', 'resolutionemu1600', fallback=False)
        self.resolutionemu960 = config.getboolean('SettingsClicker', 'resolutionemu960', fallback=True)

        self.delaymin = 0
        self.delaymax = 0

        super().__init__(log_widget, window_name3, collecting_bounds, [], [])
        window_name2 = config['WindowBlum']['name']

        if self.resolutionemu1600:
            self.image_folder = 'img/1600x900/blum/'
        elif self.resolutionemu960:
            self.image_folder = 'img/960x540/blum/'

        star_templates = [
            ('1', cv2.imread(f'{self.image_folder}/1.png', cv2.IMREAD_COLOR)),
            ('2', cv2.imread(f'{self.image_folder}/2.png', cv2.IMREAD_COLOR))
        ]
        self.star_templates_5s = [
            ('5', cv2.imread(f'{self.image_folder}/4-1.png', cv2.IMREAD_COLOR)),
            ('5', cv2.imread(f'{self.image_folder}/4-1.png', cv2.IMREAD_COLOR))
        ]
        self.star_templates_10s = [
            ('6', cv2.imread(f'{self.image_folder}/6.png', cv2.IMREAD_COLOR))
        ]
        self.last_check_time_5s = 0
        self.last_check_time_10s = 0
        super().__init__(log_widget, window_name2, collecting_bounds, star_templates, [])

        # Добавление кнопок Freeze и Restart
        self.freeze_button = tk.Button(start_frame2, text="Freeze", command=self.toggle_freeze)
        self.freeze_button.grid(row=0, column=2, padx=(0, 10))

        self.restart_button = tk.Button(start_frame2, text="Restart", command=self.toggle_restart)
        self.restart_button.grid(row=0, column=3, padx=(0, 10))

        # Установка состояния кнопок при инициализации
        if self.freeze_active:
            self.freeze_button.config(relief=tk.SUNKEN, bg="green")
        else:
            self.freeze_button.config(relief=tk.RAISED, bg="SystemButtonFace")

        if self.restart_active:
            self.restart_button.config(relief=tk.SUNKEN, bg="green")
        else:
            self.restart_button.config(relief=tk.RAISED, bg="SystemButtonFace")

    def save_delays(self, delaymin_entry, delaymax_entry):
        config = configparser.ConfigParser()
        config.read('file.ini')
        try:
            delaymin = float(delaymin_entry.get())
            delaymax = float(delaymax_entry.get())
        except ValueError:
            print("Invalid input for delaymin or delaymax. Please enter valid float numbers.")
            return
        config.set('WindowBlum', 'delaymin', str(delaymin))
        config.set('WindowBlum', 'delaymax', str(delaymax))
        with open('file.ini', 'w') as configfile:
            config.write(configfile)
        self.delaymin = delaymin
        self.delaymax = delaymax

    def open_config_window_Blum(self):
        config_window = tk.Toplevel(root)
        config_window.title("Config")
        config_window.resizable(False, False)

        bounds_frame = tk.Frame(config_window, bg="dark gray")
        bounds_frame.pack(pady=10, padx=10)

        # Поля ввода для collecting_bounds
        left_label = tk.Label(bounds_frame, text="Left:", bg="white")
        left_label.grid(row=0, column=0, padx=2, pady=2, sticky="w")
        left_entry = tk.Entry(bounds_frame)
        left_entry.insert(0, self.collecting_bounds[0])
        left_entry.grid(row=0, column=1, padx=2, pady=2, sticky="w")

        top_label = tk.Label(bounds_frame, text="Top:", bg="white")
        top_label.grid(row=0, column=2, padx=2, pady=2, sticky="w")
        top_entry = tk.Entry(bounds_frame)
        top_entry.insert(0, self.collecting_bounds[1])
        top_entry.grid(row=0, column=3, padx=2, pady=2, sticky="w")

        right_label = tk.Label(bounds_frame, text="Right:", bg="white")
        right_label.grid(row=1, column=0, padx=2, pady=2, sticky="w")
        right_entry = tk.Entry(bounds_frame)
        right_entry.insert(0, self.collecting_bounds[2])
        right_entry.grid(row=1, column=1, padx=2, pady=2, sticky="w")

        bottom_label = tk.Label(bounds_frame, text="Bottom:", bg="white")
        bottom_label.grid(row=1, column=2, padx=2, pady=2, sticky="w")
        bottom_entry = tk.Entry(bounds_frame)
        bottom_entry.insert(0, self.collecting_bounds[3])
        bottom_entry.grid(row=1, column=3, padx=2, pady=2, sticky="w")

        # Кнопка для применения collecting_bounds
        apply_bounds_button = tk.Button(bounds_frame, text="Save",
                                        command=lambda: self.update_collecting_bounds(left_entry, top_entry,
                                                                                      right_entry, bottom_entry))
        apply_bounds_button.grid(row=2, column=0, columnspan=4, pady=5)

        # Кнопка для автоматического вычисления размеров окна
        auto_bounds_button = tk.Button(bounds_frame, text="Auto Update Bounds")
        auto_bounds_button.grid(row=3, column=0, columnspan=4, pady=5)

        # Добавление кнопки для выделения области
        highlight_button = tk.Button(bounds_frame, text="Show Clicker Frame", command=self.highlight_collecting_bounds)
        highlight_button.grid(row=4, column=0, columnspan=4, pady=5)

        # Добавление текстовых полей для delaymin и delaymax

        delay_frame = tk.Frame(config_window, bg="dark gray")
        delay_frame.pack(pady=(10, 0), padx=10)
        resolution_section_label = tk.Label(delay_frame, text="Random delay between clicks\n(from and to)", bg="dark gray",
                                            font=("Arial", 10, "bold"))
        resolution_section_label.grid(row=0, column=0, columnspan=2, pady=0)
        delaymin_label = tk.Label(delay_frame, text="Delay Min:", bg="dark gray")
        delaymin_label.grid(row=1, column=0, padx=2, pady=2, sticky="w")
        delaymin_entry = tk.Entry(delay_frame)
        delaymin_entry.insert(0, config.get('WindowBlum', 'delaymin', fallback='0.04'))
        delaymin_entry.grid(row=1, column=1, padx=2, pady=2, sticky="w")

        delaymax_label = tk.Label(delay_frame, text="Delay Max:", bg="dark gray")
        delaymax_label.grid(row=2, column=0, padx=2, pady=2, sticky="w")
        delaymax_entry = tk.Entry(delay_frame)
        delaymax_entry.insert(0, config.get('WindowBlum', 'delaymax', fallback='0.08'))
        delaymax_entry.grid(row=2, column=1, padx=2, pady=2, sticky="w")

        save_button = tk.Button(delay_frame, text="Save",
                                command=lambda: blum_bot.save_delays(delaymin_entry, delaymax_entry))
        save_button.grid(row=3, column=0, columnspan=2, pady=5)

        # Новая секция для ввода значений разрешения экрана
        settings_frame5 = tk.Frame(config_window, bg="gray")
        settings_frame5.pack(pady=(10, 0), padx=10)

        resolution_section_label = tk.Label(settings_frame5, text="Display Resolution", bg="dark gray",
                                            font=("Arial", 10, "bold"))
        resolution_section_label.grid(row=0, column=0, columnspan=2, pady=0)

        settings_frame51 = tk.Frame(config_window, bg="gray")
        settings_frame51.pack(pady=2, padx=10)

        height_label = tk.Label(settings_frame51, text="Height:", bg="white")
        height_label.grid(row=2, column=0, padx=2, pady=2, sticky="w")
        height_entry = tk.Entry(settings_frame51, width=10)
        height_entry.insert(0, self.height)
        height_entry.grid(row=2, column=1, padx=2, pady=10, sticky="w")

        width_label = tk.Label(settings_frame51, text="Width:", bg="white")
        width_label.grid(row=1, column=0, padx=2, pady=2, sticky="w")
        width_entry = tk.Entry(settings_frame51, width=10)
        width_entry.insert(0, self.width)
        width_entry.grid(row=1, column=1, padx=2, pady=10, sticky="w")

        settings_frame61 = tk.Frame(config_window, bg="gray")
        settings_frame61.pack(pady=2, padx=10)

        # Кнопки для переключения разрешений
        resolution_frame71 = tk.Frame(config_window, bg="gray")
        resolution_frame71.pack(pady=(5, 2), padx=10)

        resolution_frame_label = tk.Label(resolution_frame71, text="Emulator Resolution", bg="dark gray",
                                          font=("Arial", 10, "bold"))
        resolution_frame_label.grid(row=0, column=0, columnspan=2, pady=0)

        resolution_frame = tk.Frame(config_window, bg="gray")
        resolution_frame.pack(pady=(0, 5), padx=10)

        resolution960_button = tk.Button(resolution_frame, text="960x540",
                                         bg="dark gray" if self.resolutionemu960 else "light gray",
                                         command=lambda: self.toggle_resolution('960x540', resolution960_button,
                                                                                resolution1600_button))
        resolution960_button.grid(row=0, column=0, padx=5, pady=5)

        resolution1600_button = tk.Button(resolution_frame, text="1600x900",
                                          bg="dark gray" if self.resolutionemu1600 else "light gray",
                                          command=lambda: self.toggle_resolution('1600x900', resolution960_button,
                                                                                 resolution1600_button))
        resolution1600_button.grid(row=0, column=1, padx=5, pady=5)

        # Кнопка для сохранения значений из SettingsClicker
        save_settings_button = tk.Button(settings_frame61, text="Save",
                                         command=lambda: self.update_settings_values_display(height_entry, width_entry))
        save_settings_button.grid(row=5, column=0, columnspan=2, pady=5, padx=5)

    def highlight_collecting_bounds(self):
        check = gw.getWindowsWithTitle(self.window_name)

        if not check:
            self.log_message(f"\nWindow {self.window_name} not found!\nPlease, select another window.")
            self.window_name = self.choose_window_gui()

        if not self.window_name or not gw.getWindowsWithTitle(self.window_name):
            self.log_message("\nThe specified window could not be found!\nStart the game, then restart the bot!")
            return

        telegram_window = gw.getWindowsWithTitle(self.window_name)[0]
        window_rect = (
            telegram_window.left, telegram_window.top, telegram_window.width, telegram_window.height
        )

        screenshot = self.grab_screen(window_rect, scale_factor=1.0)
        left, top, right, bottom = self.collecting_bounds
        cv2.rectangle(screenshot, (left, top), (right, bottom), (0, 255, 0), 2)

        # Отображение значений collecting_bounds рядом с границами
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        color = (0, 255, 0)
        thickness = 1

        # Отображение значений рядом с границами
        cv2.putText(screenshot, str(left), (left + 5, (top + bottom) // 2), font, font_scale, color, thickness)
        cv2.putText(screenshot, str(top), ((left + right) // 2, top + 20), font, font_scale, color, thickness)
        cv2.putText(screenshot, str(right), (right - 50, (top + bottom) // 2), font, font_scale, color, thickness)
        cv2.putText(screenshot, str(bottom), ((left + right) // 2, bottom - 15), font, font_scale, color, thickness)

        # Уменьшение размера изображения на 25 пикселей по ширине и высоте
        new_width = max(screenshot.shape[1] - 25, 1)
        new_height = max(screenshot.shape[0] - 25, 1)
        resized_screenshot = cv2.resize(screenshot, (new_width, new_height))

        cv2.imshow("Clicker Area Frame", resized_screenshot)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    def auto_update_collecting_bounds(self):
        try:
            window = gw.getWindowsWithTitle(self.window_name)[0]
            left, top, right, bottom = 0, 0, window.width, window.height
            self.update_collecting_bounds(
                tk.StringVar(value=left),
                tk.StringVar(value=top),
                tk.StringVar(value=right),
                tk.StringVar(value=bottom)
            )
        except Exception as e:
            self.log_message(f"Error: {e}")

    def toggle_freeze(self):
        self.freeze_active = not self.freeze_active
        if self.freeze_active:
            self.freeze_button.config(relief=tk.SUNKEN, bg="green")
        else:
            self.freeze_button.config(relief=tk.RAISED, bg="SystemButtonFace")
        # Сохранение состояния в файл ini
        config = configparser.ConfigParser()
        config.read('file.ini')
        config['State']['freeze_active'] = str(self.freeze_active)
        with open('file.ini', 'w') as configfile:
            config.write(configfile)

    def toggle_restart(self):
        self.restart_active = not self.restart_active
        if self.restart_active:
            self.restart_button.config(relief=tk.SUNKEN, bg="green")
        else:
            self.restart_button.config(relief=tk.RAISED, bg="SystemButtonFace")
        # Сохранение состояния в файл ini
        config = configparser.ConfigParser()
        config.read('file.ini')
        config['State']['restart_active'] = str(self.restart_active)
        with open('file.ini', 'w') as configfile:
            config.write(configfile)

    def bot_loop(self):
        check = gw.getWindowsWithTitle(self.window_name)

        if not check:
            self.log_message(f"\nWindow {self.window_name} not found!\nPlease, select another window.")
            self.window_name = self.choose_window_gui()

        if not self.window_name or not gw.getWindowsWithTitle(self.window_name):
            self.log_message("\nThe specified window could not be found!\nStart the game, then restart the bot!")
            return
        else:
            self.log_message(f"\nWindow {self.window_name} found\nPress 'D' to start\n'A' to pause\n'S' to stop bot")

        telegram_window = gw.getWindowsWithTitle(self.window_name)[0]

        # # Запуск слушателя для отслеживания нажатий и движения мыши
        # self.listener = Listener(on_click=self.on_click, on_move=self.on_move)
        # self.listener.start()

        while True:
            if not self.running.is_set():
                self.running.wait()  # wait until running is set

            if self.paused:
                time.sleep(0.1)
                continue

            window_rect = (
                telegram_window.left, telegram_window.top, telegram_window.width, telegram_window.height
            )

            if telegram_window != []:
                try:
                    telegram_window.activate()
                except:
                    telegram_window.minimize()
                    telegram_window.restore()

            if self.collecting_resources:
                screenshot = self.grab_screen(window_rect)
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    futures = []
                    current_time = time.time()

                    if self.restart_active and current_time - self.last_check_time_10s >= 30:
                        futures += [executor.submit(self.process_template, template_data, screenshot, 0.5, telegram_window.left, telegram_window.top) for template_data in self.star_templates_10s]
                        self.last_check_time_10s = current_time

                    if self.freeze_active:
                        futures += [executor.submit(self.process_template, template_data, screenshot, 0.5, telegram_window.left, telegram_window.top) for template_data in self.star_templates_5s]

                    futures += [executor.submit(self.process_template, template_data, screenshot, 0.5, telegram_window.left, telegram_window.top) for template_data in self.star_templates]

                    # Find the ship position
                    for template_data in self.star_ship:
                        _, position = self.process_template(template_data, screenshot, 0.5, telegram_window.left, telegram_window.top)
                        if position:
                            self.ship_position = (position[0] + telegram_window.left + template_data[1].shape[1] // 2,
                                                 position[1] + telegram_window.top + template_data[1].shape[0] // 2)
                            self.ship_template_size = (template_data[1].shape[1], template_data[1].shape[0])
                            break

                    # Process other templates
                    for future in concurrent.futures.as_completed(futures):
                        template_name, position = future.result()

        self.log_message('STOP')
        self.listener.stop()

        # ================================================= ScreenShoter ========================
class ScreenShoter:
    def __init__(self, queue, log_widget):
        print("ScreenShoter initialized")
        self.queue = queue
        self.screenshot_mode = False
        self.log_widget = log_widget
        self.start_x = 0
        self.start_y = 0
        self.end_x = 0
        self.end_y = 0
        self.selection_rectangle = None
        self.screenshot_counter = 1  # Initialize the screenshot counter

        self.mouse_listener = mouse.Listener(on_click=self.on_click, on_move=self.on_move)
        self.keyboard_listener = keyboard.Listener(on_press=self.on_press)
        self.keyboard_listener.start()
        self.mouse_listener.start()

        # Create a transparent overlay window
        self.overlay = tk.Toplevel()
        self.overlay.attributes('-fullscreen', True)
        self.overlay.attributes('-alpha', 0.3)  # Make the window semi-transparent
        self.overlay.attributes('-topmost', True)
        self.overlay.config(cursor="cross")
        self.canvas = tk.Canvas(self.overlay, bg='black', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.overlay.withdraw()  # Hide the overlay initially

    def log_message_scrshoter(self, message):
        self.log_widget.config(state='normal')
        self.log_widget.insert(tk.END, message + "\n")
        self.log_widget.see(tk.END)
        self.log_widget.config(state='disabled')

    def on_press(self, key):
        print(f"Key pressed: {key}")
        try:
            if key.char == 'f':
                self.queue.put(self.activate_screenshot_mode)
        except AttributeError:
            if key == keyboard.Key.print_screen:
                self.queue.put(self.take_full_screenshot)

    def activate_screenshot_mode(self):
        self.screenshot_mode = True
        self.overlay.deiconify()  # Show the overlay
        self.mouse_listener = mouse.Listener(on_click=self.on_click, on_move=self.on_move)
        self.mouse_listener.start()

    def deactivate_screenshot_mode(self):
        self.screenshot_mode = False
        self.overlay.withdraw()  # Hide the overlay
        if self.mouse_listener:
            self.mouse_listener.stop()
            self.mouse_listener = None
        self.reset_selection()

    def on_click(self, x, y, button, pressed):
        if self.screenshot_mode:
            if pressed:
                self.start_x = x
                self.start_y = y
                self.queue.put(self.create_selection_rectangle)
            else:
                self.end_x = x
                self.end_y = y
                self.queue.put(self.take_screenshot)
                self.queue.put(self.deactivate_screenshot_mode)

    def on_move(self, x, y):
        if self.screenshot_mode:
            self.end_x = x
            self.end_y = y
            self.queue.put(self.update_selection_rectangle)

    def create_selection_rectangle(self):
        if self.selection_rectangle:
            self.canvas.delete(self.selection_rectangle)
        self.selection_rectangle = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline='red', width=2)

    def update_selection_rectangle(self):
        if self.selection_rectangle:
            self.canvas.coords(self.selection_rectangle, self.start_x, self.start_y, self.end_x, self.end_y)

    def take_screenshot(self):
        self.overlay.withdraw()

        x1 = min(self.start_x, self.end_x)
        y1 = min(self.start_y, self.end_y)
        x2 = max(self.start_x, self.end_x)
        y2 = max(self.start_y, self.end_y)

        screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
        screenshot_folder = os.path.join(os.getcwd(), 'img', 'fotoshots')
        os.makedirs(screenshot_folder, exist_ok=True)
        screenshot_path = os.path.join(screenshot_folder, f'{self.screenshot_counter}.png')
        screenshot.save(screenshot_path)

        self.log_message_scrshoter(f"Screenshot saved to:\n{screenshot_path}")
        self.screenshot_counter += 1

        self.overlay.deiconify()

    def take_full_screenshot(self):
        screenshot = ImageGrab.grab()
        screenshot_folder = os.path.join(os.getcwd(), 'img', 'screenshots')
        os.makedirs(screenshot_folder, exist_ok=True)
        screenshot_path = os.path.join(screenshot_folder, f'{self.screenshot_counter}.png')
        screenshot.save(screenshot_path)

        self.log_message_scrshoter(f"Full screenshot saved to:\n{screenshot_path}")
        self.screenshot_counter += 1

    def reset_selection(self):
        self.start_x = 0
        self.start_y = 0
        self.end_x = 0
        self.end_y = 0
        if self.selection_rectangle:
            self.canvas.delete(self.selection_rectangle)
            self.selection_rectangle = None

def start_screenshot_listener(queue, log_widget):
    ScreenShoter(queue, log_widget)

def process_queue(root, queue):
    while not queue.empty():
        command = queue.get()
        try:
            command()
        except Exception as e:
            print(f"Error executing command: {e}")
    root.after(100, process_queue, root, queue)




#==========================================================================================================

class ClickerBot(BotBase):
    def __init__(self, log_widget, profile='ClickerBot1'):
        self.profile = profile
        self.profiles = ['ClickerBot1', 'ClickerBot2', 'ClickerBot3', 'ClickerBot4', 'ClickerBot5', 'ClickerBot6', 'ClickerBot7', 'ClickerBot8']
        self.profile_data = {}

        self.name = {}
        self.active = {}
        self.checkbutton = {}
        self.boost_label = {}
        self.max_energy = {}
        self.energy_per_click = {}
        self.energy_recovery_rate = {}
        self.current_energy = {}
        self.timeCurrentEnergyNULL = {}
        self.timeCurrentEnergyFULL = {}
        self.boosts_used = {}
        self.boost_time = {}
        self.booststarttimer = {}
        self.boosttimetorecharge = {}
        self.boostcooldown = {}
        self.usedAllBoost = {}

        self.min_pause = 0
        self.max_pause = 0

        self.checkbtn = 0
        self.closebtn = False
        self.boostawaittime = 0
        self.closeawaittime = 0
        self.width = 0
        self.height = 0

        self.usedBoost = False

        self.profileCurrent = ''

        config = configparser.ConfigParser()
        config.read('file.ini')
        collecting_bounds = (
            int(config['BoundsClicker']['left']),
            int(config['BoundsClicker']['top']),
            int(config['BoundsClicker']['right']),
            int(config['BoundsClicker']['bottom'])
        )
        self.resolutionemu1600 = config.getboolean('SettingsClicker', 'resolutionemu1600', fallback=True)
        self.resolutionemu960 = config.getboolean('SettingsClicker', 'resolutionemu960', fallback=False)
        window_name3 = config['WindowClicker']['name']
        super().__init__(log_widget, window_name3, collecting_bounds, [], [])
        if self.resolutionemu1600:
            self.image_folder = 'img/1600x900/clicker/'
        elif self.resolutionemu960:
            self.image_folder = 'img/960x540/clicker/'
        config = configparser.ConfigParser()
        config.read('file.ini')
        self.height = int(config.get('SettingsClicker', 'height', fallback=1080))
        self.width = int(config.get('SettingsClicker', 'width', fallback=1920))
        self.screen_width = self.width  # Установите ширину экрана
        self.screen_height = self.height  # Установите высоту экрана
        self.load_profile_settings(self.profile)
        self.load_profiles_from_config()  # Загрузка данных профилей

    def load_profiles_from_config(self):
        config = configparser.ConfigParser()
        config.read('file.ini')
        for profile in self.profiles:
            if profile in config:
                self.profile_data[profile] = {
                    'name': config.get(profile, 'name', fallback=f'{profile}'),
                    'checkbutton': config.getboolean(profile, 'checkbutton', fallback=False),
                    'closebtn': config.getboolean(profile, 'closebtn', fallback=False)
                }

    def update_collecting_bounds(self, left_entry, top_entry, right_entry, bottom_entry):
        try:
            left = int(left_entry.get())
            top = int(top_entry.get())
            right = int(right_entry.get())
            bottom = int(bottom_entry.get())
            self.collecting_bounds = (left, top, right, bottom)
            self.log_message(f"Collecting bounds updated to: {self.collecting_bounds}")
            # Обновление значений в файле ini
            config = configparser.ConfigParser()
            config.read('file.ini')
            config['BoundsClicker']['left'] = str(left)
            config['BoundsClicker']['top'] = str(top)
            config['BoundsClicker']['right'] = str(right)
            config['BoundsClicker']['bottom'] = str(bottom)
            with open('file.ini', 'w') as configfile:
                    config.write(configfile)
        except ValueError:
            self.log_message("Invalid input for collecting bounds. Please enter integers.")

    def highlight_collecting_bounds(self):
        check = gw.getWindowsWithTitle(self.window_name)

        if not check:
            self.log_message(f"\nWindow {self.window_name} not found!\nPlease, select another window.")
            self.window_name = self.choose_window_gui()

        if not self.window_name or not gw.getWindowsWithTitle(self.window_name):
            self.log_message("\nThe specified window could not be found!\nStart the game, then restart the bot!")
            return

        telegram_window = gw.getWindowsWithTitle(self.window_name)[0]
        window_rect = (
            telegram_window.left, telegram_window.top, telegram_window.width, telegram_window.height
        )

        screenshot = self.grab_screen(window_rect, scale_factor=1.0)
        left, top, right, bottom = self.collecting_bounds
        cv2.rectangle(screenshot, (left, top), (right, bottom), (0, 255, 0), 2)

        # Отображение значений collecting_bounds рядом с границами
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        color = (0, 255, 0)
        thickness = 1

        # Отображение значений рядом с границами
        cv2.putText(screenshot, str(left), (left + 5, (top + bottom) // 2), font, font_scale, color, thickness)
        cv2.putText(screenshot, str(top), ((left + right) // 2, top + 20), font, font_scale, color, thickness)
        cv2.putText(screenshot, str(right), (right - 50, (top + bottom) // 2), font, font_scale, color, thickness)
        cv2.putText(screenshot, str(bottom), ((left + right) // 2, bottom - 15), font, font_scale, color, thickness)

        # Уменьшение размера изображения на 25 пикселей по ширине и высоте
        new_width = max(screenshot.shape[1] - 25, 1)
        new_height = max(screenshot.shape[0] - 25, 1)
        resized_screenshot = cv2.resize(screenshot, (new_width, new_height))

        cv2.imshow("Clicker Area Frame", resized_screenshot)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    def load_profile_settings(self, profile):
        config = configparser.ConfigParser()
        config.read('file.ini')

        if profile not in config:
            config[profile] = {
                'name' : '',
                'active' : 'True',
                'checkbutton' : 'False',
                'closebtn' : 'False',
                'boost_label': '0',
                'max_energy': '5000',
                'energy_per_click': '9',
                'energy_recovery_rate': '10',
                'current_energy': '5000',
                'timeCurrentEnergyNULL': '0',
                'timeCurrentEnergyFULL': '0',
                'boosts_used': '0',
                'boost_time' : '3600',
                'booststarttimer': '0',
                'boosttimetorecharge': '0',
                'boostcooldown': '0',
                'usedAllBoost' : 'False'
            }
            with open('file.ini', 'w') as configfile:
                config.write(configfile)

        self.name[profile] = str(config[profile].get('name', ''))
        self.boost_label[profile] = int(config[profile].get('boost_label', '0'))
        self.max_energy[profile] = int(config[profile].get('max_energy', '5000'))
        self.energy_per_click[profile] = int(config[profile].get('energy_per_click', '9'))
        self.energy_recovery_rate[profile] = int(config[profile].get('energy_recovery_rate', '10'))
        self.current_energy[profile] = int(config[profile].get('current_energy', '5000'))
        self.timeCurrentEnergyNULL[profile] = int(config[profile].get('timeCurrentEnergyNULL', '0'))
        self.timeCurrentEnergyFULL[profile] = int(config[profile].get('timeCurrentEnergyFULL', '0'))
        self.boosts_used[profile] = int(config[profile].get('boosts_used'))
        self.boost_time[profile] = int(config[profile].get('boost_time', '3600'))
        self.booststarttimer[profile] = int(config[profile].get('booststarttimer', '0'))
        self.boosttimetorecharge[profile] = int(config[profile].get('boosttimetorecharge', '0'))
        self.boostcooldown[profile] = int(config[profile].get('boostcooldown', '0'))

        # Загрузка значений паузы из файла ini
        self.min_pause = int(config.get('RandomPause', 'min', fallback=5))
        self.max_pause = int(config.get('RandomPause', 'max', fallback=15))

        # Загрузка значений из SettingsClicker
        self.checkbtn = int(config.get('SettingsClicker', 'checkbtn', fallback=7))
        self.closebtn = int(config.get('SettingsClicker', 'closebtn', fallback=7))
        self.boostawaittime = int(config.get('SettingsClicker', 'boostawaittime', fallback=4))
        self.closeawaittime = int(config.get('SettingsClicker', 'closeawaittime', fallback=4))

    def update_resolution(self, resolution):
        config = configparser.ConfigParser()
        config.read('file.ini')
        if self.resolutionemu960 == True:
            self.resolutionemu1600 = False
        elif self.resolutionemu1600 == True:
            self.resolutionemu960 = False
        config.set('SettingsClicker', 'resolutionemu960', str(self.resolutionemu960))
        config.set('SettingsClicker', 'resolutionemu1600', str(self.resolutionemu1600))
        with open('file.ini', 'w') as configfile:
            config.write(configfile)

    def get_bot_name(self, profile):
        config = configparser.ConfigParser()
        config.read('file.ini')
        if profile in config:
            return config.get(profile, 'name', fallback=profile)
        return profile

    def save_profiles_to_config(self):
        config = configparser.ConfigParser()
        config.read('file.ini')
        for profile in self.profiles:
            if profile not in config:
                config[profile] = {}
            config[profile]['name'] = self.profile_data[profile]['name']
            config[profile]['checkbutton'] = str(self.profile_data[profile]['checkbutton'])
        with open('file.ini', 'w') as configfile:
            config.write(configfile)

    def update_profile_data(self, entries, checkbuttons_claim, checkbuttons_close):
        config = configparser.ConfigParser()
        config.read('file.ini')
        for i, profile in enumerate(self.profiles):
            config.set(profile, 'name', entries[i].get())
            config.set(profile, 'checkbutton', str(checkbuttons_claim[i].get()))
            config.set(profile, 'closebtn', str(checkbuttons_close[i].get()))
        with open('file.ini', 'w') as configfile:
            config.write(configfile)

    def open_config_windowClicker(self):
        config_window = tk.Toplevel(root)
        config_window.title("Config")
        config_window.resizable(False, False)

        tab_control = ttk.Notebook(config_window)

        # Вкладка 1
        tab1 = ttk.Frame(tab_control)
        tab_control.add(tab1, text='1')

        bounds_frame = tk.Frame(tab1, bg="dark gray")
        bounds_frame.pack(pady=10, padx=10)

        # Поля ввода для collecting_bounds
        left_label = tk.Label(bounds_frame, text="Left:", bg="white")
        left_label.grid(row=0, column=0, padx=2, pady=2, sticky="w")
        left_entry = tk.Entry(bounds_frame)
        left_entry.insert(0, self.collecting_bounds[0])
        left_entry.grid(row=0, column=1, padx=2, pady=2, sticky="w")

        top_label = tk.Label(bounds_frame, text="Top:", bg="white")
        top_label.grid(row=0, column=2, padx=2, pady=2, sticky="w")
        top_entry = tk.Entry(bounds_frame)
        top_entry.insert(0, self.collecting_bounds[1])
        top_entry.grid(row=0, column=3, padx=2, pady=2, sticky="w")

        right_label = tk.Label(bounds_frame, text="Right:", bg="white")
        right_label.grid(row=1, column=0, padx=2, pady=2, sticky="w")
        right_entry = tk.Entry(bounds_frame)
        right_entry.insert(0, self.collecting_bounds[2])
        right_entry.grid(row=1, column=1, padx=2, pady=2, sticky="w")

        bottom_label = tk.Label(bounds_frame, text="Bottom:", bg="white")
        bottom_label.grid(row=1, column=2, padx=2, pady=2, sticky="w")
        bottom_entry = tk.Entry(bounds_frame)
        bottom_entry.insert(0, self.collecting_bounds[3])
        bottom_entry.grid(row=1, column=3, padx=2, pady=2, sticky="w")

        # Кнопка для применения collecting_bounds
        apply_bounds_button = tk.Button(bounds_frame, text="Save",
                                        command=lambda: self.update_collecting_bounds(left_entry, top_entry,
                                                                                      right_entry, bottom_entry))
        apply_bounds_button.grid(row=2, column=0, columnspan=4, pady=5)

        # Кнопка для автоматического вычисления размеров окна
        auto_bounds_button = tk.Button(bounds_frame, text="Auto Update Bounds")
        auto_bounds_button.grid(row=3, column=0, columnspan=4, pady=5)

        # Добавление кнопки для выделения области
        highlight_button = tk.Button(bounds_frame, text="Show Clicker Frame", command=self.highlight_collecting_bounds)
        highlight_button.grid(row=4, column=0, columnspan=4, pady=5)

        # Горизонтальная линия
        ttk.Separator(tab1, orient='horizontal').pack(fill='x', pady=10)

        # Таблица для профилей
        table_frame = tk.Frame(tab1, bg="dark gray")
        table_frame.pack(pady=10, padx=10)

        tk.Label(table_frame, text="bot_id", bg="white").grid(row=0, column=0, padx=5, pady=5)
        tk.Label(table_frame, text="bot_name", bg="white").grid(row=0, column=1, padx=5, pady=5)
        tk.Label(table_frame, text="claim_btn", bg="white").grid(row=0, column=2, padx=5, pady=5)
        tk.Label(table_frame, text="close_btn", bg="white").grid(row=0, column=3, padx=5, pady=5)

        entries = []
        checkbuttons_claim = []
        checkbuttons_close = []

        for i, profile in enumerate(self.profiles):
            tk.Label(table_frame, text=profile, bg="white").grid(row=i + 1, column=0, padx=5, pady=5)
            entry = tk.Entry(table_frame, width=15)
            entry.insert(0, self.profile_data[profile]['name'])
            entry.grid(row=i + 1, column=1, padx=5, pady=5)
            entries.append(entry)

            check_var_claim = tk.BooleanVar(value=self.profile_data[profile]['checkbutton'])
            checkbutton_claim = tk.Checkbutton(table_frame, variable=check_var_claim, bg="white")
            checkbutton_claim.grid(row=i + 1, column=2, padx=5, pady=5)
            checkbuttons_claim.append(check_var_claim)

            check_var_close = tk.BooleanVar(value=self.profile_data[profile].get('closebtn', False))
            checkbutton_close = tk.Checkbutton(table_frame, variable=check_var_close, bg="white")
            checkbutton_close.grid(row=i + 1, column=3, padx=5, pady=5)
            checkbuttons_close.append(check_var_close)

        # Кнопка для сохранения профилей
        save_button = tk.Button(tab1, text="Save", command=lambda: self.update_profile_data(entries, checkbuttons_claim,
                                                                                            checkbuttons_close))
        save_button.pack(pady=5)

        # Вкладка 2
        tab2 = ttk.Frame(tab_control)
        tab_control.add(tab2, text='2')

        settings_frame111 = tk.Frame(tab2, bg="gray")
        settings_frame111.pack(pady=0, padx=10)
        # Заголовок для секции паузы
        pause_label = tk.Label(settings_frame111, text="Random value of the pause between transitions\n(from and to)",
                               bg="dark gray", font=("Arial", 10, "bold"))
        pause_label.pack(pady=0)

        # Новая секция для ввода значений паузы
        pause_frame = tk.Frame(tab2, bg="dark gray")
        pause_frame.pack(pady=5, padx=10)

        min_label = tk.Label(pause_frame, text="Min Value (s):", bg="white")
        min_label.grid(row=0, column=0, padx=2, pady=2, sticky="w")
        min_entry = tk.Entry(pause_frame, width=10)
        min_entry.insert(0, self.min_pause)
        min_entry.grid(row=0, column=1, padx=2, pady=2, sticky="w")

        max_label = tk.Label(pause_frame, text="Max Value (s):", bg="white")
        max_label.grid(row=0, column=2, padx=2, pady=2, sticky="w")
        max_entry = tk.Entry(pause_frame, width=10)
        max_entry.insert(0, self.max_pause)
        max_entry.grid(row=0, column=3, padx=2, pady=2, sticky="w")

        # Кнопка для сохранения значений паузы
        save_pause_button = tk.Button(pause_frame, text="Save",
                                      command=lambda: self.update_pause_values(min_entry, max_entry))
        save_pause_button.grid(row=1, column=0, columnspan=4, pady=5)

        # Горизонтальная линия
        ttk.Separator(tab2, orient='horizontal').pack(fill='x', pady=10)

        # Новая секция для ввода значений из SettingsClicker
        settings_frame2 = tk.Frame(tab2, bg="gray")
        settings_frame2.pack(pady=0, padx=10)

        checkbtn_section_label = tk.Label(settings_frame2,
                                          text="Waiting time for the window with the CLAIM button in open game",
                                          bg="dark gray", font=("Arial", 10, "bold"))
        checkbtn_section_label.grid(row=0, column=0, columnspan=2, pady=0)

        settings_frame21 = tk.Frame(tab2, bg="gray")
        settings_frame21.pack(pady=2, padx=10)

        checkbtn_label = tk.Label(settings_frame21, text="Claim Button Await Time:", bg="white")
        checkbtn_label.grid(row=1, column=0, padx=2, pady=2, sticky="w")
        checkbtn_entry = tk.Entry(settings_frame21, width=10)
        checkbtn_entry.insert(0, self.checkbtn)
        checkbtn_entry.grid(row=1, column=1, padx=2, pady=10, sticky="w")

        settings_frame3 = tk.Frame(tab2, bg="gray")
        settings_frame3.pack(pady=(10, 0), padx=10)
        boostawaittime_section_label = tk.Label(settings_frame3,
                                                text="Waiting time for the button with BOOST to appear", bg="dark gray",
                                                font=("Arial", 10, "bold"))
        boostawaittime_section_label.grid(row=2, column=0, columnspan=2, pady=0)

        settings_frame31 = tk.Frame(tab2, bg="gray")
        settings_frame31.pack(pady=2, padx=10)

        boostawaittime_label = tk.Label(settings_frame31, text="Boost Button Await Time:", bg="white")
        boostawaittime_label.grid(row=3, column=0, padx=2, pady=2, sticky="w")
        boostawaittime_entry = tk.Entry(settings_frame31, width=10)
        boostawaittime_entry.insert(0, self.boostawaittime)
        boostawaittime_entry.grid(row=3, column=1, padx=2, pady=10, sticky="w")

        settings_frame4 = tk.Frame(tab2, bg="gray")
        settings_frame4.pack(pady=(10, 0), padx=10)
        closeawaittime_section_label = tk.Label(settings_frame4,
                                                text="Waiting time for the button to appear with the window CLOSED",
                                                bg="dark gray", font=("Arial", 10, "bold"))
        closeawaittime_section_label.grid(row=4, column=0, columnspan=2, pady=0)

        settings_frame41 = tk.Frame(tab2, bg="gray")
        settings_frame41.pack(pady=2, padx=10)

        closeawaittime_label = tk.Label(settings_frame41, text="Close Button Await Time:", bg="white")
        closeawaittime_label.grid(row=5, column=0, padx=2, pady=2, sticky="w")
        closeawaittime_entry = tk.Entry(settings_frame41, width=10)
        closeawaittime_entry.insert(0, self.closeawaittime)
        closeawaittime_entry.grid(row=5, column=1, padx=2, pady=10, sticky="w")

        # Новая секция для ввода значений разрешения экрана
        settings_frame5 = tk.Frame(tab2, bg="gray")
        settings_frame5.pack(pady=(10, 0), padx=10)

        resolution_section_label = tk.Label(settings_frame5, text="Display Resolution", bg="dark gray",
                                            font=("Arial", 10, "bold"))
        resolution_section_label.grid(row=0, column=0, columnspan=2, pady=0)

        settings_frame51 = tk.Frame(tab2, bg="gray")
        settings_frame51.pack(pady=2, padx=10)

        height_label = tk.Label(settings_frame51, text="Height:", bg="white")
        height_label.grid(row=2, column=0, padx=2, pady=2, sticky="w")
        height_entry = tk.Entry(settings_frame51, width=10)
        height_entry.insert(0, self.height)
        height_entry.grid(row=2, column=1, padx=2, pady=10, sticky="w")

        width_label = tk.Label(settings_frame51, text="Width:", bg="white")
        width_label.grid(row=1, column=0, padx=2, pady=2, sticky="w")
        width_entry = tk.Entry(settings_frame51, width=10)
        width_entry.insert(0, self.width)
        width_entry.grid(row=1, column=1, padx=2, pady=10, sticky="w")

        settings_frame61 = tk.Frame(tab2, bg="gray")
        settings_frame61.pack(pady=2, padx=10)

        # Кнопки для переключения разрешений
        resolution_frame71 = tk.Frame(tab2, bg="gray")
        resolution_frame71.pack(pady=(5,2), padx=10)

        resolution_frame_label = tk.Label(resolution_frame71, text="Emulator Resolution", bg="dark gray",
                                            font=("Arial", 10, "bold"))
        resolution_frame_label.grid(row=0, column=0, columnspan=2, pady=0)

        resolution_frame = tk.Frame(tab2, bg="gray")
        resolution_frame.pack(pady=0, padx=10)



        resolution960_button = tk.Button(resolution_frame, text="960x540",
                                         bg="dark gray" if self.resolutionemu960 else "light gray",
                                         command=lambda: self.toggle_resolution('960x540', resolution960_button,
                                                                                resolution1600_button))
        resolution960_button.grid(row=0, column=0, padx=5, pady=5)

        resolution1600_button = tk.Button(resolution_frame, text="1600x900",
                                          bg="dark gray" if self.resolutionemu1600 else "light gray",
                                          command=lambda: self.toggle_resolution('1600x900', resolution960_button,
                                                                                 resolution1600_button))
        resolution1600_button.grid(row=0, column=1, padx=5, pady=5)

        # Кнопка для сохранения значений из SettingsClicker
        save_settings_button = tk.Button(settings_frame61, text="Save",
                                         command=lambda: self.update_settings_values(checkbtn_entry,
                                                                                     boostawaittime_entry,
                                                                                     closeawaittime_entry, height_entry,
                                                                                     width_entry))
        save_settings_button.grid(row=5, column=0, columnspan=2, pady=5, padx=5)

        tab_control.pack(expand=1, fill='both')

    def toggle_resolution(self, resolution, button960, button1600):
        if resolution == '960x540':
            self.resolutionemu960 = True
            self.resolutionemu1600 = False
            button960.config(bg="dark gray")
            button1600.config(bg="light gray")
        elif resolution == '1600x900':
            self.resolutionemu960 = False
            self.resolutionemu1600 = True
            button960.config(bg="light gray")
            button1600.config(bg="dark gray")
        self.update_resolution(resolution)

    def update_pause_values(self, min_entry, max_entry):
        self.min_pause = int(min_entry.get())
        self.max_pause = int(max_entry.get())
        self.log_message(f"Pause values updated: min={self.min_pause}, max={self.max_pause}")
        # Обновление значений в файле ini
        config = configparser.ConfigParser()
        config.read('file.ini')
        config['RandomPause'] = {
            'min': str(self.min_pause),
            'max': str(self.max_pause)
        }
        with open('file.ini', 'w') as configfile:
            config.write(configfile)

    def update_settings_values(self, checkbtn_entry, boostawaittime_entry, closeawaittime_entry, height_entry, width_entry):
        self.checkbtn = int(checkbtn_entry.get())
        self.boostawaittime = int(boostawaittime_entry.get())
        self.closeawaittime = int(closeawaittime_entry.get())
        self.height = int(height_entry.get())
        self.width = int(width_entry.get())
        self.log_message(f"Settings values updated: checkbtn={self.checkbtn}, boostawaittime={self.boostawaittime}, closeawaittime={self.closeawaittime}, width={self.width}, height={self.height}")
        # Обновление значений в файле ini
        config = configparser.ConfigParser()
        config.read('file.ini')
        config['SettingsClicker'] = {
            'checkbtn': str(self.checkbtn),
            'boostawaittime': str(self.boostawaittime),
            'closeawaittime': str(self.closeawaittime),
            'height': str(self.height),
            'width': str(self.width),
            'resolutionemu960': str(self.resolutionemu960),
            'resolutionemu1600': str(self.resolutionemu1600),


        }
        with open('file.ini', 'w') as configfile:
            config.write(configfile)

    def auto_update_collecting_bounds(self):
            try:
                window = gw.getWindowsWithTitle(self.window_name)[0]
                left, top, right, bottom = 0, 0, window.width, window.height
                self.update_collecting_bounds(
                    tk.StringVar(value=left),
                    tk.StringVar(value=top),
                    tk.StringVar(value=right),
                    tk.StringVar(value=bottom)
                )
            except Exception as e:
                self.log_message(f"Error: {e}")

    def load_images(self):
        images = []
        for filename in os.listdir(self.image_folder):
            if filename.endswith('.png') and filename not in []:
                image_path = os.path.join(self.image_folder, filename)
                image = cv2.imread(image_path, cv2.IMREAD_COLOR)
                if image is not None:
                    images.append((filename, image))
        return images


    def save_profile_settings(self, profile, update_only=None):
        config = configparser.ConfigParser()
        config.read('file.ini')

        # Получаем текущие значения из файла, если они существуют
        if profile in config:
            current_values = config[profile]
        else:
            current_values = {}

        # Обновляем настройки для текущего профиля, используя значения из файла в качестве значений по умолчанию
        config[profile] = {
            'name': str(self.active.get(profile, current_values.get('name', f'{profile}'))),
            'active': str(self.active.get(profile, current_values.get('active', 'False'))),
            'checkbutton': str(self.active.get(profile, current_values.get('checkbutton', 'False'))),
            'closebtn': str(self.active.get(profile, current_values.get('closebtn', 'False'))),
            'boost_label': str(self.boost_label.get(profile, current_values.get('boost_label', '0'))),
            'max_energy': str(self.max_energy.get(profile, current_values.get('max_energy', '5000'))),
            'energy_per_click': str(self.energy_per_click.get(profile, current_values.get('energy_per_click', '9'))),
            'energy_recovery_rate': str(self.energy_recovery_rate.get(profile, current_values.get('energy_recovery_rate', '10'))),
            'current_energy': str(self.current_energy.get(profile, current_values.get('current_energy', '5000'))),
            'timeCurrentEnergyNULL': str(self.timeCurrentEnergyNULL.get(profile, current_values.get('timeCurrentEnergyNULL', '0'))),
            'timeCurrentEnergyFULL': str(self.timeCurrentEnergyFULL.get(profile, current_values.get('timeCurrentEnergyFULL', '0'))),
            'boosts_used': str(self.boosts_used.get(profile, current_values.get('boosts_used', 'False'))),
            'boost_time': str(self.boost_time.get(profile, current_values.get('boost_time', '3600'))),
            'booststarttimer': str(self.booststarttimer.get(profile, current_values.get('booststarttimer', '0'))),
            'boosttimetorecharge': str(self.boosttimetorecharge.get(profile, current_values.get('boosttimetorecharge', '0'))),
            'boostcooldown': str(self.boostcooldown.get(profile, current_values.get('boostcooldown', '0'))),
            'usedAllBoost': str(self.usedAllBoost.get(profile, current_values.get('usedAllBoost')))
        }
        # Если update_only не None, обновляем только указанные поля
        if update_only:
            for key, value in update_only.items():
                config[profile][key] = str(value)
        with open('file.ini', 'w') as configfile:
            config.write(configfile)



    def calculate_time(self):
        total_time_seconds = self.max_energy[self.profile] / self.energy_recovery_rate[self.profile]
        return int(total_time_seconds)

    def calculate_time_ToBoost(self):
        # Текущее время в UTC
        now = datetime.datetime.now(datetime.timezone.utc)
        # Время следующей полуночи в UTC
        next_midnight = datetime.datetime.combine(now.date() + datetime.timedelta(days=1), datetime.time.min, tzinfo=datetime.timezone.utc)
        # Вычисление оставшегося времени до полуночи в секундах
        remaining_time_seconds = (next_midnight - now).total_seconds()
        return int(remaining_time_seconds)

    def clickToBoostEnergy(self):
        utc_boost = self.check_time_UTC()
        currentTime = int(time.time())
        if self.profile == 'ClickerBot1' and currentTime >= self.boostcooldown[self.profile] and self.boosts_used[self.profile] < self.boost_label[self.profile]:
            time.sleep(2)

            if self.imageAwait('profiles/1-4.png', self.boostawaittime):
                time.sleep(2)
                if self.imageAwait('profiles/1-5.png', self.boostawaittime):
                    time.sleep(2)
                    if self.imageAwait('profiles/1-6.png', self.boostawaittime):
                        time.sleep(2)
                        self.current_energy[self.profile] = self.max_energy[self.profile]
                        self.boosts_used[self.profile] += 1
                        self.booststarttimer[self.profile] = int(time.time())
                        self.boosttimetorecharge[self.profile] = self.booststarttimer[self.profile] + self.calculate_time_ToBoost()
                        self.save_profile_settings(self.profile)
                        profileIndex = ''.join(filter(str.isdigit, self.profile))  # Извлечение числа из строки профиля
                        bot_name = self.get_bot_name(self.profile)
                        bot_name_edit = self.log_message_name(bot_name)
                        self.log_message(f"Profile {profileIndex} {bot_name_edit} Boosts used: {self.boosts_used[self.profile]}", bot_name=bot_name)
                        self.log_message(f"Clicked start")
                        self.usedBoost = True
                        time.sleep(2)
                        ready_profiles = self.recover_energy_for_all_profiles()
                        if ready_profiles:
                            time.sleep(1)
                            telegram_window = gw.getWindowsWithTitle(self.window_name)[0]
                            self.clickerLoop(telegram_window)
                        if self.boosts_used[self.profile] == self.boost_label[self.profile] and self.usedAllBoost[self.profile] == False:
                            self.usedAllBoost[self.profile] = True
                            self.save_profile_settings(self.profile)
                            return False
                    else:
                        self.usedBoost = True
                        return False
                else:
                    self.usedBoost = True
                    return False
            else:
                self.usedBoost = True
                return False

        if self.profile == 'ClickerBot2' and currentTime >= self.boostcooldown[self.profile] and self.boosts_used[self.profile] < self.boost_label[self.profile]: #
            time.sleep(2)
            if self.imageAwait('profiles/2-3.png', self.boostawaittime):
                time.sleep(2)
                if self.imageAwait('profiles/2-4.png', self.boostawaittime):
                    time.sleep(2)
                    if self.imageAwait('profiles/2-5.png', self.boostawaittime):
                        time.sleep(2)
                        self.current_energy[self.profile] = self.max_energy[self.profile]
                        self.boosts_used[self.profile] += 1
                        self.booststarttimer[self.profile] = int(time.time())
                        self.boostcooldown[self.profile] = int(time.time()) + self.boost_time[self.profile]  # Добавляем 3600 секунд (1 час) к текущему времени
                        self.boosttimetorecharge[self.profile] = self.booststarttimer[self.profile] + self.calculate_time_ToBoost()
                        self.save_profile_settings(self.profile)
                        profileIndex = ''.join(filter(str.isdigit, self.profile))  # Извлечение числа из строки профиля
                        bot_name = self.get_bot_name(self.profile)
                        bot_name_edit = self.log_message_name(bot_name)
                        self.log_message(f"Profile {profileIndex} {bot_name_edit} Boosts used: {self.boosts_used[self.profile]}", bot_name=bot_name)
                        self.log_message(f"Clicked start")
                        self.usedBoost = True
                        time.sleep(2)
                        ready_profiles = self.recover_energy_for_all_profiles()
                        if ready_profiles:
                            time.sleep(1)
                            telegram_window = gw.getWindowsWithTitle(self.window_name)[0]
                            self.clickerLoop(telegram_window)
                        if self.boosts_used[self.profile] == self.boost_label[self.profile] and self.usedAllBoost[self.profile] == False:
                            self.boosttimetorecharge[self.profile] = self.booststarttimer[self.profile] + self.calculate_time_ToBoost()
                            self.usedAllBoost[self.profile] = True
                            self.save_profile_settings(self.profile)
                            return False
                    else:
                        self.usedBoost = True
                        return False
                else:
                    self.usedBoost = True
                    return False
            else:
                self.usedBoost = True
                return False

        if self.profile == 'ClickerBot3' and currentTime >= self.boostcooldown[self.profile] and self.boosts_used[self.profile] < self.boost_label[self.profile]: #
            time.sleep(2)
            if self.imageAwait('profiles/3-3.png', self.boostawaittime):
                time.sleep(2)
                if self.imageAwait('profiles/3-4.png', self.boostawaittime):
                    time.sleep(2)
                    if self.imageAwait('profiles/3-5.png', self.boostawaittime):
                        time.sleep(2)
                        self.current_energy[self.profile] = self.max_energy[self.profile]
                        self.boosts_used[self.profile] += 1
                        self.booststarttimer[self.profile] = int(time.time())
                        self.boostcooldown[self.profile] = int(time.time()) + self.boost_time[self.profile]  # Добавляем 3600 секунд (1 час) к текущему времени
                        self.boosttimetorecharge[self.profile] = self.booststarttimer[self.profile] + self.calculate_time_ToBoost()
                        self.save_profile_settings(self.profile)
                        profileIndex = ''.join(filter(str.isdigit, self.profile))  # Извлечение числа из строки профиля
                        bot_name = self.get_bot_name(self.profile)
                        bot_name_edit = self.log_message_name(bot_name)
                        self.log_message(f"Profile {profileIndex} {bot_name_edit} Boosts used: {self.boosts_used[self.profile]}", bot_name=bot_name)
                        self.log_message(f"Clicked start")
                        self.usedBoost = True
                        time.sleep(2)
                        ready_profiles = self.recover_energy_for_all_profiles()
                        if ready_profiles:
                            time.sleep(1)
                            telegram_window = gw.getWindowsWithTitle(self.window_name)[0]
                            self.clickerLoop(telegram_window)
                        if self.boosts_used[self.profile] == self.boost_label[self.profile] and self.usedAllBoost[self.profile] == False:
                            self.boosttimetorecharge[self.profile] = self.booststarttimer[self.profile] + self.calculate_time_ToBoost()
                            self.usedAllBoost[self.profile] = True
                            self.save_profile_settings(self.profile)
                            return False
                    else:
                        self.usedBoost = True
                        return False
                else:
                    self.usedBoost = True
                    return False
            else:
                self.usedBoost = True
                return False
        if self.profile == 'ClickerBot4' and self.boosts_used[self.profile] < self.boost_label[self.profile] and utc_boost:
            time.sleep(2)
            if self.imageAwait('profiles/4-3.png', self.boostawaittime):
                time.sleep(2)
                if self.imageAwait('profiles/4-4.png', self.boostawaittime):
                    time.sleep(2)
                    if self.imageAwait('profiles/4-5.png', self.boostawaittime):
                        time.sleep(2)
                        self.current_energy[self.profile] = self.max_energy[self.profile]
                        self.boosts_used[self.profile] += 1
                        self.booststarttimer[self.profile] = int(time.time())
                        self.boosttimetorecharge[self.profile] = self.booststarttimer[self.profile] + self.calculate_time_ToBoost()
                        self.save_profile_settings(self.profile)
                        profileIndex = ''.join(filter(str.isdigit, self.profile))  # Извлечение числа из строки профиля
                        bot_name = self.get_bot_name(self.profile)
                        bot_name_edit = self.log_message_name(bot_name)
                        self.log_message(f"Profile {profileIndex} {bot_name_edit} Boosts used: {self.boosts_used[self.profile]}", bot_name=bot_name)
                        self.log_message(f"Clicked start")
                        self.usedBoost = True
                        time.sleep(2)
                        ready_profiles = self.recover_energy_for_all_profiles()
                        if ready_profiles:
                            time.sleep(1)
                            telegram_window = gw.getWindowsWithTitle(self.window_name)[0]
                            self.clickerLoop(telegram_window)
                        if self.boosts_used[self.profile] == self.boost_label[self.profile] and self.usedAllBoost[self.profile] == False:
                            self.boosttimetorecharge[self.profile] = self.booststarttimer[self.profile] + self.calculate_time_ToBoost()
                            self.usedAllBoost[self.profile] = True
                            self.save_profile_settings(self.profile)
                            return False
                    else:
                        self.usedBoost = True
                        return False
                else:
                    self.usedBoost = True
                    return False
            else:
                self.usedBoost = True
                return False
            #============================================================================================================================================================
        if self.profile == 'ClickerBot5' and currentTime >= self.boostcooldown[self.profile] and self.boosts_used[self.profile] < self.boost_label[self.profile]:
            time.sleep(2)

            if self.imageAwait('profiles/5-3.png', self.boostawaittime):
                time.sleep(2)
                if self.imageAwait('profiles/5-4.png', self.boostawaittime):
                    time.sleep(2)
                    if self.imageAwait('profiles/5-5.png', self.boostawaittime):
                        time.sleep(2)
                        if self.imageAwait('profiles/5-6.png', self.boostawaittime):
                            time.sleep(2)
                            self.current_energy[self.profile] = self.max_energy[self.profile]
                            self.boosts_used[self.profile] += 1
                            self.booststarttimer[self.profile] = int(time.time())
                            self.boostcooldown[self.profile] = int(time.time()) + self.boost_time[self.profile]  # Добавляем 3600 секунд (1 час) к текущему времени
                            self.boosttimetorecharge[self.profile] = self.booststarttimer[self.profile] + self.calculate_time_ToBoost()
                            self.save_profile_settings(self.profile)
                            profileIndex = ''.join(filter(str.isdigit, self.profile))  # Извлечение числа из строки профиля
                            bot_name = self.get_bot_name(self.profile)
                            bot_name_edit = self.log_message_name(bot_name)
                            self.log_message(f"Profile {profileIndex} {bot_name_edit} Boosts used: {self.boosts_used[self.profile]}", bot_name=bot_name)
                            self.log_message(f"Clicked start")
                            self.usedBoost = True
                            time.sleep(2)
                            ready_profiles = self.recover_energy_for_all_profiles()
                            if ready_profiles:
                                time.sleep(1)
                                telegram_window = gw.getWindowsWithTitle(self.window_name)[0]
                                self.clickerLoop(telegram_window)
                            if self.boosts_used[self.profile] == self.boost_label[self.profile] and self.usedAllBoost[self.profile] == False:
                                self.usedAllBoost[self.profile] = True
                                self.save_profile_settings(self.profile)
                                return False
                        else:
                            self.usedBoost = True
                            return False
                else:
                    self.usedBoost = True
                    return False
            else:
                self.usedBoost = True
                return False

        if self.profile == 'ClickerBot6' and currentTime >= self.boostcooldown[self.profile] and self.boosts_used[self.profile] < self.boost_label[self.profile]: #
            time.sleep(2)
            if self.imageAwait('profiles/6-3.png', self.boostawaittime):
                time.sleep(2)
                if self.imageAwait('profiles/6-4.png', self.boostawaittime):
                    time.sleep(2)
                    if self.imageAwait('profiles/6-5.png', self.boostawaittime):
                        time.sleep(2)
                        self.current_energy[self.profile] = self.max_energy[self.profile]
                        self.boosts_used[self.profile] += 1
                        self.booststarttimer[self.profile] = int(time.time())
                        self.boostcooldown[self.profile] = int(time.time()) + self.boost_time[self.profile]  # Добавляем 3600 секунд (1 час) к текущему времени
                        self.boosttimetorecharge[self.profile] = self.booststarttimer[self.profile] + self.calculate_time_ToBoost()
                        self.save_profile_settings(self.profile)
                        bot_name = self.get_bot_name(self.profile)
                        bot_name_edit = self.log_message_name(bot_name)
                        profileIndex = ''.join(filter(str.isdigit, self.profile))  # Извлечение числа из строки профиля
                        self.log_message(f"Profile {profileIndex} {bot_name_edit} Boosts used: {self.boosts_used[self.profile]}", bot_name=bot_name)
                        self.log_message(f"Clicked start")
                        self.usedBoost = True
                        time.sleep(2)
                        ready_profiles = self.recover_energy_for_all_profiles()
                        if ready_profiles:
                            time.sleep(1)
                            telegram_window = gw.getWindowsWithTitle(self.window_name)[0]
                            self.clickerLoop(telegram_window)
                        if self.boosts_used[self.profile] == self.boost_label[self.profile] and self.usedAllBoost[self.profile] == False:
                            self.boosttimetorecharge[self.profile] = self.booststarttimer[self.profile] + self.calculate_time_ToBoost()
                            self.usedAllBoost[self.profile] = True
                            self.save_profile_settings(self.profile)
                            return False
                    else:
                        self.usedBoost = True
                        return False
                else:
                    self.usedBoost = True
                    return False
            else:
                self.usedBoost = True
                return False

        if self.profile == 'ClickerBot7' and currentTime >= self.boostcooldown[self.profile] and self.boosts_used[self.profile] < self.boost_label[self.profile]: #
            time.sleep(2)
            if self.imageAwait('profiles/7-3.png', self.boostawaittime):
                time.sleep(2)
                if self.imageAwait('profiles/7-4.png', self.boostawaittime):
                    time.sleep(2)
                    if self.imageAwait('profiles/7-5.png', self.boostawaittime):
                        time.sleep(2)
                        if self.imageAwait('profiles/7-6.png', self.boostawaittime):
                            time.sleep(2)
                            self.current_energy[self.profile] = self.max_energy[self.profile]
                            self.boosts_used[self.profile] += 1
                            self.booststarttimer[self.profile] = int(time.time())
                            self.boostcooldown[self.profile] = int(time.time()) + self.boost_time[self.profile]  # Добавляем 3600 секунд (1 час) к текущему времени
                            self.boosttimetorecharge[self.profile] = self.booststarttimer[self.profile] + self.calculate_time_ToBoost()
                            self.save_profile_settings(self.profile)
                            bot_name = self.get_bot_name(self.profile)
                            bot_name_edit = self.log_message_name(bot_name)
                            profileIndex = ''.join(filter(str.isdigit, self.profile))  # Извлечение числа из строки профиля
                            self.log_message(f"Profile {profileIndex} {bot_name_edit} Boosts used: {self.boosts_used[self.profile]}", bot_name=bot_name)
                            self.log_message(f"Clicked start")
                            self.usedBoost = True
                            time.sleep(2)
                            ready_profiles = self.recover_energy_for_all_profiles()
                            if ready_profiles:
                                time.sleep(1)
                                telegram_window = gw.getWindowsWithTitle(self.window_name)[0]
                                self.clickerLoop(telegram_window)
                            if self.boosts_used[self.profile] == self.boost_label[self.profile] and self.usedAllBoost[self.profile] == False:
                                self.boosttimetorecharge[self.profile] = self.booststarttimer[self.profile] + self.calculate_time_ToBoost()
                                self.usedAllBoost[self.profile] = True
                                self.save_profile_settings(self.profile)
                                return False
                        else:
                            self.usedBoost = True
                            return False
                else:
                    self.usedBoost = True
                    return False
            else:
                self.usedBoost = True
                return False
        if self.profile == 'ClickerBot8' and self.boosts_used[self.profile] < self.boost_label[self.profile] and utc_boost:
            time.sleep(2)
            if self.imageAwait('profiles/8-1.png', self.boostawaittime):
                time.sleep(2)
                if self.imageAwait('profiles/8-3.png', self.boostawaittime):
                    time.sleep(2)
                    if self.imageAwait('profiles/8-3.png', self.boostawaittime):
                        time.sleep(2)
                        self.current_energy[self.profile] = self.max_energy[self.profile]
                        self.boosts_used[self.profile] += 1
                        self.booststarttimer[self.profile] = int(time.time())
                        self.boostcooldown[self.profile] = int(time.time()) + self.boost_time[self.profile]  # Добавляем 3600 секунд (1 час) к текущему времени
                        self.boosttimetorecharge[self.profile] = self.booststarttimer[self.profile] + self.calculate_time_ToBoost()
                        self.save_profile_settings(self.profile)
                        bot_name = self.get_bot_name(self.profile)
                        bot_name_edit = self.log_message_name(bot_name)
                        profileIndex = ''.join(filter(str.isdigit, self.profile))  # Извлечение числа из строки профиля
                        self.log_message(f"Profile {profileIndex} {bot_name_edit} Boosts used: {self.boosts_used[self.profile]}")
                        self.log_message(f"Clicked start")
                        self.usedBoost = True
                        time.sleep(2)
                        ready_profiles = self.recover_energy_for_all_profiles()
                        if ready_profiles:
                            time.sleep(1)
                            telegram_window = gw.getWindowsWithTitle(self.window_name)[0]
                            self.clickerLoop(telegram_window)
                        if self.boosts_used[self.profile] == self.boost_label[self.profile] and self.usedAllBoost[self.profile] == False:
                            self.boosttimetorecharge[self.profile] = self.booststarttimer[self.profile] + self.calculate_time_ToBoost()
                            self.usedAllBoost[self.profile] = True
                            self.save_profile_settings(self.profile)
                            return False
                    else:
                        self.usedBoost = True
                        return False
                else:
                    self.usedBoost = True
                    return False
            else:
                self.usedBoost = True
                return False
        return False

    def check_time_UTC(self):
            config = configparser.ConfigParser()
            config.read('file.ini')
            current_time = int(time.time())
            for profile in config.sections():
                    if profile.startswith('ClickerBot'):
                        boosttimetorecharge = int(config[profile].get('boosttimetorecharge', 0))
                        if current_time >= boosttimetorecharge:
                            bot_name = self.get_bot_name(profile)
                            # self.log_message(f"Profile {bot_name} is ready boost.")
                            return profile
            return None

    def check_profiles_for_energy(self):
        self.log_message(f"Checking...\n")
        config = configparser.ConfigParser()
        config.read('file.ini')
        current_time = int(time.time())
        currentTimeUTC = int(datetime.datetime.now(datetime.timezone.utc).timestamp())

        # Первый этап: Проверка всех профилей на условие currentTimeUTC >= boosttimetorecharge
        for profile in config.sections():
            if profile.startswith('ClickerBot'):
                self.load_profile_settings(profile)
                boosttimetorecharge = int(config[profile].get('boosttimetorecharge', 0))

                if currentTimeUTC >= boosttimetorecharge:
                    self.boosts_used[profile] = 0
                    self.usedAllBoost[profile] = False
                    self.save_profile_settings(profile, update_only={'boosts_used': 0})
                    self.save_profile_settings(self.profile)
                    print(f"{profile} CurrentTimeUTC: {currentTimeUTC}, boosttimetorecharge: {boosttimetorecharge}")

        # Второй этап: Выполнение остальных проверок для каждого профиля
        for profile in config.sections():
            if profile.startswith('ClickerBot'):
                self.load_profile_settings(profile)
                timeCurrentEnergyNULL = int(config[profile].get('timecurrentenergynull', 0))
                timeCurrentEnergyFULL = int(config[profile].get('timecurrentenergyfull', 0))

                # Убедитесь, что значения current_energy и max_energy инициализированы
                if profile not in self.current_energy or profile not in self.max_energy:
                    bot_name = self.get_bot_name(profile)
                    bot_name_edit = self.log_message_name(bot_name)
                    self.log_message(f"Profile {bot_name} not initialized properly.")
                    continue  # Пропустите этот профиль, если он не инициализирован

                active1 = config[profile].get('active', 'True') == 'True'
                if current_time >= timeCurrentEnergyFULL and active1:
                    self.current_energy[profile] = self.max_energy[profile]
                    self.save_profile_settings(profile, update_only={'current_energy': self.max_energy[profile]})
                    bot_name = self.get_bot_name(profile)
                    bot_name_edit = self.log_message_name(bot_name)
                    self.log_message(f"Profile {bot_name_edit} is ready with max energy", bot_name=bot_name)
                    return profile

        return None

    def imageAwait(self, image_name, timeout):
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.click_image(image_name):
                return True
            time.sleep(0.5)  # Пауза между проверками
        return False

    def click_image(self, image_name):
        # print(f'RUN click_image: {image_name}')
        image_path = os.path.join(self.image_folder, image_name)
        template = cv2.imread(image_path, cv2.IMREAD_COLOR)
        if template is not None:
            screenshot = self.grab_screen((0, 0, self.screen_width, self.screen_height))
            position = self.find_template_on_screen(template, screenshot)
            if position:
                center_x = position[0] + template.shape[1] // 2
                center_y = position[1] + template.shape[0] // 2
                self.clickerClick(center_x, center_y)
                # print(f"Clicked on {image_name} ++++")
                return True
        # self.log_message(f"Image {image_name} not found")
        return False

    def close_current_window(self):
        config = configparser.ConfigParser()
        config.read('file.ini')
        self.closeawaittime = int(config.get('SettingsClicker', 'closeawaittime', fallback=4))
        time.sleep(2)
        if self.profile == 'ClickerBot1':
            time.sleep(2)
            self.imageAwait('close/close-1.png', self.closeawaittime)
            self.closebtn = config.getboolean('ClickerBot1', 'closebtn', fallback=True)
            if self.closebtn:
                time.sleep(2)
                self.imageAwait('close/close-1-2.png', self.closeawaittime)
            time.sleep(2)
            self.imageAwait('close/back.png', self.closeawaittime)
        if self.profile == 'ClickerBot2':
            time.sleep(2)
            self.imageAwait('close/close-2.png', self.closeawaittime)
            self.closebtn = config.getboolean('ClickerBot2', 'closebtn', fallback=True)
            if self.closebtn:
                time.sleep(2)
                self.imageAwait('close/close-2-2.png', self.closeawaittime)
            time.sleep(2)
            self.imageAwait('close/back.png', self.closeawaittime)
        if self.profile == 'ClickerBot3':
            time.sleep(2)
            self.imageAwait('close/close-3.png', self.closeawaittime)
            self.closebtn = config.getboolean('ClickerBot3', 'closebtn', fallback=True)
            if self.closebtn:
                time.sleep(2)
                self.imageAwait('close/close-3-2.png', self.closeawaittime)
            time.sleep(2)
            self.imageAwait('close/back.png', self.closeawaittime)
        if self.profile == 'ClickerBot4':
            time.sleep(2)
            self.imageAwait('close/close-4.png', self.closeawaittime)
            self.closebtn = config.getboolean('ClickerBot4', 'closebtn', fallback=True)
            if self.closebtn:
                time.sleep(2)
                self.imageAwait('close/close-4-2.png', self.closeawaittime)
            time.sleep(2)
            self.imageAwait('close/back.png', self.closeawaittime)
        if self.profile == 'ClickerBot5':
            time.sleep(2)
            self.imageAwait('close/close-5.png', self.closeawaittime)
            self.closebtn = config.getboolean('ClickerBot5', 'closebtn', fallback=True)
            if self.closebtn:
                time.sleep(2)
                self.imageAwait('close/close-5-2.png', self.closeawaittime)
            time.sleep(2)
            self.imageAwait('close/back.png', self.closeawaittime)
        if self.profile == 'ClickerBot6':
            time.sleep(2)
            self.imageAwait('close/close-6.png', self.closeawaittime)
            self.closebtn = config.getboolean('ClickerBot6', 'closebtn', fallback=True)
            if self.closebtn:
                time.sleep(2)
                self.imageAwait('close/close-6-2.png', self.closeawaittime)
            time.sleep(2)
            self.imageAwait('close/back.png', self.closeawaittime)
        if self.profile == 'ClickerBot7':
            time.sleep(2)
            self.imageAwait('close/close-7.png', self.closeawaittime)
            self.closebtn = config.getboolean('ClickerBot7', 'closebtn', fallback=True)
            if self.closebtn:
                time.sleep(2)
                self.imageAwait('close/close-7-2.png', self.closeawaittime)
            time.sleep(2)
            self.imageAwait('close/back.png', self.closeawaittime)
        if self.profile == 'ClickerBot8':
            time.sleep(2)
            self.imageAwait('close/close-8.png', self.closeawaittime)
            self.closebtn = config.getboolean('ClickerBot8', 'closebtn', fallback=True)
            if self.closebtn:
                time.sleep(2)
                self.imageAwait('close/close-8-2.png', self.closeawaittime)
            time.sleep(2)
            self.imageAwait('close/back.png', self.closeawaittime)
        time.sleep(2)
        return True

    # кликает на начальной кнопке CLAIM
    def switch_to_profile(self, profile):
        profileIndex = ''.join(filter(str.isdigit, profile))
        profileIndex_edit = self.log_message_name(profileIndex)
        self.log_message(f"Switching to profile {profileIndex_edit}", bot_name=profileIndex_edit)
        match = re.search(r'\d+', profile)
        if match:
            profile_number = match.group()
            if self.imageAwait(f'profiles/{profile_number}.png', 5):
                print(f'Switched to profile {profile_number}')
            else:
                print(f'Failed to switch to profile {profile_number}')
            time.sleep(3)
            if self.imageAwait(f'profiles/{profile_number}-1.png', 5):
                print(f'{profile_number}-1.png found')
            else:
                bot_name = self.get_bot_name(profile)
                self.log_message(f'Failed to click start for profile {bot_name}')
            time.sleep(3)

            # Словарь для хранения соответствий профилей и имен файлов
            profile_files = {
                '1': 'profiles/1-2.png',
                '2': 'profiles/2-2.png',
                '3': 'profiles/3-2.png',
                '4': 'profiles/4-2.png',
                '5': 'profiles/5-2.png',
                '6': 'profiles/6-2.png',
                '7': 'profiles/7-2.png',
                '8': 'profiles/8-2.png'
            }

            # Обработка профилей 1-8
            if profile_number in profile_files:
                config = configparser.ConfigParser()
                config.read('file.ini')
                checkbutton = config[profile].get('checkbutton', 'True') == 'True'
                print(f'checkbutton: {checkbutton}')
                if checkbutton:
                    time.sleep(3)
                    awaited_image = self.imageAwait(profile_files[profile_number], self.closeawaittime)
                    if awaited_image:
                        print('')

            time.sleep(2)
            self.profile = profile
            self.load_profile_settings(self.profile)

    def recover_energy_for_all_profiles(self):
        config = configparser.ConfigParser()
        config.read('file.ini')
        current_time = int(time.time())
        ready_profiles = []
        for profile in config.sections():
            if profile.startswith('ClickerBot'):
                timeCurrentEnergyNULL = int(config[profile].get('timeCurrentEnergyNULL', 0))
                timeCurrentEnergyFULL = int(config[profile].get('timeCurrentEnergyFULL', 0))
                current_energy = int(config[profile].get('current_energy', 0))
                max_energy = int(config[profile].get('max_energy', 0))
                active = config[profile].get('active', 'True') == 'True'
                if current_time >= timeCurrentEnergyFULL:
                    current_energy = max_energy
                    # self.log_message(f"Current_time for {profile} is {timeCurrentEnergyFULL}")
                if current_energy >= max_energy and active == True:
                    config[profile]['current_energy'] = str(max_energy)
                    ready_profiles.append(profile)
                    # self.log_message(f"Recovered energy for {profile}: {config[profile]['current_energy']}")
        with open('file.ini', 'w') as configfile:
            config.write(configfile)
        return ready_profiles

    def clickerLoop(self, telegram_window):
        while self.current_energy[self.profile] >= self.energy_per_click[self.profile]:
                    if not self.running.is_set():
                        self.running.wait()  # wait until running is set

                    if self.paused:
                        time.sleep(0.1)
                        continue

                    window_rect = (
                        telegram_window.left, telegram_window.top, telegram_window.width, telegram_window.height
                    )

                    if telegram_window != []:
                        try:
                            telegram_window.activate()
                        except:
                            telegram_window.minimize()
                            telegram_window.restore()

                    screenshot = self.grab_screen(window_rect)
                    images = self.load_images()

                    if not images:
                        self.log_message("No images to click.")
                        break

                    for filename, template in images:
                        position = self.find_template_on_screen(template, screenshot)
                        if position:
                            # Центрирование клика по изображению
                            center_x = position[0] + template.shape[1] // 2
                            center_y = position[1] + template.shape[0] // 2

                            # Добавление небольшого смещения
                            x_offset = random.randint(-int(template.shape[1] * 0.1), int(template.shape[1] * 0.1))
                            y_offset = random.randint(-int(template.shape[0] * 0.1), int(template.shape[0] * 0.1))
                            click_x = center_x + telegram_window.left + x_offset
                            click_y = center_y + telegram_window.top + y_offset

                            # Убедитесь, что смещение не выводит курсор за пределы окна
                            click_x = max(telegram_window.left, min(click_x, telegram_window.left + telegram_window.width))
                            click_y = max(telegram_window.top, min(click_y, telegram_window.top + telegram_window.height))

                            rand1 = random.randint(31, 39)
                            self.click_with_movement(click_x, click_y, click_x + rand1, click_y)

    def randomAwait(self):
        # Рандомное время ожидания перед началом кликов
        random_wait_time = random.randint(15, 70)  # От 1.5 до 7 минут
        self.log_message(f"Waiting for {random_wait_time} seconds before resuming clicks...")
        time.sleep(random_wait_time)

    def bot_loop(self):
        try:
            check = gw.getWindowsWithTitle(self.window_name)

            if not check:
                self.log_message(f"\nWindow {self.window_name} not found!\nPlease, select another window.")
                self.window_name = self.choose_window_gui()

            if not self.window_name or not gw.getWindowsWithTitle(self.window_name):
                self.log_message("\nThe specified window could not be found!\nStart the game, then restart the bot!")
                return
            else:
                current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.log_message(f'\n{current_time}')
                self.log_message(f"Window {self.window_name} found\nPress 'A' to pause\n'S' to stop bot")

            telegram_window = gw.getWindowsWithTitle(self.window_name)[0]
            current_profile_selected = False

            while self.running.is_set():
                if not self.running.is_set():
                    self.running.wait()  # wait until running is set

                if self.paused:
                    time.sleep(0.1)
                    continue

                # Проверка профилей на наличие максимальной энергии, если текущий профиль не выбран
                if not current_profile_selected:
                    next_profile = self.check_profiles_for_energy()
                    if next_profile == None:
                        print('')

                    while not next_profile:
                        if not self.running.is_set():
                            self.running.wait()  # wait until running is set

                        if self.paused:
                            time.sleep(0.1)
                            continue

                        ready_profiles = self.recover_energy_for_all_profiles()
                        if ready_profiles:
                            next_profile = ready_profiles[0]
                            break
                    if next_profile: #  and active1 == True
                        self.switch_to_profile(next_profile)
                        self.log_message(f"Сlicked start")
                        current_profile_selected = True
                while self.current_energy[self.profile] >= self.energy_per_click[self.profile]:
                    if not self.running.is_set():
                        self.running.wait()  # wait until running is set

                    if self.paused:
                        time.sleep(0.1)
                        continue

                    window_rect = (
                        telegram_window.left, telegram_window.top, telegram_window.width, telegram_window.height
                    )

                    if telegram_window != []:
                        try:
                            telegram_window.activate()
                        except:
                            telegram_window.minimize()
                            telegram_window.restore()

                    screenshot = self.grab_screen(window_rect)
                    images = self.load_images()

                    if not images:
                        self.log_message("No images to click.")
                        break

                    for filename, template in images:
                        position = self.find_template_on_screen(template, screenshot)
                        if position:
                            # Центрирование клика по изображению
                            center_x = position[0] + template.shape[1] // 2
                            center_y = position[1] + template.shape[0] // 2

                            # Добавление небольшого смещения
                            x_offset = random.randint(-int(template.shape[1] * 0.1), int(template.shape[1] * 0.1))
                            y_offset = random.randint(-int(template.shape[0] * 0.1), int(template.shape[0] * 0.1))
                            click_x = center_x + telegram_window.left + x_offset
                            click_y = center_y + telegram_window.top + y_offset

                            # Убедитесь, что смещение не выводит курсор за пределы окна
                            click_x = max(telegram_window.left, min(click_x, telegram_window.left + telegram_window.width))
                            click_y = max(telegram_window.top, min(click_y, telegram_window.top + telegram_window.height))

                            # self.clickTwoFingers(click_x, click_y)
                            rand1 = random.randint(31, 39)
                            rand2 = random.randint(10, 35)
                            self.click_with_movement(click_x, click_y, click_x + rand1, click_y, rand2)
                            # print(f"Clicked on {filename}")
                            # self.current_energy[self.profile] -= self.energy_per_click[self.profile]
                            # # print(f"Current energy after click: {self.current_energy[self.profile]}")
                            # self.save_profile_settings(self.profile)  # Сохранение текущей энергии в файл после каждого клика
                            # time.sleep(random.uniform(0.01, 0.15))  # Рандомная задержка между кликами

                self.log_message("Not enough energy. Waiting to recharge...")

                if self.current_energy[self.profile] < self.energy_per_click[self.profile]:
                    if self.clickToBoostEnergy():
                        print("")
                    else:
                        self.log_message("No boosts available")
                        self.timeCurrentEnergyNULL[self.profile] = int(time.time())
                        self.timeCurrentEnergyFULL[self.profile] = self.timeCurrentEnergyNULL[self.profile] + self.calculate_time()
                        self.save_profile_settings(self.profile)
                        self.log_message(f"Energy depleted. Waiting {self.calculate_time()} seconds to recharge")
                        current_time = datetime.datetime.now().strftime("%H:%M:%S")
                        bot_name = self.get_bot_name(self.profile)
                        bot_name_edit = self.log_message_name(bot_name)
                        profileIndex = ''.join(filter(str.isdigit, self.profile))
                        self.log_full_clicked(f"{current_time} [{profileIndex}] {bot_name_edit} full clicked", profileIndex, bot_name=bot_name)
                    current_profile_selected = False  # Сброс флага, чтобы снова проверить профили на наличие энергии

                    config = configparser.ConfigParser()
                    config.read('file.ini')
                    usedAllBoost = config[self.profile].get('usedAllBoost', 'True') == 'True'
                    currentTime = int(time.time())

                    for i in range(1, 9):
                        profile_name = f'ClickerBot{i}'
                        if self.profile == profile_name and (currentTime < self.boostcooldown[self.profile] or
                                                            self.boost_label[self.profile] <= self.boosts_used[self.profile] or
                                                            self.usedBoost == True or
                                                            usedAllBoost == True):
                            if self.close_current_window():
                                self.usedBoost = False
                                continue

                self.log_message("Checking...\n")
                while self.current_energy[self.profile] < self.max_energy[self.profile]:
                    time.sleep(1)
                    ready_profiles = self.recover_energy_for_all_profiles()

                    # config = configparser.ConfigParser()
                    # config.read('file.ini')
                    # min_pause = config.get('RandomPause', 'min')
                    # max_pause = config.get('RandomPause', 'min')

                    if ready_profiles:
                        next_profile = ready_profiles[0]
                        if next_profile:
                            # Рандомное время ожидания перед началом кликов
                            random_wait_time = random.randint(self.min_pause, self.max_pause)
                            self.log_message(f"Waiting for {random_wait_time} seconds before resuming clicks...")
                            time.sleep(random_wait_time)

                            self.switch_to_profile(next_profile)
                            # self.log_message(f"Switched to profile {next_profile}")
                            current_profile_selected = True
                            break  # Переключиться на новый профиль и начать заново

                self.log_message("Energy recharged. Resuming clicks...")

        except Exception as e:
            self.log_message(f"An error occurred: {e}")
            self.running.clear()
            self.log_message('STOP')

#============Bot==================================================================================================Bot

class Bot(BotBase):
    def __init__(self, log_widget):
        config = configparser.ConfigParser()
        config.read('file.ini')
        collecting_bounds = (
            int(config['BoundsBot']['left']),
            int(config['BoundsBot']['top']),
            int(config['BoundsBot']['right']),
            int(config['BoundsBot']['bottom'])
        )
        window_name = config['WindowBot']['name']
        super().__init__(log_widget, window_name, collecting_bounds, [], [])
        self.image_folder = 'img/bot/'
        self.screen_width = 1920
        self.screen_height = 1080
        self.load_profile_settings()

    def load_images(self):
        images = []
        for filename in os.listdir(self.image_folder):
            if filename.endswith('.png') and filename not in ['2.png']:
                image_path = os.path.join(self.image_folder, filename)
                image = cv2.imread(image_path, cv2.IMREAD_COLOR)
                if image is not None:
                    images.append((filename, image))
        return images
    def load_profile_settings(self):
        config = configparser.ConfigParser()
        config.read('file.ini')
        if 'Bot' not in config:
            config['Bot'] = {
                'click_delay': '0.1',
                'max_energy': '5000',
                'energy_per_click': '9',
                'energy_recovery_rate': '10',
                'current_energy': '5000',
                'timeawait' : '500'
            }
            with open('file.ini', 'w') as configfile:
                config.write(configfile)
        self.click_delay = float(config['Bot'].get('click_delay'))
        self.max_energy = int(config['Bot'].get('max_energy'))
        self.energy_per_click = int(config['Bot'].get('energy_per_click'))
        self.energy_recovery_rate = int(config['Bot'].get('energy_recovery_rate', 10))
        self.current_energy = int(config['Bot'].get('current_energy', self.max_energy))

    def save_profile_settings(self):
        config = configparser.ConfigParser()
        config.read('file.ini')
        config['Bot'] = {
            'click_delay': str(self.click_delay),
            'max_energy': str(self.max_energy),
            'energy_per_click': str(self.energy_per_click),
            'energy_recovery_rate': str(self.energy_recovery_rate),
            'current_energy': str(self.current_energy)
        }
        with open('file.ini', 'w') as configfile:
            config.write(configfile)

    def calculate_time(self):

        total_time_seconds = (self.max_energy / self.energy_recovery_rate) * 60
        seconds = int(total_time_seconds // 60)
        return seconds


    def click_image(self, image_name='1.png'):
        print(f'RUN click_image: {image_name}')
        image_path = os.path.join(self.image_folder, image_name)
        template = cv2.imread(image_path, cv2.IMREAD_COLOR)
        if template is not None:
            screenshot = self.grab_screen((0, 0, self.screen_width, self.screen_height))
            position = self.find_template_on_screen(template, screenshot)
            if position:
                center_x = position[0] + template.shape[1] // 2
                center_y = position[1] + template.shape[0] // 2
                self.clickerClick(center_x, center_y)
                print(f"Clicked on {image_name} ++++")
                return True
        print(f"Image {image_name} not found")
        return False

    def check_profiles_for_energy(self):
        config = configparser.ConfigParser()
        config.read('file.ini')
        ready_profiles = []
        for profile in config.sections():
            if profile.startswith('Bot'):
                current_energy = int(config[profile].get('current_energy', 0))
                max_energy = int(config[profile].get('max_energy', 0))
                energy_recovery_rate = int(config[profile].get('energy_recovery_rate', 10))
                if current_energy < max_energy:
                    current_energy = min(current_energy + energy_recovery_rate, max_energy)
                    config[profile]['current_energy'] = str(current_energy)
                    print(f"Recovered energy for {profile}: current_energy = {current_energy}")
                if current_energy >= max_energy:
                    ready_profiles.append(profile)
        with open('file.ini', 'w') as configfile:
            config.write(configfile)
        return ready_profiles

    def recover_energy_for_all_profiles(self):
        telegram_window = gw.getWindowsWithTitle(self.window_name)[0]
        while True:
            total_time_seconds = self.calculate_time()

            # Рандомное время ожидания перед началом кликов
            random_wait_time = random.randint(20, 130)  # От 1.5 до 7 минут
            print(f"Waiting for {random_wait_time} seconds before resuming clicks...")
            time.sleep(random_wait_time)

            print(f"Waiting for {total_time_seconds} seconds to recharge energy.")
            time.sleep(total_time_seconds)

            while self.current_energy >= self.energy_per_click:
                window_rect = (
                    telegram_window.left, telegram_window.top, telegram_window.width, telegram_window.height
                )

                if telegram_window != []:
                    try:
                        telegram_window.activate()
                    except:
                        telegram_window.minimize()
                        telegram_window.restore()

                screenshot = self.grab_screen(window_rect)
                images = self.load_images()

                if not images:
                    print("No images to click.")
                    break

                for filename, template in images:
                    position = self.find_template_on_screen(template, screenshot)
                    if position:
                        # Центрирование клика по изображению
                        center_x = position[0] + template.shape[1] // 2
                        center_y = position[1] + template.shape[0] // 2

                        # Добавление небольшого смещения
                        x_offset = random.randint(-int(template.shape[1] * 0.1), int(template.shape[1] * 0.1))
                        y_offset = random.randint(-int(template.shape[0] * 0.1), int(template.shape[0] * 0.1))
                        click_x = center_x + telegram_window.left + x_offset
                        click_y = center_y + telegram_window.top + y_offset

                        # Убедитесь, что смещение не выводит курсор за пределы окна
                        click_x = max(telegram_window.left, min(click_x, telegram_window.left + telegram_window.width))
                        click_y = max(telegram_window.top, min(click_y, telegram_window.top + telegram_window.height))

                        self.clickerClick(click_x, click_y)
                        print(f"Clicked on {filename}")
                        self.current_energy -= self.energy_per_click
                        print(f"Current energy after click: {self.current_energy}")
                        self.save_profile_settings()  # Сохранение текущей энергии в файл после каждого клика
                        time.sleep(random.uniform(0.01, 0.15))  # Рандомная задержка между кликами

            if self.current_energy < self.energy_per_click:
                self.current_energy = self.max_energy
                self.save_profile_settings()
                print(f"Energy recharged to max: {self.max_energy}")

    def save_profile_settings(self):
        config = configparser.ConfigParser()
        config.read('file.ini')
        config['Bot']['click_delay'] = str(self.click_delay)
        config['Bot']['max_energy'] = str(self.max_energy)
        config['Bot']['energy_per_click'] = str(self.energy_per_click)
        config['Bot']['energy_recovery_rate'] = str(self.energy_recovery_rate)
        config['Bot']['current_energy'] = str(self.current_energy)
        with open('file.ini', 'w') as configfile:
            config.write(configfile)


    def bot_loop(self):
        try:
            check = gw.getWindowsWithTitle(self.window_name)

            if not check:
                print(f"\nWindow {self.window_name} not found!\nPlease, select another window.")
                self.window_name = self.choose_window_gui()

            if not self.window_name or not gw.getWindowsWithTitle(self.window_name):
                print("\nThe specified window could not be found!\nStart the game, then restart the bot!")
                return
            else:
                print(f"\nWindow {self.window_name} found\nPress 'A' to pause\n'S' to stop bot")

            telegram_window = gw.getWindowsWithTitle(self.window_name)[0]

            while self.running.is_set():
                if self.paused:
                    time.sleep(0.1)
                    continue

                # Проверка профилей на наличие максимальной энергии
                next_profile = self.check_profiles_for_energy()
                while not next_profile:
                    print("No profiles with max energy. Waiting for energy to recharge...")
                    time.sleep(1)
                    ready_profiles = self.recover_energy_for_all_profiles()
                    if ready_profiles:
                        next_profile = ready_profiles[0]
                        break


                print(f"Current energy before click: {self.current_energy}")
                while self.current_energy >= self.energy_per_click:
                    window_rect = (
                        telegram_window.left, telegram_window.top, telegram_window.width, telegram_window.height
                    )

                    if telegram_window != []:
                        try:
                            telegram_window.activate()
                        except:
                            telegram_window.minimize()
                            telegram_window.restore()

                    screenshot = self.grab_screen(window_rect)
                    images = self.load_images()

                    if not images:
                        print("No images to click.")
                        break

                    for filename, template in images:
                        print(f"Checking image: {filename}")
                        position = self.find_template_on_screen(template, screenshot)
                        if position:
                            # Центрирование клика по изображению
                            center_x = position[0] + template.shape[1] // 2
                            center_y = position[1] + template.shape[0] // 2

                            # Добавление небольшого смещения
                            x_offset = random.randint(-int(template.shape[1] * 0.1), int(template.shape[1] * 0.1))
                            y_offset = random.randint(-int(template.shape[0] * 0.1), int(template.shape[0] * 0.1))
                            click_x = center_x + telegram_window.left + x_offset
                            click_y = center_y + telegram_window.top + y_offset

                            # Убедитесь, что смещение не выводит курсор за пределы окна
                            click_x = max(telegram_window.left, min(click_x, telegram_window.left + telegram_window.width))
                            click_y = max(telegram_window.top, min(click_y, telegram_window.top + telegram_window.height))

                            self.clickerClick(click_x, click_y)
                            print(f"Clicked on {filename}")
                            self.current_energy -= self.energy_per_click
                            print(f"Current energy after click: {self.current_energy}")
                            self.save_profile_settings()  # Сохранение текущей энергии в файл после каждого клика
                            time.sleep(random.uniform(0.01, 0.15))  # Рандомная задержка между кликами

                while self.current_energy < self.max_energy:
                    time.sleep(1)
                    self.current_energy = self.max_energy
                    self.save_profile_settings()
                    ready_profiles = self.recover_energy_for_all_profiles()

                    if ready_profiles:
                        next_profile = ready_profiles[0]
                        if next_profile:
                            # Рандомное время ожидания перед началом кликов
                            random_wait_time = random.randint(10, 15)  # От 1.5 до 7 минут
                            print(f"Waiting for {random_wait_time} seconds before resuming clicks...")
                            time.sleep(random_wait_time)

                print("Energy recharged. Resuming clicks...")

        except Exception as e:
            print(f"An error occurred: {e}")
            self.running.clear()
            print('STOP')




#========================== CipherBot ========================================================================== CipherBot
MORSE_CODE_DICT = {
    'A': '*-', 'B': '-***', 'C': '-*-*', 'D': '-**', 'E': '*', 'F': '**-*',
    'G': '--*', 'H': '****', 'I': '**', 'J': '*---', 'K': '-*-', 'L': '*-**',
    'M': '--', 'N': '-*', 'O': '---', 'P': '*--*', 'Q': '--*-', 'R': '*-*',
    'S': '***', 'T': '-', 'U': '**-', 'V': '***-', 'W': '*--', 'X': '-**-',
    'Y': '-*--', 'Z': '--**', '1': '*----', '2': '**---', '3': '***--',
    '4': '****-', '5': '*****', '6': '-****', '7': '--***', '8': '---**',
    '9': '----*', '0': '-----'
}

class CipherBot(BotBase):
    def __init__(self, log_widget):
        config = configparser.ConfigParser()
        config.read('file.ini')
        collecting_bounds = (
            int(config['BoundsCipher']['left']),
            int(config['BoundsCipher']['top']),
            int(config['BoundsCipher']['right']),
            int(config['BoundsCipher']['bottom'])
        )
        window_name5 = config['WindowCipher']['name']
        super().__init__(log_widget, window_name5, collecting_bounds, [], [])
        self.resolutionemu1600 = config.getboolean('SettingsClicker', 'resolutionemu1600', fallback=False)
        self.resolutionemu960 = config.getboolean('SettingsClicker', 'resolutionemu960', fallback=True)
        print(f'resolutionemu960 {self.resolutionemu960}')
        print(f'resolutionemu1600 {self.resolutionemu1600}')
        super().__init__(log_widget, window_name3, collecting_bounds, [], [])
        if self.resolutionemu1600:
            self.image_folder = 'img/1600x900/cipher/'
        elif self.resolutionemu960:
            self.image_folder = 'img/960x540/cipher/'

        self.screen_width = 1920  # Установите ширину экрана
        self.screen_height = 1080  # Установите высоту экрана
        self.cipher = config['CipherBot']['cipher']

    def update_cipher(self, window_name_entry):
        self.cipher = window_name_entry.get()
        self.log_message(f"Cipher name updated to: {self.cipher}")
        # Обновление значения в файле ini
        config = configparser.ConfigParser()
        config.read('file.ini')
        config['CipherBot']['cipher'] = self.cipher
        with open('file.ini', 'w') as configfile:
            config.write(configfile)
    def highlight_collecting_bounds(self):
        check = gw.getWindowsWithTitle(self.window_name)

        if not check:
            self.log_message(f"\nWindow {self.window_name} not found!\nPlease, select another window.")
            self.window_name = self.choose_window_gui()

        if not self.window_name or not gw.getWindowsWithTitle(self.window_name):
            self.log_message("\nThe specified window could not be found!\nStart the game, then restart the bot!")
            return

        telegram_window = gw.getWindowsWithTitle(self.window_name)[0]
        window_rect = (
            telegram_window.left, telegram_window.top, telegram_window.width, telegram_window.height
        )

        screenshot = self.grab_screen(window_rect, scale_factor=1.0)
        left, top, right, bottom = self.collecting_bounds
        cv2.rectangle(screenshot, (left, top), (right, bottom), (0, 255, 0), 2)

        # Отображение значений collecting_bounds рядом с границами
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        color = (0, 255, 0)
        thickness = 1

        # Отображение значений рядом с границами
        cv2.putText(screenshot, str(left), (left + 5, (top + bottom) // 2), font, font_scale, color, thickness)
        cv2.putText(screenshot, str(top), ((left + right) // 2, top + 20), font, font_scale, color, thickness)
        cv2.putText(screenshot, str(right), (right - 50, (top + bottom) // 2), font, font_scale, color, thickness)
        cv2.putText(screenshot, str(bottom), ((left + right) // 2, bottom - 15), font, font_scale, color, thickness)

        # Уменьшение размера изображения на 25 пикселей по ширине и высоте
        new_width = max(screenshot.shape[1] - 25, 1)
        new_height = max(screenshot.shape[0] - 25, 1)
        resized_screenshot = cv2.resize(screenshot, (new_width, new_height))

        cv2.imshow("Clicker Area Frame", resized_screenshot)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    def load_images(self):
        images = []
        for filename in os.listdir(self.image_folder):
            if filename.endswith('.png'):
                image_path = os.path.join(self.image_folder, filename)
                image = cv2.imread(image_path, cv2.IMREAD_COLOR)
                if image is not None:
                    images.append((filename, image))
        return images

    def bot_loop(self):
        try:
            check = gw.getWindowsWithTitle(self.window_name)

            if not check:
                self.log_message(f"\nWindow {self.window_name} not found!\nPlease, select another window.")
                self.window_name = self.choose_window_gui()

            if not self.window_name or not gw.getWindowsWithTitle(self.window_name):
                self.log_message("\nThe specified window could not be found!\nStart the game, then restart the bot!")
                return
            else:
                current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.log_message(f'\n{current_time}')
                self.log_message(f"Window {self.window_name} found\nPress 'A' to pause\n'S' to stop bot")

            telegram_window = gw.getWindowsWithTitle(self.window_name)[0]

            while self.running.is_set():
                if self.paused:
                    time.sleep(0.1)
                    continue

                window_rect = (
                    telegram_window.left, telegram_window.top, telegram_window.width, telegram_window.height
                )

                if telegram_window != []:
                    try:
                        telegram_window.activate()
                    except:
                        telegram_window.minimize()
                        telegram_window.restore()

                screenshot = self.grab_screen(window_rect)
                images = self.load_images()

                if not images:
                    self.log_message("No images to click.")
                    break

                for filename, template in images:
                    position = self.find_template_on_screen(template, screenshot)
                    if position:
                        # Центрирование клика по изображению
                        center_x = position[0] + template.shape[1] // 2
                        center_y = position[1] + template.shape[0] // 2

                        # Перемещение указателя мыши в центр изображения
                        self.mouse.position = (center_x + telegram_window.left, center_y + telegram_window.top)
                        self.click_morse_code()

                        # Остановка бота после полного ввода целевого слова
                        self.running.clear()
                        self.log_message("Target word fully entered. Stopping bot.")
                        return

        except Exception as e:
            self.log_message(f"Error: {e}")

        self.log_message('STOP')
        self.listener.stop()

    def click_morse_code(self):
        for char in self.cipher.upper():
            if char in MORSE_CODE_DICT:
                morse_code = MORSE_CODE_DICT[char]
                for i, symbol in enumerate(morse_code):
                    if symbol == '*':
                        self.mouse.press(Button.left)
                        self.mouse.release(Button.left)
                        time.sleep(0.2)  # Короткий клик
                    if symbol == '-':
                        self.mouse.press(Button.left)
                        time.sleep(1)  # Длинный клик
                        self.mouse.release(Button.left)
                        # Пауза 0.3 секунды, если следующий символ - короткий клик
                        # if i + 1 < len(morse_code) and morse_code[i + 1] == '*':
                        time.sleep(0.2)
                    time.sleep(0.3)  # Пауза между символами
                time.sleep(5)  # Пауза между буквами


root = tk.Tk()
root.title("ABClicker")
root.resizable(False, False)  # Отключение изменения размера окна
root.iconbitmap("icon.ico")  # Установка иконки окна

# Создание вкладок
notebook = ttk.Notebook(root)
notebook.pack(fill='both', expand=True)

# Создание первой вкладки ===================================================== 1
tab1 = ttk.Frame(notebook)
notebook.add(tab1, text='Anon')

# Загрузка изображения для фона
background_image = Image.open("img/background.png")
background_photo = ImageTk.PhotoImage(background_image)

# Создание холста для фона первой вкладки
canvas1 = tk.Canvas(tab1, width=background_photo.width(), height=background_photo.height())
canvas1.pack(fill="both", expand=True)
canvas1.create_image(0, 0, image=background_photo, anchor="nw")

# Создание фрейма для кнопок и изображений первой вкладки
frame1 = tk.Frame(canvas1)
frame1.place(relx=0.5, rely=0.5, anchor="center")

# Создание метки для фона фрейма первой вкладки
frame1_bg_label = tk.Label(frame1, image=background_photo)
frame1_bg_label.place(x=0, y=0, relwidth=1, relheight=1)

# Создание фрейма для группировки элементов первой вкладки
window_name_frame1 = tk.Frame(frame1)
window_name_frame1.grid(row=0, column=0, padx=(53, 2), pady=2, sticky="n")

# Поле ввода для изменения значения window_name первой вкладки
window_name_label1 = tk.Label(window_name_frame1, text="Window Name:", bg="dark gray")
window_name_label1.grid(row=0, column=0, padx=2, pady=2, sticky="w")
window_name_entry1 = tk.Entry(window_name_frame1)
# Загрузка значения window_name2 из файла ini
config = configparser.ConfigParser()
config.read('file.ini')
window_name1 = config['WindowAnon']['name']

window_name_entry1.insert(0, window_name1)
window_name_entry1.grid(row=0, column=1, padx=2, pady=2, sticky="w")
update_button1 = tk.Button(window_name_frame1, text="Apply", command=lambda: space_bot.update_window_name(window_name_entry1))
update_button1.grid(row=0, column=2, padx=2, pady=2, sticky="w")

# Загрузка изображений для первой вкладки
ship_image1 = Image.open("img/ship.png")
ship_photo1 = ImageTk.PhotoImage(ship_image1)

# Кнопка ПУСК с изображениями для первой вкладки
start_frame1 = tk.Frame(frame1, bg="dark gray")
start_frame1.grid(row=1, column=0, pady=5, columnspan=2)
start_label_left1 = tk.Label(start_frame1, image=ship_photo1, bg="dark gray")
start_label_left1.grid(row=0, column=0, padx=(0, 10))
start_button1 = tk.Button(start_frame1, text="RUN (D)", command=lambda: space_bot.start_bot())
start_button1.grid(row=0, column=1, padx=(0, 10))

# Фрейм для кнопок ПАУЗА и СТОП для первой вкладки
control_frame1 = tk.Frame(frame1, bg="black")
control_frame1.grid(row=2, column=0, pady=5, columnspan=2)

# Кнопка ПАУЗА с изображениями для первой вкладки
pause_button1 = tk.Button(control_frame1, text="PAUSE (A)", command=lambda: space_bot.pause_bot())
pause_button1.grid(row=0, column=0, padx=(0, 7))

# Кнопка СТОП с изображениями для первой вкладки
stop_button1 = tk.Button(control_frame1, text="STOP (S)", command=lambda: space_bot.stop_bot())
stop_button1.grid(row=0, column=1, padx=(7, 0))

# Кнопка для открытия окна конфигурации для первой вкладки
config_button1 = tk.Button(frame1, text="Config", command=lambda: space_bot.open_config_window())
config_button1.grid(row=3, column=0, columnspan=2, pady=3)

# Консоль для логов для первой вкладки
log_text1 = scrolledtext.ScrolledText(frame1, width=50, height=10, state='disabled', bg="black", fg="green")
log_text1.grid(row=4, column=0, columnspan=2, pady=5)

# Текст для донатов с рамкой для первой вкладки
donate_label1 = tk.Label(frame1, text="Downloaded from abclicker.com\nHelp the project any donation\nTON Wallet:\nUQBKm1osfi6A721M_iGjB9sMz-Far0vv4e8i5HXC2HXUFI2n", bg="black", fg="green", bd=2, relief="solid")
donate_label1.grid(row=5, column=0, columnspan=2, pady=1)

# Кнопка для копирования кошелька для первой вкладки
copy_button1 = tk.Button(frame1, text="Copy Wallet", command=lambda: space_bot.copy_to_clipboard())
copy_button1.grid(row=6, column=0, columnspan=2, pady=5)


# Создание второй вкладки ==================================================== 2
tab2 = ttk.Frame(notebook)
notebook.add(tab2, text='Blum')

# Загрузка изображения для фона 2 вкладки
background_image2 = Image.open("img/background3.png")
background_photo2 = ImageTk.PhotoImage(background_image2)

# Создание холста для фона второй вкладки
canvas2 = tk.Canvas(tab2, width=background_photo2.width(), height=background_photo2.height())
canvas2.pack(fill="both", expand=True)
canvas2.create_image(0, 0, image=background_photo2, anchor="nw")

# Создание фрейма для кнопок и изображений второй вкладки
frame2 = tk.Frame(canvas2)
frame2.place(relx=0.5, rely=0.5, anchor="center")

# Создание метки для фона фрейма второй вкладки
frame2_bg_label = tk.Label(frame2, image=background_photo2)
frame2_bg_label.place(x=0, y=0, relwidth=1, relheight=1)

# Аналогичные элементы для второй вкладки
window_name_frame2 = tk.Frame(frame2)
window_name_frame2.grid(row=0, column=0, padx=(53, 2), pady=2, sticky="n")

window_name_label2 = tk.Label(window_name_frame2, text="Window Name:", bg="dark gray")
window_name_label2.grid(row=0, column=0, padx=2, pady=2, sticky="w")
window_name_entry2 = tk.Entry(window_name_frame2)
# Загрузка значения window_name2 из файла ini
config = configparser.ConfigParser()
config.read('file.ini')
window_name2 = config['WindowBlum']['name']
window_name_entry2.insert(0, window_name2)
window_name_entry2.grid(row=0, column=1, padx=2, pady=2, sticky="w")
update_button2 = tk.Button(window_name_frame2, text="Apply", command=lambda: blum_bot.update_window_name(window_name_entry2))
update_button2.grid(row=0, column=2, padx=2, pady=2, sticky="w")

ship_image2 = Image.open("img/rocket4.png")
ship_photo2 = ImageTk.PhotoImage(ship_image2)

start_frame2 = tk.Frame(frame2, bg="dark gray")
start_frame2.grid(row=1, column=0, pady=5, columnspan=2)
start_label_left2 = tk.Label(start_frame2, image=ship_photo2, bg="dark gray")
start_label_left2.grid(row=0, column=0, padx=(0, 10))
start_button2 = tk.Button(start_frame2, text="RUN (D)", command=lambda: blum_bot.start_bot())
start_button2.grid(row=0, column=1, padx=(0, 10))

control_frame2 = tk.Frame(frame2, bg="black")
control_frame2.grid(row=2, column=0, pady=5, columnspan=2)

pause_button2 = tk.Button(control_frame2, text="PAUSE (A)", command=lambda: blum_bot.pause_bot())
pause_button2.grid(row=0, column=0, padx=(0, 7))

stop_button2 = tk.Button(control_frame2, text="STOP (S)", command=lambda: blum_bot.stop_bot())
stop_button2.grid(row=0, column=1, padx=(7, 0))

config_button2 = tk.Button(frame2, text="Config", command=lambda: blum_bot.open_config_window_Blum())
config_button2.grid(row=3, column=0, columnspan=2, pady=3)


# Консоль для логов для второй вкладки
log_text2 = scrolledtext.ScrolledText(frame2, width=51, height=8, state='disabled', bg="black", fg="green")
log_text2.grid(row=4, column=0, columnspan=2, pady=5)

donate_label2 = tk.Label(frame2, text="Downloaded from abclicker.com\nHelp the project any donation\nTON Wallet:\nUQBKm1osfi6A721M_iGjB9sMz-Far0vv4e8i5HXC2HXUFI2n", bg="black", fg="green", bd=2, relief="solid")
donate_label2.grid(row=5, column=0, columnspan=2, pady=1)

copy_button2 = tk.Button(frame2, text="Copy Wallet", command=lambda: blum_bot.copy_to_clipboard())
copy_button2.grid(row=6, column=0, columnspan=2, pady=5)


# Создание вкладки BOT 3 ===================================================== 3
frame3 = ttk.Frame(notebook)
notebook.add(frame3, text="Clicker")

# Установка фонового изображения
background_image3 = tk.PhotoImage(file='img/back_clicker2.png')
background_label = tk.Label(frame3, image=background_image3)
background_label.place(relwidth=1, relheight=1)  # Растягивает изображение на всю площадь frame3

# Получение цвета текста из настроек или установка значения по умолчанию
default_color = config.get('WindowClicker', 'color', fallback='green')

log_text3 = scrolledtext.ScrolledText(frame3, width=51, height=10, state='disabled', bg="black", fg=default_color)
log_text3.grid(row=8, column=0, columnspan=2, pady=5, padx=(60, 0))
clicker_bot = ClickerBot(log_text3)

# Функция для изменения цвета текста в консоли и сохранения в файл
def change_log_color(color):
    log_text3.config(fg=color)
    config.set('WindowClicker', 'color', color)
    with open('file.ini', 'w') as configfile:
        config.write(configfile)

# Кнопки для изменения цвета текста в консоли
color_buttons_frame = tk.Frame(frame3, bg="black")
color_buttons_frame.place(x=26, y=270)

color_buttons = [
    ("", "white"),
    ("", "gray"),
    ("", "orange"),
    ("", "green")
]

for i, (text, color) in enumerate(color_buttons):
    button = tk.Button(color_buttons_frame, text=text, width=2, bg=color, command=lambda c=color: change_log_color(c))
    button.grid(row=i, column=0, padx=2, pady=2)

# Элементы управления для BOT 3
window_name_frame3 = tk.Frame(frame3)
window_name_frame3.grid(row=0, column=0, padx=(110, 0), pady=(5, 15))

window_name_label3 = tk.Label(window_name_frame3, text="Window Name:", bg="dark gray")
window_name_label3.grid(row=0, column=0, padx=2, pady=2)
window_name_entry3 = tk.Entry(window_name_frame3)



config = configparser.ConfigParser()
config.read('file.ini')
window_name3 = config['WindowClicker']['name']
window_name_entry3.insert(0, window_name3)
window_name_entry3.grid(row=0, column=1, padx=2, pady=2)

update_button3 = tk.Button(window_name_frame3, text="Apply", command=lambda: clicker_bot.update_window_name(window_name_entry3))
update_button3.grid(row=0, column=2, padx=2, pady=2)

window_name_frame33 = tk.Frame(frame3, bg="black")
window_name_frame33.grid(row=1, column=0, padx=(90, 2), pady=(5, 0))

# Поле для настройки максимальной энергии
max_energy_label = tk.Label(window_name_frame33, text="Max Energy:", bg="dark gray")
max_energy_label.grid(row=3, column=0, padx=2, pady=2, sticky="w")
max_energy_entry = tk.Entry(window_name_frame33)
max_energy_entry.insert(0, str(clicker_bot.max_energy))
max_energy_entry.grid(row=3, column=1, padx=(70, 2), pady=2)

# Поле для настройки затрат энергии на один клик
energy_per_click_label = tk.Label(window_name_frame33, text="Energy per Click:", bg="dark gray")
energy_per_click_label.grid(row=4, column=0, padx=2, pady=2, sticky="w")
energy_per_click_entry = tk.Entry(window_name_frame33)
energy_per_click_entry.insert(0, str(clicker_bot.energy_per_click))
energy_per_click_entry.grid(row=4, column=1, padx=(70, 2), pady=2)

# Поле для настройки восстановления энергии
energy_recovery_rate_label = tk.Label(window_name_frame33, text="Energy Recovery Rate:", bg="dark gray")
energy_recovery_rate_label.grid(row=5, column=0, padx=2, pady=2, sticky="w")
energy_recovery_rate_entry = tk.Entry(window_name_frame33)
energy_recovery_rate_entry.insert(0, str(clicker_bot.energy_recovery_rate))
energy_recovery_rate_entry.grid(row=5, column=1, padx=(70, 2), pady=2)

# Поле для настройки количества BOOST
boost_label = tk.Label(window_name_frame33, text="Boost:", bg="dark gray")
boost_label.grid(row=1, column=0, padx=2, pady=2, sticky="w")
boost_entry = tk.Entry(window_name_frame33)
boost_entry.insert(0, str(clicker_bot.boost_label))
boost_entry.grid(row=1, column=1, padx=(70, 2), pady=2)

# Поле для настройки времени BOOST
boost_time_label = tk.Label(window_name_frame33, text="Cooldown:", bg="dark gray")
boost_time_label.grid(row=2, column=0, padx=2, pady=2, sticky="w")
boost_time_entry = tk.Entry(window_name_frame33)
boost_time_entry.insert(0, str(clicker_bot.boost_time))
boost_time_entry.grid(row=2, column=1, padx=(70, 2), pady=2)

# Кнопка для перезапуска бота
restart_button = tk.Button(frame3, text="Restart", command=clicker_bot.restart_bot)
restart_button.grid(row=5, column=0, columnspan=2, pady=3, padx=(293, 0))

# Кнопки для переключения профилей
profile_buttons_frame = tk.Frame(frame3, bg="black")
profile_buttons_frame.grid(row=1, column=1, rowspan=4, padx=(2, 0), pady=(5, 0))

# Глобальная переменная для хранения текущего профиля
def load_profile(profile):
    clicker_bot.profile = profile
    clicker_bot.load_profile_settings(profile)
    boost_entry.delete(0, tk.END)
    boost_entry.insert(0, str(clicker_bot.boost_label[profile]))
    boost_time_entry.delete(0, tk.END)
    boost_time_entry.insert(0, str(clicker_bot.boost_time[profile]))
    max_energy_entry.delete(0, tk.END)
    max_energy_entry.insert(0, str(clicker_bot.max_energy[profile]))
    energy_per_click_entry.delete(0, tk.END)
    energy_per_click_entry.insert(0, str(clicker_bot.energy_per_click[profile]))
    energy_recovery_rate_entry.delete(0, tk.END)
    energy_recovery_rate_entry.insert(0, str(clicker_bot.energy_recovery_rate[profile]))

    # Обновляем глобальную переменную profileCurrent
    clicker_bot.profileCurrent = profile
    clicker_bot.log_message(f'Profile loaded: {clicker_bot.profileCurrent}')  # Логируем текущий профиль


def toggle_profile(button, profile):
    config = configparser.ConfigParser()
    config.read('file.ini')

    # Проверяем текущее состояние профиля
    if profile in config and config[profile].getboolean('active', True):
        # Деактивируем профиль
        config[profile]['active'] = 'False'
        button.config(bg='red')  # Меняем цвет кнопки на красный
    else:
        # Активируем профиль
        config[profile]['active'] = 'True'
        button.config(bg='SystemButtonFace')  # Возвращаем цвет кнопки к обычному

    # Сохраняем изменения в файл
    with open('file.ini', 'w') as configfile:
        config.write(configfile)


def deactivate_all_except(selected_profile):
    config = configparser.ConfigParser()
    config.read('file.ini')

    all_red = all(config[profile].getboolean('active', True) == False for profile in profile_buttons if profile != selected_profile)

    for i, profile in enumerate(profile_buttons):
        if profile != selected_profile:
            if all_red:
                config[profile]['active'] = 'True'
                buttons[i].config(bg='SystemButtonFace')  # Возвращаем цвет кнопки к обычному
            else:
                config[profile]['active'] = 'False'
                buttons[i].config(bg='red')  # Меняем цвет кнопки на красный

    # Сохраняем изменения в файл
    with open('file.ini', 'w') as configfile:
        config.write(configfile)

profile_buttons = ['ClickerBot1', 'ClickerBot2', 'ClickerBot3', 'ClickerBot4', 'ClickerBot5', 'ClickerBot6', 'ClickerBot7', 'ClickerBot8']
buttons = []

for i, profile in enumerate(profile_buttons):
    button = tk.Button(profile_buttons_frame, text=str(i + 1), width=2, command=lambda p=profile: load_profile(p))

    # Определяем строку и колонку для кнопки
    row = i % 4
    column = i // 4

    button.grid(row=row, column=column, padx=2, pady=2)
    buttons.append(button)

    # Загрузка состояния профиля из файла
    config = configparser.ConfigParser()
    config.read('file.ini')
    if profile not in config:
        config[profile] = {'active': 'True'}  # Устанавливаем значение по умолчанию

    # Устанавливаем цвет кнопки в зависимости от состояния active
    if config[profile].getboolean('active', True):
        button.config(bg='SystemButtonFace')  # Обычный цвет
    else:
        button.config(bg='red')  # Красный цвет, если профиль неактивен

    # Привязка правой кнопки мыши
    button.bind("<Button-3>", lambda event, b=button, p=profile: toggle_profile(b, p))

    # Привязка средней кнопки мыши
    button.bind("<Button-2>", lambda event, p=profile: deactivate_all_except(p))

# Кнопка Apply для сохранения настроек
apply_button = tk.Button(frame3, text="Apply", command=lambda: save_settings(clicker_bot.profileCurrent))
apply_button.grid(row=5, column=0, columnspan=5, pady=(5, 5), padx=(50, 3))

# Кнопка для открытия окна конфигурации для первой вкладки
config_button1 = tk.Button(frame3, text="Config", command=lambda: clicker_bot.open_config_windowClicker())
config_button1.grid(row=5, column=1, columnspan=2, pady=3)

control_frame3 = tk.Frame(frame3, bg="black")
control_frame3.grid(row=6, column=0, columnspan=2, pady=1, padx=(50, 0))

start_button3 = tk.Button(control_frame3, text="RUN (D)", command=lambda: clicker_bot.start_bot())
start_button3.grid(row=6, column=1, padx=(0, 5), sticky="w")

pause_button3 = tk.Button(control_frame3, text="PAUSE (A)", command=lambda: clicker_bot.pause_bot())
pause_button3.grid(row=6, column=2, padx=(2, 7), sticky="w")

stop_button3 = tk.Button(control_frame3, text="STOP (S)", command=lambda: clicker_bot.stop_bot())
stop_button3.grid(row=6, column=3, padx=(0, 2), sticky="w")

# Текст для донатов с рамкой для 3 вкладки
donate_label1 = tk.Label(frame3, text="Downloaded from abclicker.com\nHelp the project any donation\nTON Wallet:\nUQBKm1osfi6A721M_iGjB9sMz-Far0vv4e8i5HXC2HXUFI2n", bg="black", fg="green", bd=2, relief="solid")
donate_label1.grid(row=9, column=0, columnspan=2, pady=1, padx=(50,0))

# Кнопка для копирования кошелька для первой вкладки
copy_button1 = tk.Button(frame3, text="Copy Wallet", command=lambda: clicker_bot.copy_to_clipboard())
copy_button1.grid(row=10, column=0, columnspan=2, pady=5, padx=(55,0))




# Создание вкладки Bot =========================================
# frame4 = ttk.Frame(notebook)
# notebook.add(frame4, text="Bot")

# log_text4 = scrolledtext.ScrolledText(frame4, width=50, height=10, state='disabled', bg="black", fg="green")
# log_text4.grid(row=6, column=0, columnspan=2, pady=5)
# bot = Bot(log_text4)

# # Элементы управления для WCoin
# window_name_frame4 = tk.Frame(frame4)
# window_name_frame4.grid(row=0, column=0, padx=(53, 2), pady=2, sticky="n")

# window_name_label4 = tk.Label(window_name_frame4, text="Window Name:", bg="dark gray")
# window_name_label4.grid(row=0, column=0, padx=2, pady=2, sticky="w")
# window_name_entry4 = tk.Entry(window_name_frame4)

# config = configparser.ConfigParser()
# config.read('file.ini')
# window_name4 = config['WindowBot']['name']
# window_name_entry4.insert(0, window_name4)
# window_name_entry4.grid(row=0, column=1, padx=2, pady=2, sticky="w")


# click_delay_label4 = tk.Label(frame4, text="Click Delay (seconds):", bg="dark gray")
# click_delay_label4.grid(row=1, column=0, padx=2, pady=2, sticky="w")
# click_delay_entry4 = tk.Entry(frame4)
# click_delay_entry4.insert(0, str(bot.click_delay))
# click_delay_entry4.grid(row=1, column=1, padx=2, pady=2, sticky="w")

# max_energy_label4 = tk.Label(frame4, text="Max Energy:", bg="dark gray")
# max_energy_label4.grid(row=2, column=0, padx=2, pady=2, sticky="w")
# max_energy_entry4 = tk.Entry(frame4)
# max_energy_entry4.insert(0, str(bot.max_energy))
# max_energy_entry4.grid(row=2, column=1, padx=2, pady=2, sticky="w")

# energy_per_click_label4 = tk.Label(frame4, text="Energy per Click:", bg="dark gray")
# energy_per_click_label4.grid(row=3, column=0, padx=2, pady=2, sticky="w")
# energy_per_click_entry4 = tk.Entry(frame4)
# energy_per_click_entry4.insert(0, str(bot.energy_per_click))
# energy_per_click_entry4.grid(row=3, column=1, padx=2, pady=2, sticky="w")

# energy_recovery_rate_label4 = tk.Label(frame4, text="Energy Recovery Rate:", bg="dark gray")
# energy_recovery_rate_label4.grid(row=4, column=0, padx=2, pady=2, sticky="w")
# energy_recovery_rate_entry4 = tk.Entry(frame4)
# energy_recovery_rate_entry4.insert(0, str(bot.energy_recovery_rate))
# energy_recovery_rate_entry4.grid(row=4, column=1, padx=2, pady=2, sticky="w")

# # Обновление функции calculate_and_display_time
# def calculate_and_display_time():
#     time_str = bot.calculate_time()
#     time_entry4.delete(0, tk.END)
#     time_entry4.insert(0, time_str)

# # Обновление UI элементов
# time_label4 = tk.Label(frame4, text="Time (min sec):", bg="dark gray")
# time_label4.grid(row=5, column=0, padx=2, pady=2, sticky="w")
# time_entry4 = tk.Entry(frame4)
# time_entry4.grid(row=5, column=1, padx=2, pady=2, sticky="w")

# calculate_button4 = tk.Button(frame4, text="Calculate", command=calculate_and_display_time)
# calculate_button4.grid(row=5, column=2, padx=2, pady=2, sticky="w")

# apply_button4 = tk.Button(frame4, text="Apply", command=lambda: save_wcoin_settings())
# apply_button4.grid(row=6, column=0, columnspan=2, pady=5)

# start_frame4 = tk.Frame(frame4, bg="dark gray")
# start_frame4.grid(row=7, column=0, pady=5, columnspan=2)
# start_button4 = tk.Button(start_frame4, text="RUN (D)", command=lambda: bot.start_bot())
# start_button4.grid(row=0, column=1, padx=(0, 10))

# control_frame4 = tk.Frame(frame4, bg="black")
# control_frame4.grid(row=8, column=0, pady=5, columnspan=2)

# pause_button4 = tk.Button(control_frame4, text="PAUSE (A)", command=lambda: bot.pause_bot())
# pause_button4.grid(row=0, column=0, padx=(0, 7))

# stop_button4 = tk.Button(control_frame4, text="STOP (S)", command=lambda: bot.stop_bot())
# stop_button4.grid(row=0, column=1, padx=(7, 0))



# Создание 5 вкладки ==================================================== 5
tab5 = ttk.Frame(notebook)
notebook.add(tab5, text='Cipher')

# Загрузка изображения для фона 5 вкладки
background_image5 = Image.open("img/backgrCipher.png")
background_photo5 = ImageTk.PhotoImage(background_image2)

# Создание холста для фона 5 вкладки
canvas5 = tk.Canvas(tab5, width=background_photo5.width(), height=background_photo5.height())
canvas5.pack(fill="both", expand=True)
canvas5.create_image(0, 0, image=background_photo5, anchor="nw")

# Создание фрейма для кнопок и изображений 5 вкладки
frame5 = tk.Frame(canvas5)
frame5.place(relx=0.5, rely=0.5, anchor="center")

# Создание метки для фона фрейма 5 вкладки
frame5_bg_label = tk.Label(frame5, image=background_photo5)
frame5_bg_label.place(x=0, y=0, relwidth=1, relheight=1)

# Аналогичные элементы для 5 вкладки
window_name_frame5 = tk.Frame(frame5)
window_name_frame5.grid(row=0, column=0, padx=(53, 2), pady=2, sticky="n")

window_name_label5 = tk.Label(window_name_frame5, text="Window Name:", bg="dark gray")
window_name_label5.grid(row=0, column=0, padx=2, pady=2, sticky="w")
window_name_entry5 = tk.Entry(window_name_frame5)
# Загрузка значения window_name2 из файла ini
config = configparser.ConfigParser()
config.read('file.ini')
window_name5 = config['WindowCipher']['name']
window_name_entry5.insert(0, window_name5)
window_name_entry5.grid(row=0, column=1, padx=2, pady=2, sticky="w")
update_button5 = tk.Button(window_name_frame5, text="Apply", command=lambda: cipher_bot.update_window_name(window_name_entry5))
update_button5.grid(row=0, column=2, padx=2, pady=2, sticky="w")

ship_image5 = Image.open("img/cipher.png")
ship_photo5 = ImageTk.PhotoImage(ship_image5)

start_frame5 = tk.Frame(frame5, bg="dark gray")
start_frame5.grid(row=1, column=0, pady=5, columnspan=2)
start_label_left5 = tk.Label(start_frame5, image=ship_photo5, bg="dark gray")
start_label_left5.grid(row=0, column=0, padx=(0, 10))
start_button5 = tk.Button(start_frame5, text="RUN (D)", command=lambda: cipher_bot.start_bot())
start_button5.grid(row=0, column=1, padx=(0, 10))

# Аналогичные элементы для 5 вкладки
cipher_frame5 = tk.Frame(frame5)
cipher_frame5.grid(row=2, column=0, padx=(53, 2), pady=2, sticky="n")

cipher_label5 = tk.Label(cipher_frame5, text="Enter cipher:", bg="dark gray")
cipher_label5.grid(row=2, column=0, padx=2, pady=2, sticky="w")
cipher_entry5 = tk.Entry(cipher_frame5)
config = configparser.ConfigParser()
config.read('file.ini')
cipher5 = config['CipherBot']['cipher']
cipher_entry5.insert(0, cipher5)
cipher_entry5.grid(row=2, column=1, padx=2, pady=2, sticky="w")
update_button5 = tk.Button(cipher_frame5, text="Apply", command=lambda: cipher_bot.update_cipher(cipher_entry5))
update_button5.grid(row=2, column=2, padx=2, pady=2, sticky="w")

control_frame5 = tk.Frame(frame5, bg="black")
control_frame5.grid(row=3, column=0, pady=5, columnspan=2)

pause_button5 = tk.Button(control_frame5, text="PAUSE (A)", command=lambda: cipher_bot.pause_bot())
pause_button5.grid(row=0, column=0, padx=(0, 7))

stop_button5 = tk.Button(control_frame5, text="STOP (S)", command=lambda: cipher_bot.stop_bot())
stop_button5.grid(row=0, column=1, padx=(7, 0))

config_button5 = tk.Button(frame5, text="Config", command=lambda: cipher_bot.open_config_window())
config_button5.grid(row=4, column=0, columnspan=1, pady=3, padx=(60, 0))

# Консоль для логов для 5 вкладки
log_text5 = scrolledtext.ScrolledText(frame5, width=50, height=10, state='disabled', bg="black", fg="green")
log_text5.grid(row=5, column=0, columnspan=2, pady=5)

donate_label5 = tk.Label(frame5, text="Downloaded from abclicker.com\nHelp the project any donation\nTON Wallet:\nUQBKm1osfi6A721M_iGjB9sMz-Far0vv4e8i5HXC2HXUFI2n", bg="black", fg="green", bd=2, relief="solid")
donate_label5.grid(row=6, column=0, columnspan=2, pady=1)

copy_button5 = tk.Button(frame5, text="Copy Wallet", command=lambda: cipher_bot.copy_to_clipboard())
copy_button5.grid(row=7, column=0, columnspan=2, pady=5)

# def save_wcoin_settings():
#     try:
#         bot.click_delay = float(click_delay_entry4.get())
#         bot.max_energy = int(max_energy_entry4.get())
#         bot.energy_per_click = int(energy_per_click_entry4.get())
#         bot.energy_recovery_rate = int(energy_recovery_rate_entry4.get())
#         bot.current_energy = bot.max_energy

#         # # Обработка времени ожидания
#         # bot.time_await = bot.calculate_time()

#         bot.save_profile_settings()
#     except ValueError as e:
#         print(f"Error saving settings: {e}")
#         bot.log_message("Invalid input for settings. Please enter valid numbers.")

# Создание экземпляров ботов
space_bot = SpaceBot(log_text1)
blum_bot = BlumBot(log_text2)
# bot = Bot(log_text4)
cipher_bot = CipherBot(log_text5)



# Добавление кнопок Freeze и Restart
freeze_button = tk.Button(start_frame2, text="Freeze", command=lambda: blum_bot.toggle_freeze())
freeze_button.grid(row=0, column=2, padx=(0, 10))
blum_bot.freeze_button = freeze_button
print(blum_bot.freeze_button)

restart_button = tk.Button(start_frame2, text="Restart", command=lambda: blum_bot.toggle_restart())
restart_button.grid(row=0, column=3, padx=(0, 10))
blum_bot.restart_button = restart_button

# Установка состояния кнопок при инициализации
if blum_bot.freeze_active:
    blum_bot.freeze_button.config(relief=tk.SUNKEN, bg="green")
else:
    blum_bot.freeze_button.config(relief=tk.RAISED, bg="SystemButtonFace")

if blum_bot.restart_active:
    blum_bot.restart_button.config(relief=tk.SUNKEN, bg="green")
else:
    blum_bot.restart_button.config(relief=tk.RAISED, bg="SystemButtonFace")




# Функция для обработки нажатий клавиш
def on_press(key):
    try:
        if notebook.index(notebook.select()) == 0:  # Если активна первая вкладка
            if key.char == 's':
                space_bot.stop_bot()
            elif key.char == 'a':
                space_bot.pause_bot()
            elif key.char == 'd':
                space_bot.start_bot()
        elif notebook.index(notebook.select()) == 1:  # Если активна вторая вкладка
            if key.char == 's':
                blum_bot.stop_bot()
            elif key.char == 'a':
                blum_bot.pause_bot()
            elif key.char == 'd':
                blum_bot.start_bot()
        elif notebook.index(notebook.select()) == 2:  # Если активна третья вкладка
            if key.char == 's':
                clicker_bot.stop_bot()
            elif key.char == 'a':
                clicker_bot.pause_bot()
            elif key.char == 'd':
                clicker_bot.start_bot()
    except AttributeError:
        pass

# Запуск слушателя для отслеживания нажатий клавиш
keyboard_listener = kb.Listener(on_press=on_press)
keyboard_listener.start()

# Обработчик закрытия окна
def on_closing():
    space_bot.stop_bot()
    blum_bot.stop_bot()
    clicker_bot.stop_bot()
    root.destroy()
    os._exit(0)  # Принудительно завершить все потоки
# Привязка обработчика закрытия окна
root.protocol("WM_DELETE_WINDOW", on_closing)

# Функция для сохранения выбранной вкладки в файл ini
def save_selected_tab(event):
    selected_index = notebook.index(notebook.select())
    config = configparser.ConfigParser()
    config.read('file.ini')
    config['Notebook'] = {'index': str(selected_index)}
    with open('file.ini', 'w') as configfile:
        config.write(configfile)


def save_settings(selected_profile):
    try:
        print(selected_profile)
        clicker_bot.boost_label[selected_profile] = int(boost_entry.get())
        clicker_bot.boost_time[selected_profile] = int(boost_time_entry.get())
        clicker_bot.max_energy[selected_profile] = int(max_energy_entry.get())
        clicker_bot.energy_per_click[selected_profile] = int(energy_per_click_entry.get())
        clicker_bot.energy_recovery_rate[selected_profile] = int(energy_recovery_rate_entry.get())
        clicker_bot.save_profile_settings(selected_profile)
        clicker_bot.log_message(f"Settings saved for {selected_profile}")  # Логирование успешного сохранения
    except ValueError as e:
        clicker_bot.log_message(f"Error saving settings: {e}")  # Логирование ошибки

# Привязка функции сохранения к событию переключения вкладок
notebook.bind("<<NotebookTabChanged>>", save_selected_tab)

# Установка активной вкладки при запуске
config = configparser.ConfigParser()
config.read('file.ini')
messageIsDisplay = False

if 'Notebook' in config and 'index' in config['Notebook']:
    try:
        selected_index = int(config['Notebook']['index'])
        if selected_index < notebook.index("end"):  # Проверка, что индекс вкладки не превышает общее количество вкладок
            notebook.select(selected_index)
            # Логирование сообщения о готовности бота
            if selected_index == 0 and not messageIsDisplay:
                messageIsDisplay = True
                space_bot.log_message("Bot is ready, press D to start.\nPress F to take a screenshot.", )
            elif selected_index == 1 and not messageIsDisplay:
                messageIsDisplay = True
                blum_bot.log_message("Bot is ready, press D to start.\nPress F to take a screenshot.")
            elif selected_index == 2:
                messageIsDisplay = True
                clicker_bot.log_message("Bot is ready, press D to start.\nPress F to take a screenshot.")
    except ValueError:
        pass


if __name__ == "__main__":

    queue = Queue()
    log_widget = clicker_bot.log_widget
    screenshot_thread = threading.Thread(target=start_screenshot_listener, args=(queue, log_widget), daemon=True)
    screenshot_thread.start()

    root.after(100, process_queue, root, queue)

root.mainloop()