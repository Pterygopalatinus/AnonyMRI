import sys
import os
from AnonyMRI.core import AnonyMRIDeidentifier

def main():
    import argparse
    parser = argparse.ArgumentParser(description='AnonyMRI: DICOM anonymizer')
    parser.add_argument('--input', type=str, default='.', help='Папка с исходными DICOM (по умолчанию текущая)')
    parser.add_argument('--output', type=str, default=None, help='Папка для сохранения анонимизированных данных (по умолчанию текущая)')
    parser.add_argument('--patient-number', type=int, default=None, help='Номер пациента (если не указан, будет интерактивный режим)')
    parser.add_argument('--no-archive', action='store_true', help='Не архивировать результат (ускоряет обработку)')
    parser.add_argument('--delimiter', type=str, default='tab', help='Разделитель для лога (по умолчанию tab, используйте ; или , если нужно)')
    parser.add_argument('--logfile', type=str, default='anonymization_log.txt', help='Имя файла для сохранения лога (по умолчанию anonymization_log.txt)')
    args = parser.parse_args()

    delimiter = '\t' if args.delimiter.lower() == 'tab' else args.delimiter
    interactive = args.patient_number is None
    anonymizer = AnonyMRIDeidentifier(patient_number=args.patient_number, archive=not args.no_archive, log_delimiter=delimiter, interactive=interactive)
    header = delimiter.join([
        'Номер пациента',
        'Номер МРТ',
        'Дата (DD.MM.YYYY)',
        'Magnetic Field Strength',
        'Manufacturer',
        "Manufacturer's Model Name"
    ])
    log_lines = anonymizer.run(args.input, out_root=args.output)
    all_lines = [header] + log_lines
    print('\n'.join(all_lines))

    # Сохраняем лог в файл
    output_dir = args.output or os.getcwd()
    log_path = os.path.join(output_dir, args.logfile)
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(all_lines) + '\n')
    print(f'\n[AnonyMRI] Лог сохранён в {log_path}')

if __name__ == '__main__':
    main() 