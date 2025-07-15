import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import os
from AnonyMRI.core import AnonyMRIDeidentifier
import pydicom
from pydicom.misc import is_dicom
import collections
import shutil
from datetime import datetime

class MRIEntry:
    def __init__(self, folder, info, short_info):
        self.folder = folder
        self.info = info
        self.short_info = short_info
        self.patient_number_var = tk.StringVar()

class MRIGroup:
    def __init__(self, key, info, short_info, series):
        self.key = key  # (StudyInstanceUID, PatientName, PatientBirthDate)
        self.info = info
        self.short_info = short_info
        self.series = series  # список (путь к подпапке, список файлов)
        self.patient_number_var = tk.StringVar()

class AnonyMRIGUI:
    def __init__(self, root):
        self.root = root
        self.root.title('AnonyMRI GUI')
        self.input_dir = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.delimiter = tk.StringVar(value='tab')
        self.archive = tk.BooleanVar(value=True)
        self.fast_check = tk.BooleanVar(value=True)
        self.entries = []
        self.status_var = tk.StringVar(value='')

        self.build_ui()

    def build_ui(self):
        frm = tk.Frame(self.root)
        frm.pack(padx=10, pady=10, fill='x')

        tk.Label(frm, text='Папка с DICOM:').grid(row=0, column=0, sticky='e')
        tk.Entry(frm, textvariable=self.input_dir, width=40).grid(row=0, column=1)
        tk.Button(frm, text='Выбрать...', command=self.choose_input_dir).grid(row=0, column=2)

        tk.Label(frm, text='Папка для сохранения:').grid(row=1, column=0, sticky='e')
        tk.Entry(frm, textvariable=self.output_dir, width=40).grid(row=1, column=1)
        tk.Button(frm, text='Выбрать...', command=self.choose_output_dir).grid(row=1, column=2)

        tk.Label(frm, text='Разделитель:').grid(row=2, column=0, sticky='e')
        ttk.Combobox(frm, textvariable=self.delimiter, values=['tab', ';', ','], width=5).grid(row=2, column=1, sticky='w')

        tk.Checkbutton(frm, text='Архивировать', variable=self.archive).grid(row=2, column=2, sticky='w')
        tk.Checkbutton(frm, text='Проверять метаданные только в первом файле (ускорить)', variable=self.fast_check).grid(row=4, column=0, columnspan=3, sticky='w')

        tk.Button(frm, text='Найти МРТ', command=self.find_mri).grid(row=3, column=0, columnspan=3, pady=10)

        self.results_frame = tk.Frame(self.root)
        self.results_frame.pack(fill='both', expand=True)

        self.canvas = tk.Canvas(self.results_frame)
        self.scrollbar = tk.Scrollbar(self.results_frame, orient='vertical', command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)
        self.scrollable_frame.bind(
            '<Configure>',
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all'))
        )
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor='nw')
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side='left', fill='both', expand=True)
        self.scrollbar.pack(side='right', fill='y')

        self.anon_btn = tk.Button(self.root, text='Анонимизировать', command=self.anonymize, state='disabled')
        self.anon_btn.pack(pady=10)

        self.status_label = tk.Label(self.root, textvariable=self.status_var, anchor='w', fg='blue')
        self.status_label.pack(fill='x', padx=10, pady=(0, 10))

    def choose_input_dir(self):
        d = filedialog.askdirectory()
        if d:
            self.input_dir.set(d)

    def choose_output_dir(self):
        d = filedialog.askdirectory()
        if d:
            self.output_dir.set(d)

    def find_mri(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.entries = []
        input_dir = self.input_dir.get()
        if not input_dir or not os.path.isdir(input_dir):
            messagebox.showerror('Ошибка', 'Выберите корректную папку с DICOM')
            return
        groups = collections.defaultdict(list)
        for dirpath, dirnames, filenames in os.walk(input_dir):
            dicom_files = []
            if self.fast_check.get():
                if filenames:
                    first_file = filenames[0]
                    if is_dicom(os.path.join(dirpath, first_file)):
                        dicom_files = [first_file]
            else:
                dicom_files = [f for f in filenames if is_dicom(os.path.join(dirpath, f))]
            if dicom_files:
                sample = pydicom.dcmread(os.path.join(dirpath, dicom_files[0]), stop_before_pixels=True)
                study_uid = getattr(sample, 'StudyInstanceUID', None)
                name = getattr(sample, 'PatientName', 'UNKNOWN')
                birth_date = getattr(sample, 'PatientBirthDate', 'UNKNOWN')
                date = getattr(sample, 'StudyDate', 'UNKNOWN')
                key = (study_uid, name, birth_date, date)
                groups[key].append((dirpath, dicom_files))
        if not groups:
            messagebox.showinfo('Результат', 'Не найдено ни одного снимка!')
            return
        for i, (key, series) in enumerate(groups.items()):
            study_uid, name, birth_date, date = key
            first_dir, first_files = series[0]
            sample = pydicom.dcmread(os.path.join(first_dir, first_files[0]), stop_before_pixels=True)
            sex = getattr(sample, 'PatientSex', 'UNKNOWN')
            info = f'Имя: {name} | Дата рождения: {birth_date} | Пол: {sex} | Дата: {date} | Исследование: {study_uid} | Серий: {len(series)}'
            short_info = f'Имя: {name} | Дата рождения: {birth_date} | Пол: {sex} | Дата: {date} | Серий: {len(series)}'
            entry = MRIGroup(key, info, short_info, series)
            self.entries.append(entry)
            tk.Label(self.scrollable_frame, text=short_info, anchor='w', justify='left').grid(row=i, column=0, sticky='w')
            tk.Entry(self.scrollable_frame, textvariable=entry.patient_number_var, width=10).grid(row=i, column=1, padx=5)
        self.anon_btn.config(state='normal')

    def anonymize(self):
        output_dir = self.output_dir.get() or os.getcwd()
        delimiter = '\t' if self.delimiter.get() == 'tab' else self.delimiter.get()
        archive = self.archive.get()
        anonymizer = AnonyMRIDeidentifier(archive=False, log_delimiter=delimiter, interactive=False)  # архивируем вручную ниже
        for entry in self.entries:
            value = entry.patient_number_var.get().strip()
            if not value.isdigit():
                messagebox.showerror('Ошибка', f'Введите корректный номер пациента для {entry.short_info}')
                self.status_var.set('')
                return
            patient_number = int(value)
            # Получаем patient_id для всей группы (по первому файлу первой серии)
            first_dir, first_files = entry.series[0]
            sample = pydicom.dcmread(os.path.join(first_dir, first_files[0]), stop_before_pixels=True)
            study_date = getattr(sample, 'StudyDate', '19000101')
            patient_id = f"{patient_number:04d}{study_date}"
            for dirpath, dicom_files in entry.series:
                series_name = os.path.basename(dirpath)
                out_dir = os.path.join(output_dir, patient_id, 'DICOM', series_name)
                for idx, f in enumerate(dicom_files, 1):
                    self.status_var.set(f'Обработка: {f} ({idx}/{len(dicom_files)}) в {series_name}')
                    self.root.update_idletasks()
                anonymizer.anonymize_dicom_folder(dirpath, out_root=out_dir, patient_number=patient_number, patient_id_override=patient_id)
            # Архивируем всю папку пациента (один раз после всех серий)
            if archive:
                patient_folder = os.path.join(output_dir, patient_id)
                zip_path = os.path.join(output_dir, f"{patient_id}.zip")
                shutil.make_archive(zip_path.replace('.zip', ''), 'zip', patient_folder)
            # Формируем лог только один раз на пациента
            mf_strength = getattr(sample, 'MagneticFieldStrength', 'NA')
            manufacturer = getattr(sample, 'Manufacturer', 'NA')
            model = getattr(sample, "ManufacturerModelName", 'NA')
            date_str = datetime.strptime(study_date, "%Y%m%d").strftime("%d.%m.%Y")
            log_line = delimiter.join([
                str(patient_number),
                patient_id,
                date_str,
                str(mf_strength),
                str(manufacturer),
                str(model)
            ])
            anonymizer.log_lines.append(log_line)
        self.status_var.set('')
        # Сохраняем лог
        header = delimiter.join([
            'Номер пациента',
            'Номер МРТ',
            'Дата (DD.MM.YYYY)',
            'Magnetic Field Strength',
            'Manufacturer',
            "Manufacturer's Model Name"
        ])
        all_lines = [header] + anonymizer.log_lines
        log_path = os.path.join(output_dir, 'anonymization_log.txt')
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(all_lines) + '\n')
        messagebox.showinfo('Готово', f'Анонимизация завершена!\nЛог сохранён в {log_path}')

if __name__ == '__main__':
    root = tk.Tk()
    root.geometry("1100x600")  # Широкое окно по умолчанию
    app = AnonyMRIGUI(root)
    root.mainloop() 