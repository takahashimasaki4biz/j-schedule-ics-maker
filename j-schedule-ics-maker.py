#!/usr/bin/env python3

import sys
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from pytz import timezone
from ics import Calendar, Event
from ics.alarm import EmailAlarm, DisplayAlarm

import warnings
warnings.filterwarnings(
    "ignore",
    category=FutureWarning,
    message="Behaviour of str\\(Component\\) will change in version 0.9"
)


def zen_to_han(text):
    han1 = text.translate(str.maketrans(
        {chr(0xFF01 + i): chr(0x21 + i) for i in range(94)})) if text else ""
    han2 = han1.replace("　", " ")
    return han2


def get_soup(url):
    response = requests.get(url)
    response.encoding = response.apparent_encoding
    return BeautifulSoup(response.text, "html.parser")


def get_match_tags(soup):
    scheduleArea_tag = soup.find("section", class_="scheduleArea")
    contentBlock_tag = scheduleArea_tag.find("section", class_="contentBlock")
    return contentBlock_tag.find_all("section", class_="matchlistWrap", recursive=False)


def get_date(match_tag):
    date_tag = match_tag.find("h4", class_="leftRedTit")
    re_date = re.match(r"(\d{4})年(\d{1,2})月(\d{1,2})日.+", date_tag.get_text())
    return f"{re_date.group(1).zfill(4)}/{re_date.group(2).zfill(2)}/{re_date.group(3).zfill(2)}"


def get_time(match_tag):
    time_tag = match_tag.find("td", class_="stadium")
    time_text = time_tag.get_text(strip=True)
    return "未定" if time_text.startswith("未定") else time_text[:5]


def get_stadium_name(domain, match_tag):
    a_tag = match_tag.find("td", class_="match").find("a")
    soup2 = get_soup(domain + a_tag["href"])
    stadium_name_tag = soup2.find("span", class_="matchVsTitle__stadium")
    if stadium_name_tag:
        return stadium_name_tag.get_text(strip=True)
    return ""


def get_rival_team_name(match_tag):
    left_team = match_tag.find(
        "td", class_="clubName leftside").get_text(strip=True)
    right_team = match_tag.find(
        "td", class_="clubName rightside").get_text(strip=True)
    if left_team != "横浜FM":
        return left_team
    else:
        return right_team


def get_note_text(match_tag):
    note_text = match_tag.find("div", class_="leagAccTit").find(
        "h5").get_text(strip=True).replace(" ", "").replace("　", "")
    note_tag = match_tag.find("td", class_="note")
    if note_tag:
        note_text += "\n" + note_tag.get_text(strip=True)
    return zen_to_han(note_text)


def get_matches(url):
    soup = get_soup(url)
    domain = re.match(r"(https?://[^/]+)", url).group(1)
    match_tags = get_match_tags(soup)
    matches = []
    for match_tag in match_tags:
        match = {}
        match["日付"] = get_date(match_tag)
        match["時刻"] = get_time(match_tag)
        match["スタジアム"] = get_stadium_name(domain, match_tag)
        match["対戦チーム名"] = get_rival_team_name(match_tag)
        match["補足事項"] = get_note_text(match_tag)
        matches.append(match)
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
        event.name = f"vs {match['対戦チーム名']}@{match['スタジアム']} {match['時刻']}〜"
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
                ymd, "%Y/%m/%d")).astimezone(timezone('UTC'))
            event.make_all_day()
        alarm = EmailAlarm(trigger=timedelta(days=-1, hours=3))
        event.alarms.append(alarm)
        popup_alarm = DisplayAlarm(trigger=timedelta(hours=-3))
        event.alarms.append(popup_alarm)
        calendar.events.add(event)

    ics_lines1 = convert_icstext2lines(str(calendar))
    events1 = [r for r in ics_lines1 if "DTSTART" in r]
    # events2 = sorted(events1, key=lambda x: get_dtstart(x))
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
    print(f"\nSaved {filename}")


def main():
    filename = "j-schedule-ics-maker.ics"
    old_ics_lines = load_ics_lines(filename)

    # url = "https://www.jleague.jp/match/search/?category%5B%5D=j1&category%5B%5D=leaguecup&category%5B%5D=j2&category%5B%5D=j3&category%5B%5D=playoff&category%5B%5D=j2playoff&category%5B%5D=J3jflplayoff&category%5B%5D=emperor&category%5B%5D=acle&category%5B%5D=acl2&category%5B%5D=acl&category%5B%5D=fcwc&category%5B%5D=supercup&category%5B%5D=asiachallenge&category%5B%5D=jwc&club%5B%5D=yokohamafm&year=2025&month%5B%5D=01&month%5B%5D=02&month%5B%5D=03&month%5B%5D=04&month%5B%5D=05&month%5B%5D=06&month%5B%5D=07&month%5B%5D=08&month%5B%5D=09&month%5B%5D=10&month%5B%5D=11&month%5B%5D=12&tba=1"
    if len(sys.argv) < 2:
        print("Usage: {sys.argv[0]} <URL>")
        sys.exit(1)
    url = sys.argv[1]

    matches = get_matches(url)
    new_ics_lines = get_ics_lines(matches)

    for i, new_ics_line in enumerate(new_ics_lines):
        for old_ics_line in old_ics_lines:
            if get_matchname(new_ics_line) == get_matchname(old_ics_line):
                new_ics_lines[i] = get_ics_line_uid_changed(
                    new_ics_line, get_uid(old_ics_line))

    save_ics_lines(filename, new_ics_lines)


if __name__ == "__main__":
    main()
