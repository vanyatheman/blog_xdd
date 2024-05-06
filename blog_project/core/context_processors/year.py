import datetime


def year(request):
    """Добавляет переменную с текущим годом."""
    today = datetime.date.today()
    cur_year = today.year
    return {
        'year': cur_year
    }
