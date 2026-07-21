#!/usr/bin/env python3

import sys
import re
import logging
import warnings
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from pytz import timezone
from ics import Calendar, Event
from ics.alarm import EmailAlarm, DisplayAlarm

logging.basicConfig(level=logging.INFO)
warnings.filterwarnings(
    "ignore",
    category=FutureWarning,
    message="Behaviour of str\\(Component\\) will change in version 0.9"
)
clubs = [
    "akita",
    "chiba",
    "cosaka",
    "ehime",
    "fosaka",
    "ftokyo",
    "fujieda",
    "fukuoka",
    "fukushima",
    "gifu",
    "gosaka",
    "hachinohe",
    "hiroshima",
    "imabari",
    "iwaki",
    "iwata",
    "kagoshima",
    "kanazawa",
    "kashima",
    "kashiwa",
    "kawasakif",
    "kitakyushu",
    "kobe",
    "kochi",
    "kofu",
    "kumamoto",
    "kusatsu",
    "kyoto",
    "machida",
    "matsumoto",
    "mito",
    "miyazaki",
    "nagano",
    "nagasaki",
    "nagoya",
    "nara",
    "niigata",
    # "numazu",
    "oita",
    "okayama",
    "omiya",
    "ryukyu",
    "sagamihara",
    "sanuki",
    "sapporo",
    "sendai",
    "shiga",
    "shimizu",
    "shonan",
    "tochigi",
    "tochigic",
    "tokushima",
    "tokyov",
    "tosu",
    "tottori",
    "toyama",
    "urawa",
    "yamagata",
    "yamaguchi",
    "yokohamafc",
    "yokohamafm",
]

name_of_stadiums = {}


def zen_to_han(text):
    han1 = text.translate(str.maketrans(
        {chr(0xFF01 + i): chr(0x21 + i) for i in range(94)})) if text else ""
    han2 = han1.replace("　", " ")
    return han2


def get_soup(url):
    logging.info(url)
    response = requests.get(url)
    # response.encoding = response.apparent_encoding
    response.encoding = "utf-8"
    return BeautifulSoup(response.text, "html.parser")


def get_match_tags1(soup):
    hiddenS4 = soup.find("div", id="S:4")
    if not hiddenS4:
        logging.info(soup)
    scheduleArea_tag = hiddenS4.find(
        "div", class_="p-game-schedule__list")
    return scheduleArea_tag.find_all("div", class_="p-game-schedule__list-item c-container", recursive=False)


def get_match_tags2(soup):
    return soup.find_all("div", class_="m-schedule__content")


def get_date(match_tag1):
    date_tag = match_tag1.find("h2")
    re_date = re.match(r"(\d{4})/(\d{1,2})/(\d{1,2}) ", date_tag.get_text())
    return f"{re_date.group(1).zfill(4)}/{re_date.group(2).zfill(2)}/{re_date.group(3).zfill(2)}"


def get_time(match_tag2):
    time_tag = match_tag2.find("p", class_="m-schedule__time-text")
    time_text = time_tag.get_text(strip=True)
    return "未定" if time_text.startswith("未定") else time_text


def get_stadium_name(match_tag2):
    return match_tag2.find_all("p", class_="m-schedule__info-stadium")[-1].get_text(strip=True)


def get_name_of_teams(match_tag2):
    name_tags = match_tag2.find_all("span", "m-schedule__team-name")
    home_team = name_tags[0].get_text(strip=True)
    away_team = name_tags[2].get_text(strip=True)
    return f"{home_team}vs{away_team}"


def get_note_text(match_tag1):
    note_tag = match_tag1.find("span")
    note_text = note_tag.get_text(strip=True).replace(" ", "").replace("　", "")
    return zen_to_han(note_text)


def get_matches(url):
    soup = get_soup(url)
    match_tags1 = get_match_tags1(soup)
    match_tags2 = get_match_tags2(soup)
    matches = []
    for match_tag1, match_tag2 in zip(match_tags1, match_tags2):
        try:
            match = {}
            match["日付"] = get_date(match_tag1)
            match["時刻"] = get_time(match_tag2)
            match["スタジアム"] = get_stadium_name(match_tag2)
            match["対戦チーム名"] = get_name_of_teams(match_tag2)
            match["補足事項"] = get_note_text(match_tag1)
            matches.append(match)
        except:
            pass
    return matches


def get_dtstart(ics_line):
    try:
        ics_line2 = ics_line.replace("\n", " ")
        dtstart = re.match(r".+DTSTART:(\d{8})", ics_line2)
        if not dtstart:
            dtstart = re.match(r".+DTSTART;VALUE=DATE:(\d{8})", ics_line2)
        return dtstart.group(1)
    except:
        return ""


def get_matchname(ics_line):
    try:
        ics_line2 = ics_line.replace("\n", " ")
        matchname = re.match(r".+DESCRIPTION:(\w+)", ics_line2)
        return matchname.group(1)
    except:
        return ""


def get_uid(ics_line):
    try:
        ics_line2 = ics_line.replace("\n", " ")
        uid = re.match(r".+UID:(.+\.org)", ics_line2)
        return uid.group(1)
    except:
        return ""


def convert_icstext2lines(ics_text):
    try:
        ics_text2 = ics_text.replace("\r\n", "\n")
        result = re.split(r"END:VEVENT\n|BEGIN:VEVENT\n",
                          ics_text2)
        ics_lines = []
        for event in result[1:-1]:
            if not event:
                continue
            ics_lines.append(
                f"BEGIN:VEVENT\n{event}END:VEVENT\n")
        ics_lines = sorted(ics_lines, key=lambda x: get_dtstart(x))
        ics_lines.insert(0, result[0])
        ics_lines.append(result[-1])
        return ics_lines
    except:
        return []


def get_ics_line_uid_changed(ics_line, uid):
    ics_line2 = ics_line.replace("\n", "@@@")
    ics_line3 = re.sub(r"UID:.+\.org", f"UID:{uid}", ics_line2)
    ics_line4 = ics_line3.replace("@@@", "\n")
    return ics_line4


def get_ics_lines(matches):
    calendar = Calendar()
    jst = timezone('Asia/Tokyo')
    for match in matches:
        event = Event()
        event.name = f"{match['対戦チーム名']} @{match['スタジアム']} {match['時刻']}〜"
        event.location = match['スタジアム']
        event.description = match['補足事項']
        ymdhm = f"{match['日付']} {match['時刻']}"
        ymd = match['日付']
        try:
            event.begin = jst.localize(datetime.strptime(
                ymdhm, "%Y/%m/%d %H:%M")).astimezone(timezone('UTC'))
            event.end = (jst.localize(datetime.strptime(ymdhm, "%Y/%m/%d %H:%M")) +
                         timedelta(hours=2)).astimezone(timezone('UTC'))
        except:
            event.begin = jst.localize(datetime.strptime(
                f"{ymd} 13:00", "%Y/%m/%d %H:%M")).astimezone(timezone('UTC'))
            event.make_all_day()
        alarm = EmailAlarm(trigger=timedelta(days=-1, hours=3))
        event.alarms.append(alarm)
        popup_alarm = DisplayAlarm(trigger=timedelta(hours=-3))
        event.alarms.append(popup_alarm)
        calendar.events.add(event)

    ics_lines1 = convert_icstext2lines(str(calendar))
    events1 = [r for r in ics_lines1 if "DTSTART" in r]
    ics_lines2 = [ics_lines1[0]]
    for event in events1:
        ics_lines2.append(event)
    ics_lines2.append(ics_lines1[-1])
    return ics_lines2


def load_ics_lines(filename):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            calendar = Calendar(f.read())
            return convert_icstext2lines(str(calendar))
    except:
        return []


def save_ics_lines(filename, ics_lines):
    with open(filename, "w", encoding="utf-8", newline='\r\n') as f:
        for line in ics_lines:
            line2 = line.replace("END:VALARM", "ATTENDEE:\nEND:VALARM")
            f.write(line2)
    print(f"Saved {filename}")


def make_ics(clubname, year1, year2):
    filename = f"all-clubs-ics/{clubname}.ics"
    old_ics_lines = load_ics_lines(filename)
    url = "https://www.jleague.jp/j1/match/search-list/?startdate="
    url += year1 + "-08-01&enddate="
    url += year2 + "-07-31&period=month&club="
    url += clubname
    matches = get_matches(url)
    new_ics_lines = get_ics_lines(matches)
    for i, new_ics_line in enumerate(new_ics_lines):
        for j, old_ics_line in enumerate(old_ics_lines):
            if get_matchname(new_ics_line) == get_matchname(old_ics_line):
                new_ics_lines[i] = get_ics_line_uid_changed(
                    new_ics_line, get_uid(old_ics_line))
                old_ics_lines[j] = None
                break
    save_ics_lines(filename, new_ics_lines)


if __name__ == "__main__":
    scriptname = sys.argv[0]
    if len(sys.argv) != 3:
        print(f"Usage: {scriptname} <YEAR1> <YEAR2>")
        sys.exit(1)
    year1 = sys.argv[1]
    year2 = sys.argv[2]
    for club in clubs:
        make_ics(club, year1, year2)
    print("Done.")
