import os
import shutil
import zipfile
from datetime import datetime
import pydicom
from typing import List, Tuple, Optional
from pydicom.misc import is_dicom

TAGS_TO_REMOVE = [
    (0x0010, 0x0010),  # Patient's Name
    (0x0010, 0x0020),  # Patient ID (будет заменён)
    (0x0010, 0x0030),  # Patient's Birth Date
    (0x0010, 0x0040),  # Patient's Sex
    (0x0010, 0x1010),  # Patient's Age
    (0x0010, 0x1030),  # Patient's Weight
    (0x0018, 0x5100),  # Patient Position
    (0x0010, 0x0032),  # Patient's Birth Time
    (0x0008, 0x0090),  # Referring Physician's Name
    (0x0008, 0x0050),  # Accession Number
    (0x0008, 0x0080),  # Institution Name
    (0x0008, 0x0081),  # Institution Address
    (0x0008, 0x1040),  # Institutional Department Name
    (0x0008, 0x1070),  # Operators' Name
    (0x0010, 0x21B0),  # Additional Patient History
    (0x0010, 0x4000),  # Patient Comments
]

def remove_tags_recursive(ds, tags_to_remove):
    for tag in tags_to_remove:
        if tag in ds:
            del ds[tag]
    for elem in ds.iterall():
        if elem.VR == 'SQ':
            for item in elem.value:
                remove_tags_recursive(item, tags_to_remove)

class AnonyMRIDeidentifier:
    def __init__(self, patient_number: Optional[int] = None, archive: bool = False, log_delimiter: str = 'tab', interactive: bool = True):
        self.patient_number = patient_number
        self.archive = archive
        self.log_delimiter = log_delimiter
        self.log_lines = []
        self.interactive = interactive

    def find_leaf_dirs_with_dicoms(self, root: str) -> List[str]:
        print(f'[AnonyMRI] Поиск папок с DICOM в: {root}')
        dicom_dirs = []
        for dirpath, dirnames, filenames in os.walk(root):
            dicom_files = [f for f in filenames if is_dicom(os.path.join(dirpath, f))]
            if dicom_files:
                dicom_dirs.append(dirpath)
        print(f'[AnonyMRI] Найдено снимков: {len(dicom_dirs)}')
        return dicom_dirs

    def anonymize_dicom_folder(self, folder: str, out_root: str = None, patient_number: Optional[int] = None, patient_id_override: Optional[str] = None) -> str:
        dicom_files = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f)) and is_dicom(os.path.join(folder, f))]
        print(f'[AnonyMRI] Обработка снимка: {folder} (файлов: {len(dicom_files)})')
        if not dicom_files:
            print(f'[AnonyMRI] Нет DICOM-файлов в {folder}')
            return ''
        sample = pydicom.dcmread(os.path.join(folder, dicom_files[0]), stop_before_pixels=True)
        patient_name = getattr(sample, 'PatientName', 'UNKNOWN')
        patient_age = getattr(sample, 'PatientAge', 'UNKNOWN')
        print(f'  Имя пациента: {patient_name}')
        print(f'  Возраст: {patient_age}')
        if patient_number is not None:
            pass
        elif self.interactive:
            while True:
                try:
                    input_number = input('  Введите номер пациента для этого снимка: ')
                    patient_number = int(input_number)
                    break
                except ValueError:
                    print('  Ошибка: введите целое число!')
        else:
            raise ValueError("Patient number is None! Проверьте, что все поля заполнены.")
        study_date = getattr(sample, 'StudyDate', '19000101')
        if patient_id_override is not None:
            patient_id = patient_id_override
        else:
            patient_id = f"{patient_number:04d}{study_date}"

        mri_number = patient_id
        date_str = datetime.strptime(study_date, "%Y%m%d").strftime("%d.%m.%Y")
        mf_strength = getattr(sample, 'MagneticFieldStrength', 'NA')
        manufacturer = getattr(sample, 'Manufacturer', 'NA')
        model = getattr(sample, "ManufacturerModelName", 'NA')

        out_dir = out_root or os.path.join(os.getcwd(), patient_id, "DICOM")
        os.makedirs(out_dir, exist_ok=True)

        for f in dicom_files:
            ds = pydicom.dcmread(os.path.join(folder, f))
            remove_tags_recursive(ds, TAGS_TO_REMOVE)
            ds.PatientID = patient_id
            ds.save_as(os.path.join(out_dir, f), write_like_original=False)

        if self.archive and patient_id_override is None:
            zip_path = os.path.join(os.path.dirname(out_dir), f"{patient_id}.zip")
            print(f'[AnonyMRI] Архивация в {zip_path}')
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root_dir, _, files in os.walk(os.path.join(os.path.dirname(out_dir), patient_id)):
                    for file in files:
                        abs_path = os.path.join(root_dir, file)
                        rel_path = os.path.relpath(abs_path, os.path.join(os.path.dirname(out_dir), patient_id))
                        zipf.write(abs_path, os.path.join(patient_id, rel_path))

        # Добавляем строку в лог только если это главный вызов (без patient_id_override)
        if patient_id_override is None:
            log_line = self.log_delimiter.join([
                str(patient_number),
                mri_number,
                date_str,
                str(mf_strength),
                str(manufacturer),
                str(model)
            ])
            self.log_lines.append(log_line)
        return ''

    def run(self, root: str, out_root: str = None) -> List[str]:
        print(f'[AnonyMRI] Запуск анонимизации для {root}')
        dicom_dirs = self.find_leaf_dirs_with_dicoms(root)
        for folder in dicom_dirs:
            self.anonymize_dicom_folder(folder, out_root=out_root)
        print(f'[AnonyMRI] Анонимизация завершена!')
        return self.log_lines 