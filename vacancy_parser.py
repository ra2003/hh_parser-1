"""
Скрипт для поверхностного и полного парсинга вакансий по url поиска вакансии с сайта hh.ru
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Поверхностный парсинг - парсинг данных, указанных только на странице поиска

Полный парсинг - парсинг данных, указанных на странице самой вакансии

На данный момент все данные собираются в один длинный список, состоящий из словарей такого формата:
{"name": название вакансии, "salary_from": зарплата от, "salary_to": зарплата до,
 "salary_in": валюта указанной зарплаты, "company_name": название компании,
 "date": дата вакансии, "city": город вакансии, "hh_id": id вакансии на hh.ru,
 "responsibility": ответственность работника по вакансии, "requirement": требования для работника по вакансии,
 "link": ссылка на вакансию, "link_to_company": ссылка на компанию}
(salary_in - "руб" или "USD")

При парсинге в полном режиме ко всему выше добавляются также:
{'required_experience': требуемый опыт работы, 'employment_mode': тип занятости,
 'schedule': график работы, 'key_skills': ключевые навыки для вакансии}
(key_skills - список всех ключевых навыков (может быть пустым))

Сделал так, потому что далее можно будет без проблем переделать под все что угодно (json, sql, etc.)

Сохраняется в указанный вами файл: одна вакансия - одна строка

Парсинг в полном режиме требует значительно больше времени
"""

import sys
import datetime
import locale
import io
from selenium import webdriver
from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager


def parse_vacancies_on_page(page):
    """функция для поверхностного парсинга всех вакансий на одной странице"""
    all_vacancies = []  # все вакансии на данной странице
    soup = BeautifulSoup(page, features="html.parser")
    vacancies_on_page = soup.find_all("div", {"class": "vacancy-serp-item"})

    # Списки с предварительными данными на этой странице
    vacancy_names = []
    vacancy_cities = []
    vacancy_hh_ids = []
    vacancy_links = []
    vacancy_salary_min = []
    vacancy_salary_max = []
    vacancy_company_names = []
    vacancy_company_links = []
    vacancy_responsibilities = []
    vacancy_requirements = []
    vacancy_dates = []
    vacancy_salary_in = []

    # Парсинг каждой вакансии отдельно
    for vacancy in vacancies_on_page:
        vacancy_info_text = vacancy.find("div", {"class": "vacancy-serp-item__info"})

        # Название вакансии
        name_block = vacancy_info_text.find("a", {"class": "bloko-link HH-LinkModifier"})
        if name_block is not None:
            name = name_block.text
        else:
            name = ""
        vacancy_names.append(name)

        # Ссылка на вакансию
        vacancy_link_block = vacancy_info_text.find("a", {"class": "bloko-link HH-LinkModifier"})
        if vacancy_link_block is not None:
            vacancy_link = vacancy_link_block.get("href")
        else:
            vacancy_link = ""
        vacancy_links.append(vacancy_link)

        # Id вакансии на сайте hh
        if len(vacancy_link) == 0:
            vacancy_hh_id = None
        else:
            try:
                vacancy_hh_id = vacancy_link.split('/')[4].split("?")[0]
            except IndexError:
                vacancy_hh_id = None

        vacancy_hh_ids.append(vacancy_hh_id)

        vacancy_salary_block = vacancy.find("div", {"class": "vacancy-serp-item__sidebar"})
        if vacancy_salary_block is not None:
            vacancy_salary = vacancy_salary_block.text
        else:
            vacancy_salary = ""

        # Заполнение зарплатных данных (может быть Null)
        if len(vacancy_salary) == 0:
            vacancy_salary_min.append(None)
            vacancy_salary_max.append(None)
        elif vacancy_salary.find("-") != -1:
            vacancy_salary_min.append(vacancy_salary.split('-')[0].replace(u'\xa0', u''))
            vacancy_salary_max.append(vacancy_salary.split('-')[1].split("руб")[0].split("USD")[0].replace(u'\xa0', u''))
        elif vacancy_salary.find("от") != -1:
            vacancy_salary_min.append(vacancy_salary.split('от')[1].split("руб")[0].split("USD")[0].replace(u'\xa0', u''))
            vacancy_salary_max.append(None)
        elif vacancy_salary.find("до") != -1:
            vacancy_salary_min.append(None)
            vacancy_salary_max.append(vacancy_salary.split('до')[1].split("руб")[0].split("USD")[0].replace(u'\xa0', u''))

        # В какой валюте зарплата (может быть Null)
        if vacancy_salary.find("руб") != -1:
            vacancy_salary_in.append("руб")
        elif vacancy_salary.find("USD") != -1:
            vacancy_salary_in.append("USD")
        else:
            vacancy_salary_in.append(None)

        # Название компании
        vacancy_company = vacancy.find("div", {"class": "vacancy-serp-item__meta-info"})
        if vacancy_company is not None:
            vacancy_company_name = vacancy_company.text.replace(u'\xa0', u'')
        else:
            vacancy_company_name = ""
        vacancy_company_names.append(vacancy_company_name)

        # Ссылка на компанию
        vacancy_company_link_block = vacancy_company.find("a", {"class": "bloko-link bloko-link_secondary"})
        if vacancy_company_link_block is not None:
            vacancy_company_link = "https://hh.ru" + vacancy_company_link_block.get('href')
        else:
            vacancy_company_link = ""
        vacancy_company_links.append(vacancy_company_link)

        # Город вакансии
        vacancy_city_block = vacancy.find("span", {"data-qa": "vacancy-serp__vacancy-address"})
        if vacancy_city_block is not None:
            vacancy_city = vacancy_city_block.text.split(',')[0]
        else:
            vacancy_city = ""
        vacancy_cities.append(vacancy_city)

        # Ответсвенность работника по данной вакансии
        vacancy_responsibility_block = vacancy.find("div", {"data-qa": "vacancy-serp__vacancy_snippet_responsibility"})
        if vacancy_responsibility_block is not None:
            vacancy_responsibility = vacancy_responsibility_block.text
        else:
            vacancy_responsibility = ""
        vacancy_responsibilities.append(vacancy_responsibility)

        # Требования для работника по данной вакансии
        vacancy_requirement_block = vacancy.find("div", {"data-qa": "vacancy-serp__vacancy_snippet_requirement"})
        if vacancy_requirement_block is not None:
            vacancy_requirement = vacancy_requirement_block.text
        else:
            vacancy_requirement = ""
        vacancy_requirements.append(vacancy_requirement)

        # Дата, когда была выложена вакансия
        vacancy_date_block = vacancy.find("span", {"class": "vacancy-serp-item__publication-date"})
        if vacancy_date_block is not None:
            vacancy_date_text = vacancy_date_block.text
        else:
            vacancy_date_text = ""

        if len(vacancy_date_text) == 0:
            vacancy_dates.append(None)
        else:
            vacancy_dates.append(parse_date(vacancy_date_text))

    # Заполнение словарей по каждой вакансии
    for i in range(len(vacancy_names)):
        vacancy = {"name": vacancy_names[i],
                   "salary_from": vacancy_salary_min[i], "salary_to": vacancy_salary_max[i],
                   "salary_in": vacancy_salary_in[i], "company_name": vacancy_company_names[i],
                   "date": vacancy_dates[i], "city": vacancy_cities[i], "hh_id": vacancy_hh_ids[i],
                   "responsibility": vacancy_responsibilities[i], "requirement": vacancy_requirements[i],
                   "link": vacancy_links[i], "link_to_company": vacancy_company_links[i]}
        all_vacancies.append(vacancy)
    return all_vacancies


def parse_vacancy(page):
    """функция парсинга одной вакансии со страницы этой вакансии"""
    key_skills = []

    soup = BeautifulSoup(page, features="html.parser")

    # Требуемый опыт работы
    required_experience_block = soup.find("span", {"data-qa": "vacancy-experience"})
    if required_experience_block is not None:
        required_experience = required_experience_block.text
    else:
        required_experience = ""

    employment_block = soup.find("p", {"data-qa": "vacancy-view-employment-mode"})

    # Тип занятости
    if employment_block is not None:
        employment_mode = employment_block.text.split(', ')[0]
    else:
        employment_mode = ""

    # График работы
    if employment_block is not None:
        schedule = employment_block.text.split(', ')[1]
    else:
        schedule = ""

    # Ключевые навыки
    all_skills = soup.find_all("span", {"class": "bloko-tag__section_text"})
    for skill in all_skills:
        key_skills.append(skill.text.replace(u'\xa0', u' '))

    # Доп. инфа с полного парсинга
    vacancy = {"required_experience": required_experience, "employment_mode": employment_mode,
               "schedule": schedule, "key_skills": key_skills}

    return vacancy


def check_exists_by_class_name(class_name):
    """Проверяет наличие элемента на странице по имени класса"""
    try:
        browser.find_element_by_class_name(class_name)
    except NoSuchElementException:
        return False
    return True


def parse_date(date_str):
    """Парсит дату вакансии"""
    day = int(date_str.split("\xa0")[0])
    month_str = date_str.split("\xa0")[1]
    a = datetime.date.today()
    month_dict = {"января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5, "июня": 6, "июля": 7, "августа": 8,
                  "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12}
    if month_str in month_dict.keys():
        month = month_dict[month_str]
    else:
        month = a.month
    year = a.year
    if month > a.month:
        year -= 1
    return datetime.date(year, month, day).isoformat()


if __name__ == '__main__':
    locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
    options = webdriver.ChromeOptions()
    options.add_argument('headless')  # Невидимый режим браузера
    options.add_argument('--log-level=1')  # Не выводит логи браузера в командную строку
    browser = webdriver.Chrome(ChromeDriverManager().install(), options=options)
    wait = WebDriverWait(browser, 1000)

    # Получение агрументов программы
    hh_url = sys.argv[1]
    parse_mode = int(sys.argv[2])
    file_name = sys.argv[3]

    all_vacancies = []  # все вакансии по данному поисковому запросу в данном регионе

    browser.get(hh_url)

    # Поверхностный парсинг каждой страницы и получение данных
    if parse_mode == 1 or parse_mode == 2:
        print("Поверхностный парсинг: Start")
        page = browser.page_source
        while check_exists_by_class_name("HH-Pager-Controls-Next"):
            all_vacancies += parse_vacancies_on_page(page)
            browser.find_element_by_class_name("HH-Pager-Controls-Next").click()
            page = browser.page_source
        all_vacancies += parse_vacancies_on_page(page)
        print("Поверхностный парсинг: Done\n")

    # Полный парсинг, если выбран режим полного парсинга
    # (Уже до этого можно использовать предварительный (без доп. инфы) список all_vacancies, если надо)
    if parse_mode == 2:
        print("Глубокий парсинг: Start")
        i = int(0)
        for vacancy in all_vacancies:
            print("Парсинг вакансии " + str(i + 1) + ": Start")
            vacancy_link = vacancy["link"]
            browser.get(vacancy_link)
            page = browser.page_source
            # Добавляем доп. данные в словарь текущей вакансии
            all_vacancies[i].update(parse_vacancy(page))
            print("Парсинг вакансии " + str(i + 1) + ": Done")
            i += 1
        print("Глубокий парсинг: Done\n")

    # Запись в файл
    with io.open(file_name, "w", encoding="utf-8") as f:
        for vacancy in all_vacancies:
            f.write(str(vacancy))
            f.write("\n")

    print("Получено " + str(len(all_vacancies)) + " Вакансий")
