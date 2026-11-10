
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
def safe_excel_value(value):
    if value is None:
        return ""

    value = str(value)

    dangerous_prefix = value.lstrip(" \t\r\n")[:1]

    if dangerous_prefix in ("=", "+", "-", "@"):
        return "'" + value

    return value

STATUS_NAMES = {
    "new": "Новая",
    "in_progress": "В работе",
    "completed": "Завершена",
    "cancelled": "Отменена"
}


def create_excel_report(applications):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Заявки"

    headers = [
        "Номер",
        "Telegram ID",
        "Username",
        "Имя",
        "Телефон",
        "Услуга",
        "Комментарий",
        "Статус",
        "Дата создания"
    ]

    sheet.append(headers)

    for application in applications:
        sheet.append([
    application["id"],
    application["user_id"],
    safe_excel_value(application["username"]),
    safe_excel_value(application["name"]),
    safe_excel_value(application["phone"]),
    safe_excel_value(application["service"]),
    safe_excel_value(application["comment"]),
    safe_excel_value(
        STATUS_NAMES.get(
            application["status"],
            application["status"]
        )
    ),
    safe_excel_value(application["created_at"])
])

    # Оформление заголовков
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(
            fill_type="solid",
            fgColor="2563EB"
        )
        cell.alignment = Alignment(
            horizontal="center",
            vertical="center"
        )

    # Ширина столбцов
    for column in sheet.columns:
        max_length = max(
            len(str(cell.value or ""))
            for cell in column
        )

        column_letter = get_column_letter(
            column[0].column
        )

        sheet.column_dimensions[column_letter].width = min(
            max_length + 3,
            40
        )

    # Удобство работы с таблицей
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions

    # Формируем файл в памяти
    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)

    return buffer
